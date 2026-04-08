"""
KICK API Client
Handles communication with KICK's REST API
"""
import aiohttp
from typing import Optional


class KickAPI:
    """Async client for KICK API v2."""

    BASE_URL = 'https://kick.com/api/v2'

    def __init__(self, access_token: Optional[str] = None):
        """
        Initialize KICK API client.

        Args:
            access_token: OAuth access token for authenticated requests
        """
        self.access_token = access_token

    def _get_headers(self) -> dict:
        """Get headers for API requests."""
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }
        if self.access_token:
            headers['Authorization'] = f'Bearer {self.access_token}'
        return headers

    async def get_channel(self, channel_slug: str) -> dict:
        """
        Get channel info by slug (username).

        Args:
            channel_slug: The channel's slug/username

        Returns:
            Channel information dict
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f'{self.BASE_URL}/channels/{channel_slug}',
                headers=self._get_headers()
            ) as resp:
                resp.raise_for_status()
                return await resp.json()

    async def get_livestream(self, channel_slug: str) -> Optional[dict]:
        """
        Get current livestream info for a channel.

        Args:
            channel_slug: The channel's slug/username

        Returns:
            Livestream info dict or None if offline
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f'{self.BASE_URL}/channels/{channel_slug}/livestream',
                headers=self._get_headers()
            ) as resp:
                if resp.status == 404:
                    return None
                resp.raise_for_status()
                return await resp.json()

    async def get_channel_videos(self, channel_slug: str, limit: int = 10) -> list:
        """
        Get VODs for a channel.

        Args:
            channel_slug: The channel's slug/username
            limit: Maximum number of videos to return

        Returns:
            List of video info dicts
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f'{self.BASE_URL}/channels/{channel_slug}/videos',
                params={'limit': limit},
                headers=self._get_headers()
            ) as resp:
                resp.raise_for_status()
                return await resp.json()

    async def send_chat_message(self, chatroom_id: int, message: str) -> dict:
        """
        Send a message to a channel's chat.

        Args:
            chatroom_id: The chatroom ID
            message: Message content

        Returns:
            API response dict

        Requires authenticated access token with chat:write scope.
        """
        if not self.access_token:
            raise ValueError("Access token required for sending messages")

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f'{self.BASE_URL}/messages/send/{chatroom_id}',
                headers=self._get_headers(),
                json={'content': message}
            ) as resp:
                resp.raise_for_status()
                return await resp.json()

    async def get_user(self) -> dict:
        """
        Get authenticated user info.

        Returns:
            User info dict

        Requires authenticated access token.
        """
        if not self.access_token:
            raise ValueError("Access token required")

        async with aiohttp.ClientSession() as session:
            async with session.get(
                f'{self.BASE_URL}/user',
                headers=self._get_headers()
            ) as resp:
                resp.raise_for_status()
                return await resp.json()

    async def get_chatroom_info(self, channel_slug: str) -> dict:
        """
        Get chatroom info for a channel.

        Args:
            channel_slug: The channel's slug/username

        Returns:
            Chatroom info including ID
        """
        channel = await self.get_channel(channel_slug)
        return channel.get('chatroom', {})
