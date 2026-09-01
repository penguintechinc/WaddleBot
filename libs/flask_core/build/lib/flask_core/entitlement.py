"""
Two-gate entitlement client -- the real engine behind `feature_flags.feature_enabled`.
========================================================================================

Every feature gate in Waddles is two checks, both mandatory (critical-rules.md
Feature Flags & License Tiers):

1. **PostHog flag** -- general enablement (staged rollout, kill-switch,
   experimentation). Wraps the published `posthog` SDK, never a hand-rolled
   HTTP call.
2. **License tier** -- does the tenant's license entitle this feature.
   Wraps the published `penguin_licensing` package (`LicenseClient.validate()`
   against `license.penguintech.io`), skipped only on a hardcoded
   license-bypass hostname (penguintech.md), never via env var or CLI flag.

Neither gate is allowed to take a request path down with it. Both PostHog and
the license server can be unreachable at the same time; this module answers
with the last-known cached value, or `default` if nothing has ever been
cached for that (flag, tenant, community) tuple -- never an exception. See
`EntitlementClient.evaluate` for the exact fallback order.

`feature_flags.feature_enabled` is the stable, product-facing signature;
this module is its implementation and is not meant to be imported directly
by product code except to build a non-default `EntitlementClient` (e.g. to
register `tier_requirements`, or to inject fakes in tests).
"""

from __future__ import annotations

import asyncio
import fnmatch
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Mapping, Optional, Protocol

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# posthog wiring -- published SDK, required dependency (task explicitly asks
# this path be wired for real, not stubbed).
# ---------------------------------------------------------------------------
from posthog import Posthog  # noqa: E402

# ---------------------------------------------------------------------------
# penguin_licensing wiring -- published PyPI package. Import is guarded so a
# genuinely broken install degrades to a fail-closed (free-tier) adapter
# instead of taking the whole module down; every deployment CI validates the
# real dependency is present via requirements.txt, so this branch should
# never fire outside a misconfigured local env.
# ---------------------------------------------------------------------------
try:
    from penguin_licensing import LicenseClient, get_license_client

    _PENGUIN_LICENSING_AVAILABLE = True
except ImportError:  # pragma: no cover - only fires with a broken install
    LicenseClient = None  # type: ignore[assignment,misc]
    get_license_client = None  # type: ignore[assignment]
    _PENGUIN_LICENSING_AVAILABLE = False


# ---------------------------------------------------------------------------
# License-bypass hostnames (penguintech.md License Bypass Domains) -- skips
# the LICENSE gate only, never the flag gate. fnmatch requires the pattern to
# match the ENTIRE candidate string (unlike `in`/`.find`), so
# "waddles.penguintech.cloud.attacker.com" cannot match "*.penguintech.cloud"
# the way a naive substring or unanchored `.endswith` check might be coaxed
# into via a crafted Host header.
# ---------------------------------------------------------------------------
_BYPASS_HOSTNAME_PATTERNS: frozenset[str] = frozenset(
    {
        "penguincloud.io",
        "*.penguincloud.io",
        "penguintech.cloud",
        "*.penguintech.cloud",
        "waddles.app",
        "*.waddles.app",
    }
)

# Tier ordering. penguin_licensing's LicenseClient reports "community" for
# the unlicensed floor; critical-rules.md's canonical tier name is "free" --
# normalize both to the same rung rather than tracking two vocabularies.
_TIER_LEVELS: Mapping[str, int] = {
    "community": 1,
    "free": 1,
    "professional": 2,
    "enterprise": 3,
}

_DEFAULT_CACHE_TTL_SECONDS = 300.0  # matches penguin_licensing's own validate() cache window


def _normalize_tier(tier: str) -> str:
    """Map penguin_licensing's "community" onto the canonical "free" rung."""
    normalized = tier.strip().lower()
    return "free" if normalized == "community" else normalized


def _tier_level(tier: str) -> int:
    """Numeric rung for a tier name; unknown tiers rank below "free" (fail closed)."""
    return _TIER_LEVELS.get(_normalize_tier(tier), 0)


def is_bypass_domain(hostname: Optional[str]) -> bool:
    """
    True if `hostname` is a hardcoded license-bypass domain.

    Matches the FULL hostname against the pattern set via `fnmatch` -- never
    a substring/`.endswith` check, which a crafted Host header could defeat
    with a lookalike suffix. Only the LICENSE gate is skipped for a bypass
    domain; the PostHog flag gate always still runs.
    """
    if not hostname:
        return False
    host = hostname.split(":", 1)[0].strip().lower()
    return any(fnmatch.fnmatchcase(host, pattern) for pattern in _BYPASS_HOSTNAME_PATTERNS)


