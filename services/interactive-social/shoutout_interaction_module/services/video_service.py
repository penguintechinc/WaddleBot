"""
Video Service for Video Shoutouts

Fetches video content from Twitch (clips) and YouTube for video shoutouts.
Includes channel info lookup for game/category data.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import aiohttp
from flask_core import CircuitBreaker, with_retry

logger = logging.getLogger(__name__)


class VideoAPIError(Exception):
    """Video API error"""
    pass


@dataclass
class VideoInfo:
    """Video information for shoutout display"""
    platform: str  # 'twitch' or 'youtube'
    video_id: str
    title: str
    thumbnail_url: str
    video_url: str
    duration_seconds: Optional[int] = None
    view_count: Optional[int] = None
    created_at: Optional[str] = None


@dataclass
class ChannelInfo:
    """Channel info including game/category"""
    platform: str
    user_id: str
    username: str
    display_name: str
    profile_image_url: Optional[str] = None
    game_name: Optional[str] = None  # Last game/category played
    is_live: bool = False
    stream_title: Optional[str] = None


class VideoService:
    """
    Video content service for shoutouts.

    Fetches clips from Twitch and videos from YouTube with channel info.
    """

    TWITCH_HELIX_API = "https://api.twitch.tv/helix"
    YOUTUBE_API = "https://www.googleapis.com/youtube/v3"

    def __init__(
        self,
        twitch_client_id: str,
        twitch_client_secret: str,
        youtube_api_key: str,
        twitch_access_token: Optional[str] = None
    ):
        self.twitch_client_id = twitch_client_id
        self.twitch_client_secret = twitch_client_secret
        self.youtube_api_key = youtube_api_key
        self._twitch_token = twitch_access_token

        # Circuit breakers
        self._twitch_breaker = CircuitBreaker(
            name="twitch_video_api",
            failure_threshold=5,
            timeout_seconds=60,
            expected_exception=VideoAPIError
        )
        self._youtube_breaker = CircuitBreaker(
            name="youtube_api",
            failure_threshold=5,
            timeout_seconds=60,
            expected_exception=VideoAPIError
        )

    async def _get_twitch_token(self) -> str:
        """Get or refresh Twitch OAuth token"""
        if self._twitch_token:
            return self._twitch_token

        url = "https://id.twitch.tv/oauth2/token"
        params = {
            "client_id": self.twitch_client_id,
            "client_secret": self.twitch_client_secret,
            "grant_type": "client_credentials"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        self._twitch_token = data['access_token']
                        return self._twitch_token
                    else:
                        error = await response.text()
                        raise VideoAPIError(f"Twitch token error: {error}")
        except aiohttp.ClientError as e:
            raise VideoAPIError(f"Network error: {e}")

    # =====================================================
    # TWITCH METHODS
    # =====================================================

    @with_retry(max_retries=2, initial_delay=1.0)
    async def get_twitch_user(
        self,
        username: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get Twitch user info by username or ID"""
        if not username and not user_id:
            raise ValueError("Either username or user_id required")

        async def _fetch():
            token = await self._get_twitch_token()
            headers = {
                "Client-ID": self.twitch_client_id,
                "Authorization": f"Bearer {token}"
            }
            params = {}
            if username:
                params['login'] = username.lower()
            if user_id:
                params['id'] = user_id

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.TWITCH_HELIX_API}/users",
                    headers=headers,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        users = data.get('data', [])
                        return users[0] if users else None
                    elif response.status == 401:
                        self._twitch_token = None
                        raise VideoAPIError("Token expired")
                    else:
                        raise VideoAPIError(f"Failed: {await response.text()}")

        try:
            return await self._twitch_breaker.call(_fetch)
        except VideoAPIError as e:
            logger.error(f"Twitch user lookup error: {e}")
            return None

    @with_retry(max_retries=2, initial_delay=1.0)
    async def get_twitch_channel_info(
        self,
        broadcaster_id: str
    ) -> Optional[ChannelInfo]:
        """Get Twitch channel info including last game played"""
        async def _fetch():
            token = await self._get_twitch_token()
            headers = {
                "Client-ID": self.twitch_client_id,
                "Authorization": f"Bearer {token}"
            }

            async with aiohttp.ClientSession() as session:
                # Get channel info (includes game_name)
                async with session.get(
                    f"{self.TWITCH_HELIX_API}/channels",
                    headers=headers,
                    params={'broadcaster_id': broadcaster_id},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        channels = data.get('data', [])
                        if not channels:
                            return None
                        ch = channels[0]
                        return ChannelInfo(
                            platform='twitch',
                            user_id=ch['broadcaster_id'],
                            username=ch['broadcaster_login'],
                            display_name=ch['broadcaster_name'],
                            game_name=ch.get('game_name'),
                            is_live=False,  # Updated by stream check
                            stream_title=ch.get('title')
                        )
                    elif response.status == 401:
                        self._twitch_token = None
                        raise VideoAPIError("Token expired")
                    else:
                        raise VideoAPIError(f"Failed: {await response.text()}")

        try:
            return await self._twitch_breaker.call(_fetch)
        except VideoAPIError as e:
            logger.error(f"Twitch channel info error: {e}")
            return None

    @with_retry(max_retries=2, initial_delay=1.0)
    async def get_twitch_clips(
        self,
        broadcaster_id: str,
        limit: int = 5,
        started_at: Optional[str] = None
    ) -> List[VideoInfo]:
        """
        Get recent clips from a Twitch channel.

        Args:
            broadcaster_id: Twitch broadcaster ID
            limit: Max clips to return (default 5)
            started_at: ISO timestamp to filter clips from

        Returns:
            List of VideoInfo for clips
        """
        async def _fetch():
            token = await self._get_twitch_token()
            headers = {
                "Client-ID": self.twitch_client_id,
                "Authorization": f"Bearer {token}"
            }
            params = {
                'broadcaster_id': broadcaster_id,
                'first': min(limit, 20)  # Twitch max is 100
            }
            if started_at:
                params['started_at'] = started_at

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.TWITCH_HELIX_API}/clips",
                    headers=headers,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        clips = data.get('data', [])
                        return [
                            VideoInfo(
                                platform='twitch',
                                video_id=clip['id'],
                                title=clip['title'],
                                thumbnail_url=clip['thumbnail_url'],
                                video_url=clip['url'],
                                duration_seconds=int(clip.get('duration', 0)),
                                view_count=clip.get('view_count', 0),
                                created_at=clip.get('created_at')
                            )
                            for clip in clips
                        ]
                    elif response.status == 401:
                        self._twitch_token = None
                        raise VideoAPIError("Token expired")
                    else:
                        raise VideoAPIError(f"Failed: {await response.text()}")

        try:
            return await self._twitch_breaker.call(_fetch)
        except VideoAPIError as e:
            logger.error(f"Twitch clips error: {e}")
            return []

    async def check_twitch_live(self, broadcaster_id: str) -> bool:
        """Check if a Twitch channel is currently live"""
        async def _fetch():
            token = await self._get_twitch_token()
            headers = {
                "Client-ID": self.twitch_client_id,
                "Authorization": f"Bearer {token}"
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.TWITCH_HELIX_API}/streams",
                    headers=headers,
                    params={'user_id': broadcaster_id},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        streams = data.get('data', [])
                        return len(streams) > 0
                    return False

        try:
            return await self._twitch_breaker.call(_fetch)
        except VideoAPIError:
            return False

    # =====================================================
    # YOUTUBE METHODS
    # =====================================================

    @with_retry(max_retries=2, initial_delay=1.0)
    async def get_youtube_channel_by_handle(
        self,
        handle: str
    ) -> Optional[Dict[str, Any]]:
        """Get YouTube channel by handle (e.g., @username)"""
        if not self.youtube_api_key:
            logger.warning("YouTube API key not configured")
            return None

        async def _fetch():
            # Remove @ if present
            clean_handle = handle.lstrip('@')
            params = {
                'key': self.youtube_api_key,
                'forHandle': clean_handle,
                'part': 'snippet,contentDetails'
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.YOUTUBE_API}/channels",
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        items = data.get('items', [])
                        return items[0] if items else None
                    else:
                        raise VideoAPIError(f"YT error: {await response.text()}")

        try:
            return await self._youtube_breaker.call(_fetch)
        except VideoAPIError as e:
            logger.error(f"YouTube channel lookup error: {e}")
            return None

    @with_retry(max_retries=2, initial_delay=1.0)
    async def get_youtube_channel_info(
        self,
        channel_id: str
    ) -> Optional[ChannelInfo]:
        """Get YouTube channel info by channel ID"""
        if not self.youtube_api_key:
            return None

        async def _fetch():
            params = {
                'key': self.youtube_api_key,
                'id': channel_id,
                'part': 'snippet,contentDetails'
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.YOUTUBE_API}/channels",
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        items = data.get('items', [])
                        if not items:
                            return None
                        ch = items[0]
                        snippet = ch.get('snippet', {})
                        return ChannelInfo(
                            platform='youtube',
                            user_id=ch['id'],
                            username=snippet.get('customUrl', '').lstrip('@'),
                            display_name=snippet.get('title', ''),
                            profile_image_url=snippet.get('thumbnails', {})
                                .get('default', {}).get('url'),
                            game_name=None,  # YouTube doesn't have games
                            is_live=False
                        )
                    else:
                        raise VideoAPIError(f"YT error: {await response.text()}")

        try:
            return await self._youtube_breaker.call(_fetch)
        except VideoAPIError as e:
            logger.error(f"YouTube channel info error: {e}")
            return None

    @with_retry(max_retries=2, initial_delay=1.0)
    async def get_youtube_videos(
        self,
        channel_id: str,
        limit: int = 5
    ) -> List[VideoInfo]:
        """
        Get recent videos from a YouTube channel.

        Args:
            channel_id: YouTube channel ID
            limit: Max videos to return

        Returns:
            List of VideoInfo for videos
        """
        if not self.youtube_api_key:
            return []

        async def _fetch():
            # First get uploads playlist
            params = {
                'key': self.youtube_api_key,
                'channelId': channel_id,
                'part': 'snippet',
                'order': 'date',
                'maxResults': min(limit, 25),
                'type': 'video'
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.YOUTUBE_API}/search",
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        items = data.get('items', [])
                        return [
                            VideoInfo(
                                platform='youtube',
                                video_id=item['id']['videoId'],
                                title=item['snippet']['title'],
                                thumbnail_url=item['snippet']['thumbnails']
                                    .get('high', {})
                                    .get('url', item['snippet']['thumbnails']
                                         .get('default', {}).get('url', '')),
                                video_url=f"https://youtube.com/watch?v="
                                          f"{item['id']['videoId']}",
                                created_at=item['snippet'].get('publishedAt')
                            )
                            for item in items
                            if item['id'].get('videoId')
                        ]
                    else:
                        raise VideoAPIError(f"YT error: {await response.text()}")

        try:
            return await self._youtube_breaker.call(_fetch)
        except VideoAPIError as e:
            logger.error(f"YouTube videos error: {e}")
            return []

    # =====================================================
    # COMBINED METHODS
    # =====================================================

    async def get_video_for_shoutout(
        self,
        platform: str,
        username: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get video content for a shoutout.

        Returns the best available video (most recent clip/video) along with
        channel info including last game played.

        Args:
            platform: 'twitch' or 'youtube'
            username: Platform username
            user_id: Platform user ID

        Returns:
            Dict with 'video', 'channel', and 'game_name' or None
        """
        if platform == 'twitch':
            return await self._get_twitch_shoutout_data(username, user_id)
        elif platform == 'youtube':
            return await self._get_youtube_shoutout_data(username, user_id)
        else:
            logger.warning(f"Unsupported platform: {platform}")
            return None

    async def _get_twitch_shoutout_data(
        self,
        username: Optional[str],
        user_id: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """Get Twitch shoutout data with clip and channel info"""
        # Get user if only username provided
        if username and not user_id:
            user = await self.get_twitch_user(username=username)
            if not user:
                return None
            user_id = user['id']

        # Fetch channel info and clips in parallel
        channel_task = self.get_twitch_channel_info(user_id)
        clips_task = self.get_twitch_clips(user_id, limit=1)
        live_task = self.check_twitch_live(user_id)

        channel, clips, is_live = await asyncio.gather(
            channel_task, clips_task, live_task,
            return_exceptions=True
        )

        # Handle exceptions
        if isinstance(channel, Exception):
            logger.error(f"Channel info error: {channel}")
            channel = None
        if isinstance(clips, Exception):
            logger.error(f"Clips error: {clips}")
            clips = []
        if isinstance(is_live, Exception):
            is_live = False

        if channel:
            channel.is_live = is_live

        return {
            'video': clips[0] if clips else None,
            'channel': channel,
            'game_name': channel.game_name if channel else None,
            'is_live': is_live
        }

    async def _get_youtube_shoutout_data(
        self,
        username: Optional[str],
        channel_id: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """Get YouTube shoutout data with video and channel info"""
        # Get channel if only username/handle provided
        if username and not channel_id:
            channel_data = await self.get_youtube_channel_by_handle(username)
            if not channel_data:
                return None
            channel_id = channel_data['id']

        # Fetch channel info and videos in parallel
        channel_task = self.get_youtube_channel_info(channel_id)
        videos_task = self.get_youtube_videos(channel_id, limit=1)

        channel, videos = await asyncio.gather(
            channel_task, videos_task,
            return_exceptions=True
        )

        if isinstance(channel, Exception):
            logger.error(f"Channel info error: {channel}")
            channel = None
        if isinstance(videos, Exception):
            logger.error(f"Videos error: {videos}")
            videos = []

        return {
            'video': videos[0] if videos else None,
            'channel': channel,
            'game_name': None,  # YouTube doesn't track games
            'is_live': False  # Would need separate live check
        }

    def get_circuit_breaker_metrics(self) -> Dict[str, Any]:
        """Get circuit breaker metrics for both platforms"""
        return {
            'twitch': self._twitch_breaker.get_metrics(),
            'youtube': self._youtube_breaker.get_metrics()
        }
