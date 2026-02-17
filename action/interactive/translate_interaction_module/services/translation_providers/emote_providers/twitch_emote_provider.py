"""
Twitch Emote Provider - Fetches emotes from Twitch and third-party services
===========================================================================

Fetches emotes from:
- Twitch Official API - Global and channel emotes (requires Client-ID)
- BTTV (BetterTTV) - Global and channel emotes
- FFZ (FrankerFaceZ) - Global and channel emotes
- 7TV - Global and channel emotes
"""

import asyncio
import logging
from typing import List, Optional

import httpx

from .base_emote_provider import BaseEmoteProvider, Emote

logger = logging.getLogger(__name__)

# Twitch Official API (requires Client-ID header)
TWITCH_GLOBAL_EMOTES_URL = "https://api.twitch.tv/helix/chat/emotes/global"
TWITCH_CHANNEL_EMOTES_URL = "https://api.twitch.tv/helix/chat/emotes?broadcaster_id={channel_id}"

# Third-party emote API endpoints (no auth required)
BTTV_GLOBAL_URL = "https://api.betterttv.net/3/cached/emotes/global"
BTTV_CHANNEL_URL = "https://api.betterttv.net/3/cached/users/twitch/{channel_id}"

FFZ_GLOBAL_URL = "https://api.frankerfacez.com/v1/set/global"
FFZ_CHANNEL_URL = "https://api.frankerfacez.com/v1/room/id/{channel_id}"

SEVENTV_GLOBAL_URL = "https://7tv.io/v3/emote-sets/global"
SEVENTV_CHANNEL_URL = "https://7tv.io/v3/users/twitch/{channel_id}"

# Request timeout in seconds
REQUEST_TIMEOUT = 10


