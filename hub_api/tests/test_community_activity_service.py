"""`services/community_activity.py` -- direct unit tests for functions not fully.

exercised through `test_community_activity.py`'s blueprint-level tests.

`period=alltime`'s `date_filter` is an empty string (`_DATE_FILTERS`), so
the leaderboard/period-stats/rank queries need no Postgres-only `INTERVAL`
syntax at all and run correctly against sqlite:memory -- only the
`weekly`/`monthly` branches (already documented skips) and `_update_daily_
stats`'s `ON CONFLICT` need Postgres. This file seeds real
`activity_stats_daily`/`community_leaderboard_config` rows and calls the
service functions directly to cover the "populated" branches the
blueprint's empty-state tests don't reach.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from services.community_activity import (
    _find_hub_user_id,
    _leaderboard_config,
    _period_stats,
    _user_rank,
    get_leaderboard_config,
    get_message_leaderboard,
    get_watch_time_leaderboard,
)


def _seed_stats(
    dal: Any,
    community_id: int,
    *,
    hub_user_id: int | None,
    username: str,
    watch_seconds: int,
    messages: int,
) -> None:
    dal.activity_stats_daily.insert(
        community_id=community_id,
        hub_user_id=hub_user_id,
        platform_user_id=str(hub_user_id) if hub_user_id else "anon-1",
        platform_username=username,
        stat_date=date.today(),
        watch_time_seconds=watch_seconds,
        message_count=messages,
    )
    dal.commit()


class TestLeaderboardConfigExistingRow:
    def test_leaderboard_config_reads_existing_row(self, community_db: Any) -> None:
        dal, community_id = community_db
        dal.community_leaderboard_config.insert(
            community_id=community_id,
            min_watch_time_minutes=1,
            min_message_count=1,
            display_limit=5,
        )
        dal.commit()

        cfg = _leaderboard_config(dal, community_id)
        assert cfg == {"min_watch_time_minutes": 1, "min_message_count": 1, "display_limit": 5}

    def test_get_leaderboard_config_reads_existing_row(self, community_db: Any) -> None:
        dal, community_id = community_db
        dal.community_leaderboard_config.insert(
            community_id=community_id,
            enabled_platforms=["twitch"],
            watch_time_enabled=False,
            messages_enabled=False,
            public_leaderboard=False,
            min_watch_time_minutes=2,
            min_message_count=3,
            display_limit=7,
        )
        dal.commit()

        response = get_leaderboard_config(dal, community_id)
        assert response.config.enabled_platforms == ["twitch"]
        assert response.config.watch_time_enabled is False
        assert response.config.display_limit == 7


class TestLeaderboardsWithData:
    def test_watch_time_leaderboard_ranks_by_total_descending(self, community_db: Any) -> None:
        dal, community_id = community_db
        dal.community_leaderboard_config.insert(
            community_id=community_id, min_watch_time_minutes=1, display_limit=25
        )
        dal.commit()
        _seed_stats(
            dal, community_id, hub_user_id=1, username="alice", watch_seconds=600, messages=0
        )
        _seed_stats(
            dal, community_id, hub_user_id=2, username="bob", watch_seconds=1200, messages=0
        )
        _seed_stats(
            dal,
            community_id,
            hub_user_id=None,
            username="anon-viewer",
            watch_seconds=300,
            messages=0,
        )

        result = get_watch_time_leaderboard(dal, community_id, period="alltime", limit=25, offset=0)
        assert result.success is True
        assert [e.username for e in result.leaderboard] == ["bob", "alice", "anon-viewer"]
        assert result.leaderboard[0].rank == 1
        assert result.leaderboard[0].value == 1200
        assert result.leaderboard[0].value_formatted == "20m"
        assert result.leaderboard[2].user_id is None  # unlinked platform-only viewer
        assert result.pagination.total == 3
        assert result.pagination.has_more is False

    def test_watch_time_leaderboard_respects_min_threshold(self, community_db: Any) -> None:
        dal, community_id = community_db
        dal.community_leaderboard_config.insert(
            community_id=community_id, min_watch_time_minutes=100, display_limit=25
        )
        dal.commit()
        _seed_stats(
            dal, community_id, hub_user_id=1, username="alice", watch_seconds=60, messages=0
        )

        result = get_watch_time_leaderboard(dal, community_id, period="alltime", limit=25, offset=0)
        assert result.leaderboard == []
        assert result.pagination.total == 0

    def test_message_leaderboard_ranks_by_count_descending(self, community_db: Any) -> None:
        dal, community_id = community_db
        dal.community_leaderboard_config.insert(
            community_id=community_id, min_message_count=1, display_limit=25
        )
        dal.commit()
        _seed_stats(dal, community_id, hub_user_id=1, username="alice", watch_seconds=0, messages=5)
        _seed_stats(dal, community_id, hub_user_id=2, username="bob", watch_seconds=0, messages=15)

        result = get_message_leaderboard(dal, community_id, period="alltime", limit=25, offset=0)
        assert [e.username for e in result.leaderboard] == ["bob", "alice"]
        assert result.leaderboard[0].value == 15
        assert result.pagination.total == 2

    def test_watch_time_leaderboard_pagination_has_more(self, community_db: Any) -> None:
        dal, community_id = community_db
        dal.community_leaderboard_config.insert(
            community_id=community_id, min_watch_time_minutes=1, display_limit=25
        )
        dal.commit()
        for i in range(3):
            _seed_stats(
                dal,
                community_id,
                hub_user_id=i + 1,
                username=f"user{i}",
                watch_seconds=100 * (i + 1),
                messages=0,
            )

        result = get_watch_time_leaderboard(dal, community_id, period="alltime", limit=2, offset=0)
        assert len(result.leaderboard) == 2
        assert result.pagination.total == 3
        assert result.pagination.has_more is True


class TestPeriodStatsAndRankDirect:
    """`_period_stats`/`_user_rank` at `date_filter=""` (alltime) need no.

    Postgres-only `INTERVAL` syntax -- called directly since `get_my_
    activity_stats` always computes weekly/monthly too (documented skip).
    """

    def test_period_stats_alltime_with_data(self, community_db: Any) -> None:
        dal, community_id = community_db
        _seed_stats(
            dal, community_id, hub_user_id=1, username="alice", watch_seconds=125, messages=4
        )

        stats = _period_stats(dal, community_id, 1, "")
        assert stats.watch_time_seconds == 125
        assert stats.watch_time_formatted == "2m"
        assert stats.message_count == 4

    def test_period_stats_alltime_no_data_defaults_to_zero(self, community_db: Any) -> None:
        dal, community_id = community_db
        stats = _period_stats(dal, community_id, 999, "")
        assert stats.watch_time_seconds == 0
        assert stats.message_count == 0

    def test_user_rank_alltime_with_data(self, community_db: Any) -> None:
        dal, community_id = community_db
        _seed_stats(
            dal, community_id, hub_user_id=1, username="alice", watch_seconds=100, messages=0
        )
        _seed_stats(dal, community_id, hub_user_id=2, username="bob", watch_seconds=500, messages=0)

        assert _user_rank(dal, community_id, 2, "watch_time_seconds") == 1
        assert _user_rank(dal, community_id, 1, "watch_time_seconds") == 2

    def test_user_rank_unranked_user_is_none(self, community_db: Any) -> None:
        dal, community_id = community_db
        assert _user_rank(dal, community_id, 999, "watch_time_seconds") is None


class TestFindHubUserId:
    def test_returns_linked_user_id(self, community_db: Any) -> None:
        dal, _ = community_db
        dal.hub_user_identities.insert(hub_user_id=42, platform="twitch", platform_user_id="p1")
        dal.commit()
        assert _find_hub_user_id(dal, "twitch", "p1") == 42

    def test_returns_none_when_unlinked(self, community_db: Any) -> None:
        dal, _ = community_db
        assert _find_hub_user_id(dal, "twitch", "no-such-user") is None