# ---------------------------------------------------------------------------
# Gate adapters -- thin, injectable seams so tests exercise EntitlementClient
# without a live PostHog/license-server connection.
# ---------------------------------------------------------------------------
class FlagGate(Protocol):
    """Adapter contract for the PostHog general-enablement gate."""

    def is_enabled(
        self,
        flag_key: str,
        distinct_id: str,
        *,
        groups: Optional[Mapping[str, str]] = None,
    ) -> Optional[bool]:
        """Evaluate a flag. Returns None if the flag can't be resolved (error or unknown key)."""
        ...


class LicenseGate(Protocol):
    """Adapter contract for the license-tier gate."""

    def resolve_tier(self) -> str:
        """Return the deployment's current license tier ("free"/"professional"/"enterprise")."""
        ...


class PostHogFlagGate:
    """Wraps the published `posthog` SDK -- the only place this module calls it."""

    def __init__(self, client: Posthog) -> None:
        """Hold a pre-built `Posthog` client (constructed by `from_env`, or injected in tests)."""
        self._client = client

    @classmethod
    def from_env(cls) -> "PostHogFlagGate":
        """
        Build a client from POSTHOG_HOST / POSTHOG_API_KEY.

        `POSTHOG_KEY` is accepted as a fallback for parity with the
        `integrating-license-server` skill's documented env name. Without a
        key the client is constructed `disabled=True` so calls resolve to
        None (unresolvable) rather than raising -- degradation, not a crash,
        for an unconfigured deployment.
        """
        api_key = os.getenv("POSTHOG_API_KEY") or os.getenv("POSTHOG_KEY", "")
        host = os.getenv("POSTHOG_HOST", "https://license.penguintech.io")
        client = Posthog(project_api_key=api_key or "disabled", host=host, disabled=not api_key)
        return cls(client)

    def is_enabled(
        self,
        flag_key: str,
        distinct_id: str,
        *,
        groups: Optional[Mapping[str, str]] = None,
    ) -> Optional[bool]:
        """Evaluate via PostHog; any error (network, disabled client, unknown flag) yields None."""
        try:
            # TODO: posthog-python 7.x deprecates feature_enabled() in favor of
            # evaluate_flags()+flags.is_enabled(); migrate once that surface is
            # stable and documented in the integrating-license-server skill.
            return self._client.feature_enabled(flag_key, distinct_id, groups=groups)
        except Exception:  # noqa: BLE001 - a flag gate must never raise into a request path
            logger.warning("entitlement.flag_gate_error", extra={"flag_key": flag_key})
            return None


class _CommunityOnlyLicenseGate:
    """
    Fail-closed stand-in used only when `penguin_licensing` fails to import.

    TODO: once a `penguin-licensing` release is guaranteed present in every
    deployment target (it already imports cleanly against the PyPI package
    in this worktree's venv), delete this fallback and let `PenguinLicenseGate
    .from_env` raise ImportError unconditionally instead of degrading silently.
    """

    def resolve_tier(self) -> str:
        """Always report the unlicensed floor -- never grants entitlement it can't verify."""
        return "free"


class PenguinLicenseGate:
    """Wraps `penguin_licensing.LicenseClient.validate().tier` -- the only place this module calls it."""

    def __init__(self, client: object) -> None:
        """Hold a `LicenseClient` (real or injected fake) with a `.validate()` method."""
        self._client = client

    @classmethod
    def from_env(cls) -> LicenseGate:
        """
        Build the license gate to use for this process.

        Returns `_CommunityOnlyLicenseGate` directly (not wrapped in
        `PenguinLicenseGate`, whose `resolve_tier` assumes a `.validate()`
        method the fallback doesn't have) when `penguin_licensing` failed to
        import; otherwise a `PenguinLicenseGate` over the real shared client.
        """
        if not _PENGUIN_LICENSING_AVAILABLE:
            logger.error(
                "entitlement.penguin_licensing_unavailable",
                extra={"action": "falling back to fail-closed free-tier adapter"},
            )
            return _CommunityOnlyLicenseGate()
        return cls(get_license_client())

    def resolve_tier(self) -> str:
        """Validate against the license server (penguin_licensing handles its own caching/fail-closed logic)."""
        return str(self._client.validate().tier)  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# In-process degradation cache
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class _CacheEntry:
    """A single (flag, tenant, community) decision, remembered for the outage window."""

    value: bool
    expires_at: float


CacheKey = tuple[str, str, Optional[int]]


