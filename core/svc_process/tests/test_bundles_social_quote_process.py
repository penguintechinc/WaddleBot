"""Tests for bundles.social_quote_process: quote command transform.

Tests the !quote command parsing, database lookups for random/ID fetch, and
quote addition intent storage for the action stage.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest
from flask_core import PlatformEvent, bundle_context, reset_bundle_dal_for_tests, set_bundle_dal

from bundles.social_quote_process import transform


def _event(
    text: str,
    *,
    actor: str | None = "penguin",
    platform: str = "twitch",
    **payload_overrides: object,
) -> PlatformEvent:
    """Factory to build a PlatformEvent for testing."""
    payload: dict[str, object] = {"text": text, **payload_overrides}
    return PlatformEvent(
        platform=platform,
        event_type="message",
        actor=actor,
        payload=payload,
        occurred_at="2026-01-01T00:00:00+00:00",
    )


class _FakeDal:
    """In-memory stand-in for AsyncDAL -- implements only the .execute() surface."""

    def __init__(self) -> None:
        self._quotes: dict[int, dict[str, Any]] = {
            42: {"id": 42, "quote_text": "test quote", "quoted_username": "bob"},
            1: {"id": 1, "quote_text": "random quote", "quoted_username": "alice"},
        }

    async def execute(self, sql: str, params: list[Any]) -> list[dict[str, Any]]:
        """Mock execute for quote lookups."""
        if "ORDER BY RANDOM()" in sql:
            # Random quote query
            approved = [q for q in self._quotes.values() if q.get("quoted_username")]
            return approved[:1] if approved else []
        if "WHERE id =" in sql and params:
            # ID lookup
            quote_id = params[0]
            if quote_id in self._quotes:
                return [self._quotes[quote_id]]
            return []
        return []


@pytest.fixture(autouse=True)
def _dal() -> Any:
    """Set up fake DAL for all tests."""
    fake = _FakeDal()
    set_bundle_dal(fake)
    yield fake
    reset_bundle_dal_for_tests()


class TestQuoteCommands:
    async def test_bare_quote_command_shows_help(self) -> None:
        """!quote with no args shows help text."""
        result = await transform(_event("!quote"))
        assert result is not None
        assert "Quote commands:" in result.payload["text"]
        assert "!quote add" in result.payload["text"]
        assert "!quote random" in result.payload["text"]

    async def test_add_quote_stores_intent(self) -> None:
        """!quote add <text> stores add action in payload for action stage."""
        result = await transform(_event("!quote add hello world this is a quote"))
        assert result is not None
        assert result.payload["_quote_action"] == "add"
        assert result.payload["_quote_text"] == "hello world this is a quote"
        assert result.payload["_actor"] == "penguin"

    async def test_add_quote_without_text_shows_usage(self) -> None:
        """!quote add with no text shows usage hint."""
        result = await transform(_event("!quote add"))
        assert result is not None
        assert "Usage:" in result.payload["text"]
        assert "!quote add" in result.payload["text"]

    async def test_add_quote_with_only_whitespace_shows_usage(self) -> None:
        """!quote add with only whitespace shows usage hint."""
        result = await transform(_event("!quote add    "))
        assert result is not None
        assert "Usage:" in result.payload["text"]

    async def test_quote_by_id_makes_db_call(self) -> None:
        """!quote <id> attempts database lookup."""
        with bundle_context(tenant="acme", community="1", app_id="waddles.social.quote.default"):
            result = await transform(_event("!quote 42"))

        assert result is not None
        assert "#42:" in result.payload["text"]
        assert "test" in result.payload["text"]
        assert "bob" in result.payload["text"]

    async def test_quote_by_id_not_found(self) -> None:
        """!quote <id> when quote not found shows not-found message."""
        with bundle_context(tenant="acme", community="1", app_id="waddles.social.quote.default"):
            result = await transform(_event("!quote 999"))

        assert result is not None
        assert "not found" in result.payload["text"]

    async def test_quote_random_makes_db_call(self) -> None:
        """!quote random attempts database lookup."""
        with bundle_context(tenant="acme", community="1", app_id="waddles.social.quote.default"):
            result = await transform(_event("!quote random"))

        assert result is not None
        assert "#" in result.payload["text"]

    async def test_quote_random_not_found(self) -> None:
        """!quote random when no quotes exist shows not-found message."""
        # Create a DAL with no quotes
        fake = _FakeDal()
        fake._quotes = {}
        set_bundle_dal(fake)
        try:
            with bundle_context(
                tenant="acme", community="1", app_id="waddles.social.quote.default"
            ):
                result = await transform(_event("!quote random"))

            assert result is not None
            assert "No quotes found" in result.payload["text"]
        finally:
            reset_bundle_dal_for_tests()

    async def test_unknown_quote_subcommand(self) -> None:
        """!quote <unknown> shows unknown command message."""
        with bundle_context(tenant="acme", community="1", app_id="waddles.social.quote.default"):
            result = await transform(_event("!quote nonsense"))
        assert result is not None
        assert "Unknown quote command:" in result.payload["text"]

    async def test_quote_commands_case_insensitive(self) -> None:
        """Quote subcommands are case-insensitive."""
        with bundle_context(tenant="acme", community="1", app_id="waddles.social.quote.default"):
            result = await transform(_event("!QUOTE RANDOM"))

        assert result is not None
        assert "#" in result.payload["text"]

    async def test_quote_id_with_leading_zeros(self) -> None:
        """!quote 0042 is treated as numeric ID."""
        with bundle_context(tenant="acme", community="1", app_id="waddles.social.quote.default"):
            result = await transform(_event("!quote 0042"))

        assert result is not None
        assert "#42:" in result.payload["text"]


class TestNonQuoteChatter:
    async def test_regular_message_is_no_reply(self) -> None:
        """Regular chatter (no !quote prefix) returns None."""
        assert await transform(_event("hello everyone")) is None
        assert await transform(_event("just chatting")) is None

    async def test_empty_message_is_no_reply(self) -> None:
        """Empty or whitespace-only messages return None."""
        assert await transform(_event("")) is None
        assert await transform(_event("   ")) is None

    async def test_missing_text_field_raises(self) -> None:
        """Event with missing 'text' field raises ValueError."""
        event = PlatformEvent(
            platform="twitch",
            event_type="message",
            actor="penguin",
            payload={},  # missing text
            occurred_at="2026-01-01T00:00:00+00:00",
        )
        with pytest.raises(ValueError, match="text"):
            await transform(event)

    async def test_non_string_text_raises(self) -> None:
        """Event with non-string text field raises ValueError."""
        event = PlatformEvent(
            platform="twitch",
            event_type="message",
            actor="penguin",
            payload={"text": 123},  # not a string
            occurred_at="2026-01-01T00:00:00+00:00",
        )
        with pytest.raises(ValueError, match="text"):
            await transform(event)


class TestEdgeCases:
    async def test_payload_fields_preserved_on_reply(self) -> None:
        """Payload fields like channel_id are preserved on reply."""
        result = await transform(_event("!quote", channel_id="chan-42"))
        assert result is not None
        assert result.payload["channel_id"] == "chan-42"

    async def test_top_level_fields_preserved(self) -> None:
        """Top-level PlatformEvent fields are never mutated."""
        event = _event("!quote", platform="discord")
        result = await transform(event)
        assert result is not None
        assert result.platform == "discord"
        assert result.event_type == "message"
        assert result.actor == "penguin"

    async def test_original_event_not_mutated(self) -> None:
        """Transform returns a new event, doesn't mutate the input."""
        event = _event("!quote add test")
        result = await transform(event)
        assert event.payload["text"] == "!quote add test"
        assert result is not event
        assert "_quote_action" in result.payload

    async def test_missing_actor_handled_gracefully(self) -> None:
        """Quote add with no actor stores None gracefully."""
        result = await transform(_event("!quote add test", actor=None))
        assert result is not None
        assert result.payload["_quote_action"] == "add"
        assert result.payload["_actor"] is None

    async def test_db_exception_on_random_quote(self) -> None:
        """Database exception on random quote fetch returns None gracefully."""
        fake = _FakeDal()
        fake.execute = AsyncMock(side_effect=Exception("DB error"))  # type: ignore
        set_bundle_dal(fake)
        try:
            with bundle_context(
                tenant="acme", community="1", app_id="waddles.social.quote.default"
            ):
                result = await transform(_event("!quote random"))

            assert result is not None
            assert "No quotes found" in result.payload["text"]
        finally:
            reset_bundle_dal_for_tests()

    async def test_db_exception_on_id_quote(self) -> None:
        """Database exception on ID quote fetch returns None gracefully."""
        fake = _FakeDal()
        fake.execute = AsyncMock(side_effect=Exception("DB error"))  # type: ignore
        set_bundle_dal(fake)
        try:
            with bundle_context(
                tenant="acme", community="1", app_id="waddles.social.quote.default"
            ):
                result = await transform(_event("!quote 42"))

            assert result is not None
            assert "not found" in result.payload["text"]
        finally:
            reset_bundle_dal_for_tests()

    async def test_quote_with_extra_spaces(self) -> None:
        """Extra spaces in command are handled correctly."""
        result = await transform(_event("!quote    add    hello world"))
        assert result is not None
        assert result.payload["_quote_action"] == "add"
        assert result.payload["_quote_text"] == "hello world"

    async def test_very_long_quote_text(self) -> None:
        """Very long quote text is stored as-is."""
        long_text = "a" * 1000
        result = await transform(_event(f"!quote add {long_text}"))
        assert result is not None
        assert result.payload["_quote_text"] == long_text
