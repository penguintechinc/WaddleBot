"""`message_queue` action-target adapter -- Valkey PUBLISH to a bundle-declared channel.

No HTTP/SSRF surface (the target is a Valkey channel name, not a URL) --
the only failure modes are a dead/unreachable Valkey connection (retryable)
or an invalid channel name (non-retryable, caught by `action_target.py`
before this adapter ever runs).
"""

from __future__ import annotations

import json

import redis.asyncio as redis

from services.action_target import ActionTarget
from services.adapters.base import AdapterResult, RetryableDispatchError
from services.envelope import ActionEnvelope


async def dispatch(
    target: ActionTarget, envelope: ActionEnvelope, *, redis_client: redis.Redis
) -> AdapterResult:
    """PUBLISH the envelope payload (JSON) to `target.channel`.

    Raises :class:`RetryableDispatchError` on any Valkey connection error --
    PUBLISH has no notion of a 4xx-equivalent rejection, so every failure
    here is transient by definition.
    """
    message = json.dumps(dict(envelope.payload))
    try:
        subscriber_count = await redis_client.publish(target.channel, message)
    except redis.RedisError as exc:
        raise RetryableDispatchError(f"message_queue publish failed: {exc}") from exc

    return AdapterResult(
        target_type="message_queue",
        detail=f"published to {target.channel!r}, {subscriber_count} subscriber(s)",
    )
