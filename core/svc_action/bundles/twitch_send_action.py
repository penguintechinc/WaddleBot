"""bundles/twitch_send_action.py -- OUTBOUND `irc` transport chat send, relayed to svc-ingest.

Loaded via the same bundle-script entrypoint mechanism Discord's action
bundle uses (`services/adapters/bundle.py::dispatch`,
`app_catalog.stages.action.entrypoint`), but its OWN implementation does
NOT call an HTTP API the way `discord_send_action.py`'s `send_message`
does. Twitch chat send is `irc`, `Direction.OUTBOUND`; for this
connector's demo scope it relays through Valkey to svc-ingest's own
`outbound_drain.py` (which sends via a fresh `waddle_transports.
transports.irc.IrcTransport` connection) rather than calling Twitch's
Helix REST API directly -- svc-action never holds Twitch credentials or
opens its own IRC connections. Realigned (2026-09-03) onto the merged
`waddle_transports.transports.irc_relay.RelayOutboundIrcTransport`.

Replies to the ORIGIN channel: `envelope.payload["channel_name"]` (the
channel the triggering chat message came from, carried through process->
action by `bundles/twitch_ingest.py::normalize()`'s own payload shape)
takes precedence over the bundle's static `config["channel"]` default --
a reply belongs in the channel the request came from, not a hardcoded
one; the static config value only matters for an action with no
triggering chat message (e.g. a scheduled announcement).

Seeded via `config/postgres/migrations/083_twitch_send_action_bundle.sql`
as `waddles.bot.twitch.default`'s `stages.action.entrypoint`.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx
import redis.asyncio as redis
from waddle_transports import NonRetryableTransportError, RetryableTransportError, TransportResult
from waddle_transports.transports.irc_relay import RelayOutboundIrcTransport

from services.adapters.base import NonRetryableDispatchError, RetryableDispatchError
from services.envelope import ActionEnvelope

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
) -> TransportResult:
    """Relay `envelope.payload["text"]` to the origin (or configured) Twitch channel.

    `channel` resolution: `envelope.payload["channel_name"]` (the
    triggering message's own channel) first, falling back to the bundle's
    static `config["channel"]` default. `http_client` is accepted (and
    unused) only because `services/adapters/bundle.py::dispatch` always
    passes it -- every bundle-script entrypoint shares that one call
    signature.

    Raises `NonRetryableDispatchError` for a config error or an empty
    payload `text`, translating any `waddle_transports.
    NonRetryableTransportError`/`RetryableTransportError` the relay itself
    raises into this bundle's own `*DispatchError` family --
    `services/adapters/bundle.py::dispatch` only ever catches that family,
    never `waddle_transports`' own error types directly. On success,
    returns the transport's own `waddle_transports.TransportResult`
    unwrapped -- `dispatch()` normalizes it into this service's local
    `AdapterResult` shape for the dispatch-log audit record.
    """
    payload_channel = envelope.payload.get("channel_name")
    channel = payload_channel if isinstance(payload_channel, str) and payload_channel else None
    if channel is None:
        config_channel = config.get("channel")
        channel = config_channel if isinstance(config_channel, str) and config_channel else None
    if not channel:
        raise NonRetryableDispatchError(
            "twitch bundle has no channel: envelope.payload['channel_name'] and "
            "config['channel'] are both missing"
        )

    text = envelope.payload.get("text")
    if not isinstance(text, str) or not text:
        raise NonRetryableDispatchError("action envelope payload missing required 'text' string")

    transport = RelayOutboundIrcTransport(provider="twitch", redis_client=_get_redis_client(config))

    try:
        return await transport.send({"channel": channel}, {"text": text})
    except NonRetryableTransportError as exc:
        raise NonRetryableDispatchError(str(exc), http_status=exc.http_status) from exc
    except RetryableTransportError as exc:
        raise RetryableDispatchError(str(exc), http_status=exc.http_status) from exc
