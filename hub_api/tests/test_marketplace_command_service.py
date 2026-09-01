"""`services/marketplace_command_service.py` -- command registration + router-integration reads."""

from __future__ import annotations

from typing import Any

import pytest
from pydal import DAL, Field

from services import marketplace_command_service as commands


@pytest.fixture
def dal() -> Any:
    db = DAL("sqlite:memory")
    db.define_table(
        "commands",
        Field("command", "string"),
        Field("module_name", "string"),
        Field("module_url", "string"),
        Field("description", "text"),
        Field("usage", "text"),
        Field("category", "string", default="general"),
        Field("permission_level", "string", default="everyone"),
        Field("cooldown_seconds", "integer", default=0),
        Field("community_id", "integer"),
        Field("is_enabled", "boolean", default=True),
        Field("is_active", "boolean", default=True),
        Field("created_at", "datetime"),
        Field("updated_at", "datetime"),
    )
    yield db
    db.close()


class _FakeModule:
    def __init__(self, **kwargs: Any) -> None:
        self.id = kwargs.get("id", 1)
        self.trigger_commands = kwargs.get("trigger_commands", [])
        self.name = kwargs.get("name", "Mod")
        self.description = kwargs.get("description")
        self.category = kwargs.get("category")


class TestRegisterModuleCommands:
    def test_inserts_a_row_per_trigger_command(self, dal: Any) -> None:
        module = _FakeModule(id=5, trigger_commands=["!weather", "!forecast"])
        commands.register_module_commands(dal, community_id=1, module=module)

        rows = dal(dal.commands.community_id == 1).select()
        assert len(rows) == 2
        assert {r.command for r in rows} == {"!weather", "!forecast"}
        assert all(r.module_name == "marketplace:5" for r in rows)
        expected_url = "http://marketplace:8100/api/v1/internal/execute/5"
        assert all(r.module_url == expected_url for r in rows)

    def test_no_trigger_commands_is_a_noop(self, dal: Any) -> None:
        module = _FakeModule(id=6, trigger_commands=[])
        commands.register_module_commands(dal, community_id=1, module=module)
        assert dal(dal.commands.id > 0).count() == 0

    def test_re_registering_updates_existing_row(self, dal: Any) -> None:
        module = _FakeModule(id=7, trigger_commands=["!x"])
        commands.register_module_commands(dal, community_id=1, module=module)
        commands.register_module_commands(dal, community_id=1, module=module)
        assert dal(dal.commands.community_id == 1).count() == 1


class TestUnregisterModuleCommands:
    def test_removes_only_the_targeted_module(self, dal: Any) -> None:
        commands.register_module_commands(
            dal, community_id=1, module=_FakeModule(id=1, trigger_commands=["!a"])
        )
        commands.register_module_commands(
            dal, community_id=1, module=_FakeModule(id=2, trigger_commands=["!b"])
        )
        commands.unregister_module_commands(dal, community_id=1, module_id=1)

        remaining = dal(dal.commands.community_id == 1).select()
        assert len(remaining) == 1
        assert remaining[0].module_name == "marketplace:2"


class TestGetCommunityCommands:
    def test_filters_enabled_marketplace_commands_only(self, dal: Any) -> None:
        commands.register_module_commands(
            dal, community_id=1, module=_FakeModule(id=1, trigger_commands=["!a"])
        )
        dal.commands.insert(command="!other", module_name="not-marketplace:1", community_id=1)
        dal.commit()

        result = commands.get_community_commands(dal, 1)
        assert len(result) == 1
        assert result[0]["command"] == "!a"


class TestGetRegisteredCommands:
    def test_returns_all_marketplace_commands_regardless_of_enabled(self, dal: Any) -> None:
        commands.register_module_commands(
            dal, community_id=1, module=_FakeModule(id=1, trigger_commands=["!a"])
        )
        dal(dal.commands.community_id == 1).update(is_enabled=False)
        dal.commit()

        result = commands.get_registered_commands(dal, 1)
        assert len(result) == 1
        assert result[0]["isEnabled"] is False
