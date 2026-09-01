"""Tests for `bundles.echo_process.transform` -- the demo process entrypoint."""

from __future__ import annotations

import pytest

from bundles.echo_process import transform


class TestTransform:
    async def test_transforms_valid_event(self) -> None:
        event = {
            "platform": "twitch",
            "event_type": "message",
            "actor": "penguin",
            "payload": {"text": "hello world"},
            "occurred_at": "2026-01-01T00:00:00+00:00",
        }
        result = await transform(event)
        assert result["payload"]["text"] == "HELLO WORLD"
        assert result["payload"]["word_count"] == 2
        assert result["processed"] is True
        assert result["platform"] == "twitch"  # non-payload fields preserved

    async def test_missing_payload_raises(self) -> None:
        with pytest.raises(ValueError, match="payload"):
            await transform({"platform": "twitch"})

    async def test_missing_text_raises(self) -> None:
        with pytest.raises(ValueError, match="text"):
            await transform({"payload": {}})

    async def test_preserves_other_payload_fields(self) -> None:
        event = {"payload": {"text": "hi there", "extra": "keep-me"}}
        result = await transform(event)
        assert result["payload"]["extra"] == "keep-me"
        assert result["payload"]["word_count"] == 2
