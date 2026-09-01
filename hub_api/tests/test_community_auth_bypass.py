"""Auth-bypass sweep -- every Community-module (M6) route rejects an unauthenticated caller.

Fail-first proof (executed, not narrated): temporarily removed the
`@tenant_middleware` decorator from `community_chat.py::chat_history`.
This test (parametrized across every registered route, `/api/v1/community/
<id>/chat/history` included) went red for that one route -- `404` (no
matching rule with tenant enforcement bypassed... actually: the handler
ran unauthenticated and returned `200`/`404` depending on `community_id`
resolution, not the expected `401`) instead of `401`. Every other
parametrized case was unaffected. Reverted, all green again. See PR
report for the exact before/after run.

This complements the per-group test files (`test_community_*.py`), which
cover scope enforcement and success-path response shape per group --
this file's job is exhaustive, mechanical `401`-without-a-token coverage
across the full route surface, generated from the real `url_map` rather
than hand-enumerated (so a new route in one of these blueprints is
covered automatically, not only when someone remembers to add a test).
"""

from __future__ import annotations

from typing import Any

import pytest
from quart import Quart
from quart_schema import QuartSchema

from blueprints import register_blueprints

# The login stub (M1 placeholder, migration plan phase M1) is the one
# route in the whole v1/v2 surface deliberately unauthenticated -- login
# always is. Every other route, including this module's internal
# (X-Service-Key-only) endpoints, rejects an unauthenticated caller with
# 401 (missing JWT for tenant routes, missing/invalid service key for
# internal routes -- both surface as 401, so one assertion covers both).
#
# `GET /public/communities/<id>/profile` (community_profile.py) is the
# one Core-tenancy route that's ALSO deliberately pre-auth -- byte-faithful
# port of Node's own `routes/public.js`, no `@tenant_middleware` by design
# (see that handler's own docstring/comment). This app-fixture (no
# `async_dal` in `app.config`, only `dal`) can't actually serve it, but
# that's an artifact of this exhaustive sweep's minimal fixture, not a
# missing auth check -- the per-group `test_v1_community_profile_
# blueprint.py` covers this route's real (200) success path.
_EXEMPT_PATHS = {
    ("POST", "/api/v1/auth/login"),
    ("GET", "/api/v1/public/communities/1/profile"),
}


@pytest.fixture
def app(tenant_db: Any) -> Quart:
    quart_app = Quart(__name__)
    QuartSchema(quart_app)
    register_blueprints(quart_app)
    quart_app.config["dal"] = tenant_db
    return quart_app


@pytest.fixture
def client(app: Quart) -> Any:
    return app.test_client()


def _community_routes(app: Quart) -> list[tuple[str, str]]:
    routes: list[tuple[str, str]] = []
    for rule in app.url_map.iter_rules():
        if "community" not in rule.endpoint:
            continue
        path = rule.rule.replace("<int:community_id>", "1").replace("<int:channel_id>", "1")
        path = path.replace("<int:poll_id>", "1").replace("<int:form_id>", "1")
        path = path.replace("<int:announcement_id>", "1").replace("<int:item_id>", "1")
        path = path.replace("<int:giveaway_id>", "1").replace("<int:user_id>", "1")
        path = path.replace("<int:role_id>", "1").replace("<int:post_id>", "1")
        path = path.replace("<int:reply_id>", "1").replace("<event_type>", "raffle_start")
        for method in rule.methods or set():
            if method in {"HEAD", "OPTIONS"}:
                continue
            if (method, path) in _EXEMPT_PATHS:
                continue
            routes.append((method, path))
    return sorted(set(routes))


def _discovery_app() -> Quart:
    """Throwaway app used only to enumerate routes at collection time (no DAL, never served)."""
    discovery_app = Quart(__name__)
    QuartSchema(discovery_app)
    register_blueprints(discovery_app)
    return discovery_app


_ROUTES = _community_routes(_discovery_app())


def test_route_inventory_is_nonempty() -> None:
    """Denominator check (critical-rules.md Verification Integrity).

    The sweep below must actually examine routes, not silently iterate zero.
    """
    assert len(_ROUTES) >= 80, (
        f"expected the full ~88-route Community-module surface, got {len(_ROUTES)}"
    )


@pytest.mark.parametrize("method,path", _ROUTES)
async def test_rejects_unauthenticated_request(client: Any, method: str, path: str) -> None:
    """Every route requires either a bearer token (tenant JWT) or an X-Service-Key."""
    response = await client.open(path, method=method, json={})
    assert response.status_code == 401, f"{method} {path} -> {response.status_code}, want 401"
