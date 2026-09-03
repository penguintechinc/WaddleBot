"""Placeholder boundary for the shared `waddle_transports` library (`libs/waddle_transports/`).

Design decision (2026-09-02): ingest and action are unifying under one
shared transport abstraction, `libs/waddle_transports/`, landing
separately (a distinct in-flight change). Until that package exists, this
module defines the minimal subset of its expected public interface
svc-ingest's own persistent-socket receivers depend on: `Transport` (the
ABC every transport implements), `TransportType` (how events physically
arrive/depart), and `Direction` (which way). Every name here is chosen to
match `waddle_transports`' expected public API, so swapping
``from transport_boundary import Transport, TransportType, Direction``
for ``from waddle_transports import Transport, TransportType, Direction``
is a one-line import change once it lands, not a rewrite --
`receivers/discord_gateway.py`'s `DiscordGatewayReceiver` already
subclasses `Transport` and declares `transport_type = TransportType.
SOCKET`, `direction = Direction.INBOUND`.

Deliberately NOT modeled as a bundle-manifest `communication_model` enum
value (an earlier revision of this code did exactly that, adding a
bespoke `"gateway_socket"` member) -- a transport's type/direction is a
property of the CODE that implements it, not of the manifest schema;
duplicating that classification into `communication_model` would just be
a second, competing vocabulary once the real `waddle_transports` package
lands. See `flask_core.app_manifest.KNOWN_COMMUNICATION_MODELS`'s own
comment for the manifest-side half of this reasoning.
"""

from __future__ import annotations

import enum
from abc import ABC, abstractmethod


class TransportType(enum.Enum):
    """How a transport physically moves bytes.

    `SOCKET` covers any persistent duplex connection (Discord's WebSocket
    gateway today); `IRC` is the wire-protocol-specific sibling for
    IRC-based chat platforms (e.g. Twitch chat) that don't fit the plain
    `SOCKET` shape one-to-one. Both are still "long-lived inbound
    connections" from `ReceiverSupervisor`'s point of view -- this enum is
    intentionally small (just what svc-ingest needs today), not an attempt
    to predict `waddle_transports`' full eventual member set.
    """

    SOCKET = "socket"
    IRC = "irc"


class Direction(enum.Enum):
    """Which way data flows across a `Transport`."""

    INBOUND = "inbound"
    OUTBOUND = "outbound"


class Transport(ABC):
    """Minimal shared shape every transport implements.

    `ReceiverSupervisor` (`supervisor.py`) only ever calls `run()`/
    `stop()` on a registered transport; `transport_type`/`direction` are
    classification metadata for callers that need to introspect what kind
    of transport they're holding (logging, metrics, a future transport
    registry) -- `ReceiverSupervisor.register()` accepts an optional
    `Transport` instance for exactly that.
    """

    transport_type: TransportType
    direction: Direction

    @abstractmethod
    async def run(self) -> None:
        """Run until the transport's connection ends or `stop()` is called."""
        ...

    @abstractmethod
    async def stop(self) -> None:
        """Stop the transport. Must never raise -- shutdown must not fail."""
        ...
