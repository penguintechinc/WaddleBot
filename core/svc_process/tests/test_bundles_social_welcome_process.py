"""Tests for social_welcome_process bundle."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest
from flask_core import PlatformEvent, bundle_context, reset_bundle_dal_for_tests, set_bundle_dal

from bundles.social_welcome_process import (
    _build_welcome,
    _is_first_time,
    _try_mark_welcomed,
    transform,
)


def _event(
    text: str = "hello",
    author_id: str = "user123",
    actor: str = "penguin",
) -> PlatformEvent:
    """Create a test PlatformEvent."""
    return PlatformEvent(
        platform="discord",
        event_type="message",
        actor=actor,
        payload={
            "text": text,
            "author_id": author_id,
            "channel_id": "chan-1",
        },
        occurred_at="2026-01-01T00:00:00+00:00",
    )


def _mock_executor(**rows_by_query: object) -> AsyncMock:
    """Create a mock SQL executor."""
    executor = AsyncMock()

    async def execute_side_effect(sql: str, params: list | None = None) -> list[dict[str, Any]]:
        for query_fragment, rows in rows_by_query.items():
            if query_fragment in sql:
                return rows if isinstance(rows, list) else []
        return []

    executor.execute.side_effect = execute_side_effect
    return executor


@pytest.fixture(autouse=True)
def reset_bundle_dal() -> None:
    """Reset the bundle DAL before each test."""
    yield
    reset_bundle_dal_for_tests()


class TestIsFirstTime:
    """Tests for _is_first_time."""

    async def test_returns_true_if_no_prior_events(self) -> None:
        """User with no prior activity_message_events is a first-timer."""
        executor = _mock_executor(activity_message_events=[])
        set_bundle_dal(executor)
        with bundle_context(tenant="acme", community="42", app_id="waddles.social.welcome.default"):
            result = await _is_first_time("discord", "user123")
        assert result is True

    async def test_returns_false_if_prior_events_exist(self) -> None:
        """User with prior events is not a first-timer."""
        executor = _mock_executor(activity_message_events=[{"id": 1}])
        set_bundle_dal(executor)
        with bundle_context(tenant="acme", community="42", app_id="waddles.social.welcome.default"):
            result = await _is_first_time("discord", "user123")
        assert result is False

    async def test_parameterized_query(self) -> None:
        """Query is parameterized with correct community, platform, user."""
        executor = AsyncMock()
        executor.execute.return_value = []
        set_bundle_dal(executor)
        with bundle_context(tenant="acme", community="42", app_id="waddles.social.welcome.default"):
            await _is_first_time("twitch", "user789")
        executor.execute.assert_called_once()
        call_args = executor.execute.call_args
        assert "activity_message_events" in call_args[0][0]
        assert [42, "twitch", "user789"] == call_args[0][1]


class TestTryMarkWelcomed:
    """Tests for _try_mark_welcomed."""

    async def test_returns_true_if_insert_succeeded(self) -> None:
        """Returning a row means this call won the race."""
        executor = _mock_executor(community_welcomed_users=[{"id": 999}])
        set_bundle_dal(executor)
        with bundle_context(tenant="acme", community="42", app_id="waddles.social.welcome.default"):
            result = await _try_mark_welcomed("discord", "user123")
        assert result is True

    async def test_returns_false_if_conflict_prevented_insert(self) -> None:
        """No returned row means a concurrent insert already claimed the welcome."""
        executor = _mock_executor(community_welcomed_users=[])
        set_bundle_dal(executor)
        with bundle_context(tenant="acme", community="42", app_id="waddles.social.welcome.default"):
            result = await _try_mark_welcomed("discord", "user123")
        assert result is False

    async def test_parameterized_query(self) -> None:
        """Query is parameterized with community, platform, user."""
        executor = AsyncMock()
        executor.execute.return_value = []
        set_bundle_dal(executor)
        with bundle_context(tenant="acme", community="42", app_id="waddles.social.welcome.default"):
            await _try_mark_welcomed("twitch", "user789")
        executor.execute.assert_called_once()
        call_args = executor.execute.call_args
        assert "community_welcomed_users" in call_args[0][0]
        assert "ON CONFLICT" in call_args[0][0]
        assert [42, "twitch", "user789"] == call_args[0][1]


class TestBuildWelcome:
    """Tests for _build_welcome."""

    async def test_returns_template_and_source(self) -> None:
        """Welcome message includes username and is marked as template source."""
        text, source = await _build_welcome(platform_username="alice")
        assert "alice" in text
        assert source == "template"

    async def test_different_username_in_template(self) -> None:
        """Template respects the provided username."""
        text1, _ = await _build_welcome(platform_username="alice")
        text2, _ = await _build_welcome(platform_username="bob")
        assert "alice" in text1
        assert "bob" in text2
        assert text1 != text2


class TestTransform:
    """Tests for transform entrypoint."""

    async def test_missing_text_raises_valueerror(self) -> None:
        """Missing 'text' in payload raises ValueError."""
        event = _event(text="")
        event.payload.pop("text", None)
        set_bundle_dal(_mock_executor())
        with pytest.raises(ValueError, match="text"):
            with bundle_context(
                tenant="acme", community="42", app_id="waddles.social.welcome.default"
            ):
                await transform(event)

    async def test_missing_author_id_raises_valueerror(self) -> None:
        """Missing 'author_id' in payload raises ValueError."""
        event = _event()
        event.payload.pop("author_id", None)
        set_bundle_dal(_mock_executor())
        with pytest.raises(ValueError, match="author_id"):
            with bundle_context(
                tenant="acme", community="42", app_id="waddles.social.welcome.default"
            ):
                await transform(event)

    async def test_missing_actor_raises_valueerror(self) -> None:
        """Missing event.actor raises ValueError."""
        event = _event(actor="")
        set_bundle_dal(_mock_executor())
        with pytest.raises(ValueError, match="event.actor"):
            with bundle_context(
                tenant="acme", community="42", app_id="waddles.social.welcome.default"
            ):
                await transform(event)

    async def test_repeat_visitor_returns_none(self) -> None:
        """Event from a repeat visitor returns None (no welcome)."""
        event = _event()
        executor = _mock_executor(activity_message_events=[{"id": 1}])
        set_bundle_dal(executor)
        with bundle_context(tenant="acme", community="42", app_id="waddles.social.welcome.default"):
            result = await transform(event)
        assert result is None

    async def test_race_condition_returns_none(self) -> None:
        """If another process already marked user as welcomed, return None."""
        event = _event()
        executor = AsyncMock()
        executor.execute.side_effect = [
            [],  # _is_first_time returns empty (first-timer)
            [],  # _try_mark_welcomed returns empty (lost race)
        ]
        set_bundle_dal(executor)
        with bundle_context(tenant="acme", community="42", app_id="waddles.social.welcome.default"):
            result = await transform(event)
        assert result is None

    async def test_welcome_claims_and_modifies_event(self) -> None:
        """On successful first-message claim, return event with welcome text."""
        event = _event(text="hello world")
        executor = AsyncMock()
        executor.execute.side_effect = [
            [],  # _is_first_time returns empty (first-timer)
            [{"id": 999}],  # _try_mark_welcomed succeeds
        ]
        set_bundle_dal(executor)
        with bundle_context(tenant="acme", community="42", app_id="waddles.social.welcome.default"):
            result = await transform(event)
        assert isinstance(result, PlatformEvent)
        assert result.payload["text"] != event.payload["text"]
        assert "Welcome" in result.payload["text"]
        assert result.payload["channel_id"] == event.payload["channel_id"]

    async def test_non_string_text_raises_valueerror(self) -> None:
        """Non-string 'text' in payload raises ValueError."""
        event = _event()
        event.payload["text"] = 123
        set_bundle_dal(_mock_executor())
        with pytest.raises(ValueError, match="text"):
            with bundle_context(
                tenant="acme", community="42", app_id="waddles.social.welcome.default"
            ):
                await transform(event)

    async def test_non_string_author_id_raises_valueerror(self) -> None:
        """Non-string 'author_id' raises ValueError."""
        event = _event()
        event.payload["author_id"] = 123
        set_bundle_dal(_mock_executor())
        with pytest.raises(ValueError, match="author_id"):
            with bundle_context(
                tenant="acme", community="42", app_id="waddles.social.welcome.default"
            ):
                await transform(event)

    async def test_empty_author_id_raises_valueerror(self) -> None:
        """Empty 'author_id' raises ValueError."""
        event = _event()
        event.payload["author_id"] = ""
        set_bundle_dal(_mock_executor())
        with pytest.raises(ValueError, match="author_id"):
            with bundle_context(
                tenant="acme", community="42", app_id="waddles.social.welcome.default"
            ):
                await transform(event)

    async def test_welcome_preserves_payload_fields(self) -> None:
        """Modified event preserves original payload fields except text."""
        event = _event(text="hello")
        event.payload["extra_field"] = "should be preserved"
        executor = AsyncMock()
        executor.execute.side_effect = [[], [{"id": 999}]]
        set_bundle_dal(executor)
        with bundle_context(tenant="acme", community="42", app_id="waddles.social.welcome.default"):
            result = await transform(event)
        assert result is not None
        assert result.payload["extra_field"] == "should be preserved"
        assert result.platform == event.platform
