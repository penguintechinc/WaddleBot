"""Tests for `bundles.inventory_process.transform` -- `!inventory` chat commands."""

from __future__ import annotations

from typing import Any

import pytest
from flask_core import PlatformEvent, bundle_context, reset_bundle_dal_for_tests, set_bundle_dal

from bundles.inventory_process import transform


class _FakeDal:
    """In-memory stand-in for `AsyncDAL` -- dispatches on SQL shape, like `community_chat`'s."""

    def __init__(self, *, raise_on_execute: bool = False) -> None:
        self._items: dict[str, dict[str, Any]] = {}
        self._raise_on_execute = raise_on_execute

    async def execute(self, sql: str, params: list[Any]) -> list[dict[str, Any]]:
        if self._raise_on_execute:
            raise RuntimeError("simulated DB outage")

        statement = sql.strip()
        if statement.startswith("SELECT id FROM inventory_items"):
            _community_id, name = params
            row = self._items.get(name)
            return [{"id": 1}] if row and not row["deleted"] else []

        if statement.startswith("INSERT INTO inventory_items"):
            _community_id, name, metadata = params
            self._items[name] = {
                "metadata": metadata,
                "quantity": 1,
                "available_quantity": 1,
                "deleted": False,
            }
            return []

        if statement.startswith("UPDATE inventory_items"):
            _community_id, name = params
            row = self._items.get(name)
            if row and not row["deleted"]:
                row["deleted"] = True
                return [{"id": 1}]
            return []

        if statement.startswith("SELECT name, quantity"):
            return [
                {
                    "name": name,
                    "quantity": row["quantity"],
                    "available_quantity": row["available_quantity"],
                    "metadata": row["metadata"],
                }
                for name, row in self._items.items()
                if not row["deleted"]
            ]

        raise AssertionError(f"unexpected SQL in test fake: {statement[:60]!r}")


def _event(text: str, *, actor: str | None = "penguinzplays") -> PlatformEvent:
    return PlatformEvent(
        platform="twitch",
        event_type="message",
        actor=actor,
        payload={"text": text},
        occurred_at="2026-01-01T00:00:00+00:00",
    )


async def _run(dal: _FakeDal, text: str, *, community: str | None = "4") -> PlatformEvent | None:
    set_bundle_dal(dal)
    try:
        with bundle_context(
            tenant="acme", community=community, app_id="waddles.bot.twitch.default"
        ):
            return await transform(_event(text))
    finally:
        reset_bundle_dal_for_tests()


class TestBareAndUnknown:
    async def test_bare_command_shows_usage(self) -> None:
        result = await _run(_FakeDal(), "!inventory")
        assert result is not None
        assert result.payload["text"].startswith("Inventory commands:")

    async def test_unknown_subcommand(self) -> None:
        result = await _run(_FakeDal(), "!inventory launch")
        assert result is not None
        assert "Unknown inventory command" in result.payload["text"]

    async def test_non_inventory_text_returns_none(self) -> None:
        assert await transform(_event("just chatting")) is None

    async def test_malformed_event_raises_value_error(self) -> None:
        event = PlatformEvent(
            platform="twitch", event_type="message", actor="p", payload={}, occurred_at="x"
        )
        with pytest.raises(ValueError, match="text"):
            await transform(event)


class TestAdd:
    async def test_add_new_item(self) -> None:
        result = await _run(_FakeDal(), "!inventory add fishing-rod -t tool -o penguinzplays")
        assert result is not None
        assert result.payload["text"] == "\U0001f4e6 added 'fishing-rod' to inventory."

    async def test_add_without_name_shows_usage(self) -> None:
        result = await _run(_FakeDal(), "!inventory add")
        assert result is not None
        assert result.payload["text"].startswith("Usage:")

    async def test_add_duplicate_item(self) -> None:
        dal = _FakeDal()
        await _run(dal, "!inventory add fishing-rod")
        result = await _run(dal, "!inventory add fishing-rod")
        assert result is not None
        assert result.payload["text"] == "'fishing-rod' already exists in inventory."

    async def test_add_missing_community_context_is_graceful(self) -> None:
        result = await _run(_FakeDal(), "!inventory add fishing-rod", community=None)
        assert result is not None
        assert "community context" in result.payload["text"]

    async def test_add_db_failure_is_swallowed_gracefully(self) -> None:
        """GUARDED: a DB error never crashes the bot -- graceful reply instead."""
        result = await _run(_FakeDal(raise_on_execute=True), "!inventory add fishing-rod")
        assert result is not None
        assert result.payload["text"] == "Error adding 'fishing-rod' to inventory."


class TestRemove:
    async def test_remove_existing_item(self) -> None:
        dal = _FakeDal()
        await _run(dal, "!inventory add fishing-rod")
        result = await _run(dal, "!inventory remove fishing-rod")
        assert result is not None
        assert result.payload["text"] == "\U0001f5d1 removed 'fishing-rod' from inventory."

    async def test_remove_missing_item(self) -> None:
        result = await _run(_FakeDal(), "!inventory remove ghost-item")
        assert result is not None
        assert result.payload["text"] == "'ghost-item' not found in inventory."

    async def test_remove_without_name_shows_usage(self) -> None:
        result = await _run(_FakeDal(), "!inventory remove")
        assert result is not None
        assert result.payload["text"].startswith("Usage:")

    async def test_remove_db_failure_is_swallowed_gracefully(self) -> None:
        result = await _run(_FakeDal(raise_on_execute=True), "!inventory remove fishing-rod")
        assert result is not None
        assert result.payload["text"] == "Error removing 'fishing-rod' from inventory."


class TestList:
    async def test_list_empty(self) -> None:
        result = await _run(_FakeDal(), "!inventory list")
        assert result is not None
        assert result.payload["text"].startswith("(no items yet")

    async def test_list_with_items_shows_owner_and_tags(self) -> None:
        dal = _FakeDal()
        await _run(dal, "!inventory add fishing-rod -t tool -o penguinzplays")
        result = await _run(dal, "!inventory list")
        assert result is not None
        text = result.payload["text"]
        assert "fishing-rod" in text
        assert "1/1 available" in text
        assert "owner: penguinzplays" in text
        assert "tags: tool" in text

    async def test_list_db_failure_is_swallowed_gracefully(self) -> None:
        result = await _run(_FakeDal(raise_on_execute=True), "!inventory list")
        assert result is not None
        assert result.payload["text"] == "Error listing inventory."


class TestCheckoutStub:
    @pytest.mark.parametrize("cmd", ["checkout", "checkin", "return"])
    async def test_checkout_family_returns_graceful_stub(self, cmd: str) -> None:
        """`checkout`/`checkin`/`return` are deferred -- an honest stub, never a DB write."""
        dal = _FakeDal(raise_on_execute=True)  # any DB touch here would blow up the test
        result = await _run(dal, f"!inventory {cmd} fishing-rod -T someone")
        assert result is not None
        assert "coming soon" in result.payload["text"].lower()
