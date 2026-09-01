"""
Event Module -- Feature contracts + default App bindings
============================================================

Declares the Event Module's two Feature contracts and registers each one's
shipped default App, per docs/plans/2026-08-31-v3-sccembs-program-plan.md
SS9 P4 and docs/plans/2026-08-31-hubapi-node-to-quart-migration.md SS2's
controller inventory: ``calendarController`` -> ``waddles.event.calendar``,
``ticketController`` -> ``waddles.event.ticketing`` ("proxy to calendar for
event ticketing"). Both are already ported and live at
``hub_api/blueprints/v1/event.py`` (M8) -- a table-driven `ProxyRoute`
list, not per-function handlers (that file's own module docstring explains
why); this PR adds a `feature_flag` field to that table and wires the
two-gate guard into its single generic `_make_handler`, gating all 58
ported routes by capability in one place rather than one at a time.

| Feature id            | Flag                       | Tier         | Scopes                    |
|-------------------------|-------------------------------|--------------|------------------------------|
| ``event.calendar``    | ``waddles.event.calendar``  | free         | ``event.calendar:write``  |
| ``event.ticketing``   | ``waddles.event.ticketing`` | professional | ``event.calendar:admin``  |

Each Feature gets exactly one shipped default App (``provider="builtin"``,
``is_default=True``) -- the "permanent fallback" the design doc's ``Apps ->
Binding resolution`` describes as un-swappable cluster-wide. See
``hub_api/blueprints/v1/event.py``'s ``_make_handler`` for the worked gate
wired end-to-end this PR (every `calendarController.js`/`calendarAdmin.js`
route defaults to ``event.calendar``; every `ticketController.js` route is
explicitly tagged ``event.ticketing``); the public booking routes
(`scope=None`) are intentionally ungated (`feature_flag=None` -- no tenant
context to evaluate against).

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

MODULE = "event"


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
        "id": "event.calendar",
        "version": 1,
        "module": MODULE,
        "requires_scopes": frozenset({"event.calendar:write"}),
        "min_tier": "free",
        "flag": "waddles.event.calendar",
    },
    {
        "id": "event.ticketing",
        "version": 1,
        "module": MODULE,
        "requires_scopes": frozenset({"event.calendar:admin"}),
        "min_tier": "professional",
        "flag": "waddles.event.ticketing",
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
        "app_id": "waddles.event.calendar.default",
        "name": "Calendar (default)",
        "version": "1.0.0",
        "feature": "waddles.event.calendar",
        "module": MODULE,
        "provider": "builtin",
        "surfaces": ("action",),
        "permissions": ("event.calendar:write",),
        "is_default": True,
    },
    {
        "app_id": "waddles.event.ticketing.default",
        "name": "Ticketing (default)",
        "version": "1.0.0",
        "feature": "waddles.event.ticketing",
        "module": MODULE,
        "provider": "builtin",
        "surfaces": ("action",),
        "permissions": ("event.calendar:admin",),
        "is_default": True,
    },
)


def build_contracts() -> Tuple[FeatureContract, ...]:
    """Parse and validate the two Event Feature contracts, without registering them."""
    return tuple(parse_feature_contract(raw) for raw in _FEATURE_DEFS)


def build_default_apps() -> Tuple[AppManifest, ...]:
    """Parse and validate the two Event default App manifests, without registering them."""
    return tuple(parse_manifest(raw) for raw in _DEFAULT_APP_DEFS)


def register_all(
    *,
    feature_registry: Optional[FeatureRegistry] = None,
    app_registry: Optional[AppRegistry] = None,
) -> Tuple[Tuple[FeatureContract, ...], Tuple[AppManifest, ...]]:
    """
    Parse, validate and register both Event Features and their shipped
    default Apps.

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
