"""Tests for `bundles.twitch_ingest.normalize` -- raw Twitch chat event -> platform event shape."""

from __future__ import annotations

import pytest

from bundles.twitch_ingest import normalize


async def test_normalizes_a_real_chat_message() -> None:
    raw = {
        "platform": "twitch",
        "channel_name": "waddlebot",
        "message_id": "abc-123",
        "author_id": "555",
        "author_username": "alice",
        "author_display_name": "Alice",
        "content": "  hello chat  ",
        "is_mod": False,
        "is_subscriber": True,
        "is_broadcaster": False,
    }
    event = await normalize(raw)

    assert event["platform"] == "twitch"
    assert event["event_type"] == "message"
    assert event["actor"] == "alice"
    assert event["payload"]["text"] == "hello chat"
    assert event["payload"]["channel_name"] == "waddlebot"
    assert event["payload"]["is_subscriber"] is True
    assert "occurred_at" in event


async def test_falls_back_to_author_id_when_username_missing() -> None:
    raw = {"channel_name": "waddlebot", "content": "hi", "author_id": "555"}
    event = await normalize(raw)
    assert event["actor"] == "555"


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
    assert event["occurred_at"] == "2026-01-01T00:00:00+00:00"
