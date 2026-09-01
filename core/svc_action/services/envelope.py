"""Action-stage queue envelope -- the item every adapter dispatches.

Popped off `waddles:t:{tenant}:c:{community}:app:{app_id}:action`
(BRPOP, see services/queue_scanner.py + services/runner.py) as a JSON
string; `parse_envelope` validates its shape before any adapter runs.
Tenant/community/app_id come from the envelope (and, defense-in-depth,
must match the queue key they were popped from -- see runner.py) -- never
from the payload body, matching backend.md's "tenant from JWT/envelope,
never request body" convention applied to a queue consumer instead of an
HTTP request.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


class EnvelopeError(ValueError):
    """Raised when a popped queue item isn't a valid action-stage envelope."""


@dataclass(slots=True, frozen=True)
class ActionEnvelope:
    """One process->action stage item: `{tenant, community, app_id, stage, payload, ts}`."""

    tenant: str
    community: str | None
    app_id: str
    stage: str
    payload: Mapping[str, Any]
    ts: str
    raw: str  # original JSON, for audit-log storage (masked before persisting)


def parse_envelope(raw: bytes | str) -> ActionEnvelope:
    """Parse+validate one raw queue item into an :class:`ActionEnvelope`.

    Raises :class:`EnvelopeError` on malformed JSON or a missing/wrong-typed
    required field -- a poison item that can never be retried into success,
    dead-lettered by the runner rather than requeued.
    """
    text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise EnvelopeError(f"queue item is not valid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise EnvelopeError(f"queue item must be a JSON object, got {type(data).__name__}")

    for key in ("tenant", "app_id", "stage", "ts"):
        if not isinstance(data.get(key), str) or not data[key]:
            raise EnvelopeError(f"queue item missing required string field {key!r}")

    if data["stage"] != "action":
        raise EnvelopeError(f"queue item stage {data['stage']!r} is not 'action'")

    community = data.get("community")
    if community is not None and not isinstance(community, str):
        raise EnvelopeError("queue item 'community' must be a string or null")

    payload = data.get("payload")
    if not isinstance(payload, dict):
        raise EnvelopeError("queue item 'payload' must be a JSON object")

    return ActionEnvelope(
        tenant=data["tenant"],
        community=community,
        app_id=data["app_id"],
        stage=data["stage"],
        payload=payload,
        ts=data["ts"],
        raw=text,
    )
