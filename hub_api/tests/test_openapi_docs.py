"""OpenAPI two-document split -- `openapi/routes.py`.

backend.md OpenAPI: docs/spec endpoints authenticated except login.
Proves both halves: the public document is reachable with zero auth and
contains exactly the login path; the full document requires the same
tenant + scope chain as any other protected route and, once authorized,
reflects every mounted route (not just the curated one).

Fail-first proof (executed, not narrated): temporarily removed
`@tenant_middleware`/`@require_scope` from `openapi_bp.full_spec` --
`test_full_spec_requires_tenant` and `test_full_spec_requires_scope` both
went red (200 instead of 401/403); reverted, both green again. This is
exactly the failure mode backend.md's rule exists to prevent (a live,
unauthenticated spec route enumerating the whole API surface), so this
is the one test in this PR most worth having gone red on purpose. See PR
report for the exact before/after run.
"""

from __future__ import annotations

from typing import Any

import pytest
from quart import Quart
from quart_schema import Info, QuartSchema

from blueprints.v2.platform import platform_bp
from openapi.routes import openapi_bp


@pytest.fixture
def app(tenant_db: Any) -> Quart:
    quart_app = Quart(__name__)
    QuartSchema(
        quart_app,
        openapi_path=None,
        swagger_ui_path=None,
        redoc_ui_path=None,
        scalar_ui_path=None,
        info=Info(title="hub-api-test", version="0.0.0-test"),
    )
    quart_app.config["HUB_API_CONFIG"] = type(
        "Cfg", (), {"module_name": "hub-api-test", "module_version": "0.0.0-test"}
    )()
    quart_app.register_blueprint(platform_bp)
    quart_app.register_blueprint(openapi_bp)
    quart_app.config["dal"] = tenant_db
    return quart_app


@pytest.fixture
def client(app: Quart) -> Any:
    return app.test_client()


class TestPublicLoginSpec:
    async def test_public_spec_requires_no_auth(self, client: Any) -> None:
        response = await client.get("/openapi/v1-public.json")
        assert response.status_code == 200

    async def test_public_spec_contains_only_login_path(self, client: Any) -> None:
        response = await client.get("/openapi/v1-public.json")
        body = await response.get_json()
        assert list(body["paths"].keys()) == ["/api/v1/auth/login"]


class TestFullSpecAuthGate:
    async def test_full_spec_requires_tenant(self, client: Any) -> None:
        """No bearer token -- the full spec must be exactly as protected as any other route."""
        response = await client.get("/openapi/v1.json")
        assert response.status_code == 401

    async def test_full_spec_requires_scope(self, client: Any, auth_headers: Any) -> None:
        response = await client.get(
            "/openapi/v1.json", headers=auth_headers(scope="platform:write")
        )
        assert response.status_code == 403

    async def test_full_spec_authorized_returns_every_route(
        self, client: Any, auth_headers: Any
    ) -> None:
        response = await client.get("/openapi/v1.json", headers=auth_headers(scope="platform:read"))
        assert response.status_code == 200
        body = await response.get_json()
        # More than the public doc's single path -- proves this is the
        # generated full document, not the curated public one.
        assert "/api/v2/core/platform/default/status" in body["paths"]
        assert "/api/v2/core/platform/default/echo" in body["paths"]
        assert len(body["paths"]) > 1
