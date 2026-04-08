"""
Identity Service for Cross-Platform Lookup

Resolves cross-platform identities using the hub_user_identities table.
Enables video shoutouts to fall back to linked platform accounts.
"""

import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import aiohttp
from config import Config

logger = logging.getLogger(__name__)


@dataclass
class LinkedIdentity:
    """A linked platform identity"""
    platform: str
    platform_user_id: str
    platform_username: str
    is_primary: bool = False


class IdentityService:
    """
    Cross-platform identity resolution service.

    Queries the identity core module to find linked accounts
    for cross-platform video shoutout fallback.
    """

    def __init__(self, identity_url: Optional[str] = None):
        """
        Initialize identity service.

        Args:
            identity_url: URL to identity core module API
        """
        self.identity_url = identity_url or Config.IDENTITY_URL

    async def get_linked_identities(
        self,
        platform: str,
        platform_user_id: str
    ) -> List[LinkedIdentity]:
        """
        Get all linked identities for a user.

        Args:
            platform: Source platform (e.g., 'twitch', 'discord')
            platform_user_id: User's ID on the source platform

        Returns:
            List of LinkedIdentity objects for all linked accounts
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.identity_url}/api/v1/identities/lookup",
                    params={
                        'platform': platform,
                        'platform_user_id': platform_user_id
                    },
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        identities = data.get('identities', [])
                        return [
                            LinkedIdentity(
                                platform=identity['platform'],
                                platform_user_id=identity['platform_user_id'],
                                platform_username=identity.get(
                                    'platform_username', ''
                                ),
                                is_primary=identity.get('is_primary', False)
                            )
                            for identity in identities
                        ]
                    elif response.status == 404:
                        # No linked identities found
                        return []
                    else:
                        error = await response.text()
                        logger.warning(f"Identity lookup failed: {error}")
                        return []

        except aiohttp.ClientError as e:
            logger.error(f"Identity service connection error: {e}")
            return []
        except Exception as e:
            logger.error(f"Identity lookup error: {e}")
            return []

    async def resolve_video_platform(
        self,
        platform: str,
        platform_user_id: str,
        preferred_platforms: Optional[List[str]] = None
    ) -> Optional[LinkedIdentity]:
        """
        Resolve the best platform for video content.

        Checks linked identities to find a platform with video content
        (Twitch or YouTube).

        Args:
            platform: Source platform
            platform_user_id: User's ID on source platform
            preferred_platforms: Priority order for platforms
                                 (default: ['twitch', 'youtube'])

        Returns:
            LinkedIdentity for best video platform or None
        """
        if preferred_platforms is None:
            preferred_platforms = ['twitch', 'youtube']

        # If source platform is already a video platform, return it
        if platform in preferred_platforms:
            return LinkedIdentity(
                platform=platform,
                platform_user_id=platform_user_id,
                platform_username='',  # Will be fetched by video service
                is_primary=True
            )

        # Get linked identities
        identities = await self.get_linked_identities(platform, platform_user_id)
        if not identities:
            return None

        # Find video platform in priority order
        identity_map = {i.platform: i for i in identities}

        for pref_platform in preferred_platforms:
            if pref_platform in identity_map:
                return identity_map[pref_platform]

        return None

    async def find_twitch_identity(
        self,
        platform: str,
        platform_user_id: str
    ) -> Optional[LinkedIdentity]:
        """
        Find Twitch identity for a user (via linked accounts).

        Args:
            platform: Source platform
            platform_user_id: User's ID on source platform

        Returns:
            LinkedIdentity for Twitch or None
        """
        # If already on Twitch, return directly
        if platform == 'twitch':
            return LinkedIdentity(
                platform='twitch',
                platform_user_id=platform_user_id,
                platform_username='',
                is_primary=True
            )

        # Look up linked identities
        identities = await self.get_linked_identities(platform, platform_user_id)

        for identity in identities:
            if identity.platform == 'twitch':
                return identity

        return None

    async def find_youtube_identity(
        self,
        platform: str,
        platform_user_id: str
    ) -> Optional[LinkedIdentity]:
        """
        Find YouTube identity for a user (via linked accounts).

        Args:
            platform: Source platform
            platform_user_id: User's ID on source platform

        Returns:
            LinkedIdentity for YouTube or None
        """
        # If already on YouTube, return directly
        if platform == 'youtube':
            return LinkedIdentity(
                platform='youtube',
                platform_user_id=platform_user_id,
                platform_username='',
                is_primary=True
            )

        # Look up linked identities
        identities = await self.get_linked_identities(platform, platform_user_id)

        for identity in identities:
            if identity.platform == 'youtube':
                return identity

        return None

    async def get_all_video_platforms(
        self,
        platform: str,
        platform_user_id: str
    ) -> Dict[str, LinkedIdentity]:
        """
        Get all video platform identities for a user.

        Args:
            platform: Source platform
            platform_user_id: User's ID on source platform

        Returns:
            Dict mapping platform name to LinkedIdentity
        """
        result = {}
        video_platforms = ['twitch', 'youtube']

        # If source is a video platform, include it
        if platform in video_platforms:
            result[platform] = LinkedIdentity(
                platform=platform,
                platform_user_id=platform_user_id,
                platform_username='',
                is_primary=True
            )

        # Get linked identities
        identities = await self.get_linked_identities(platform, platform_user_id)

        for identity in identities:
            if identity.platform in video_platforms:
                result[identity.platform] = identity

        return result
