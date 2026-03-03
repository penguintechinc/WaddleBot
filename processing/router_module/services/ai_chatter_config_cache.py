"""
AI Chatter Config Cache
========================
Thin Redis cache wrapper around community_ai_chatter_config DB table.
Called once per chat message; must be fast (Redis hit ~1ms).
Cache TTL: 60 seconds. Returns None if community has no config.
"""
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class AiChatterConfigCache:
    """
    Caches community AIChatter configuration.
    Redis primary with DB fallback.
    """

    CACHE_TTL = 60  # seconds

    def __init__(self, redis_client, dal):
        self.redis = redis_client
        self.dal = dal

    def _key(self, community_id: int) -> str:
        return f"ai_chatter_config:{community_id}"

    async def get(self, community_id: int) -> Optional[dict]:
        """
        Get AIChatter config for a community.
        Returns dict with 'enabled' bool and config fields, or None if no config.
        Fast path: Redis hit returns in ~1ms.
        """
        cache_key = self._key(community_id)

        # Redis primary
        try:
            if self.redis:
                cached = await self.redis.get(cache_key)
                if cached is not None:
                    return json.loads(cached)
        except Exception as e:
            logger.warning(f"Redis cache miss for community {community_id} chatter config: {e}")

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

            # Cache result (None as "null" to avoid DB hammering for communities with no config)
            try:
                if self.redis:
                    await self.redis.setex(cache_key, self.CACHE_TTL, json.dumps(config))
            except Exception:
                pass

            return config

        except Exception as e:
            logger.error(f"DB error fetching chatter config for community {community_id}: {e}")
            return None
