"""Music Station: the browser-source player page + its JSON queue-state read.

    GET /overlay/<community>/music         -- render the player page
    GET /overlay/<community>/music/queue   -- JSON now-playing + upcoming queue

The queue JSON is read straight from Valkey (`services/queue_reader.py`) --
see that module's own docstring for exactly why this reads Valkey directly
instead of a hub-api endpoint (hub-api has none today).
"""

from __future__ import annotations

from typing import Any

from quart import Blueprint, current_app, jsonify

from services.presentation_config_service import get_theme_config, is_surface_enabled
from services.queue_reader import MusicQueueReader, QueueTrack
from services.render import render_music
from services.surfaces import is_valid_community

music_bp = Blueprint("music_overlay", __name__, url_prefix="/overlay")


def _dal() -> tuple[Any, Any]:
    """Return `(async_dal, dal)` from app config -- set at startup, see `app.py`."""
    return current_app.config["async_dal"], current_app.config["dal"]


def _queue_reader() -> MusicQueueReader:
    """Return this process's `MusicQueueReader` -- set at startup, see `app.py`."""
    return current_app.config["MUSIC_QUEUE_READER"]  # type: ignore[no-any-return]


def _track_dict(track: QueueTrack) -> dict[str, Any]:
    """Explicit wire-schema for one queue track (security.md Output Validation).

    Named fields only -- never a raw `dataclasses.asdict()`/`**__dict__`
    dump, so `QueueTrack` can grow internal-only fields later without
    silently widening this response.
    """
    return {
        "queue_id": track.queue_id,
        "provider": track.provider,
        "external_id": track.external_id,
        "name": track.name,
        "artist": track.artist,
        "album_art_url": track.album_art_url,
        "duration_ms": track.duration_ms,
        "uri": track.uri,
        "status": track.status,
        "votes": track.votes,
    }


@music_bp.route("/<community>/music")
async def render_music_surface(community: str) -> Any:
    """Render the Music Station browser-source player page."""
    if not is_valid_community(community):
        return "invalid community", 400

    async_dal, dal = _dal()
    if not await is_surface_enabled(async_dal, dal, community=community, surface="music"):
        return "surface disabled for this community", 404
    theme = await get_theme_config(async_dal, dal, community=community)

    body = render_music(
        community,
        primary_color=theme.primary_color,
        secondary_color=theme.secondary_color,
        font_family=theme.font_family,
    )
    return body, 200, {"Content-Type": "text/html; charset=utf-8"}


@music_bp.route("/<community>/music/queue")
async def get_queue(community: str) -> Any:
    """Return `{now_playing, upcoming}` for `community`'s music queue, JSON."""
    if not is_valid_community(community):
        return jsonify({"error": "invalid community"}), 400

    tracks = await _queue_reader().get_queue(community)

    now_playing: QueueTrack | None = next((t for t in tracks if t.status == "playing"), None)
    if now_playing is None and tracks:
        # Nothing explicitly marked "playing" yet (process-stage queue
        # advance is out of this task's scope) -- show the head of the
        # queue so the player isn't empty the moment a track is requested.
        now_playing = tracks[0]

    upcoming = [t for t in tracks if t is not now_playing]

    return jsonify(
        {
            "community": community,
            "now_playing": _track_dict(now_playing) if now_playing is not None else None,
            "upcoming": [_track_dict(t) for t in upcoming],
        }
    )


BLUEPRINTS: list[Blueprint] = [music_bp]
