"""
Public feature-flag entry point for Waddles modules (v3 flag plane).
======================================================================

Thin, stable-signature facade over `entitlement.EntitlementClient` -- the
real two-gate (PostHog flag AND license tier) evaluation and outage
degradation live there (see that module's docstring for the full contract).
Kept as its own module so product code imports a small surface
(`from flask_core.feature_flags import feature_enabled`) without needing to
know about the posthog/penguin_licensing wiring or gate adapters underneath.
"""

from __future__ import annotations

from typing import Optional

from .entitlement import get_entitlement_client


def _current_request_host() -> Optional[str]:
    """
    Best-effort request Host header, for the license bypass-domain check.

    Only meaningful inside an active Quart request context; a background
    job, CLI invocation, or scheduled task has none. Absence just means the
    bypass check can't fire (normal license gating still applies) -- it must
    never raise into the caller.
    """
    try:
        from quart import request  # type: ignore[import-not-found]

        return str(request.host)
    except Exception:  # noqa: BLE001 - no active request context, or quart unavailable
        return None


async def feature_enabled(
    flag_key: str,
    *,
    tenant: str,
    community: int | None = None,
    default: bool = False,
) -> bool:
    """
    Evaluate a namespaced (`waddles.<module>.<feature>`) flag for a tenant.

    Two gates, both must pass: the PostHog flag evaluates true AND the
    deployment's license tier entitles `flag_key` (the license check is
    skipped on a hardcoded license-bypass domain, per penguintech.md --
    never via env var or CLI flag; the flag check is never skipped).
    Degrades to the last-known cached value, or `default` if nothing has
    ever been cached, on any PostHog/license-server outage -- never raises
    into the caller. See `entitlement.EntitlementClient.evaluate`.
    """
    client = get_entitlement_client()
    return await client.evaluate(
        flag_key,
        tenant=tenant,
        community=community,
        default=default,
        request_host=_current_request_host(),
    )
