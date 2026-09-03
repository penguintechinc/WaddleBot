"""Tests for `transport_boundary` -- the `waddle_transports` interface placeholder.

Design decision (2026-09-02): model a persistent-socket ingest connection
as this shared library's `Transport`/`TransportType.SOCKET`/`Direction.
INBOUND` shape rather than a bespoke `communication_model` manifest value
-- see `transport_boundary.py`'s own module docstring for the full
reasoning and the swap-to-real-package path.
"""

from __future__ import annotations

import pytest

from transport_boundary import Direction, Transport, TransportType


def test_transport_type_has_socket_and_irc_members() -> None:
    assert TransportType.SOCKET.value == "socket"
    assert TransportType.IRC.value == "irc"


def test_direction_has_inbound_and_outbound_members() -> None:
    assert Direction.INBOUND.value == "inbound"
    assert Direction.OUTBOUND.value == "outbound"


def test_transport_is_abstract_and_cannot_be_instantiated_directly() -> None:
    with pytest.raises(TypeError):
        Transport()  # type: ignore[abstract]


class TestTransportSubclassing:
    async def test_concrete_subclass_must_implement_run_and_stop(self) -> None:
        class _Incomplete(Transport):
            transport_type = TransportType.SOCKET
            direction = Direction.INBOUND

            async def run(self) -> None:  # only implements run, not stop
                pass

        with pytest.raises(TypeError):
            _Incomplete()  # type: ignore[abstract]

    async def test_fully_implemented_subclass_is_instantiable(self) -> None:
        class _FakeSocketTransport(Transport):
            transport_type = TransportType.SOCKET
            direction = Direction.INBOUND

            async def run(self) -> None:
                pass

            async def stop(self) -> None:
                pass

        instance = _FakeSocketTransport()
        assert instance.transport_type is TransportType.SOCKET
        assert instance.direction is Direction.INBOUND
