"""
Chatter Configuration Service
================================
Fetches and caches community AIChatter configuration.
Redis cache with 60s TTL, DB fallback.
"""
import json
from typing import Optional


class ChatterConfigService:
    """Manages community AIChatter configuration with Redis caching."""

    CACHE_TTL = 60  # seconds

    def __init__(self, dal, redis_client, logger):
        self.dal = dal
        self.redis = redis_client
        self.logger = logger

    def _cache_key(self, community_id: int) -> str:
        return f"ai_chatter_config:{community_id}"

    async def get_community_config(self, community_id: int) -> Optional[dict]:
        """
        Get community AIChatter config. Redis cache -> DB fallback.
        Returns None if community has no config (treat as disabled).
        """
        cache_key = self._cache_key(community_id)

        # Try Redis
        try:
            if self.redis:
                cached = await self.redis.get(cache_key)
                if cached:
                    return json.loads(cached)
        except Exception as e:
            self.logger.warning(
                f"Redis cache miss for chatter config: {e}",
                community_id=community_id
            )

        # DB fallback
        try:
            result = self.dal.executesql(
                """SELECT enabled, max_responses_per_window, window_seconds,
                          max_per_user_per_window, response_probability, min_message_length
                   FROM community_ai_chatter_config
                   WHERE community_id = %s""",
                [community_id]
            )
            if not result:
                config = None
            else:
                row = result[0]
                config = {
                    'enabled': bool(row[0]),
                    'max_responses_per_window': int(row[1]),
                    'window_seconds': int(row[2]),
                    'max_per_user_per_window': int(row[3]),
                    'response_probability': float(row[4]),
                    'min_message_length': int(row[5]),
                }

            # Cache result (even None as "null" so we don't hammer DB)
            try:
                if self.redis:
                    await self.redis.setex(cache_key, self.CACHE_TTL, json.dumps(config))
            except Exception:
                pass

            return config
        except Exception as e:
            self.logger.error(
                f"DB error fetching chatter config: {e}",
                community_id=community_id
            )
            return None

    async def update_community_config(self, community_id: int, settings: dict) -> dict:
        """
        Upsert community AIChatter config. Invalidates cache.
        Returns the updated config.
        """
        self.dal.executesql(
            """INSERT INTO community_ai_chatter_config
               (community_id, enabled, max_responses_per_window, window_seconds,
                max_per_user_per_window, response_probability, min_message_length, updated_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
               ON CONFLICT (community_id) DO UPDATE SET
                 enabled = EXCLUDED.enabled,
                 max_responses_per_window = EXCLUDED.max_responses_per_window,
                 window_seconds = EXCLUDED.window_seconds,
                 max_per_user_per_window = EXCLUDED.max_per_user_per_window,
                 response_probability = EXCLUDED.response_probability,
                 min_message_length = EXCLUDED.min_message_length,
                 updated_at = NOW()""",
            [
                community_id,
                settings.get('enabled', False),
                settings.get('max_responses_per_window', 10),
                settings.get('window_seconds', 600),
                settings.get('max_per_user_per_window', 2),
                settings.get('response_probability', 0.30),
                settings.get('min_message_length', 10),
            ]
        )
        self.dal.commit()

        # Invalidate cache
        try:
            if self.redis:
                await self.redis.delete(self._cache_key(community_id))
        except Exception:
            pass

        return await self.get_community_config(community_id)
