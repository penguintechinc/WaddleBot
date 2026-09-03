"""registry.py -- get_transport resolves every TransportType with the right directions."""

from __future__ import annotations

import pytest

from waddle_transports.base import Direction, Transport
from waddle_transports.registry import get_transport
from waddle_transports.types import TransportType


@pytest.mark.parametrize(
    ("transport_type", "expected_directions"),
    [
        (TransportType.HTTP, {Direction.OUTBOUND, Direction.INBOUND}),
        (TransportType.MESSAGE_QUEUE, {Direction.OUTBOUND, Direction.INBOUND}),
        (TransportType.IRC, {Direction.OUTBOUND, Direction.INBOUND}),
        (TransportType.SOCKET, {Direction.OUTBOUND, Direction.INBOUND}),
        (TransportType.OVERLAY, {Direction.OUTBOUND}),
        (TransportType.EMAIL, {Direction.OUTBOUND}),
    ],
)
def test_resolves_every_transport_type(transport_type, expected_directions) -> None:  # noqa: ANN001
    transport = get_transport(transport_type)
    assert isinstance(transport, Transport)
    assert transport.name == transport_type.value
    assert transport.directions == expected_directions


def test_http_transport_receives_the_given_http_client() -> None:
    import httpx

    from waddle_transports.transports.http import HttpTransport

    client = httpx.AsyncClient()
    transport = get_transport(TransportType.HTTP, http_client=client)
    assert isinstance(transport, HttpTransport)
    assert transport._client is client  # noqa: SLF001 -- white-box wiring check


def test_message_queue_transport_receives_the_given_redis_client() -> None:
    from waddle_transports.transports.message_queue import MessageQueueTransport

    fake_redis = object()
    transport = get_transport(TransportType.MESSAGE_QUEUE, redis_client=fake_redis)  # type: ignore[arg-type]
    assert isinstance(transport, MessageQueueTransport)
    assert transport._redis is fake_redis  # noqa: SLF001
