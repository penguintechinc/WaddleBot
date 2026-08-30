"""
Bot Module -- Feature contracts + default App bindings
==========================================================

Declares the Bot Module's four Feature contracts and registers each one's
shipped default App, per docs/plans/2026-08-26-v3-scbm-apps-design.md
``Features`` / ``Apps`` / migration phase P1 ("convert 2-3 Bot units as
proof"). All four are Free tier per the license catalog.

| Feature id         | Flag                     | Scopes                  |
|---------------------|--------------------------|--------------------------|
| ``bot.shoutout``    | ``waddles.bot.shoutout``    | ``bot.command:write``    |
| ``bot.commands``    | ``waddles.bot.commands``    | ``bot.command:write``    |
| ``bot.connectors``  | ``waddles.bot.connectors``  | ``bot.connector:write``  |
| ``bot.interactions``| ``waddles.bot.interactions``| ``bot.interaction:write``|

Each Feature gets exactly one shipped default App (``provider="builtin"``,
``is_default=True``) -- the "permanent fallback" the design doc's ``Apps ->
Binding resolution`` describes as un-swappable cluster-wide. Bot's actual
handler code still lives in its pre-v3 locations (``trigger/receiver/*``,
``action/pushing/*``, ``action/interactive/*`` -- Bot is ~0% green-field per
the ``Modules`` table); this module is the Feature-contract registration
point those handlers gate against, not a rewrite of them. See
``action/interactive/shoutout_interaction_module/app.py``'s
``create_shoutout`` for the one worked gate example wired end-to-end; the
other three Features follow the identical one-line guard.

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

MODULE = "bot"


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
        "id": "bot.shoutout",
        "version": 1,
        "module": MODULE,
        "requires_scopes": frozenset({"bot.command:write"}),
        "min_tier": "free",
        "flag": "waddles.bot.shoutout",
    },
    {
        "id": "bot.commands",
        "version": 1,
        "module": MODULE,
        "requires_scopes": frozenset({"bot.command:write"}),
        "min_tier": "free",
        "flag": "waddles.bot.commands",
    },
    {
        "id": "bot.connectors",
        "version": 1,
        "module": MODULE,
        "requires_scopes": frozenset({"bot.connector:write"}),
        "min_tier": "free",
        "flag": "waddles.bot.connectors",
    },
    {
        "id": "bot.interactions",
        "version": 1,
        "module": MODULE,
        "requires_scopes": frozenset({"bot.interaction:write"}),
        "min_tier": "free",
        "flag": "waddles.bot.interactions",
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
        "app_id": "waddles.bot.shoutout.default",
        "name": "Shoutout (default)",
        "version": "1.0.0",
        "feature": "waddles.bot.shoutout",
        "module": MODULE,
        "provider": "builtin",
        "surfaces": ("process", "action"),
        "permissions": ("bot.command:write",),
        "is_default": True,
    },
    {
        "app_id": "waddles.bot.commands.default",
        "name": "Command Dispatch (default)",
        "version": "1.0.0",
        "feature": "waddles.bot.commands",
        "module": MODULE,
        "provider": "builtin",
        "surfaces": ("process", "action"),
        "permissions": ("bot.command:write",),
        "is_default": True,
    },
    {
        "app_id": "waddles.bot.connectors.default",
        "name": "Platform Connectors (default)",
        "version": "1.0.0",
        "feature": "waddles.bot.connectors",
        "module": MODULE,
        "provider": "builtin",
        "surfaces": ("ingest",),
        "permissions": ("bot.connector:write",),
        "is_default": True,
    },
    {
        "app_id": "waddles.bot.interactions.default",
        "name": "Interactions (default)",
        "version": "1.0.0",
        "feature": "waddles.bot.interactions",
        "module": MODULE,
        "provider": "builtin",
        "surfaces": ("process", "action"),
        "permissions": ("bot.interaction:write",),
        "is_default": True,
    },
)


def build_contracts() -> Tuple[FeatureContract, ...]:
    """Parse and validate the four Bot Feature contracts, without registering them."""
    return tuple(parse_feature_contract(raw) for raw in _FEATURE_DEFS)


def build_default_apps() -> Tuple[AppManifest, ...]:
    """Parse and validate the four Bot default App manifests, without registering them."""
    return tuple(parse_manifest(raw) for raw in _DEFAULT_APP_DEFS)


def register_all(
    *,
    feature_registry: Optional[FeatureRegistry] = None,
    app_registry: Optional[AppRegistry] = None,
) -> Tuple[Tuple[FeatureContract, ...], Tuple[AppManifest, ...]]:
    """
    Parse, validate and register all four Bot Features and their shipped
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
