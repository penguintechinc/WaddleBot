"""`blueprints/v1/community_loyalty.py` -- reverse-proxy to `loyalty-interaction`.

Same pattern as `test_community_polls.py`, mocking `services.
community_loyalty`'s `get_or_default`/`call` (the shared proxy helpers
every one of the 20 routes in this group funnels through) rather than
each route's own HTTP call.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest
from quart import Quart
from quart_schema import QuartSchema

from blueprints.v1.community_loyalty import loyalty_bp
from services import community_loyalty as loyalty_svc


@pytest.fixture
def app(community_db: Any) -> Quart:
    dal, _ = community_db
    quart_app = Quart(__name__)
    QuartSchema(quart_app)
    quart_app.register_blueprint(loyalty_bp)
    quart_app.config["dal"] = dal
    return quart_app


@pytest.fixture
def client(app: Quart) -> Any:
    return app.test_client()


@pytest.fixture(autouse=True)
def _feature_enabled_default_on(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Default the `community.loyalty` two-gate Feature flag ON for every test in this file."""
    import blueprints.v1.community_loyalty as loyalty_module

    monkeypatch.setattr(loyalty_module, "feature_enabled", AsyncMock(return_value=True))


class TestScopeAndTenant:
    async def test_wrong_scope_is_403(
        self, client: Any, auth_headers: Any, community_db: Any
    ) -> None:
        _, community_id = community_db
        response = await client.get(
            f"/api/v1/admin/{community_id}/loyalty/config",
            headers=auth_headers(scope="community.loyalty:write"),
        )
        assert response.status_code == 403

    async def test_wipe_requires_admin_scope(
        self, client: Any, auth_headers: Any, community_db: Any
    ) -> None:
        _, community_id = community_db
        response = await client.post(
            f"/api/v1/admin/{community_id}/loyalty/wipe",
            headers=auth_headers(scope="community.loyalty:write"),
        )
        assert response.status_code == 403

    async def test_unknown_community_is_404(self, client: Any, auth_headers: Any) -> None:
        response = await client.get(
            "/api/v1/admin/9999/loyalty/config",
            headers=auth_headers(scope="community.loyalty:read"),
        )
        assert response.status_code == 404

    @pytest.mark.parametrize(
        "method,path_suffix,scope",
        [
            ("PUT", "loyalty/config", "community.loyalty:write"),
            ("GET", "loyalty/leaderboard", "community.loyalty:read"),
            ("PUT", "loyalty/user/1/balance", "community.loyalty:admin"),
            ("POST", "loyalty/wipe", "community.loyalty:admin"),
            ("GET", "loyalty/stats", "community.loyalty:read"),
            ("GET", "loyalty/giveaways", "community.loyalty:read"),
            ("POST", "loyalty/giveaways", "community.loyalty:write"),
            ("GET", "loyalty/giveaways/1/entries", "community.loyalty:read"),
            ("POST", "loyalty/giveaways/1/draw", "community.loyalty:write"),
            ("PUT", "loyalty/giveaways/1/end", "community.loyalty:write"),
            ("GET", "loyalty/games/config", "community.loyalty:read"),
            ("PUT", "loyalty/games/config", "community.loyalty:write"),
            ("GET", "loyalty/games/stats", "community.loyalty:read"),
            ("GET", "loyalty/games/recent", "community.loyalty:read"),
            ("GET", "loyalty/gear/categories", "community.loyalty:read"),
            ("GET", "loyalty/gear/items", "community.loyalty:read"),
            ("POST", "loyalty/gear/items", "community.loyalty:write"),
            ("PUT", "loyalty/gear/items/1", "community.loyalty:write"),
            ("DELETE", "loyalty/gear/items/1", "community.loyalty:write"),
            ("GET", "loyalty/gear/stats", "community.loyalty:read"),
        ],
    )
    async def test_remaining_routes_404_on_unknown_community(
        self, client: Any, auth_headers: Any, method: str, path_suffix: str, scope: str
    ) -> None:
        response = await client.open(
            f"/api/v1/admin/9999/{path_suffix}", method=method, headers=auth_headers(scope=scope)
        )
        assert response.status_code == 404


