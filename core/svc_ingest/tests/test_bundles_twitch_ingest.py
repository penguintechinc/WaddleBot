"""Tests for `bundles.twitch_ingest.normalize` -- raw Twitch chat event -> `PlatformEvent`."""

from __future__ import annotations

import pytest
from flask_core import PlatformEvent

from bundles.twitch_ingest import normalize


async def test_normalizes_a_real_chat_message() -> None:
    raw = {
        "platform": "twitch",
        "channel_name": "waddlebot",
        "author_username": "alice",
        "content": "  hello chat  ",
    }
    event = await normalize(raw)

    assert isinstance(event, PlatformEvent)
    assert event.platform == "twitch"
    assert event.event_type == "message"
    assert event.actor == "alice"
    assert event.payload["text"] == "hello chat"
    assert event.payload["channel_name"] == "waddlebot"
    assert event.payload["author"] == "alice"
    assert event.occurred_at


async def test_falls_back_to_unknown_when_sender_missing() -> None:
    raw = {"channel_name": "waddlebot", "content": "hi"}
    event = await normalize(raw)
    assert event.actor == "unknown"
    assert event.payload["author"] == "unknown"


async def test_missing_content_raises() -> None:
    with pytest.raises(ValueError, match="content"):
        await normalize({"channel_name": "waddlebot"})


async def test_missing_channel_name_raises() -> None:
    with pytest.raises(ValueError, match="channel_name"):
        await normalize({"content": "hi"})


async def test_preserves_supplied_occurred_at() -> None:
    raw = {
        "channel_name": "waddlebot",
        "content": "hi",
        "occurred_at": "2026-01-01T00:00:00+00:00",
    }
    event = await normalize(raw)
    assert event.occurred_at == "2026-01-01T00:00:00+00:00"
