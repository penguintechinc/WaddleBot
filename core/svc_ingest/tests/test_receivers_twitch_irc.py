"""Tests for `receivers.twitch_irc.TwitchIrcReceiver`.

Real `twitchio.ext.commands.Bot` subclass instance (constructing one does
not open a network connection -- only `bot.start()` does, same precedent
`receivers/discord_gateway.py`'s own tests document for py-cord), duck-
typed fake `twitchio.Message`/`Author`/`Channel` objects (twitchio's own
`Message` needs live IRC state to construct, so a fake with just the
attributes this receiver reads is the standard testing pattern), and a
real `fakeredis` round trip for the fan-out + outbound-relay assertions --
no mocked IRC connection is ever opened.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock

from flask_core.app_registry import AppRegistry
from flask_core.stream_pipeline import bundle_stream_key
from waddle_transports.irc import outbound_queue_key

from bundles.twitch_gateway_manifest import register_default_bundles
from receivers.twitch_irc import TwitchIrcReceiver

TENANT = "acme-corp"
APP_ID = "waddles.bot.twitch.gateway"


@dataclass
class _FakeAuthor:
    id: int
    name: str
    display_name: str = ""
    is_mod: bool = False
    is_subscriber: bool = False


@dataclass
class _FakeChannel:
    name: str

    async def send(self, text: str) -> None:  # pragma: no cover - overridden per-test as needed
        pass


@dataclass
class _FakeMessage:
    id: str
    author: _FakeAuthor | None
    channel: _FakeChannel | None
    content: str
    echo: bool = False


def _make_receiver(redis_client: Any, registry: AppRegistry | None = None) -> TwitchIrcReceiver:
    reg = registry if registry is not None else AppRegistry()
    if not reg.all_apps():
        register_default_bundles(reg)
    return TwitchIrcReceiver(
        token="oauth:fake-token-not-a-real-twitch-token",  # noqa: S106 - test literal
        nick="waddlebot",
        channels=["waddlebot"],
        redis_client=redis_client,
        registry=reg,
        tenant_slug=TENANT,
    )


class TestHandleMessage:
    async def test_echoed_message_is_ignored(self, redis_client: Any) -> None:
        receiver = _make_receiver(redis_client)
        message = _FakeMessage(
            id="1",
            author=_FakeAuthor(id=999, name="waddlebot"),
            channel=_FakeChannel(name="waddlebot"),
            content="I am the bot",
            echo=True,
        )
        await receiver._handle_message(message)  # noqa: SLF001 - exercising the real handler

        ingest_key = bundle_stream_key(TENANT, "waddlebot", APP_ID, "ingest")
        assert await redis_client.rpop(ingest_key) is None

    async def test_human_chat_message_fans_out_to_the_twitch_ingest_bundle(
        self, redis_client: Any
    ) -> None:
        receiver = _make_receiver(redis_client)
        message = _FakeMessage(
            id="123",
            author=_FakeAuthor(id=555, name="alice", display_name="Alice", is_subscriber=True),
            channel=_FakeChannel(name="waddlebot"),
            content="hello waddlebot",
        )
        await receiver._handle_message(message)  # noqa: SLF001

        ingest_key = bundle_stream_key(TENANT, "waddlebot", APP_ID, "ingest")
        raw = await redis_client.rpop(ingest_key)
        assert raw is not None
        event = json.loads(raw)
        assert event == {
            "platform": "twitch",
            "channel_name": "waddlebot",
            "message_id": "123",
            "author_id": "555",
            "author_username": "alice",
            "author_display_name": "Alice",
            "content": "hello waddlebot",
            "is_mod": False,
            "is_subscriber": True,
            "is_broadcaster": False,
        }

    async def test_broadcaster_message_is_flagged(self, redis_client: Any) -> None:
        receiver = _make_receiver(redis_client)
        message = _FakeMessage(
            id="124",
            author=_FakeAuthor(id=1, name="waddlebot_owner"),
            channel=_FakeChannel(name="waddlebot_owner"),
            content="mod command",
        )
        await receiver._handle_message(message)  # noqa: SLF001

        ingest_key = bundle_stream_key(TENANT, "waddlebot_owner", APP_ID, "ingest")
        event = json.loads(await redis_client.rpop(ingest_key))
        assert event["is_broadcaster"] is True

    async def test_fanout_failure_does_not_propagate(self, redis_client: Any) -> None:
        """One bad event must never kill the IRC connection -- `_handle_message` swallows."""

        class _BrokenRedis:
            async def lpush(self, key: str, value: str) -> None:
                raise ConnectionError("valkey unreachable")

        receiver = _make_receiver(_BrokenRedis())
        message = _FakeMessage(
            id="125",
            author=_FakeAuthor(id=555, name="alice"),
            channel=_FakeChannel(name="waddlebot"),
            content="hello",
        )
        await receiver._handle_message(message)  # noqa: SLF001 - must not raise


class TestOutboundDrain:
    async def test_send_one_delivers_through_the_matching_channel(self, redis_client: Any) -> None:
        receiver = _make_receiver(redis_client)
        sent: list[str] = []

        class _RecordingChannel(_FakeChannel):
            async def send(self, text: str) -> None:
                sent.append(text)

        fake_channel = _RecordingChannel(name="waddlebot")
        receiver.bot.get_channel = lambda name: fake_channel if name == "waddlebot" else None  # type: ignore[method-assign]

        await receiver._send_one(json.dumps({"channel": "waddlebot", "text": "hi chat"}))  # noqa: SLF001

        assert sent == ["hi chat"]

    async def test_send_one_unknown_channel_is_a_noop(self, redis_client: Any) -> None:
        receiver = _make_receiver(redis_client)
        receiver.bot.get_channel = lambda name: None  # type: ignore[method-assign]

        await receiver._send_one(json.dumps({"channel": "nope", "text": "hi"}))  # noqa: SLF001 - must not raise

    async def test_send_one_malformed_payload_is_a_noop(self, redis_client: Any) -> None:
        receiver = _make_receiver(redis_client)
        await receiver._send_one("not json")  # noqa: SLF001 - must not raise

    async def test_drain_outbound_relays_a_queued_message_end_to_end(
        self, redis_client: Any
    ) -> None:
        """Fail-first proof: a message relayed via `outbound_queue_key` is delivered.

        By the receiver's own drain loop -- the same queue `bundles/
        twitch_send_action.py` LPUSHes onto from svc-action.
        """
        receiver = _make_receiver(redis_client)
        sent: list[tuple[str, str]] = []

        class _RecordingChannel(_FakeChannel):
            async def send(self, text: str) -> None:
                sent.append((self.name, text))

        receiver.bot.get_channel = lambda name: _RecordingChannel(name=name)  # type: ignore[method-assign]

        await redis_client.lpush(
            outbound_queue_key("twitch"), json.dumps({"channel": "waddlebot", "text": "relayed!"})
        )

        receiver._running = True  # noqa: SLF001
        import asyncio

        task = asyncio.ensure_future(receiver._drain_outbound())  # noqa: SLF001
        await asyncio.sleep(0.05)
        receiver._running = False  # noqa: SLF001
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        assert sent == [("waddlebot", "relayed!")]


class TestRunStop:
    async def test_run_delegates_to_bot_start_and_stops_the_drain_loop(
        self, redis_client: Any
    ) -> None:
        receiver = _make_receiver(redis_client)
        receiver.bot.start = AsyncMock()  # type: ignore[method-assign]

        await receiver.run()

        receiver.bot.start.assert_awaited_once()
        assert receiver._outbound_task is not None  # noqa: SLF001
        assert receiver._outbound_task.cancelled() or receiver._outbound_task.done()  # noqa: SLF001

    async def test_stop_closes_the_bot(self, redis_client: Any) -> None:
        receiver = _make_receiver(redis_client)
        receiver.bot.close = AsyncMock()  # type: ignore[method-assign]

        await receiver.stop()

        receiver.bot.close.assert_awaited_once()

    async def test_stop_swallows_close_errors(self, redis_client: Any) -> None:
        receiver = _make_receiver(redis_client)
        receiver.bot.close = AsyncMock(side_effect=RuntimeError("already closed"))  # type: ignore[method-assign]

        await receiver.stop()  # must not raise
