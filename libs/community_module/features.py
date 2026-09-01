"""
Community Module -- Feature contracts + default App bindings
================================================================

Declares the Community Module's eleven Feature contracts and registers each
one's shipped default App, per docs/plans/2026-08-31-v3-sccembs-program-plan.md
SS9 P4 ("per-module default bundles + per-capability flags -- migrate
KNOWN_MODULES to SCCEMBS; map 44 controllers -> default App Bundles per
module") and docs/plans/2026-08-31-hubapi-node-to-quart-migration.md SS2's
controller inventory (the 9 M6-Community controllers). Nine of eleven map
1:1 onto an already-ported ``hub_api/blueprints/v1/community_*.py`` group;
``community.forums``/``community.interactions`` are BOTH served by the same
``community_interaction.py`` blueprint (its own docstring: "channel CRUD...
forum read/post/reply... roles" are two distinct capabilities sharing one
file, split here to match the migration doc's own per-capability flag
convention); ``community.virtual_stages`` is greenfield (migration doc SS2's
"Greenfield: Community (forum/virtual-stages)" line) -- no handler exists
yet, mirroring ``core_platform_module``'s precedent of registering a
Feature contract for a capability with "no code here to gate yet".

| Feature id                     | Flag                                    | Tier         | Scopes                              |
|----------------------------------|--------------------------------------------|--------------|----------------------------------------|
| ``community.chat``             | ``waddles.community.chat``             | free         | ``community.chat:read``             |
| ``community.polls``            | ``waddles.community.polls``            | free         | ``community.polls:write``           |
| ``community.announcements``    | ``waddles.community.announcements``    | free         | ``community.announcements:write``   |
| ``community.forms``            | ``waddles.community.forms``            | free         | ``community.forms:write``           |
| ``community.forums``           | ``waddles.community.forums``           | free         | ``community.interaction:write``     |
| ``community.interactions``     | ``waddles.community.interactions``     | free         | ``community.interaction:manage_channels`` |
| ``community.activity``         | ``waddles.community.activity``         | free         | ``community.activity:read``         |
| ``community.loyalty``          | ``waddles.community.loyalty``          | professional | ``community.loyalty:write``         |
| ``community.inventory``        | ``waddles.community.inventory``        | professional | ``community.inventory:write``       |
| ``community.raffles``          | ``waddles.community.raffles``          | professional | ``community.raffle:write``          |
| ``community.virtual_stages``   | ``waddles.community.virtual_stages``   | professional | ``community.virtual_stages:write``  |

Each Feature gets exactly one shipped default App (``provider="builtin"``,
``is_default=True``) -- the "permanent fallback" the design doc's ``Apps ->
Binding resolution`` describes as un-swappable cluster-wide. Community's
actual handler code lives in ``hub_api/blueprints/v1/community_*.py`` (M6,
already ported); this module is the Feature-contract registration point
those handlers gate against. See ``hub_api/blueprints/v1/community_chat.py``'s
``chat_history`` for one worked gate example wired end-to-end (this PR);
the free-tier engagement Features (``community.polls``/``.announcements``/
``.forms``/``.forums``/``.interactions``/``.activity``) each carry their own
one-line guard in their own blueprint (this PR); the monetized/economy
Features (``.loyalty``/``.inventory``/``.raffles``) likewise. Only
``community.virtual_stages`` has no handler to gate yet.

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

MODULE = "community"


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
        "id": "community.chat",
        "version": 1,
        "module": MODULE,
        "requires_scopes": frozenset({"community.chat:read"}),
        "min_tier": "free",
        "flag": "waddles.community.chat",
    },
    {
        "id": "community.polls",
        "version": 1,
        "module": MODULE,
        "requires_scopes": frozenset({"community.polls:write"}),
        "min_tier": "free",
        "flag": "waddles.community.polls",
    },
    {
        "id": "community.announcements",
        "version": 1,
        "module": MODULE,
        "requires_scopes": frozenset({"community.announcements:write"}),
        "min_tier": "free",
        "flag": "waddles.community.announcements",
    },
    {
        "id": "community.forms",
        "version": 1,
        "module": MODULE,
        "requires_scopes": frozenset({"community.forms:write"}),
        "min_tier": "free",
        "flag": "waddles.community.forms",
    },
    {
        "id": "community.forums",
        "version": 1,
        "module": MODULE,
        "requires_scopes": frozenset({"community.interaction:write"}),
        "min_tier": "free",
        "flag": "waddles.community.forums",
    },
    {
        "id": "community.interactions",
        "version": 1,
        "module": MODULE,
        "requires_scopes": frozenset({"community.interaction:manage_channels"}),
        "min_tier": "free",
        "flag": "waddles.community.interactions",
    },
    {
        "id": "community.activity",
        "version": 1,
        "module": MODULE,
        "requires_scopes": frozenset({"community.activity:read"}),
        "min_tier": "free",
        "flag": "waddles.community.activity",
    },
    {
        "id": "community.loyalty",
        "version": 1,
        "module": MODULE,
        "requires_scopes": frozenset({"community.loyalty:write"}),
        "min_tier": "professional",
        "flag": "waddles.community.loyalty",
    },
    {
        "id": "community.inventory",
        "version": 1,
        "module": MODULE,
        "requires_scopes": frozenset({"community.inventory:write"}),
        "min_tier": "professional",
        "flag": "waddles.community.inventory",
    },
    {
        "id": "community.raffles",
        "version": 1,
        "module": MODULE,
        "requires_scopes": frozenset({"community.raffle:write"}),
        "min_tier": "professional",
        "flag": "waddles.community.raffles",
    },
    {
        "id": "community.virtual_stages",
        "version": 1,
        "module": MODULE,
        "requires_scopes": frozenset({"community.virtual_stages:write"}),
        "min_tier": "professional",
        "flag": "waddles.community.virtual_stages",
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
        "app_id": "waddles.community.chat.default",
        "name": "Chat (default)",
        "version": "1.0.0",
        "feature": "waddles.community.chat",
        "module": MODULE,
        "provider": "builtin",
        "surfaces": ("action",),
        "permissions": ("community.chat:read",),
        "is_default": True,
    },
    {
        "app_id": "waddles.community.polls.default",
        "name": "Polls (default)",
        "version": "1.0.0",
        "feature": "waddles.community.polls",
        "module": MODULE,
        "provider": "builtin",
        "surfaces": ("process", "action"),
        "permissions": ("community.polls:write",),
        "is_default": True,
    },
    {
        "app_id": "waddles.community.announcements.default",
        "name": "Announcements (default)",
        "version": "1.0.0",
        "feature": "waddles.community.announcements",
        "module": MODULE,
        "provider": "builtin",
        "surfaces": ("process", "action"),
        "permissions": ("community.announcements:write",),
        "is_default": True,
    },
    {
        "app_id": "waddles.community.forms.default",
        "name": "Forms (default)",
        "version": "1.0.0",
        "feature": "waddles.community.forms",
        "module": MODULE,
        "provider": "builtin",
        "surfaces": ("process", "action"),
        "permissions": ("community.forms:write",),
        "is_default": True,
    },
    {
        "app_id": "waddles.community.forums.default",
        "name": "Forums (default)",
        "version": "1.0.0",
        "feature": "waddles.community.forums",
        "module": MODULE,
        "provider": "builtin",
        "surfaces": ("process", "action"),
        "permissions": ("community.interaction:write",),
        "is_default": True,
    },
    {
        "app_id": "waddles.community.interactions.default",
        "name": "Interactions (default)",
        "version": "1.0.0",
        "feature": "waddles.community.interactions",
        "module": MODULE,
        "provider": "builtin",
        "surfaces": ("process", "action"),
        "permissions": ("community.interaction:manage_channels",),
        "is_default": True,
    },
    {
        "app_id": "waddles.community.activity.default",
        "name": "Activity (default)",
        "version": "1.0.0",
        "feature": "waddles.community.activity",
        "module": MODULE,
        "provider": "builtin",
        "surfaces": ("ingest", "process"),
        "permissions": ("community.activity:read",),
        "is_default": True,
    },
    {
        "app_id": "waddles.community.loyalty.default",
        "name": "Loyalty (default)",
        "version": "1.0.0",
        "feature": "waddles.community.loyalty",
        "module": MODULE,
        "provider": "builtin",
        "surfaces": ("process", "action"),
        "permissions": ("community.loyalty:write",),
        "is_default": True,
    },
    {
        "app_id": "waddles.community.inventory.default",
        "name": "Inventory (default)",
        "version": "1.0.0",
        "feature": "waddles.community.inventory",
        "module": MODULE,
        "provider": "builtin",
        "surfaces": ("process", "action"),
        "permissions": ("community.inventory:write",),
        "is_default": True,
    },
    {
        "app_id": "waddles.community.raffles.default",
        "name": "Raffles (default)",
        "version": "1.0.0",
        "feature": "waddles.community.raffles",
        "module": MODULE,
        "provider": "builtin",
        "surfaces": ("process", "action"),
        "permissions": ("community.raffle:write",),
        "is_default": True,
    },
    {
        "app_id": "waddles.community.virtual_stages.default",
        "name": "Virtual Stages (default)",
        "version": "1.0.0",
        "feature": "waddles.community.virtual_stages",
        "module": MODULE,
        "provider": "builtin",
        "surfaces": ("presentation",),
        "permissions": ("community.virtual_stages:write",),
        "is_default": True,
    },
)


def build_contracts() -> Tuple[FeatureContract, ...]:
    """Parse and validate the eleven Community Feature contracts, without registering them."""
    return tuple(parse_feature_contract(raw) for raw in _FEATURE_DEFS)


def build_default_apps() -> Tuple[AppManifest, ...]:
    """Parse and validate the eleven Community default App manifests, without registering them."""
    return tuple(parse_manifest(raw) for raw in _DEFAULT_APP_DEFS)


def register_all(
    *,
    feature_registry: Optional[FeatureRegistry] = None,
    app_registry: Optional[AppRegistry] = None,
) -> Tuple[Tuple[FeatureContract, ...], Tuple[AppManifest, ...]]:
    """
    Parse, validate and register all eleven Community Features and their
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
