"""`email` transport -- CLEAN SLOT, not yet implemented (assigned to a parallel worker).

Target shape: outbound `smtp` sub-type (real SMTP send via `aiosmtplib`,
`aiosmtplib>=5.1.2` already pinned in `requirements.in` for the
PYSEC-2026-2338/CVE-2026-55558 fix) -- port the pre-existing, already-
working logic from this repo's git history (`core/svc_action/services/
adapters/email.py`, pre-shared-library) onto this module's
`Transport.send(config, payload)` contract: `config` carries `to`/
`subject_template`/`body_template`/`smtp_host`/`smtp_port`/`smtp_user`/
`smtp_password`/`smtp_use_tls`/`smtp_from_addr` (a bundle's own config,
not a central service-wide object); `payload` is what `subject_template`/
`body_template` render against (`waddle_transports.templating.
render_template`). Inbound `imap` sub-type is explicitly out of scope for
this pass (a second, later clean slot -- do not build both at once).

`registry.get_transport(TransportType.EMAIL)` already resolves to this
class -- implementing `send()` below is the only work needed.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from waddle_transports.base import NonRetryableTransportError, Transport, TransportResult
from waddle_transports.types import Direction


class EmailTransport(Transport):
    """`email` transport -- outbound `smtp` implemented as a clean slot; inbound `imap` deferred."""

    name = "email"
    directions = frozenset({Direction.OUTBOUND})

    async def send(self, config: Mapping[str, Any], payload: Mapping[str, Any]) -> TransportResult:
        """CLEAN SLOT -- see module docstring for the target implementation."""
        raise NonRetryableTransportError(
            "email transport is not yet implemented (clean slot -- see module docstring "
            "for the target shape; port core/svc_action/services/adapters/email.py's "
            "pre-shared-library logic onto this class's send() contract)"
        )
