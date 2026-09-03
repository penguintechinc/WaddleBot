"""Twitch EventSub ingest bundle -- normalizes a raw fanned-out EventSub notification.

Fanned out by this container's own EventSub webhook handler
(`eventsub.py`, mounted at `POST /eventsub/twitch/webhook` in `app.py`).
Referenced by `app_catalog.stages.ingest.entrypoint` as
`"bundles.twitch_eventsub_ingest:normalize"` for the
`waddles.bot.twitch.eventsub` bundle seeded by `config/postgres/
migrations/082_twitch_gateway_bundle.sql`.

Consumes the raw event shape `eventsub.py`'s `build_raw_event` LPUSHes
onto this bundle's `:ingest` Valkey key -- `{platform, event_type,
broadcaster_id, broadcaster_login, user_id, user_login, user_display_name,
metadata}` -- ported from `trigger/receiver/twitch_module/services/
eventsub_handler.py`'s own `_build_event_data` field set, trimmed to the
subset this connector's MVP normalizes (follow/subscribe/subscription-gift/
cheer/raid) -- and produces the same `{platform, event_type, actor,
payload, occurred_at}` platform event shape `twitch_ingest.py` documents.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

#: EventSub subscription types this connector's MVP normalizes -- matches
#: `eventsub.py`'s own `DEFAULT_SUBSCRIPTION_TYPES`, ported from the
#: legacy module's `subscribe_to_events` default list.
KNOWN_EVENT_TYPES = frozenset(
    {
        "channel.follow",
        "channel.subscribe",
        "channel.subscription.gift",
        "channel.cheer",
        "channel.raid",
    }
)


async def normalize(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize one raw Twitch EventSub notification to the platform event shape.

    Real, working transform (not a stub): requires `event_type`/
    `broadcaster_id` on the raw event, rejects an `event_type` outside
    :data:`KNOWN_EVENT_TYPES`. Raises `ValueError` on a malformed/
    unsupported raw event -- the ingest runner catches this per-event so
    one bad event never kills the poll loop.
    """
    event_type = raw.get("event_type")
    broadcaster_id = raw.get("broadcaster_id")
    if not isinstance(event_type, str) or event_type not in KNOWN_EVENT_TYPES:
        raise ValueError(
            f"raw Twitch EventSub event has unsupported event_type {event_type!r}, "
            f"expected one of {sorted(KNOWN_EVENT_TYPES)}"
        )
    if not broadcaster_id or not isinstance(broadcaster_id, str):
        raise ValueError("raw Twitch EventSub event missing required 'broadcaster_id' string field")

    actor = raw.get("user_login") or raw.get("user_id") or broadcaster_id
    return {
        "platform": raw.get("platform", "twitch"),
        "event_type": event_type,
        "actor": actor,
        "payload": {
            "broadcaster_id": broadcaster_id,
            "broadcaster_login": raw.get("broadcaster_login"),
            "user_id": raw.get("user_id"),
            "user_login": raw.get("user_login"),
            "user_display_name": raw.get("user_display_name"),
            "metadata": raw.get("metadata") or {},
        },
        "occurred_at": raw.get("occurred_at") or datetime.now(UTC).isoformat(),
    }
