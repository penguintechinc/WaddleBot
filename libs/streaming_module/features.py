"""
Streaming Module -- Feature contracts + default App bindings
================================================================

Declares the Streaming Module's five Feature contracts and registers each
one's shipped default App, per docs/plans/2026-08-31-v3-sccembs-program-plan.md
SS9 P4 and docs/plans/2026-08-31-hubapi-node-to-quart-migration.md SS2's
controller inventory (the 5 M7-Streaming controllers). All five are already
ported and live at ``hub_api/blueprints/v1/{stream,streaming,calls,music,
overlay}.py``.

| Feature id                    | Flag                                | Tier         | Scopes                       |
|----------------------------------|------------------------------------------|--------------|-----------------------------------|
| ``streaming.stream``          | ``waddles.streaming.stream``          | free         | ``streaming.stream:read``     |
| ``streaming.broadcast``       | ``waddles.streaming.broadcast``       | professional | ``streaming.broadcast:admin`` |
| ``streaming.rtc``             | ``waddles.streaming.rtc``             | free         | ``streaming.calls:admin``     |
| ``streaming.music_station``   | ``waddles.streaming.music_station``   | free         | ``streaming.music:admin``     |
| ``streaming.overlays``        | ``waddles.streaming.overlays``        | free         | ``streaming.overlay:admin``   |

``streaming.broadcast`` (``streamingController.js``'s forward/record/
transcode destination management -- program plan SS4.3's monetized
RECORD/FORWARD/TRANSCODE capabilities) is the module's one paid capability;
the other four are free-tier engagement/control-plane surfaces (live-stream
listings, calls/RTC control-plane, the music station "major advertised
selling point" per the program plan, and browser-source overlay token
management).

Each Feature gets exactly one shipped default App (``provider="builtin"``,
``is_default=True``) -- the "permanent fallback" the design doc's ``Apps ->
Binding resolution`` describes as un-swappable cluster-wide. See
``hub_api/blueprints/v1/stream.py``'s ``get_live_streams`` for one worked
gate example wired end-to-end (this PR); ``streaming.py``/``calls.py``/
``music.py``/``overlay.py`` each carry their own one-line guard in their
own blueprint (this PR).

Call :func:`register_all` once at process startup to register these
against the process-wide singletons. Tests pass fresh
:class:`~flask_core.feature_registry.FeatureRegistry` /
:class:`~flask_core.app_registry.AppRegistry` instances for isolation
instead of calling it bare.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from flask_core.app_manifest import AppManifest, parse_manifest
from flask_core.app_registry import AppRegistry
from flask_core.app_registry import get_registry as get_app_registry
from flask_core.feature_contract import FeatureContract, parse_feature_contract
from flask_core.feature_registry import FeatureRegistry
from flask_core.feature_registry import get_registry as get_feature_registry

MODULE = "streaming"


class ScopeWideningError(Exception):
    """
    Raised when a default App's manifest ``permissions`` are not a subset
    of its Feature contract's ``requires_scopes``.

    A default App is the shipped fallback every deployment trusts as a
    known-good baseline (design doc ``Apps -> Binding resolution``); one
    that grants itself scopes beyond what its own Feature declares would
    silently widen what "the box" is allowed to do relative to what the
    Feature's contract -- and by extension its MCP tool derivation -- says
    it can do. Caught at registration time, not at an authz boundary.
    """


# ---------------------------------------------------------------------------
# Feature contracts -- raw dicts, validated by parse_feature_contract().
# ---------------------------------------------------------------------------
_FEATURE_DEFS: Tuple[Dict[str, Any], ...] = (
    {
        "id": "streaming.stream",
        "version": 1,
        "module": MODULE,
        "requires_scopes": frozenset({"streaming.stream:read"}),
        "min_tier": "free",
        "flag": "waddles.streaming.stream",
    },
    {
        "id": "streaming.broadcast",
        "version": 1,
        "module": MODULE,
        "requires_scopes": frozenset({"streaming.broadcast:admin"}),
        "min_tier": "professional",
        "flag": "waddles.streaming.broadcast",
    },
    {
        "id": "streaming.rtc",
        "version": 1,
        "module": MODULE,
        "requires_scopes": frozenset({"streaming.calls:admin"}),
        "min_tier": "free",
        "flag": "waddles.streaming.rtc",
    },
    {
        "id": "streaming.music_station",
        "version": 1,
        "module": MODULE,
        "requires_scopes": frozenset({"streaming.music:admin"}),
        "min_tier": "free",
        "flag": "waddles.streaming.music_station",
    },
    {
        "id": "streaming.overlays",
        "version": 1,
        "module": MODULE,
        "requires_scopes": frozenset({"streaming.overlay:admin"}),
        "min_tier": "free",
        "flag": "waddles.streaming.overlays",
    },
)

# ---------------------------------------------------------------------------
# Shipped default Apps -- raw dicts, validated by parse_manifest(). Each
# `feature` is the corresponding contract's `flag` ("waddles." + id), and
# each `permissions` set is a subset of that contract's `requires_scopes`
# (checked in register_all(), not just by construction here).
# ---------------------------------------------------------------------------
_DEFAULT_APP_DEFS: Tuple[Dict[str, Any], ...] = (
    {
        "app_id": "waddles.streaming.stream.default",
        "name": "Live Streams (default)",
        "version": "1.0.0",
        "feature": "waddles.streaming.stream",
        "module": MODULE,
        "provider": "builtin",
        "surfaces": ("action",),
        "permissions": ("streaming.stream:read",),
        "is_default": True,
    },
    {
        "app_id": "waddles.streaming.broadcast.default",
        "name": "Broadcast Forwarding (default)",
        "version": "1.0.0",
        "feature": "waddles.streaming.broadcast",
        "module": MODULE,
        "provider": "builtin",
        "surfaces": ("action",),
        "permissions": ("streaming.broadcast:admin",),
        "is_default": True,
    },
    {
        "app_id": "waddles.streaming.rtc.default",
        "name": "Calls / RTC (default)",
        "version": "1.0.0",
        "feature": "waddles.streaming.rtc",
        "module": MODULE,
        "provider": "builtin",
        "surfaces": ("ingest", "action"),
        "permissions": ("streaming.calls:admin",),
        "is_default": True,
    },
    {
        "app_id": "waddles.streaming.music_station.default",
        "name": "Music Station (default)",
        "version": "1.0.0",
        "feature": "waddles.streaming.music_station",
        "module": MODULE,
        "provider": "builtin",
        "surfaces": ("process", "presentation"),
        "permissions": ("streaming.music:admin",),
        "is_default": True,
    },
    {
        "app_id": "waddles.streaming.overlays.default",
        "name": "Overlays (default)",
        "version": "1.0.0",
        "feature": "waddles.streaming.overlays",
        "module": MODULE,
        "provider": "builtin",
        "surfaces": ("presentation",),
        "permissions": ("streaming.overlay:admin",),
        "is_default": True,
    },
)


def build_contracts() -> Tuple[FeatureContract, ...]:
    """Parse and validate the five Streaming Feature contracts, without registering them."""
    return tuple(parse_feature_contract(raw) for raw in _FEATURE_DEFS)


def build_default_apps() -> Tuple[AppManifest, ...]:
    """Parse and validate the five Streaming default App manifests, without registering them."""
    return tuple(parse_manifest(raw) for raw in _DEFAULT_APP_DEFS)


def register_all(
    *,
    feature_registry: Optional[FeatureRegistry] = None,
    app_registry: Optional[AppRegistry] = None,
) -> Tuple[Tuple[FeatureContract, ...], Tuple[AppManifest, ...]]:
    """
    Parse, validate and register all five Streaming Features and their
    shipped default Apps.

    Defaults to the process-wide singletons
    (:func:`flask_core.feature_registry.get_registry`,
    :func:`flask_core.app_registry.get_registry`); tests pass fresh
    instances for isolation. Every default App's ``permissions`` is checked
    against its own Feature's ``requires_scopes`` -- raising
    :class:`ScopeWideningError` -- before anything is registered, so a
    violation never leaves the registries partially populated.
    """
    f_registry = feature_registry if feature_registry is not None else get_feature_registry()
    a_registry = app_registry if app_registry is not None else get_app_registry()

    contracts = build_contracts()
    manifests = build_default_apps()

    contracts_by_id = {contract.id: contract for contract in contracts}
    for manifest in manifests:
        contract_id = manifest.feature.removeprefix("waddles.")
        contract = contracts_by_id[contract_id]
        widened = set(manifest.permissions) - contract.requires_scopes
        if widened:
            raise ScopeWideningError(
                f"default app {manifest.app_id!r} widens feature {contract.id!r}'s "
                f"scopes: {sorted(widened)}"
            )

    for contract in contracts:
        f_registry.register(contract)
    for manifest in manifests:
        a_registry.register(manifest)

    return contracts, manifests
