"""Dispatch registry: routes an :class:`ActionTarget` to its adapter module.

One shared entrypoint (`dispatch_action`) so `runner.py` never branches on
`target.type` itself -- each adapter owns its own call signature (a
webhook needs an HTTP client + secret, message_queue needs a Redis client,
email needs SMTP settings), unified here into one uniform call the runner
makes regardless of which type resolved.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx

from config import ActionConfig
from services.action_target import ActionTarget
from services.adapters import email, message_queue, overlay, rest_api, webhook
from services.adapters.base import AdapterResult, NonRetryableDispatchError
from services.envelope import ActionEnvelope

if TYPE_CHECKING:
    import redis.asyncio as redis


async def dispatch_action(
    target: ActionTarget,
    envelope: ActionEnvelope,
    *,
    config: ActionConfig,
    redis_client: "redis.Redis[bytes]",
    http_client: httpx.AsyncClient,
) -> AdapterResult:
    """Route `target` to its adapter and return the successful dispatch result.

    Raises `RetryableDispatchError`/`NonRetryableDispatchError` (from the
    adapter itself) on failure -- `runner.py` is the only caller, and it
    wraps this in `retry_with_backoff`.
    """
    if target.type == "webhook":
        return await webhook.dispatch(
            target, envelope, timeout_seconds=config.http_timeout_seconds, client=http_client
        )
    if target.type == "rest_api":
        return await rest_api.dispatch(
            target, envelope, timeout_seconds=config.http_timeout_seconds, client=http_client
        )
    if target.type == "message_queue":
        return await message_queue.dispatch(target, envelope, redis_client=redis_client)
    if target.type == "overlay":
        return await overlay.dispatch(
            target,
            envelope,
            presentation_base_url=config.presentation_base_url,
            timeout_seconds=config.http_timeout_seconds,
            client=http_client,
        )
    if target.type == "email":
        return await email.dispatch(
            target,
            envelope,
            smtp_host=config.smtp_host,
            smtp_port=config.smtp_port,
            smtp_user=config.smtp_user,
            smtp_password=config.smtp_password,
            smtp_use_tls=config.smtp_use_tls,
            smtp_from_addr=config.smtp_from_addr,
            timeout_seconds=config.http_timeout_seconds,
        )
    # action_target.py's KNOWN_TARGET_TYPES already rejects anything else at
    # parse time -- this branch is defense-in-depth against a future type
    # being added to that set without a matching adapter arm here.
    raise NonRetryableDispatchError(f"no adapter registered for action_target.type={target.type!r}")
