"""base.py -- the `Transport` base class's default `send()`/`receive()` behavior."""

from __future__ import annotations

import pytest

from waddle_transports.base import Transport


class _BareTransport(Transport):
    name = "bare"


async def test_default_send_raises_not_implemented() -> None:
    transport = _BareTransport()
    with pytest.raises(NotImplementedError, match="does not implement outbound send"):
        await transport.send({}, {})


async def test_default_receive_raises_not_implemented_on_first_iteration() -> None:
    transport = _BareTransport()
    generator = transport.receive({})
    with pytest.raises(NotImplementedError, match="does not implement inbound receive"):
        await generator.__anext__()


def test_default_directions_is_empty() -> None:
    assert _BareTransport().directions == frozenset()
