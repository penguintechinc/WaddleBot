"""
Discord Emote Provider - Discord emoji detection and API integration
====================================================================

Supports two modes of operation:
1. Regex detection: Detects <:name:id> format in messages (always works)
2. API fetching: Fetches guild emojis from Discord API (requires bot token)

Discord emotes are inline in messages with the format:
- Custom emotes: <:name:id> or <a:name:id> (animated)
- Unicode emojis: handled natively by the platform
"""

import logging
import re
from typing import List, Optional, Set

import httpx

from .base_emote_provider import BaseEmoteProvider, Emote

logger = logging.getLogger(__name__)

# Discord custom emote pattern: <:name:id> or <a:name:id>
DISCORD_EMOTE_PATTERN = re.compile(r'<(a?):(\w+):(\d+)>')

# Discord API endpoints
DISCORD_API_BASE = "https://discord.com/api/v10"
DISCORD_GUILD_EMOJIS_URL = f"{DISCORD_API_BASE}/guilds/{{guild_id}}/emojis"

# Request timeout in seconds
REQUEST_TIMEOUT = 10


class DiscordEmoteProvider(BaseEmoteProvider):
    """
    Emote provider for Discord platform.

    Features:
    - Regex detection for inline Discord emotes (always works)
    - Optional Discord API integration for fetching guild emojis
    - Requires bot token for API mode
    """

    def __init__(self, bot_token: Optional[str] = None):
        """
        Initialize Discord emote provider.

        Args:
            bot_token: Discord bot token for API access (optional).
                      If not provided, tries to load from config.
        """
        super().__init__("discord")

        # Try to get bot_token from config if not provided
        if bot_token is None:
            try:
                from config import Config
                bot_token = getattr(Config, 'DISCORD_BOT_TOKEN', None)
            except ImportError:
                pass

        self._bot_token = bot_token
        self._client: Optional[httpx.AsyncClient] = None

        # Common Unicode emoji that should also be preserved
        self._unicode_emoji: Set[str] = set()

        if self._bot_token:
            logger.info("DiscordEmoteProvider initialized with API support")
        else:
            logger.info("DiscordEmoteProvider initialized (regex mode only)")

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            headers = {"User-Agent": "WaddleBot/1.0"}
            if self._bot_token:
                headers["Authorization"] = f"Bot {self._bot_token}"
            self._client = httpx.AsyncClient(
                timeout=REQUEST_TIMEOUT,
                headers=headers
            )
        return self._client

    async def fetch_emotes(
        self,
        channel_id: Optional[str] = None,
        sources: Optional[List[str]] = None
    ) -> List[Emote]:
        """
        Fetch Discord guild emojis from the Discord API.

        Requires a bot token to be configured. If no token is available,
        returns an empty list (emotes will be detected via regex instead).

        Args:
            channel_id: Discord guild ID to fetch emojis for
            sources: Not used for Discord (kept for interface compatibility)

        Returns:
            List of Emote objects, or empty if no token/guild_id
        """
        # Without a bot token, we can only detect via regex
        if not self._bot_token:
            logger.debug("Discord emotes detected via regex (no API token)")
            return []

        # channel_id for Discord should be the guild_id
        if not channel_id:
            logger.debug("No guild_id provided - skipping Discord API fetch")
            return []

        return await self._fetch_guild_emojis(channel_id)

    async def _fetch_guild_emojis(self, guild_id: str) -> List[Emote]:
        """
        Fetch all custom emojis for a Discord guild.

        Args:
            guild_id: The Discord guild (server) ID

        Returns:
            List of Emote objects
        """
        try:
            client = await self._get_client()
            url = DISCORD_GUILD_EMOJIS_URL.format(guild_id=guild_id)
            response = await client.get(url)

            if response.status_code == 403:
                logger.warning(f"No permission to fetch emojis for guild {guild_id}")
                return []

            if response.status_code == 404:
                logger.debug(f"Guild {guild_id} not found or bot not in guild")
                return []

            response.raise_for_status()
            data = response.json()

            emotes = []
            for emoji in data:
                name = emoji.get('name', '')
                emote_id = emoji.get('id')
                animated = emoji.get('animated', False)

                # Store both the name and the full format for matching
                emotes.append(Emote(
                    code=name,  # Store just the name for lookup
                    source='native',
                    platform='discord',
                    channel_id=guild_id,
                    emote_id=emote_id,
                    url=self._get_discord_emote_url(emote_id, animated)
                ))

            logger.debug(f"Fetched {len(emotes)} Discord emojis for guild {guild_id}")
            return emotes

        except Exception as e:
            logger.error(f"Failed to fetch Discord guild emojis: {e}")
            return []

    def detect_emotes_in_text(self, text: str) -> List[Emote]:
        """
        Detect Discord custom emotes in message text.

        Args:
            text: Message text to scan

        Returns:
            List of detected Emote objects
        """
        emotes = []

        for match in DISCORD_EMOTE_PATTERN.finditer(text):
            animated = match.group(1) == 'a'
            name = match.group(2)
            emote_id = match.group(3)

            # Full match text includes the angle brackets
            full_match = match.group(0)

            emotes.append(Emote(
                code=full_match,  # Keep full format for preservation
                source='native',
                platform='discord',
                emote_id=emote_id,
                url=self._get_discord_emote_url(emote_id, animated)
            ))

        logger.debug(f"Detected {len(emotes)} Discord emotes in text")
        return emotes

    def _get_discord_emote_url(self, emote_id: str, animated: bool) -> str:
        """Get Discord CDN URL for an emote."""
        ext = 'gif' if animated else 'png'
        return f"https://cdn.discordapp.com/emojis/{emote_id}.{ext}"

    def is_discord_emote(self, text: str) -> bool:
        """
        Check if text is a Discord custom emote.

        Args:
            text: Text to check

        Returns:
            True if text matches Discord emote pattern
        """
        return bool(DISCORD_EMOTE_PATTERN.fullmatch(text))

    async def health_check(self) -> bool:
        """
        Check if Discord provider is healthy.

        Returns True if:
        - No bot token configured (regex mode works without API)
        - Bot token configured and API is accessible
        """
        if not self._bot_token:
            # Regex mode is always healthy
            return True

        try:
            client = await self._get_client()
            # Check we can reach Discord API (use /users/@me as health check)
            response = await client.get(f"{DISCORD_API_BASE}/users/@me", timeout=5)
            return response.status_code in [200, 401]  # 401 means API is up but token may be invalid
        except Exception:
            return False

    async def close(self):
        """Close HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
