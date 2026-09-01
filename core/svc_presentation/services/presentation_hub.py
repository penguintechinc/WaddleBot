"""Live-update fan-out for per-community overlay browser sources (Server-Sent Events).

`PresentationHub` is the one real distribution mechanism behind every
`/overlay/<community>/<surface>/push` call: a push is published to a Valkey
pub/sub channel (`VALKEY_URL`/`REDIS_URL`, see `config.py`) so every
svc-presentation replica -- including the one that received the POST --
stays in sync, and a single background subscriber task per process fans
each message out to that process's own locally-connected SSE clients
(`asyncio.Queue` per connection). When no Valkey URL is configured (local
dev, most unit tests) the hub falls back to pure in-process delivery --
`enable_fallback` mirrors the exact pattern `flask_core.cache.CacheManager`
and `core/unified_music_module/services/unified_queue.py.UnifiedQueue`
already use elsewhere in this repo, never crashing on a missing broker.

SSE (not python-socketio) was the live-channel choice for this scaffold:
no second ASGI app to mount alongside Quart's own (`hypercorn app:app`),
trivially testable via Quart's native streaming `Response`, and OBS
browser sources (plain Chromium) support `EventSource` natively with zero
extra JS dependency.
"""

from __future__ import annotations

import asyncio
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

#: Channel naming: `presentation:{community}:{surface}` -- psubscribe
#: pattern below matches exactly this shape.
_CHANNEL_PREFIX = "presentation"
_CHANNEL_PATTERN = f"{_CHANNEL_PREFIX}:*:*"


def _channel(community: str, surface: str) -> str:
    """Build the Valkey pub/sub channel name for one community+surface."""
    return f"{_CHANNEL_PREFIX}:{community}:{surface}"


def _parse_channel(channel: str) -> tuple[str, str] | None:
    """Recover `(community, surface)` from a channel name; `None` if malformed."""
    parts = channel.split(":", 2)
    if len(parts) != 3 or parts[0] != _CHANNEL_PREFIX:
        return None
    return parts[1], parts[2]


@dataclass(slots=True)
class PresentationHub:
    """Owns local SSE subscriber queues and (optionally) a Valkey pub/sub relay."""

    valkey_url: str | None = None
    _redis: Any | None = field(default=None, init=False, repr=False)
    _pubsub: Any | None = field(default=None, init=False, repr=False)
    _listen_task: asyncio.Task[None] | None = field(default=None, init=False, repr=False)
    _local: dict[tuple[str, str], set[asyncio.Queue[dict[str, Any]]]] = field(
        default_factory=dict, init=False, repr=False
    )
    fallback_mode: bool = field(default=True, init=False)

    async def start(self) -> None:
        """Connect to Valkey and start the pub/sub relay loop, if configured."""
        if not self.valkey_url or not REDIS_AVAILABLE:
            logger.warning(
                "presentation_hub.fallback_mode reason=%s",
                "no_valkey_url" if not self.valkey_url else "redis_package_missing",
            )
            self.fallback_mode = True
            return

        try:
            self._redis = redis_asyncio.from_url(
                self.valkey_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=None,
            )
            await self._redis.ping()
            self._pubsub = self._redis.pubsub()
            await self._pubsub.psubscribe(_CHANNEL_PATTERN)
            self._listen_task = asyncio.create_task(self._listen_loop())
            self.fallback_mode = False
            logger.info("presentation_hub.connected pattern=%s", _CHANNEL_PATTERN)
        except Exception:  # noqa: BLE001 - broker unavailability must not crash startup
            logger.exception("presentation_hub.connect_failed")
            self.fallback_mode = True

    async def stop(self) -> None:
        """Cancel the relay loop and close the Valkey connection."""
        if self._listen_task is not None:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
        if self._pubsub is not None:
            await self._pubsub.close()
        if self._redis is not None:
            await self._redis.close()

    async def _listen_loop(self) -> None:
        """Background task: relay every Valkey pub/sub message to local subscribers."""
        assert self._pubsub is not None  # noqa: S101 - only scheduled after psubscribe succeeds
        async for message in self._pubsub.listen():
            if message.get("type") != "pmessage":
                continue
            parsed = _parse_channel(message["channel"])
            if parsed is None:
                continue
            community, surface = parsed
            try:
                payload = json.loads(message["data"])
            except (TypeError, ValueError):
                logger.warning("presentation_hub.bad_payload channel=%s", message["channel"])
                continue
            await self._deliver_local(community, surface, payload)

    def register(self, community: str, surface: str) -> asyncio.Queue[dict[str, Any]]:
        """Register a new SSE connection's queue for `community`/`surface`."""
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=64)
        self._local.setdefault((community, surface), set()).add(queue)
        return queue

    def unregister(self, community: str, surface: str, queue: asyncio.Queue[dict[str, Any]]) -> None:
        """Drop a disconnected SSE connection's queue."""
        subscribers = self._local.get((community, surface))
        if subscribers is not None:
            subscribers.discard(queue)
            if not subscribers:
                del self._local[(community, surface)]

    def local_subscriber_count(self, community: str, surface: str) -> int:
        """Number of SSE clients currently connected to this process for `community`/`surface`."""
        return len(self._local.get((community, surface), ()))

    async def publish(self, community: str, surface: str, payload: dict[str, Any]) -> None:
        """Push `payload` to every connected browser-source client for `community`/`surface`.

        Connected via Valkey: published once; the relay loop (running in
        every replica, including this process) delivers it locally -- a
        single code path, so the publishing instance never double-delivers
        to its own local subscribers. Fallback mode (no Valkey): delivered
        directly to this process's local subscribers only.
        """
        if not self.fallback_mode and self._redis is not None:
            await self._redis.publish(_channel(community, surface), json.dumps(payload))
        else:
            await self._deliver_local(community, surface, payload)

    async def _deliver_local(self, community: str, surface: str, payload: dict[str, Any]) -> None:
        """Fan `payload` out to every locally-registered queue for `community`/`surface`."""
        for queue in list(self._local.get((community, surface), ())):
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                logger.warning(
                    "presentation_hub.queue_full community=%s surface=%s", community, surface
                )
