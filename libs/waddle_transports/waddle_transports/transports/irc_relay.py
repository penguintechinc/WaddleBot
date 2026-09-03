"""`irc_relay` -- outbound-only IRC send relayed through Valkey to the process holding the socket.

Folded in from the Twitch connector's own design (2026-09-02
coordination: "reuse the IRC connection for the demo"): svc-action is a
separate container/process from whichever service holds the live IRC
socket (e.g. `core/svc_ingest`'s `TwitchIrcReceiver`) -- an outbound send
here does NOT open a second IRC connection (which would mean two bot
sessions under one account) and does NOT call a REST fallback API.
Instead :class:`RelayOutboundIrcTransport` LPUSHes onto a small Valkey
relay queue (`outbound_queue_key`) that the socket-holding process drains
itself (alongside its own inbound recv loop) and sends through the
connection it already holds -- the single real IRC socket is reused both
directions, just relayed across the process boundary via Valkey rather
than shared in-process.

Deliberately a **separate** module from `transports/irc.py`'s own
`IrcTransport` (which opens its own direct TCP/TLS connection per call,
`registry.get_transport(TransportType.IRC)`'s default) -- `irc_relay` is
for the "one persistent socket, shared across process boundaries via a
queue" topology specifically; `irc` is for "connect directly, no shared-
socket constraint" cases. Not wired into `registry.get_transport()` (its
signature has no "relay vs direct" selector, and widening it isn't worth
the churn for one topology-specific variant) -- a caller needing this
imports the class directly, the same documented escape hatch `transports/
__init__.py`'s own docstring already describes for bypassing the registry.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from typing import Any, Protocol

from waddle_transports.base import NonRetryableTransportError, Transport, TransportResult
from waddle_transports.types import Direction

logger = logging.getLogger(__name__)

TRANSPORT_TYPE = "irc"


def outbound_queue_key(provider: str) -> str:
    """The Valkey list key an outbound relay send LPUSHes onto for `provider`.

    One key per provider (not per tenant/community) -- matches the
    inbound side's own platform-level connection model (one socket serves
    every channel/community the bot has joined); the queued message
    itself carries its own `channel`, so a single relay queue is enough.
    """
    return f"waddles:transport:{TRANSPORT_TYPE}:{provider}:outbound"


class RelayRedisLike(Protocol):
    """The one Valkey method the outbound relay side needs -- narrow, easy to fake in tests."""

    async def lpush(self, key: str, value: str) -> Any:
        """LPUSH `value` onto `key`."""
        ...


class InboundIrcSocketOwner(Protocol):
    """What the process holding the real IRC socket provides (e.g. `TwitchIrcReceiver`).

    Documented here rather than imported -- the socket-owning receiver
    lives in a different service (svc-ingest) than this outbound relay
    (svc-action); this shared library is the only thing both sides import.
    """

    async def run(self) -> None:
        """Connect and run until the connection ends or `stop()` is called."""
        ...

    async def stop(self) -> None:
        """Close the connection. Never raises."""
        ...


class RelayOutboundIrcTransport(Transport):
    """Outbound-only `irc` relay -- LPUSHes rather than opening its own connection.

    See module docstring for the process-topology rationale.
    """

    name = "irc_relay"
    directions = frozenset({Direction.OUTBOUND})

    def __init__(self, *, provider: str, redis_client: RelayRedisLike) -> None:
        """Bind to one `provider`'s relay queue (e.g. `"twitch"`) and one Valkey client."""
        self.provider = provider
        self.redis_client = redis_client

    async def send(self, config: Mapping[str, Any], payload: Mapping[str, Any]) -> TransportResult:
        """LPUSH `{channel, text}` onto this provider's outbound relay queue.

        `config["channel"]` and `payload["text"]` are required. Raises
        `NonRetryableTransportError` on an empty channel/text -- the
        receiving socket-owner's drain loop has no way to report a
        delivery failure back to this call (fire-and-forget relay, no
        request/response round trip), so a malformed message is rejected
        HERE, before it is ever queued, rather than silently dropped later.
        """
        channel = config.get("channel")
        text = payload.get("text")
        if not isinstance(channel, str) or not channel:
            raise NonRetryableTransportError("irc_relay send requires a non-empty 'channel'")
        if not isinstance(text, str) or not text:
            raise NonRetryableTransportError("irc_relay send requires non-empty payload 'text'")

        key = outbound_queue_key(self.provider)
        await self.redis_client.lpush(key, json.dumps({"channel": channel, "text": text}))
        logger.debug("transport.irc_relay_sent provider=%s channel=%s", self.provider, channel)
        return TransportResult(
            transport="irc_relay",
            detail=f"relayed to {self.provider} channel={channel}",
        )
