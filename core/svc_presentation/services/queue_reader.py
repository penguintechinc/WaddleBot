"""Read a community's music queue directly from Valkey.

hub-api has no `GET .../music/queue` endpoint today (confirmed:
`hub_api/blueprints/v1/music.py` exposes only settings/providers/
radio-stations -- zero repo-wide hits for a queue route). The only real,
already-implemented per-community queue state is the Redis/Valkey key
`core/unified_music_module/services/unified_queue.py`'s `UnifiedQueue`
writes and reads (`_make_key`, `unified_queue.py:180-182`:
`f"{namespace}:{community_id}:queue"`, JSON array of `QueueItem.to_dict()`
-- `unified_queue.py:69-76`). This module reads that exact key/shape
directly (read-only, no write path here) rather than importing
`unified_music_module` as a cross-service dependency -- svc-presentation
is its own deployable container with its own `requirements.txt`; each
stage-runner in this repo talks to shared state over the wire (Valkey),
never via a Python import across container boundaries.

Track field names below (`provider`, `external_id`) are pinned to this
task's own wire contract; `external_id` maps from `MusicTrack.track_id`
(`base_provider.py:14-37`) -- the DRAFT `Track` model in
`docs/plans/2026-08-31-music-station-design.md` §2 proposes renaming this
to `source_id`, but that model is undecided/unimplemented (§11), so this
reader targets today's real, live schema, not tomorrow's proposed one.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

try:
    import redis.asyncio as redis_asyncio

    REDIS_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised only if redis isn't installed
    REDIS_AVAILABLE = False
    redis_asyncio = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

#: Providers with a real, documented client-side embed today (task scope:
#: YouTube IFrame API + Spotify embed). SoundCloud tracks still render in
#: the queue/now-playing list -- just without a player embed (no fake
#: player, an honestly-absent one).
EMBEDDABLE_PROVIDERS: frozenset[str] = frozenset({"youtube", "spotify"})


@dataclass(slots=True)
class QueueTrack:
    """One normalized queue entry as rendered to the Music Station overlay."""

    queue_id: str
    provider: str
    external_id: str
    name: str
    artist: str
    album_art_url: str
    duration_ms: int
    uri: str
    status: str
    position: int
    votes: int


@dataclass(slots=True)
class MusicQueueReader:
    """Read-only Valkey client for the `UnifiedQueue`-compatible community queue key."""

    valkey_url: str | None
    namespace: str = "music_queue"
    _redis: Any | None = field(default=None, init=False, repr=False)
    connected: bool = field(default=False, init=False)

    async def start(self) -> None:
        """Connect to Valkey, if configured. Never raises -- missing broker means empty queues."""
        if not self.valkey_url or not REDIS_AVAILABLE:
            logger.warning("music_queue_reader.no_backend -- queue reads will return empty")
            return
        try:
            self._redis = redis_asyncio.from_url(
                self.valkey_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            await self._redis.ping()
            self.connected = True
            logger.info("music_queue_reader.connected namespace=%s", self.namespace)
        except Exception:  # noqa: BLE001 - broker unavailability must not crash startup
            logger.exception("music_queue_reader.connect_failed")
            self.connected = False

    async def stop(self) -> None:
        """Close the Valkey connection."""
        if self._redis is not None:
            await self._redis.close()

    def _key(self, community_id: str) -> str:
        """`{namespace}:{community_id}:queue` -- matches `UnifiedQueue._make_key` exactly."""
        return f"{self.namespace}:{community_id}:queue"

    async def get_queue(self, community_id: str) -> list[QueueTrack]:
        """Return the active (queued/playing) tracks for `community_id`, sorted by position."""
        if not self.connected or self._redis is None:
            return []
        try:
            raw = await self._redis.get(self._key(community_id))
        except Exception:  # noqa: BLE001 - a transient Valkey error must not 500 the overlay
            logger.exception("music_queue_reader.read_failed community=%s", community_id)
            return []
        if not raw:
            return []
        try:
            items = json.loads(raw)
        except (TypeError, ValueError):
            logger.warning("music_queue_reader.bad_payload community=%s", community_id)
            return []

        tracks: list[QueueTrack] = []
        for item in items:
            status = item.get("status")
            if status not in ("queued", "playing"):
                continue
            track = item.get("track") or {}
            tracks.append(
                QueueTrack(
                    queue_id=str(item.get("id", "")),
                    provider=str(track.get("provider", "")),
                    external_id=str(track.get("track_id", "")),
                    name=str(track.get("name", "Unknown Track")),
                    artist=str(track.get("artist", "Unknown Artist")),
                    album_art_url=str(track.get("album_art_url", "")),
                    duration_ms=int(track.get("duration_ms", 0) or 0),
                    uri=str(track.get("uri", "")),
                    status=str(status),
                    position=int(item.get("position", 0) or 0),
                    votes=int(item.get("votes", 0) or 0),
                )
            )
        tracks.sort(key=lambda t: t.position)
        return tracks
