"""Demo ingest bundle -- normalizes a raw inbound event to the platform event shape.

Referenced by `app_catalog.stages.ingest.entrypoint` (migration 071) as
`"bundles.echo_ingest:normalize"` for the `waddles.core.demo.echo` bundle
that migration seeds. No repo-wide "platform event shape" schema exists yet
(no `PlatformEvent`/`normalized_event` convention found anywhere in this
codebase) -- this module documents its own minimal, sensible shape:
`{platform, event_type, actor, payload, occurred_at}`.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


async def normalize(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize one raw inbound event dict to the platform event shape.

    Real, working transform (not a stub): requires `source`/`text` on the
    raw event, trims `text`, and stamps a UTC `occurred_at` when the raw
    event didn't carry its own timestamp. Raises `ValueError` on a
    malformed raw event -- the ingest runner catches this per-event so one
    bad event never kills the poll loop.
    """
    source = raw.get("source")
    text = raw.get("text")
    if not source or not isinstance(source, str):
        raise ValueError("raw event missing required 'source' string field")
    if not text or not isinstance(text, str):
        raise ValueError("raw event missing required 'text' string field")

    return {
        "platform": source,
        "event_type": raw.get("event_type", "message"),
        "actor": raw.get("actor", "unknown"),
        "payload": {"text": text.strip()},
        "occurred_at": raw.get("occurred_at") or datetime.now(UTC).isoformat(),
    }
