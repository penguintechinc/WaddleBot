"""
Twitch Receiver Cache Manager

Implements distributed caching for:
- Channel lists (TTL: 300s)
- Community mappings (TTL: 600s)
- Entity -> community lookups (TTL: 600s)
- Channel metadata (broadcaster IDs, etc.)
"""

import logging
from typing import Dict, Any, Optional, Set
from flask_core import CacheManager

logger = logging.getLogger(__name__)


class TwitchCacheManager:
    """
    Cache manager for Twitch receiver module.

    Caches:
    - channels: Full channel list with metadata
    - community_map: Channel -> community_id mappings
    - entity_lookups: Entity ID -> community lookups
    """

    # Cache TTLs in seconds
    CHANNEL_LIST_TTL = 300  # 5 minutes
    COMMUNITY_MAP_TTL = 600  # 10 minutes
    ENTITY_LOOKUP_TTL = 600  # 10 minutes

    def __init__(self, cache: CacheManager):
        """
        Initialize Twitch cache manager.

        Args:
            cache: Configured CacheManager instance
        """
        self.cache = cache

    async def get_channels(self) -> Optional[Dict[str, Dict[str, Any]]]:
        """Get cached channel list"""
        return await self.cache.get("channels:all")

    async def set_channels(
        self,
        channels: Dict[str, Dict[str, Any]]
    ) -> bool:
        """Cache channel list"""
        return await self.cache.set(
            "channels:all",
            channels,
            ttl=self.CHANNEL_LIST_TTL
        )

    async def get_channel(self, channel_name: str) -> Optional[Dict[str, Any]]:
        """Get cached channel info"""
        # Try individual channel cache first
        channel_info = await self.cache.get(f"channel:{channel_name}")
        if channel_info:
            return channel_info

        # Fallback to full channel list
        all_channels = await self.get_channels()
        if all_channels:
            return all_channels.get(channel_name.lower())

        return None

    async def set_channel(
        self,
        channel_name: str,
        channel_info: Dict[str, Any]
    ) -> bool:
        """Cache individual channel info"""
        return await self.cache.set(
            f"channel:{channel_name}",
            channel_info,
            ttl=self.CHANNEL_LIST_TTL
        )

    async def get_community_id(
        self,
        channel_name: str
    ) -> Optional[int]:
        """Get cached community ID for channel"""
        cache_key = f"community_map:{channel_name}"
        return await self.cache.get(cache_key)

    async def set_community_id(
        self,
        channel_name: str,
        community_id: int
    ) -> bool:
        """Cache community ID for channel"""
        cache_key = f"community_map:{channel_name}"
        return await self.cache.set(
            cache_key,
            community_id,
            ttl=self.COMMUNITY_MAP_TTL
        )

    async def get_community_for_entity(
        self,
        entity_id: str
    ) -> Optional[int]:
        """Get cached community ID for entity"""
        cache_key = f"entity_lookup:{entity_id}"
        return await self.cache.get(cache_key)

    async def set_community_for_entity(
        self,
        entity_id: str,
        community_id: int
    ) -> bool:
        """Cache community ID for entity"""
        cache_key = f"entity_lookup:{entity_id}"
        return await self.cache.set(
            cache_key,
            community_id,
            ttl=self.ENTITY_LOOKUP_TTL
        )

    async def get_broadcaster_id(
        self,
        channel_name: str
    ) -> Optional[str]:
        """Get cached broadcaster ID"""
        channel_info = await self.get_channel(channel_name)
        if channel_info:
            return channel_info.get('broadcaster_id')
        return None

    async def invalidate_channel(self, channel_name: str):
        """Invalidate all caches for a channel"""
        await self.cache.delete(f"channel:{channel_name}")
        await self.cache.delete(f"community_map:{channel_name}")
        logger.info(f"Invalidated cache for channel: {channel_name}")

    async def invalidate_all_channels(self):
        """Invalidate entire channel cache"""
        await self.cache.delete("channels:all")
        await self.cache.delete_pattern("channel:*")
        await self.cache.delete_pattern("community_map:*")
        logger.info("Invalidated all channel caches")

    async def warm_channels(
        self,
        channels: Dict[str, Dict[str, Any]]
    ):
        """
        Warm cache with channel data on startup.

        Args:
            channels: Dictionary of channel_name -> channel_info
        """
        if not channels:
            logger.warning("No channels to warm cache")
            return

        try:
            # Cache full channel list
            await self.set_channels(channels)

            # Cache community mappings
            community_map = {}
            for channel_name, info in channels.items():
                community_id = info.get('community_id')
                if community_id:
                    community_map[f"community_map:{channel_name}"] = community_id

            if community_map:
                await self.cache.set_many(
                    community_map,
                    ttl=self.COMMUNITY_MAP_TTL
                )

            logger.info(
                f"Warmed cache with {len(channels)} channels "
                f"and {len(community_map)} community mappings"
            )

        except Exception as e:
            logger.error(f"Failed to warm channel cache: {e}")

    async def get_channel_names(self) -> Optional[Set[str]]:
        """Get set of cached channel names"""
        channels = await self.get_channels()
        if channels:
            return set(channels.keys())
        return None

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        base_stats = await self.cache.get_stats()

        # Add Twitch-specific stats
        channels = await self.get_channels()
        base_stats.update({
            "cached_channels": len(channels) if channels else 0,
            "cache_hit_rate": "N/A"  # Would need counters for this
        })

        return base_stats
