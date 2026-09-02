"""Authentication tests for the credential-manager `/api/v1/credentials/*` routes.

`app.py`'s `credential_status` (`GET /api/v1/credentials/status`) and
`force_refresh` (`POST /api/v1/credentials/refresh-now`) previously had
ZERO authentication -- any caller reaching the service's network address
could enumerate every tracked OAuth integration's refresh state, or
trigger refresh cycles (and their downstream rate-limit/quota
consumption) at will. This is the fix's regression suite.

These routes are platform-admin, not tenant/community-scoped (this
service manages OAuth credentials via `asyncpg`, no pydal `dal`), so only
`require_scope("credentials:admin")` is exercised here -- no
`tenant_middleware`/DB fixtures needed, matching `app.py`'s own
docstring rationale. `refresh_service` is intentionally left `None` (no
`app.test_app()` lifecycle, no real `asyncpg`/Redis connections) --
requests that clear the auth gate hit the `if not refresh_service` guard
and return 503, which is exactly how this suite proves the auth layer
opened without needing real infrastructure: 401/403 (blocked) vs. 503
(blocked by nothing except missing test infra) are unambiguously
distinct outcomes.

Fail-first proof: with both `@require_scope("credentials:admin")`
decorators temporarily removed, `test_status_requires_token`,
`test_status_requires_correct_scope`, `test_refresh_now_requires_token`,
and `test_refresh_now_requires_correct_scope` all went green->red as
expected (503 instead of 401/403 -- reaching the handler with no auth at
all). Reverted after confirming; see PR report for the exact before/after
run.
"""

from __future__ import annotations

import os
from typing import Any

import pytest
from flask_core.auth import create_jwt_token

os.environ.setdefault("DATABASE_URL", "postgresql://u:p@localhost:5432/db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

from .app import app  # noqa: E402 - env vars must be set before Config is imported

SECRET = "change-me-in-production"


def _token(scope: str = "") -> str:
    return create_jwt_token(
        user_id="1",
        username="alice",
        email="alice@example.com",
        roles=[],
        secret_key=SECRET,
        tenant="acme-corp",
        scope=scope,
    )


@pytest.fixture
def client() -> Any:
    return app.test_client()


class TestCredentialStatusAuth:
    async def test_status_requires_token(self, client: Any) -> None:
        response = await client.get("/api/v1/credentials/status")
        assert response.status_code == 403

    async def test_status_requires_correct_scope(self, client: Any) -> None:
        token = _token(scope="widgets:read")
        response = await client.get(
            "/api/v1/credentials/status", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403

    async def test_status_with_admin_scope_reaches_handler(self, client: Any) -> None:
        """Auth passes; 503 (`refresh_service` not started in this test) proves it opened."""
        token = _token(scope="credentials:admin")
        response = await client.get(
            "/api/v1/credentials/status", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 503

    async def test_status_with_global_wildcard_admin_passes(self, client: Any) -> None:
        """`*:admin` (SCOPE_BUNDLES global.admin) covers `credentials:admin`."""
        token = _token(scope="*:admin")
        response = await client.get(
            "/api/v1/credentials/status", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 503


class TestForceRefreshAuth:
    async def test_refresh_now_requires_token(self, client: Any) -> None:
        response = await client.post("/api/v1/credentials/refresh-now")
        assert response.status_code == 403

    async def test_refresh_now_requires_correct_scope(self, client: Any) -> None:
        token = _token(scope="widgets:write")
        response = await client.post(
            "/api/v1/credentials/refresh-now", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403

    async def test_refresh_now_with_admin_scope_reaches_handler(self, client: Any) -> None:
        token = _token(scope="credentials:admin")
        response = await client.post(
            "/api/v1/credentials/refresh-now", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 503


class TestHealthRemainsPublic:
    async def test_health_needs_no_token(self, client: Any) -> None:
        """Health checks stay unauthenticated -- K8s liveness/readiness probes."""
        response = await client.get("/health")
        assert response.status_code in (200, 503)