@dataclass(slots=True)
class EntitlementClient:
    """
    Evaluates the two-gate (flag AND license) decision for a flag/tenant/community.

    Both gates are injectable (`flag_gate`, `license_gate`) so tests run
    without a live PostHog/license-server connection. `tier_requirements`
    maps a namespaced flag key (`waddles.<module>.<feature>`) to the minimum
    tier it needs; a flag absent from the map requires only "free" -- i.e.
    the license gate passes trivially unless a module explicitly registers a
    higher bar, matching critical-rules.md's "Free: no gated functionality"
    default.
    """

    flag_gate: FlagGate = field(default_factory=lambda: PostHogFlagGate.from_env())
    license_gate: LicenseGate = field(default_factory=lambda: PenguinLicenseGate.from_env())
    tier_requirements: Mapping[str, str] = field(default_factory=dict)
    cache_ttl_seconds: float = field(
        default_factory=lambda: float(
            os.getenv("ENTITLEMENT_CACHE_TTL_SECONDS", str(_DEFAULT_CACHE_TTL_SECONDS))
        )
    )
    _cache: dict[CacheKey, _CacheEntry] = field(default_factory=dict, init=False, repr=False)

    async def evaluate(
        self,
        flag_key: str,
        *,
        tenant: str,
        community: Optional[int] = None,
        default: bool = False,
        request_host: Optional[str] = None,
    ) -> bool:
        """
        Resolve `flag_key` for `tenant` (optionally narrower per `community`).

        Both gates are checked live on every call (no silently-stale
        decisions while the services are healthy -- entitlement freshness
        matters for licensing). Wrapped end-to-end: any unexpected exception
        here still returns `default` rather than propagating into the
        caller's request path.
        """
        try:
            return await self._evaluate(
                flag_key,
                tenant=tenant,
                community=community,
                default=default,
                request_host=request_host,
            )
        except Exception:  # noqa: BLE001 - entitlement must never crash a request path
            logger.exception("entitlement.evaluate_unexpected_error", extra={"flag_key": flag_key})
            return default

    async def _evaluate(
        self,
        flag_key: str,
        *,
        tenant: str,
        community: Optional[int],
        default: bool,
        request_host: Optional[str],
    ) -> bool:
        if not tenant:
            raise ValueError("tenant is required for entitlement evaluation")

        cache_key: CacheKey = (flag_key, tenant, community)
        now = time.monotonic()

        flag_result = await self._check_flag(flag_key, tenant, community)

        bypassed = is_bypass_domain(request_host)
        license_result: Optional[bool] = True if bypassed else await self._check_license(flag_key)

        if flag_result is None or license_result is None:
            cached = self._cache.get(cache_key)
            if cached is not None and cached.expires_at > now:
                logger.info(
                    "entitlement.degraded_cache_hit",
                    extra={"flag_key": flag_key, "tenant": tenant, "value": cached.value},
                )
                return cached.value
            logger.info(
                "entitlement.degraded_default",
                extra={"flag_key": flag_key, "tenant": tenant, "default": default},
            )
            return default

        enabled = bool(flag_result) and bool(license_result)
        self._cache[cache_key] = _CacheEntry(value=enabled, expires_at=now + self.cache_ttl_seconds)
        return enabled

    async def _check_flag(
        self, flag_key: str, tenant: str, community: Optional[int]
    ) -> Optional[bool]:
        """Evaluate the PostHog gate off the event loop; any failure yields None (unresolvable)."""
        distinct_id = tenant if community is None else f"{tenant}:{community}"
        groups = {"tenant": tenant}
        try:
            return await asyncio.to_thread(
                self.flag_gate.is_enabled, flag_key, distinct_id, groups=groups
            )
        except Exception:  # noqa: BLE001 - defense in depth atop the adapter's own try/except
            logger.warning("entitlement.flag_gate_unreachable", extra={"flag_key": flag_key})
            return None

    async def _check_license(self, flag_key: str) -> Optional[bool]:
        """Resolve tier off the event loop and compare against `flag_key`'s requirement."""
        try:
            tier = await asyncio.to_thread(self.license_gate.resolve_tier)
        except Exception:  # noqa: BLE001 - a down license server must degrade, not raise
            logger.warning("entitlement.license_gate_unreachable", extra={"flag_key": flag_key})
            return None
        required = self.tier_requirements.get(flag_key, "free")
        return _tier_level(tier) >= _tier_level(required)


# ---------------------------------------------------------------------------
# Process-wide default client -- mirrors penguin_licensing's own
# double-checked-lock singleton so concurrent first requests share one
# warm cache instead of each building a rival (cold) EntitlementClient.
# ---------------------------------------------------------------------------
_default_client: Optional[EntitlementClient] = None
_default_client_lock = threading.Lock()


def get_entitlement_client() -> EntitlementClient:
    """Return the process-wide `EntitlementClient`, built from env on first use."""
    global _default_client

    client = _default_client
    if client is not None:
        return client

    with _default_client_lock:
        if _default_client is None:
            _default_client = EntitlementClient()
        return _default_client
