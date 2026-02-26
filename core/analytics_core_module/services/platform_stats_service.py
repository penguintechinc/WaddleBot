"""
Platform Statistics Service
=============================
Platform-wide aggregate analytics with no individual PII.
All queries return aggregate data only (counts, averages, histograms).
"""


class PlatformStatsService:
    def __init__(self, dal, logger):
        self.dal = dal
        self.logger = logger

    async def get_platform_summary(self) -> dict:
        """Platform-level summary: total users, active 30d, total communities, avg reputation."""
        result = self.dal.executesql("""
            SELECT
              (SELECT COUNT(*) FROM hub_users WHERE is_active = TRUE) AS total_users,
              (SELECT COUNT(*) FROM hub_users WHERE is_active = TRUE
                 AND last_login >= NOW() - INTERVAL '30 days') AS active_users_30d,
              (SELECT COUNT(*) FROM communities WHERE is_active = TRUE AND is_global = FALSE) AS total_communities,
              (SELECT ROUND(AVG(platform_reputation)::numeric, 1) FROM platform_user_reputation) AS avg_reputation
        """)
        row = result[0] if result else [0, 0, 0, 0]
        return {
            'total_users': int(row[0]),
            'active_users_30d': int(row[1]),
            'total_communities': int(row[2]),
            'avg_platform_reputation': round(float(row[3] or 0), 1),
        }

    async def get_reputation_distribution(self) -> dict:
        """Histogram of reputation scores in 50-point buckets + stats."""
        stats_result = self.dal.executesql("""
            SELECT
              COUNT(*) AS total,
              ROUND(AVG(platform_reputation)::numeric, 1) AS avg,
              PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY platform_reputation) AS median,
              MIN(platform_reputation) AS min,
              MAX(platform_reputation) AS max
            FROM platform_user_reputation
        """)
        stats_row = stats_result[0] if stats_result else [0, 0, 0, 0, 0]

        bucket_result = self.dal.executesql("""
            SELECT
              FLOOR(platform_reputation / 50) * 50 AS bucket_min,
              FLOOR(platform_reputation / 50) * 50 + 49 AS bucket_max,
              COUNT(*) AS count
            FROM platform_user_reputation
            GROUP BY FLOOR(platform_reputation / 50)
            ORDER BY bucket_min
        """)

        return {
            'stats': {
                'total': int(stats_row[0]),
                'avg': float(stats_row[1] or 0),
                'median': float(stats_row[2] or 0),
                'min': int(stats_row[3] or 0),
                'max': int(stats_row[4] or 0),
            },
            'histogram': [
                {'range': f"{int(row[0])}-{int(row[1])}", 'count': int(row[2])}
                for row in bucket_result
            ],
        }

    async def get_growth_trends(self, period: str = '90d') -> dict:
        """New users and communities per time bucket."""
        period_map = {
            '30d': ('30 days', 'day'),
            '90d': ('90 days', 'week'),
            '1y': ('1 year', 'month'),
        }
        interval, trunc = period_map.get(period, ('90 days', 'week'))

        users_result = self.dal.executesql(
            """SELECT DATE_TRUNC(%s, created_at) AS period, COUNT(*) AS count
               FROM hub_users
               WHERE created_at >= NOW() - INTERVAL %s
               GROUP BY DATE_TRUNC(%s, created_at)
               ORDER BY period""",
            [trunc, interval, trunc]
        )
        comms_result = self.dal.executesql(
            """SELECT DATE_TRUNC(%s, created_at) AS period, COUNT(*) AS count
               FROM communities
               WHERE created_at >= NOW() - INTERVAL %s
                 AND is_global = FALSE
               GROUP BY DATE_TRUNC(%s, created_at)
               ORDER BY period""",
            [trunc, interval, trunc]
        )

        return {
            'period': period,
            'truncation': trunc,
            'users': [{'period': row[0].isoformat(), 'count': int(row[1])} for row in users_result],
            'communities': [{'period': row[0].isoformat(), 'count': int(row[1])} for row in comms_result],
        }

    async def get_activity_breakdown(self) -> dict:
        """Active user segments by last_login recency."""
        result = self.dal.executesql("""
            SELECT
              COUNT(*) FILTER (WHERE last_login >= NOW() - INTERVAL '24 hours') AS active_24h,
              COUNT(*) FILTER (WHERE last_login >= NOW() - INTERVAL '7 days'
                                 AND last_login < NOW() - INTERVAL '24 hours') AS active_7d,
              COUNT(*) FILTER (WHERE last_login >= NOW() - INTERVAL '30 days'
                                 AND last_login < NOW() - INTERVAL '7 days') AS active_30d,
              COUNT(*) FILTER (WHERE last_login >= NOW() - INTERVAL '90 days'
                                 AND last_login < NOW() - INTERVAL '30 days') AS active_90d,
              COUNT(*) FILTER (WHERE last_login < NOW() - INTERVAL '90 days'
                                 OR last_login IS NULL) AS inactive,
              COUNT(*) AS total
            FROM hub_users
            WHERE is_active = TRUE
        """)
        row = result[0] if result else [0, 0, 0, 0, 0, 0]
        return {
            'segments': [
                {'label': 'Active (24h)', 'key': 'active_24h', 'count': int(row[0])},
                {'label': 'Active (7d)', 'key': 'active_7d', 'count': int(row[1])},
                {'label': 'Active (30d)', 'key': 'active_30d', 'count': int(row[2])},
                {'label': 'Active (90d)', 'key': 'active_90d', 'count': int(row[3])},
                {'label': 'Inactive', 'key': 'inactive', 'count': int(row[4])},
            ],
            'total': int(row[5]),
        }

    async def get_community_health_summaries(self, limit: int = 50) -> dict:
        """Per-community aggregate health data. No individual user PII."""
        result = self.dal.executesql(
            """SELECT
                 c.id,
                 c.name,
                 COUNT(cm.hub_user_id) AS member_count,
                 COALESCE(ach.health_score, 0) AS health_score,
                 COALESCE(abs2.grade, 'N/A') AS bot_score_grade
               FROM communities c
               LEFT JOIN community_members cm ON cm.community_id = c.id
               LEFT JOIN analytics_community_health ach ON ach.community_id = c.id
               LEFT JOIN analytics_bot_scores abs2 ON abs2.community_id = c.id
               WHERE c.is_active = TRUE AND c.is_global = FALSE
               GROUP BY c.id, c.name, ach.health_score, abs2.grade
               ORDER BY member_count DESC
               LIMIT %s""",
            [limit]
        )
        return {
            'communities': [
                {
                    'community_id': row[0],
                    'name': row[1],
                    'member_count': int(row[2]),
                    'health_score': float(row[3] or 0),
                    'bot_score_grade': row[4] or 'N/A',
                }
                for row in result
            ],
            'total': len(result),
        }
