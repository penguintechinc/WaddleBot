"""Tests for `bundles.community_reputation_process` -- `!reputation`/`!rep`."""

from __future__ import annotations

from typing import Any

import pytest
from flask_core import PlatformEvent, bundle_context, reset_bundle_dal_for_tests, set_bundle_dal

from bundles.community_reputation_process import _reputation_label, transform


class _FakeDal:
    """In-memory stand-in for `AsyncDAL` -- routes by distinctive SQL substrings.

    Three query shapes this bundle issues, distinguished the same way the
    production SQL is distinguished by table/clause:
    - `community_members` by `(platform, platform_user_id)`
    - `community_members` by `display_name`
    - `communities` label lookup
    - `reputation_global` score lookup
    """

    def __init__(self, *, raise_on_execute: bool = False) -> None:
        self._raise_on_execute = raise_on_execute
        self.by_platform_id: dict[str, dict[str, Any]] = {}
        self.by_display_name: dict[str, dict[str, Any]] = {}
        self.community_labels: dict[int, dict[str, Any]] = {}
        self.global_scores: dict[int, dict[str, Any]] = {}

    async def execute(self, sql: str, params: list[Any]) -> list[dict[str, Any]]:
        if self._raise_on_execute:
            raise RuntimeError("simulated DB outage")
        if "reputation_global" in sql:
            (hub_user_id,) = params
            row = self.global_scores.get(hub_user_id)
            return [row] if row else []
        if "FROM communities" in sql:
            (community_id,) = params
            row = self.community_labels.get(community_id)
            return [row] if row else []
        if "cm.platform_user_id" in sql:
            _community_id, _platform, platform_user_id = params
            row = self.by_platform_id.get(platform_user_id)
            return [row] if row else []
        _community_id, actor = params
        row = self.by_display_name.get(actor)
        return [row] if row else []


def _event(
    text: str, *, actor: str | None = "penguinzplays", author_id: str | None = None
) -> PlatformEvent:
    payload: dict[str, object] = {"text": text}
    if author_id is not None:
        payload["author_id"] = author_id
    return PlatformEvent(
        platform="twitch",
        event_type="message",
        actor=actor,
        payload=payload,
        occurred_at="2026-01-01T00:00:00+00:00",
    )


async def _run(dal: _FakeDal, text: str, **event_kwargs: object) -> PlatformEvent | None:
    set_bundle_dal(dal)
    try:
        with bundle_context(tenant="acme", community="4", app_id="waddles.bot.twitch.default"):
            return await transform(_event(text, **event_kwargs))  # type: ignore[arg-type]
    finally:
        reset_bundle_dal_for_tests()


class TestRouting:
    async def test_non_command_text_returns_none(self) -> None:
        assert await transform(_event("just chatting")) is None

    async def test_malformed_event_raises_value_error(self) -> None:
        event = PlatformEvent(
            platform="twitch", event_type="message", actor="p", payload={}, occurred_at="x"
        )
        with pytest.raises(ValueError, match="text"):
            await transform(event)

    async def test_bare_bang_returns_none(self) -> None:
        assert await transform(_event("!")) is None


class TestLookup:
    async def test_reply_shows_both_global_and_community_with_labels(self) -> None:
        dal = _FakeDal()
        dal.by_platform_id["u-123"] = {
            "display_name": "penguinzplays",
            "reputation": 720,
            "hub_user_id": "42",
        }
        dal.community_labels[4] = {"label": "Waddlebot HQ"}
        dal.global_scores[42] = {"score": 600}
        result = await _run(dal, "!reputation", author_id="u-123")
        assert result is not None
        assert result.payload["text"] == (
            "\U0001f427 penguinzplays — Global: 600 (Fair) · " "Waddlebot HQ: 720 (Outstanding)"
        )

    async def test_falls_back_to_display_name_when_no_author_id(self) -> None:
        dal = _FakeDal()
        dal.by_display_name["penguinzplays"] = {
            "display_name": "penguinzplays",
            "reputation": 655,
            "hub_user_id": None,
        }
        dal.community_labels[4] = {"label": "Waddlebot HQ"}
        result = await _run(dal, "!rep")
        assert result is not None
        assert "Waddlebot HQ: 655 (Good)" in result.payload["text"]
        assert "Global: 600 (Fair)" in result.payload["text"]

    async def test_new_user_defaults_both_sides_to_600(self) -> None:
        """No `community_members` row and no `reputation_global` row -> 600 (Fair) both sides."""
        dal = _FakeDal()
        dal.community_labels[4] = {"label": "Waddlebot HQ"}
        result = await _run(dal, "!reputation", actor="stranger")
        assert result is not None
        assert result.payload["text"] == (
            "\U0001f427 stranger — Global: 600 (Fair) · Waddlebot HQ: 600 (Fair)"
        )

    async def test_community_without_display_name_falls_back_to_id(self) -> None:
        dal = _FakeDal()  # no community_labels entry at all
        result = await _run(dal, "!reputation", actor="stranger")
        assert result is not None
        assert "community 4: 600 (Fair)" in result.payload["text"]

    async def test_missing_community_context_is_graceful(self) -> None:
        set_bundle_dal(_FakeDal())
        try:
            with bundle_context(tenant="acme", community=None, app_id="waddles.bot.twitch.default"):
                result = await transform(_event("!reputation"))
        finally:
            reset_bundle_dal_for_tests()
        assert result is not None
        assert "unavailable" in result.payload["text"]

    async def test_db_failure_is_swallowed_gracefully(self) -> None:
        """GUARDED: a DB error inside the bundle's own guard never crashes the bot."""
        result = await _run(_FakeDal(raise_on_execute=True), "!reputation")
        assert result is not None
        assert "unavailable" in result.payload["text"]


class TestReputationLabel:
    @pytest.mark.parametrize(
        ("score", "expected"),
        [
            (549, "Menace"),
            (550, "Troll"),
            (599, "Troll"),
            (600, "Fair"),
            (649, "Fair"),
            (650, "Good"),
            (699, "Good"),
            (700, "Outstanding"),
            (749, "Outstanding"),
            (750, "Saint"),
            (850, "Saint"),
        ],
    )
    def test_boundaries(self, score: int, expected: str) -> None:
        assert _reputation_label(score) == expected
