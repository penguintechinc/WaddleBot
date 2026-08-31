"""`blueprints/platform.py` -- the port-pattern proof, exercised end-to-end.

Standalone Quart app (mirrors `libs/flask_core/tests/test_mcp_routes.py`'s
own pattern: real JWTs, real in-memory pydal `tenants` table) registering
only `platform_bp`, rather than the full `create_app()` -- keeps this
file's assertions about tenant/scope/DTO enforcement independent of DAL
startup, health, and MCP wiring (covered separately in
`test_app_factory.py`).

Fail-first proof (executed, not narrated): temporarily swapped
`require_scope("platform:read")` for `require_scope("platform:write")`
on `blueprints/platform.py`'s `/status` handler. `test_wrong_scope_is_403`
went red (its `platform:write` token now satisfied the swapped
requirement, returning 200 instead of the expected 403);
`test_correct_scope_returns_validated_dto` and `test_wildcard_scope_passes`
also went red (their `platform:read`/`*:read` tokens no longer satisfied
it, returning 403 instead of the expected 200). The other 7 tests in
this file were unaffected (they exercise `/echo` or the tenant-resolution
path, neither of which touches `/status`'s scope requirement). Reverted,
all 10 green again. See PR report for the exact before/after run.
"""

from __future__ import annotations

from typing import Any

import pytest
from quart import Quart
from quart_schema import QuartSchema

from blueprints.platform import platform_bp


@pytest.fixture
def app(tenant_db: Any) -> Quart:
    quart_app = Quart(__name__)
    QuartSchema(quart_app)
    quart_app.register_blueprint(platform_bp)
    quart_app.config["dal"] = tenant_db
    return quart_app


@pytest.fixture
def client(app: Quart) -> Any:
    return app.test_client()


class TestTenantEnforcement:
    async def test_missing_tenant_is_401(self, client: Any) -> None:
        """No bearer token at all -- tenant_middleware (outermost) rejects first."""
        response = await client.get("/core/platform/default/status")
        assert response.status_code == 401

    async def test_invalid_token_is_401(self, client: Any) -> None:
        response = await client.get(
            "/core/platform/default/status",
            headers={"Authorization": "Bearer not-a-real-token"},
        )
        assert response.status_code == 401

    async def test_unknown_tenant_is_403(self, client: Any, auth_headers: Any) -> None:
        headers = auth_headers(scope="platform:read", tenant="no-such-tenant")
        response = await client.get("/core/platform/default/status", headers=headers)
        assert response.status_code == 403


class TestScopeEnforcement:
    async def test_missing_scope_is_403(self, client: Any, auth_headers: Any) -> None:
        """Tenant resolves fine; empty `scope` claim -- require_scope rejects."""
        response = await client.get("/core/platform/default/status", headers=auth_headers(scope=""))
        assert response.status_code == 403

    async def test_wrong_scope_is_403(self, client: Any, auth_headers: Any) -> None:
        response = await client.get(
            "/core/platform/default/status", headers=auth_headers(scope="platform:write")
        )
        assert response.status_code == 403


class TestValidatedResponseDTO:
    async def test_correct_scope_returns_validated_dto(
        self, client: Any, auth_headers: Any
    ) -> None:
        response = await client.get(
            "/core/platform/default/status", headers=auth_headers(scope="platform:read")
        )
        assert response.status_code == 200
        body = await response.get_json()
        # Exact field set -- security.md Output Validation: never a wider shape
        # than the DTO declares.
        assert body == {"module": "hub-api", "status": "ok", "tenant": "acme-corp"}

    async def test_wildcard_scope_passes(self, client: Any, auth_headers: Any) -> None:
        response = await client.get(
            "/core/platform/default/status", headers=auth_headers(scope="*:read")
        )
        assert response.status_code == 200


class TestValidatedRequestDTO:
    async def test_echo_requires_write_scope(self, client: Any, auth_headers: Any) -> None:
        response = await client.post(
            "/core/platform/default/echo",
            headers=auth_headers(scope="platform:read"),
            json={"message": "hello"},
        )
        assert response.status_code == 403

    async def test_echo_round_trips_validated_request_and_response(
        self, client: Any, auth_headers: Any
    ) -> None:
        response = await client.post(
            "/core/platform/default/echo",
            headers=auth_headers(scope="platform:write"),
            json={"message": "hello"},
        )
        assert response.status_code == 200
        body = await response.get_json()
        assert body == {"echoed": "hello", "tenant": "acme-corp"}

    async def test_echo_missing_required_field_is_400(self, client: Any, auth_headers: Any) -> None:
        """quart-schema's @validate_request rejects a body missing `message`."""
        response = await client.post(
            "/core/platform/default/echo",
            headers=auth_headers(scope="platform:write"),
            json={},
        )
        assert response.status_code == 400
