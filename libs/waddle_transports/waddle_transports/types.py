"""Shared enums -- `TransportType` (the six transports) and `Direction`.

Kept dependency-free (stdlib `enum` only) so every consumer -- outbound
`svc-action`, inbound `svc-ingest`, a platform connector bundle -- can
import this module without pulling in httpx/redis/websockets/aiosmtplib
transitively.
"""

from __future__ import annotations

from enum import StrEnum


class TransportType(StrEnum):
    """The six delivery/receipt mechanisms this library knows about."""

    HTTP = "http"
    MESSAGE_QUEUE = "message_queue"
    IRC = "irc"
    SOCKET = "socket"
    OVERLAY = "overlay"
    EMAIL = "email"


class Direction(StrEnum):
    """Which way data moves through a transport for one particular call."""

    INBOUND = "inbound"
    OUTBOUND = "outbound"


#: Sub-types per transport -- `None` for a transport with no sub_type
#: concept (`irc`, `socket`). Single source of truth for both this
#: library's own validation and any consumer wanting to list valid
#: sub-types (e.g. a config-authoring UI).
KNOWN_SUB_TYPES: dict[TransportType, frozenset[str] | None] = {
    TransportType.HTTP: frozenset({"webhook", "rest_api", "grpc", "graphql", "rest_pull"}),
    TransportType.MESSAGE_QUEUE: frozenset({"valkey", "aws_sqs", "kafka"}),
    TransportType.IRC: None,
    TransportType.SOCKET: None,
    TransportType.OVERLAY: frozenset({"full_screen", "media", "crawler"}),
    TransportType.EMAIL: frozenset({"smtp", "imap"}),
}
