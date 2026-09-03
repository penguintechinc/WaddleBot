"""`message_queue` transport -- publish/consume via a bundle-declared queue/topic.

Three sub-types:

- `valkey` -- **implemented, both directions.** Outbound: Valkey/Redis
  PUBLISH to `config["channel"]`. Inbound: SUBSCRIBE to `config["channel"]`
  and yield each received message.
- `aws_sqs` -- **deferred.** Needs `boto3`/`aioboto3` (a genuinely heavy
  dependency -- boto3 alone pulls a large transitive footprint), out of
  scope for this pass. Routed correctly, explicitly rejected with a clear
  "not yet implemented" error -- never silently pretends to work.
- `kafka` -- **deferred.** Needs `aiokafka` plus a *persistent*
  producer/consumer lifecycle (started once at service startup, not
  created-and-torn-down per call) -- real architectural surface beyond
  this pass's scope. Routed correctly, explicitly rejected.

Both deferred sub-types are tracked for a focused follow-up PR rather than
shipped as a stub that appears to work.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Mapping
from typing import Any

import redis.asyncio as redis

from waddle_transports.base import (
    NonRetryableTransportError,
    RetryableTransportError,
    Transport,
    TransportResult,
)
from waddle_transports.types import Direction


class MessageQueueTransport(Transport):
    """`message_queue` transport -- see module docstring for the sub_type matrix."""

    name = "message_queue"
    directions = frozenset({Direction.OUTBOUND, Direction.INBOUND})

    def __init__(self, *, redis_client: redis.Redis | None = None) -> None:
        """`redis_client` is required for the `valkey` sub_type (the only one needing it today)."""
        self._redis = redis_client

    async def send(self, config: Mapping[str, Any], payload: Mapping[str, Any]) -> TransportResult:
        """Route to the sub_type-specific outbound publish."""
        sub_type = config.get("sub_type")
        if sub_type == "valkey":
            return await self._send_valkey(config, payload)
        if sub_type == "aws_sqs":
            return await self._send_aws_sqs(config, payload)
        if sub_type == "kafka":
            return await self._send_kafka(config, payload)
        raise NonRetryableTransportError(f"message_queue sub_type={sub_type!r} is not supported")

    async def receive(self, config: Mapping[str, Any]) -> AsyncIterator[Mapping[str, Any]]:
        """Route to the sub_type-specific inbound consume. Only `valkey` is implemented."""
        sub_type = config.get("sub_type")
        if sub_type == "valkey":
            async for item in self._receive_valkey(config):
                yield item
            return
        raise NonRetryableTransportError(
            f"message_queue sub_type={sub_type!r} is not supported for receive()"
        )
        yield {}  # pragma: no cover -- unreachable, keeps this a real async generator function

    # --- valkey (implemented) -------------------------------------------------

    async def _send_valkey(
        self, config: Mapping[str, Any], payload: Mapping[str, Any]
    ) -> TransportResult:
        channel = config.get("channel")
        if not isinstance(channel, str) or not channel:
            raise NonRetryableTransportError(
                "message_queue:valkey config missing required 'channel'"
            )
        if self._redis is None:
            raise NonRetryableTransportError("message_queue:valkey requires a redis_client")

        message = json.dumps(dict(payload))
        try:
            subscriber_count = await self._redis.publish(channel, message)
        except redis.RedisError as exc:
            raise RetryableTransportError(f"message_queue:valkey publish failed: {exc}") from exc

        return TransportResult(
            transport="message_queue",
            sub_type="valkey",
            detail=f"published to {channel!r}, {subscriber_count} subscriber(s)",
        )

    async def _receive_valkey(self, config: Mapping[str, Any]) -> AsyncIterator[Mapping[str, Any]]:
        channel = config.get("channel")
        if not isinstance(channel, str) or not channel:
            raise NonRetryableTransportError(
                "message_queue:valkey config missing required 'channel'"
            )
        if self._redis is None:
            raise NonRetryableTransportError("message_queue:valkey requires a redis_client")

        max_messages = config.get("_max_messages")  # test-only escape hatch, see tests
        pubsub = self._redis.pubsub()
        try:
            await pubsub.subscribe(channel)
            received = 0
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                data = message["data"]
                text = data.decode("utf-8") if isinstance(data, bytes) else data
                try:
                    parsed = json.loads(text)
                except (TypeError, ValueError):
                    continue  # a poison message is dropped, never fatal to the consume loop
                if isinstance(parsed, dict):
                    yield parsed
                    received += 1
                if max_messages is not None and received >= max_messages:
                    return
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()

    # --- aws_sqs / kafka (deferred) --------------------------------------------

    async def _send_aws_sqs(
        self, config: Mapping[str, Any], payload: Mapping[str, Any]
    ) -> TransportResult:
        """Deferred -- see module docstring. Tracked for a focused follow-up PR."""
        raise NonRetryableTransportError(
            "message_queue sub_type='aws_sqs' is deferred (not yet implemented) -- needs "
            f"boto3/aioboto3 in a focused follow-up PR; queue_url={config.get('queue_url')!r} "
            "was not published to"
        )

    async def _send_kafka(
        self, config: Mapping[str, Any], payload: Mapping[str, Any]
    ) -> TransportResult:
        """Deferred -- see module docstring. Tracked for a focused follow-up PR."""
        raise NonRetryableTransportError(
            "message_queue sub_type='kafka' is deferred (not yet implemented) -- needs aiokafka "
            f"plus a persistent producer lifecycle in a focused follow-up PR; "
            f"topic={config.get('topic')!r} was not published to"
        )
