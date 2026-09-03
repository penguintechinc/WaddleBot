"""bundles/twitch_send_action.py -- OUTBOUND `irc` transport chat send, relayed to svc-ingest.

Loaded via the same bundle-script entrypoint mechanism Discord's action
bundle uses (`services/adapters/bundle.py::dispatch`,
`app_catalog.stages.action.entrypoint`), but its OWN implementation does
NOT call an HTTP API the way `discord_send_action.py`'s `send_message`
does. Per the 2026-09-02 transport-unification coordination note (see
`libs/waddle_transports/waddle_transports/irc.py`'s module docstring):
Twitch chat send is `irc`, `Direction.OUTBOUND`, and for this connector's
demo scope it reuses the ONE real IRC connection svc-ingest's
`TwitchIrcReceiver` already holds, relayed across the process boundary
via `waddle_transports.irc.RelayOutboundIrcTransport` (a Valkey LPUSH) --
not a second IRC connection and not Twitch's Helix REST API (a
documented future alternative, out of scope here).

Seeded via `config/postgres/migrations/083_twitch_send_action_bundle.sql`
as `waddles.bot.twitch.default`'s `stages.action.entrypoint`.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx
import redis.asyncio as redis

from services.adapters.base import AdapterResult, NonRetryableDispatchError, RetryableDispatchError
from services.envelope import ActionEnvelope

try:
    from waddle_transports.base import NonRetryableTransportError, RetryableTransportError
    from waddle_transports.irc import RelayOutboundIrcTransport
except ImportError as exc:  # pragma: no cover - packaging guard, not a runtime code path
    raise ImportError(
        "waddle_transports is not installed -- see core/svc_action/Dockerfile "
        "('pip install /app/libs/waddle_transports')"
    ) from exc

#: Lazily-built, process-wide Valkey client -- `send_message`'s own
#: signature (`(envelope, config, *, http_client)`) is the same one every
#: other bundle-script entrypoint uses (`services/adapters/bundle.py::
#: dispatch`'s fixed call shape), so a redis client is not passed in;
#: built here instead of per-call to avoid opening a new connection on
#: every dispatched message.
_redis_client: redis.Redis | None = None


def _get_redis_client(config: Mapping[str, Any]) -> redis.Redis:
    """Build (once) or return the cached Valkey client for the outbound IRC relay.

    Reads `VALKEY_URL`/`REDIS_URL` env vars, mirroring `config.py`
    `ActionConfig.from_env`'s own fallback chain. Tests never exercise
    this real network path -- they monkeypatch `_get_redis_client` itself
    (module-level function, easy `monkeypatch.setattr` target) to return
    a `fakeredis.FakeAsyncRedis` instead, matching `discord_send_action.py`'s
    own `guarded_request` monkeypatch precedent.
    """
    global _redis_client
    if _redis_client is None:
        import os

        url = (
            os.environ.get("VALKEY_URL")
            or os.environ.get("REDIS_URL")
            or "redis://localhost:6379/0"
        )
        _redis_client = redis.from_url(url, decode_responses=True)
    return _redis_client


async def send_message(
    envelope: ActionEnvelope,
    config: Mapping[str, Any],
    *,
    http_client: httpx.AsyncClient,
) -> AdapterResult:
    """Relay `envelope.payload["text"]` to a Twitch channel via the OUTBOUND `irc` transport.

    `config` is the bundle's resolved `stages.action.config` and must
    declare `channel` (the Twitch channel name svc-ingest's
    `TwitchIrcReceiver` has joined). `http_client` is accepted (and
    unused) only because `services/adapters/bundle.py::dispatch` always
    passes it -- every bundle-script entrypoint shares that one call
    signature.

    Raises `NonRetryableDispatchError` for a config error or an empty
    payload `text`; a `RetryableTransportError` from the transport layer
    (currently: none -- the Valkey relay itself has no notion of a
    "transient" failure distinct from any other write) would map to
    `RetryableDispatchError`, kept symmetric with `discord_send_action.py`
    for when a future retryable transport failure mode is added.
    """
    channel = config.get("channel")
    if not isinstance(channel, str) or not channel:
        raise NonRetryableDispatchError("twitch bundle config missing required 'channel'")

    text = envelope.payload.get("text")
    if not isinstance(text, str) or not text:
        raise NonRetryableDispatchError("action envelope payload missing required 'text' string")

    transport = RelayOutboundIrcTransport(provider="twitch", redis_client=_get_redis_client(config))

    try:
        result = await transport.send(channel=channel, text=text)
    except NonRetryableTransportError as exc:
        raise NonRetryableDispatchError(str(exc), http_status=exc.http_status) from exc
    except RetryableTransportError as exc:
        raise RetryableDispatchError(str(exc), http_status=exc.http_status) from exc

    return AdapterResult(target_type="bundle", detail=result.detail, http_status=result.http_status)
