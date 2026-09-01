"""
Social Module -- Feature contracts + default App bindings
==========================================================

Declares the Social Module's nine Feature contracts and registers each
one's shipped default App, per docs/plans/2026-08-26-v3-scbm-apps-design.md
``Features`` / ``Apps`` / migration phase P1 ("convert 2-3 Bot units as
proof") -- Social is the second Module converted onto the same spine, one
Feature per existing capability (community_module, presence, alias, quote,
module_rtc, browser_source_core, plus the already-shipped social.welcome).
All are Free tier per the license catalog except ``social.welcome_ai``,
which is Enterprise.

| Feature id                | Flag                             | Scopes                          | Tier       |
|----------------------------|-----------------------------------|-----------------------------------|------------|
| ``social.polls``           | ``waddles.social.polls``           | ``social.poll:write``             | free       |
| ``social.presence``        | ``waddles.social.presence``        | ``social.presence:read``          | free       |
| ``social.communities``     | ``waddles.social.communities``     | ``social.community:write``        | free       |
| ``social.alias``           | ``waddles.social.alias``           | ``social.alias:write``            | free       |
| ``social.quote``           | ``waddles.social.quote``           | ``social.quote:write``            | free       |
| ``social.browser_source``  | ``waddles.social.browser_source``  | ``social.browser_source:read``    | free       |
| ``social.rtc``              | ``waddles.social.rtc``              | ``social.rtc:write``               | free       |
| ``social.welcome``         | ``waddles.social.welcome``         | ``social.welcome:write``          | free       |
| ``social.welcome_ai``      | ``waddles.social.welcome_ai``      | ``social.welcome:write``          | enterprise |

``social.welcome`` is the first-message-recognition Feature -- the always-on
base capability already shipped in
``action/interactive/welcome_interaction_module/services/
welcome_service.py`` (``check_and_welcome``/``try_mark_welcomed``);
``social.welcome_ai`` is the separate, Enterprise-tier, flag-gated
AI-personalization layer on top of it (``WELCOME_AI_FLAG_KEY`` ==
``waddles.social.welcome_ai`` in that module's ``config.py``). Both share
the same ``requires_scopes`` (``social.welcome:write``) but are distinct
contracts with distinct flags -- this module now owns both.

Each Feature gets exactly one shipped default App (``provider="builtin"``,
``is_default=True``) -- the "permanent fallback" the design doc's ``Apps ->
Binding resolution`` describes as un-swappable cluster-wide. Social's actual
handler code still lives in its pre-v3 locations (``core/community_module``,
``core/module_rtc``, ``core/browser_source_core_module``, ``libs/presence``,
``action/interactive/{alias,quote,welcome}_interaction_module``); this
module is the Feature-contract registration point those handlers gate
against, not a rewrite of them. See
``action/interactive/quote_interaction_module/app.py``'s ``add_quote`` for
the one worked gate example wired end-to-end; the other Free-tier Features
follow the identical one-line guard. ``social.welcome_ai``'s gate already
exists in ``action/interactive/welcome_interaction_module/services/
welcome_service.py`` and is not re-gated here (``social.welcome`` itself has
no separate flag check -- it is the always-on base path); only their
contracts and default Apps are registered.

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

MODULE = "social"


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
        "id": "social.polls",
        "version": 1,
        "module": MODULE,
        "requires_scopes": frozenset({"social.poll:write"}),
        "min_tier": "free",
        "flag": "waddles.social.polls",
    },
    {
        "id": "social.presence",
        "version": 1,
        "module": MODULE,
        "requires_scopes": frozenset({"social.presence:read"}),
        "min_tier": "free",
        "flag": "waddles.social.presence",
    },
    {
        "id": "social.communities",
        "version": 1,
        "module": MODULE,
        "requires_scopes": frozenset({"social.community:write"}),
        "min_tier": "free",
        "flag": "waddles.social.communities",
    },
    {
        "id": "social.alias",
        "version": 1,
        "module": MODULE,
        "requires_scopes": frozenset({"social.alias:write"}),
        "min_tier": "free",
        "flag": "waddles.social.alias",
    },
    {
        "id": "social.quote",
        "version": 1,
        "module": MODULE,
        "requires_scopes": frozenset({"social.quote:write"}),
        "min_tier": "free",
        "flag": "waddles.social.quote",
    },
    {
        "id": "social.browser_source",
        "version": 1,
        "module": MODULE,
        "requires_scopes": frozenset({"social.browser_source:read"}),
        "min_tier": "free",
        "flag": "waddles.social.browser_source",
    },
    {
        "id": "social.rtc",
        "version": 1,
        "module": MODULE,
        "requires_scopes": frozenset({"social.rtc:write"}),
        "min_tier": "free",
        "flag": "waddles.social.rtc",
    },
    {
        "id": "social.welcome",
        "version": 1,
        "module": MODULE,
        "requires_scopes": frozenset({"social.welcome:write"}),
        "min_tier": "free",
        "flag": "waddles.social.welcome",
    },
    {
        "id": "social.welcome_ai",
        "version": 1,
        "module": MODULE,
        "requires_scopes": frozenset({"social.welcome:write"}),
        "min_tier": "enterprise",
        "flag": "waddles.social.welcome_ai",
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
        "app_id": "waddles.social.polls.default",
        "name": "Polls (default)",
        "version": "1.0.0",
        "feature": "waddles.social.polls",
        "module": MODULE,
        "provider": "builtin",
        "surfaces": ("process", "action"),
        "permissions": ("social.poll:write",),
        "is_default": True,
    },
    {
        "app_id": "waddles.social.presence.default",
        "name": "Presence (default)",
        "version": "1.0.0",
        "feature": "waddles.social.presence",
        "module": MODULE,
        "provider": "builtin",
        "surfaces": ("ingest",),
        "permissions": ("social.presence:read",),
        "is_default": True,
    },
    {
        "app_id": "waddles.social.communities.default",
        "name": "Communities (default)",
        "version": "1.0.0",
        "feature": "waddles.social.communities",
        "module": MODULE,
        "provider": "builtin",
        "surfaces": ("process", "action"),
        "permissions": ("social.community:write",),
        "is_default": True,
    },
    {
        "app_id": "waddles.social.alias.default",
        "name": "Alias (default)",
        "version": "1.0.0",
        "feature": "waddles.social.alias",
        "module": MODULE,
        "provider": "builtin",
        "surfaces": ("process", "action"),
        "permissions": ("social.alias:write",),
        "is_default": True,
    },
    {
        "app_id": "waddles.social.quote.default",
        "name": "Quote (default)",
        "version": "1.0.0",
        "feature": "waddles.social.quote",
        "module": MODULE,
        "provider": "builtin",
        "surfaces": ("process", "action"),
        "permissions": ("social.quote:write",),
        "is_default": True,
    },
    {
        "app_id": "waddles.social.browser_source.default",
        "name": "Browser Source (default)",
        "version": "1.0.0",
        "feature": "waddles.social.browser_source",
        "module": MODULE,
        "provider": "builtin",
        "surfaces": ("action",),
        "permissions": ("social.browser_source:read",),
        "is_default": True,
    },
    {
        "app_id": "waddles.social.rtc.default",
        "name": "RTC (default)",
        "version": "1.0.0",
        "feature": "waddles.social.rtc",
        "module": MODULE,
        "provider": "builtin",
        "surfaces": ("ingest", "process"),
        "permissions": ("social.rtc:write",),
        "is_default": True,
    },
    {
        "app_id": "waddles.social.welcome.default",
        "name": "Welcome (default)",
        "version": "1.0.0",
        "feature": "waddles.social.welcome",
        "module": MODULE,
        "provider": "builtin",
        "surfaces": ("process", "action"),
        "permissions": ("social.welcome:write",),
        "is_default": True,
    },
    {
        "app_id": "waddles.social.welcome_ai.default",
        "name": "Welcome AI (default)",
        "version": "1.0.0",
        "feature": "waddles.social.welcome_ai",
        "module": MODULE,
        "provider": "builtin",
        "surfaces": ("process", "action"),
        "permissions": ("social.welcome:write",),
        "is_default": True,
    },
)


def build_contracts() -> Tuple[FeatureContract, ...]:
    """Parse and validate the nine Social Feature contracts, without registering them."""
    return tuple(parse_feature_contract(raw) for raw in _FEATURE_DEFS)


def build_default_apps() -> Tuple[AppManifest, ...]:
    """Parse and validate the nine Social default App manifests, without registering them."""
    return tuple(parse_manifest(raw) for raw in _DEFAULT_APP_DEFS)


def register_all(
    *,
    feature_registry: Optional[FeatureRegistry] = None,
    app_registry: Optional[AppRegistry] = None,
) -> Tuple[Tuple[FeatureContract, ...], Tuple[AppManifest, ...]]:
    """
    Parse, validate and register all nine Social Features and their
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
