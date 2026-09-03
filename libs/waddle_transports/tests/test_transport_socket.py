"""transports/socket.py -- real generic WebSocket connect+send/receive over a real local server.

No mocking of the transport -- `websockets.serve()` runs a genuine
loopback WebSocket server; this transport connects to it as a real client.
"""

from __future__ import annotations

import json

import pytest
import websockets

from waddle_transports.base import NonRetryableTransportError, RetryableTransportError
from waddle_transports.transports.socket import SocketTransport


@pytest.fixture
async def echo_server():
    """Echoes every received frame straight back."""

    async def _handler(ws):  # noqa: ANN001
        async for message in ws:
            await ws.send(message)

    server = await websockets.serve(_handler, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    yield f"ws://127.0.0.1:{port}"
    server.close()
    await server.wait_closed()


@pytest.fixture
async def push_server():
    """Pushes two frames (one JSON, one plain text) to every connecting client, then closes."""

    async def _handler(ws):  # noqa: ANN001
        await ws.send(json.dumps({"event": "hello", "n": 1}))
        await ws.send("not-json")

    server = await websockets.serve(_handler, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    yield f"ws://127.0.0.1:{port}"
    server.close()
    await server.wait_closed()


class TestSend:
    async def test_sends_json_serialized_payload(self, echo_server: str) -> None:
        transport = SocketTransport()
        result = await transport.send({"url": echo_server}, {"text": "hello"})
        assert result.transport == "socket"
        assert echo_server in result.detail

    async def test_sends_raw_message_verbatim(self, echo_server: str) -> None:
        transport = SocketTransport()
        result = await transport.send({"url": echo_server, "raw_message": "PING"}, {})
        assert result.transport == "socket"

    async def test_missing_url_is_non_retryable(self) -> None:
        transport = SocketTransport()
        with pytest.raises(NonRetryableTransportError, match="url"):
            await transport.send({}, {})

    async def test_invalid_url_is_non_retryable(self) -> None:
        transport = SocketTransport()
        with pytest.raises(NonRetryableTransportError, match="invalid"):
            await transport.send({"url": "not-a-websocket-url"}, {})

    async def test_connection_refused_is_retryable(self) -> None:
        transport = SocketTransport()
        with pytest.raises(RetryableTransportError):
            await transport.send({"url": "ws://127.0.0.1:1", "timeout_seconds": 2.0}, {})


class TestReceive:
    async def test_yields_parsed_json_and_raw_text_frames(self, push_server: str) -> None:
        transport = SocketTransport()
        items = [item async for item in transport.receive({"url": push_server, "_max_messages": 2})]

        assert items[0]["data"] == {"event": "hello", "n": 1}
        assert items[0]["raw"] == json.dumps({"event": "hello", "n": 1})
        assert "data" not in items[1]
        assert items[1]["raw"] == "not-json"

    async def test_parse_json_false_never_populates_data(self, push_server: str) -> None:
        transport = SocketTransport()
        items = [
            item
            async for item in transport.receive(
                {"url": push_server, "parse_json": False, "_max_messages": 1}
            )
        ]
        assert "data" not in items[0]

    async def test_missing_url_is_non_retryable(self) -> None:
        transport = SocketTransport()
        with pytest.raises(NonRetryableTransportError, match="url"):
            async for _item in transport.receive({}):
                pass

    async def test_connection_refused_is_retryable(self) -> None:
        transport = SocketTransport()
        with pytest.raises(RetryableTransportError):
            async for _item in transport.receive(
                {"url": "ws://127.0.0.1:1", "timeout_seconds": 2.0}
            ):
                pass
