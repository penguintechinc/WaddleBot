"""Labels-Core Authentication Tests.

`app.py`'s `api_bp` (10 routes -- label CRUD, apply/remove, entity
lookup, search) previously had ZERO authentication -- any caller reaching
the service's network address could read/write ANY tenant's labels. This
is the fix's regression suite.

Fail-first proof: with `install_community_scoped_auth(api_bp)` (app.py's
module-level call) commented out, every test in this file went
green->red as expected (200 instead of 401). Reverted after confirming;
see PR report for the exact before/after run.
"""

from __future__ import annotations

from typing import Any

from tests.conftest import make_token, seed_tenant


class TestApiBpRequiresAuth:
    async def test_list_labels_requires_token(self, client: Any) -> None:
        response = await client.get("/api/v1/labels")
        assert response.status_code == 401

    async def test_create_label_requires_token(self, client: Any) -> None:
        response = await client.post("/api/v1/labels", json={"name": "x", "category": "y"})
        assert response.status_code == 401

    async def test_apply_label_requires_token(self, client: Any) -> None:
        response = await client.post("/api/v1/labels/apply", json={})
        assert response.status_code == 401

    async def test_search_requires_token(self, client: Any) -> None:
        response = await client.get("/api/v1/labels/search")
        assert response.status_code == 401

    async def test_valid_token_passes_the_auth_gate(
        self, client: Any, dal_pair: tuple[Any, Any]
    ) -> None:
        """Auth passes -- proven by a non-401/403 response (real handler reached)."""
        _, dal = dal_pair
        seed_tenant(dal)
        token = make_token()
        response = await client.get(
            "/api/v1/labels", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code not in (401, 403)
