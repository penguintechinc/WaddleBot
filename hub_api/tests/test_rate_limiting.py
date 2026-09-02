"""`services/rate_limiting.py`'s global `before_request` hook -- gh security-review C5.

Boots the real `app.create_app()` (matching `tests/test_app_factory.py`'s
own `async with app.test_app():` pattern, the same `before_serving`/
`after_serving` hooks hypercorn triggers in production) with tiny,
explicit `rate_limit_*` config values so a handful of requests is enough
to trip the limit deterministically -- no `sleep()`, no timing races.

Fail-first proof (executed, not narrated): with
`services.rate_limiting.install_rate_limiting(app, cfg)`'s call site in
`app.py::create_app()` commented out, `test_standard_tier_returns_429_
after_limit_exceeded` and `test_auth_tier_has_its_own_stricter_limit`
both went red (6th/4th request returned 401/400 instead of 429 -- the
exact "449 endpoints, zero effective rate limiting" gap this PR fixes);
restored, green again.
"""

from __future__ import annotations

from typing import Any

import pytest
from quart import Quart

from app import create_app
from config import HubAPIConfig


def _test_config(**overrides: Any) -> HubAPIConfig:
    base: dict[str, Any] = {
        "module_name": "hub-api-test",
        "module_version": "0.0.0-test",
        "module_port": 8204,
        "grpc_port": 50204,
        "database_url": "sqlite:memory",
        "database_read_replica_url": None,
        "db_pool_size": 1,
        "db_max_retries": 1,
        "db_retry_delay": 1,
        "secret_key": "change-me-in-production",
        "jwt_algorithm": "HS256",
        "default_tenant_slug": "global",
        "posthog_api_key": None,
        "posthog_host": "https://license.penguintech.io",
        "license_server_url": "https://license.penguintech.io",
        "identity_callback_base_url": "http://localhost:8204",
        "frontend_origin": "http://localhost:5173",
        "log_level": "INFO",
        # No REDIS_URL/VALKEY_URL reachable in the test sandbox --
        # RateLimiter.connect() fails open to its in-memory fallback
        # (flask_core/rate_limiter.py's own documented behavior), which
        # is exactly what these tests exercise: the sliding window still
        # enforces correctly with no real Redis present.
        "valkey_url": "redis://unreachable-in-tests.invalid:6379/0",
    }
    base.update(overrides)
    return HubAPIConfig(**base)


@pytest.fixture
def app_standard_tier() -> Quart:
    """Standard tier tight (3 req/60s); auth tier left generous so it doesn't interfere."""
    return create_app(
        _test_config(
            rate_limit_max_requests=3,
            rate_limit_window_seconds=60,
            rate_limit_auth_max_requests=1000,
            rate_limit_auth_window_seconds=60,
        )
    )


@pytest.fixture
def app_auth_tier() -> Quart:
    """Auth tier tight (2 req/60s); standard tier left generous so it doesn't interfere."""
    return create_app(
        _test_config(
            rate_limit_max_requests=1000,
            rate_limit_window_seconds=60,
            rate_limit_auth_max_requests=2,
            rate_limit_auth_window_seconds=60,
        )
    )


class TestStandardTier:
    async def test_standard_tier_returns_429_after_limit_exceeded(
        self, app_standard_tier: Quart
    ) -> None:
        """3 allowed (401, unauthenticated) -- the 4th on the same bucket is 429."""
        async with app_standard_tier.test_app():
            client = app_standard_tier.test_client()
            statuses = []
            for _ in range(4):
                response = await client.get("/api/v2/core/platform/default/status")
                statuses.append(response.status_code)

            assert statuses[:3] == [401, 401, 401]
            assert statuses[3] == 429

    async def test_429_response_has_retry_after_header_and_shared_error_shape(
        self, app_standard_tier: Quart
    ) -> None:
        async with app_standard_tier.test_app():
            client = app_standard_tier.test_client()
            for _ in range(3):
                await client.get("/api/v2/core/platform/default/status")
            response = await client.get("/api/v2/core/platform/default/status")

            assert response.status_code == 429
            assert response.headers.get("Retry-After") == "60"
            body: dict[str, Any] = await response.get_json()
            assert body["success"] is False
            assert body["error"]["code"] == "RATE_LIMIT_EXCEEDED"

    async def test_health_endpoint_is_exempt_from_rate_limiting(
        self, app_standard_tier: Quart
    ) -> None:
        """`/health` must never 429 -- K8s liveness/readiness depend on it."""
        async with app_standard_tier.test_app():
            client = app_standard_tier.test_client()
            for _ in range(10):
                response = await client.get("/health")
                assert response.status_code == 200


class TestAuthTierIsStricter:
    async def test_auth_tier_has_its_own_stricter_limit(self, app_auth_tier: Quart) -> None:
        """2 allowed (400, empty body) on /api/v1/auth/login -- the 3rd is 429."""
        async with app_auth_tier.test_app():
            client = app_auth_tier.test_client()
            statuses = []
            for _ in range(3):
                response = await client.post("/api/v1/auth/login", json={})
                statuses.append(response.status_code)

            assert statuses[:2] == [400, 400]
            assert statuses[2] == 429

    async def test_auth_tier_bucket_is_independent_of_standard_tier_bucket(
        self, app_auth_tier: Quart
    ) -> None:
        """Exhausting the (tight) auth-tier bucket doesn't touch the (loose) standard tier."""
        async with app_auth_tier.test_app():
            client = app_auth_tier.test_client()
            for _ in range(3):
                await client.post("/api/v1/auth/login", json={})

            # Auth tier is now exhausted for this client...
            exhausted = await client.post("/api/v1/auth/login", json={})
            assert exhausted.status_code == 429

            # ...but a standard-tier route from the same client is unaffected.
            standard = await client.get("/api/v2/core/platform/default/status")
            assert standard.status_code == 401
