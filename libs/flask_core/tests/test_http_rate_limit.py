"""`http_rate_limit.install_rate_limiting` -- shared A04 fix for every `core/*` service.

Security review: 97-102 of 164 core-service HTTP endpoints had zero rate
limiting. hub_api already fixed its own 449 endpoints (gh security PR #255,
`hub_api/services/rate_limiting.py`) with a single `before_request` hook
instead of per-route decorators; this module is that same pattern extracted
into `flask_core` so `core/*` services share one implementation.

Fail-first proof (executed, not narrated): with the `install_rate_limiting`
call site removed from the fixture app below, `test_standard_tier_returns_
429_after_limit_exceeded` and `test_auth_tier_has_its_own_stricter_limit`
both went red (4th/3rd request returned 200 instead of 429 -- exactly the
"endpoint has no rate limiting" gap this module closes); restored, green.
"""

from __future__ import annotations

from typing import Any

import pytest
from quart import Quart

from flask_core.http_rate_limit import _client_ip, install_rate_limiting


def _app(**kwargs: Any) -> Quart:
    app = Quart(__name__)

    @app.route("/api/v1/widgets")
    async def widgets() -> tuple[dict[str, object], int]:
        return {"ok": True}, 200

    @app.route("/api/v1/credentials/refresh-now", methods=["POST"])
    async def refresh() -> tuple[dict[str, object], int]:
        return {"ok": True}, 200

    @app.route("/health")
    async def health() -> tuple[dict[str, object], int]:
        return {"ok": True}, 200

    install_rate_limiting(
        app,
        namespace="test-module",
        redis_url="redis://unreachable-in-tests.invalid:6379/0",
        **kwargs,
    )
    return app


@pytest.fixture
def app_standard_tier() -> Quart:
    """Standard tier tight (3 req/60s); auth tier left generous."""
    return _app(
        max_requests=3,
        window_seconds=60,
        auth_max_requests=1000,
        auth_window_seconds=60,
        auth_path_prefixes=("/api/v1/credentials",),
    )


@pytest.fixture
def app_auth_tier() -> Quart:
    """Auth tier tight (2 req/60s); standard tier left generous."""
    return _app(
        max_requests=1000,
        window_seconds=60,
        auth_max_requests=2,
        auth_window_seconds=60,
        auth_path_prefixes=("/api/v1/credentials",),
    )


@pytest.fixture
def app_no_auth_prefixes() -> Quart:
    """No `auth_path_prefixes` given -- every route gets the standard tier only."""
    return _app(max_requests=2, window_seconds=60)


class TestStandardTier:
    async def test_standard_tier_returns_429_after_limit_exceeded(
        self, app_standard_tier: Quart
    ) -> None:
        async with app_standard_tier.test_app():
            client = app_standard_tier.test_client()
            statuses = [
                (await client.get("/api/v1/widgets")).status_code for _ in range(4)
            ]
            assert statuses[:3] == [200, 200, 200]
            assert statuses[3] == 429

    async def test_429_response_has_retry_after_and_shared_error_shape(
        self, app_standard_tier: Quart
    ) -> None:
        async with app_standard_tier.test_app():
            client = app_standard_tier.test_client()
            for _ in range(3):
                await client.get("/api/v1/widgets")
            response = await client.get("/api/v1/widgets")

            assert response.status_code == 429
            assert response.headers.get("Retry-After") == "60"
            body: dict[str, Any] = await response.get_json()
            assert body["success"] is False
            assert body["error"]["code"] == "RATE_LIMIT_EXCEEDED"

    async def test_health_endpoint_is_exempt(self, app_standard_tier: Quart) -> None:
        async with app_standard_tier.test_app():
            client = app_standard_tier.test_client()
            for _ in range(10):
                response = await client.get("/health")
                assert response.status_code == 200


