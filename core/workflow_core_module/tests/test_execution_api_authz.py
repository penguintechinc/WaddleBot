"""`controllers/execution_api.py` -- community/tenant scoping fix (A01, deferred from gh security PR #260).

Fail-first proof (executed, not narrated): with `_authorize_execution_
community`'s body temporarily replaced with `return None`,
`test_get_execution_details_non_member_is_403` and `test_cancel_execution_
member_without_admin_is_403` both went green -> red as expected (200/500
instead of 403 -- `get_execution_details`/`cancel_execution` previously had
NO permission check at all, only `auth_required`); reverted after
confirming.

Same testing shape as `test_workflow_api_authz.py`: stub `WorkflowService`/
`WorkflowEngine`/`PermissionService` (the real ones speak Postgres-only raw
SQL), real sqlite-backed `communities`/`community_members`/`tenants` via
`bind_shared_read_tables`, so the REAL `@tenant_middleware`/`@auth_required`/
`_authorize_*_community` wiring is what's under test.
"""

from __future__ import annotations

from typing import Any

import pytest
from pydal import DAL
from quart import Quart

from config import Config
from controllers.execution_api import register_execution_api
from flask_core.auth import create_jwt_token
from flask_core.community_access import bind_shared_read_tables

SECRET = Config.SECRET_KEY


def _token(*, sub: str, tenant: str) -> str:
    return create_jwt_token(
        user_id=sub, username=f"user{sub}", email=f"user{sub}@example.com",
        roles=[], secret_key=SECRET, tenant=tenant,
    )


class _FakeAsyncDAL:
    def __init__(self, dal: Any) -> None:
        self.dal = dal

    async def select_async(self, query_set: Any, *fields: Any) -> Any:
        return query_set.select(*fields) if fields else query_set.select()


class _FakeWorkflowDal:
    """Stub for `WorkflowService.dal` -- resolves `workflows`/`workflow_executions` lookups."""

    def __init__(
        self, workflow_community: dict[str, int], execution_workflow: dict[str, str]
    ) -> None:
        self._workflow_community = workflow_community
        self._execution_workflow = execution_workflow

    def executesql(self, sql: str, params: list[Any]) -> list[tuple[Any, ...]]:
        if "FROM workflow_executions" in sql:
            workflow_id = self._execution_workflow.get(params[0])
            community_id = (
                self._workflow_community.get(workflow_id) if workflow_id else None
            )
            return [(community_id,)] if community_id is not None else []
        if "SELECT community_id FROM workflows" in sql:
            community_id = self._workflow_community.get(params[0])
            return [(community_id,)] if community_id is not None else []
        raise AssertionError(f"unexpected query: {sql}")


class _FakeWorkflowService:
    def __init__(self, dal: _FakeWorkflowDal) -> None:
        self.dal = dal

    async def get_workflow(self, **kwargs: Any) -> dict[str, Any]:
        return {"workflow_id": kwargs["workflow_id"], "entity_id": 1}


class _AlwaysAllowPermissionService:
    """Stub -- the pre-existing fine-grained `can_execute`/`can_view` check, always passes.

    This suite tests the NEW community-membership gate that now runs
    before this check, not the pre-existing check itself.
    """

    async def check_permission(self, **kwargs: Any) -> bool:
        return True


class _Execution:
    execution_id = "exec-result-1"
    workflow_id = "wf-a"
    execution_path: list[str] = []
    execution_time_seconds = 0.1
    final_variables: dict[str, Any] = {}
    is_successful = True

    class status:
        value = "running"

    class start_time:
        @staticmethod
        def isoformat() -> str:
            return "2026-01-01T00:00:00Z"

    @staticmethod
    def get_failed_nodes() -> list[str]:
        return []


class _FakeWorkflowEngine:
    async def execute_workflow(self, **kwargs: Any) -> _Execution:
        return _Execution()

    async def get_execution_status(self, execution_id: str) -> dict[str, Any]:
        return {"execution_id": execution_id, "workflow_id": "wf-a", "status": "running"}

    async def get_execution_metrics(self, execution_id: str) -> Any:
        return None

    async def cancel_execution(self, execution_id: str) -> bool:
        return True


@pytest.fixture
def db() -> Any:
    dal = DAL("sqlite:memory")
    bind_shared_read_tables(dal, migrate=True)
    yield dal
    dal.close()


@pytest.fixture
def seeded(db: Any) -> dict[str, int]:
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
    workflow_dal = _FakeWorkflowDal(
        workflow_community={"wf-a": seeded["community_a"]},
        execution_workflow={"exec-1": "wf-a"},
    )
    quart_app.config["workflow_service"] = _FakeWorkflowService(workflow_dal)
    quart_app.config["permission_service"] = _AlwaysAllowPermissionService()
    register_execution_api(quart_app, _FakeWorkflowEngine())
    return quart_app


