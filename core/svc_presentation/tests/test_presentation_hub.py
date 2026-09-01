"""`PresentationHub` -- local fan-out, fallback mode, and the Valkey pub/sub relay path."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest

from services.presentation_hub import PresentationHub, _channel, _parse_channel


def test_channel_naming_roundtrips() -> None:
    """`_channel`/`_parse_channel` are inverses -- the relay loop depends on this."""
    channel = _channel("acme", "full_screen")
    assert channel == "presentation:acme:full_screen"
    assert _parse_channel(channel) == ("acme", "full_screen")


def test_parse_channel_rejects_malformed_names() -> None:
    """A channel outside this hub's own naming convention is ignored, not mis-routed."""
    assert _parse_channel("something:else") is None
    assert _parse_channel("not-presentation:a:b") is None


@pytest.mark.asyncio
async def test_fallback_mode_when_no_valkey_url() -> None:
    """No `valkey_url` configured -- `start()` leaves the hub in fallback mode, never crashes."""
    hub = PresentationHub(valkey_url=None)
    await hub.start()
    assert hub.fallback_mode is True
    await hub.stop()


@pytest.mark.asyncio
async def test_register_publish_deliver_fallback() -> None:
    """Fallback mode: `publish()` delivers directly into every registered local queue."""
    hub = PresentationHub(valkey_url=None)
    await hub.start()

    queue = hub.register("acme", "media")
    assert hub.local_subscriber_count("acme", "media") == 1

    await hub.publish("acme", "media", {"title": "hello"})
    delivered = await asyncio.wait_for(queue.get(), timeout=1)
    assert delivered == {"title": "hello"}

    hub.unregister("acme", "media", queue)
    assert hub.local_subscriber_count("acme", "media") == 0


@pytest.mark.asyncio
async def test_publish_does_not_cross_deliver_other_surfaces() -> None:
    """A publish to `crawler` never lands in a `media` subscriber's queue."""
    hub = PresentationHub(valkey_url=None)
    await hub.start()

    media_queue = hub.register("acme", "media")
    crawler_queue = hub.register("acme", "crawler")

    await hub.publish("acme", "crawler", {"text": "breaking news"})

    delivered = await asyncio.wait_for(crawler_queue.get(), timeout=1)
    assert delivered == {"text": "breaking news"}
    assert media_queue.empty()


class _FakePubSub:
    """Stand-in for `redis.asyncio.Redis().pubsub()` -- yields one canned pmessage then blocks."""

    def __init__(self, messages: list[dict[str, Any]]) -> None:
        self._messages = messages
        self._closed = asyncio.Event()

    async def psubscribe(self, pattern: str) -> None:
        return None

    async def listen(self) -> Any:
        for message in self._messages:
            yield message
        await self._closed.wait()  # block "forever" until the test cancels the listener task

    async def close(self) -> None:
        self._closed.set()


class _FakeRedisClient:
    """Stand-in for `redis.asyncio.Redis` -- records every `publish()` call."""

    def __init__(self, pubsub: _FakePubSub) -> None:
        self._pubsub_obj = pubsub
        self.published: list[tuple[str, str]] = []

    async def ping(self) -> bool:
        return True

    def pubsub(self) -> _FakePubSub:
        return self._pubsub_obj

    async def publish(self, channel: str, message: str) -> None:
        self.published.append((channel, message))

    async def close(self) -> None:
        return None


