"""`services/community_scope.py` -- resolves a workflow/execution's REAL owning community.

Unit-level coverage for the two resolver functions in isolation from the
controller wiring (covered separately in `test_workflow_api_authz.py` /
`test_execution_api_authz.py`). `workflow_service.dal.executesql()` speaks
Postgres-only SQL (`%s` placeholders) -- these tests stub `.executesql()`
directly rather than standing up a real Postgres instance, since the SQL
text/params contract is exactly what's under test here.
"""

from __future__ import annotations

from typing import Any

import pytest

from services.community_scope import (
    WorkflowCommunityNotFoundError,
    resolve_execution_community_id,
    resolve_workflow_community_id,
)


class _FakeDal:
    """Records the SQL/params it was called with; returns a canned row set."""

    def __init__(self, rows: list[tuple[Any, ...]]) -> None:
        self.rows = rows
        self.calls: list[tuple[str, list[Any]]] = []

    def executesql(self, sql: str, params: list[Any]) -> list[tuple[Any, ...]]:
        self.calls.append((sql, params))
        return self.rows


class TestResolveWorkflowCommunityId:
    async def test_returns_the_real_community_id(self) -> None:
        dal = _FakeDal(rows=[(42,)])
        result = await resolve_workflow_community_id(dal, "wf-1")
        assert result == 42
        sql, params = dal.calls[0]
        assert "workflows" in sql
        assert params == ["wf-1"]

    async def test_missing_workflow_raises(self) -> None:
        dal = _FakeDal(rows=[])
        with pytest.raises(WorkflowCommunityNotFoundError):
            await resolve_workflow_community_id(dal, "does-not-exist")

    async def test_null_community_id_raises(self) -> None:
        """A workflow row with a NULL community_id is treated as unresolvable, not community 0."""
        dal = _FakeDal(rows=[(None,)])
        with pytest.raises(WorkflowCommunityNotFoundError):
            await resolve_workflow_community_id(dal, "wf-orphaned")


class TestResolveExecutionCommunityId:
    async def test_returns_the_owning_workflows_community_id(self) -> None:
        dal = _FakeDal(rows=[(7,)])
        result = await resolve_execution_community_id(dal, "exec-1")
        assert result == 7
        sql, params = dal.calls[0]
        assert "workflow_executions" in sql
        assert "workflows" in sql
        assert params == ["exec-1"]

    async def test_missing_execution_raises(self) -> None:
        dal = _FakeDal(rows=[])
        with pytest.raises(WorkflowCommunityNotFoundError):
            await resolve_execution_community_id(dal, "does-not-exist")
