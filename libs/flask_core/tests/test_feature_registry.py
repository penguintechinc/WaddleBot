"""
Feature registry tests
========================

Covers :mod:`flask_core.feature_registry`: register/get/for_module/
all_contracts on an isolated :class:`FeatureRegistry`, and
:func:`entitled_features` against a fake ``check`` callable so no live
PostHog/license-server connection is needed (mirrors ``test_entitlement.py``'s
fake-adapter shape).

Fail-on-purpose proof: ``test_entitled_features_filters_out_disabled``
was verified to catch a regression by temporarily making
``entitled_features`` return the full pool unconditionally and confirming
this test goes red, then reverting.
"""

from __future__ import annotations

from typing import List, Optional

import pytest

from flask_core.feature_contract import FeatureContract
from flask_core.feature_registry import (
    REASON_DUPLICATE_ID,
    REASON_NOT_FOUND,
    FeatureRegistry,
    FeatureRegistryError,
    entitled_features,
)


def make_contract(
    id: str, module: str = "bot", min_tier: str = "free", flag: Optional[str] = None
) -> FeatureContract:
    return FeatureContract(
        id=id,
        version=1,
        module=module,
        requires_scopes=frozenset({f"{module}.command:write"}),
        min_tier=min_tier,
        flag=flag or f"waddles.{id}",
    )


class TestFeatureRegistry:
    def test_register_then_get_returns_same_contract(self) -> None:
        registry = FeatureRegistry()
        contract = make_contract("bot.shoutout")
        registry.register(contract)
        assert registry.get("bot.shoutout") is contract

    def test_get_unknown_id_raises_not_found(self) -> None:
        registry = FeatureRegistry()
        with pytest.raises(FeatureRegistryError) as excinfo:
            registry.get("bot.unknown")
        assert excinfo.value.reason == REASON_NOT_FOUND

    def test_duplicate_id_raises(self) -> None:
        registry = FeatureRegistry()
        registry.register(make_contract("bot.shoutout"))
        with pytest.raises(FeatureRegistryError) as excinfo:
            registry.register(make_contract("bot.shoutout"))
        assert excinfo.value.reason == REASON_DUPLICATE_ID

    def test_for_module_returns_only_that_modules_contracts_in_registration_order(self) -> None:
        registry = FeatureRegistry()
        bot_shoutout = registry.register(make_contract("bot.shoutout"))
        bot_commands = registry.register(make_contract("bot.commands"))
        registry.register(make_contract("social.polls", module="social"))

        assert registry.for_module("bot") == (bot_shoutout, bot_commands)
        assert [c.module for c in registry.for_module("social")] == ["social"]

    def test_for_module_unknown_module_returns_empty_tuple(self) -> None:
        registry = FeatureRegistry()
        assert registry.for_module("customer") == ()

    def test_all_contracts_returns_every_registered_contract(self) -> None:
        registry = FeatureRegistry()
        a = registry.register(make_contract("bot.shoutout"))
        b = registry.register(make_contract("social.polls", module="social"))
        assert set(registry.all_contracts()) == {a, b}

    def test_clear_empties_registry(self) -> None:
        registry = FeatureRegistry()
        registry.register(make_contract("bot.shoutout"))
        registry.clear()
        assert registry.all_contracts() == ()
        assert registry.for_module("bot") == ()


class TestFeatureRegistrySingletonModuleFunctions:
    """The module-level `register`/`get`/`for_module`/`all_contracts`
    functions are thin delegations to the process-wide singleton
    (`get_registry()`) -- exercised here directly, mirroring
    `TestAppRegistrySingletonModuleFunctions` in test_app_framework.py, so a
    drift between the module-function call shape and the class method it
    delegates to is caught here rather than only in production wiring."""

    def test_module_functions_delegate_to_singleton(self) -> None:
        from flask_core import feature_registry as feature_registry_module

        registry = feature_registry_module.get_registry()
        registry.clear()
        try:
            contract = make_contract("bot.shoutout")
            registered = feature_registry_module.register(contract)
            assert registered is contract
            assert feature_registry_module.get("bot.shoutout") is contract
            assert feature_registry_module.for_module("bot") == (contract,)
            assert feature_registry_module.all_contracts() == (contract,)
        finally:
            registry.clear()


