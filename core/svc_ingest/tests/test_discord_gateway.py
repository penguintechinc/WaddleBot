"""Tests for `receivers.discord_gateway.DiscordGatewayReceiver`.

Real `discord.Bot` instance (constructing one does not open a network
connection -- only `bot.start()` does), duck-typed fake `discord.Message`/
`Author`/`Guild`/`Channel` objects (py-cord's own `Message` needs live HTTP
state to construct, so a fake with just the attributes this receiver
reads is the standard py-cord testing pattern), and a real `fakeredis`
round trip for the fan-out assertions -- no mocked gateway connection is
ever opened, matching the task's own "mock the gateway in tests" scope.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock

from flask_core.app_registry import AppRegistry
from flask_core.stream_pipeline import bundle_stream_key

from bundles.discord_gateway_manifest import register_default_bundles
from receivers.discord_gateway import DiscordGatewayReceiver
from transport_boundary import Direction, Transport, TransportType

TENANT = "acme-corp"
APP_ID = "waddles.bot.discord.gateway"


@dataclass
class _FakeAuthor:
    id: int
    name: str
    bot: bool = False


@dataclass
class _FakeGuild:
    id: int


@dataclass
class _FakeChannel:
    id: int


@dataclass
class _FakeMessage:
    id: int
    author: _FakeAuthor
    channel: _FakeChannel
    content: str
    guild: _FakeGuild | None = None


def _make_receiver(
    redis_client: Any, registry: AppRegistry | None = None
) -> DiscordGatewayReceiver:
    reg = registry if registry is not None else AppRegistry()
    if not reg.all_apps():
        register_default_bundles(reg)
    return DiscordGatewayReceiver(
        token="fake-token-not-a-real-discord-token",  # noqa: S106 - test literal, not a secret
        redis_client=redis_client,
        registry=reg,
        tenant_slug=TENANT,
    )


class TestHandleMessage:
    async def test_bot_authored_message_is_ignored(self, redis_client: Any) -> None:
        receiver = _make_receiver(redis_client)
        message = _FakeMessage(
            id=1,
            author=_FakeAuthor(id=999, name="OtherBot", bot=True),
            channel=_FakeChannel(id=42),
            content="I am a bot",
            guild=_FakeGuild(id=7),
        )
        await receiver._handle_message(message)  # noqa: SLF001 - exercising the real handler

        ingest_key = bundle_stream_key(TENANT, "7", APP_ID, "ingest")
        assert await redis_client.rpop(ingest_key) is None

    async def test_human_guild_message_fans_out_to_the_discord_ingest_bundle(
        self, redis_client: Any
    ) -> None:
        receiver = _make_receiver(redis_client)
        message = _FakeMessage(
            id=123,
            author=_FakeAuthor(id=555, name="alice"),
            channel=_FakeChannel(id=42),
            content="hello waddlebot",
            guild=_FakeGuild(id=7),
        )
        await receiver._handle_message(message)  # noqa: SLF001

        ingest_key = bundle_stream_key(TENANT, "7", APP_ID, "ingest")
        raw = await redis_client.rpop(ingest_key)
        assert raw is not None
        event = json.loads(raw)
        assert event == {
            "platform": "discord",
            "guild_id": "7",
            "channel_id": "42",
            "message_id": "123",
            "author_id": "555",
            "author_username": "alice",
            "content": "hello waddlebot",
        }

    async def test_dm_message_has_no_guild_and_uses_tenant_wide_key(
        self, redis_client: Any
    ) -> None:
        receiver = _make_receiver(redis_client)
        message = _FakeMessage(
            id=124,
            author=_FakeAuthor(id=555, name="alice"),
            channel=_FakeChannel(id=99),
            content="dm text",
            guild=None,
        )
        await receiver._handle_message(message)  # noqa: SLF001

        ingest_key = bundle_stream_key(TENANT, None, APP_ID, "ingest")
        raw = await redis_client.rpop(ingest_key)
        assert raw is not None
        event = json.loads(raw)
        assert event["guild_id"] is None

    async def test_fanout_failure_does_not_propagate(self, redis_client: Any) -> None:
        """One bad event must never kill the gateway connection -- `_handle_message` swallows."""

        class _BrokenRedis:
            async def lpush(self, key: str, value: str) -> None:
                raise ConnectionError("valkey unreachable")

        receiver = _make_receiver(_BrokenRedis())
        message = _FakeMessage(
            id=125,
            author=_FakeAuthor(id=555, name="alice"),
            channel=_FakeChannel(id=42),
            content="hello",
            guild=_FakeGuild(id=7),
        )
        await receiver._handle_message(message)  # noqa: SLF001 - must not raise


class TestRunStop:
    async def test_run_delegates_to_bot_start_with_token(self, redis_client: Any) -> None:
        receiver = _make_receiver(redis_client)
        receiver.bot.start = AsyncMock()  # type: ignore[method-assign]

        await receiver.run()

        receiver.bot.start.assert_awaited_once_with("fake-token-not-a-real-discord-token")

    async def test_stop_closes_the_bot(self, redis_client: Any) -> None:
        receiver = _make_receiver(redis_client)
        receiver.bot.close = AsyncMock()  # type: ignore[method-assign]

        await receiver.stop()

        receiver.bot.close.assert_awaited_once()

    async def test_stop_swallows_close_errors(self, redis_client: Any) -> None:
        receiver = _make_receiver(redis_client)
        receiver.bot.close = AsyncMock(side_effect=RuntimeError("already closed"))  # type: ignore[method-assign]

        await receiver.stop()  # must not raise


class TestTransportClassification:
    """`DiscordGatewayReceiver` maps to `(TransportType.SOCKET, Direction.INBOUND)`."""

    def test_is_a_transport_subclass(self, redis_client: Any) -> None:
        receiver = _make_receiver(redis_client)
        assert isinstance(receiver, Transport)

    def test_transport_type_is_socket(self, redis_client: Any) -> None:
        receiver = _make_receiver(redis_client)
        assert receiver.transport_type is TransportType.SOCKET

    def test_direction_is_inbound(self, redis_client: Any) -> None:
        receiver = _make_receiver(redis_client)
        assert receiver.direction is Direction.INBOUND
