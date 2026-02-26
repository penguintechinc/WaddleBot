"""
AIChatter Rate Limiter
========================
Per-community and per-user rate limiting for AI proactive chat.
Mirrors ai_researcher_module rate_limiter.py pattern.

Uses rolling window (not hourly) since chatter windows are configurable (60-3600s).
Redis primary, DB fallback (ai_chatter_rate_limit_state table), fail-open.
"""
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

import redis.asyncio as redis

logger = logging.getLogger(__name__)


@dataclass
class RateLimitResult:
    """Result of a rate limit check"""
    allowed: bool
    remaining: int
    reset_at: datetime
    limit: int


class ChatterRateLimiter:
    """
    Rate limiter for AI chatter with Redis primary and DB fallback.
    Fail-open: if both fail, allows the request.
    """

    def __init__(self, redis_client: Optional[redis.Redis], db_connection=None):
        self.redis = redis_client
        self.db = db_connection

    def _window_key(self, community_id: int, window_seconds: int) -> str:
        """Rolling window key based on current time bucket."""
        now = datetime.utcnow()
        bucket = now.strftime('%Y%m%d%H%M')
        return f"ai_chatter:{community_id}:{bucket}:{window_seconds}"

    def _user_window_key(self, community_id: int, user_id: str, window_seconds: int) -> str:
        now = datetime.utcnow()
        bucket = now.strftime('%Y%m%d%H%M')
        return f"ai_chatter_user:{community_id}:{user_id}:{bucket}:{window_seconds}"

    async def check_and_increment_community(
        self,
        community_id: int,
        window_seconds: int,
        max_count: int
    ) -> RateLimitResult:
        """
        Check community-level rate limit and increment if allowed.
        Returns RateLimitResult with allowed=True if under limit.
        """
        key = self._window_key(community_id, window_seconds)
        reset_at = datetime.utcnow() + timedelta(seconds=window_seconds)

        try:
            if self.redis:
                count = await self.redis.incr(key)
                await self.redis.expire(key, window_seconds + 60)  # grace period
                if count > max_count:
                    await self.redis.decr(key)  # rollback
                    return RateLimitResult(
                        allowed=False,
                        remaining=0,
                        reset_at=reset_at,
                        limit=max_count
                    )
                return RateLimitResult(
                    allowed=True,
                    remaining=max(0, max_count - count),
                    reset_at=reset_at,
                    limit=max_count
                )
        except Exception as e:
            logger.warning(f"Redis chatter rate limit check failed: {e}, using DB fallback")

        # DB fallback
        return await self._db_check_and_increment(key, window_seconds, max_count, reset_at)

    async def check_and_increment_user(
        self,
        community_id: int,
        user_id: str,
        window_seconds: int,
        max_count: int
    ) -> RateLimitResult:
        """Check per-user rate limit and increment if allowed."""
        key = self._user_window_key(community_id, user_id, window_seconds)
        reset_at = datetime.utcnow() + timedelta(seconds=window_seconds)

        try:
            if self.redis:
                count = await self.redis.incr(key)
                await self.redis.expire(key, window_seconds + 60)
                if count > max_count:
                    await self.redis.decr(key)
                    return RateLimitResult(
                        allowed=False,
                        remaining=0,
                        reset_at=reset_at,
                        limit=max_count
                    )
                return RateLimitResult(
                    allowed=True,
                    remaining=max(0, max_count - count),
                    reset_at=reset_at,
                    limit=max_count
                )
        except Exception as e:
            logger.warning(f"Redis chatter user rate limit check failed: {e}, using DB fallback")

        return await self._db_check_and_increment(key, window_seconds, max_count, reset_at)

    async def _db_check_and_increment(
        self,
        key: str,
        window_seconds: int,
        max_count: int,
        reset_at: datetime
    ) -> RateLimitResult:
        """DB fallback rate limit using ai_chatter_rate_limit_state table."""
        try:
            if not self.db:
                # Fail-open: no DB connection
                logger.warning("No DB connection for chatter rate limit fallback, failing open")
                return RateLimitResult(allowed=True, remaining=999, reset_at=reset_at, limit=max_count)

            result = self.db.executesql(
                "SELECT count FROM ai_chatter_rate_limit_state WHERE key = %s AND expires_at > NOW()",
                [key]
            )
            current_count = int(result[0][0]) if result else 0

            if current_count >= max_count:
                return RateLimitResult(allowed=False, remaining=0, reset_at=reset_at, limit=max_count)

            new_count = current_count + 1
            self.db.executesql(
                """INSERT INTO ai_chatter_rate_limit_state (key, count, expires_at)
                   VALUES (%s, 1, %s)
                   ON CONFLICT (key) DO UPDATE
                     SET count = ai_chatter_rate_limit_state.count + 1,
                         expires_at = EXCLUDED.expires_at""",
                [key, reset_at]
            )
            self.db.commit()
            return RateLimitResult(
                allowed=True,
                remaining=max(0, max_count - new_count),
                reset_at=reset_at,
                limit=max_count
            )
        except Exception as e:
            logger.error(f"DB chatter rate limit check failed: {e}, failing open")
            return RateLimitResult(allowed=True, remaining=999, reset_at=reset_at, limit=max_count)
