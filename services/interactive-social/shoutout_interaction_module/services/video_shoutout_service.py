"""
Video Shoutout Service

Core logic for video shoutouts (!vso command):
- Permission checking
- Community type validation (creator/gaming only)
- Cooldown management
- Cross-platform video lookup with fallback
- History recording
- Auto-shoutout eligibility
"""

import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import asyncpg
from config import Config
from .video_service import VideoService, VideoInfo, ChannelInfo
from .identity_service import IdentityService, LinkedIdentity

logger = logging.getLogger(__name__)


# Community types that support shoutouts
SHOUTOUT_ELIGIBLE_TYPES = ['creator', 'gaming']

# Permission levels in order of precedence
PERMISSION_LEVELS = ['admin_only', 'mod', 'vip', 'subscriber', 'everyone']


@dataclass
class VideoShoutoutResult:
    """Result of a video shoutout execution"""
    success: bool
    video: Optional[VideoInfo] = None
    channel: Optional[ChannelInfo] = None
    game_name: Optional[str] = None
    is_live: bool = False
    error: Optional[str] = None
    cooldown_remaining: Optional[int] = None  # seconds


@dataclass
class ShoutoutConfig:
    """Community shoutout configuration"""
    so_enabled: bool = True
    so_permission: str = 'mod'
    vso_enabled: bool = True
    vso_permission: str = 'mod'
    auto_shoutout_mode: str = 'disabled'
    trigger_first_message: bool = False
    trigger_raid_host: bool = True
    widget_position: str = 'bottom-right'
    widget_duration_seconds: int = 30
    cooldown_minutes: int = 60


