"""Shared transport contract: the `Transport` ABC, its result shape, and its two exceptions.

Every transport module (`transports/{http,message_queue,irc,socket,
overlay,email}.py`) exports one `Transport` subclass implementing
whichever of `send()` (outbound)/`receive()` (inbound) it actually
supports -- see each module's own docstring and `types.KNOWN_SUB_TYPES`
for the direction matrix. Calling the direction a transport doesn't
implement raises `NotImplementedError` with a clear message (the base
class's own default), never a silent no-op.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass
from typing import Any, ClassVar

from waddle_transports.types import Direction


class RetryableTransportError(Exception):
    """A transient failure (5xx, network/timeout, connection drop) -- worth retrying."""

    def __init__(self, message: str, *, http_status: int | None = None) -> None:
        """Store `message` (the exception text) and the originating HTTP status, if any."""
        super().__init__(message)
        self.http_status = http_status


class NonRetryableTransportError(Exception):
    """A permanent failure (4xx auth, bad config, deferred/unsupported sub_type) -- never retry."""

    def __init__(self, message: str, *, http_status: int | None = None) -> None:
        """Store `message` (the exception text) and the originating HTTP status, if any."""
        super().__init__(message)
        self.http_status = http_status


@dataclass(slots=True, frozen=True)
class TransportResult:
    """Successful-dispatch outcome -- a consumer's own audit log records this."""

    transport: str
    detail: str
    sub_type: str | None = None
    http_status: int | None = None


class Transport:
    """Base class every transport module's implementation extends.

    Not declared `abc.ABC`/`abstractmethod` deliberately -- a transport
    implementing only one direction (e.g. `overlay`, outbound-only) must
    not be forced to stub out the other with a body that just re-raises;
    the base class's own default already does exactly that, so a
    single-direction transport simply doesn't override the other method.
    """

    name: ClassVar[str]
    directions: ClassVar[frozenset[Direction]] = frozenset()

    async def send(self, config: Mapping[str, Any], payload: Mapping[str, Any]) -> TransportResult:
        """Outbound: deliver `payload` per `config`. Raises `NotImplementedError` if unsupported."""
        raise NotImplementedError(f"{self.name} transport does not implement outbound send()")

    async def receive(self, config: Mapping[str, Any]) -> AsyncIterator[Mapping[str, Any]]:
        """Inbound: yield each received item per `config`. Unsupported -> `NotImplementedError`."""
        raise NotImplementedError(f"{self.name} transport does not implement inbound receive()")
        yield {}  # pragma: no cover -- unreachable; makes this a real async generator function
