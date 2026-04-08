"""
Shoutout Service

Generates platform-aware shoutout messages with customizable templates.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ShoutoutService:
    """
    Service for generating shoutout messages.

    Supports:
    - Custom templates per community
    - Platform-specific formatting
    - Variable substitution
    - Fallback messages
    """

    # Default templates
    DEFAULT_TEMPLATES = {
        'twitch': {
            'live': (
                "Go check out {display_name} at twitch.tv/{login}! "
                "They're currently streaming {game_name} with {viewer_count} viewers! "
                "Last seen playing: {game_name}"
            ),
            'offline': (
                "Go check out {display_name} at twitch.tv/{login}! "
                "They were last seen streaming {game_name}. "
                "Show them some love!"
            ),
            'minimal': (
                "Shoutout to {display_name}! "
                "Check them out at twitch.tv/{login}"
            )
        },
        'discord': {
            'default': (
                "**Shoutout** to {display_name}! "
                "Check out their stream at <https://twitch.tv/{login}>"
            )
        },
        'slack': {
            'default': (
                "*Shoutout* to {display_name}! "
                "Check them out at <https://twitch.tv/{login}|twitch.tv/{login}>"
            )
        }
    }

    def __init__(self, dal):
        """
        Initialize shoutout service.

        Args:
            dal: Database access layer
        """
        self.dal = dal

    async def generate_shoutout(
        self,
        twitch_data: Dict[str, Any],
        community_id: int,
        platform: str = 'twitch'
    ) -> Dict[str, Any]:
        """
        Generate shoutout message.

        Args:
            twitch_data: Data from Twitch API (user, channel, stream)
            community_id: Community ID for custom templates
            platform: Target platform (twitch, discord, slack)

        Returns:
            Dictionary with formatted shoutout message and metadata
        """
        user = twitch_data.get('user', {})
        channel = twitch_data.get('channel', {})
        stream = twitch_data.get('stream')
        is_live = twitch_data.get('is_live', False)

        # Get custom template if exists
        template = await self._get_template(community_id, platform, is_live)

        # Prepare variables for substitution
        variables = {
            'display_name': user.get('display_name', 'Unknown'),
            'login': user.get('login', 'unknown'),
            'game_name': (
                stream.get('game_name', 'Unknown') if is_live
                else channel.get('game_name', 'Unknown')
            ),
            'title': stream.get('title', '') if is_live else channel.get('title', ''),
            'viewer_count': stream.get('viewer_count', 0) if is_live else 0,
            'description': user.get('description', ''),
            'broadcaster_type': user.get('broadcaster_type', ''),
            'profile_image_url': user.get('profile_image_url', ''),
            'offline_image_url': user.get('offline_image_url', ''),
        }

        # Format message
        message = template.format(**variables)

        # Log shoutout
        await self._log_shoutout(
            community_id=community_id,
            target_username=user.get('login'),
            target_user_id=user.get('id'),
            platform=platform,
            message=message
        )

        return {
            'message': message,
            'target_username': user.get('login'),
            'target_display_name': user.get('display_name'),
            'is_live': is_live,
            'game_name': variables['game_name'],
            'viewer_count': variables['viewer_count'] if is_live else None,
            'profile_image_url': variables['profile_image_url'],
        }

    async def _get_template(
        self,
        community_id: int,
        platform: str,
        is_live: bool
    ) -> str:
        """
        Get shoutout template for community.

        Args:
            community_id: Community ID
            platform: Target platform
            is_live: Whether streamer is live

        Returns:
            Template string
        """
        try:
            # Try to get custom template from database
            result = self.dal.executesql(
                """SELECT template FROM shoutout_templates
                   WHERE community_id = %s AND platform = %s AND is_live = %s
                   AND is_active = true
                   LIMIT 1""",
                [community_id, platform, is_live]
            )

            if result and result[0]:
                return result[0][0]

        except Exception as e:
            logger.error(f"Failed to get custom template: {e}")

        # Fallback to default template
        platform_templates = self.DEFAULT_TEMPLATES.get(platform, {})

        if is_live and 'live' in platform_templates:
            return platform_templates['live']
        elif not is_live and 'offline' in platform_templates:
            return platform_templates['offline']
        elif 'default' in platform_templates:
            return platform_templates['default']
        else:
            # Ultimate fallback
            return self.DEFAULT_TEMPLATES['twitch']['minimal']

    async def _log_shoutout(
        self,
        community_id: int,
        target_username: str,
        target_user_id: str,
        platform: str,
        message: str
    ):
        """Log shoutout to database"""
        try:
            self.dal.executesql(
                """INSERT INTO shoutout_history
                   (community_id, target_username, target_user_id, platform, message, created_at)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                [
                    community_id,
                    target_username,
                    target_user_id,
                    platform,
                    message,
                    datetime.utcnow()
                ]
            )
        except Exception as e:
            logger.error(f"Failed to log shoutout: {e}")

    async def get_shoutout_history(
        self,
        community_id: int,
        limit: int = 50
    ) -> list:
        """
        Get recent shoutout history.

        Args:
            community_id: Community ID
            limit: Maximum number of results

        Returns:
            List of shoutout records
        """
        try:
            result = self.dal.executesql(
                """SELECT target_username, target_user_id, platform, message, created_at
                   FROM shoutout_history
                   WHERE community_id = %s
                   ORDER BY created_at DESC
                   LIMIT %s""",
                [community_id, limit]
            )

            return [
                {
                    'target_username': row[0],
                    'target_user_id': row[1],
                    'platform': row[2],
                    'message': row[3],
                    'created_at': row[4].isoformat() if row[4] else None
                }
                for row in result
            ]

        except Exception as e:
            logger.error(f"Failed to get shoutout history: {e}")
            return []

    async def save_custom_template(
        self,
        community_id: int,
        platform: str,
        is_live: bool,
        template: str
    ) -> bool:
        """
        Save custom shoutout template.

        Args:
            community_id: Community ID
            platform: Target platform
            is_live: Whether template is for live streamers
            template: Template string with {variables}

        Returns:
            True if successful
        """
        try:
            # Validate template has required variables
            required_vars = ['display_name', 'login']
            for var in required_vars:
                if f'{{{var}}}' not in template:
                    logger.error(
                        f"Template missing required variable: {var}"
                    )
                    return False

            # Upsert template
            self.dal.executesql(
                """INSERT INTO shoutout_templates
                   (community_id, platform, is_live, template, created_at, updated_at)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   ON CONFLICT (community_id, platform, is_live)
                   DO UPDATE SET template = EXCLUDED.template,
                                 updated_at = EXCLUDED.updated_at""",
                [
                    community_id,
                    platform,
                    is_live,
                    template,
                    datetime.utcnow(),
                    datetime.utcnow()
                ]
            )

            return True

        except Exception as e:
            logger.error(f"Failed to save custom template: {e}")
            return False

    async def get_stats(self, community_id: int) -> Dict[str, Any]:
        """
        Get shoutout statistics for community.

        Args:
            community_id: Community ID

        Returns:
            Statistics dictionary
        """
        try:
            # Total shoutouts
            result = self.dal.executesql(
                """SELECT COUNT(*),
                          COUNT(DISTINCT target_username),
                          MIN(created_at),
                          MAX(created_at)
                   FROM shoutout_history
                   WHERE community_id = %s""",
                [community_id]
            )

            if result and result[0]:
                row = result[0]
                return {
                    'total_shoutouts': row[0],
                    'unique_users': row[1],
                    'first_shoutout': row[2].isoformat() if row[2] else None,
                    'last_shoutout': row[3].isoformat() if row[3] else None
                }

        except Exception as e:
            logger.error(f"Failed to get shoutout stats: {e}")

        return {
            'total_shoutouts': 0,
            'unique_users': 0,
            'first_shoutout': None,
            'last_shoutout': None
        }
