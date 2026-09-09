"""Tests for `bundles.community_chat_process.transform`."""

from __future__ import annotations

from typing import Any

import pytest
from flask_core import (
    PlatformEvent,
    bundle_context,
    reset_bundle_dal_for_tests,
    set_bundle_dal,
)

from bundles.community_chat_process import (
    ChatChannel,
    ChatMessage,
    _format_channels,
    _format_chat_history,
    transform,
)


class _FakeDal:
    """In-memory stand-in for `AsyncDAL` -- implements `.execute()` for chat queries."""

    def __init__(self) -> None:
        self._messages: list[dict[str, Any]] = []
        self._channels: dict[str, dict[str, Any]] = {}

    async def execute(self, sql: str, params: list[Any]) -> list[dict[str, Any]]:
        """Execute a mock query and return results based on stored data."""
        if "hub_chat_messages" in sql and "GROUP BY" in sql:
            # Channels query
            return list(self._channels.values())
        else:
            # History query - return messages in reverse chronological order
            return sorted(self._messages, key=lambda m: m["created_at"] or "", reverse=True)

    def add_message(self, **kwargs: object) -> None:
        """Add a test message to the fake store."""
        self._messages.append(kwargs)  # type: ignore[arg-type]

    def add_channel(self, name: str, **kwargs: object) -> None:
        """Add a test channel to the fake store."""
        self._channels[name] = {"channel_name": name, **kwargs}  # type: ignore[arg-type]


@pytest.fixture(autouse=True)
def _dal() -> Any:
    """Set up and tear down fake DAL for each test."""
    fake = _FakeDal()
    set_bundle_dal(fake)
    yield fake
    reset_bundle_dal_for_tests()


def _event(text: str, **payload_overrides: object) -> PlatformEvent:
    """Build a test PlatformEvent with optional payload overrides."""
    default_payload = {"text": text, "channel_id": "chan-1"}
    default_payload.update(payload_overrides)
    return PlatformEvent(
        platform="discord",
        event_type="message",
        actor="test_user",
        payload=default_payload,
        occurred_at="2026-01-01T00:00:00+00:00",
    )


