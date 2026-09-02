"""Security regression tests for `core/ai_researcher_module/app.py`.

Closes two HIGH findings on this module:

- CORS wildcard (A05/A01): `app = cors(app, allow_origin="*")` let any
  site's browser JS read this service's responses. Now a configured exact-
  origin allowlist (`Config.CORS_ALLOWED_ORIGINS`) -- see
  `test_disallowed_origin_gets_no_cors_header`/
  `test_allowed_origin_gets_echoed_cors_header` for the red->green proof.
- No auth on the game/patch/build/tech/price/clip-research/event-lookup
  sub-blueprints (A01): these routes have neither `@auth_required` (added
  by a sibling PR to 17 *other* routes -- see `test_auth_required.py`) nor
  the pre-existing `X-Service-Key` internal-service gate.
  `app.py::_require_service_key` is now a global `before_request` hook
  covering every route except `/health`/`/healthz`/`/api/v1/status`/CORS
  preflight -- see `test_unauthenticated_request_is_rejected`/
  `test_wrong_service_key_is_rejected`.

Deliberately does NOT re-test the 17 `@auth_required` routes -- that's
`test_auth_required.py`'s job. What this file *does* prove about the
overlap: `_require_service_key` accepts a valid bearer JWT as an
alternative to `X-Service-Key` (`test_valid_jwt_alone_passes_the_blanket_gate`)
specifically so it doesn't 401 those 17 routes' real JWT-authenticated
callers before `@auth_required` ever gets a chance to run, and `/api/v1/
status` is explicitly exempt here too, matching `test_auth_required.py::
TestUnaffectedRoutesStillWork::test_status_endpoint_is_still_public`'s own
assertion that route is deliberately public.

`conftest.py` (this directory) sets `SECRET_KEY` and inserts the module
root onto `sys.path`; the parent directory's `conftest.py` (loaded first,
as an ancestor) sets `SERVICE_API_KEY`/`CORS_ALLOWED_ORIGINS` and imports
`flask_core` before anything else can shadow it. Tests use the plain
`app.test_client()` (never `app.test_app()`) so `@app.before_serving`
(`init_database()` against a real Postgres `DATABASE_URL`) never runs --
the before_request/after_request hooks under test fire on every request
regardless of app lifespan.
"""

from __future__ import annotations

import app as app_module
import pytest
from flask_core.auth import create_jwt_token

from config import Config

_ALLOWED_ORIGIN = "https://allowed.example.com"
_DISALLOWED_ORIGIN = "https://evil.example.com"
_VALID_KEY_HEADERS = {"X-Service-Key": Config.SERVICE_API_KEY}
#: A route with neither `@auth_required` nor an inline `X-Service-Key`
#: check of its own -- the sub-blueprints `_require_service_key` alone
#: still protects (see module docstring).
_UNPROTECTED_SUB_BLUEPRINT_ROUTE = "/api/v1/game/status"


def _bearer_jwt_headers() -> dict[str, str]:
    token = create_jwt_token(
        user_id="1", username="alice", email="alice@example.com",
        roles=[], secret_key=Config.SECRET_KEY, tenant="acme-corp",
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def client():
    """The module's real Quart app, test client only -- no `before_serving` DB init."""
    return app_module.app.test_client()


class TestCorsAllowlist:
    """`allow_origin` is `Config.CORS_ALLOWED_ORIGINS`, never `"*"`."""

    @pytest.mark.asyncio
    async def test_disallowed_origin_gets_no_cors_header(self, client) -> None:
        """A non-allowlisted Origin gets no `Access-Control-Allow-Origin` -- browser blocks it."""
        response = await client.get(
            "/health", headers={"Origin": _DISALLOWED_ORIGIN, **_VALID_KEY_HEADERS}
        )
        assert response.status_code == 200
        assert "Access-Control-Allow-Origin" not in response.headers

    @pytest.mark.asyncio
    async def test_allowed_origin_gets_echoed_cors_header(self, client) -> None:
        """The configured allowlisted Origin is echoed back -- browser permits the read."""
        response = await client.get(
            "/health", headers={"Origin": _ALLOWED_ORIGIN, **_VALID_KEY_HEADERS}
        )
        assert response.status_code == 200
        assert response.headers["Access-Control-Allow-Origin"] == _ALLOWED_ORIGIN

    @pytest.mark.asyncio
    async def test_wildcard_is_never_sent(self, client) -> None:
        """Regression proof for the specific bug: `Access-Control-Allow-Origin: *` never appears."""
        response = await client.get(
            "/health", headers={"Origin": _ALLOWED_ORIGIN, **_VALID_KEY_HEADERS}
        )
        assert response.headers.get("Access-Control-Allow-Origin") != "*"


class TestGlobalAuthGate:
    """`_require_service_key` covers every route the `@auth_required` fix didn't reach."""

    @pytest.mark.asyncio
    async def test_unauthenticated_request_is_rejected(self, client) -> None:
        """No credential at all on a still-open sub-blueprint route -- 401, handler never runs."""
        response = await client.get(_UNPROTECTED_SUB_BLUEPRINT_ROUTE)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_wrong_service_key_is_rejected(self, client) -> None:
        """An incorrect key (and no JWT either) is rejected exactly like no credential at all."""
        response = await client.get(
            _UNPROTECTED_SUB_BLUEPRINT_ROUTE, headers={"X-Service-Key": "not-the-key"}
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_valid_service_key_passes_the_blanket_gate(self, client) -> None:
        response = await client.get(_UNPROTECTED_SUB_BLUEPRINT_ROUTE, headers=_VALID_KEY_HEADERS)
        assert response.status_code != 401

    @pytest.mark.asyncio
    async def test_valid_jwt_alone_passes_the_blanket_gate(self, client) -> None:
        """A real user JWT (no `X-Service-Key` at all) is also accepted -- not service-key-only.

        This is the specific fix needed to coexist with the sibling PR's
        `@auth_required` on 17 other routes: those routes' real callers
        carry a JWT, never an internal service key, and this hook runs
        before `@auth_required` ever does.
        """
        response = await client.get(_UNPROTECTED_SUB_BLUEPRINT_ROUTE, headers=_bearer_jwt_headers())
        assert response.status_code != 401

    @pytest.mark.asyncio
    async def test_health_is_exempt_from_the_auth_gate(self, client) -> None:
        """K8s liveness/readiness probes never carry any credential -- `/health` stays open."""
        response = await client.get("/health")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_healthz_is_exempt_from_the_auth_gate(self, client) -> None:
        response = await client.get("/healthz")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_status_is_exempt_from_the_blanket_gate(self, client) -> None:
        """`/api/v1/status` stays public -- matches `test_auth_required.py`'s own assertion."""
        response = await client.get("/api/v1/status")
        assert response.status_code != 401

    @pytest.mark.asyncio
    async def test_cors_preflight_is_exempt_from_the_auth_gate(self, client) -> None:
        """A real browser preflight never carries a credential -- must not 401."""
        response = await client.options(
            _UNPROTECTED_SUB_BLUEPRINT_ROUTE,
            headers={
                "Origin": _ALLOWED_ORIGIN,
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code != 401


class TestSecurityHeaders:
    """`install_security_headers(app)` is wired in alongside the CORS/auth fixes."""

    @pytest.mark.asyncio
    async def test_response_carries_the_security_header_baseline(self, client) -> None:
        response = await client.get("/health")
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["Referrer-Policy"] == "no-referrer"
        assert "Content-Security-Policy" in response.headers
