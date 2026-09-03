"""`overlay` transport -- CLEAN SLOT, not yet implemented (assigned to a parallel worker).

Target shape (per `core/svc_presentation/services/surfaces.py::
KNOWN_SURFACES`): outbound-only, sub-types `full_screen`/`media`/
`crawler` -- SSRF-guarded HTTP POST to
`{config['presentation_base_url']}/overlay/{config['community']}/{sub_type}/push`.
Port the pre-existing, already-working logic from this repo's git history
(`core/svc_action/services/adapters/overlay.py`, pre-shared-library) onto
this module's `Transport.send(config, payload)` contract -- the delivery
logic itself does not need to be reinvented, only re-homed onto the
generic `Mapping[str, Any]` config/payload shape this library's `base.py`
declares (see `transports/http.py`/`transports/irc.py` for the pattern:
extract fields from `config` with `NonRetryableTransportError` on a
missing required one, reuse `waddle_transports.url_guard.guarded_request`
for the SSRF-guarded call).

`registry.get_transport(TransportType.OVERLAY, http_client=...)` already
resolves to this class -- implementing `send()` below is the only work
needed; no other file requires a change.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx

from waddle_transports.base import NonRetryableTransportError, Transport, TransportResult
from waddle_transports.types import Direction


class OverlayTransport(Transport):
    """`overlay` transport -- outbound only. See module docstring for the implementation slot."""

    name = "overlay"
    directions = frozenset({Direction.OUTBOUND})

    def __init__(self, *, http_client: httpx.AsyncClient | None = None) -> None:
        """`http_client` reused across calls when given; otherwise built+closed per call."""
        self._client = http_client

    async def send(self, config: Mapping[str, Any], payload: Mapping[str, Any]) -> TransportResult:
        """CLEAN SLOT -- see module docstring for the target implementation."""
        raise NonRetryableTransportError(
            "overlay transport is not yet implemented (clean slot -- see module docstring "
            "for the target shape; port core/svc_action/services/adapters/overlay.py's "
            "pre-shared-library logic onto this class's send() contract)"
        )