class TestTransform:
    """Tests for the transform entrypoint."""

    async def test_chat_history_command_returns_reply(self, _dal: _FakeDal) -> None:
        """!chat-history command triggers a reply."""
        _dal.add_message(
            id=1,
            community_id=1,
            channel_name="general",
            sender_username="alice",
            message_content="hello",
            message_type="text",
            created_at="2026-01-01T12:00:00Z",
        )
        with bundle_context(
            tenant="tenant-1", community="1", app_id="waddles.community.chat.default"
        ):
            result = await transform(_event("!chat-history"))
        assert isinstance(result, PlatformEvent)
        assert result.payload["text"]
        assert "Chat History" in result.payload["text"]
        assert "alice" in result.payload["text"]

    async def test_channels_command_returns_reply(self, _dal: _FakeDal) -> None:
        """!channels command triggers a reply."""
        _dal.add_channel("general", message_count=5, last_message_at="2026-01-01T12:00:00Z")
        with bundle_context(
            tenant="tenant-1", community="1", app_id="waddles.community.chat.default"
        ):
            result = await transform(_event("!channels"))
        assert isinstance(result, PlatformEvent)
        assert result.payload["text"]
        assert "Chat Channels" in result.payload["text"]
        assert "general" in result.payload["text"]

    async def test_case_insensitive_commands(self, _dal: _FakeDal) -> None:
        """Commands are case-insensitive."""
        _dal.add_message(
            id=1,
            community_id=1,
            channel_name="general",
            sender_username="alice",
            message_content="hello",
            message_type="text",
            created_at="2026-01-01T12:00:00Z",
        )
        with bundle_context(
            tenant="tenant-1", community="1", app_id="waddles.community.chat.default"
        ):
            for cmd in ["!CHAT-HISTORY", "!Chat-History", "!CHANNELS", "!Channels"]:
                result = await transform(_event(cmd))
                assert result is not None, f"Command '{cmd}' should return a reply"
                assert isinstance(result, PlatformEvent)

    async def test_ordinary_chatter_returns_none(self, _dal: _FakeDal) -> None:
        """Non-command messages return None (no reply)."""
        with bundle_context(
            tenant="tenant-1", community="1", app_id="waddles.community.chat.default"
        ):
            for text in ["hello", "just chatting", "what's up?", "tell me a story"]:
                result = await transform(_event(text))
                assert result is None, f"Text '{text}' should return None"

    async def test_preserves_channel_id_on_reply(self, _dal: _FakeDal) -> None:
        """Response preserves the original channel_id in payload."""
        _dal.add_message(
            id=1,
            community_id=1,
            channel_name="general",
            sender_username="alice",
            message_content="hello",
            message_type="text",
            created_at="2026-01-01T12:00:00Z",
        )
        with bundle_context(
            tenant="tenant-1", community="1", app_id="waddles.community.chat.default"
        ):
            result = await transform(_event("!chat-history"))
        assert result is not None
        assert result.payload["channel_id"] == "chan-1"

    async def test_preserves_other_payload_fields(self, _dal: _FakeDal) -> None:
        """Response preserves non-text payload fields."""
        _dal.add_channel("general", message_count=5, last_message_at="2026-01-01T12:00:00Z")
        with bundle_context(
            tenant="tenant-1", community="1", app_id="waddles.community.chat.default"
        ):
            result = await transform(_event("!channels", author_id="123"))
        assert result is not None
        assert result.payload.get("author_id") == "123"
        assert result.payload["channel_id"] == "chan-1"

    async def test_missing_text_returns_none(self, _dal: _FakeDal) -> None:
        """Event without 'text' in payload returns None."""
        event = PlatformEvent(
            platform="discord",
            event_type="message",
            actor=None,
            payload={"channel_id": "1"},
            occurred_at="2026-01-01T00:00:00+00:00",
        )
        with bundle_context(
            tenant="tenant-1", community="1", app_id="waddles.community.chat.default"
        ):
            result = await transform(event)
        assert result is None

    async def test_empty_text_returns_none(self, _dal: _FakeDal) -> None:
        """Empty or whitespace-only text returns None."""
        with bundle_context(
            tenant="tenant-1", community="1", app_id="waddles.community.chat.default"
        ):
            for text in ["", "   ", "\t", "\n"]:
                result = await transform(_event(text))
                assert result is None, f"Text '{repr(text)}' should return None"

    async def test_non_string_text_returns_none(self, _dal: _FakeDal) -> None:
        """Non-string 'text' in payload returns None."""
        with bundle_context(
            tenant="tenant-1", community="1", app_id="waddles.community.chat.default"
        ):
            event = PlatformEvent(
                platform="discord",
                event_type="message",
                actor="test_user",
                payload={"text": 123, "channel_id": "chan-1"},
                occurred_at="2026-01-01T00:00:00+00:00",
            )
            result = await transform(event)
            assert result is None

            event2 = PlatformEvent(
                platform="discord",
                event_type="message",
                actor="test_user",
                payload={"text": ["list"], "channel_id": "chan-1"},
                occurred_at="2026-01-01T00:00:00+00:00",
            )
            result2 = await transform(event2)
            assert result2 is None

    async def test_text_with_whitespace_stripped(self, _dal: _FakeDal) -> None:
        """Whitespace is stripped before command detection."""
        _dal.add_message(
            id=1,
            community_id=1,
            channel_name="general",
            sender_username="alice",
            message_content="hello",
            message_type="text",
            created_at="2026-01-01T12:00:00Z",
        )
        with bundle_context(
            tenant="tenant-1", community="1", app_id="waddles.community.chat.default"
        ):
            result = await transform(_event("   !chat-history   "))
        assert result is not None
        assert isinstance(result, PlatformEvent)

    async def test_command_in_middle_of_text_no_reply(self, _dal: _FakeDal) -> None:
        """Command word in the middle of text does not trigger reply."""
        with bundle_context(
            tenant="tenant-1", community="1", app_id="waddles.community.chat.default"
        ):
            result = await transform(_event("please !chat-history for me"))
        assert result is None

    async def test_reply_preserves_platform_metadata(self, _dal: _FakeDal) -> None:
        """Response preserves platform, event_type, actor, occurred_at."""
        _dal.add_channel("general", message_count=5, last_message_at="2026-01-01T12:00:00Z")
        with bundle_context(
            tenant="tenant-1", community="1", app_id="waddles.community.chat.default"
        ):
            result = await transform(_event("!channels"))
        assert result is not None
        assert result.platform == "discord"
        assert result.event_type == "message"
        assert result.actor == "test_user"
        assert result.occurred_at == "2026-01-01T00:00:00+00:00"


