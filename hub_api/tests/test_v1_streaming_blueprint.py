"""`blueprints/v1/streaming.py` -- characterization tests for the video-proxy config port.

`services.streaming_proxy_service.VideoProxyClient` is monkeypatched at
the method level (mirrors `tests/test_event_blueprint.py`'s `proxy_stub`
pattern) -- no real network I/O in route-level tests. `services/
streaming_proxy_service.py`'s own `httpx` forwarding logic (success/404/
409/transport-failure per client method) is exercised directly, below
the route layer, in `tests/test_streaming_proxy_service.py` (mirrors
`tests/test_event_calendar_proxy.py`'s split from `tests/
test_event_blueprint.py`).

Fail-first proof (executed, not narrated): temporarily removed the
`await validate_outbound_url(rtmp_url, ...)` call from `blueprints.v1.
streaming.add_destination` -- `test_add_destination_ssrf_rtmp_url_is_400`
went red (the mocked proxy call was reached with a private-IP `rtmpUrl`
instead of being rejected first); reverted, green again.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest
from quart import Quart
from quart_schema import QuartSchema

import blueprints.v1.streaming as streaming_module
from blueprints.v1.streaming import streaming_bp
from config import HubAPIConfig
from services.errors import bad_request, not_found
from tests.conftest import TENANT_SLUG, make_user_token


def _test_config() -> HubAPIConfig:
    return HubAPIConfig(
        module_name="hub-api-test",
        module_version="0.0.0-test",
        module_port=8204,
        grpc_port=50204,
        database_url="sqlite:memory",
        database_read_replica_url=None,
        db_pool_size=1,
        db_max_retries=1,
        db_retry_delay=1,
        secret_key="change-me-in-production",
        jwt_algorithm="HS256",
        default_tenant_slug="global",
        posthog_api_key=None,
        posthog_host="https://license.penguintech.io",
        license_server_url="https://license.penguintech.io",
        identity_callback_base_url="http://localhost:8204",
        frontend_origin="http://localhost:5173",
        log_level="INFO",
    )


@pytest.fixture
def app(streaming_db: Any) -> Quart:
    quart_app = Quart(__name__)
    QuartSchema(quart_app)
    quart_app.register_blueprint(streaming_bp)
    quart_app.config["dal"] = streaming_db.dal
    quart_app.config["async_dal"] = streaming_db
    quart_app.config["HUB_API_CONFIG"] = _test_config()
    return quart_app


@pytest.fixture
def client(app: Quart) -> Any:
    return app.test_client()


@pytest.fixture(autouse=True)
def _feature_enabled_default_on(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    """Default the `streaming.broadcast` two-gate Feature flag ON for every test in this file."""
    stub = AsyncMock(return_value=True)
    monkeypatch.setattr(streaming_module, "feature_enabled", stub)
    return stub


def _tenant_id(db: Any) -> int:
    row = db.dal(db.dal.tenants.slug == TENANT_SLUG).select().first()
    return int(row.id)


def _seed_community(db: Any) -> int:
    community_id: int = db.dal.communities.insert(name="acme-community", tenant_id=_tenant_id(db))
    db.dal.commit()
    return community_id


def _seed_admin(db: Any, *, community_id: int, user_id: int = 1) -> dict[str, str]:
    role_id = db.dal.community_roles.insert(
        community_id=community_id,
        name="community-admin",
        base_claims={"scopes": ["community:manage_members"]},
    )
    db.dal.community_members.insert(
        community_id=community_id,
        user_id=str(user_id),
        role="community-admin",
        community_role_id=role_id,
        is_active=True,
    )
    db.dal.commit()
    return {"Authorization": f"Bearer {make_user_token(user_id=user_id)}"}


class TestAuthAndAdminGate:
    async def test_missing_token_is_401(self, client: Any, streaming_db: Any) -> None:
        community_id = _seed_community(streaming_db)
        response = await client.get(f"/api/v1/admin/{community_id}/streams")
        assert response.status_code == 401

    async def test_non_admin_member_is_403(self, client: Any, streaming_db: Any) -> None:
        community_id = _seed_community(streaming_db)
        streaming_db.dal.community_members.insert(
            community_id=community_id, user_id="1", role="member", is_active=True
        )
        streaming_db.dal.commit()
        headers = {"Authorization": f"Bearer {make_user_token(user_id=1)}"}
        response = await client.get(f"/api/v1/admin/{community_id}/streams", headers=headers)
        assert response.status_code == 403


@pytest.fixture
def proxy_stub(monkeypatch: pytest.MonkeyPatch) -> dict[str, AsyncMock]:
    """Patch every `VideoProxyClient` method the routes call -- no real network I/O."""
    stubs = {
        "get_config": AsyncMock(return_value={"rtmpPort": 1935, "enabled": True}),
        "create_config": AsyncMock(return_value={"rtmpPort": 1935, "enabled": True}),
        "regenerate_key": AsyncMock(return_value="new-stream-key"),
        "get_destinations": AsyncMock(return_value=[]),
        "add_destination": AsyncMock(return_value={"id": 1, "platform": "twitch"}),
        "remove_destination": AsyncMock(return_value=None),
        "toggle_force_cut": AsyncMock(return_value={"id": 1, "forceCut": True}),
        "get_status": AsyncMock(return_value={"active": True, "destinations": []}),
    }
    for name, stub in stubs.items():
        monkeypatch.setattr(streaming_module._client, name, stub)
    return stubs


class TestProxiedRoutes:
    async def test_get_stream_config_relays_body(
        self, client: Any, streaming_db: Any, proxy_stub: dict[str, AsyncMock]
    ) -> None:
        community_id = _seed_community(streaming_db)
        headers = _seed_admin(streaming_db, community_id=community_id)
        response = await client.get(f"/api/v1/admin/{community_id}/streams", headers=headers)
        assert response.status_code == 200
        body = await response.get_json()
        assert body == {"success": True, "config": {"rtmpPort": 1935, "enabled": True}}
        proxy_stub["get_config"].assert_awaited_once_with(community_id)

    async def test_create_stream_config_invalid_port_is_400(
        self, client: Any, streaming_db: Any, proxy_stub: dict[str, AsyncMock]
    ) -> None:
        community_id = _seed_community(streaming_db)
        headers = _seed_admin(streaming_db, community_id=community_id)
        response = await client.post(
            f"/api/v1/admin/{community_id}/streams",
            headers=headers,
            json={"rtmpPort": 80},
        )
        assert response.status_code == 400
        proxy_stub["create_config"].assert_not_awaited()

    async def test_create_stream_config_success(
        self, client: Any, streaming_db: Any, proxy_stub: dict[str, AsyncMock]
    ) -> None:
        community_id = _seed_community(streaming_db)
        headers = _seed_admin(streaming_db, community_id=community_id)
        response = await client.post(
            f"/api/v1/admin/{community_id}/streams",
            headers=headers,
            json={"rtmpPort": 1935, "httpPort": 8080},
        )
        assert response.status_code == 201

    async def test_regenerate_key(
        self, client: Any, streaming_db: Any, proxy_stub: dict[str, AsyncMock]
    ) -> None:
        community_id = _seed_community(streaming_db)
        headers = _seed_admin(streaming_db, community_id=community_id)
        response = await client.post(
            f"/api/v1/admin/{community_id}/streams/key/regenerate", headers=headers
        )
        assert response.status_code == 200
        body = await response.get_json()
        assert body["streamKey"] == "new-stream-key"

    async def test_get_destinations(
        self, client: Any, streaming_db: Any, proxy_stub: dict[str, AsyncMock]
    ) -> None:
        community_id = _seed_community(streaming_db)
        headers = _seed_admin(streaming_db, community_id=community_id)
        response = await client.get(
            f"/api/v1/admin/{community_id}/streams/destinations", headers=headers
        )
        assert response.status_code == 200

    async def test_add_destination_missing_fields_is_400(
        self, client: Any, streaming_db: Any, proxy_stub: dict[str, AsyncMock]
    ) -> None:
        community_id = _seed_community(streaming_db)
        headers = _seed_admin(streaming_db, community_id=community_id)
        response = await client.post(
            f"/api/v1/admin/{community_id}/streams/destinations",
            headers=headers,
            json={"platform": "twitch"},
        )
        assert response.status_code == 400
        proxy_stub["add_destination"].assert_not_awaited()

    async def test_add_destination_ssrf_rtmp_url_is_400(
        self, client: Any, streaming_db: Any, proxy_stub: dict[str, AsyncMock]
    ) -> None:
        """`rtmpUrl` targeting a private/link-local address is rejected before proxying."""
        community_id = _seed_community(streaming_db)
        headers = _seed_admin(streaming_db, community_id=community_id)
        response = await client.post(
            f"/api/v1/admin/{community_id}/streams/destinations",
            headers=headers,
            json={
                "platform": "twitch",
                "rtmpUrl": "rtmp://169.254.169.254/latest/meta-data",
                "streamKey": "sk-123",
            },
        )
        assert response.status_code == 400
        proxy_stub["add_destination"].assert_not_awaited()

    async def test_add_destination_success(
        self, client: Any, streaming_db: Any, proxy_stub: dict[str, AsyncMock]
    ) -> None:
        community_id = _seed_community(streaming_db)
        headers = _seed_admin(streaming_db, community_id=community_id)
        response = await client.post(
            f"/api/v1/admin/{community_id}/streams/destinations",
            headers=headers,
            json={
                "platform": "twitch",
                "rtmpUrl": "rtmp://8.8.8.8/live",
                "streamKey": "sk-123",
            },
        )
        assert response.status_code == 201

    async def test_remove_destination(
        self, client: Any, streaming_db: Any, proxy_stub: dict[str, AsyncMock]
    ) -> None:
        community_id = _seed_community(streaming_db)
        headers = _seed_admin(streaming_db, community_id=community_id)
        response = await client.delete(
            f"/api/v1/admin/{community_id}/streams/destinations/5", headers=headers
        )
        assert response.status_code == 200
        proxy_stub["remove_destination"].assert_awaited_once_with(community_id, 5)

    async def test_toggle_force_cut_bad_body_is_400(
        self, client: Any, streaming_db: Any, proxy_stub: dict[str, AsyncMock]
    ) -> None:
        community_id = _seed_community(streaming_db)
        headers = _seed_admin(streaming_db, community_id=community_id)
        response = await client.put(
            f"/api/v1/admin/{community_id}/streams/destinations/5/force-cut",
            headers=headers,
            json={},
        )
        assert response.status_code == 400

    async def test_toggle_force_cut_success(
        self, client: Any, streaming_db: Any, proxy_stub: dict[str, AsyncMock]
    ) -> None:
        community_id = _seed_community(streaming_db)
        headers = _seed_admin(streaming_db, community_id=community_id)
        response = await client.put(
            f"/api/v1/admin/{community_id}/streams/destinations/5/force-cut",
            headers=headers,
            json={"forceCut": True},
        )
        assert response.status_code == 200

    async def test_get_stream_status(
        self, client: Any, streaming_db: Any, proxy_stub: dict[str, AsyncMock]
    ) -> None:
        community_id = _seed_community(streaming_db)
        headers = _seed_admin(streaming_db, community_id=community_id)
        response = await client.get(f"/api/v1/admin/{community_id}/streams/status", headers=headers)
        assert response.status_code == 200


class TestProxyFailurePropagation:
    """Every route's `except ApiError` branch -- the downstream client raising, not 200."""

    async def test_create_stream_config_invalid_http_port_is_400(
        self, client: Any, streaming_db: Any, proxy_stub: dict[str, AsyncMock]
    ) -> None:
        community_id = _seed_community(streaming_db)
        headers = _seed_admin(streaming_db, community_id=community_id)
        response = await client.post(
            f"/api/v1/admin/{community_id}/streams",
            headers=headers,
            json={"httpPort": 80},
        )
        assert response.status_code == 400
        proxy_stub["create_config"].assert_not_awaited()

    async def test_regenerate_key_propagates_client_failure(
        self, client: Any, streaming_db: Any, proxy_stub: dict[str, AsyncMock]
    ) -> None:
        community_id = _seed_community(streaming_db)
        headers = _seed_admin(streaming_db, community_id=community_id)
        proxy_stub["regenerate_key"].side_effect = not_found("Stream configuration not found")
        response = await client.post(
            f"/api/v1/admin/{community_id}/streams/key/regenerate", headers=headers
        )
        assert response.status_code == 404

    async def test_get_destinations_propagates_client_failure(
        self, client: Any, streaming_db: Any, proxy_stub: dict[str, AsyncMock]
    ) -> None:
        community_id = _seed_community(streaming_db)
        headers = _seed_admin(streaming_db, community_id=community_id)
        proxy_stub["get_destinations"].side_effect = bad_request("Failed to fetch")
        response = await client.get(
            f"/api/v1/admin/{community_id}/streams/destinations", headers=headers
        )
        assert response.status_code == 400

    async def test_remove_destination_propagates_client_failure(
        self, client: Any, streaming_db: Any, proxy_stub: dict[str, AsyncMock]
    ) -> None:
        community_id = _seed_community(streaming_db)
        headers = _seed_admin(streaming_db, community_id=community_id)
        proxy_stub["remove_destination"].side_effect = not_found("Destination not found")
        response = await client.delete(
            f"/api/v1/admin/{community_id}/streams/destinations/5", headers=headers
        )
        assert response.status_code == 404

    async def test_get_stream_status_propagates_client_failure(
        self, client: Any, streaming_db: Any, proxy_stub: dict[str, AsyncMock]
    ) -> None:
        community_id = _seed_community(streaming_db)
        headers = _seed_admin(streaming_db, community_id=community_id)
        proxy_stub["get_status"].side_effect = bad_request("Failed to fetch streaming status")
        response = await client.get(f"/api/v1/admin/{community_id}/streams/status", headers=headers)
        assert response.status_code == 400
