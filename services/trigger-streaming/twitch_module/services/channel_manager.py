"""
Twitch Channel Manager - Manages which channels the bot is in
"""
import asyncio
from typing import Dict, Any, Optional, Set
from flask_core import setup_aaa_logging
from .cache_manager import TwitchCacheManager


class ChannelManager:
    """
    Manages Twitch channels for the bot:
    - Load channels from database
    - Join/leave channels dynamically
    - Periodic refresh of channel list
    - Map channels to communities
    """

    def __init__(self, dal, bot, refresh_interval: int = 300, cache_manager: Optional[TwitchCacheManager] = None):
        self.dal = dal
        self.bot = bot
        self.refresh_interval = refresh_interval
        self.cache = cache_manager
        self.logger = setup_aaa_logging('channel_manager', '2.0.0')

        self._active_channels: Dict[str, Dict[str, Any]] = {}
        self._refresh_task: Optional[asyncio.Task] = None
        self._running = False

    async def load_channels(self) -> Dict[str, Dict[str, Any]]:
        """Load channels from database with caching"""
        # Try cache first
        if self.cache:
            cached_channels = await self.cache.get_channels()
            if cached_channels:
                self.logger.debug(f"Loaded {len(cached_channels)} channels from cache")
                return cached_channels

        channels = {}
        try:
            result = self.dal.executesql(
                """SELECT s.platform_server_id, s.platform_data, cs.community_id
                   FROM servers s
                   JOIN community_servers cs ON cs.platform_server_id = s.platform_server_id
                   WHERE s.platform = 'twitch' AND s.is_active = true AND cs.is_active = true
                """
            )
            for row in result:
                channel_id = row[0]
                platform_data = row[1] or {}
                community_id = row[2]

                # Extract channel name and broadcaster ID
                channel_name = channel_id.lower()
                broadcaster_id = ''
                if isinstance(platform_data, dict):
                    broadcaster_id = platform_data.get('broadcaster_id', '')
                    if platform_data.get('channel_name'):
                        channel_name = platform_data['channel_name'].lower()

                channels[channel_name] = {
                    'broadcaster_id': broadcaster_id,
                    'community_id': community_id,
                    'platform_server_id': channel_id
                }

            self.logger.info(f"Loaded {len(channels)} Twitch channels from database")

            # Cache the result
            if self.cache and channels:
                await self.cache.set_channels(channels)

        except Exception as e:
            self.logger.error(f"Failed to load channels: {e}")
        return channels

    async def start(self):
        """Start the channel manager with periodic refresh"""
        self._running = True

        # Initial load
        self._active_channels = await self.load_channels()

        # Warm cache on startup
        if self.cache and self._active_channels:
            await self.cache.warm_channels(self._active_channels)

        # Start refresh task
        self._refresh_task = asyncio.create_task(self._refresh_loop())
        self.logger.info("Channel manager started")

    async def stop(self):
        """Stop the channel manager"""
        self._running = False
        if self._refresh_task:
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass
        self.logger.info("Channel manager stopped")

    async def _refresh_loop(self):
        """Periodically refresh channel list"""
        while self._running:
            await asyncio.sleep(self.refresh_interval)
            await self.refresh_channels()

    async def refresh_channels(self):
        """Refresh channels from database and update bot"""
        try:
            new_channels = await self.load_channels()

            current_names = set(self._active_channels.keys())
            new_names = set(new_channels.keys())

            # Channels to join
            to_join = new_names - current_names
            for channel in to_join:
                community_id = new_channels[channel].get('community_id')
                await self.bot.join_channel(channel, community_id)
                self.logger.info(f"Added new channel: {channel}")

            # Channels to leave
            to_leave = current_names - new_names
            for channel in to_leave:
                await self.bot.leave_channel(channel)
                self.logger.info(f"Removed channel: {channel}")

            # Update community mappings for existing channels
            for channel in current_names & new_names:
                old_community = self._active_channels[channel].get('community_id')
                new_community = new_channels[channel].get('community_id')
                if old_community != new_community:
                    self.bot.channel_community_map[channel] = new_community

            self._active_channels = new_channels
            self.logger.debug(f"Channel refresh complete: {len(self._active_channels)} channels")

        except Exception as e:
            self.logger.error(f"Channel refresh failed: {e}")

    def get_channel_info(self, channel_name: str) -> Optional[Dict[str, Any]]:
        """Get info for a specific channel"""
        return self._active_channels.get(channel_name.lower())

    async def get_community_id(self, channel_name: str) -> Optional[int]:
        """Get community ID for a channel with caching"""
        # Try cache first
        if self.cache:
            cached_id = await self.cache.get_community_id(channel_name)
            if cached_id is not None:
                return cached_id

        # Fallback to in-memory
        info = self.get_channel_info(channel_name)
        community_id = info.get('community_id') if info else None

        # Cache the result
        if self.cache and community_id is not None:
            await self.cache.set_community_id(channel_name, community_id)

        return community_id

    def get_all_channels(self) -> Dict[str, Dict[str, Any]]:
        """Get all active channels"""
        return self._active_channels.copy()

    def get_channel_names(self) -> Set[str]:
        """Get set of all channel names"""
        return set(self._active_channels.keys())
