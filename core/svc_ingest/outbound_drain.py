"""TwitchOutboundDrain -- OUTBOUND `irc` relay drain, sends via a fresh `IrcTransport` connection.

Realigned (2026-09-03) onto the merged `waddle_transports` library:
`IrcTransport.send()` connects, authenticates, joins, PRIVMSGs, quits,
and closes -- a short-lived connection per call, not a persistent one --
so relaying an outbound send through a receiver's already-open socket
(this connector's original draft) is unnecessary; the real transport
never held a persistent connection to reuse in the first place. The
Valkey-relay hand-off itself is kept (svc-action never holds Twitch
credentials or opens its own IRC connections -- 2026-09-03 coordination
note), it now just resolves to "drain the queue, open a fresh connection
per message" rather than "drain the queue, reuse the receiver's socket".

Runs as its own `ReceiverSupervisor`-registered task, independent of any
per-channel `TwitchIrcReceiver` -- NOT lease-guarded: `BRPOP` is atomic,
so N `svc-ingest` replicas each running their own drain loop against the
same shared queue key (`waddle_transports.transports.irc_relay.
outbound_queue_key`) safely compete for items with no duplicate sends,
unlike the per-channel INBOUND receivers (which genuinely must not open
two connections to the same channel, hence their own per-channel lease).
"""

from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Mapping
from typing import Any, Protocol

from waddle_transports.transports.irc import IrcTransport
from waddle_transports.transports.irc_relay import outbound_queue_key

logger = logging.getLogger(__name__)

#: How long one BRPOP call blocks before looping back to check `self._running` --
#: bounds shutdown latency without busy-polling.
_POLL_TIMEOUT_S = 5


class DrainRedisLike(Protocol):
    """The one Valkey method the drain loop needs -- narrow, easy to fake in tests.

    `keys`/`timeout: Any` -- `redis.asyncio.Redis.brpop`'s real signature
    accepts a broader `KeysT`/`Number | None` than this narrow duck-typed
    contract declares; `Any` here keeps this Protocol satisfied by both
    the real client and a hand-rolled test double, same rationale as
    `fanout.RedisLike`'s own docstring -- including the plain-`def`-
    returning-`Awaitable` shape (see that Protocol's own docstring for
    why `async def` doesn't match `redis-py`'s own stub return type).
    """

    def brpop(self, keys: Any, timeout: Any) -> Awaitable[Any]:  # noqa: ASYNC109 - mirrors redis.asyncio.Redis.brpop's own signature, not an internal cancellation timeout
        """BRPOP across `keys`; returns `(key, value)` or `None` on timeout."""
        ...


class TwitchOutboundDrain:
    """Drains `outbound_queue_key("twitch")`, sending each item via a fresh `IrcTransport`."""

    def __init__(self, *, redis_client: DrainRedisLike, irc_config_base: Mapping[str, Any]) -> None:
        """Bind to `redis_client` and the shared (non-channel) IRC connection settings.

        `irc_config_base` carries `{host, port, nick, password_ref,
        use_tls}` -- everything `IrcTransport.send()`'s config needs
        except `channel`, which comes from each dequeued message.
        """
        self._redis = redis_client
        self._irc_config_base = irc_config_base
        self._irc = IrcTransport()
        self._running = False

    async def run(self) -> None:
        """`ReceiverSupervisor`-compatible entrypoint: BRPOP + send, forever, until cancelled."""
        self._running = True
        key = outbound_queue_key("twitch")
        while self._running:
            popped = await self._redis.brpop([key], timeout=_POLL_TIMEOUT_S)
            if popped is None:
                continue
            _popped_key, raw_value = popped
            await self._send_one(raw_value)

    async def stop(self) -> None:
        """Signal `run()`'s loop to exit after its current BRPOP call. Never raises."""
        self._running = False

    async def _send_one(self, raw_value: bytes | str) -> None:
        """Parse+send one relayed outbound message; malformed items are dropped, logged."""
        try:
            text = raw_value.decode("utf-8") if isinstance(raw_value, bytes) else raw_value
            data = json.loads(text)
            channel = data["channel"]
            message_text = data["text"]
        except (TypeError, ValueError, KeyError) as exc:
            logger.error("outbound_drain.malformed error=%s", exc)
            return

        config = {**self._irc_config_base, "channel": channel}
        try:
            result = await self._irc.send(config, {"text": message_text})
            logger.debug("outbound_drain.sent channel=%s detail=%s", channel, result.detail)
        except Exception as exc:  # noqa: BLE001 - one bad send must never kill the drain loop
            logger.error("outbound_drain.send_failed channel=%s error=%s", channel, exc)
