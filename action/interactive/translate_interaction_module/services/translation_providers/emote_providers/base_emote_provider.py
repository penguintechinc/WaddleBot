"""
Base Emote Provider - Abstract base class for emote providers
=============================================================

Defines the interface that all emote providers must implement.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Emote:
    """Represents a platform emote."""
    code: str
    source: str  # 'global', 'bttv', 'ffz', '7tv', 'native'
    platform: str
    channel_id: Optional[str] = None
    emote_id: Optional[str] = None
    url: Optional[str] = None


class BaseEmoteProvider(ABC):
    """
    Abstract base class for emote providers.

    Each platform has its own provider implementation that knows
    how to fetch emotes from the relevant APIs.
    """

    def __init__(self, platform: str):
        """
        Initialize the emote provider.

        Args:
            platform: Platform name (twitch, discord, slack, kick)
        """
        self.platform = platform
        logger.info(f"Initialized {self.__class__.__name__} for {platform}")

    @abstractmethod
    async def fetch_emotes(
        self,
        channel_id: Optional[str] = None,
        sources: Optional[List[str]] = None
    ) -> List[Emote]:
        """
        Fetch emotes from external APIs.

        Args:
            channel_id: Optional channel ID for channel-specific emotes
            sources: Optional list of sources to fetch from

        Returns:
            List of Emote objects
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the provider is healthy and can fetch emotes.

        Returns:
            True if healthy, False otherwise
        """
        pass
