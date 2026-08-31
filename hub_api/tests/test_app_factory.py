"""`app.create_app()` boots end-to-end -- DAL init, health, MCP, v1/v2 routers, OpenAPI.

Uses `async with app.test_app():` so Quart actually runs the
`before_serving`/`after_serving` hooks (`app.py::startup`/`shutdown`),
not just registers routes -- the same hooks hypercorn triggers in
production. `sqlite:memory` (matching `tests/conftest.py::tenant_db` and
every `libs/flask_core` DB fixture) stands in for the real Postgres
`DATABASE_URL` so this test has no external dependency.
"""

from __future__ import annotations

from typing import Any

import pytest
from quart import Quart

from app import create_app
from config import HubAPIConfig


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
        log_level="INFO",
    )


@pytest.fixture
def app() -> Quart:
    return create_app(_test_config())


class TestAppFactoryBoots:
    async def test_startup_and_shutdown_hooks_run_cleanly(self, app: Quart) -> None:
        async with app.test_app():
            client = app.test_client()
            response = await client.get("/health")
            assert response.status_code == 200

    async def test_dal_is_bound_after_startup(self, app: Quart) -> None:
        async with app.test_app():
            assert app.config.get("dal") is not None
            assert app.config.get("async_dal") is not None


class TestHealthEndpoint:
    async def test_health_returns_200_and_module_name(self, app: Quart) -> None:
        async with app.test_app():
            client = app.test_client()
            response = await client.get("/health")
            assert response.status_code == 200
            body: dict[str, Any] = await response.get_json()
            assert body["module"] == "hub-api-test"
            assert body["status"] == "healthy"

    async def test_healthz_returns_200(self, app: Quart) -> None:
        async with app.test_app():
            client = app.test_client()
            response = await client.get("/healthz")
            assert response.status_code == 200


class TestVersionedRoutersMounted:
    async def test_v1_login_stub_reachable(self, app: Quart) -> None:
        """v1 frozen router mounted -- the M1 placeholder answers (501), not 404."""
        async with app.test_app():
            client = app.test_client()
            response = await client.post("/api/v1/auth/login", json={})
            assert response.status_code == 501

    async def test_v2_platform_example_reachable_but_gated(self, app: Quart) -> None:
        """v2 additive router mounted -- reaches tenant_middleware (401), not 404."""
        async with app.test_app():
            client = app.test_client()
            response = await client.get("/api/v2/core/platform/default/status")
            assert response.status_code == 401
