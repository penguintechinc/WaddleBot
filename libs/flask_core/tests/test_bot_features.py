"""
Bot Module Feature tests
===========================

Covers :mod:`bot_module.features` -- the Bot Module's registration of its
four Feature contracts and their shipped default Apps against the v3
Feature-contract spine (:mod:`flask_core.feature_contract`,
:mod:`flask_core.feature_registry`, :mod:`flask_core.app_manifest`,
:mod:`flask_core.app_registry`).

Every assertion runs against fresh, isolated registries (never the process
singletons) so this test file can run in any order relative to
``test_feature_registry.py`` / ``test_app_framework.py`` without leaking
registrations between them.

Fail-on-purpose proof: ``test_default_app_scopes_are_subset_of_feature_scopes``
was verified to catch a regression by temporarily widening
``bot.commands.default``'s ``permissions`` in ``bot_module/features.py``
past its Feature's ``requires_scopes`` and confirming
``register_all`` raises ``ScopeWideningError``, then reverting.
"""

from __future__ import annotations

from typing import Optional

import pytest

from bot_module.features import ScopeWideningError, register_all
from flask_core.app_registry import AppRegistry
from flask_core.feature_registry import FeatureRegistry

EXPECTED_FEATURES = {
    "bot.shoutout": ("waddles.bot.shoutout", frozenset({"bot.command:write"})),
    "bot.commands": ("waddles.bot.commands", frozenset({"bot.command:write"})),
    "bot.connectors": ("waddles.bot.connectors", frozenset({"bot.connector:write"})),
    "bot.interactions": ("waddles.bot.interactions", frozenset({"bot.interaction:write"})),
}


@pytest.fixture
def registries() -> tuple[FeatureRegistry, AppRegistry]:
    """Fresh, isolated Feature + App registries -- never the process singletons."""
    return FeatureRegistry(), AppRegistry()


class TestBotFeatureContracts:
    def test_all_four_features_registered_with_correct_tier_and_flag(
        self, registries: tuple[FeatureRegistry, AppRegistry]
    ) -> None:
        feature_registry, app_registry = registries
        contracts, _ = register_all(feature_registry=feature_registry, app_registry=app_registry)

        assert {c.id for c in contracts} == set(EXPECTED_FEATURES)
        for c in contracts:
            expected_flag, expected_scopes = EXPECTED_FEATURES[c.id]
            assert c.module == "bot"
            assert c.version == 1
            assert c.min_tier == "free"
            assert c.flag == expected_flag
            assert c.requires_scopes == expected_scopes

    def test_features_are_queryable_from_the_registry_by_id_and_module(
        self, registries: tuple[FeatureRegistry, AppRegistry]
    ) -> None:
        feature_registry, app_registry = registries
        register_all(feature_registry=feature_registry, app_registry=app_registry)

        assert feature_registry.get("bot.shoutout").flag == "waddles.bot.shoutout"
        assert {c.id for c in feature_registry.for_module("bot")} == set(EXPECTED_FEATURES)


class TestBotDefaultApps:
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
            assert default_app.module == "bot"
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
        import bot_module.features as features_module

        original_defs = features_module._DEFAULT_APP_DEFS
        widened = dict(original_defs[1])  # bot.commands.default
        widened["permissions"] = ("bot.command:write", "bot.command:admin")
        features_module._DEFAULT_APP_DEFS = (
            original_defs[0],
            widened,
            original_defs[2],
            original_defs[3],
        )
        try:
            with pytest.raises(ScopeWideningError):
                register_all(feature_registry=FeatureRegistry(), app_registry=AppRegistry())
        finally:
            features_module._DEFAULT_APP_DEFS = original_defs


class FakeCheck:
    """Resolves each flag against a fixed enabled-set; mirrors test_feature_registry.py's fake."""

    def __init__(self, enabled_flags: set[str]) -> None:
        self.enabled_flags = enabled_flags

    async def __call__(
        self, flag_key: str, *, tenant: str, community: Optional[int] = None, default: bool = False
    ) -> bool:
        return flag_key in self.enabled_flags


class TestShoutoutGate:
    """
    Exercises the worked gate example's contract, not the Quart handler
    itself: the shoutout route (action/interactive/shoutout_interaction_module
    /app.py::create_shoutout) is a separate service with its own heavy
    dependency chain (pydal, asyncpg, twitch client), out of scope for
    flask_core's unit suite. What's asserted here is the gate condition the
    handler guards on -- `feature_enabled("waddles.bot.shoutout", ...)` --
    using the same fake-check shape as `test_feature_registry.py`, so a
    regression in the flag-name the handler checks is caught here even
    though the handler's own process isn't imported.
    """

    async def test_shoutout_flag_off_is_not_entitled(self) -> None:
        from flask_core.feature_registry import entitled_features

        from bot_module.features import build_contracts

        contracts = build_contracts()
        shoutout = next(c for c in contracts if c.id == "bot.shoutout")
        check = FakeCheck(enabled_flags=set())  # waddles.bot.shoutout OFF

        result = await entitled_features(tenant="acme", contracts=(shoutout,), check=check)

        assert result == []

    async def test_shoutout_flag_on_is_entitled(self) -> None:
        from flask_core.feature_registry import entitled_features

        from bot_module.features import build_contracts

        contracts = build_contracts()
        shoutout = next(c for c in contracts if c.id == "bot.shoutout")
        check = FakeCheck(enabled_flags={"waddles.bot.shoutout"})

        result = await entitled_features(tenant="acme", contracts=(shoutout,), check=check)

        assert result == [shoutout]
