"""Tests for `receivers.twitch_irc.TwitchIrcReceiver`.

`IrcTransport.receive()` is monkeypatched to a fake async generator --
the real transport opens a genuine TCP/TLS socket, which this unit suite
never does (matches `waddle_transports`' own test suite precedent of
exercising the wire protocol against a local `asyncio` server, out of
scope for THIS container's tests, which only need to prove the
normalize + fan-out + supervisor-compatible `run()`/`stop()` wiring).
`redis_client` (from `conftest.py`) is a real `fakeredis.FakeAsyncRedis`
-- genuine LPUSH/RPOP round trip for the fan-out assertions.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Mapping
from typing import Any

import pytest
from flask_core.app_registry import AppRegistry
from flask_core.stream_pipeline import bundle_stream_key
from waddle_transports import Direction

from bundles.twitch_gateway_manifest import register_default_bundles
from receivers.twitch_irc import TwitchIrcReceiver

TENANT = "acme-corp"
APP_ID = "waddles.bot.twitch.gateway"


def _make_receiver(
    redis_client: Any, registry: AppRegistry | None = None, *, channel: str = "waddlebot"
) -> TwitchIrcReceiver:
    reg = registry if registry is not None else AppRegistry()
    if not reg.all_apps():
        register_default_bundles(reg)
    return TwitchIrcReceiver(
        irc_config={
            "host": "irc.chat.twitch.tv",
            "port": 6697,
            "nick": "waddlebot",
            "channel": channel,
            "password_ref": "TEST_TWITCH_TOKEN_REF",
        },
        redis_client=redis_client,
        registry=reg,
        tenant_slug=TENANT,
    )


async def _fake_privmsgs(*items: Mapping[str, str]) -> AsyncIterator[Mapping[str, str]]:
    for item in items:
        yield item


class TestTransportShape:
    def test_declares_inbound_irc(self, redis_client: Any) -> None:
        receiver = _make_receiver(redis_client)
        assert receiver.name == "twitch_irc"
        assert receiver.directions == frozenset({Direction.INBOUND})

    def test_channel_property_reflects_config(self, redis_client: Any) -> None:
        receiver = _make_receiver(redis_client, channel="othershow")
        assert receiver.channel == "othershow"


class TestNormalize:
    """`TwitchIrcReceiver.receive()`'s own normalization, isolated from the real IRC socket."""

    async def test_normalizes_raw_irc_transport_output(
        self, redis_client: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        receiver = _make_receiver(redis_client)
        raw_privmsg = {"channel": "#waddlebot", "sender": "alice", "text": "hi"}
        monkeypatch.setattr(
            receiver._irc,  # noqa: SLF001 - test override of the real IrcTransport instance
            "receive",
            lambda config: _fake_privmsgs(raw_privmsg),
        )

        events = [event async for event in receiver.receive({"channel": "waddlebot"})]

        assert events == [
            {
                "platform": "twitch",
                "channel_name": "waddlebot",
                "author_username": "alice",
                "content": "hi",
            }
        ]


class TestHandleMessage:
    async def test_fans_out_at_community_none(self, redis_client: Any) -> None:
        """T9 (2026-09-03): every Twitch event fans out at community=None for the demo."""
        receiver = _make_receiver(redis_client)
        event = {
            "platform": "twitch",
            "channel_name": "waddlebot",
            "author_username": "alice",
            "content": "hello waddlebot",
        }
        await receiver._handle_message(event)  # noqa: SLF001 - exercising the real handler

        ingest_key = bundle_stream_key(TENANT, None, APP_ID, "ingest")
        raw = await redis_client.rpop(ingest_key)
        assert raw is not None
        assert json.loads(raw) == event

    async def test_fanout_failure_does_not_propagate(self, redis_client: Any) -> None:
        """One bad event must never kill the connection -- `_handle_message` swallows."""

        class _BrokenRedis:
            async def lpush(self, key: str, value: str) -> None:
                raise ConnectionError("valkey unreachable")

        receiver = _make_receiver(_BrokenRedis())
        await receiver._handle_message(  # noqa: SLF001
            {"platform": "twitch", "channel_name": "waddlebot", "content": "hi"}
        )


class TestRunStop:
    async def test_run_drives_receive_and_fans_out_each_event(
        self, redis_client: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        receiver = _make_receiver(redis_client)
        monkeypatch.setattr(
            receiver._irc,  # noqa: SLF001
            "receive",
            lambda config: _fake_privmsgs(
                {"channel": "#waddlebot", "sender": "alice", "text": "one"},
                {"channel": "#waddlebot", "sender": "bob", "text": "two"},
            ),
        )

        await receiver.run()

        ingest_key = bundle_stream_key(TENANT, None, APP_ID, "ingest")
        first = json.loads(await redis_client.rpop(ingest_key))
        second = json.loads(await redis_client.rpop(ingest_key))
        assert {first["author_username"], second["author_username"]} == {"alice", "bob"}

    async def test_run_returns_when_receive_generator_ends(
        self, redis_client: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A connection drop (generator ends) makes `run()` return.

        `ReceiverSupervisor`'s own restart-on-exit contract treats that
        exactly like a raised exception.
        """
        receiver = _make_receiver(redis_client)
        monkeypatch.setattr(receiver._irc, "receive", lambda config: _fake_privmsgs())  # noqa: SLF001

        await asyncio.wait_for(receiver.run(), timeout=2.0)  # must return promptly, not hang

    async def test_stop_never_raises(self, redis_client: Any) -> None:
        receiver = _make_receiver(redis_client)
        await receiver.stop()  # must not raise
