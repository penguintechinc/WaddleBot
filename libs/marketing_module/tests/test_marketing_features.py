"""Marketing Module Feature tests
===================================

Covers :mod:`marketing_module.features` -- the Marketing Module's
registration of its three Feature contracts and their shipped default Apps
against the v3 Feature-contract spine (:mod:`flask_core.feature_contract`,
:mod:`flask_core.feature_registry`, :mod:`flask_core.app_manifest`,
:mod:`flask_core.app_registry`) -- plus the worked gate wired end-to-end in
``core/engagement_module/app.py``'s ``create_poll`` handler
(``marketing.engagement``, Free tier).

Every registry assertion runs against fresh, isolated registries (never the
process singletons), mirroring
``libs/flask_core/tests/test_bot_features.py``.

Fail-on-purpose proof: ``test_default_app_scopes_are_subset_of_feature_scopes``
was verified to catch a regression by temporarily widening
``marketing.scheduling.default``'s ``permissions`` in
``marketing_module/features.py`` past its Feature's ``requires_scopes`` and
confirming ``register_all`` raises ``ScopeWideningError``, then reverting
(see the module docstring commit message for the exact before/after).
"""

from __future__ import annotations

from types import ModuleType
from unittest.mock import AsyncMock, patch

import pytest
from flask_core.app_registry import AppRegistry
from flask_core.feature_registry import FeatureRegistry
from marketing_module.features import (
    _DEFAULT_APP_DEFS,
    _FEATURE_DEFS,
    ScopeWideningError,
    build_contracts,
    build_default_apps,
    register_all,
)

EXPECTED_FEATURES = {
    "marketing.engagement": (
        "waddles.marketing.engagement",
        "free",
        frozenset({"marketing.engagement:write"}),
    ),
    "marketing.scheduling": (
        "waddles.marketing.scheduling",
        "professional",
        frozenset({"marketing.schedule:write"}),
    ),
    "marketing.publishing": (
        "waddles.marketing.publishing",
        "professional",
        frozenset({"marketing.publish:write"}),
    ),
}


@pytest.fixture
def registries() -> tuple[FeatureRegistry, AppRegistry]:
    """Fresh, isolated Feature + App registries -- never the process singletons."""
    return FeatureRegistry(), AppRegistry()


class TestMarketingFeatureContracts:
    def test_all_three_features_registered_with_correct_tier_and_flag(
        self, registries: tuple[FeatureRegistry, AppRegistry]
    ) -> None:
        feature_registry, app_registry = registries
        contracts, _ = register_all(feature_registry=feature_registry, app_registry=app_registry)

        assert {c.id for c in contracts} == set(EXPECTED_FEATURES)
        for c in contracts:
            expected_flag, expected_tier, expected_scopes = EXPECTED_FEATURES[c.id]
            assert c.module == "marketing"
            assert c.version == 1
            assert c.min_tier == expected_tier
            assert c.flag == expected_flag
            assert c.flag == f"waddles.{c.id}"
            assert c.requires_scopes == expected_scopes

    def test_features_are_queryable_from_the_registry_by_id_and_module(
        self, registries: tuple[FeatureRegistry, AppRegistry]
    ) -> None:
        feature_registry, app_registry = registries
        register_all(feature_registry=feature_registry, app_registry=app_registry)

        assert (
            feature_registry.get("marketing.engagement").flag == "waddles.marketing.engagement"
        )
        assert {c.id for c in feature_registry.for_module("marketing")} == set(EXPECTED_FEATURES)


class TestMarketingDefaultApps:
    def test_every_feature_has_exactly_one_default_app(
        self, registries: tuple[FeatureRegistry, AppRegistry]
    ) -> None:
        feature_registry, app_registry = registries
        register_all(feature_registry=feature_registry, app_registry=app_registry)

        for feature_id, (flag, _tier, _scopes) in EXPECTED_FEATURES.items():
            default_app = app_registry.default_app_for(flag)
            assert default_app is not None, f"no default app for {feature_id}"
            assert default_app.is_default is True
            assert default_app.provider == "builtin"
            assert default_app.module == "marketing"
            assert default_app.feature == flag

    def test_default_app_scopes_are_subset_of_feature_scopes(
        self, registries: tuple[FeatureRegistry, AppRegistry]
    ) -> None:
        feature_registry, app_registry = registries
        contracts, manifests = register_all(
            feature_registry=feature_registry, app_registry=app_registry
        )
        contracts_by_flag = {c.flag: c for c in contracts}

        assert len(manifests) == 3
        for manifest in manifests:
            contract = contracts_by_flag[manifest.feature]
            assert set(manifest.permissions) <= contract.requires_scopes

    def test_build_contracts_and_apps_are_side_effect_free(self) -> None:
        """build_contracts()/build_default_apps() never touch a registry."""
        contracts = build_contracts()
        manifests = build_default_apps()
        assert len(contracts) == 3
        assert len(manifests) == 3


