"""
App manifest schema
====================

Per docs/plans/2026-08-26-v3-scbm-apps-design.md ``Apps``: an App implements
one or more Feature contracts. "First-party defaults are Apps too — shipping
in the box is a default *binding*, not a different kind of code." This
module defines the manifest shape every App (first-party or marketplace)
must declare, and the validator that keeps a bad manifest from ever reaching
the registry.

Naming is deliberately load-bearing: ``app_id`` is namespaced
``waddles.<module>.<feature>.<app>`` so the App's Feature and Module are
recoverable from the id alone, and ``feature`` (``waddles.<module>.<feature>``)
must be the exact prefix of ``app_id`` minus its trailing App segment — the
manifest cannot claim to implement one Feature while being named for another.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, Tuple

# Modules table in the design doc: Bot, Social, Marketing, Customer.
KNOWN_MODULES = frozenset({"bot", "social", "marketing", "customer"})

# Pipeline stages an App's manifest may declare it touches ("stages" in the
# design doc's YAML example; named "surfaces" per this task's schema).
KNOWN_SURFACES = frozenset({"ingest", "process", "action"})

KNOWN_PROVIDERS = frozenset({"builtin", "thirdparty"})

_SEGMENT = r"[a-z0-9][a-z0-9_-]*"
# waddles.<module>.<feature>.<app> -- exactly four dot-separated tokens.
_APP_ID_RE = re.compile(rf"^waddles\.{_SEGMENT}\.{_SEGMENT}\.{_SEGMENT}$")
# waddles.<module>.<feature> -- exactly three dot-separated tokens.
_FEATURE_RE = re.compile(rf"^waddles\.{_SEGMENT}\.{_SEGMENT}$")
# SemVer 2.0.0 core + optional pre-release/build metadata.
_SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*)?"
    r"(?:\+[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*)?$"
)


class ManifestError(Exception):
    """
    Raised when a manifest dict fails validation. ``reason`` is a stable
    machine-checkable code (see the ``REASON_*`` constants below) so callers
    and tests can assert on *why* a manifest was rejected, not just that it
    was.
    """

    def __init__(self, reason: str, detail: str) -> None:
        self.reason = reason
        super().__init__(f"{reason}: {detail}")


REASON_MISSING_FIELD = "missing_field"
REASON_BAD_SEMVER = "bad_semver"
REASON_NOT_NAMESPACED = "not_namespaced"
REASON_UNKNOWN_MODULE = "unknown_module"
REASON_FEATURE_PREFIX_MISMATCH = "feature_prefix_mismatch"
REASON_INVALID_PROVIDER = "invalid_provider"
REASON_UNKNOWN_SURFACE = "unknown_surface"

_REQUIRED_STR_FIELDS = ("app_id", "name", "version", "feature", "module", "provider")


@dataclass(slots=True, frozen=True)
class AppManifest:
    """
    A validated, installable App descriptor.

    Built exclusively by :func:`parse_manifest` -- constructing one directly
    bypasses the semver/namespacing/module/feature-prefix checks, so callers
    reading manifests from disk, a marketplace payload, or a DB row must
    always go through ``parse_manifest``.
    """

    app_id: str
    name: str
    version: str
    feature: str
    module: str
    provider: str  # 'builtin' | 'thirdparty'
    surfaces: Tuple[str, ...] = ()
    permissions: Tuple[str, ...] = ()
    config_schema: Dict[str, Any] = field(default_factory=dict)
    is_default: bool = False


def _require_str(data: Dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ManifestError(REASON_MISSING_FIELD, f"{key!r} must be a non-empty string")
    return value


def parse_manifest(data: Dict[str, Any]) -> AppManifest:
    """
    Validate a raw manifest dict (parsed YAML/JSON, or a marketplace
    payload) and build an :class:`AppManifest`.

    Rejects, in order, with a typed :class:`ManifestError`:

    1. missing/empty required fields
    2. ``version`` that is not valid SemVer 2.0.0
    3. ``app_id`` that is not namespaced ``waddles.<module>.<feature>.<app>``
    4. ``module`` not one of the known Modules
    5. ``app_id``'s feature-prefix (``app_id`` minus its trailing App
       segment) not equal to ``feature``
    6. ``provider`` outside ``{builtin, thirdparty}``
    7. any ``surfaces`` entry outside ``{ingest, process, action}``
    """
    for key in _REQUIRED_STR_FIELDS:
        _require_str(data, key)

    app_id = data["app_id"]
    name = data["name"]
    version = data["version"]
    feature = data["feature"]
    module = data["module"]
    provider = data["provider"]

    if not _SEMVER_RE.match(version):
        raise ManifestError(REASON_BAD_SEMVER, f"{version!r} is not valid SemVer 2.0.0")

    if not _APP_ID_RE.match(app_id):
        raise ManifestError(
            REASON_NOT_NAMESPACED,
            f"app_id {app_id!r} must be namespaced 'waddles.<module>.<feature>.<app>'",
        )

    if not _FEATURE_RE.match(feature):
        raise ManifestError(
            REASON_NOT_NAMESPACED,
            f"feature {feature!r} must be namespaced 'waddles.<module>.<feature>'",
        )

    if module not in KNOWN_MODULES:
        raise ManifestError(
            REASON_UNKNOWN_MODULE, f"module {module!r} is not one of {sorted(KNOWN_MODULES)}"
        )

    app_id_feature_prefix = app_id.rsplit(".", 1)[0]
    if app_id_feature_prefix != feature:
        raise ManifestError(
            REASON_FEATURE_PREFIX_MISMATCH,
            f"app_id {app_id!r} implies feature {app_id_feature_prefix!r}, "
            f"but manifest declares feature {feature!r}",
        )

    if provider not in KNOWN_PROVIDERS:
        raise ManifestError(
            REASON_INVALID_PROVIDER, f"provider {provider!r} is not one of {sorted(KNOWN_PROVIDERS)}"
        )

    surfaces_raw = data.get("surfaces", ())
    surfaces = tuple(surfaces_raw)
    for surface in surfaces:
        if surface not in KNOWN_SURFACES:
            raise ManifestError(
                REASON_UNKNOWN_SURFACE,
                f"surface {surface!r} is not one of {sorted(KNOWN_SURFACES)}",
            )

    permissions = tuple(data.get("permissions", ()))
    config_schema = dict(data.get("config_schema", {}))
    is_default = bool(data.get("is_default", False))

    return AppManifest(
        app_id=app_id,
        name=name,
        version=version,
        feature=feature,
        module=module,
        provider=provider,
        surfaces=surfaces,
        permissions=permissions,
        config_schema=config_schema,
        is_default=is_default,
    )