class TestFormatChatHistory:
    """Tests for _format_chat_history helper."""

    def test_empty_list(self) -> None:
        """Empty message list returns placeholder."""
        result = _format_chat_history([])
        assert result == "(no messages found)"

    def test_single_message(self) -> None:
        """Single message is formatted correctly."""
        msg = ChatMessage(
            id=1,
            community_id=1,
            channel_name="general",
            sender_username="alice",
            content="hello world",
            message_type="text",
            created_at="2026-01-01T12:00:00",
        )
        result = _format_chat_history([msg])
        assert "Chat History" in result
        assert "alice" in result
        assert "hello world" in result
        assert "2026-01-01" in result

    def test_multiple_messages(self) -> None:
        """Multiple messages are all included (up to limit)."""
        msgs = [
            ChatMessage(
                id=i,
                community_id=1,
                channel_name="general",
                sender_username=f"user{i}",
                content=f"message {i}",
                message_type="text",
                created_at="2026-01-01T12:00:00",
            )
            for i in range(5)
        ]
        result = _format_chat_history(msgs)
        for i in range(5):
            assert f"user{i}" in result

    def test_truncates_long_messages(self) -> None:
        """Long message content is truncated in output."""
        msg = ChatMessage(
            id=1,
            community_id=1,
            channel_name="general",
            sender_username="alice",
            content="x" * 200,
            message_type="text",
            created_at="2026-01-01T12:00:00",
        )
        result = _format_chat_history([msg])
        assert len(result) < 4100  # must fit in platform limit

    def test_truncates_entire_output_if_too_long(self) -> None:
        """Entire output is capped at ~4000 chars."""
        msgs = [
            ChatMessage(
                id=i,
                community_id=1,
                channel_name="general",
                sender_username=f"very_long_username_{i}",
                content="message content " * 10,
                message_type="text",
                created_at="2026-01-01T12:00:00",
            )
            for i in range(50)
        ]
        result = _format_chat_history(msgs)
        assert len(result) <= 4100

    def test_missing_created_at(self) -> None:
        """Message with None created_at renders gracefully."""
        msg = ChatMessage(
            id=1,
            community_id=1,
            channel_name="general",
            sender_username="alice",
            content="hello",
            message_type="text",
            created_at=None,
        )
        result = _format_chat_history([msg])
        assert "?" in result  # placeholder for missing timestamp

    def test_missing_sender_username(self) -> None:
        """Message with None sender_username renders as 'unknown'."""
        msg = ChatMessage(
            id=1,
            community_id=1,
            channel_name="general",
            sender_username=None,
            content="hello",
            message_type="text",
            created_at="2026-01-01T12:00:00",
        )
        result = _format_chat_history([msg])
        assert "unknown" in result


class TestFormatChannels:
    """Tests for _format_channels helper."""

    def test_empty_list(self) -> None:
        """Empty channel list returns placeholder."""
        result = _format_channels([])
        assert result == "(no channels found)"

    def test_single_channel(self) -> None:
        """Single channel is formatted correctly."""
        ch = ChatChannel(name="general", message_count=42, last_message_at="2026-01-01T12:00:00")
        result = _format_channels([ch])
        assert "Chat Channels" in result
        assert "general" in result
        assert "42" in result

    def test_multiple_channels(self) -> None:
        """Multiple channels are all listed."""
        channels = [
            ChatChannel(name="general", message_count=100, last_message_at="2026-01-01T12:00:00"),
            ChatChannel(name="random", message_count=50, last_message_at="2026-01-01T11:00:00"),
            ChatChannel(
                name="announcements", message_count=10, last_message_at="2026-01-01T10:00:00"
            ),
        ]
        result = _format_channels(channels)
        for ch in channels:
            assert ch.name in result

    def test_truncates_if_too_long(self) -> None:
        """Output is capped at ~4000 chars if needed."""
        channels = [
            ChatChannel(
                name=f"channel_with_a_very_long_name_{i}",
                message_count=1000000,
                last_message_at="2026-01-01T12:00:00",
            )
            for i in range(100)
        ]
        result = _format_channels(channels)
        assert len(result) <= 4100
