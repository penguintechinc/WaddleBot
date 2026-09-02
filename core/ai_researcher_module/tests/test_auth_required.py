"""Every previously-unauthenticated `ai_researcher_module` route now requires a bearer JWT.

Security review (46 routes, flagged "un-reviewed"): every route below had
NO authentication decorator at all -- any caller reaching this service's
network address could trigger AI research/insight generation, read
per-user behavior profiles, read/write admin config, and acknowledge
anomalies, all by supplying `community_id`/`user_id`/`admin_id` directly in
the request with zero identity verification. Fixed by adding
`flask_core.auth_required` (already a dependency of this file, already
used platform-wide) to each -- the `/api/v1/status` route and the two
`X-Service-Key`-gated internal routes (`/messages/firehose`, `/stream/end`)
are deliberately left as-is (public status, and service-to-service auth is
its own equivalent mechanism, not a per-user JWT).

Fail-first proof (executed, not narrated): with `@auth_required` removed
from `get_context` (this suite's canary), `test_previously_unauthenticated_
routes_now_require_a_token[...get_context...]` went green -> red as
expected (200 instead of 401); restored, green.

Deliberately does NOT run `@app.before_serving` (`async with app.test_app()`)
-- `startup()` connects to a real Postgres DB, Redis, and SearXNG, none of
which belong in this unit test. `@auth_required` runs before any of that
matters (outermost decorator on every route below), so a bare
`test_client()` request is sufficient to prove the gate is in place.
"""

from __future__ import annotations

import os

import pytest
from flask_core.auth import create_jwt_token
from quart import Quart

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ai-researcher-module-tests")

import app as ai_researcher_app_module  # noqa: E402

SECRET = os.environ["SECRET_KEY"]

#: (method, path) for every route this PR added `@auth_required` to.
PROTECTED_ROUTES: list[tuple[str, str]] = [
    ("POST", "/api/v1/researcher/research"),
    ("POST", "/api/v1/researcher/ask"),
    ("POST", "/api/v1/researcher/recall"),
    ("POST", "/api/v1/researcher/summarize"),
    ("GET", "/api/v1/researcher/context/1"),
    ("GET", "/api/v1/researcher/memory/1"),
    ("GET", "/api/v1/admin/1/ai-insights"),
    ("GET", "/api/v1/admin/1/ai-researcher/config"),
    ("PUT", "/api/v1/admin/1/ai-researcher/config"),
    ("GET", "/api/v1/researcher/1/insights"),
    ("POST", "/api/v1/researcher/1/insights/generate"),
    ("GET", "/api/v1/researcher/1/anomalies"),
    ("POST", "/api/v1/researcher/1/anomalies/1/acknowledge"),
    ("GET", "/api/v1/researcher/1/sentiment"),
    ("GET", "/api/v1/researcher/1/user/twitch/u1/profile"),
    ("GET", "/api/v1/researcher/1/users/profiles"),
    ("GET", "/api/v1/admin/1/bot-detection"),
]


def _token() -> str:
    return create_jwt_token(
        user_id="1", username="alice", email="alice@example.com",
        roles=[], secret_key=SECRET, tenant="acme-corp",
    )


@pytest.fixture
def app() -> Quart:
    return ai_researcher_app_module.app


class TestPreviouslyUnauthenticatedRoutesNowRequireAToken:
    @pytest.mark.parametrize("method,path", PROTECTED_ROUTES)
    async def test_no_token_is_401(self, app: Quart, method: str, path: str) -> None:
        client = app.test_client()
        response = await client.open(path, method=method, json={})
        assert response.status_code == 401

    @pytest.mark.parametrize("method,path", PROTECTED_ROUTES)
    async def test_invalid_token_is_401(self, app: Quart, method: str, path: str) -> None:
        client = app.test_client()
        response = await client.open(
            path, method=method, json={}, headers={"Authorization": "Bearer not-a-real-token"}
        )
        assert response.status_code == 401

    async def test_valid_token_passes_the_auth_gate(self, app: Quart) -> None:
        """A valid token gets PAST `@auth_required` -- whatever happens next (dal unset -> 500
        without `startup()` having run) is a different, unrelated failure mode, not 401.
        """
        client = app.test_client()
        response = await client.get(
            "/api/v1/researcher/context/1",
            headers={"Authorization": f"Bearer {_token()}"},
        )
        assert response.status_code != 401


class TestUnaffectedRoutesStillWork:
    async def test_status_endpoint_is_still_public(self, app: Quart) -> None:
        """Not 401 -- `/status` was never gated and this PR doesn't change that.

        (Not asserting 200: this test environment hits an unrelated
        pre-existing `Config.BOT_DETECTION_ENABLED` AttributeError inside
        the handler body, out of scope for this auth-only fix -- the only
        thing under test here is that no auth gate was added.)
        """
        client = app.test_client()
        response = await client.get("/api/v1/status")
        assert response.status_code != 401

    async def test_firehose_still_uses_service_key_not_auth_required(self, app: Quart) -> None:
        """Deliberately untouched -- service-to-service auth via `X-Service-Key`, not a user JWT."""
        client = app.test_client()
        response = await client.post("/api/v1/researcher/messages/firehose", json={})
        assert response.status_code == 401
        body = await response.get_json()
        assert body["success"] is False
        assert body["error"]["message"] == "Unauthorized"
