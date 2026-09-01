"""Music Station player page + its `/music/queue` JSON read."""

from __future__ import annotations

import json
from typing import Any

import pytest
from quart.typing import TestClientProtocol

from services.queue_reader import MusicQueueReader


class _FakeRedis:
    """Minimal stand-in for `redis.asyncio.Redis` -- just enough for `get_queue()`."""

    def __init__(self, stored: dict[str, str]) -> None:
        self._stored = stored

    async def get(self, key: str) -> str | None:
        return self._stored.get(key)

    async def ping(self) -> bool:
        return True

    async def close(self) -> None:
        return None


def _queue_payload(
    *, queue_id: str, provider: str, track_id: str, status: str, position: int
) -> dict[str, Any]:
    """Build one `QueueItem.to_dict()`-shaped entry, matching `UnifiedQueue`'s real wire schema."""
    return {
        "id": queue_id,
        "track": {
            "track_id": track_id,
            "name": f"Track {track_id}",
            "artist": "Test Artist",
            "album": "Test Album",
            "album_art_url": "https://example.com/art.jpg",
            "duration_ms": 210000,
            "provider": provider,
            "uri": f"https://example.com/{provider}/{track_id}",
            "metadata": {},
        },
        "requested_by_user_id": "user-uuid-1",
        "requested_at": "2026-08-31T00:00:00",
        "votes": 0,
        "position": position,
        "status": status,
        "community_id": 99,
        "voters": [],
    }


@pytest.mark.asyncio
async def test_music_page_renders_html_with_live_bootstrap(client: TestClientProtocol) -> None:
    """The Music Station page is real HTML with the YouTube IFrame API + poll loop wired in."""
    response = await client.get("/overlay/testcommunity/music")
    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("text/html")
    body = await response.get_data(as_text=True)
    assert "<!DOCTYPE html>" in body
    assert "youtube.com/iframe_api" in body
    assert "/overlay/${community}/music/queue" in body
    assert "testcommunity" in body


@pytest.mark.asyncio
async def test_queue_endpoint_empty_when_no_valkey_data(client: TestClientProtocol) -> None:
    """No Valkey configured in tests -- an honestly empty queue, not fake data."""
    response = await client.get("/overlay/testcommunity/music/queue")
    assert response.status_code == 200
    payload = await response.get_json()
    assert payload["now_playing"] is None
    assert payload["upcoming"] == []


@pytest.mark.asyncio
async def test_queue_endpoint_renders_now_playing_and_upcoming(
    client: TestClientProtocol,
) -> None:
    """A real Valkey-shaped payload parses into now_playing/upcoming with provider+external_id."""
    items = [
        _queue_payload(
            queue_id="q1",
            provider="spotify",
            track_id="spotify123",
            status="playing",
            position=0,
        ),
        _queue_payload(
            queue_id="q2",
            provider="youtube",
            track_id="ytABC",
            status="queued",
            position=1,
        ),
    ]
    fake_redis = _FakeRedis({"music_queue_test:99:queue": json.dumps(items)})
    reader: MusicQueueReader = client.app.config["MUSIC_QUEUE_READER"]
    reader._redis = fake_redis  # type: ignore[attr-defined]
    reader.connected = True

    response = await client.get("/overlay/99/music/queue")
    assert response.status_code == 200
    payload = await response.get_json()

    assert payload["now_playing"]["queue_id"] == "q1"
    assert payload["now_playing"]["provider"] == "spotify"
    assert payload["now_playing"]["external_id"] == "spotify123"
    assert len(payload["upcoming"]) == 1
    assert payload["upcoming"][0]["provider"] == "youtube"
    assert payload["upcoming"][0]["external_id"] == "ytABC"


@pytest.mark.asyncio
async def test_queue_endpoint_head_of_queue_when_nothing_playing(
    client: TestClientProtocol,
) -> None:
    """No track explicitly `playing` yet -- the head of the queue fills now_playing."""
    items = [
        _queue_payload(
            queue_id="q1",
            provider="soundcloud",
            track_id="sc1",
            status="queued",
            position=0,
        ),
    ]
    fake_redis = _FakeRedis({"music_queue_test:5:queue": json.dumps(items)})
    reader: MusicQueueReader = client.app.config["MUSIC_QUEUE_READER"]
    reader._redis = fake_redis  # type: ignore[attr-defined]
    reader.connected = True

    response = await client.get("/overlay/5/music/queue")
    payload = await response.get_json()
    assert payload["now_playing"]["queue_id"] == "q1"
    assert payload["now_playing"]["provider"] == "soundcloud"
    assert payload["upcoming"] == []


@pytest.mark.asyncio
async def test_music_page_invalid_community_rejected(client: TestClientProtocol) -> None:
    """Same slug validation as the core overlay surfaces."""
    response = await client.get("/overlay/%3Cscript%3E/music")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_queue_endpoint_invalid_community_rejected(client: TestClientProtocol) -> None:
    """Same slug validation applied to the JSON queue endpoint."""
    response = await client.get("/overlay/%3Cscript%3E/music/queue")
    assert response.status_code == 400
