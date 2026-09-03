"""Twitch chat ingest bundle -- normalizes a raw fanned-out Twitch IRC chat message.

Fanned out by this container's own Twitch IRC receiver
(`receivers/twitch_irc.py`). Referenced by `app_catalog.stages.ingest.
entrypoint` (same pattern as migration 071's `bundles.echo_ingest:
normalize`) as `"bundles.twitch_ingest:normalize"` for the
`waddles.bot.twitch.default` bundle seeded by `config/postgres/
migrations/083_discord_twitch_demo_convergence.sql` (on the merged
`feature/v3-svc-gateway-discord` branch) and registered into svc-ingest's
own in-process registry at startup (`app.py`, `bundles/
twitch_gateway_manifest.py`).

Consumes the raw event shape `receivers/twitch_irc.py`'s
`TwitchIrcReceiver.receive()` LPUSHes onto this bundle's `:ingest` Valkey
key -- `{platform, channel_name, author_username, content}` -- and
produces the same `{platform, event_type, actor, payload, occurred_at}`
platform event shape `echo_ingest.py`/`discord_ingest.py` document (this
repo's own minimal convention, no repo-wide schema exists yet).

Realigned (2026-09-03) onto the merged `waddle_transports` library's
generic `IrcTransport` -- that transport does NOT parse Twitch's own
IRCv3 message tags (badges, mod/sub/broadcaster flags, numeric user id),
only the base `PRIVMSG` line, so the richer per-message metadata this
bundle's earlier draft carried (`author_id`, `is_mod`, `is_subscriber`,
`is_broadcaster`, `message_id`) is no longer available from the raw
event -- documented gap, not silently dropped.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


async def normalize(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize one raw Twitch IRC chat message event to the platform event shape.

    Real, working transform (not a stub): requires `content`/`channel_name`
    on the raw event, trims `content`, and stamps a UTC `occurred_at` when
    the raw event didn't carry its own timestamp. Raises `ValueError` on a
    malformed raw event -- the ingest runner catches this per-event so one
    bad event never kills the poll loop (`core/svc_ingest/runner.py`).
    """
    content = raw.get("content")
    channel_name = raw.get("channel_name")
    if not isinstance(content, str) or not content:
        raise ValueError("raw Twitch event missing required 'content' string field")
    if not channel_name or not isinstance(channel_name, str):
        raise ValueError("raw Twitch event missing required 'channel_name' string field")

    return {
        "platform": raw.get("platform", "twitch"),
        "event_type": "message",
        "actor": raw.get("author_username") or "unknown",
        "payload": {
            "text": content.strip(),
            "channel_name": channel_name,
        },
        "occurred_at": raw.get("occurred_at") or datetime.now(UTC).isoformat(),
    }
