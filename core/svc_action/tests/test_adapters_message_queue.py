"""services/adapters/message_queue.py -- Valkey PUBLISH via fakeredis."""

from __future__ import annotations

import json

import fakeredis.aioredis
import pytest

from services.action_target import ActionTarget
from services.adapters import message_queue
from services.adapters.base import RetryableDispatchError
from services.envelope import ActionEnvelope


def _envelope() -> ActionEnvelope:
    return ActionEnvelope(
        tenant="1",
        community="42",
        app_id="waddles.bot.shoutout.default",
        stage="action",
        payload={"event": "raid", "count": 5},
        ts="2026-08-31T12:00:00Z",
        raw="{}",
    )


async def test_publishes_json_payload_to_channel() -> None:
    redis_client = fakeredis.aioredis.FakeRedis()
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("waddles:notify")
    await pubsub.get_message(timeout=1)  # subscribe confirmation

    target = ActionTarget(type="message_queue", channel="waddles:notify")
    result = await message_queue.dispatch(target, _envelope(), redis_client=redis_client)

    message = await pubsub.get_message(timeout=1)
    assert message is not None
    assert json.loads(message["data"]) == {"event": "raid", "count": 5}
    assert result.target_type == "message_queue"

    await pubsub.aclose()
    await redis_client.aclose()


async def test_redis_error_is_retryable(monkeypatch: pytest.MonkeyPatch) -> None:
    redis_client = fakeredis.aioredis.FakeRedis()

    import redis.asyncio as redis

    async def _raise_publish(*args: object, **kwargs: object) -> None:
        raise redis.ConnectionError("connection lost")

    monkeypatch.setattr(redis_client, "publish", _raise_publish)

    target = ActionTarget(type="message_queue", channel="waddles:notify")
    with pytest.raises(RetryableDispatchError):
        await message_queue.dispatch(target, _envelope(), redis_client=redis_client)

    await redis_client.aclose()
