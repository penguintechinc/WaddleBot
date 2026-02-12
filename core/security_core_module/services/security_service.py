"""
Security Service - Main orchestrator for security features
"""
from typing import Optional, Dict, List
from datetime import datetime


class SecurityService:
    """Main security service coordinating all security features."""

    def __init__(self, dal, logger):
        self.dal = dal
        self.logger = logger

    async def get_config(self, community_id: int) -> Dict:
        """Get security configuration for community."""
        try:
            result = self.dal.executesql(
                """SELECT spam_detection_enabled, spam_message_threshold,
                          spam_interval_seconds, spam_duplicate_threshold,
                          content_filter_enabled, blocked_words, blocked_patterns,
                          filter_action, warning_enabled, warning_threshold_timeout,
                          warning_threshold_ban, warning_decay_days,
                          rate_limit_enabled, rate_limit_commands_per_minute,
                          rate_limit_messages_per_minute, auto_timeout_enabled,
                          timeout_base_duration_minutes, cross_platform_sync,
                          reputation_integration_enabled, use_default_profanity_list,
                          created_at, updated_at
                   FROM security_config
                   WHERE community_id = %s""",
                [community_id]
            )

            if not result:
                # Return defaults
                from config import Config
                return {
                    'community_id': community_id,
                    'spam_detection_enabled': True,
                    'spam_message_threshold': Config.DEFAULT_SPAM_MESSAGE_THRESHOLD,
                    'spam_interval_seconds': Config.DEFAULT_SPAM_INTERVAL_SECONDS,
                    'spam_duplicate_threshold': Config.DEFAULT_SPAM_DUPLICATE_THRESHOLD,
                    'content_filter_enabled': True,
                    'blocked_words': [],
                    'blocked_patterns': [],
                    'filter_action': 'delete',
                    'warning_enabled': True,
                    'warning_threshold_timeout': Config.DEFAULT_WARNING_THRESHOLD_TIMEOUT,
                    'warning_threshold_ban': Config.DEFAULT_WARNING_THRESHOLD_BAN,
                    'warning_decay_days': Config.DEFAULT_WARNING_DECAY_DAYS,
                    'rate_limit_enabled': True,
                    'rate_limit_commands_per_minute': 10,
                    'rate_limit_messages_per_minute': 30,
                    'auto_timeout_enabled': True,
                    'timeout_base_duration_minutes': 10,
                    'cross_platform_sync': False,
                    'reputation_integration_enabled': True,
                    'use_default_profanity_list': Config.DEFAULT_USE_BUILTIN_PROFANITY,
                }

            row = result[0]
            return {
                'community_id': community_id,
                'spam_detection_enabled': row[0],
                'spam_message_threshold': row[1],
                'spam_interval_seconds': row[2],
                'spam_duplicate_threshold': row[3],
                'content_filter_enabled': row[4],
                'blocked_words': row[5] or [],
                'blocked_patterns': row[6] or [],
                'filter_action': row[7],
                'warning_enabled': row[8],
                'warning_threshold_timeout': row[9],
                'warning_threshold_ban': row[10],
                'warning_decay_days': row[11],
                'rate_limit_enabled': row[12],
                'rate_limit_commands_per_minute': row[13],
                'rate_limit_messages_per_minute': row[14],
                'auto_timeout_enabled': row[15],
                'timeout_base_duration_minutes': row[16],
                'cross_platform_sync': row[17],
                'reputation_integration_enabled': row[18],
                'use_default_profanity_list': row[19] if row[19] is not None else False,
                'created_at': row[20].isoformat() + 'Z' if row[20] else None,
                'updated_at': row[21].isoformat() + 'Z' if row[21] else None
            }

        except Exception as e:
            self.logger.error(f"Failed to get security config: {e}")
            raise

    async def update_config(self, community_id: int, updates: Dict) -> Dict:
        """Update security configuration."""
        try:
            # Get existing config
            config = await self.get_config(community_id)

            # Check if config exists
            exists = self.dal.executesql(
                "SELECT id FROM security_config WHERE community_id = %s",
                [community_id]
            )

            if not exists:
                # Insert new config
                self.dal.executesql(
                    """INSERT INTO security_config
                       (community_id, spam_detection_enabled, spam_message_threshold,
                        spam_interval_seconds, spam_duplicate_threshold,
                        content_filter_enabled, blocked_words, blocked_patterns,
                        filter_action, warning_enabled, warning_threshold_timeout,
                        warning_threshold_ban, warning_decay_days, rate_limit_enabled,
                        rate_limit_commands_per_minute, rate_limit_messages_per_minute,
                        auto_timeout_enabled, timeout_base_duration_minutes,
                        cross_platform_sync, reputation_integration_enabled,
                        use_default_profanity_list)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                               %s, %s, %s, %s, %s, %s, %s)""",
                    [
                        community_id,
                        updates.get('spam_detection_enabled', config['spam_detection_enabled']),
                        updates.get('spam_message_threshold', config['spam_message_threshold']),
                        updates.get('spam_interval_seconds', config['spam_interval_seconds']),
                        updates.get('spam_duplicate_threshold', config['spam_duplicate_threshold']),
                        updates.get('content_filter_enabled', config['content_filter_enabled']),
                        updates.get('blocked_words', config['blocked_words']),
                        updates.get('blocked_patterns', config['blocked_patterns']),
                        updates.get('filter_action', config['filter_action']),
                        updates.get('warning_enabled', config['warning_enabled']),
                        updates.get('warning_threshold_timeout', config['warning_threshold_timeout']),
                        updates.get('warning_threshold_ban', config['warning_threshold_ban']),
                        updates.get('warning_decay_days', config['warning_decay_days']),
                        updates.get('rate_limit_enabled', config['rate_limit_enabled']),
                        updates.get('rate_limit_commands_per_minute', config['rate_limit_commands_per_minute']),
                        updates.get('rate_limit_messages_per_minute', config['rate_limit_messages_per_minute']),
                        updates.get('auto_timeout_enabled', config['auto_timeout_enabled']),
                        updates.get('timeout_base_duration_minutes', config['timeout_base_duration_minutes']),
                        updates.get('cross_platform_sync', config['cross_platform_sync']),
                        updates.get('reputation_integration_enabled', config['reputation_integration_enabled']),
                        updates.get('use_default_profanity_list', config.get('use_default_profanity_list', False))
                    ]
                )
            else:
                # Update existing config
                set_clauses = []
                params = []
                for key, value in updates.items():
                    set_clauses.append(f"{key} = %s")
                    params.append(value)

                if set_clauses:
                    set_clauses.append("updated_at = NOW()")
                    params.append(community_id)
                    self.dal.executesql(
                        f"UPDATE security_config SET {', '.join(set_clauses)} WHERE community_id = %s",
                        params
                    )

            self.dal.commit()

            self.logger.audit(
                "Security config updated",
                community_id=community_id,
                action="update_security_config",
                result="SUCCESS"
            )

            return await self.get_config(community_id)

        except Exception as e:
            self.logger.error(f"Failed to update security config: {e}")
            raise

    async def get_moderation_log(
        self,
        community_id: int,
        page: int = 1,
        limit: int = 50
    ) -> Dict:
        """Get moderation actions log."""
        try:
            offset = (page - 1) * limit

            result = self.dal.executesql(
                """SELECT id, platform, platform_user_id, platform_username,
                          action_type, action_reason, moderator_id, synced_to_platforms,
                          reputation_impact, created_at
                   FROM security_moderation_actions
                   WHERE community_id = %s
                   ORDER BY created_at DESC
                   LIMIT %s OFFSET %s""",
                [community_id, limit, offset]
            )

            actions = []
            if result:
                for row in result:
                    actions.append({
                        'id': row[0],
                        'platform': row[1],
                        'platform_user_id': row[2],
                        'platform_username': row[3],
                        'action_type': row[4],
                        'action_reason': row[5],
                        'moderator_id': row[6],
                        'synced_to_platforms': row[7] or [],
                        'reputation_impact': float(row[8]) if row[8] else None,
                        'created_at': row[9].isoformat() + 'Z' if row[9] else None
                    })

            return {
                'actions': actions,
                'page': page,
                'limit': limit,
                'total': len(actions)
            }

        except Exception as e:
            self.logger.error(f"Failed to get moderation log: {e}")
            raise

    async def sync_moderation_action(
        self,
        community_id: int,
        platform: str,
        platform_user_id: str,
        action_type: str,
        action_reason: Optional[str] = None,
        moderator_id: Optional[int] = None,
        sync_to_platforms: Optional[List[str]] = None
    ) -> Dict:
        """
        Sync moderation action across platforms.

        This logs the action and can trigger cross-platform enforcement.
        """
        try:
            sync_to_platforms = sync_to_platforms or []

            # Get hub_user_id
            hub_user_id = await self._get_hub_user_id(platform, platform_user_id)

            # Calculate reputation impact
            from config import Config
            reputation_impact = Config.REPUTATION_IMPACT.get(action_type, 0.0)

            # Log moderation action
            self.dal.executesql(
                """INSERT INTO security_moderation_actions
                   (community_id, hub_user_id, platform, platform_user_id,
                    action_type, action_reason, moderator_id, synced_to_platforms,
                    reputation_impact)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                [community_id, hub_user_id, platform, platform_user_id,
                 action_type, action_reason, moderator_id, sync_to_platforms,
                 reputation_impact]
            )
            self.dal.commit()

            # Apply reputation impact if enabled
            config = await self.get_config(community_id)
            if config['reputation_integration_enabled'] and reputation_impact != 0:
                await self._apply_reputation_impact(
                    community_id, hub_user_id, platform,
                    platform_user_id, reputation_impact, action_type
                )

            self.logger.audit(
                "Moderation action synced",
                community_id=community_id,
                platform=platform,
                platform_user_id=platform_user_id,
                action_type=action_type,
                moderator_id=moderator_id,
                action="sync_moderation_action",
                result="SUCCESS"
            )

            return {
                'synced': True,
                'action_type': action_type,
                'synced_to_platforms': sync_to_platforms,
                'reputation_impact': reputation_impact
            }

        except Exception as e:
            self.logger.error(f"Failed to sync moderation action: {e}")
            raise

    async def _get_hub_user_id(self, platform: str, platform_user_id: str) -> Optional[int]:
        """Get hub_user_id from platform identity."""
        try:
            result = self.dal.executesql(
                """SELECT hub_user_id FROM hub_user_identities
                   WHERE platform = %s AND platform_user_id = %s""",
                [platform, platform_user_id]
            )
            return result[0][0] if result else None
        except Exception:
            return None

    async def _apply_reputation_impact(
        self,
        community_id: int,
        hub_user_id: Optional[int],
        platform: str,
        platform_user_id: str,
        impact: float,
        reason: str
    ):
        """Apply reputation impact for moderation action."""
        try:
            # This would call the reputation module API
            # For now, just log it
            self.logger.audit(
                "Reputation impact applied",
                community_id=community_id,
                hub_user_id=hub_user_id,
                platform=platform,
                platform_user_id=platform_user_id,
                impact=impact,
                reason=reason,
                action="apply_reputation_impact",
                result="SUCCESS"
            )
        except Exception as e:
            self.logger.error(f"Failed to apply reputation impact: {e}")
