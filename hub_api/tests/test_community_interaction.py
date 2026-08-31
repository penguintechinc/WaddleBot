"""`blueprints/v1/community_interaction.py` -- channels, forum, roles, permission overrides, relay.

Largest single group -- covers admin channel/role CRUD, member forum
read/post/reply, and the internal relay endpoint's `X-Service-Key` gate
(mirror-group fan-out itself is a no-op here: no mirror group exists for
the test community, so `relay_message` returns immediately after finding
zero groups -- exercised in isolation would need `mirror_groups`/
`mirror_group_members` fixture rows, out of scope for this REST-contract
test file).
"""

from __future__ import annotations

import json as json_module
from typing import Any

import pytest
from quart import Quart
from quart_schema import QuartSchema

from blueprints.v1.community_interaction import (
    interaction_admin_bp,
    interaction_internal_bp,
    interaction_member_bp,
)


@pytest.fixture
def app(community_db: Any) -> Quart:
    dal, _ = community_db
    quart_app = Quart(__name__)
    QuartSchema(quart_app)
    quart_app.register_blueprint(interaction_admin_bp)
    quart_app.register_blueprint(interaction_member_bp)
    quart_app.register_blueprint(interaction_internal_bp)
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
            f"/api/v1/admin/{community_id}/interaction/channels",
            headers=auth_headers(scope="community.interaction:write"),
        )
        assert response.status_code == 403

    async def test_unknown_community_is_404(self, client: Any, auth_headers: Any) -> None:
        response = await client.get(
            "/api/v1/admin/9999/interaction/channels",
            headers=auth_headers(scope="community.interaction:read"),
        )
        assert response.status_code == 404


class TestChannelCrudAndAutoProvision:
    async def test_create_channel_auto_provisions_hub_server(
        self, client: Any, auth_headers: Any, community_db: Any
    ) -> None:
        dal, community_id = community_db
        response = await _post_json(
            client,
            f"/api/v1/admin/{community_id}/interaction/channels",
            auth_headers(scope="community.interaction:write", user_id="1"),
            {"name": "general-chat", "channel_type": "chat"},
        )
        assert response.status_code == 201
        channel = (await response.get_json())["channel"]
        assert channel["channel_type"] == "chat"
        assert channel["community_server_channel_id"] is not None

        hub_server = (
            dal(
                (dal.community_servers.community_id == community_id)
                & (dal.community_servers.platform == "hub")
            )
            .select()
            .first()
        )
        assert hub_server is not None

    async def test_duplicate_channel_name_is_409(
        self, client: Any, auth_headers: Any, community_db: Any
    ) -> None:
        _, community_id = community_db
        headers = auth_headers(scope="community.interaction:write", user_id="1")
        await _post_json(
            client, f"/api/v1/admin/{community_id}/interaction/channels", headers, {"name": "dupe"}
        )
        response = await _post_json(
            client, f"/api/v1/admin/{community_id}/interaction/channels", headers, {"name": "dupe"}
        )
        assert response.status_code == 409


