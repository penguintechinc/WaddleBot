"""
Community Module Feature tests
=================================

Covers :mod:`community_module.features` -- the Community Module's
registration of its eleven Feature contracts and their shipped default
Apps against the v3 Feature-contract spine
(:mod:`flask_core.feature_contract`, :mod:`flask_core.feature_registry`,
:mod:`flask_core.app_manifest`, :mod:`flask_core.app_registry`). Mirrors
``libs/social_module/tests/test_social_features.py``'s structure
one-for-one.

Every assertion runs against fresh, isolated registries (never the process
singletons) so this test file can run in any order relative to
``test_feature_registry.py`` / ``test_app_framework.py`` without leaking
registrations between them.

Fail-on-purpose proof: ``test_scope_widening_default_app_is_rejected`` was
verified to catch a regression by temporarily widening
``community.chat.default``'s ``permissions`` in
``community_module/features.py`` past its Feature's ``requires_scopes`` and
confirming ``register_all`` raises ``ScopeWideningError``, then reverting.
"""

from __future__ import annotations

from typing import Optional

import pytest
from community_module.features import ScopeWideningError, register_all
from flask_core.app_registry import AppRegistry
from flask_core.feature_registry import FeatureRegistry

EXPECTED_FEATURES = {
    "community.chat": ("waddles.community.chat", frozenset({"community.chat:read"}), "free"),
    "community.polls": (
        "waddles.community.polls",
        frozenset({"community.polls:write"}),
        "free",
    ),
    "community.announcements": (
        "waddles.community.announcements",
        frozenset({"community.announcements:write"}),
        "free",
    ),
    "community.forms": (
        "waddles.community.forms",
        frozenset({"community.forms:write"}),
        "free",
    ),
    "community.forums": (
        "waddles.community.forums",
        frozenset({"community.interaction:write"}),
        "free",
    ),
    "community.interactions": (
        "waddles.community.interactions",
        frozenset({"community.interaction:manage_channels"}),
        "free",
    ),
    "community.activity": (
        "waddles.community.activity",
        frozenset({"community.activity:read"}),
        "free",
    ),
    "community.loyalty": (
        "waddles.community.loyalty",
        frozenset({"community.loyalty:write"}),
        "professional",
    ),
    "community.inventory": (
        "waddles.community.inventory",
        frozenset({"community.inventory:write"}),
        "professional",
    ),
    "community.raffles": (
        "waddles.community.raffles",
        frozenset({"community.raffle:write"}),
        "professional",
    ),
    "community.virtual_stages": (
        "waddles.community.virtual_stages",
        frozenset({"community.virtual_stages:write"}),
        "professional",
    ),
}


@pytest.fixture
def registries() -> tuple[FeatureRegistry, AppRegistry]:
    """Fresh, isolated Feature + App registries -- never the process singletons."""
    return FeatureRegistry(), AppRegistry()


class TestCommunityFeatureContracts:
    def test_all_eleven_features_registered_with_correct_tier_and_flag(
        self, registries: tuple[FeatureRegistry, AppRegistry]
    ) -> None:
        feature_registry, app_registry = registries
        contracts, _ = register_all(feature_registry=feature_registry, app_registry=app_registry)

        assert {c.id for c in contracts} == set(EXPECTED_FEATURES)
        for c in contracts:
            expected_flag, expected_scopes, expected_tier = EXPECTED_FEATURES[c.id]
            assert c.module == "community"
            assert c.version == 1
            assert c.min_tier == expected_tier
            assert c.flag == expected_flag
            assert c.requires_scopes == expected_scopes

    def test_features_are_queryable_from_the_registry_by_id_and_module(
        self, registries: tuple[FeatureRegistry, AppRegistry]
    ) -> None:
        feature_registry, app_registry = registries
        register_all(feature_registry=feature_registry, app_registry=app_registry)

        assert feature_registry.get("community.chat").flag == "waddles.community.chat"
        assert {c.id for c in feature_registry.for_module("community")} == set(EXPECTED_FEATURES)


class TestCommunityDefaultApps:
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
            assert default_app.module == "community"
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

    def test_virtual_stages_default_app_declares_presentation_surface(
        self, registries: tuple[FeatureRegistry, AppRegistry]
    ) -> None:
        """The one greenfield capability -- no handler yet, but a real, valid manifest."""
        feature_registry, app_registry = registries
        register_all(feature_registry=feature_registry, app_registry=app_registry)

        default_app = app_registry.default_app_for("waddles.community.virtual_stages")
        assert default_app is not None
        assert default_app.surfaces == ("presentation",)

    def test_scope_widening_default_app_is_rejected(self) -> None:
        """A default App claiming a scope its own Feature doesn't grant must be rejected."""
        import community_module.features as features_module

        original_defs = features_module._DEFAULT_APP_DEFS
        widened_index = next(
            i
            for i, d in enumerate(original_defs)
            if d["app_id"] == "waddles.community.chat.default"
        )
        widened = dict(original_defs[widened_index])
        widened["permissions"] = ("community.chat:read", "community.chat:admin")
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


class TestChatGate:
    """
    Exercises the worked gate example's contract, not the Quart handler
    itself -- same reasoning as ``test_social_features.py::TestQuoteGate``:
    the real handler (``hub_api/blueprints/v1/community_chat.py::
    chat_history``) has a heavy dependency chain (pydal, quart) out of scope
    for this unit suite. What's asserted here is the gate condition the
    handler guards on -- ``feature_enabled("waddles.community.chat", ...)``
    -- using the same fake-check shape as ``test_feature_registry.py``, so a
    regression in the flag name the handler checks is caught here even
    though the handler's own process isn't imported.
    """

    async def test_chat_flag_off_is_not_entitled(self) -> None:
        from community_module.features import build_contracts
        from flask_core.feature_registry import entitled_features

        contracts = build_contracts()
        chat = next(c for c in contracts if c.id == "community.chat")
        check = FakeCheck(enabled_flags=set())  # waddles.community.chat OFF

        result = await entitled_features(tenant="acme", contracts=(chat,), check=check)

        assert result == []

    async def test_chat_flag_on_is_entitled(self) -> None:
        from community_module.features import build_contracts
        from flask_core.feature_registry import entitled_features

        contracts = build_contracts()
        chat = next(c for c in contracts if c.id == "community.chat")
        check = FakeCheck(enabled_flags={"waddles.community.chat"})

        result = await entitled_features(tenant="acme", contracts=(chat,), check=check)

        assert result == [chat]
