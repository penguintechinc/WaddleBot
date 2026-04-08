"""
Twitch API Service for Shoutout Module

Provides Twitch Helix API integration for:
- User information lookup
- Channel information
- Stream status
- Recent game/category
"""

import logging
import aiohttp
from typing import Optional, Dict, Any
from flask_core import CircuitBreaker, with_retry

logger = logging.getLogger(__name__)


class TwitchAPIError(Exception):
    """Twitch API error"""
    pass


class TwitchService:
    """
    Twitch Helix API service for shoutouts.

    Fetches user and channel information for generating shoutouts.
    """

    # Twitch API endpoint
    HELIX_API = "https://api.twitch.tv/helix"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        access_token: Optional[str] = None
    ):
        """
        Initialize Twitch service.

        Args:
            client_id: Twitch application client ID
            client_secret: Twitch application client secret
            access_token: Optional pre-generated access token
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self._access_token = access_token

        # Circuit breaker for API calls
        self._breaker = CircuitBreaker(
            name="twitch_api",
            failure_threshold=5,
            timeout_seconds=60,
            expected_exception=TwitchAPIError
        )

    async def _get_access_token(self) -> str:
        """Get or refresh OAuth access token"""
        if self._access_token:
            return self._access_token

        # Get app access token
        url = "https://id.twitch.tv/oauth2/token"
        params = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        self._access_token = data['access_token']
                        return self._access_token
                    else:
                        error = await response.text()
                        raise TwitchAPIError(
                            f"Failed to get access token: {error}"
                        )

        except aiohttp.ClientError as e:
            raise TwitchAPIError(f"Network error getting access token: {e}")

    @with_retry(max_retries=2, initial_delay=1.0)
    async def get_user_info(
        self,
        username: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get user information from Twitch.

        Args:
            username: Twitch username (login)
            user_id: Twitch user ID

        Returns:
            User information dict or None if not found
        """
        if not username and not user_id:
            raise ValueError("Either username or user_id must be provided")

        async def _fetch():
            token = await self._get_access_token()
            headers = {
                "Client-ID": self.client_id,
                "Authorization": f"Bearer {token}"
            }

            params = {}
            if username:
                params['login'] = username.lower()
            if user_id:
                params['id'] = user_id

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.HELIX_API}/users",
                    headers=headers,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        users = data.get('data', [])
                        if users:
                            return users[0]
                        return None

                    elif response.status == 401:
                        # Token expired, clear and retry
                        self._access_token = None
                        raise TwitchAPIError("Token expired")

                    else:
                        error = await response.text()
                        raise TwitchAPIError(
                            f"Failed to get user info: {error}"
                        )

        try:
            return await self._breaker.call(_fetch)
        except TwitchAPIError as e:
            logger.error(f"Twitch API error: {e}")
            return None

    @with_retry(max_retries=2, initial_delay=1.0)
    async def get_channel_info(
        self,
        broadcaster_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get channel information.

        Args:
            broadcaster_id: Twitch broadcaster user ID

        Returns:
            Channel info dict or None
        """
        async def _fetch():
            token = await self._get_access_token()
            headers = {
                "Client-ID": self.client_id,
                "Authorization": f"Bearer {token}"
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.HELIX_API}/channels",
                    headers=headers,
                    params={'broadcaster_id': broadcaster_id},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        channels = data.get('data', [])
                        if channels:
                            return channels[0]
                        return None

                    elif response.status == 401:
                        self._access_token = None
                        raise TwitchAPIError("Token expired")

                    else:
                        error = await response.text()
                        raise TwitchAPIError(
                            f"Failed to get channel info: {error}"
                        )

        try:
            return await self._breaker.call(_fetch)
        except TwitchAPIError as e:
            logger.error(f"Twitch API error: {e}")
            return None

    @with_retry(max_retries=2, initial_delay=1.0)
    async def get_stream_info(
        self,
        broadcaster_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get stream information (if live).

        Args:
            broadcaster_id: Twitch broadcaster user ID

        Returns:
            Stream info dict or None if offline
        """
        async def _fetch():
            token = await self._get_access_token()
            headers = {
                "Client-ID": self.client_id,
                "Authorization": f"Bearer {token}"
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.HELIX_API}/streams",
                    headers=headers,
                    params={'user_id': broadcaster_id},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        streams = data.get('data', [])
                        if streams:
                            return streams[0]
                        return None  # Offline

                    elif response.status == 401:
                        self._access_token = None
                        raise TwitchAPIError("Token expired")

                    else:
                        error = await response.text()
                        raise TwitchAPIError(
                            f"Failed to get stream info: {error}"
                        )

        try:
            return await self._breaker.call(_fetch)
        except TwitchAPIError as e:
            logger.error(f"Twitch API error: {e}")
            return None

    async def get_full_shoutout_data(
        self,
        username: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive data for shoutout.

        Args:
            username: Twitch username

        Returns:
            Combined user, channel, and stream data
        """
        # Get user info
        user = await self.get_user_info(username=username)
        if not user:
            return None

        broadcaster_id = user['id']

        # Get channel and stream info in parallel
        channel_task = self.get_channel_info(broadcaster_id)
        stream_task = self.get_stream_info(broadcaster_id)

        channel, stream = await asyncio.gather(
            channel_task,
            stream_task,
            return_exceptions=True
        )

        # Handle exceptions
        if isinstance(channel, Exception):
            logger.error(f"Failed to get channel info: {channel}")
            channel = None

        if isinstance(stream, Exception):
            logger.error(f"Failed to get stream info: {stream}")
            stream = None

        return {
            'user': user,
            'channel': channel,
            'stream': stream,
            'is_live': stream is not None
        }

    def get_circuit_breaker_metrics(self) -> Dict[str, Any]:
        """Get circuit breaker metrics"""
        return self._breaker.get_metrics()


import asyncio  # noqa: E402 (for get_full_shoutout_data)
