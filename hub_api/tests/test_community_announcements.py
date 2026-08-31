"""`blueprints/v1/community_announcements.py` -- CRUD + publish/pin/archive/broadcast.

Uses `data=`/explicit content-type for write bodies (see
`test_community_activity.py`'s comment on the quart-schema test-client
`json=` pre-serialization bug this sidesteps).
"""

from __future__ import annotations

import json as json_module
from typing import Any

import pytest
from quart import Quart
from quart_schema import QuartSchema

from blueprints.v1.community_announcements import announcements_bp


@pytest.fixture
def app(community_db: Any) -> Quart:
    dal, _ = community_db
    quart_app = Quart(__name__)
    QuartSchema(quart_app)
    quart_app.register_blueprint(announcements_bp)
    quart_app.config["dal"] = dal
    return quart_app


@pytest.fixture
def client(app: Quart) -> Any:
    return app.test_client()


async def _post_json(
    client: Any, path: str, headers: dict[str, str], payload: dict[str, Any]
) -> Any:
    return await client.post(
        path,
        headers={**headers, "Content-Type": "application/json"},
        data=json_module.dumps(payload),
    )


class TestScopeAndTenant:
    async def test_wrong_scope_is_403(
        self, client: Any, auth_headers: Any, community_db: Any
    ) -> None:
        _, community_id = community_db
        response = await client.get(
            f"/api/v1/admin/{community_id}/announcements",
            headers=auth_headers(scope="community.announcements:write"),
        )
        assert response.status_code == 403

    async def test_unknown_community_is_404(self, client: Any, auth_headers: Any) -> None:
        response = await client.get(
            "/api/v1/admin/9999/announcements",
            headers=auth_headers(scope="community.announcements:read"),
        )
        assert response.status_code == 404


class TestCreateAndLifecycle:
    async def test_create_requires_title_and_content(
        self, client: Any, auth_headers: Any, community_db: Any
    ) -> None:
        _, community_id = community_db
        response = await _post_json(
            client,
            f"/api/v1/admin/{community_id}/announcements",
            auth_headers(scope="community.announcements:write", user_id="1"),
            {"title": "", "content": "body"},
        )
        assert response.status_code == 400

    async def test_full_create_publish_pin_flow(
        self, client: Any, auth_headers: Any, community_db: Any
    ) -> None:
        _, community_id = community_db
        headers = auth_headers(scope="community.announcements:write", user_id="1")

        create_resp = await _post_json(
            client,
            f"/api/v1/admin/{community_id}/announcements",
            headers,
            {"title": "Server maintenance", "content": "Downtime tonight", "status": "draft"},
        )
        assert create_resp.status_code == 201
        created = (await create_resp.get_json())["data"]
        assert created["status"] == "draft"
        assert created["is_pinned"] is False
        announcement_id = created["id"]

        publish_resp = await client.post(
            f"/api/v1/admin/{community_id}/announcements/{announcement_id}/publish",
            headers=headers,
        )
        assert publish_resp.status_code == 200
        published = (await publish_resp.get_json())["data"]
        assert published["status"] == "published"
        assert published["published_at"] is not None

        pin_resp = await client.put(
            f"/api/v1/admin/{community_id}/announcements/{announcement_id}/pin", headers=headers
        )
        assert pin_resp.status_code == 200
        assert (await pin_resp.get_json())["data"]["is_pinned"] is True

        list_resp = await client.get(
            f"/api/v1/admin/{community_id}/announcements",
            headers=auth_headers(scope="community.announcements:read"),
        )
        assert list_resp.status_code == 200
        list_body = await list_resp.get_json()
        assert list_body["pagination"]["total"] == 1
        assert list_body["data"][0]["id"] == announcement_id

    async def test_get_missing_announcement_is_404(
        self, client: Any, auth_headers: Any, community_db: Any
    ) -> None:
        _, community_id = community_db
        response = await client.get(
            f"/api/v1/admin/{community_id}/announcements/9999",
            headers=auth_headers(scope="community.announcements:read"),
        )
        assert response.status_code == 404


class TestBroadcast:
    async def test_broadcast_requires_published_status(
        self, client: Any, auth_headers: Any, community_db: Any
    ) -> None:
        _, community_id = community_db
        headers = auth_headers(scope="community.announcements:write", user_id="1")
        create_resp = await _post_json(
            client,
            f"/api/v1/admin/{community_id}/announcements",
            headers,
            {"title": "Draft only", "content": "not published yet", "status": "draft"},
        )
        announcement_id = (await create_resp.get_json())["data"]["id"]

        response = await _post_json(
            client,
            f"/api/v1/admin/{community_id}/announcements/{announcement_id}/broadcast",
            headers,
            {"platforms": ["discord"]},
        )
        assert response.status_code == 400

    async def test_broadcast_rejects_empty_platforms(
        self, client: Any, auth_headers: Any, community_db: Any
    ) -> None:
        _, community_id = community_db
        headers = auth_headers(scope="community.announcements:write", user_id="1")
        response = await _post_json(
            client,
            f"/api/v1/admin/{community_id}/announcements/1/broadcast",
            headers,
            {"platforms": []},
        )
        assert response.status_code == 400
