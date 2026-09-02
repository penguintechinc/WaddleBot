"""`controllers/workflow_api.py` -- community/tenant scoping fix (A01, deferred from gh security PR #260).

Fail-first proof (executed, not narrated): with `_authorize_community`'s
body temporarily replaced with `return None` (the pre-fix shape -- any
authenticated user could act on any workflow regardless of community),
`test_get_workflow_cross_tenant_is_403`, `test_get_workflow_non_member_is_
403`, and `test_update_workflow_member_without_admin_is_403` all went green
-> red as expected (200 instead of 403); reverted after confirming.

Every route wires the same `WorkflowService`/`PermissionService` machinery,
which speaks Postgres-only raw SQL (`%s` placeholders, `RETURNING`, etc) --
not testable against sqlite. This suite substitutes a minimal stub
`WorkflowService` (`_FakeWorkflowService`) exercising only what
`_authorize_community` needs (`.dal.executesql()`, pattern-matched) plus
canned returns for the post-authorization service call, so the REAL
`@tenant_middleware`/`@auth_required`/authorization wiring in the actual
blueprint is what's under test -- not a reimplementation of it.
"""

from __future__ import annotations

from typing import Any

import pytest
from pydal import DAL
from quart import Quart

from config import Config
from controllers.workflow_api import register_workflow_api
from flask_core.auth import create_jwt_token
from flask_core.community_access import bind_shared_read_tables

SECRET = Config.SECRET_KEY


def _token(*, sub: str, tenant: str) -> str:
    return create_jwt_token(
        user_id=sub, username=f"user{sub}", email=f"user{sub}@example.com",
        roles=[], secret_key=SECRET, tenant=tenant,
    )


class _FakeAsyncDAL:
    """Runs pydal calls synchronously -- fine for a sqlite:memory unit test."""

    def __init__(self, dal: Any) -> None:
        self.dal = dal

    async def select_async(self, query_set: Any, *fields: Any) -> Any:
        return query_set.select(*fields) if fields else query_set.select()


class _FakeWorkflowDal:
    """Stub for `WorkflowService.dal` -- only `.executesql()` is used by `community_scope.py`."""

    def __init__(self, workflow_community: dict[str, int]) -> None:
        self._workflow_community = workflow_community

    def executesql(self, sql: str, params: list[Any]) -> list[tuple[Any, ...]]:
        assert "SELECT community_id FROM workflows" in sql
        community_id = self._workflow_community.get(params[0])
        return [(community_id,)] if community_id is not None else []


class _FakeWorkflowService:
    """Stub -- only reached once `_authorize_community` has already passed."""

    def __init__(self, dal: _FakeWorkflowDal) -> None:
        self.dal = dal

    async def create_workflow(self, **kwargs: Any) -> dict[str, Any]:
        return {"workflow_id": "wf-new", **kwargs}

    async def get_workflow(self, **kwargs: Any) -> dict[str, Any]:
        return {"workflow_id": kwargs["workflow_id"], "name": "test"}

    async def update_workflow(self, **kwargs: Any) -> dict[str, Any]:
        return {"workflow_id": kwargs["workflow_id"], "name": "updated"}

    async def delete_workflow(self, **kwargs: Any) -> dict[str, Any]:
        return {"workflow_id": kwargs["workflow_id"], "status": "archived"}

    async def publish_workflow(self, **kwargs: Any) -> dict[str, Any]:
        return {"workflow_id": kwargs["workflow_id"], "status": "active"}

    async def validate_workflow(self, **kwargs: Any) -> dict[str, Any]:
        return {
            "is_valid": True, "errors": [], "warnings": [],
            "node_validation_errors": {}, "error_count": 0, "warning_count": 0,
        }

    async def list_workflows(self, **kwargs: Any) -> dict[str, Any]:
        return {"workflows": [], "total": 0, "page": 1, "per_page": 20, "total_pages": 0}


@pytest.fixture
def db() -> Any:
    dal = DAL("sqlite:memory")
    bind_shared_read_tables(dal, migrate=True)
    yield dal
    dal.close()


@pytest.fixture
def seeded(db: Any) -> dict[str, int]:
    """acme-corp tenant with community CA (user 1 admin, user 2 member); other-corp tenant with community CB."""
    acme_id = db.tenants.insert(slug="acme-corp", is_active=True)
    other_id = db.tenants.insert(slug="other-corp", is_active=True)
    community_a = db.communities.insert(tenant_id=acme_id)
    community_b = db.communities.insert(tenant_id=other_id)
    db.community_members.insert(
        community_id=community_a, user_id="1", role="community-admin", is_active=True
    )
    db.community_members.insert(
        community_id=community_a, user_id="2", role="member", is_active=True
    )
    db.commit()
    return {"community_a": community_a, "community_b": community_b}


@pytest.fixture
def app(db: Any, seeded: dict[str, int]) -> Quart:
    quart_app = Quart(__name__)
    quart_app.config["dal"] = db
    quart_app.config["async_dal"] = _FakeAsyncDAL(db)
    workflow_dal = _FakeWorkflowDal(workflow_community={"wf-a": seeded["community_a"]})
    register_workflow_api(quart_app, _FakeWorkflowService(workflow_dal))
    return quart_app


