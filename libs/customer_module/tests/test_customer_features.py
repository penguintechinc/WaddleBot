"""
Customer Module Feature tests
=================================

Covers :mod:`customer_module.features` -- the Customer Module's
registration of its five Feature contracts and their shipped default Apps
against the v3 Feature-contract spine (:mod:`flask_core.feature_contract`,
:mod:`flask_core.feature_registry`, :mod:`flask_core.app_manifest`,
:mod:`flask_core.app_registry`). Mirrors
``libs/flask_core/tests/test_bot_features.py``'s structure one-for-one.

Every assertion runs against fresh, isolated registries (never the process
singletons) so this test file can run in any order relative to
``test_feature_registry.py`` / ``test_app_framework.py`` without leaking
registrations between them.

Fail-on-purpose proof: ``test_scope_widening_default_app_is_rejected``
was verified to catch a regression by temporarily widening
``customer.contacts.default``'s ``permissions`` past its Feature's
``requires_scopes`` and confirming ``register_all`` raises
``ScopeWideningError``, then reverting -- see that test's body.
"""

from __future__ import annotations

import pytest
from customer_module.features import ScopeWideningError, register_all
from flask_core.app_registry import AppRegistry
from flask_core.feature_registry import FeatureRegistry

EXPECTED_FEATURES = {
    "customer.accounts": ("waddles.customer.accounts", frozenset({"customer.account:write"})),
    "customer.contacts": ("waddles.customer.contacts", frozenset({"customer.contact:write"})),
    "customer.opportunities": (
        "waddles.customer.opportunities",
        frozenset({"customer.opportunity:write"}),
    ),
    "customer.pipelines": ("waddles.customer.pipelines", frozenset({"customer.pipeline:write"})),
    "customer.cases": ("waddles.customer.cases", frozenset({"customer.case:write"})),
}


@pytest.fixture
def registries() -> tuple[FeatureRegistry, AppRegistry]:
    """Fresh, isolated Feature + App registries -- never the process singletons."""
    return FeatureRegistry(), AppRegistry()


class TestCustomerFeatureContracts:
    def test_all_five_features_registered_with_correct_tier_and_flag(
        self, registries: tuple[FeatureRegistry, AppRegistry]
    ) -> None:
        feature_registry, app_registry = registries
        contracts, _ = register_all(feature_registry=feature_registry, app_registry=app_registry)

        assert {c.id for c in contracts} == set(EXPECTED_FEATURES)
        for c in contracts:
            expected_flag, expected_scopes = EXPECTED_FEATURES[c.id]
            assert c.module == "customer"
            assert c.version == 1
            assert c.min_tier == "free"
            assert c.flag == expected_flag
            assert c.requires_scopes == expected_scopes

    def test_features_are_queryable_from_the_registry_by_id_and_module(
        self, registries: tuple[FeatureRegistry, AppRegistry]
    ) -> None:
        feature_registry, app_registry = registries
        register_all(feature_registry=feature_registry, app_registry=app_registry)

        assert feature_registry.get("customer.accounts").flag == "waddles.customer.accounts"
        assert {c.id for c in feature_registry.for_module("customer")} == set(EXPECTED_FEATURES)


class TestCustomerDefaultApps:
    def test_every_feature_has_exactly_one_default_app(
        self, registries: tuple[FeatureRegistry, AppRegistry]
    ) -> None:
        feature_registry, app_registry = registries
        register_all(feature_registry=feature_registry, app_registry=app_registry)

        for feature_id, (flag, _) in EXPECTED_FEATURES.items():
            default_app = app_registry.default_app_for(flag)
            assert default_app is not None, f"no default app for {feature_id}"
            assert default_app.is_default is True
            assert default_app.provider == "builtin"
            assert default_app.module == "customer"
            assert default_app.feature == flag

    def test_default_app_scopes_are_subset_of_feature_scopes(
        self, registries: tuple[FeatureRegistry, AppRegistry]
    ) -> None:
        feature_registry, app_registry = registries
        contracts, manifests = register_all(
            feature_registry=feature_registry, app_registry=app_registry
        )
        contracts_by_flag = {c.flag: c for c in contracts}

        for manifest in manifests:
            contract = contracts_by_flag[manifest.feature]
            assert set(manifest.permissions) <= contract.requires_scopes

    def test_scope_widening_default_app_is_rejected(self) -> None:
        """A default App claiming a scope its own Feature doesn't grant must be rejected."""
        import customer_module.features as features_module

        original_defs = features_module._DEFAULT_APP_DEFS
        widened = dict(original_defs[1])  # customer.contacts.default
        widened["permissions"] = ("customer.contact:write", "customer.contact:admin")
        features_module._DEFAULT_APP_DEFS = (
            original_defs[0],
            widened,
            original_defs[2],
            original_defs[3],
            original_defs[4],
        )
        try:
            with pytest.raises(ScopeWideningError):
                register_all(feature_registry=FeatureRegistry(), app_registry=AppRegistry())
        finally:
            features_module._DEFAULT_APP_DEFS = original_defs
