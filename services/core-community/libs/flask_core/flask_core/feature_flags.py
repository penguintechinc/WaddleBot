"""
Feature-Flag Evaluation Service
================================

Shared, Redis-cached feature-flag evaluator for all Waddles modules.

Backing table (migration 068)::

    feature_flags(id, flag_key, community_id NULL, platform NULL,
                  is_enabled, rollout_pct, description, updated_by,
                  created_at, updated_at)
    UNIQUE (flag_key, COALESCE(community_id, -1), COALESCE(platform, '*'))

Resolution picks the *most specific* matching row for a
``(flag_key, community_id, platform)`` lookup, in this order (first match
wins)::

    1. (community_id, platform)   -- exact community + exact platform
    2. (community_id, NULL)       -- exact community, all platforms
    3. (NULL, platform)           -- global community, exact platform
    4. (NULL, NULL)               -- global default

Fail-open semantics: when no row matches, or when Redis / the DB raise, the
caller-supplied ``default`` is returned (an absent flag means the feature is
on). A matched row with ``is_enabled = false`` is an explicit kill-switch and
returns ``False``. When ``is_enabled = true`` and ``rollout_pct < 100`` a
deterministic, sticky bucketing decides the result so the same
``(flag_key, community_id)`` always lands the same way.

Redis-client vs CacheManager
----------------------------
This service takes a **raw** ``redis.asyncio`` client (the same object the
Router already holds and the object ``AiChatterConfigCache`` consumes), not a
``flask_core.CacheManager``. Rationale: the Router and the platform receivers
pass their bare Redis connection around directly, and this service needs
``PUBLISH`` + ``SCAN`` for reload fan-out / cache invalidation -- surface that
``CacheManager`` does not expose. A raw client is therefore the lowest common
denominator that *both* the Router and other ``flask_core`` consumers already
have on hand, so no adapter is required at any call site. The ``__init__``
signature stays ``(redis_client, dal, default_ttl)`` regardless.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

#: Redis Pub/Sub channel used to broadcast cache-invalidation reloads.
RELOAD_CHANNEL = "feature_flags:reload"


@dataclass(slots=True)
class _FlagRow:
    """A single ``feature_flags`` row materialized for specificity ranking."""

    community_id: int | None
    platform: str | None
    is_enabled: bool
    rollout_pct: int


class FeatureFlagService:
    """
    Evaluate feature flags with a most-specific-wins resolution and a
    Redis-cached final boolean.

    All public evaluation paths are fail-open: any Redis or DB error is logged
    at ``warning`` level and the caller-supplied ``default`` is returned.
    """

    def __init__(self, redis_client: Any, dal: Any, default_ttl: int = 300) -> None:
        """
        Args:
            redis_client: Raw ``redis.asyncio`` client (may be ``None`` -- the
                service then falls straight through to the DB and never caches).
            dal: Object exposing a synchronous ``executesql(sql, params)`` that
                returns a list of row tuples (PyDAL ``AsyncDAL`` / DAL).
            default_ttl: TTL in seconds for cached boolean results.
        """
        self.redis = redis_client
        self.dal = dal
        self.default_ttl = default_ttl

    # ------------------------------------------------------------------ #
    # Key helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _cache_key(
        flag_key: str, community_id: int | None, platform: str | None
    ) -> str:
        scope = community_id if community_id is not None else "global"
        return f"feature_flag:{scope}:{flag_key}:{platform or '*'}"

    @staticmethod
    def _invalidate_pattern(flag_key: str) -> str:
        # Matches every community/platform variant cached for this flag.
        return f"feature_flag:*:{flag_key}:*"

    @staticmethod
    def _bucket_enabled(
        flag_key: str, community_id: int | None, rollout_pct: int
    ) -> bool:
        """Deterministic sticky bucketing: same inputs -> same decision."""
        scope = community_id if community_id is not None else "global"
        digest = hashlib.sha256(f"{flag_key}:{scope}".encode()).hexdigest()
        return int(digest, 16) % 100 < rollout_pct

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    async def is_enabled(
        self,
        flag_key: str,
        community_id: int | None = None,
        platform: str | None = None,
        *,
        default: bool = True,
    ) -> bool:
        """
        Resolve whether ``flag_key`` is enabled for the given scope.

        Checks the Redis cache first; on a miss, resolves from the DB (one
        parameterized query fetching every row for ``flag_key`` scoped to the
        community, then picks specificity in Python) and caches the boolean.

        Returns ``default`` when no row matches or on any Redis/DB failure.
        """
        cache_key = self._cache_key(flag_key, community_id, platform)

        # 1) Cache fast-path.
        try:
            if self.redis is not None:
                cached = await self.redis.get(cache_key)
                if cached is not None:
                    return self._decode_bool(cached)
        except Exception as e:  # noqa: BLE001 - fail open on cache errors
            logger.warning(
                "Feature flag cache read failed for %s: %s", cache_key, e
            )
            return default

        # 2) Resolve from the DB.
        try:
            rows = self._fetch_rows(flag_key, community_id)
        except Exception as e:  # noqa: BLE001 - fail open on DB errors
            logger.warning(
                "Feature flag DB lookup failed for %s: %s", flag_key, e
            )
            return default

        row = self._pick_most_specific(rows, community_id, platform)
        if row is None:
            # Absent flag -> feature on (fail open). Not cached: the flag may be
            # created at any moment and we want to pick it up promptly.
            return default

        if not row.is_enabled:
            result = False
        elif row.rollout_pct >= 100:
            result = True
        elif row.rollout_pct <= 0:
            result = False
        else:
            result = self._bucket_enabled(flag_key, community_id, row.rollout_pct)

        # 3) Cache the resolved boolean (best-effort).
        try:
            if self.redis is not None:
                await self.redis.setex(
                    cache_key, self.default_ttl, b"1" if result else b"0"
                )
        except Exception as e:  # noqa: BLE001 - caching is best effort
            logger.warning(
                "Feature flag cache write failed for %s: %s", cache_key, e
            )

        return result

    async def publish_reload(
        self, flag_key: str, community_id: int | None = None
    ) -> None:
        """
        Broadcast a cache-invalidation reload for ``flag_key`` on the
        ``feature_flags:reload`` channel. Best-effort: logs and swallows errors.
        """
        payload = json.dumps({"flag_key": flag_key, "community_id": community_id})
        try:
            if self.redis is not None:
                await self.redis.publish(RELOAD_CHANNEL, payload)
        except Exception as e:  # noqa: BLE001 - reload publish is best effort
            logger.warning(
                "Feature flag reload publish failed for %s: %s", flag_key, e
            )

    async def handle_reload(self, message: dict[str, Any]) -> None:
        """
        Handle a reload message (a payload dict, or a raw Redis Pub/Sub message
        whose ``data`` holds the JSON payload) by invalidating every cached key
        for the referenced flag (``feature_flag:*:{flag_key}:*``).
        """
        try:
            payload = self._extract_payload(message)
            flag_key = payload.get("flag_key")
            if not flag_key:
                return
            await self._invalidate(flag_key)
        except Exception as e:  # noqa: BLE001 - invalidation is best effort
            logger.warning("Feature flag reload handling failed: %s", e)

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #
    def _fetch_rows(self, flag_key: str, community_id: int | None) -> list[_FlagRow]:
        """Fetch all candidate rows for ``flag_key`` scoped to the community."""
        result = self.dal.executesql(
            """SELECT community_id, platform, is_enabled, rollout_pct
                 FROM feature_flags
                WHERE flag_key = %s
                  AND (community_id IS NULL OR community_id = %s)""",
            [flag_key, community_id],
        )
        rows: list[_FlagRow] = []
        for raw in result or []:
            rows.append(
                _FlagRow(
                    community_id=raw[0],
                    platform=raw[1],
                    is_enabled=bool(raw[2]),
                    rollout_pct=int(raw[3]) if raw[3] is not None else 100,
                )
            )
        return rows

    @staticmethod
    def _pick_most_specific(
        rows: list[_FlagRow], community_id: int | None, platform: str | None
    ) -> _FlagRow | None:
        """
        Return the highest-specificity row matching the scope, or ``None``.

        Community specificity dominates platform specificity, so a
        community-scoped row always beats a global row even when the global row
        is platform-specific.
        """
        best: _FlagRow | None = None
        best_score = -1
        for row in rows:
            comm_specific = row.community_id is not None and row.community_id == community_id
            comm_global = row.community_id is None
            if not (comm_specific or comm_global):
                continue

            plat_specific = (
                row.platform is not None
                and platform is not None
                and row.platform == platform
            )
            plat_global = row.platform is None
            if not (plat_specific or plat_global):
                continue

            # Community rank weighted above platform rank so it always dominates.
            score = (2 if comm_specific else 1) * 10 + (2 if plat_specific else 1)
            if score > best_score:
                best_score = score
                best = row
        return best

    async def _invalidate(self, flag_key: str) -> None:
        """SCAN + DEL every cache key for ``flag_key`` (raw-client path)."""
        if self.redis is None:
            return
        pattern = self._invalidate_pattern(flag_key)
        async for key in self.redis.scan_iter(match=pattern):
            await self.redis.delete(key)

    @staticmethod
    def _decode_bool(cached: Any) -> bool:
        """Coerce a cached Redis value (bytes or str, ``1``/``0``) to bool."""
        if isinstance(cached, (bytes, bytearray)):
            cached = cached.decode()
        return str(cached) == "1"

    @staticmethod
    def _extract_payload(message: dict[str, Any]) -> dict[str, Any]:
        """
        Normalize a reload message into its payload dict. Accepts both a bare
        payload ``{"flag_key": ...}`` and a Redis Pub/Sub envelope whose
        ``data`` holds the JSON string.
        """
        data = message.get("data") if isinstance(message, dict) else None
        if data is not None and not isinstance(data, dict):
            if isinstance(data, (bytes, bytearray)):
                data = data.decode()
            try:
                parsed = json.loads(data)
                if isinstance(parsed, dict):
                    return parsed
            except (ValueError, TypeError):
                pass
        return message


def create_feature_flag_service(
    redis_client: Any, dal: Any, default_ttl: int = 300
) -> FeatureFlagService:
    """Factory for :class:`FeatureFlagService`."""
    return FeatureFlagService(redis_client=redis_client, dal=dal, default_ttl=default_ttl)
