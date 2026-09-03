"""`socket` transport -- generic WebSocket connect+receive/send. Inbound primary.

Real, working generic WebSocket client (`websockets` library -- pure
Python, already an established dependency elsewhere in this repo:
`services/trigger-webhooks`, `trigger/receiver/mattermost_module`), no
sub_type (one protocol: WebSocket).

**Inbound** (primary use case -- Discord Gateway, Slack Socket Mode):
connects once, yields one dict per frame received (`{"raw": <str|bytes>}`
for a text/binary frame; a `config["parse_json"]=True` -- the default --
additionally attempts `json.loads` on a text frame and yields the parsed
object under `"data"` when it succeeds).

**Outbound** (where supported): connects, sends one frame, closes.

**Documented limitation, not a stub**: this transport implements the
*generic* WebSocket protocol only -- it does not speak Discord Gateway's
or Slack Socket Mode's own application-level protocol (opcodes,
heartbeat/ACK cycles, session resume, sequence-number tracking). A
connector needing that owns its own protocol logic on top of this
primitive's raw frame stream, exactly like `bundles/discord_send_action.py`
owns its Discord-specific logic instead of routing through a generic HTTP
primitive (see that module's docstring for the same pattern applied to
`http`/`grpc`).
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Mapping
from typing import Any

import websockets
from websockets.exceptions import ConnectionClosed, InvalidURI, WebSocketException

from waddle_transports.base import (
    NonRetryableTransportError,
    RetryableTransportError,
    Transport,
    TransportResult,
)
from waddle_transports.types import Direction

_DEFAULT_TIMEOUT_SECONDS = 10.0


class SocketTransport(Transport):
    """`socket` transport -- generic WebSocket, no sub_type."""

    name = "socket"
    directions = frozenset({Direction.OUTBOUND, Direction.INBOUND})

    async def send(self, config: Mapping[str, Any], payload: Mapping[str, Any]) -> TransportResult:
        """Connect, send one frame (JSON `payload`, or `config['raw_message']` verbatim), close."""
        url = config.get("url")
        if not isinstance(url, str) or not url:
            raise NonRetryableTransportError("socket config missing required 'url'")
        timeout_seconds = float(config.get("timeout_seconds", _DEFAULT_TIMEOUT_SECONDS))

        raw_message = config.get("raw_message")
        message = raw_message if isinstance(raw_message, str) else json.dumps(dict(payload))

        try:
            async with websockets.connect(url, open_timeout=timeout_seconds) as ws:
                await ws.send(message)
        except InvalidURI as exc:
            raise NonRetryableTransportError(f"socket URL is invalid: {exc}") from exc
        except (TimeoutError, OSError, ConnectionClosed, WebSocketException) as exc:
            raise RetryableTransportError(f"socket send failed: {exc}") from exc

        return TransportResult(transport="socket", detail=f"sent {len(message)} byte(s) to {url}")

    async def receive(self, config: Mapping[str, Any]) -> AsyncIterator[Mapping[str, Any]]:
        """Connect once, yield one dict per frame received until the connection closes.

        `config["parse_json"]` (default `True`): also attempt `json.loads`
        on each text frame, yielding the parsed object under `"data"` in
        addition to the raw frame under `"raw"` -- a malformed frame still
        yields (`"raw"` only, `"data"` omitted), never dropped silently.
        """
        url = config.get("url")
        if not isinstance(url, str) or not url:
            raise NonRetryableTransportError("socket config missing required 'url'")
        timeout_seconds = float(config.get("timeout_seconds", _DEFAULT_TIMEOUT_SECONDS))
        parse_json = bool(config.get("parse_json", True))
        max_messages = config.get("_max_messages")  # test-only escape hatch, see tests

        try:
            async with websockets.connect(url, open_timeout=timeout_seconds) as ws:
                received = 0
                async for raw in ws:
                    item: dict[str, Any] = {"raw": raw}
                    if parse_json:
                        try:
                            item["data"] = json.loads(raw)
                        except (TypeError, ValueError):
                            pass  # not JSON -- "raw" alone is still yielded
                    yield item
                    received += 1
                    if max_messages is not None and received >= max_messages:
                        return
        except InvalidURI as exc:
            raise NonRetryableTransportError(f"socket URL is invalid: {exc}") from exc
        except (TimeoutError, OSError, ConnectionClosed, WebSocketException) as exc:
            raise RetryableTransportError(f"socket receive failed: {exc}") from exc
