"""Reputation-driven auto-moderation enforcement engine."""
import logging
from datetime import datetime, timezone
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class EnforcementService:
    """Enforces access policies on game/voice servers based on reputation scores."""

    def __init__(self, dal, config, rcon_service, encryption_service):
        self.dal = dal
        self.config = config
        self.rcon = rcon_service
        self.encryption = encryption_service

    async def get_policy(self, server_config_id: int) -> Optional[dict]:
        rows = self.dal.executesql(
            "SELECT id, server_config_id, community_id, require_community_member, "
            "auto_kick_enabled, auto_kick_threshold, auto_ban_enabled, auto_ban_threshold, "
            "auto_ban_duration_hours, min_reputation_to_join, sync_interval_minutes, "
            "notify_on_action, exempt_roles, sync_to_community, last_enforced_at "
            "FROM server_access_policies WHERE server_config_id = $1",
            placeholders=[server_config_id],
        )
        if not rows:
            return None
        r = rows[0]
        return {
            'id': r[0], 'server_config_id': r[1], 'community_id': r[2],
            'require_community_member': r[3], 'auto_kick_enabled': r[4],
            'auto_kick_threshold': r[5], 'auto_ban_enabled': r[6],
            'auto_ban_threshold': r[7], 'auto_ban_duration_hours': r[8],
            'min_reputation_to_join': r[9], 'sync_interval_minutes': r[10],
            'notify_on_action': r[11], 'exempt_roles': r[12] or [],
            'sync_to_community': r[13], 'last_enforced_at': r[14],
        }

    async def upsert_policy(self, server_config_id: int, community_id: int, data: dict) -> dict:
        self.dal.executesql(
            """INSERT INTO server_access_policies
               (server_config_id, community_id, require_community_member,
                auto_kick_enabled, auto_kick_threshold, auto_ban_enabled,
                auto_ban_threshold, auto_ban_duration_hours, min_reputation_to_join,
                sync_interval_minutes, notify_on_action, exempt_roles, sync_to_community)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
               ON CONFLICT (server_config_id) DO UPDATE SET
                 require_community_member = EXCLUDED.require_community_member,
                 auto_kick_enabled = EXCLUDED.auto_kick_enabled,
                 auto_kick_threshold = EXCLUDED.auto_kick_threshold,
                 auto_ban_enabled = EXCLUDED.auto_ban_enabled,
                 auto_ban_threshold = EXCLUDED.auto_ban_threshold,
                 auto_ban_duration_hours = EXCLUDED.auto_ban_duration_hours,
                 min_reputation_to_join = EXCLUDED.min_reputation_to_join,
                 sync_interval_minutes = EXCLUDED.sync_interval_minutes,
                 notify_on_action = EXCLUDED.notify_on_action,
                 exempt_roles = EXCLUDED.exempt_roles,
                 sync_to_community = EXCLUDED.sync_to_community,
                 updated_at = NOW()""",
            placeholders=[
                server_config_id, community_id,
                data.get('require_community_member', False),
                data.get('auto_kick_enabled', False),
                data.get('auto_kick_threshold', 450),
                data.get('auto_ban_enabled', False),
                data.get('auto_ban_threshold', 350),
                data.get('auto_ban_duration_hours'),
                data.get('min_reputation_to_join'),
                data.get('sync_interval_minutes', 5),
                data.get('notify_on_action', True),
                data.get('exempt_roles', []),
                data.get('sync_to_community', False),
            ],
        )
        self.dal.commit()
        return await self.get_policy(server_config_id)

    def _log_action(self, server_config_id: int, target_player: str, action: str, reason: str, reputation_score: int = None):
        self.dal.executesql(
            "INSERT INTO server_access_log (server_config_id, target_player, action, reason, reputation_score) "
            "VALUES ($1, $2, $3, $4, $5)",
            placeholders=[server_config_id, target_player, action, reason, reputation_score],
        )
        self.dal.commit()

    async def get_access_log(self, server_config_id: int, limit: int = 50, offset: int = 0) -> list:
        rows = self.dal.executesql(
            "SELECT id, target_player, action, reason, reputation_score, created_at "
            "FROM server_access_log WHERE server_config_id = $1 "
            "ORDER BY created_at DESC LIMIT $2 OFFSET $3",
            placeholders=[server_config_id, limit, offset],
        )
        return [
            {
                'id': r[0], 'target_player': r[1], 'action': r[2],
                'reason': r[3], 'reputation_score': r[4],
                'created_at': r[5].isoformat() if r[5] else None,
            }
            for r in (rows or [])
        ]

    async def enforce_server(self, server_config_id: int) -> dict:
        """Run one enforcement cycle for a server."""
        policy = await self.get_policy(server_config_id)
        if not policy:
            return {'enforced': False, 'reason': 'No access policy configured'}

        # Update last_enforced_at
        self.dal.executesql(
            "UPDATE server_access_policies SET last_enforced_at = NOW() WHERE server_config_id = $1",
            placeholders=[server_config_id],
        )
        self.dal.commit()

        actions_taken = []
        logger.info("Enforcement cycle started for server_config_id=%s", server_config_id)

        # Stub: actual enforcement requires player-to-member mapping
        # which depends on game-specific identity resolution
        return {
            'enforced': True,
            'server_config_id': server_config_id,
            'actions_taken': actions_taken,
        }

    async def enforce_all(self) -> dict:
        """Cron endpoint: enforce all active policies where interval has elapsed."""
        rows = self.dal.executesql(
            """SELECT sap.server_config_id
               FROM server_access_policies sap
               JOIN server_status_configs ssc ON ssc.id = sap.server_config_id
               WHERE ssc.is_active = TRUE AND ssc.deleted_at IS NULL
                 AND (sap.last_enforced_at IS NULL
                      OR sap.last_enforced_at < NOW() - (sap.sync_interval_minutes || ' minutes')::INTERVAL)"""
        )
        results = []
        for row in (rows or []):
            result = await self.enforce_server(row[0])
            results.append(result)
        return {'enforced_count': len(results), 'results': results}
