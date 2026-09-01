"""
Status Service for Server Status Interaction Module

Manages server status configs, polling, and event tracking.
"""
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class StatusService:
    """Manages server status configurations and event history."""

    def __init__(self, dal, config, provider_service):
        self.dal = dal
        self.config = config
        self.provider_service = provider_service

    async def check_status(
        self, community_id: int, game_name: str
    ) -> dict:
        """Live-check status for a specific game in a community.

        Args:
            community_id: The community ID.
            game_name: The game name to check.

        Returns:
            Status result dict or error dict.
        """
        rows = self.dal.executesql(
            "SELECT id, status_api_type, status_url "
            "FROM server_status_configs "
            "WHERE community_id=$1 AND game_name=$2 AND is_active=TRUE",
            placeholders=[community_id, game_name],
        )

        if not rows:
            return {
                'error': True,
                'message': (
                    f"No active config for game '{game_name}' "
                    f"in community {community_id}"
                ),
            }

        row = rows[0]
        config_id, api_type, status_url = row[0], row[1], row[2]

        result = await self.provider_service.check(
            api_type=api_type, url=status_url
        )
        result['game_name'] = game_name
        result['config_id'] = config_id
        return result

    async def poll_all(self) -> dict:
        """Poll all active server status configs across all communities.

        Compares current status to last event and inserts new events
        when state changes are detected.

        Returns:
            Summary dict with polled count and changes count.
        """
        rows = self.dal.executesql(
            "SELECT id, community_id, game_name, status_api_type, status_url "
            "FROM server_status_configs "
            "WHERE is_active=TRUE"
        )

        if not rows:
            return {'polled': 0, 'changes': 0}

        polled = 0
        changes = 0

        for row in rows:
            config_id = row[0]
            game_name = row[2]
            api_type = row[3]
            status_url = row[4]

            try:
                result = await self.provider_service.check(
                    api_type=api_type, url=status_url
                )
                polled += 1

                # Get last event for this config
                last_events = self.dal.executesql(
                    "SELECT event_type FROM server_status_events "
                    "WHERE config_id=$1 "
                    "ORDER BY created_at DESC LIMIT 1",
                    placeholders=[config_id],
                )

                last_status = last_events[0][0] if last_events else None
                current_status = result['status']

                if current_status != last_status:
                    self.dal.executesql(
                        "INSERT INTO server_status_events "
                        "(config_id, event_type, details, created_at) "
                        "VALUES ($1, $2, $3, $4)",
                        placeholders=[
                            config_id,
                            current_status,
                            result.get('details', ''),
                            datetime.now(timezone.utc),
                        ],
                    )
                    self.dal.commit()
                    changes += 1
                    logger.info(
                        "Status change for %s: %s -> %s",
                        game_name,
                        last_status,
                        current_status,
                    )
            except Exception as exc:
                logger.error(
                    "Failed to poll config %s (%s): %s",
                    config_id,
                    game_name,
                    exc,
                )

        return {'polled': polled, 'changes': changes}

    async def get_current_status(self, community_id: int) -> list:
        """Get current status for all games in a community.

        Args:
            community_id: The community ID.

        Returns:
            List of status dicts per game config.
        """
        rows = self.dal.executesql(
            "SELECT c.game_name, c.status_api_type, c.is_active, "
            "e.event_type, e.created_at "
            "FROM server_status_configs c "
            "LEFT JOIN LATERAL ("
            "  SELECT event_type, created_at "
            "  FROM server_status_events "
            "  WHERE config_id = c.id "
            "  ORDER BY created_at DESC LIMIT 1"
            ") e ON TRUE "
            "WHERE c.community_id=$1",
            placeholders=[community_id],
        )

        results = []
        for row in rows:
            results.append({
                'game_name': row[0],
                'status_api_type': row[1],
                'is_active': row[2],
                'last_event_type': row[3],
                'last_event_at': (
                    row[4].isoformat() if row[4] else None
                ),
            })
        return results

    async def add_config(
        self,
        community_id: int,
        game_name: str,
        status_api_type: str,
        status_url: str = None,
        alert_on_outage: bool = True,
        poll_interval_minutes: int = None,
    ) -> dict:
        """Add or update a server status config for a community.

        Args:
            community_id: The community ID.
            game_name: Game name identifier.
            status_api_type: One of 'steam', 'riot', 'custom_url'.
            status_url: URL for custom_url checks.
            alert_on_outage: Whether to alert on outages.
            poll_interval_minutes: Polling interval override.

        Returns:
            Config dict for the upserted row.
        """
        if poll_interval_minutes is None:
            poll_interval_minutes = self.config.DEFAULT_POLL_INTERVAL_MINUTES

        self.dal.executesql(
            "INSERT INTO server_status_configs "
            "(community_id, game_name, status_api_type, status_url, "
            "alert_on_outage, poll_interval_minutes, is_active) "
            "VALUES ($1, $2, $3, $4, $5, $6, TRUE) "
            "ON CONFLICT (community_id, game_name) DO UPDATE SET "
            "status_api_type=EXCLUDED.status_api_type, "
            "status_url=EXCLUDED.status_url, "
            "alert_on_outage=EXCLUDED.alert_on_outage, "
            "poll_interval_minutes=EXCLUDED.poll_interval_minutes, "
            "is_active=TRUE",
            placeholders=[
                community_id,
                game_name,
                status_api_type,
                status_url,
                alert_on_outage,
                poll_interval_minutes,
            ],
        )
        self.dal.commit()

        return {
            'community_id': community_id,
            'game_name': game_name,
            'status_api_type': status_api_type,
            'status_url': status_url,
            'alert_on_outage': alert_on_outage,
            'poll_interval_minutes': poll_interval_minutes,
            'is_active': True,
        }

    async def remove_config(
        self, community_id: int, game_name: str
    ) -> bool:
        """Soft-delete a server status config.

        Args:
            community_id: The community ID.
            game_name: Game name to deactivate.

        Returns:
            True if a row was updated, False otherwise.
        """
        result = self.dal.executesql(
            "UPDATE server_status_configs "
            "SET is_active=FALSE "
            "WHERE community_id=$1 AND game_name=$2 AND is_active=TRUE "
            "RETURNING id",
            placeholders=[community_id, game_name],
        )
        self.dal.commit()
        return bool(result)

    async def get_recent_events(
        self, community_id: int, limit: int = 20
    ) -> list:
        """Get recent status events for a community.

        Args:
            community_id: The community ID.
            limit: Maximum number of events to return.

        Returns:
            List of event dicts ordered by most recent first.
        """
        rows = self.dal.executesql(
            "SELECT e.id, c.game_name, e.event_type, e.details, "
            "e.created_at "
            "FROM server_status_events e "
            "JOIN server_status_configs c ON c.id = e.config_id "
            "WHERE c.community_id=$1 "
            "ORDER BY e.created_at DESC LIMIT $2",
            placeholders=[community_id, limit],
        )

        results = []
        for row in rows:
            results.append({
                'id': row[0],
                'game_name': row[1],
                'event_type': row[2],
                'details': row[3],
                'created_at': (
                    row[4].isoformat() if row[4] else None
                ),
            })
        return results
