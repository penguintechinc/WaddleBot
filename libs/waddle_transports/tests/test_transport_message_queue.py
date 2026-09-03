"""transports/message_queue.py -- valkey publish/subscribe (real), aws_sqs/kafka (deferred)."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest

from waddle_transports.base import NonRetryableTransportError, RetryableTransportError
from waddle_transports.transports.message_queue import MessageQueueTransport


class TestValkeySubType:
    async def test_publish_and_subscribe_round_trip(self, redis_client: Any) -> None:
        transport = MessageQueueTransport(redis_client=redis_client)

        receive_gen = transport.receive(
            {"sub_type": "valkey", "channel": "waddles:notify", "_max_messages": 1}
        )
        received: list = []

        async def _collect() -> None:
            async for item in receive_gen:
                received.append(item)

        task = asyncio.ensure_future(_collect())
        await asyncio.sleep(0.05)  # let the subscribe land before publishing

        result = await transport.send(
            {"sub_type": "valkey", "channel": "waddles:notify"}, {"raider": "bob"}
        )
        await asyncio.wait_for(task, timeout=3.0)

        assert result.transport == "message_queue"
        assert result.sub_type == "valkey"
        assert received == [{"raider": "bob"}]

    async def test_send_missing_channel_is_non_retryable(self, redis_client: Any) -> None:
        transport = MessageQueueTransport(redis_client=redis_client)
        with pytest.raises(NonRetryableTransportError, match="channel"):
            await transport.send({"sub_type": "valkey"}, {})

    async def test_send_without_redis_client_is_non_retryable(self) -> None:
        transport = MessageQueueTransport(redis_client=None)
        with pytest.raises(NonRetryableTransportError, match="redis_client"):
            await transport.send({"sub_type": "valkey", "channel": "x"}, {})

    async def test_poison_message_is_dropped_not_fatal(self, redis_client: Any) -> None:
        transport = MessageQueueTransport(redis_client=redis_client)
        receive_gen = transport.receive(
            {"sub_type": "valkey", "channel": "waddles:poison", "_max_messages": 1}
        )
        received: list = []

        async def _collect() -> None:
            async for item in receive_gen:
                received.append(item)

        task = asyncio.ensure_future(_collect())
        await asyncio.sleep(0.05)
        await redis_client.publish("waddles:poison", b"not valid json{{{")
        await redis_client.publish("waddles:poison", json.dumps({"ok": True}))
        await asyncio.wait_for(task, timeout=3.0)

        assert received == [{"ok": True}]


class TestDeferredSubTypes:
    async def test_aws_sqs_send_is_deferred_not_a_stub(self) -> None:
        transport = MessageQueueTransport()
        with pytest.raises(NonRetryableTransportError, match="deferred"):
            await transport.send({"sub_type": "aws_sqs", "queue_url": "https://sqs/q"}, {})

    async def test_kafka_send_is_deferred_not_a_stub(self) -> None:
        transport = MessageQueueTransport()
        with pytest.raises(NonRetryableTransportError, match="deferred"):
            await transport.send({"sub_type": "kafka", "topic": "waddles.events"}, {})

    async def test_unknown_sub_type_is_non_retryable(self) -> None:
        transport = MessageQueueTransport()
        with pytest.raises(NonRetryableTransportError, match="not supported"):
            await transport.send({"sub_type": "carrier_pigeon"}, {})


async def test_network_error_on_publish_is_retryable() -> None:
    class _BrokenRedis:
        async def publish(self, *args: object, **kwargs: object) -> int:
            import redis.exceptions

            raise redis.exceptions.ConnectionError("boom")

    transport = MessageQueueTransport(redis_client=_BrokenRedis())  # type: ignore[arg-type]
    with pytest.raises(RetryableTransportError):
        await transport.send({"sub_type": "valkey", "channel": "x"}, {})
