"""Action-stage queue envelope -- the item every adapter dispatches.

Popped off `waddles:t:{tenant}:c:{community}:app:{app_id}:action` (RPOP,
`runner.py::_dispatch_bundle`) as a JSON string. `parse_envelope` decodes
it into the shared, frozen `flask_core.StageEnvelope` contract -- the ONE
typed pipeline object every stage (ingest/process/action) now passes
between each other; svc-action no longer defines its own envelope shape.
Tenant/community/app_id come from the envelope (and, defense-in-depth,
must match the queue key they were popped from -- see runner.py) -- never
from the payload body, matching backend.md's "tenant from JWT/envelope,
never request body" convention applied to a queue consumer instead of an
HTTP request. Message data (text, channel_id, ...) lives one level deeper
than it used to: `envelope.event.payload[...]`, never `envelope.payload[...]`.

`ActionEnvelope` is kept as an alias, not a second type -- callers that
still spell it that way (bundles, tests) get the exact same
`StageEnvelope` object; there is only one envelope type in this codebase.
"""

from __future__ import annotations

import json
from typing import Any

from flask_core import EnvelopeError, StageEnvelope

__all__ = ["ActionEnvelope", "EnvelopeError", "parse_envelope"]

#: No second envelope type -- every reference to the pre-Wave-2 local name
#: resolves to the shared, frozen contract.
ActionEnvelope = StageEnvelope


def parse_envelope(raw: bytes | str) -> StageEnvelope:
    """Parse+validate one raw queue item into a shared :class:`StageEnvelope`.

    The wire format is `StageEnvelope.to_dict()`'s own shape (a JSON object
    carrying the event under an `event` key, never `payload`). Raises
    :class:`EnvelopeError` on malformed JSON, a non-object top level, a
    missing/wrong-typed required field, or a `stage` that isn't `'action'`
    -- a poison item that can never be retried into success, dead-lettered
    by the runner rather than requeued.
    """
    text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
    try:
        data: Any = json.loads(text)
    except json.JSONDecodeError as exc:
        raise EnvelopeError(f"queue item is not valid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise EnvelopeError(f"queue item must be a JSON object, got {type(data).__name__}")

    envelope = StageEnvelope.from_dict(data)
    if envelope.stage != "action":
        raise EnvelopeError(f"queue item stage {envelope.stage!r} is not 'action'")
    return envelope
