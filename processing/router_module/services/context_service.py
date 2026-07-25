"""Context Service — per-user community context overrides.

Implements the three-level context resolution used by the router:
  1. Per-user override  → Redis key ``ctx:{platform}:{user_id}:{entity_id}`` (TTL 24 h)
  2. Channel/server default → ``entity:community:{entity_id}`` (existing cache, handled by
     _get_community_for_entity in command_processor)
  3. None → caller returns an error

The context_entity_id is the platform-side channel/server/workspace that maps to a
``community_servers.platform_server_id`` value. Only communities with an **approved**
link to that entity are eligible for context switching.
"""
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Redis TTL for per-user context overrides (24 hours)
USER_CTX_TTL = 86_400


class ContextService:
    """Manages per-user community context overrides."""

    def __init__(self, dal, cache_manager):
        self.dal = dal
        self.cache = cache_manager

    # ──────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────

    async def get_context(
        self, platform: str, user_id: str, entity_id: str
    ) -> Optional[int]:
        """Return the community_id from the per-user override, or None.

        None means the caller should fall back to the channel/server default.
        """
        cache_key = self._user_ctx_key(platform, user_id, entity_id)
        cached = await self.cache.get(cache_key)
        if cached:
            return int(cached)

        # Cache miss — check DB
        try:
            result = self.dal.executesql(
                """SELECT community_id FROM user_platform_context
                   WHERE platform = %s AND platform_user_id = %s AND platform_entity_id = %s
                   LIMIT 1""",
                [platform, user_id, entity_id],
            )
            if result:
                community_id = result[0][0]
                await self.cache.set(cache_key, str(community_id), ttl=USER_CTX_TTL)
                return community_id
        except Exception as e:
            logger.warning(f"Failed to fetch user context from DB: {e}")

        return None

    async def set_user_context(
        self, platform: str, user_id: str, entity_id: str, community_id: int
    ) -> bool:
        """Set a per-user context override.

        Validates that the community has an approved link to this entity before
        persisting. Returns True on success, False if not approved.
        """
        available = await self.get_available_communities(platform, entity_id)
        if not any(c["id"] == community_id for c in available):
            return False  # Not an approved community for this channel

        try:
            self.dal.executesql(
                """INSERT INTO user_platform_context
                     (platform, platform_user_id, platform_entity_id, community_id, updated_at)
                   VALUES (%s, %s, %s, %s, NOW())
                   ON CONFLICT (platform, platform_user_id, platform_entity_id)
                   DO UPDATE SET community_id = EXCLUDED.community_id, updated_at = NOW()""",
                [platform, user_id, entity_id, community_id],
            )
            cache_key = self._user_ctx_key(platform, user_id, entity_id)
            await self.cache.set(cache_key, str(community_id), ttl=USER_CTX_TTL)
            return True
        except Exception as e:
            logger.error(f"Failed to set user context: {e}")
            return False

    async def clear_user_context(
        self, platform: str, user_id: str, entity_id: str
    ) -> None:
        """Remove the per-user context override, falling back to channel default."""
        try:
            self.dal.executesql(
                """DELETE FROM user_platform_context
                   WHERE platform = %s AND platform_user_id = %s AND platform_entity_id = %s""",
                [platform, user_id, entity_id],
            )
        except Exception as e:
            logger.warning(f"Failed to clear user context from DB: {e}")

        cache_key = self._user_ctx_key(platform, user_id, entity_id)
        await self.cache.delete(cache_key)

    async def set_default_context(
        self, platform: str, entity_id: str, community_id: int
    ) -> bool:
        """Set the default community for a channel/server (owner-only action).

        Updates community_servers.is_primary and clears the entity→community cache
        so the next command picks up the new default.
        """
        try:
            # Unset existing primary for this entity
            self.dal.executesql(
                """UPDATE community_servers
                   SET is_primary = FALSE
                   WHERE platform = %s AND platform_server_id = %s AND is_primary = TRUE""",
                [platform, entity_id],
            )
            # Set the new primary
            rows = self.dal.executesql(
                """UPDATE community_servers
                   SET is_primary = TRUE
                   WHERE platform = %s AND platform_server_id = %s AND community_id = %s
                     AND status = 'approved' AND is_active = TRUE
                   RETURNING id""",
                [platform, entity_id, community_id],
            )
            if not rows:
                return False  # No approved link found

            # Clear the entity→community cache so command_processor picks up new default
            await self.cache.delete(f"entity:community:{entity_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to set default context: {e}")
            return False

    async def get_available_communities(
        self, platform: str, entity_id: str
    ) -> List[Dict[str, Any]]:
        """Return communities with an approved link to this platform entity.

        This is the security gate for context switching — only approved links
        are eligible targets.
        """
        try:
            result = self.dal.executesql(
                """SELECT c.id, c.name, c.slug, cs.is_primary
                   FROM community_servers cs
                   JOIN communities c ON c.id = cs.community_id
                   WHERE cs.platform = %s
                     AND cs.platform_server_id = %s
                     AND cs.status = 'approved'
                   ORDER BY cs.is_primary DESC, c.name ASC""",
                [platform, entity_id],
            )
            return [
                {"id": row[0], "name": row[1], "slug": row[2], "is_primary": row[3]}
                for row in result
            ]
        except Exception as e:
            logger.warning(f"Failed to fetch available communities: {e}")
            return []

    # ──────────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def _user_ctx_key(platform: str, user_id: str, entity_id: str) -> str:
        return f"ctx:{platform}:{user_id}:{entity_id}"
