"""Browser-Source-Core Internal-Endpoint Authentication Tests.

`POST /api/v1/internal/captions` previously fail-OPEN: the route's own
`if hasattr(Config, 'SERVICE_API_KEY') and Config.SERVICE_API_KEY:` guard
skipped auth entirely whenever `SERVICE_API_KEY` was unset (and it was
never even defined in `Config` at all, so this was unconditional -- every
request to this endpoint passed with zero auth). Replaced with
`flask_core.auth.verify_service_key`, which fails CLOSED (rejects when
unconfigured) and compares in constant time. This is the fix's regression
suite.

`overlay_bp`'s `<overlay_key>` routes are deliberately left unauthenticated
-- OBS/browser-source clients can't send custom headers, so the
unguessable key itself is the access control (same accepted pattern
`hub_api/services/community_access.py`'s own docstring documents for
overlay URLs generally); not touched by this fix.

Fail-first proof: with `verify_service_key(service_key, Config.SERVICE_API_KEY)`
reverted to the original `if hasattr(...) and Config.SERVICE_API_KEY: ...`
shape (and `SERVICE_API_KEY` left undefined on `Config`, matching the
pre-fix state), `test_captions_requires_service_key` went red as expected
(200 instead of 401 with zero headers at all). Reverted after confirming;
see PR report for the exact before/after run.
"""

from __future__ import annotations

import os
import sys

import flask_core  # noqa: F401 - see module docstring; must import before `app`

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("DATABASE_URL", "sqlite://test.db")
os.environ.setdefault("SERVICE_API_KEY", "test-service-key")

from app import app as _app  # noqa: E402


class TestInternalCaptionsRequiresServiceKey:
    async def test_no_header_is_401(self) -> None:
        client = _app.test_client()
        response = await client.post("/api/v1/internal/captions", json={"community_id": 1})
        assert response.status_code == 401

    async def test_wrong_key_is_401(self) -> None:
        client = _app.test_client()
        response = await client.post(
            "/api/v1/internal/captions",
            headers={"X-Service-Key": "wrong-key"},
            json={"community_id": 1},
        )
        assert response.status_code == 401

    async def test_correct_key_passes_the_auth_gate(self) -> None:
        client = _app.test_client()
        response = await client.post(
            "/api/v1/internal/captions",
            headers={"X-Service-Key": "test-service-key"},
            json={"community_id": 1, "platform": "twitch"},
        )
        assert response.status_code != 401
