"""
Customer Module -- Feature contracts + default App bindings
==========================================================

Declares the Customer Module's five Feature contracts and registers each
one's shipped default App, per docs/plans/2026-08-26-v3-scbm-apps-design.md
``Features`` / ``Apps``. All five are Free tier per the merged license
catalog (v3.0.0 core CRM).

| Feature id                  | Flag                              | Scopes                          |
|-------------------------------|-------------------------------------|------------------------------------|
| ``customer.accounts``       | ``waddles.customer.accounts``       | ``customer.account:write``       |
| ``customer.contacts``       | ``waddles.customer.contacts``       | ``customer.contact:write``       |
| ``customer.opportunities``  | ``waddles.customer.opportunities``  | ``customer.opportunity:write``   |
| ``customer.pipelines``      | ``waddles.customer.pipelines``      | ``customer.pipeline:write``      |
| ``customer.cases``          | ``waddles.customer.cases``          | ``customer.case:write``          |

Each Feature gets exactly one shipped default App (``provider="builtin"``,
``is_default=True``) -- the "permanent fallback" the design doc's ``Apps ->
Binding resolution`` describes as un-swappable cluster-wide. Customer is
~0% pre-v3 code (100% green-field per the ``Modules`` table), so unlike Bot
this module also owns its own MVP handler skeleton
(:mod:`customer_module.app`) rather than gating pre-existing code -- see
that module's ``create_account`` for the one worked gate example wired
end-to-end; the other four Features follow the identical one-line guard
once their handlers exist. This is registration + MVP skeleton only, not
the full CRM (a multi-year effort per the design doc).

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

MODULE = "customer"


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
        "id": "customer.accounts",
        "version": 1,
        "module": MODULE,
        "requires_scopes": frozenset({"customer.account:write"}),
        "min_tier": "free",
        "flag": "waddles.customer.accounts",
    },
    {
        "id": "customer.contacts",
        "version": 1,
        "module": MODULE,
        "requires_scopes": frozenset({"customer.contact:write"}),
        "min_tier": "free",
        "flag": "waddles.customer.contacts",
    },
    {
        "id": "customer.opportunities",
        "version": 1,
        "module": MODULE,
        "requires_scopes": frozenset({"customer.opportunity:write"}),
        "min_tier": "free",
        "flag": "waddles.customer.opportunities",
    },
    {
        "id": "customer.pipelines",
        "version": 1,
        "module": MODULE,
        "requires_scopes": frozenset({"customer.pipeline:write"}),
        "min_tier": "free",
        "flag": "waddles.customer.pipelines",
    },
    {
        "id": "customer.cases",
        "version": 1,
        "module": MODULE,
        "requires_scopes": frozenset({"customer.case:write"}),
        "min_tier": "free",
        "flag": "waddles.customer.cases",
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
        "app_id": "waddles.customer.accounts.default",
        "name": "Accounts (default)",
        "version": "1.0.0",
        "feature": "waddles.customer.accounts",
        "module": MODULE,
        "provider": "builtin",
        "surfaces": ("action",),
        "permissions": ("customer.account:write",),
        "is_default": True,
    },
    {
        "app_id": "waddles.customer.contacts.default",
        "name": "Contacts (default)",
        "version": "1.0.0",
        "feature": "waddles.customer.contacts",
        "module": MODULE,
        "provider": "builtin",
        "surfaces": ("action",),
        "permissions": ("customer.contact:write",),
        "is_default": True,
    },
    {
        "app_id": "waddles.customer.opportunities.default",
        "name": "Opportunities (default)",
        "version": "1.0.0",
        "feature": "waddles.customer.opportunities",
        "module": MODULE,
        "provider": "builtin",
        "surfaces": ("action",),
        "permissions": ("customer.opportunity:write",),
        "is_default": True,
    },
    {
        "app_id": "waddles.customer.pipelines.default",
        "name": "Pipelines (default)",
        "version": "1.0.0",
        "feature": "waddles.customer.pipelines",
        "module": MODULE,
        "provider": "builtin",
        "surfaces": ("action",),
        "permissions": ("customer.pipeline:write",),
        "is_default": True,
    },
    {
        "app_id": "waddles.customer.cases.default",
        "name": "Cases (default)",
        "version": "1.0.0",
        "feature": "waddles.customer.cases",
        "module": MODULE,
        "provider": "builtin",
        "surfaces": ("action",),
        "permissions": ("customer.case:write",),
        "is_default": True,
    },
)


def build_contracts() -> Tuple[FeatureContract, ...]:
    """Parse and validate the five Customer Feature contracts, without registering them."""
    return tuple(parse_feature_contract(raw) for raw in _FEATURE_DEFS)


def build_default_apps() -> Tuple[AppManifest, ...]:
    """Parse and validate the five Customer default App manifests, without registering them."""
    return tuple(parse_manifest(raw) for raw in _DEFAULT_APP_DEFS)


def register_all(
    *,
    feature_registry: Optional[FeatureRegistry] = None,
    app_registry: Optional[AppRegistry] = None,
) -> Tuple[Tuple[FeatureContract, ...], Tuple[AppManifest, ...]]:
    """
    Parse, validate and register all five Customer Features and their
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
