"""`blueprints/v1/community_activity.py` -- leaderboards, admin config, internal ingestion.

Covers the three auth surfaces this group mixes: member `tenant_middleware`
+ `require_scope`, admin `:admin` scope, and internal `X-Service-Key`
(no tenant/JWT at all -- `test_community_auth_bypass.py` already proves
every one of these rejects an unauthenticated caller; this file covers
scope enforcement + response shape for the authenticated path).
"""

from __future__ import annotations

import json as json_module
from typing import Any

import pytest
from quart import Quart
from quart_schema import QuartSchema

from blueprints.v1.community_activity import (
    activity_admin_bp,
    activity_internal_bp,
    activity_member_bp,
)


@pytest.fixture
def app(community_db: Any) -> Quart:
    dal, _ = community_db
    quart_app = Quart(__name__)
    QuartSchema(quart_app)
    quart_app.register_blueprint(activity_member_bp)
    quart_app.register_blueprint(activity_admin_bp)
    quart_app.register_blueprint(activity_internal_bp)
    quart_app.config["dal"] = dal
    return quart_app


@pytest.fixture
def client(app: Quart) -> Any:
    return app.test_client()


class TestMemberLeaderboards:
    async def test_wrong_scope_is_403(
        self, client: Any, auth_headers: Any, community_db: Any
    ) -> None:
        _, community_id = community_db
        response = await client.get(
            f"/api/v1/community/{community_id}/leaderboard/watch-time",
            headers=auth_headers(scope="community.activity:write"),
        )
        assert response.status_code == 403

    async def test_empty_leaderboard_shape(
        self, client: Any, auth_headers: Any, community_db: Any
    ) -> None:
        _, community_id = community_db
        response = await client.get(
            f"/api/v1/community/{community_id}/leaderboard/watch-time",
            headers=auth_headers(scope="community.activity:read"),
        )
        assert response.status_code == 200
        body = await response.get_json()
        assert body == {
            "success": True,
            "leaderboard": [],
            "pagination": {"offset": 0, "limit": 25, "total": 0, "has_more": False},
            "period": "alltime",
        }

    @pytest.mark.skip(
        reason="_period_stats' weekly/monthly branches use Postgres-only "
        "CURRENT_DATE - INTERVAL syntax sqlite:memory can't execute; "
        "exercised against real Postgres in integration testing, not this "
        "sqlite-backed unit fixture."
    )
    async def test_my_stats_requires_auth_required_user(
        self, client: Any, auth_headers: Any, community_db: Any
    ) -> None:
        _, community_id = community_db
        response = await client.get(
            f"/api/v1/community/{community_id}/activity/my-stats",
            headers=auth_headers(scope="community.activity:read", user_id="1"),
        )
        assert response.status_code == 200
        body = await response.get_json()
        assert body["stats"]["all_time"]["watch_time_seconds"] == 0
        assert body["stats"]["ranks"] == {"watch_time": None, "messages": None}


class TestAdminLeaderboardConfig:
    async def test_get_returns_defaults(
        self, client: Any, auth_headers: Any, community_db: Any
    ) -> None:
        _, community_id = community_db
        response = await client.get(
            f"/api/v1/admin/{community_id}/leaderboard-config",
            headers=auth_headers(scope="community.activity:admin"),
        )
        assert response.status_code == 200
        body = await response.get_json()
        assert body["config"]["display_limit"] == 25

    async def test_wrong_scope_is_403(
        self, client: Any, auth_headers: Any, community_db: Any
    ) -> None:
        _, community_id = community_db
        response = await client.get(
            f"/api/v1/admin/{community_id}/leaderboard-config",
            headers=auth_headers(scope="community.activity:read"),
        )
        assert response.status_code == 403


class TestInternalIngestion:
    async def test_missing_service_key_is_401(self, client: Any) -> None:
        response = await client.post("/api/v1/internal/activity/watch-session", json={})
        assert response.status_code == 401

    async def test_wrong_service_key_is_401(self, client: Any) -> None:
        response = await client.post(
            "/api/v1/internal/activity/watch-session",
            headers={"X-Service-Key": "not-the-real-key"},
            json={},
        )
        assert response.status_code == 401

    @pytest.mark.skip(
        reason="_update_daily_stats' ON CONFLICT target is expression-based "
        "(COALESCE(...) columns, matching migration 044's expression unique "
        "index) -- sqlite:memory's plain define_table has no equivalent "
        "expression index. Exercised against real Postgres in integration "
        "testing, not this sqlite-backed unit fixture."
    )
    async def test_valid_key_records_message_event(
        self, client: Any, service_key_headers: Any, community_db: Any
    ) -> None:
        dal, community_id = community_db
        response = await client.post(
            "/api/v1/internal/activity/message",
            headers={**service_key_headers, "Content-Type": "application/json"},
            data=json_module.dumps(
                {
                    "communityId": community_id,
                    "platform": "twitch",
                    "platformUserId": "p1",
                    "platformUsername": "streamer1",
                }
            ),
        )
        assert response.status_code == 200
        body = await response.get_json()
        assert body == {"success": True}
        assert dal(dal.activity_message_events.community_id == community_id).count() == 1

    async def test_batch_caps_at_100_events(self, client: Any, service_key_headers: Any) -> None:
        response = await client.post(
            "/api/v1/internal/activity/batch",
            headers=service_key_headers,
            json={"events": [{"type": "message"}] * 101},
        )
        assert response.status_code == 400
