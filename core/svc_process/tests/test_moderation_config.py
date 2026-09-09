"""Tests for `services.moderation_config` -- `community_moderation_config`/`tenants` reads."""

from __future__ import annotations

from typing import Any

from services.moderation_config import get_enabled_categories, get_tenant_id


class _FakeDal:
    """Records every `execute()` call; returns a preloaded row set for that SQL."""

    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows
        self.calls: list[tuple[str, list[Any] | None]] = []

    async def execute(self, sql: str, params: list[Any] | None = None) -> list[Any]:
        self.calls.append((sql, params))
        return self._rows


class TestGetEnabledCategories:
    async def test_no_row_returns_empty_set(self) -> None:
        dal = _FakeDal(rows=[])
        result = await get_enabled_categories(dal, 42)
        assert result == set()
        assert dal.calls[0][1] == [42]

    async def test_row_with_list_value(self) -> None:
        dal = _FakeDal(rows=[{"enabled_categories": ["hate_speech", "slurs"]}])
        result = await get_enabled_categories(dal, 42)
        assert result == {"hate_speech", "slurs"}

    async def test_row_with_json_string_value(self) -> None:
        """Some drivers return JSONB as a raw string rather than a parsed list."""
        dal = _FakeDal(rows=[{"enabled_categories": '["hate_speech"]'}])
        result = await get_enabled_categories(dal, 42)
        assert result == {"hate_speech"}

    async def test_row_with_null_value_returns_empty_set(self) -> None:
        dal = _FakeDal(rows=[{"enabled_categories": None}])
        result = await get_enabled_categories(dal, 42)
        assert result == set()

    async def test_row_with_empty_list_returns_empty_set(self) -> None:
        dal = _FakeDal(rows=[{"enabled_categories": []}])
        result = await get_enabled_categories(dal, 42)
        assert result == set()


class TestGetTenantId:
    async def test_no_row_returns_none(self) -> None:
        dal = _FakeDal(rows=[])
        result = await get_tenant_id(dal, "global")
        assert result is None
        assert dal.calls[0][1] == ["global"]

    async def test_row_returns_int_id(self) -> None:
        dal = _FakeDal(rows=[{"id": 7}])
        result = await get_tenant_id(dal, "global")
        assert result == 7