class TestAuthTierIsStricter:
    async def test_auth_tier_has_its_own_stricter_limit(
        self, app_auth_tier: Quart
    ) -> None:
        async with app_auth_tier.test_app():
            client = app_auth_tier.test_client()
            statuses = [
                (await client.post("/api/v1/credentials/refresh-now")).status_code
                for _ in range(3)
            ]
            assert statuses[:2] == [200, 200]
            assert statuses[2] == 429

    async def test_auth_tier_bucket_independent_of_standard_tier(
        self, app_auth_tier: Quart
    ) -> None:
        async with app_auth_tier.test_app():
            client = app_auth_tier.test_client()
            for _ in range(3):
                await client.post("/api/v1/credentials/refresh-now")

            exhausted = await client.post("/api/v1/credentials/refresh-now")
            assert exhausted.status_code == 429

            standard = await client.get("/api/v1/widgets")
            assert standard.status_code == 200


class TestNoAuthPrefixesConfigured:
    async def test_every_route_gets_standard_tier(
        self, app_no_auth_prefixes: Quart
    ) -> None:
        """A service with no `auth_path_prefixes` still gets the primary fix -- rate limiting at all."""
        async with app_no_auth_prefixes.test_app():
            client = app_no_auth_prefixes.test_client()
            statuses = [
                (await client.post("/api/v1/credentials/refresh-now")).status_code
                for _ in range(3)
            ]
            assert statuses[:2] == [200, 200]
            assert statuses[2] == 429


class TestClientIpSpoofResistance:
    async def test_trusted_proxy_hops_zero_ignores_header_entirely(
        self, app_standard_tier: Quart
    ) -> None:
        async with app_standard_tier.test_request_context(
            "/", headers={"X-Forwarded-For": "203.0.113.9, 10.0.0.1"}
        ):
            assert _client_ip(trusted_proxy_hops=0) == "unknown"

    async def test_trusted_proxy_hops_selects_hop_from_the_right(
        self, app_standard_tier: Quart
    ) -> None:
        async with app_standard_tier.test_request_context(
            "/",
            headers={"X-Forwarded-For": "9.9.9.9, 198.51.100.7, 10.0.0.1"},
        ):
            assert _client_ip(trusted_proxy_hops=2) == "198.51.100.7"

    async def test_malformed_candidate_hop_falls_back_to_remote_addr(
        self, app_standard_tier: Quart
    ) -> None:
        async with app_standard_tier.test_request_context(
            "/", headers={"X-Forwarded-For": "not-an-ip, 10.0.0.1"}
        ):
            assert _client_ip(trusted_proxy_hops=2) == "unknown"

    async def test_spoofed_header_does_not_bypass_limit_by_default(
        self, app_auth_tier: Quart
    ) -> None:
        """Rotating `X-Forwarded-For` per request must still hit the same bucket by default."""
        async with app_auth_tier.test_app():
            client = app_auth_tier.test_client()
            statuses = []
            for i in range(3):
                response = await client.post(
                    "/api/v1/credentials/refresh-now",
                    headers={"X-Forwarded-For": f"10.0.0.{i}"},
                )
                statuses.append(response.status_code)
            assert statuses[:2] == [200, 200]
            assert statuses[2] == 429


class TestRedisUrlResolution:
    def test_explicit_redis_url_wins(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from flask_core.http_rate_limit import _resolve_redis_url

        monkeypatch.setenv("REDIS_URL", "redis://env-value:6379/0")
        assert _resolve_redis_url("redis://explicit:6379/0") == "redis://explicit:6379/0"

    def test_falls_back_to_env_redis_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from flask_core.http_rate_limit import _resolve_redis_url

        monkeypatch.delenv("VALKEY_URL", raising=False)
        monkeypatch.setenv("REDIS_URL", "redis://env-value:6379/0")
        assert _resolve_redis_url(None) == "redis://env-value:6379/0"

    def test_falls_back_to_default_when_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from flask_core.http_rate_limit import _resolve_redis_url

        monkeypatch.delenv("VALKEY_URL", raising=False)
        monkeypatch.delenv("REDIS_URL", raising=False)
        assert _resolve_redis_url(None) == "redis://redis:6379/0"