@pytest.mark.asyncio
async def test_connected_mode_publishes_to_valkey_not_direct_local_delivery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Connected mode: `publish()` calls the Valkey client, mocked here -- no direct local write."""
    fake_pubsub = _FakePubSub(messages=[])
    fake_client = _FakeRedisClient(fake_pubsub)

    hub = PresentationHub(valkey_url="redis://fake:6379/0")

    class _FakeRedisModule:
        @staticmethod
        def from_url(*_args: Any, **_kwargs: Any) -> _FakeRedisClient:
            return fake_client

    monkeypatch.setattr("services.presentation_hub.redis_asyncio", _FakeRedisModule())
    monkeypatch.setattr("services.presentation_hub.REDIS_AVAILABLE", True)

    await hub.start()
    assert hub.fallback_mode is False

    queue = hub.register("acme", "full_screen")
    await hub.publish("acme", "full_screen", {"title": "pushed via valkey"})

    # publish() goes to the mocked Valkey client, not a direct local write --
    # the local queue only gets a message via the relay loop (exercised
    # separately below), so it must still be empty right after publish().
    assert queue.empty()
    assert fake_client.published == [
        ("presentation:acme:full_screen", json.dumps({"title": "pushed via valkey"}))
    ]

    await hub.stop()


@pytest.mark.asyncio
async def test_start_connect_failure_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    """`ping()` raising (broker unreachable) -- `fallback_mode` stays True, never crashes."""

    class _BrokenRedis:
        async def ping(self) -> bool:
            raise ConnectionError("no route to host")

    class _FakeRedisModule:
        @staticmethod
        def from_url(*_args: Any, **_kwargs: Any) -> _BrokenRedis:
            return _BrokenRedis()

    monkeypatch.setattr("services.presentation_hub.redis_asyncio", _FakeRedisModule())
    monkeypatch.setattr("services.presentation_hub.REDIS_AVAILABLE", True)

    hub = PresentationHub(valkey_url="redis://fake:6379/0")
    await hub.start()
    assert hub.fallback_mode is True


@pytest.mark.asyncio
async def test_relay_loop_skips_non_pmessage_malformed_channel_and_bad_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The relay loop tolerates a subscribe-confirmation frame, a bad channel, and bad JSON."""
    canned_messages = [
        {"type": "psubscribe", "pattern": "presentation:*:*", "channel": None, "data": 1},
        {"type": "pmessage", "channel": "not-presentation:a:b", "data": "{}"},
        {"type": "pmessage", "channel": "presentation:acme:media", "data": "{not json"},
        {
            "type": "pmessage",
            "channel": "presentation:acme:media",
            "data": json.dumps({"ok": True}),
        },
    ]
    fake_pubsub = _FakePubSub(messages=canned_messages)
    fake_client = _FakeRedisClient(fake_pubsub)

    hub = PresentationHub(valkey_url="redis://fake:6379/0")

    class _FakeRedisModule:
        @staticmethod
        def from_url(*_args: Any, **_kwargs: Any) -> _FakeRedisClient:
            return fake_client

    monkeypatch.setattr("services.presentation_hub.redis_asyncio", _FakeRedisModule())
    monkeypatch.setattr("services.presentation_hub.REDIS_AVAILABLE", True)

    queue = hub.register("acme", "media")
    await hub.start()

    # Only the final, well-formed pmessage should ever reach the queue.
    delivered = await asyncio.wait_for(queue.get(), timeout=2)
    assert delivered == {"ok": True}
    assert queue.empty()

    await hub.stop()


@pytest.mark.asyncio
async def test_deliver_local_drops_silently_when_queue_full() -> None:
    """A full subscriber queue (`maxsize=64`) never raises out of `publish()` -- it just logs."""
    hub = PresentationHub(valkey_url=None)
    await hub.start()
    queue = hub.register("acme", "media")
    for _ in range(64):
        queue.put_nowait({"i": 0})

    await hub.publish("acme", "media", {"one": "too many"})  # must not raise
    assert queue.full()


@pytest.mark.asyncio
async def test_relay_loop_delivers_pmessage_to_local_subscribers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The background relay loop, fed a mocked Valkey pmessage, fans it out locally."""
    canned_message = {
        "type": "pmessage",
        "pattern": "presentation:*:*",
        "channel": "presentation:acme:media",
        "data": json.dumps({"title": "from relay"}),
    }
    fake_pubsub = _FakePubSub(messages=[canned_message])
    fake_client = _FakeRedisClient(fake_pubsub)

    hub = PresentationHub(valkey_url="redis://fake:6379/0")

    class _FakeRedisModule:
        @staticmethod
        def from_url(*_args: Any, **_kwargs: Any) -> _FakeRedisClient:
            return fake_client

    monkeypatch.setattr("services.presentation_hub.redis_asyncio", _FakeRedisModule())
    monkeypatch.setattr("services.presentation_hub.REDIS_AVAILABLE", True)

    # Registered before start() so the relay task can never observe the
    # canned pmessage before a subscriber exists to deliver it to --
    # eliminates a scheduling race against asyncio.create_task() in start().
    queue = hub.register("acme", "media")
    await hub.start()

    delivered = await asyncio.wait_for(queue.get(), timeout=2)
    assert delivered == {"title": "from relay"}

    await hub.stop()
