"""transports/irc_relay.py -- outbound IRC send relayed through Valkey (real LPUSH/BRPOP)."""

from __future__ import annotations

import json
from typing import Any

import pytest

from waddle_transports.base import Direction, NonRetryableTransportError
from waddle_transports.transports.irc_relay import RelayOutboundIrcTransport, outbound_queue_key


class TestOutboundQueueKey:
    def test_is_provider_scoped(self) -> None:
        assert outbound_queue_key("twitch") == "waddles:transport:irc:twitch:outbound"

    def test_different_providers_get_different_keys(self) -> None:
        assert outbound_queue_key("twitch") != outbound_queue_key("kick")


class TestRelayOutboundIrcTransport:
    def test_directions_is_outbound_only(self) -> None:
        transport = RelayOutboundIrcTransport(provider="twitch", redis_client=object())  # type: ignore[arg-type]
        assert transport.directions == {Direction.OUTBOUND}
        assert transport.name == "irc_relay"

    async def test_real_lpush_round_trip(self, redis_client: Any) -> None:
        """Fail-first: a real LPUSH lands on the provider-scoped key, real RPOP reads it back."""
        transport = RelayOutboundIrcTransport(provider="twitch", redis_client=redis_client)
        result = await transport.send({"channel": "#somechannel"}, {"text": "hello chat"})

        assert result.transport == "irc_relay"
        assert "twitch" in result.detail
        assert "#somechannel" in result.detail

        raw = await redis_client.rpop(outbound_queue_key("twitch"))
        assert raw is not None
        assert json.loads(raw) == {"channel": "#somechannel", "text": "hello chat"}

    async def test_empty_channel_is_non_retryable(self, redis_client: Any) -> None:
        transport = RelayOutboundIrcTransport(provider="twitch", redis_client=redis_client)
        with pytest.raises(NonRetryableTransportError, match="channel"):
            await transport.send({"channel": ""}, {"text": "hi"})

    async def test_empty_text_is_non_retryable(self, redis_client: Any) -> None:
        transport = RelayOutboundIrcTransport(provider="twitch", redis_client=redis_client)
        with pytest.raises(NonRetryableTransportError, match="text"):
            await transport.send({"channel": "#chan"}, {})

    async def test_nothing_queued_on_validation_failure(self, redis_client: Any) -> None:
        transport = RelayOutboundIrcTransport(provider="twitch", redis_client=redis_client)
        with pytest.raises(NonRetryableTransportError):
            await transport.send({"channel": ""}, {"text": "hi"})
        assert await redis_client.rpop(outbound_queue_key("twitch")) is None

    async def test_receive_not_implemented(self, redis_client: Any) -> None:
        """Outbound-only -- the base class's default `receive()` rejection applies."""
        transport = RelayOutboundIrcTransport(provider="twitch", redis_client=redis_client)
        with pytest.raises(NotImplementedError, match="does not implement inbound receive"):
            await transport.receive({}).__anext__()
