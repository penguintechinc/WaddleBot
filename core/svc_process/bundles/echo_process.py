"""Demo process bundle -- applies a real transform to a normalized platform event.

Referenced by `app_catalog.stages.process.entrypoint` (migration 071) as
`"bundles.echo_process:transform"` for the `waddles.core.demo.echo` bundle
that migration seeds.
"""

from __future__ import annotations

from typing import Any


async def transform(event: dict[str, Any]) -> dict[str, Any]:
    """Apply the demo bundle's process transform to one normalized platform event.

    Real, working transform (not a stub): uppercases the event's
    `payload.text` and tags it with a computed `word_count`. Raises
    `ValueError` on a malformed event -- the process runner catches this
    per-event so one bad event never kills the poll loop.
    """
    payload = event.get("payload")
    if not isinstance(payload, dict):
        raise ValueError("event missing required 'payload' object")
    text = payload.get("text")
    if not isinstance(text, str):
        raise ValueError("event payload missing required 'text' string field")

    return {
        **event,
        "payload": {
            **payload,
            "text": text.upper(),
            "word_count": len(text.split()),
        },
        "processed": True,
    }
