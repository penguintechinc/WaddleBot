"""
Social Module Feature tests
==============================

Covers :mod:`social_module.features` -- the Social Module's registration of
its eight Feature contracts and their shipped default Apps against the v3
Feature-contract spine (:mod:`flask_core.feature_contract`,
:mod:`flask_core.feature_registry`, :mod:`flask_core.app_manifest`,
:mod:`flask_core.app_registry`). Mirrors
``libs/flask_core/tests/test_bot_features.py``'s structure one-for-one.

Every assertion runs against fresh, isolated registries (never the process
singletons) so this test file can run in any order relative to
``test_feature_registry.py`` / ``test_app_framework.py`` without leaking
registrations between them.

Fail-on-purpose proof: ``test_scope_widening_default_app_is_rejected``
was verified to catch a regression by temporarily widening
``social.quote.default``'s ``permissions`` in ``social_module/features.py``
past its Feature's ``requires_scopes`` and confirming ``register_all``
raises ``ScopeWideningError``, then reverting.
"""

from __future__ import annotations

from typing import Optional

import pytest

from flask_core.app_registry import AppRegistry
from flask_core.feature_registry import FeatureRegistry
from social_module.features import ScopeWideningError, register_all

EXPECTED_FEATURES = {
    "social.polls": ("waddles.social.polls", frozenset({"social.poll:write"}), "free"),
    "social.presence": (
        "waddles.social.presence",
        frozenset({"social.presence:read"}),
        "free",
    ),
    "social.communities": (
        "waddles.social.communities",
        frozenset({"social.community:write"}),
        "free",
    ),
    "social.alias": ("waddles.social.alias", frozenset({"social.alias:write"}), "free"),
    "social.quote": ("waddles.social.quote", frozenset({"social.quote:write"}), "free"),
    "social.browser_source": (
        "waddles.social.browser_source",
        frozenset({"social.browser_source:read"}),
        "free",
    ),
    "social.rtc": ("waddles.social.rtc", frozenset({"social.rtc:write"}), "free"),
    "social.welcome_ai": (
        "waddles.social.welcome_ai",
        frozenset({"social.welcome:write"}),
        "enterprise",
    ),
}


@pytest.fixture
def registries() -> tuple[FeatureRegistry, AppRegistry]:
    """Fresh, isolated Feature + App registries -- never the process singletons."""
    return FeatureRegistry(), AppRegistry()


class TestSocialFeatureContracts:
    def test_all_eight_features_registered_with_correct_tier_and_flag(
        self, registries: tuple[FeatureRegistry, AppRegistry]
    ) -> None:
        feature_registry, app_registry = registries
        contracts, _ = register_all(feature_registry=feature_registry, app_registry=app_registry)

        assert {c.id for c in contracts} == set(EXPECTED_FEATURES)
        for c in contracts:
            expected_flag, expected_scopes, expected_tier = EXPECTED_FEATURES[c.id]
            assert c.module == "social"
            assert c.version == 1
            assert c.min_tier == expected_tier
            assert c.flag == expected_flag
            assert c.requires_scopes == expected_scopes

    def test_features_are_queryable_from_the_registry_by_id_and_module(
        self, registries: tuple[FeatureRegistry, AppRegistry]
    ) -> None:
        feature_registry, app_registry = registries
        register_all(feature_registry=feature_registry, app_registry=app_registry)

        assert feature_registry.get("social.quote").flag == "waddles.social.quote"
        assert {c.id for c in feature_registry.for_module("social")} == set(EXPECTED_FEATURES)


class TestSocialDefaultApps:
    def test_every_feature_has_exactly_one_default_app(
        self, registries: tuple[FeatureRegistry, AppRegistry]
    ) -> None:
        feature_registry, app_registry = registries
        register_all(feature_registry=feature_registry, app_registry=app_registry)

        for feature_id, (flag, _, _) in EXPECTED_FEATURES.items():
            default_app = app_registry.default_app_for(flag)
            assert default_app is not None, f"no default app for {feature_id}"
            assert default_app.is_default is True
            assert default_app.provider == "builtin"
            assert default_app.module == "social"
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
        import social_module.features as features_module

        original_defs = features_module._DEFAULT_APP_DEFS
        widened_index = next(
            i for i, d in enumerate(original_defs) if d["app_id"] == "waddles.social.quote.default"
        )
        widened = dict(original_defs[widened_index])
        widened["permissions"] = ("social.quote:write", "social.quote:admin")
        features_module._DEFAULT_APP_DEFS = (
            original_defs[:widened_index] + (widened,) + original_defs[widened_index + 1 :]
        )
        try:
            with pytest.raises(ScopeWideningError):
                register_all(feature_registry=FeatureRegistry(), app_registry=AppRegistry())
        finally:
            features_module._DEFAULT_APP_DEFS = original_defs


class FakeCheck:
    """Resolves each flag against a fixed enabled-set; mirrors test_bot_features.py's fake."""

    def __init__(self, enabled_flags: set[str]) -> None:
        self.enabled_flags = enabled_flags

    async def __call__(
        self, flag_key: str, *, tenant: str, community: Optional[int] = None, default: bool = False
    ) -> bool:
        return flag_key in self.enabled_flags


class TestQuoteGate:
    """
    Exercises the worked gate example's contract, not the Quart handler
    itself: the quote route (action/interactive/quote_interaction_module
    /app.py::add_quote) is a separate service with its own heavy dependency
    chain (pydal, asyncpg), out of scope for this unit suite -- same
    reasoning as ``test_bot_features.py::TestShoutoutGate``. What's asserted
    here is the gate condition the handler guards on --
    ``feature_enabled("waddles.social.quote", ...)`` -- using the same
    fake-check shape as ``test_feature_registry.py``, so a regression in the
    flag name the handler checks is caught here even though the handler's
    own process isn't imported.
    """

    async def test_quote_flag_off_is_not_entitled(self) -> None:
        from flask_core.feature_registry import entitled_features

        from social_module.features import build_contracts

        contracts = build_contracts()
        quote = next(c for c in contracts if c.id == "social.quote")
        check = FakeCheck(enabled_flags=set())  # waddles.social.quote OFF

        result = await entitled_features(tenant="acme", contracts=(quote,), check=check)

        assert result == []

    async def test_quote_flag_on_is_entitled(self) -> None:
        from flask_core.feature_registry import entitled_features

        from social_module.features import build_contracts

        contracts = build_contracts()
        quote = next(c for c in contracts if c.id == "social.quote")
        check = FakeCheck(enabled_flags={"waddles.social.quote"})

        result = await entitled_features(tenant="acme", contracts=(quote,), check=check)

        assert result == [quote]
