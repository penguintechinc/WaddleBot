"""
User Statistics Service
========================
Per-user analytics queries across communities.
Hub is the auth boundary; this service trusts caller-provided user IDs.
"""
from typing import Optional


class UserStatsService:
    def __init__(self, dal, logger):
        self.dal = dal
        self.logger = logger

    async def get_user_self_stats(self, hub_user_id: int) -> dict:
        """
        Cross-community aggregate stats for a user.
        Returns: total_messages, total_watch_hours, active_community_count,
                 communities list (each with: community_id, name, messages, watch_time_hours, last_active)
        Sources: activity_message_events, activity_watch_sessions, communities
        """
        # Total messages
        msg_result = self.dal.executesql(
            """SELECT COUNT(*) FROM activity_message_events
               WHERE hub_user_id = %s""",
            [hub_user_id]
        )
        total_messages = msg_result[0][0] if msg_result else 0

        # Total watch hours
        watch_result = self.dal.executesql(
            """SELECT COALESCE(SUM(duration_seconds), 0) / 3600.0
               FROM activity_watch_sessions
               WHERE hub_user_id = %s""",
            [hub_user_id]
        )
        total_watch_hours = round(float(watch_result[0][0]) if watch_result else 0.0, 2)

        # Per-community breakdown
        comm_result = self.dal.executesql(
            """SELECT
                 c.id AS community_id,
                 c.name,
                 COUNT(DISTINCT ame.id) AS messages,
                 COALESCE(SUM(aws.duration_seconds), 0) / 3600.0 AS watch_time_hours,
                 GREATEST(
                   MAX(ame.created_at),
                   MAX(aws.ended_at)
                 ) AS last_active
               FROM communities c
               LEFT JOIN activity_message_events ame
                 ON ame.community_id = c.id AND ame.hub_user_id = %s
               LEFT JOIN activity_watch_sessions aws
                 ON aws.community_id = c.id AND aws.hub_user_id = %s
               WHERE (ame.id IS NOT NULL OR aws.id IS NOT NULL)
               GROUP BY c.id, c.name
               ORDER BY last_active DESC NULLS LAST""",
            [hub_user_id, hub_user_id]
        )

        communities = []
        for row in comm_result:
            communities.append({
                'community_id': row[0],
                'name': row[1],
                'messages': int(row[2]),
                'watch_time_hours': round(float(row[3]), 2),
                'last_active': row[4].isoformat() if row[4] else None,
            })

        return {
            'hub_user_id': hub_user_id,
            'total_messages': int(total_messages),
            'total_watch_hours': total_watch_hours,
            'active_community_count': len(communities),
            'communities': communities,
        }

    async def get_user_stats_in_community(self, hub_user_id: int, community_id: int) -> dict:
        """
        User stats within a specific community.
        Returns: messages, watch_time_hours, community_role, reputation,
                 activity_timeline (30d daily buckets), first_seen, last_seen
        """
        # Messages in community
        msg_result = self.dal.executesql(
            """SELECT COUNT(*) FROM activity_message_events
               WHERE hub_user_id = %s AND community_id = %s""",
            [hub_user_id, community_id]
        )
        messages = int(msg_result[0][0]) if msg_result else 0

        # Watch time in community
        watch_result = self.dal.executesql(
            """SELECT COALESCE(SUM(duration_seconds), 0) / 3600.0
               FROM activity_watch_sessions
               WHERE hub_user_id = %s AND community_id = %s""",
            [hub_user_id, community_id]
        )
        watch_hours = round(float(watch_result[0][0]) if watch_result else 0.0, 2)

        # Community membership details
        member_result = self.dal.executesql(
            """SELECT cm.role, cm.reputation, cm.joined_at
               FROM community_members cm
               WHERE cm.hub_user_id = %s AND cm.community_id = %s""",
            [hub_user_id, community_id]
        )
        community_role = None
        reputation = 0
        joined_at = None
        if member_result:
            community_role = member_result[0][0]
            reputation = int(member_result[0][1] or 0)
            joined_at = member_result[0][2]

        # 30-day activity timeline (daily message counts)
        timeline_result = self.dal.executesql(
            """SELECT DATE_TRUNC('day', created_at) AS day, COUNT(*) AS messages
               FROM activity_message_events
               WHERE hub_user_id = %s AND community_id = %s
                 AND created_at >= NOW() - INTERVAL '30 days'
               GROUP BY DATE_TRUNC('day', created_at)
               ORDER BY day""",
            [hub_user_id, community_id]
        )
        timeline = [
            {'date': row[0].strftime('%Y-%m-%d'), 'messages': int(row[1])}
            for row in timeline_result
        ]

        # First/last seen
        seen_result = self.dal.executesql(
            """SELECT MIN(created_at), MAX(created_at)
               FROM activity_message_events
               WHERE hub_user_id = %s AND community_id = %s""",
            [hub_user_id, community_id]
        )
        first_seen = seen_result[0][0].isoformat() if seen_result and seen_result[0][0] else None
        last_seen = seen_result[0][1].isoformat() if seen_result and seen_result[0][1] else None

        return {
            'hub_user_id': hub_user_id,
            'community_id': community_id,
            'messages': messages,
            'watch_time_hours': watch_hours,
            'community_role': community_role,
            'reputation': reputation,
            'joined_at': joined_at.isoformat() if joined_at else None,
            'activity_timeline': timeline,
            'first_seen': first_seen,
            'last_seen': last_seen,
        }

    async def get_user_reputation_summary(self, hub_user_id: int) -> dict:
        """
        User reputation summary: global score + per-community breakdown + 90d trend.
        Uses platform_user_reputation view and community_members.reputation.
        NOTE: platform_user_reputation view joins with cm.user_id = hu.id::text cast.
        """
        # Global reputation from view (user_id is text in view, hub_user_id is int)
        global_result = self.dal.executesql(
            """SELECT platform_reputation
               FROM platform_user_reputation
               WHERE user_id = %s::text""",
            [hub_user_id]
        )
        global_reputation = int(global_result[0][0]) if global_result else None

        # Per-community reputation
        comm_rep_result = self.dal.executesql(
            """SELECT c.id, c.name, cm.reputation, cm.role
               FROM community_members cm
               JOIN communities c ON c.id = cm.community_id
               WHERE cm.hub_user_id = %s
               ORDER BY cm.reputation DESC""",
            [hub_user_id]
        )
        community_reputations = [
            {
                'community_id': row[0],
                'community_name': row[1],
                'reputation': int(row[2] or 0),
                'role': row[3],
            }
            for row in comm_rep_result
        ]

        # 90-day reputation trend from reputation_events (if table exists)
        try:
            trend_result = self.dal.executesql(
                """SELECT DATE_TRUNC('week', created_at) AS week,
                          SUM(points) AS points_delta
                   FROM reputation_events
                   WHERE user_id = %s
                     AND created_at >= NOW() - INTERVAL '90 days'
                   GROUP BY DATE_TRUNC('week', created_at)
                   ORDER BY week""",
                [hub_user_id]
            )
            trend = [
                {'week': row[0].strftime('%Y-%m-%d'), 'points_delta': int(row[1])}
                for row in trend_result
            ]
        except Exception:
            trend = []

        return {
            'hub_user_id': hub_user_id,
            'global_reputation': global_reputation,
            'community_reputations': community_reputations,
            'reputation_trend_90d': trend,
        }