class TestGetWorkflowCommunityScoping:
    async def test_admin_of_workflows_community_gets_200(self, app: Quart) -> None:
        client = app.test_client()
        response = await client.get(
            "/api/v1/workflows/wf-a",
            headers={"Authorization": f"Bearer {_token(sub='1', tenant='acme-corp')}"},
        )
        assert response.status_code == 200

    async def test_member_of_workflows_community_gets_200(self, app: Quart) -> None:
        """GET only requires membership, not admin."""
        client = app.test_client()
        response = await client.get(
            "/api/v1/workflows/wf-a",
            headers={"Authorization": f"Bearer {_token(sub='2', tenant='acme-corp')}"},
        )
        assert response.status_code == 200

    async def test_non_member_same_tenant_is_403(self, app: Quart) -> None:
        client = app.test_client()
        response = await client.get(
            "/api/v1/workflows/wf-a",
            headers={"Authorization": f"Bearer {_token(sub='999', tenant='acme-corp')}"},
        )
        assert response.status_code == 403

    async def test_cross_tenant_request_is_403(self, app: Quart) -> None:
        """Security-review HIGH: a valid JWT from a DIFFERENT tenant must never reach this workflow.

        `sub=1` really is `community-admin` of `community_a` -- but under
        `other-corp`'s tenant claim, `_require_community_in_tenant` must
        reject before membership is even checked (community_a belongs to
        acme-corp, not other-corp).
        """
        client = app.test_client()
        response = await client.get(
            "/api/v1/workflows/wf-a",
            headers={"Authorization": f"Bearer {_token(sub='1', tenant='other-corp')}"},
        )
        assert response.status_code == 403

    async def test_unknown_workflow_is_404(self, app: Quart) -> None:
        client = app.test_client()
        response = await client.get(
            "/api/v1/workflows/does-not-exist",
            headers={"Authorization": f"Bearer {_token(sub='1', tenant='acme-corp')}"},
        )
        assert response.status_code == 404

    async def test_no_token_is_401(self, app: Quart) -> None:
        client = app.test_client()
        response = await client.get("/api/v1/workflows/wf-a")
        assert response.status_code == 401


class TestMutatingRoutesRequireAdmin:
    async def test_update_by_admin_is_200(self, app: Quart) -> None:
        client = app.test_client()
        response = await client.put(
            "/api/v1/workflows/wf-a",
            headers={"Authorization": f"Bearer {_token(sub='1', tenant='acme-corp')}"},
            json={"name": "new name"},
        )
        assert response.status_code == 200

    async def test_update_by_member_without_admin_is_403(self, app: Quart) -> None:
        client = app.test_client()
        response = await client.put(
            "/api/v1/workflows/wf-a",
            headers={"Authorization": f"Bearer {_token(sub='2', tenant='acme-corp')}"},
            json={"name": "new name"},
        )
        assert response.status_code == 403

    async def test_delete_by_member_without_admin_is_403(self, app: Quart) -> None:
        client = app.test_client()
        response = await client.delete(
            "/api/v1/workflows/wf-a",
            headers={"Authorization": f"Bearer {_token(sub='2', tenant='acme-corp')}"},
        )
        assert response.status_code == 403

    async def test_publish_by_member_without_admin_is_403(self, app: Quart) -> None:
        client = app.test_client()
        response = await client.post(
            "/api/v1/workflows/wf-a/publish",
            headers={"Authorization": f"Bearer {_token(sub='2', tenant='acme-corp')}"},
        )
        assert response.status_code == 403

    async def test_validate_by_non_member_is_403(self, app: Quart) -> None:
        """`validate_workflow` previously had NO permission check at all."""
        client = app.test_client()
        response = await client.post(
            "/api/v1/workflows/wf-a/validate",
            headers={"Authorization": f"Bearer {_token(sub='999', tenant='acme-corp')}"},
        )
        assert response.status_code == 403


class TestCreateWorkflowRequiresCommunityAdmin:
    async def test_admin_can_create_under_own_community(
        self, app: Quart, seeded: dict[str, int]
    ) -> None:
        client = app.test_client()
        response = await client.post(
            "/api/v1/workflows",
            headers={"Authorization": f"Bearer {_token(sub='1', tenant='acme-corp')}"},
            json={"name": "wf", "entity_id": 1, "community_id": seeded["community_a"]},
        )
        assert response.status_code == 201

    async def test_non_member_cannot_create_under_arbitrary_community(
        self, app: Quart, seeded: dict[str, int]
    ) -> None:
        """The core BOLA fix: previously NOTHING checked membership before create."""
        client = app.test_client()
        response = await client.post(
            "/api/v1/workflows",
            headers={"Authorization": f"Bearer {_token(sub='999', tenant='acme-corp')}"},
            json={"name": "wf", "entity_id": 1, "community_id": seeded["community_a"]},
        )
        assert response.status_code == 403


class TestListWorkflowsCommunityFilter:
    async def test_no_community_filter_is_unaffected(self, app: Quart) -> None:
        client = app.test_client()
        response = await client.get(
            "/api/v1/workflows?entity_id=1",
            headers={"Authorization": f"Bearer {_token(sub='999', tenant='acme-corp')}"},
        )
        assert response.status_code == 200

    async def test_community_filter_for_a_community_caller_isnt_in_is_403(
        self, app: Quart, seeded: dict[str, int]
    ) -> None:
        client = app.test_client()
        response = await client.get(
            f"/api/v1/workflows?entity_id=1&community_id={seeded['community_a']}",
            headers={"Authorization": f"Bearer {_token(sub='999', tenant='acme-corp')}"},
        )
        assert response.status_code == 403
