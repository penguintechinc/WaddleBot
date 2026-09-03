"""`get_transport(transport_type, ...) -> Transport` -- resolve a transport instance.

**Frozen contract** (parallel transport-module implementations target
this signature without touching `types.py`/`base.py`/`registry.py`
themselves): every `Transport` subclass takes its shared runtime
resources (an `httpx.AsyncClient`, a `redis.asyncio.Redis`) via
constructor injection, wired here once per resolve call -- never per
`send()`/`receive()` call. A transport that needs no shared resource
(`irc`, `socket`, `overlay` via its own `http_client`, `email`) simply
ignores the kwargs it doesn't use.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from waddle_transports.base import Transport
from waddle_transports.types import TransportType

if TYPE_CHECKING:
    import httpx
    import redis.asyncio as redis


def get_transport(
    transport_type: TransportType,
    *,
    http_client: httpx.AsyncClient | None = None,
    redis_client: redis.Redis | None = None,
) -> Transport:
    """Return a `Transport` instance wired with whichever of `http_client`/`redis_client` it needs.

    Raises `ValueError` for a `transport_type` outside `TransportType` --
    defense-in-depth; the enum itself already constrains callers to a
    valid value at the type-checker level.
    """
    if transport_type == TransportType.HTTP:
        from waddle_transports.transports.http import HttpTransport

        return HttpTransport(http_client=http_client)

    if transport_type == TransportType.MESSAGE_QUEUE:
        from waddle_transports.transports.message_queue import MessageQueueTransport

        return MessageQueueTransport(redis_client=redis_client)

    if transport_type == TransportType.IRC:
        from waddle_transports.transports.irc import IrcTransport

        return IrcTransport()

    if transport_type == TransportType.SOCKET:
        from waddle_transports.transports.socket import SocketTransport

        return SocketTransport()

    if transport_type == TransportType.OVERLAY:
        from waddle_transports.transports.overlay import OverlayTransport

        return OverlayTransport(http_client=http_client)

    if transport_type == TransportType.EMAIL:
        from waddle_transports.transports.email import EmailTransport

        return EmailTransport()

    raise ValueError(
        f"unknown transport_type {transport_type!r}"
    )  # pragma: no cover -- enum-exhaustive