class TestRemainingRoutesForward:
    """One representative call per remaining route.

    Proves the URL/scope wiring for the group's other ~17 endpoints
    without re-deriving the full graceful-degradation behavior already
    covered by `TestProxyDegradesGracefully`.
    """

    @pytest.mark.parametrize(
        "method,path_suffix,scope,expected_key",
        [
            ("GET", "loyalty/leaderboard", "community.loyalty:read", "users"),
            ("GET", "loyalty/stats", "community.loyalty:read", "stats"),
            ("GET", "loyalty/giveaways", "community.loyalty:read", "giveaways"),
            ("GET", "loyalty/giveaways/1/entries", "community.loyalty:read", "entries"),
            ("GET", "loyalty/games/config", "community.loyalty:read", "config"),
            ("GET", "loyalty/games/stats", "community.loyalty:read", "stats"),
            ("GET", "loyalty/games/recent", "community.loyalty:read", "games"),
            ("GET", "loyalty/gear/categories", "community.loyalty:read", "categories"),
            ("GET", "loyalty/gear/items", "community.loyalty:read", "items"),
            ("GET", "loyalty/gear/stats", "community.loyalty:read", "stats"),
        ],
    )
    async def test_get_route_forwards(
        self,
        client: Any,
        auth_headers: Any,
        community_db: Any,
        monkeypatch: Any,
        method: str,
        path_suffix: str,
        scope: str,
        expected_key: str,
    ) -> None:
        _, community_id = community_db

        async def fake_get_or_default(path: str, defaults: dict[str, Any]) -> dict[str, Any]:
            return {"success": True, **defaults}

        monkeypatch.setattr(loyalty_svc, "get_or_default", fake_get_or_default)
        response = await client.open(
            f"/api/v1/admin/{community_id}/{path_suffix}",
            method=method,
            headers=auth_headers(scope=scope),
        )
        assert response.status_code == 200
        body = await response.get_json()
        assert expected_key in body

    @pytest.mark.parametrize(
        "method,path_suffix,scope",
        [
            ("PUT", "loyalty/user/1/balance", "community.loyalty:admin"),
            ("POST", "loyalty/giveaways/1/draw", "community.loyalty:write"),
            ("PUT", "loyalty/giveaways/1/end", "community.loyalty:write"),
            ("PUT", "loyalty/games/config", "community.loyalty:write"),
            ("PUT", "loyalty/gear/items/1", "community.loyalty:write"),
        ],
    )
    async def test_write_route_forwards(
        self,
        client: Any,
        auth_headers: Any,
        community_db: Any,
        monkeypatch: Any,
        method: str,
        path_suffix: str,
        scope: str,
    ) -> None:
        import json as json_module

        _, community_id = community_db

        async def fake_call(
            method_arg: str, path: str, json_body: dict[str, Any] | None = None
        ) -> dict[str, Any]:
            return {"success": True}

        monkeypatch.setattr(loyalty_svc, "call", fake_call)
        response = await client.open(
            f"/api/v1/admin/{community_id}/{path_suffix}",
            method=method,
            headers={**auth_headers(scope=scope), "Content-Type": "application/json"},
            data=json_module.dumps({}),
        )
        assert response.status_code == 200

    async def test_create_giveaway_forwards(
        self, client: Any, auth_headers: Any, community_db: Any, monkeypatch: Any
    ) -> None:
        import json as json_module

        _, community_id = community_db

        async def fake_call(
            method_arg: str, path: str, json_body: dict[str, Any] | None = None
        ) -> dict[str, Any]:
            return {"success": True, "giveaway": {"id": 1}}

        monkeypatch.setattr(loyalty_svc, "call", fake_call)
        response = await client.post(
            f"/api/v1/admin/{community_id}/loyalty/giveaways",
            headers={
                **auth_headers(scope="community.loyalty:write"),
                "Content-Type": "application/json",
            },
            data=json_module.dumps({"title": "Summer raffle"}),
        )
        assert response.status_code == 201

    async def test_create_gear_item_forwards(
        self, client: Any, auth_headers: Any, community_db: Any, monkeypatch: Any
    ) -> None:
        import json as json_module

        _, community_id = community_db

        async def fake_call(
            method_arg: str, path: str, json_body: dict[str, Any] | None = None
        ) -> dict[str, Any]:
            return {"success": True, "item": {"id": 1}}

        monkeypatch.setattr(loyalty_svc, "call", fake_call)
        response = await client.post(
            f"/api/v1/admin/{community_id}/loyalty/gear/items",
            headers={
                **auth_headers(scope="community.loyalty:write"),
                "Content-Type": "application/json",
            },
            data=json_module.dumps({"name": "Sword skin"}),
        )
        assert response.status_code == 201

    async def test_delete_gear_item_forwards(
        self, client: Any, auth_headers: Any, community_db: Any, monkeypatch: Any
    ) -> None:
        _, community_id = community_db

        async def fake_call(
            method_arg: str, path: str, json_body: dict[str, Any] | None = None
        ) -> dict[str, Any]:
            return {"success": True}

        monkeypatch.setattr(loyalty_svc, "call", fake_call)
        response = await client.delete(
            f"/api/v1/admin/{community_id}/loyalty/gear/items/1",
            headers=auth_headers(scope="community.loyalty:write"),
        )
        assert response.status_code == 200

    async def test_proxy_error_surfaces_as_502(
        self, client: Any, auth_headers: Any, community_db: Any, monkeypatch: Any
    ) -> None:
        _, community_id = community_db

        async def fake_call(
            method_arg: str, path: str, json_body: dict[str, Any] | None = None
        ) -> dict[str, Any]:
            raise loyalty_svc.LoyaltyProxyError("downstream exploded")

        monkeypatch.setattr(loyalty_svc, "call", fake_call)
        response = await client.post(
            f"/api/v1/admin/{community_id}/loyalty/wipe",
            headers=auth_headers(scope="community.loyalty:admin"),
        )
        assert response.status_code == 502


class TestProxyDegradesGracefully:
    async def test_config_falls_back_to_defaults_when_service_unavailable(
        self, client: Any, auth_headers: Any, community_db: Any, monkeypatch: Any
    ) -> None:
        _, community_id = community_db

        async def fake_get_or_default(path: str, defaults: dict[str, Any]) -> dict[str, Any]:
            return {"success": True, "unavailable": True, **defaults}

        monkeypatch.setattr(loyalty_svc, "get_or_default", fake_get_or_default)

        response = await client.get(
            f"/api/v1/admin/{community_id}/loyalty/config",
            headers=auth_headers(scope="community.loyalty:read"),
        )
        assert response.status_code == 200
        body = await response.get_json()
        assert body["success"] is True
        assert body["unavailable"] is True
        assert body["config"]["currency_name"] == "Points"
