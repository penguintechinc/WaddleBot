"""
Viewer Tracker Service - Polls Twitch chatters API for viewer activity tracking
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Optional, Set

import aiohttp

logger = logging.getLogger(__name__)


class ViewerTracker:
    """
    Tracks viewer presence in Twitch channels for activity leaderboards.

    Polls the Twitch chatters API at regular intervals to detect:
    - Viewers joining a channel
    - Viewers leaving a channel
    - Continuous watch time via heartbeats
    """

    def __init__(
        self,
        hub_api_url: str,
        service_api_key: str,
        twitch_client_id: str,
        twitch_access_token: str,
        poll_interval: int = 60,
    ):
        self.hub_api_url = hub_api_url
        self.service_api_key = service_api_key
        self.twitch_client_id = twitch_client_id
        self.twitch_access_token = twitch_access_token
        self.poll_interval = poll_interval

        # Track previous poll results per channel: {channel_id: {user_id: username}}
        self._previous_viewers: Dict[str, Dict[str, str]] = {}
        # Track active channels being monitored: {channel_id: broadcaster_id}
        self._active_channels: Dict[str, str] = {}
        # Community mapping cache: {channel_id: community_id}
        self._community_cache: Dict[str, int] = {}

        self._http_session: Optional[aiohttp.ClientSession] = None
        self._running = False
        self._poll_task: Optional[asyncio.Task] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session"""
        if self._http_session is None or self._http_session.closed:
            self._http_session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self._http_session

    async def start(self, channels: Dict[str, dict]):
        """
        Start tracking viewers for the given channels.

        Args:
            channels: Dict mapping channel_id to channel info containing:
                      - broadcaster_id: Twitch broadcaster user ID
                      - community_id: WaddleBot community ID
        """
        self._running = True

        for channel_id, info in channels.items():
            self._active_channels[channel_id] = info.get('broadcaster_id', '')
            if info.get('community_id'):
                self._community_cache[channel_id] = info['community_id']

        logger.info(
            f"Starting viewer tracker for {len(self._active_channels)} channels"
        )

        self._poll_task = asyncio.create_task(self._poll_loop())

    async def stop(self):
        """Stop the viewer tracker and clean up"""
        self._running = False

        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass

        # Send leave events for all tracked viewers
        for channel_id, viewers in self._previous_viewers.items():
            community_id = self._community_cache.get(channel_id)
            if community_id:
                for user_id, username in viewers.items():
                    await self._send_activity_event(
                        'leave', community_id, channel_id, user_id, username
                    )

        if self._http_session and not self._http_session.closed:
            await self._http_session.close()

        logger.info("Viewer tracker stopped")

    async def add_channel(self, channel_id: str, broadcaster_id: str,
                          community_id: int):
        """Add a channel to track"""
        self._active_channels[channel_id] = broadcaster_id
        self._community_cache[channel_id] = community_id
        logger.info(f"Added channel {channel_id} to viewer tracking")

    async def remove_channel(self, channel_id: str):
        """Remove a channel from tracking"""
        if channel_id in self._active_channels:
            # Send leave events for current viewers
            viewers = self._previous_viewers.get(channel_id, {})
            community_id = self._community_cache.get(channel_id)
            if community_id:
                for user_id, username in viewers.items():
                    await self._send_activity_event(
                        'leave', community_id, channel_id, user_id, username
                    )

            del self._active_channels[channel_id]
            self._previous_viewers.pop(channel_id, None)
            self._community_cache.pop(channel_id, None)
            logger.info(f"Removed channel {channel_id} from viewer tracking")

    async def _poll_loop(self):
        """Main polling loop"""
        while self._running:
            try:
                await self._poll_all_channels()
            except Exception as e:
                logger.error(f"Error in viewer poll loop: {e}")

            await asyncio.sleep(self.poll_interval)

    async def _poll_all_channels(self):
        """Poll all active channels for viewers"""
        tasks = []
        for channel_id, broadcaster_id in self._active_channels.items():
            if broadcaster_id:
                tasks.append(self._poll_channel(channel_id, broadcaster_id))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _poll_channel(self, channel_id: str, broadcaster_id: str):
        """Poll a single channel for current viewers"""
        try:
            current_viewers = await self._get_chatters(broadcaster_id)
            previous_viewers = self._previous_viewers.get(channel_id, {})

            current_ids = set(current_viewers.keys())
            previous_ids = set(previous_viewers.keys())

            # Detect joins and leaves
            joined_ids = current_ids - previous_ids
            left_ids = previous_ids - current_ids
            continuing_ids = current_ids & previous_ids

            community_id = self._community_cache.get(channel_id)
            if not community_id:
                logger.debug(f"No community_id for channel {channel_id}")
                return

            # Send join events
            for user_id in joined_ids:
                username = current_viewers.get(user_id, '')
                await self._send_activity_event(
                    'join', community_id, channel_id, user_id, username
                )

            # Send leave events
            for user_id in left_ids:
                username = previous_viewers.get(user_id, '')
                await self._send_activity_event(
                    'leave', community_id, channel_id, user_id, username
                )

            # Send heartbeats for continuing viewers
            for user_id in continuing_ids:
                username = current_viewers.get(user_id, '')
                await self._send_activity_event(
                    'heartbeat', community_id, channel_id, user_id, username
                )

            # Update previous viewers
            self._previous_viewers[channel_id] = current_viewers

            logger.debug(
                f"Channel {channel_id}: {len(joined_ids)} joins, "
                f"{len(left_ids)} leaves, {len(continuing_ids)} continuing"
            )

        except Exception as e:
            logger.warning(f"Failed to poll channel {channel_id}: {e}")

    async def _get_chatters(self, broadcaster_id: str) -> Dict[str, str]:
        """
        Get current chatters from Twitch API.

        Returns dict mapping user_id to username.
        """
        session = await self._get_session()
        chatters: Dict[str, str] = {}
        cursor = None

        try:
            # Paginate through all chatters
            while True:
                url = (
                    f"https://api.twitch.tv/helix/chat/chatters"
                    f"?broadcaster_id={broadcaster_id}"
                    f"&moderator_id={broadcaster_id}"
                    f"&first=1000"
                )
                if cursor:
                    url += f"&after={cursor}"

                async with session.get(
                    url,
                    headers={
                        'Client-ID': self.twitch_client_id,
                        'Authorization': f'Bearer {self.twitch_access_token}',
                    }
                ) as resp:
                    if resp.status == 401:
                        logger.warning("Twitch API auth failed - token may be expired")
                        break
                    elif resp.status != 200:
                        logger.warning(f"Twitch API error: {resp.status}")
                        break

                    data = await resp.json()

                    for chatter in data.get('data', []):
                        chatters[chatter['user_id']] = chatter['user_login']

                    cursor = data.get('pagination', {}).get('cursor')
                    if not cursor:
                        break

        except Exception as e:
            logger.error(f"Failed to get chatters: {e}")

        return chatters

    async def _send_activity_event(
        self,
        event_type: str,
        community_id: int,
        channel_id: str,
        platform_user_id: str,
        platform_username: str,
    ):
        """Send activity event to hub internal API"""
        if not self.hub_api_url or not self.service_api_key:
            return

        try:
            session = await self._get_session()
            payload = {
                'event_type': event_type,
                'community_id': community_id,
                'platform': 'twitch',
                'platform_user_id': platform_user_id,
                'platform_username': platform_username,
                'channel_id': channel_id,
            }

            await session.post(
                f"{self.hub_api_url}/api/v1/internal/activity/watch-session",
                json=payload,
                headers={'X-Service-Key': self.service_api_key},
            )
        except Exception as e:
            logger.debug(f"Failed to send activity event: {e}")
