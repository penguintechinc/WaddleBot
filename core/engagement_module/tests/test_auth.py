"""Engagement-Module Authentication Tests.

`app.py` registers routes directly on `app` (no `Blueprint`). GET routes
(`/api/v1/polls/community/<community_id>`, `/api/v1/forms/community/
<community_id>`, and single-item lookups) had ZERO authentication, and
the module-local `require_auth` decorator on write routes referenced
`config.JWT_SECRET_KEY` -- an attribute never defined on `Config` --
crashing with `AttributeError` on every call before ever checking a
token. This is the fix's regression suite.

Fail-first proof: with `install_community_scoped_auth(app, ...)` (app.py's
module-level call) commented out, `test_community_polls_requires_token`
and `test_non_member_community_polls_is_403` both went green->red as
expected (200 instead of 401/403). Reverted after confirming; see PR
report for the exact before/after run.
"""

from __future__ import annotations

from typing import Any

from tests.conftest import make_token, seed_tenant


class TestHealthStaysExempt:
    async def test_health_needs_no_token(self, client: Any) -> None:
        response = await client.get("/health")
        assert response.status_code == 200


class TestApiRoutesRequireAuth:
    async def test_community_polls_requires_token(self, client: Any) -> None:
        response = await client.get("/api/v1/polls/community/1")
        assert response.status_code == 401

    async def test_community_forms_requires_token(self, client: Any) -> None:
        response = await client.get("/api/v1/forms/community/1")
        assert response.status_code == 401

    async def test_create_poll_requires_token(self, client: Any) -> None:
        response = await client.post("/api/v1/polls", json={})
        assert response.status_code == 401

    async def test_non_member_community_polls_is_403(
        self, client: Any, app_db: Any
    ) -> None:
        """BOLA case: valid tenant JWT, but not a member of the target community."""
        seed_tenant(app_db)
        token = make_token(sub="999")
        response = await client.get(
            "/api/v1/polls/community/1", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403

    async def test_member_passes_the_auth_gate(self, client: Any, app_db: Any) -> None:
        tenant_id = seed_tenant(app_db)
        community_id = app_db.communities.insert(tenant_id=tenant_id)
        app_db.community_members.insert(
            community_id=community_id, user_id="1", role="member", is_active=True
        )
        app_db.commit()
        token = make_token(sub="1")
        response = await client.get(
            f"/api/v1/polls/community/{community_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code not in (401, 403)