class FakeCheck:
    """Records calls; resolves each (flag, tenant, community) triple against a fixed map."""

    def __init__(self, enabled_flags: set[str]) -> None:
        self.enabled_flags = enabled_flags
        self.calls: List[tuple[str, str, Optional[int]]] = []

    async def __call__(
        self, flag_key: str, *, tenant: str, community: Optional[int] = None, default: bool = False
    ) -> bool:
        self.calls.append((flag_key, tenant, community))
        return flag_key in self.enabled_flags


class TestEntitledFeatures:
    async def test_entitled_features_filters_out_disabled(self) -> None:
        shoutout = make_contract("bot.shoutout")
        commands = make_contract("bot.commands")
        check = FakeCheck(enabled_flags={"waddles.bot.shoutout"})

        result = await entitled_features(
            tenant="acme", contracts=(shoutout, commands), check=check
        )

        assert result == [shoutout]

    async def test_entitled_features_all_enabled_returns_all(self) -> None:
        shoutout = make_contract("bot.shoutout")
        commands = make_contract("bot.commands")
        check = FakeCheck(enabled_flags={"waddles.bot.shoutout", "waddles.bot.commands"})

        result = await entitled_features(
            tenant="acme", contracts=(shoutout, commands), check=check
        )

        assert result == [shoutout, commands]

    async def test_entitled_features_none_enabled_returns_empty(self) -> None:
        shoutout = make_contract("bot.shoutout")
        check = FakeCheck(enabled_flags=set())

        result = await entitled_features(tenant="acme", contracts=(shoutout,), check=check)

        assert result == []

    async def test_entitled_features_empty_pool_returns_empty_without_calling_check(self) -> None:
        check = FakeCheck(enabled_flags=set())

        result = await entitled_features(tenant="acme", contracts=(), check=check)

        assert result == []
        assert check.calls == []

    async def test_entitled_features_passes_tenant_and_community_through(self) -> None:
        shoutout = make_contract("bot.shoutout")
        check = FakeCheck(enabled_flags={"waddles.bot.shoutout"})

        await entitled_features(tenant="acme", community=42, contracts=(shoutout,), check=check)

        assert check.calls == [("waddles.bot.shoutout", "acme", 42)]

    async def test_entitled_features_defaults_to_singleton_registry_pool(self) -> None:
        """No `contracts` given -> pulls from the process-wide registry singleton."""
        from flask_core.feature_registry import get_registry

        registry = get_registry()
        registry.clear()
        try:
            shoutout = registry.register(make_contract("bot.shoutout"))
            check = FakeCheck(enabled_flags={"waddles.bot.shoutout"})

            result = await entitled_features(tenant="acme", check=check)

            assert result == [shoutout]
        finally:
            registry.clear()

    async def test_entitled_features_defaults_check_to_feature_flags_feature_enabled(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No `check` given -> lazily imports and uses
        `flask_core.feature_flags.feature_enabled` (the real PostHog+license
        gate) rather than silently no-oping. Regression this guards against:
        a caller that forgets to pass `check` in production would otherwise
        never be caught by a test suite that always injects a fake."""
        import flask_core.feature_flags as feature_flags_module

        shoutout = make_contract("bot.shoutout")
        fake = FakeCheck(enabled_flags={"waddles.bot.shoutout"})
        monkeypatch.setattr(feature_flags_module, "feature_enabled", fake)

        result = await entitled_features(tenant="acme", contracts=(shoutout,))

        assert result == [shoutout]
        assert fake.calls == [("waddles.bot.shoutout", "acme", None)]