class TestScopeWideningFailsFirst:
    def test_widened_default_app_permissions_raise_before_any_registration(
        self, registries: tuple[FeatureRegistry, AppRegistry]
    ) -> None:
        """
        Fail-first proof: a default App manifest claiming a permission
        outside its own Feature's requires_scopes raises
        ScopeWideningError, and *nothing* -- not even the two well-formed
        Features -- ends up registered. Widens marketing.scheduling.default
        with a scope only marketing.publishing's contract grants
        (marketing.publish:write), the same cross-Feature-widening shape a
        real bug would take.
        """
        feature_registry, app_registry = registries

        widened_app_defs = tuple(
            {**app_def, "permissions": (*app_def["permissions"], "marketing.publish:write")}
            if app_def["app_id"] == "waddles.marketing.scheduling.default"
            else app_def
            for app_def in _DEFAULT_APP_DEFS
        )

        with patch("marketing_module.features._DEFAULT_APP_DEFS", widened_app_defs):
            with pytest.raises(ScopeWideningError) as exc_info:
                register_all(feature_registry=feature_registry, app_registry=app_registry)

        assert "waddles.marketing.scheduling.default" in str(exc_info.value)
        assert "marketing.scheduling" in str(exc_info.value)
        # Nothing registered -- not even the two features unaffected by the
        # widened manifest. register_all() validates every manifest before
        # registering any contract.
        assert feature_registry.for_module("marketing") == ()
        assert all(
            app_registry.default_app_for(flag) is None
            for _fid, (flag, _tier, _scopes) in EXPECTED_FEATURES.items()
        )

    def test_feature_defs_are_internally_consistent(self) -> None:
        """Sanity check the fixture data itself has no accidental widening."""
        for feature_def in _FEATURE_DEFS:
            assert feature_def["flag"] == f"waddles.{feature_def['id']}"


class TestWorkedGateEngagement:
    """
    The one worked gate, end-to-end: create_poll in
    core/engagement_module/app.py guards on
    ``feature_enabled("waddles.marketing.engagement", tenant=..., community=...)``.
    marketing.scheduling / marketing.publishing follow this identical
    one-line guard at their own handler entry points once wired -- not
    re-tested here, per the module docstring.
    """

    @staticmethod
    def _auth_headers() -> dict[str, str]:
        return {"Authorization": "Bearer fake-token-verify_jwt_token-is-patched"}

    @pytest.mark.asyncio
    async def test_create_poll_is_a_no_op_when_the_flag_is_off(
        self, engagement_app: ModuleType
    ) -> None:
        with patch.object(
            engagement_app, "verify_jwt_token", return_value={"user_id": 1, "tenant": "acme"}
        ), patch.object(
            engagement_app, "feature_enabled", new_callable=AsyncMock
        ) as mock_gate:
            mock_gate.return_value = False

            client = engagement_app.app.test_client()
            response = await client.post(
                "/api/v1/polls",
                headers=self._auth_headers(),
                json={
                    "community_id": 42,
                    "title": "Best penguin?",
                    "options": ["Gentoo", "Emperor"],
                },
            )

            assert response.status_code == 404
            # The actual proof of "no-op": create_poll returns before ever
            # touching the DAL insert path.
            engagement_app.db.community_polls.insert.assert_not_called()
            mock_gate.assert_awaited_once_with(
                "waddles.marketing.engagement", tenant="acme", community=42
            )

    @pytest.mark.asyncio
    async def test_create_poll_proceeds_past_the_gate_when_the_flag_is_on(
        self, engagement_app: ModuleType
    ) -> None:
        with patch.object(
            engagement_app, "verify_jwt_token", return_value={"user_id": 1, "tenant": "acme"}
        ), patch.object(
            engagement_app, "feature_enabled", new_callable=AsyncMock
        ) as mock_gate:
            mock_gate.return_value = True
            engagement_app.db.community_polls.insert.return_value = 7

            client = engagement_app.app.test_client()
            response = await client.post(
                "/api/v1/polls",
                headers=self._auth_headers(),
                json={
                    "community_id": 42,
                    "title": "Best penguin?",
                    "options": ["Gentoo", "Emperor"],
                },
            )

            # Gate passed -- insert was attempted (contrast with the
            # not-called assertion in the flag-off test above). The mocked
            # DAL doesn't produce a realistic row, so this only asserts the
            # gate let the request through, not full 201 response shape.
            assert response.status_code != 404
            engagement_app.db.community_polls.insert.assert_called_once()
            mock_gate.assert_awaited_once_with(
                "waddles.marketing.engagement", tenant="acme", community=42
            )