class TestForumFlow:
    async def test_create_post_then_reply_then_read(
        self, client: Any, auth_headers: Any, community_db: Any
    ) -> None:
        _, community_id = community_db
        write_headers = auth_headers(scope="community.interaction:write", user_id="1")

        channel_resp = await _post_json(
            client,
            f"/api/v1/admin/{community_id}/interaction/channels",
            write_headers,
            {"name": "forum-general", "channel_type": "forum"},
        )
        channel_id = (await channel_resp.get_json())["channel"]["id"]

        post_resp = await _post_json(
            client,
            f"/api/v1/community/{community_id}/interact/forum/{channel_id}/posts",
            write_headers,
            {"title": "Welcome thread", "body": "Say hi!"},
        )
        assert post_resp.status_code == 201
        post_id = (await post_resp.get_json())["post"]["id"]

        reply_resp = await _post_json(
            client,
            f"/api/v1/community/{community_id}/interact/forum/posts/{post_id}/replies",
            write_headers,
            {"content": "Hi there!"},
        )
        assert reply_resp.status_code == 201

        get_resp = await client.get(
            f"/api/v1/community/{community_id}/interact/forum/{channel_id}/posts/{post_id}",
            headers=auth_headers(scope="community.interaction:read"),
        )
        assert get_resp.status_code == 200
        body = await get_resp.get_json()
        assert body["post"]["reply_count"] == 1
        assert len(body["post"]["replies"]) == 1
        assert body["post"]["replies"][0]["content"] == "Hi there!"

    async def test_reply_on_locked_post_is_rejected(
        self, client: Any, auth_headers: Any, community_db: Any
    ) -> None:
        dal, community_id = community_db
        write_headers = auth_headers(scope="community.interaction:write", user_id="1")
        channel_resp = await _post_json(
            client,
            f"/api/v1/admin/{community_id}/interaction/channels",
            write_headers,
            {"name": "locked-forum", "channel_type": "forum"},
        )
        channel_id = (await channel_resp.get_json())["channel"]["id"]
        post_resp = await _post_json(
            client,
            f"/api/v1/community/{community_id}/interact/forum/{channel_id}/posts",
            write_headers,
            {"title": "Locked topic"},
        )
        post_id = (await post_resp.get_json())["post"]["id"]

        await client.put(
            f"/api/v1/admin/{community_id}/interaction/forum/posts/{post_id}",
            headers={**write_headers, "Content-Type": "application/json"},
            data=json_module.dumps({"is_locked": True}),
        )

        reply_resp = await _post_json(
            client,
            f"/api/v1/community/{community_id}/interact/forum/posts/{post_id}/replies",
            write_headers,
            {"content": "too late"},
        )
        assert reply_resp.status_code == 400


class TestCommunityRoles:
    async def test_priority_out_of_range_is_400(
        self, client: Any, auth_headers: Any, community_db: Any
    ) -> None:
        _, community_id = community_db
        response = await _post_json(
            client,
            f"/api/v1/admin/{community_id}/interaction/roles",
            auth_headers(scope="community.interaction:manage_roles"),
            {"name": "vip", "priority": 99},
        )
        assert response.status_code == 400

    async def test_create_and_delete_custom_role(
        self, client: Any, auth_headers: Any, community_db: Any
    ) -> None:
        dal, community_id = community_db
        # `member` is the reassignment target on role delete -- seed it,
        # matching `seed_community_system_roles()` (058_tenants_and_claims.sql).
        dal.community_roles.insert(
            community_id=community_id, name="member", is_system=True, priority=10
        )
        dal.commit()

        manage_headers = auth_headers(scope="community.interaction:manage_roles")
        create_resp = await _post_json(
            client,
            f"/api/v1/admin/{community_id}/interaction/roles",
            manage_headers,
            {"name": "VIP", "priority": 20, "scopes": ["channels:read"]},
        )
        assert create_resp.status_code == 201
        role = (await create_resp.get_json())["role"]
        assert role["name"] == "vip"

        delete_resp = await client.delete(
            f"/api/v1/admin/{community_id}/interaction/roles/{role['id']}", headers=manage_headers
        )
        assert delete_resp.status_code == 200

    async def test_delete_system_role_is_403(
        self, client: Any, auth_headers: Any, community_db: Any
    ) -> None:
        dal, community_id = community_db
        role_id = dal.community_roles.insert(
            community_id=community_id, name="admin", is_system=True, priority=90
        )
        dal.commit()

        response = await client.delete(
            f"/api/v1/admin/{community_id}/interaction/roles/{role_id}",
            headers=auth_headers(scope="community.interaction:manage_roles"),
        )
        assert response.status_code == 403


class TestInternalRelay:
    async def test_missing_service_key_is_401(self, client: Any) -> None:
        response = await client.post("/api/v1/internal/relay/incoming", json={})
        assert response.status_code == 401

    async def test_unknown_source_channel_is_404(
        self, client: Any, service_key_headers: Any
    ) -> None:
        response = await _post_json(
            client,
            "/api/v1/internal/relay/incoming",
            service_key_headers,
            {"sourcePlatformChannelId": "does-not-exist"},
        )
        assert response.status_code == 404
