"""`MusicQueueReader` -- direct unit tests for the Valkey-backed queue parse logic."""

from __future__ import annotations

import json

import pytest

from services.queue_reader import MusicQueueReader


class _FakeRedis:
    def __init__(self, stored: dict[str, str]) -> None:
        self._stored = stored

    async def get(self, key: str) -> str | None:
        return self._stored.get(key)

    async def ping(self) -> bool:
        return True

    async def close(self) -> None:
        return None


@pytest.mark.asyncio
async def test_start_without_valkey_url_stays_disconnected() -> None:
    """No URL configured -- `connected` stays False, `get_queue` returns an empty list."""
    reader = MusicQueueReader(valkey_url=None)
    await reader.start()
    assert reader.connected is False
    assert await reader.get_queue("1") == []
    await reader.stop()


@pytest.mark.asyncio
async def test_get_queue_filters_out_played_and_skipped() -> None:
    """Only `queued`/`playing` statuses surface -- `played`/`skipped` are history, not the queue."""
    reader = MusicQueueReader(valkey_url="redis://fake", namespace="music_queue_test")
    items = [
        {
            "id": "q1",
            "track": {
                "track_id": "t1",
                "name": "A",
                "artist": "X",
                "provider": "youtube",
                "album_art_url": "",
                "duration_ms": 1000,
                "uri": "",
            },
            "position": 0,
            "status": "played",
            "votes": 0,
        },
        {
            "id": "q2",
            "track": {
                "track_id": "t2",
                "name": "B",
                "artist": "Y",
                "provider": "youtube",
                "album_art_url": "",
                "duration_ms": 1000,
                "uri": "",
            },
            "position": 1,
            "status": "skipped",
            "votes": 0,
        },
        {
            "id": "q3",
            "track": {
                "track_id": "t3",
                "name": "C",
                "artist": "Z",
                "provider": "youtube",
                "album_art_url": "",
                "duration_ms": 1000,
                "uri": "",
            },
            "position": 2,
            "status": "queued",
            "votes": 0,
        },
    ]
    reader._redis = _FakeRedis({"music_queue_test:1:queue": json.dumps(items)})  # type: ignore[attr-defined]
    reader.connected = True

    tracks = await reader.get_queue("1")
    assert [t.queue_id for t in tracks] == ["q3"]


@pytest.mark.asyncio
async def test_get_queue_sorts_by_position() -> None:
    """Out-of-order raw entries are returned sorted by `position`."""
    reader = MusicQueueReader(valkey_url="redis://fake", namespace="music_queue_test")
    items = [
        {
            "id": "q-second",
            "track": {
                "track_id": "t2",
                "name": "B",
                "artist": "Y",
                "provider": "youtube",
                "album_art_url": "",
                "duration_ms": 1000,
                "uri": "",
            },
            "position": 1,
            "status": "queued",
            "votes": 0,
        },
        {
            "id": "q-first",
            "track": {
                "track_id": "t1",
                "name": "A",
                "artist": "X",
                "provider": "spotify",
                "album_art_url": "",
                "duration_ms": 1000,
                "uri": "",
            },
            "position": 0,
            "status": "playing",
            "votes": 0,
        },
    ]
    reader._redis = _FakeRedis({"music_queue_test:2:queue": json.dumps(items)})  # type: ignore[attr-defined]
    reader.connected = True

    tracks = await reader.get_queue("2")
    assert [t.queue_id for t in tracks] == ["q-first", "q-second"]


@pytest.mark.asyncio
async def test_get_queue_handles_missing_key() -> None:
    """No key in Valkey for this community -- empty queue, not an error."""
    reader = MusicQueueReader(valkey_url="redis://fake", namespace="music_queue_test")
    reader._redis = _FakeRedis({})  # type: ignore[attr-defined]
    reader.connected = True

    assert await reader.get_queue("999") == []


@pytest.mark.asyncio
async def test_get_queue_handles_malformed_json() -> None:
    """Corrupt JSON at the key -- logged and treated as empty, never a 500."""
    reader = MusicQueueReader(valkey_url="redis://fake", namespace="music_queue_test")
    reader._redis = _FakeRedis({"music_queue_test:3:queue": "{not json"})  # type: ignore[attr-defined]
    reader.connected = True

    assert await reader.get_queue("3") == []


@pytest.mark.asyncio
async def test_start_connects_successfully(monkeypatch: pytest.MonkeyPatch) -> None:
    """A reachable Valkey URL -- `start()` pings it and flips `connected` True."""
    fake_client = _FakeRedis({})

    class _FakeRedisModule:
        @staticmethod
        def from_url(*_args: object, **_kwargs: object) -> _FakeRedis:
            return fake_client

    monkeypatch.setattr("services.queue_reader.redis_asyncio", _FakeRedisModule())
    monkeypatch.setattr("services.queue_reader.REDIS_AVAILABLE", True)

    reader = MusicQueueReader(valkey_url="redis://fake:6379/0")
    await reader.start()
    assert reader.connected is True
    await reader.stop()


@pytest.mark.asyncio
async def test_start_connection_failure_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    """`ping()` raising (broker unreachable) -- `connected` stays False, never crashes startup."""

    class _BrokenRedis:
        async def ping(self) -> bool:
            raise ConnectionError("no route to host")

    class _FakeRedisModule:
        @staticmethod
        def from_url(*_args: object, **_kwargs: object) -> _BrokenRedis:
            return _BrokenRedis()

    monkeypatch.setattr("services.queue_reader.redis_asyncio", _FakeRedisModule())
    monkeypatch.setattr("services.queue_reader.REDIS_AVAILABLE", True)

    reader = MusicQueueReader(valkey_url="redis://fake:6379/0")
    await reader.start()
    assert reader.connected is False


@pytest.mark.asyncio
async def test_get_queue_read_failure_returns_empty() -> None:
    """A transient Valkey error on `get()` -- logged and treated as empty, never a 500."""

    class _FlakyRedis:
        async def get(self, _key: str) -> str:
            raise TimeoutError("valkey read timed out")

    reader = MusicQueueReader(valkey_url="redis://fake", namespace="music_queue_test")
    reader._redis = _FlakyRedis()  # type: ignore[attr-defined]
    reader.connected = True

    assert await reader.get_queue("4") == []