class VideoShoutoutService:
    """
    Video shoutout service for !vso command.

    Handles permission checking, cooldowns, cross-platform lookup,
    and recording of video shoutouts.
    """

    def __init__(
        self,
        db_pool: asyncpg.Pool,
        video_service: VideoService,
        identity_service: IdentityService
    ):
        self.db = db_pool
        self.video_service = video_service
        self.identity_service = identity_service

    async def check_community_eligible(self, community_id: int) -> bool:
        """
        Check if community type supports shoutouts.

        Only 'creator' and 'gaming' communities can use shoutouts.
        """
        async with self.db.acquire() as conn:
            result = await conn.fetchrow(
                "SELECT community_type FROM communities WHERE id = $1",
                community_id
            )
            if not result:
                return False
            return result['community_type'] in SHOUTOUT_ELIGIBLE_TYPES

    async def get_config(self, community_id: int) -> Optional[ShoutoutConfig]:
        """Get shoutout configuration for a community"""
        async with self.db.acquire() as conn:
            result = await conn.fetchrow(
                """SELECT so_enabled, so_permission, vso_enabled, vso_permission,
                          auto_shoutout_mode, trigger_first_message, trigger_raid_host,
                          widget_position, widget_duration_seconds, cooldown_minutes
                   FROM shoutout_config WHERE community_id = $1""",
                community_id
            )
            if result:
                return ShoutoutConfig(**dict(result))

            # Return defaults if no config exists
            return ShoutoutConfig()

    async def update_config(
        self,
        community_id: int,
        config: Dict[str, Any]
    ) -> bool:
        """Update shoutout configuration for a community"""
        # Validate community eligibility
        if not await self.check_community_eligible(community_id):
            logger.warning(
                f"Cannot update config for non-eligible community {community_id}"
            )
            return False

        async with self.db.acquire() as conn:
            # Upsert config
            await conn.execute(
                """INSERT INTO shoutout_config
                   (community_id, so_enabled, so_permission, vso_enabled, vso_permission,
                    auto_shoutout_mode, trigger_first_message, trigger_raid_host,
                    widget_position, widget_duration_seconds, cooldown_minutes)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                   ON CONFLICT (community_id) DO UPDATE SET
                    so_enabled = EXCLUDED.so_enabled,
                    so_permission = EXCLUDED.so_permission,
                    vso_enabled = EXCLUDED.vso_enabled,
                    vso_permission = EXCLUDED.vso_permission,
                    auto_shoutout_mode = EXCLUDED.auto_shoutout_mode,
                    trigger_first_message = EXCLUDED.trigger_first_message,
                    trigger_raid_host = EXCLUDED.trigger_raid_host,
                    widget_position = EXCLUDED.widget_position,
                    widget_duration_seconds = EXCLUDED.widget_duration_seconds,
                    cooldown_minutes = EXCLUDED.cooldown_minutes,
                    updated_at = NOW()""",
                community_id,
                config.get('so_enabled', True),
                config.get('so_permission', 'mod'),
                config.get('vso_enabled', True),
                config.get('vso_permission', 'mod'),
                config.get('auto_shoutout_mode', 'disabled'),
                config.get('trigger_first_message', False),
                config.get('trigger_raid_host', True),
                config.get('widget_position', 'bottom-right'),
                config.get('widget_duration_seconds', 30),
                config.get('cooldown_minutes', 60)
            )
            return True

    async def check_permission(
        self,
        community_id: int,
        user_roles: List[str],
        command_type: str = 'vso'
    ) -> bool:
        """
        Check if user has permission to use shoutout command.

        Args:
            community_id: Community ID
            user_roles: User's roles (e.g., ['mod', 'vip'])
            command_type: 'so' for text or 'vso' for video

        Returns:
            True if user has permission
        """
        config = await self.get_config(community_id)
        if not config:
            return False

        # Check if command is enabled
        if command_type == 'vso' and not config.vso_enabled:
            return False
        if command_type == 'so' and not config.so_enabled:
            return False

        # Get permission level
        permission = (config.vso_permission if command_type == 'vso'
                      else config.so_permission)

        # Check based on permission level
        if permission == 'everyone':
            return True
        elif permission == 'subscriber':
            return any(r in ['subscriber', 'vip', 'mod', 'admin', 'owner']
                       for r in user_roles)
        elif permission == 'vip':
            return any(r in ['vip', 'mod', 'admin', 'owner'] for r in user_roles)
        elif permission == 'mod':
            return any(r in ['mod', 'admin', 'owner'] for r in user_roles)
        elif permission == 'admin_only':
            return any(r in ['admin', 'owner'] for r in user_roles)

        return False

    async def check_cooldown(
        self,
        community_id: int,
        target_platform: str,
        target_user_id: str
    ) -> Optional[int]:
        """
        Check if target user is on cooldown.

        Returns remaining cooldown seconds or None if not on cooldown.
        """
        config = await self.get_config(community_id)
        if not config:
            return None

        cooldown_threshold = datetime.utcnow() - timedelta(
            minutes=config.cooldown_minutes
        )

        async with self.db.acquire() as conn:
            result = await conn.fetchrow(
                """SELECT created_at FROM video_shoutout_history
                   WHERE community_id = $1
                     AND target_platform = $2
                     AND target_user_id = $3
                     AND created_at > $4
                   ORDER BY created_at DESC LIMIT 1""",
                community_id, target_platform, target_user_id, cooldown_threshold
            )

            if result:
                last_shoutout = result['created_at']
                cooldown_end = last_shoutout + timedelta(
                    minutes=config.cooldown_minutes
                )
                remaining = (cooldown_end - datetime.utcnow()).total_seconds()
                return max(0, int(remaining))

            return None

    async def execute_video_shoutout(
        self,
        community_id: int,
        target_username: str,
        target_platform: str,
        trigger_type: str = 'manual',
        triggered_by_user_id: Optional[str] = None,
        triggered_by_username: Optional[str] = None,
        user_roles: Optional[List[str]] = None,
        skip_permission_check: bool = False
    ) -> VideoShoutoutResult:
        """
        Execute a video shoutout.

        Args:
            community_id: Community ID
            target_username: Username to shoutout
            target_platform: Platform of the target user
            trigger_type: 'manual', 'first_message', 'raid', 'host'
            triggered_by_user_id: User who triggered (for manual)
            triggered_by_username: Username who triggered
            user_roles: Roles of triggering user (for permission check)
            skip_permission_check: Skip permission check (for auto triggers)

        Returns:
            VideoShoutoutResult with video data or error
        """
        # Check community eligibility
        if not await self.check_community_eligible(community_id):
            return VideoShoutoutResult(
                success=False,
                error="Shoutouts not available for this community type"
            )

        # Check permissions (unless auto-triggered)
        if not skip_permission_check and user_roles:
            if not await self.check_permission(community_id, user_roles, 'vso'):
                return VideoShoutoutResult(
                    success=False,
                    error="You don't have permission to use video shoutouts"
                )

        # Get video data with cross-platform fallback
        video_data = await self._get_video_with_fallback(
            target_username, target_platform
        )

        if not video_data or not video_data.get('video'):
            return VideoShoutoutResult(
                success=False,
                error=f"No video content found for {target_username}"
            )

        video = video_data['video']
        channel = video_data.get('channel')

        # Check cooldown
        target_user_id = channel.user_id if channel else target_username
        cooldown = await self.check_cooldown(
            community_id, video.platform, target_user_id
        )
        if cooldown:
            return VideoShoutoutResult(
                success=False,
                error=f"{target_username} was shouted out recently",
                cooldown_remaining=cooldown
            )

        # Record the shoutout
        await self._record_shoutout(
            community_id=community_id,
            target_platform=video.platform,
            target_user_id=target_user_id,
            target_username=channel.display_name if channel else target_username,
            video=video,
            game_name=video_data.get('game_name'),
            trigger_type=trigger_type,
            triggered_by_user_id=triggered_by_user_id,
            triggered_by_username=triggered_by_username
        )

        return VideoShoutoutResult(
            success=True,
            video=video,
            channel=channel,
            game_name=video_data.get('game_name'),
            is_live=video_data.get('is_live', False)
        )

    async def _get_video_with_fallback(
        self,
        username: str,
        platform: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get video content with cross-platform fallback.

        First tries the specified platform, then falls back to
        linked accounts on other video platforms.
        """
        # Try direct lookup first if it's a video platform
        if platform in ['twitch', 'youtube']:
            result = await self.video_service.get_video_for_shoutout(
                platform=platform,
                username=username
            )
            if result and result.get('video'):
                return result

        # Try to find linked video platform accounts
        # Note: This requires the user to have a platform_user_id, which
        # we don't have from just a username. In practice, this fallback
        # would be used when the triggering event includes user IDs.

        # For username-only lookups on non-video platforms (e.g., Discord),
        # we can't do fallback without additional context.
        # The frontend/command handler should resolve user IDs first.

        return None

    async def get_video_with_identity_fallback(
        self,
        platform: str,
        platform_user_id: str,
        username: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get video content using identity service for fallback.

        This method is used when we have the user's platform ID and can
        look up linked accounts.
        """
        # Try primary platform first
        if platform in ['twitch', 'youtube']:
            result = await self.video_service.get_video_for_shoutout(
                platform=platform,
                username=username,
                user_id=platform_user_id
            )
            if result and result.get('video'):
                return result

        # Get linked video platforms
        video_identities = await self.identity_service.get_all_video_platforms(
            platform, platform_user_id
        )

        # Try each video platform
        for vid_platform, identity in video_identities.items():
            if vid_platform == platform:
                continue  # Already tried

            result = await self.video_service.get_video_for_shoutout(
                platform=vid_platform,
                username=identity.platform_username,
                user_id=identity.platform_user_id
            )
            if result and result.get('video'):
                return result

        return None

    async def _record_shoutout(
        self,
        community_id: int,
        target_platform: str,
        target_user_id: str,
        target_username: str,
        video: VideoInfo,
        game_name: Optional[str],
        trigger_type: str,
        triggered_by_user_id: Optional[str],
        triggered_by_username: Optional[str]
    ):
        """Record a video shoutout in history"""
        async with self.db.acquire() as conn:
            await conn.execute(
                """INSERT INTO video_shoutout_history
                   (community_id, target_platform, target_user_id, target_username,
                    video_platform, video_id, video_title, video_thumbnail_url,
                    video_url, game_name, trigger_type,
                    triggered_by_user_id, triggered_by_username)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)""",
                community_id, target_platform, target_user_id, target_username,
                video.platform, video.video_id, video.title, video.thumbnail_url,
                video.video_url, game_name, trigger_type,
                triggered_by_user_id, triggered_by_username
            )

    async def get_history(
        self,
        community_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get video shoutout history for a community"""
        async with self.db.acquire() as conn:
            rows = await conn.fetch(
                """SELECT id, target_platform, target_user_id, target_username,
                          video_platform, video_id, video_title, video_thumbnail_url,
                          video_url, game_name, trigger_type,
                          triggered_by_user_id, triggered_by_username, created_at
                   FROM video_shoutout_history
                   WHERE community_id = $1
                   ORDER BY created_at DESC
                   LIMIT $2 OFFSET $3""",
                community_id, limit, offset
            )
            return [dict(row) for row in rows]

    # =====================================================
    # AUTO-SHOUTOUT METHODS
    # =====================================================

    async def check_auto_shoutout_eligible(
        self,
        community_id: int,
        platform: str,
        user_id: str,
        user_roles: List[str],
        trigger_type: str
    ) -> bool:
        """
        Check if a user is eligible for auto-shoutout.

        Args:
            community_id: Community ID
            platform: User's platform
            user_id: User's platform ID
            user_roles: User's roles in the community
            trigger_type: 'first_message' or 'raid'

        Returns:
            True if user should receive auto-shoutout
        """
        config = await self.get_config(community_id)
        if not config or not config.vso_enabled:
            return False

        # Check if this trigger type is enabled
        if trigger_type == 'first_message' and not config.trigger_first_message:
            return False
        if trigger_type in ['raid', 'host'] and not config.trigger_raid_host:
            return False

        # Check auto-shoutout mode
        mode = config.auto_shoutout_mode
        if mode == 'disabled':
            return False

        if mode == 'all_creators':
            # Auto-shoutout any creator (has Twitch/YouTube linked)
            identities = await self.identity_service.get_all_video_platforms(
                platform, user_id
            )
            return len(identities) > 0

        if mode == 'list_only':
            # Check if user is in the manual creator list
            return await self._is_in_creator_list(community_id, platform, user_id)

        if mode == 'role_based':
            # Check if user has a shoutout-enabled role
            return await self._has_shoutout_role(community_id, user_roles)

        return False

    async def _is_in_creator_list(
        self,
        community_id: int,
        platform: str,
        user_id: str
    ) -> bool:
        """Check if user is in manual creator list"""
        async with self.db.acquire() as conn:
            result = await conn.fetchrow(
                """SELECT id FROM auto_shoutout_creators
                   WHERE community_id = $1
                     AND platform = $2
                     AND platform_user_id = $3""",
                community_id, platform, user_id
            )
            return result is not None

    async def _has_shoutout_role(
        self,
        community_id: int,
        user_roles: List[str]
    ) -> bool:
        """Check if user has a role configured for auto-shoutout"""
        if not user_roles:
            return False

        async with self.db.acquire() as conn:
            result = await conn.fetchrow(
                """SELECT id FROM auto_shoutout_roles
                   WHERE community_id = $1
                     AND role_name = ANY($2)""",
                community_id, user_roles
            )
            return result is not None

    # =====================================================
    # CREATOR LIST MANAGEMENT
    # =====================================================

    async def add_creator(
        self,
        community_id: int,
        platform: str,
        user_id: str,
        username: str,
        added_by: Optional[int] = None,
        custom_trigger: str = 'default'
    ) -> bool:
        """Add a creator to the auto-shoutout list"""
        async with self.db.acquire() as conn:
            try:
                await conn.execute(
                    """INSERT INTO auto_shoutout_creators
                       (community_id, platform, platform_user_id, platform_username,
                        custom_trigger, added_by)
                       VALUES ($1, $2, $3, $4, $5, $6)
                       ON CONFLICT (community_id, platform, platform_user_id)
                       DO UPDATE SET platform_username = EXCLUDED.platform_username,
                                     custom_trigger = EXCLUDED.custom_trigger""",
                    community_id, platform, user_id, username, custom_trigger, added_by
                )
                return True
            except Exception as e:
                logger.error(f"Failed to add creator: {e}")
                return False

    async def remove_creator(
        self,
        community_id: int,
        platform: str,
        user_id: str
    ) -> bool:
        """Remove a creator from the auto-shoutout list"""
        async with self.db.acquire() as conn:
            result = await conn.execute(
                """DELETE FROM auto_shoutout_creators
                   WHERE community_id = $1
                     AND platform = $2
                     AND platform_user_id = $3""",
                community_id, platform, user_id
            )
            return 'DELETE' in result

    async def get_creators(
        self,
        community_id: int
    ) -> List[Dict[str, Any]]:
        """Get all creators in the auto-shoutout list"""
        async with self.db.acquire() as conn:
            rows = await conn.fetch(
                """SELECT id, platform, platform_user_id, platform_username,
                          custom_trigger, created_at
                   FROM auto_shoutout_creators
                   WHERE community_id = $1
                   ORDER BY created_at DESC""",
                community_id
            )
            return [dict(row) for row in rows]
