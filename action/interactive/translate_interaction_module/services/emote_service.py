"""
Emote Service - Platform Emote Fetching and Caching
====================================================

Provides multi-level caching for platform-specific emotes:
1. In-memory LRU cache (fast, per-instance)
2. Redis cache (shared across instances)
3. PostgreSQL cache (persistent)

Fetches emotes from external APIs:
- Twitch Official API (Global and channel emotes)
- BTTV (BetterTTV)
- FFZ (FrankerFaceZ)
- 7TV

CACHING STRATEGY:
- Global emotes: Refreshed once per day via cron job (no on-demand API calls)
- Channel emotes: Fetched on-demand with 24-hour cache
- This prevents rate limiting from Twitch and other platforms

TTL: 1 month for global emotes, 1 day for channel-specific
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Set

from cachetools import TTLCache

logger = logging.getLogger(__name__)

# Default TTL: 1 month (30 days) for global emotes
DEFAULT_EMOTE_TTL_SECONDS = 30 * 24 * 60 * 60  # 2,592,000 seconds

# Channel-specific emotes: 1 day cache
CHANNEL_EMOTE_TTL_SECONDS = 24 * 60 * 60  # 86,400 seconds

# Redis key for global emotes refresh timestamp
GLOBAL_EMOTES_LAST_REFRESH_KEY = "emotes:global:last_refresh"

# Minimum time between on-demand global refreshes (prevent accidental spam)
MIN_GLOBAL_REFRESH_INTERVAL_HOURS = 12


class EmoteService:
    """
    Service for fetching and caching platform emotes.

    Provides a unified interface for checking if a word is a known emote
    for any supported platform (Twitch, Discord, Slack, Kick).
    """

    def __init__(self, dal, cache_manager):
        """
        Initialize EmoteService.

        Args:
            dal: Database access layer
            cache_manager: Redis cache manager
        """
        self.dal = dal
        self.cache = cache_manager

        # In-memory cache: platform:channel_id -> Set[emote_codes]
        # TTL: 1 hour for quick lookups, refresh from Redis/DB as needed
        self._memory_cache: TTLCache = TTLCache(maxsize=500, ttl=3600)

        # Providers will be initialized lazily
        self._providers: Dict[str, 'BaseEmoteProvider'] = {}
        self._providers_initialized = False

        logger.info("EmoteService initialized")

    def _initialize_providers(self) -> None:
        """Lazy initialization of emote providers."""
        if self._providers_initialized:
            return

        try:
            from services.translation_providers.emote_providers import (
                TwitchEmoteProvider,
                DiscordEmoteProvider,
                SlackEmoteProvider,
            )

            self._providers['twitch'] = TwitchEmoteProvider()
            self._providers['discord'] = DiscordEmoteProvider()
            self._providers['slack'] = SlackEmoteProvider()

            # Kick can share Twitch emotes or have its own provider
            self._providers['kick'] = TwitchEmoteProvider()

            self._providers_initialized = True
            logger.info("Emote providers initialized")

        except ImportError as e:
            logger.warning(f"Failed to import emote providers: {e}")

    async def get_emotes(
        self,
        platform: str,
        channel_id: Optional[str] = None,
        sources: Optional[List[str]] = None
    ) -> Set[str]:
        """
        Get all emote codes for a platform/channel.

        Args:
            platform: Platform name (twitch, discord, slack, kick)
            channel_id: Optional channel ID for channel-specific emotes
            sources: Optional list of sources to include (e.g., ['global', 'bttv'])

        Returns:
            Set of emote codes
        """
        cache_key = self._get_cache_key(platform, channel_id)

        # 1. Check memory cache
        if cache_key in self._memory_cache:
            logger.debug(f"Emote cache hit (memory): {cache_key}")
            return self._memory_cache[cache_key]

        # 2. Check Redis cache
        redis_key = f"emotes:{cache_key}"
        redis_data = await self.cache.get(redis_key)
        if redis_data:
            emotes = set(redis_data.split(',')) if redis_data else set()
            self._memory_cache[cache_key] = emotes
            logger.debug(f"Emote cache hit (Redis): {cache_key}, {len(emotes)} emotes")
            return emotes

        # 3. Check database cache
        emotes = await self._get_from_db(platform, channel_id, sources)
        if emotes:
            # Populate higher cache levels
            self._memory_cache[cache_key] = emotes
            await self.cache.set(
                redis_key,
                ','.join(emotes),
                ttl=DEFAULT_EMOTE_TTL_SECONDS
            )
            logger.debug(f"Emote cache hit (DB): {cache_key}, {len(emotes)} emotes")
            return emotes

        # 4. Fetch from external APIs
        emotes = await self.refresh_emotes(platform, channel_id, sources)
        return emotes

    async def is_emote(
        self,
        code: str,
        platform: str,
        channel_id: Optional[str] = None
    ) -> bool:
        """
        Check if a code is a known emote.

        Args:
            code: Potential emote code
            platform: Platform name
            channel_id: Optional channel ID

        Returns:
            True if code is a known emote
        """
        emotes = await self.get_emotes(platform, channel_id)
        return code in emotes

    async def refresh_emotes(
        self,
        platform: str,
        channel_id: Optional[str] = None,
        sources: Optional[List[str]] = None
    ) -> Set[str]:
        """
        Refresh emote cache from external APIs.

        IMPORTANT: For global emotes (channel_id=None), this will NOT make
        API calls to prevent rate limiting. Use refresh_global_emotes_cron()
        for that purpose (called by cron job once per day).

        For channel-specific emotes, this will fetch from APIs.

        Args:
            platform: Platform name
            channel_id: Optional channel ID (required for API refresh)
            sources: Optional list of sources

        Returns:
            Set of emote codes
        """
        self._initialize_providers()

        provider = self._providers.get(platform)
        if not provider:
            logger.warning(f"No emote provider for platform: {platform}")
            return set()

        # For global emotes, don't make API calls - return cached data only
        # Global emotes are refreshed via cron job to prevent rate limiting
        if not channel_id:
            logger.debug(
                f"Global emote refresh requested for {platform} - "
                "returning cached data only. Use cron job for API refresh."
            )
            return await self._get_from_db(platform, None, sources)

        try:
            # Fetch channel-specific emotes from provider
            # Only pass channel_id to avoid fetching global emotes again
            emotes = await provider.fetch_emotes(channel_id, sources or ['channel'])

            if emotes:
                # Store in all cache levels with shorter TTL for channel emotes
                await self._store_emotes(platform, channel_id, emotes, is_channel=True)

                # Update memory and Redis cache
                cache_key = self._get_cache_key(platform, channel_id)
                emote_codes = {e.code for e in emotes}

                # Get global emotes and merge
                global_emotes = await self._get_from_db(platform, None, sources)
                all_emotes = emote_codes.union(global_emotes)

                self._memory_cache[cache_key] = all_emotes
                await self.cache.set(
                    f"emotes:{cache_key}",
                    ','.join(all_emotes),
                    ttl=CHANNEL_EMOTE_TTL_SECONDS
                )

                logger.info(
                    f"Refreshed {len(emotes)} channel emotes for {platform}/{channel_id}"
                )
                return all_emotes

        except Exception as e:
            logger.error(f"Failed to refresh emotes for {platform}: {e}")

        return set()

    async def _get_from_db(
        self,
        platform: str,
        channel_id: Optional[str],
        sources: Optional[List[str]]
    ) -> Set[str]:
        """Retrieve emotes from database cache."""
        try:
            if channel_id:
                # Get both global and channel-specific emotes
                query = """
                    SELECT DISTINCT emote_code
                    FROM emote_cache
                    WHERE platform = %s
                      AND (channel_id = %s OR channel_id IS NULL)
                      AND expires_at > NOW()
                """
                params = [platform, channel_id]
            else:
                # Global emotes only
                query = """
                    SELECT DISTINCT emote_code
                    FROM emote_cache
                    WHERE platform = %s
                      AND channel_id IS NULL
                      AND expires_at > NOW()
                """
                params = [platform]

            # Add source filter if specified
            if sources:
                placeholders = ','.join(['%s'] * len(sources))
                query += f" AND emote_source IN ({placeholders})"
                params.extend(sources)

            result = self.dal.executesql(query, params)

            if result:
                return {row[0] for row in result}

        except Exception as e:
            logger.error(f"DB emote lookup failed: {e}")

        return set()

    async def _store_emotes(
        self,
        platform: str,
        channel_id: Optional[str],
        emotes: List['Emote'],
        is_channel: bool = False
    ) -> None:
        """
        Store emotes in database cache.

        Args:
            platform: Platform name
            channel_id: Optional channel ID
            emotes: List of Emote objects to store
            is_channel: If True, use shorter TTL for channel-specific emotes
        """
        if not emotes:
            return

        try:
            # Use different TTLs: 30 days for global, 1 day for channel-specific
            if is_channel:
                expires_at = datetime.now(timezone.utc) + timedelta(days=1)
            else:
                expires_at = datetime.now(timezone.utc) + timedelta(days=30)

            for emote in emotes:
                self.dal.executesql(
                    """
                    INSERT INTO emote_cache
                    (platform, channel_id, emote_source, emote_code, emote_id, emote_url, expires_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (platform, channel_id, emote_source, emote_code)
                    DO UPDATE SET
                        emote_id = EXCLUDED.emote_id,
                        emote_url = EXCLUDED.emote_url,
                        expires_at = EXCLUDED.expires_at
                    """,
                    [
                        platform,
                        channel_id,
                        emote.source,
                        emote.code,
                        emote.emote_id,
                        emote.url,
                        expires_at
                    ]
                )

            self.dal.commit()
            logger.debug(f"Stored {len(emotes)} emotes in database")

        except Exception as e:
            logger.error(f"Failed to store emotes in DB: {e}")

    def _get_cache_key(self, platform: str, channel_id: Optional[str]) -> str:
        """Generate cache key for emote lookup."""
        if channel_id:
            return f"{platform}:{channel_id}"
        return f"{platform}:global"

    async def refresh_global_emotes_cron(self) -> Dict[str, int]:
        """
        Refresh global emotes for all platforms.

        This method should be called by a cron job once per day.
        It fetches global emotes from all sources and updates the cache.

        Returns:
            Dict mapping platform to number of emotes fetched
        """
        logger.info("Starting global emotes refresh (cron job)")

        self._initialize_providers()

        results = {}
        platforms = ['twitch', 'discord', 'slack']

        for platform in platforms:
            provider = self._providers.get(platform)
            if not provider:
                continue

            try:
                # Fetch global emotes only (no channel_id)
                emotes = await provider.fetch_emotes(
                    channel_id=None,
                    sources=['global', 'twitch', 'bttv', 'ffz', '7tv']
                )

                if emotes:
                    # Store in database with long TTL
                    await self._store_emotes(platform, None, emotes)

                    # Update caches
                    cache_key = self._get_cache_key(platform, None)
                    emote_codes = {e.code for e in emotes}
                    self._memory_cache[cache_key] = emote_codes
                    await self.cache.set(
                        f"emotes:{cache_key}",
                        ','.join(emote_codes),
                        ttl=DEFAULT_EMOTE_TTL_SECONDS
                    )

                    results[platform] = len(emotes)
                    logger.info(f"Refreshed {len(emotes)} global emotes for {platform}")

            except Exception as e:
                logger.error(f"Failed to refresh global emotes for {platform}: {e}")
                results[platform] = 0

        # Update last refresh timestamp
        await self.cache.set(
            GLOBAL_EMOTES_LAST_REFRESH_KEY,
            datetime.now(timezone.utc).isoformat(),
            ttl=DEFAULT_EMOTE_TTL_SECONDS
        )

        logger.info(f"Global emotes refresh complete: {results}")
        return results

    async def get_last_global_refresh(self) -> Optional[datetime]:
        """Get timestamp of last global emotes refresh."""
        try:
            ts = await self.cache.get(GLOBAL_EMOTES_LAST_REFRESH_KEY)
            if ts:
                return datetime.fromisoformat(ts)
        except Exception as e:
            logger.warning(f"Failed to get last refresh timestamp: {e}")
        return None

    async def needs_global_refresh(self) -> bool:
        """Check if global emotes need to be refreshed."""
        last_refresh = await self.get_last_global_refresh()
        if not last_refresh:
            return True

        hours_since = (datetime.now(timezone.utc) - last_refresh).total_seconds() / 3600
        return hours_since >= 24  # Refresh once per day

    async def get_stats(self) -> Dict:
        """Get emote cache statistics."""
        try:
            result = self.dal.executesql(
                """
                SELECT
                    platform,
                    emote_source,
                    COUNT(*) as count,
                    COUNT(DISTINCT channel_id) as channels
                FROM emote_cache
                WHERE expires_at > NOW()
                GROUP BY platform, emote_source
                ORDER BY platform, emote_source
                """
            )

            stats = {
                'memory_cache_size': len(self._memory_cache),
                'by_platform': {}
            }

            if result:
                for row in result:
                    platform = row[0]
                    source = row[1]
                    count = row[2]
                    channels = row[3]

                    if platform not in stats['by_platform']:
                        stats['by_platform'][platform] = {}

                    stats['by_platform'][platform][source] = {
                        'count': count,
                        'channels': channels
                    }

            return stats

        except Exception as e:
            logger.error(f"Failed to get emote stats: {e}")
            return {'error': str(e)}


# =============================================================================
# DATA CLASSES
# =============================================================================

from dataclasses import dataclass


@dataclass
class Emote:
    """Represents a platform emote."""
    code: str
    source: str  # 'global', 'bttv', 'ffz', '7tv', 'native'
    platform: str
    channel_id: Optional[str] = None
    emote_id: Optional[str] = None
    url: Optional[str] = None