class TwitchEmoteProvider(BaseEmoteProvider):
    """
    Emote provider for Twitch platform.

    Fetches emotes from Twitch Official API, BTTV, FFZ, and 7TV.
    """

    def __init__(self, client_id: Optional[str] = None):
        """
        Initialize Twitch emote provider.

        Args:
            client_id: Twitch Client-ID for official API (optional but recommended)
        """
        super().__init__("twitch")
        self._client: Optional[httpx.AsyncClient] = None

        # Try to get client_id from config if not provided
        if client_id is None:
            try:
                from config import Config
                client_id = getattr(Config, 'TWITCH_CLIENT_ID', None)
            except ImportError:
                pass

        self._client_id = client_id
        if self._client_id:
            logger.info("TwitchEmoteProvider initialized with official API support")
        else:
            logger.info("TwitchEmoteProvider initialized (third-party APIs only)")

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=REQUEST_TIMEOUT,
                headers={"User-Agent": "WaddleBot/1.0"}
            )
        return self._client

    async def fetch_emotes(
        self,
        channel_id: Optional[str] = None,
        sources: Optional[List[str]] = None
    ) -> List[Emote]:
        """
        Fetch emotes from Twitch Official API, BTTV, FFZ, and 7TV.

        Args:
            channel_id: Twitch channel ID (numeric) for channel emotes
            sources: List of sources to fetch ('twitch', 'bttv', 'ffz', '7tv', 'global')

        Returns:
            List of Emote objects
        """
        # Default to all sources
        if sources is None:
            sources = ['global', 'twitch', 'bttv', 'ffz', '7tv']

        emotes: List[Emote] = []
        tasks = []

        # Twitch Official API (if client_id configured)
        if self._client_id and ('twitch' in sources or 'global' in sources):
            tasks.append(self._fetch_twitch_global())
            if channel_id:
                tasks.append(self._fetch_twitch_channel(channel_id))

        # Third-party APIs
        if 'bttv' in sources or 'global' in sources:
            tasks.append(self._fetch_bttv_global())
            if channel_id:
                tasks.append(self._fetch_bttv_channel(channel_id))

        if 'ffz' in sources or 'global' in sources:
            tasks.append(self._fetch_ffz_global())
            if channel_id:
                tasks.append(self._fetch_ffz_channel(channel_id))

        if '7tv' in sources or 'global' in sources:
            tasks.append(self._fetch_7tv_global())
            if channel_id:
                tasks.append(self._fetch_7tv_channel(channel_id))

        # Fetch all in parallel
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    logger.warning(f"Emote fetch task failed: {result}")
                elif isinstance(result, list):
                    emotes.extend(result)

        logger.info(f"Fetched {len(emotes)} Twitch emotes")
        return emotes

    async def _fetch_twitch_global(self) -> List[Emote]:
        """Fetch global Twitch emotes from official API."""
        if not self._client_id:
            logger.debug("Skipping Twitch global emotes - no client_id configured")
            return []

        try:
            client = await self._get_client()
            headers = {
                "Client-ID": self._client_id,
                "Authorization": f"Bearer {self._get_app_access_token()}"
            }
            response = await client.get(TWITCH_GLOBAL_EMOTES_URL, headers=headers)

            if response.status_code == 401:
                logger.warning("Twitch API auth failed - check client credentials")
                return []

            response.raise_for_status()
            data = response.json()

            emotes = []
            for item in data.get('data', []):
                emotes.append(Emote(
                    code=item.get('name', ''),
                    source='twitch',
                    platform='twitch',
                    emote_id=item.get('id'),
                    url=item.get('images', {}).get('url_1x')
                ))

            logger.debug(f"Fetched {len(emotes)} Twitch global emotes")
            return emotes

        except Exception as e:
            logger.error(f"Failed to fetch Twitch global emotes: {e}")
            return []

    async def _fetch_twitch_channel(self, channel_id: str) -> List[Emote]:
        """Fetch channel-specific Twitch emotes from official API."""
        if not self._client_id:
            logger.debug("Skipping Twitch channel emotes - no client_id configured")
            return []

        try:
            client = await self._get_client()
            headers = {
                "Client-ID": self._client_id,
                "Authorization": f"Bearer {self._get_app_access_token()}"
            }
            url = TWITCH_CHANNEL_EMOTES_URL.format(channel_id=channel_id)
            response = await client.get(url, headers=headers)

            if response.status_code == 404:
                logger.debug(f"No Twitch emotes for channel {channel_id}")
                return []

            if response.status_code == 401:
                logger.warning("Twitch API auth failed - check client credentials")
                return []

            response.raise_for_status()
            data = response.json()

            emotes = []
            for item in data.get('data', []):
                emotes.append(Emote(
                    code=item.get('name', ''),
                    source='twitch',
                    platform='twitch',
                    channel_id=channel_id,
                    emote_id=item.get('id'),
                    url=item.get('images', {}).get('url_1x')
                ))

            logger.debug(f"Fetched {len(emotes)} Twitch channel emotes for {channel_id}")
            return emotes

        except Exception as e:
            logger.error(f"Failed to fetch Twitch channel emotes: {e}")
            return []

    def _get_app_access_token(self) -> str:
        """
        Get Twitch app access token for API calls.

        Note: In production, this should cache the token and refresh when needed.
        For now, returns empty string - API calls will work with just Client-ID
        for public endpoints, or you can implement OAuth flow.
        """
        # TODO: Implement proper OAuth app access token flow
        # For now, many emote endpoints work with just Client-ID
        return ""

    async def _fetch_bttv_global(self) -> List[Emote]:
        """Fetch global BTTV emotes."""
        try:
            client = await self._get_client()
            response = await client.get(BTTV_GLOBAL_URL)
            response.raise_for_status()
            data = response.json()

            emotes = []
            for item in data:
                emotes.append(Emote(
                    code=item.get('code', ''),
                    source='bttv',
                    platform='twitch',
                    emote_id=item.get('id'),
                    url=f"https://cdn.betterttv.net/emote/{item.get('id')}/1x"
                ))

            logger.debug(f"Fetched {len(emotes)} BTTV global emotes")
            return emotes

        except Exception as e:
            logger.error(f"Failed to fetch BTTV global emotes: {e}")
            return []

    async def _fetch_bttv_channel(self, channel_id: str) -> List[Emote]:
        """Fetch channel-specific BTTV emotes."""
        try:
            client = await self._get_client()
            url = BTTV_CHANNEL_URL.format(channel_id=channel_id)
            response = await client.get(url)

            if response.status_code == 404:
                logger.debug(f"No BTTV emotes for channel {channel_id}")
                return []

            response.raise_for_status()
            data = response.json()

            emotes = []

            # Channel emotes
            for item in data.get('channelEmotes', []):
                emotes.append(Emote(
                    code=item.get('code', ''),
                    source='bttv',
                    platform='twitch',
                    channel_id=channel_id,
                    emote_id=item.get('id'),
                    url=f"https://cdn.betterttv.net/emote/{item.get('id')}/1x"
                ))

            # Shared emotes
            for item in data.get('sharedEmotes', []):
                emotes.append(Emote(
                    code=item.get('code', ''),
                    source='bttv',
                    platform='twitch',
                    channel_id=channel_id,
                    emote_id=item.get('id'),
                    url=f"https://cdn.betterttv.net/emote/{item.get('id')}/1x"
                ))

            logger.debug(f"Fetched {len(emotes)} BTTV channel emotes for {channel_id}")
            return emotes

        except Exception as e:
            logger.error(f"Failed to fetch BTTV channel emotes: {e}")
            return []

    async def _fetch_ffz_global(self) -> List[Emote]:
        """Fetch global FFZ emotes."""
        try:
            client = await self._get_client()
            response = await client.get(FFZ_GLOBAL_URL)
            response.raise_for_status()
            data = response.json()

            emotes = []
            default_sets = data.get('default_sets', [])
            sets = data.get('sets', {})

            for set_id in default_sets:
                set_data = sets.get(str(set_id), {})
                for item in set_data.get('emoticons', []):
                    emotes.append(Emote(
                        code=item.get('name', ''),
                        source='ffz',
                        platform='twitch',
                        emote_id=str(item.get('id')),
                        url=item.get('urls', {}).get('1')
                    ))

            logger.debug(f"Fetched {len(emotes)} FFZ global emotes")
            return emotes

        except Exception as e:
            logger.error(f"Failed to fetch FFZ global emotes: {e}")
            return []

    async def _fetch_ffz_channel(self, channel_id: str) -> List[Emote]:
        """Fetch channel-specific FFZ emotes."""
        try:
            client = await self._get_client()
            url = FFZ_CHANNEL_URL.format(channel_id=channel_id)
            response = await client.get(url)

            if response.status_code == 404:
                logger.debug(f"No FFZ emotes for channel {channel_id}")
                return []

            response.raise_for_status()
            data = response.json()

            emotes = []
            sets = data.get('sets', {})

            for set_id, set_data in sets.items():
                for item in set_data.get('emoticons', []):
                    emotes.append(Emote(
                        code=item.get('name', ''),
                        source='ffz',
                        platform='twitch',
                        channel_id=channel_id,
                        emote_id=str(item.get('id')),
                        url=item.get('urls', {}).get('1')
                    ))

            logger.debug(f"Fetched {len(emotes)} FFZ channel emotes for {channel_id}")
            return emotes

        except Exception as e:
            logger.error(f"Failed to fetch FFZ channel emotes: {e}")
            return []

    async def _fetch_7tv_global(self) -> List[Emote]:
        """Fetch global 7TV emotes."""
        try:
            client = await self._get_client()
            response = await client.get(SEVENTV_GLOBAL_URL)
            response.raise_for_status()
            data = response.json()

            emotes = []
            for item in data.get('emotes', []):
                emote_data = item.get('data', {})
                emotes.append(Emote(
                    code=item.get('name', ''),
                    source='7tv',
                    platform='twitch',
                    emote_id=item.get('id'),
                    url=self._get_7tv_url(emote_data)
                ))

            logger.debug(f"Fetched {len(emotes)} 7TV global emotes")
            return emotes

        except Exception as e:
            logger.error(f"Failed to fetch 7TV global emotes: {e}")
            return []

    async def _fetch_7tv_channel(self, channel_id: str) -> List[Emote]:
        """Fetch channel-specific 7TV emotes."""
        try:
            client = await self._get_client()
            url = SEVENTV_CHANNEL_URL.format(channel_id=channel_id)
            response = await client.get(url)

            if response.status_code == 404:
                logger.debug(f"No 7TV emotes for channel {channel_id}")
                return []

            response.raise_for_status()
            data = response.json()

            emotes = []
            emote_set = data.get('emote_set', {})

            for item in emote_set.get('emotes', []):
                emote_data = item.get('data', {})
                emotes.append(Emote(
                    code=item.get('name', ''),
                    source='7tv',
                    platform='twitch',
                    channel_id=channel_id,
                    emote_id=item.get('id'),
                    url=self._get_7tv_url(emote_data)
                ))

            logger.debug(f"Fetched {len(emotes)} 7TV channel emotes for {channel_id}")
            return emotes

        except Exception as e:
            logger.error(f"Failed to fetch 7TV channel emotes: {e}")
            return []

    def _get_7tv_url(self, emote_data: dict) -> Optional[str]:
        """Get 7TV emote URL from emote data."""
        host = emote_data.get('host', {})
        files = host.get('files', [])
        if files:
            # Get smallest size (1x)
            for f in files:
                if f.get('name', '').endswith('1x.webp'):
                    base_url = host.get('url', '')
                    return f"https:{base_url}/{f.get('name')}"
        return None

    async def health_check(self) -> bool:
        """Check if BTTV API is accessible."""
        try:
            client = await self._get_client()
            response = await client.get(BTTV_GLOBAL_URL, timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    async def close(self):
        """Close HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
