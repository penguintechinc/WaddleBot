"""waddle_transports -- shared inbound/outbound transport-primitives library.

One package, imported by every pipeline-stage service that needs to
either dispatch an outbound delivery (`core/svc_action`) or poll/consume
an inbound source (`core/svc_ingest`, platform connector bundles) --
see the package README for the transport x direction matrix.
"""

from __future__ import annotations

from waddle_transports.base import (
    NonRetryableTransportError,
    RetryableTransportError,
    Transport,
    TransportResult,
)
from waddle_transports.registry import get_transport
from waddle_transports.types import Direction, TransportType

__all__ = [
    "Direction",
    "NonRetryableTransportError",
    "RetryableTransportError",
    "Transport",
    "TransportResult",
    "TransportType",
    "get_transport",
]