class TestExecuteWorkflowCommunityScoping:
    async def test_member_of_workflows_community_gets_202(self, app: Quart) -> None:
        client = app.test_client()
        response = await client.post(
            "/api/v1/workflows/wf-a/execute",
            headers={"Authorization": f"Bearer {_token(sub='2', tenant='acme-corp')}"},
            json={"community_id": 999999},  # ignored for authz -- real value resolved from DB
        )
        assert response.status_code == 202

    async def test_non_member_is_403_regardless_of_supplied_community_id(
        self, app: Quart, seeded: dict[str, int]
    ) -> None:
        """The core BOLA fix: the (correct!) `community_id` in the body used to be sufficient."""
        client = app.test_client()
        response = await client.post(
            "/api/v1/workflows/wf-a/execute",
            headers={"Authorization": f"Bearer {_token(sub='999', tenant='acme-corp')}"},
            json={"community_id": seeded["community_a"]},
        )
        assert response.status_code == 403

    async def test_cross_tenant_execute_is_403(self, app: Quart) -> None:
        client = app.test_client()
        response = await client.post(
            "/api/v1/workflows/wf-a/execute",
            headers={"Authorization": f"Bearer {_token(sub='1', tenant='other-corp')}"},
            json={},
        )
        assert response.status_code == 403


class TestGetExecutionDetailsHadNoCheckAtAll:
    async def test_member_of_owning_workflows_community_gets_200(self, app: Quart) -> None:
        client = app.test_client()
        response = await client.get(
            "/api/v1/workflows/executions/exec-1",
            headers={"Authorization": f"Bearer {_token(sub='2', tenant='acme-corp')}"},
        )
        assert response.status_code == 200

    async def test_non_member_is_403(self, app: Quart) -> None:
        """SECURITY: previously ANY authenticated user could view ANY execution by UUID."""
        client = app.test_client()
        response = await client.get(
            "/api/v1/workflows/executions/exec-1",
            headers={"Authorization": f"Bearer {_token(sub='999', tenant='acme-corp')}"},
        )
        assert response.status_code == 403

    async def test_cross_tenant_is_403(self, app: Quart) -> None:
        client = app.test_client()
        response = await client.get(
            "/api/v1/workflows/executions/exec-1",
            headers={"Authorization": f"Bearer {_token(sub='1', tenant='other-corp')}"},
        )
        assert response.status_code == 403

    async def test_unknown_execution_is_404(self, app: Quart) -> None:
        client = app.test_client()
        response = await client.get(
            "/api/v1/workflows/executions/does-not-exist",
            headers={"Authorization": f"Bearer {_token(sub='1', tenant='acme-corp')}"},
        )
        assert response.status_code == 404


class TestCancelExecutionRequiresAdmin:
    async def test_admin_can_cancel(self, app: Quart) -> None:
        client = app.test_client()
        response = await client.post(
            "/api/v1/workflows/executions/exec-1/cancel",
            headers={"Authorization": f"Bearer {_token(sub='1', tenant='acme-corp')}"},
        )
        assert response.status_code == 200

    async def test_member_without_admin_is_403(self, app: Quart) -> None:
        """SECURITY: previously ANY authenticated user could cancel ANY execution by UUID."""
        client = app.test_client()
        response = await client.post(
            "/api/v1/workflows/executions/exec-1/cancel",
            headers={"Authorization": f"Bearer {_token(sub='2', tenant='acme-corp')}"},
        )
        assert response.status_code == 403


class TestListWorkflowExecutionsCommunityScoping:
    async def test_non_member_is_403_regardless_of_supplied_community_id(
        self, app: Quart, seeded: dict[str, int]
    ) -> None:
        client = app.test_client()
        response = await client.get(
            f"/api/v1/workflows/wf-a/executions?community_id={seeded['community_a']}",
            headers={"Authorization": f"Bearer {_token(sub='999', tenant='acme-corp')}"},
        )
        assert response.status_code == 403

    async def test_cross_tenant_is_403(self, app: Quart, seeded: dict[str, int]) -> None:
        client = app.test_client()
        response = await client.get(
            f"/api/v1/workflows/wf-a/executions?community_id={seeded['community_a']}",
            headers={"Authorization": f"Bearer {_token(sub='1', tenant='other-corp')}"},
        )
        assert response.status_code == 403


class TestWorkflowTestCommunityScoping:
    async def test_member_gets_200(self, app: Quart) -> None:
        client = app.test_client()
        response = await client.post(
            "/api/v1/workflows/wf-a/test",
            headers={"Authorization": f"Bearer {_token(sub='2', tenant='acme-corp')}"},
            json={},
        )
        assert response.status_code == 200

    async def test_non_member_is_403(self, app: Quart) -> None:
        client = app.test_client()
        response = await client.post(
            "/api/v1/workflows/wf-a/test",
            headers={"Authorization": f"Bearer {_token(sub='999', tenant='acme-corp')}"},
            json={},
        )
        assert response.status_code == 403
