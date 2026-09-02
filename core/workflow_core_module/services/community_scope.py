"""Resolves and enforces a workflow/execution's REAL owning community -- BOLA/IDOR fix (A01).

Every CRUD/execution route in this module accepted `community_id` as
client-supplied input (JSON body or query string, frequently OPTIONAL) and
passed it straight into `PermissionService.check_permission` as advisory
"context" -- nothing ever verified the caller actually belongs to that
community, and nothing verified the supplied value even matches the
workflow's OWN `community_id` in the database. A caller with ANY valid JWT
could `POST /api/v1/workflows` under an arbitrary `community_id` they hold
no membership in (`create_workflow` never checked membership at all before
this fix), or, on read/update/delete/execute routes, could pass a
`community_id` different from the workflow's real one and still exercise
whatever role/entity-level ACL happened to key off it (`permission_service.
_get_user_roles(user_id, community_id)` trusted that argument outright).

This module is the fix: resolve the workflow's (or execution's, joined
through its workflow) TRUE `community_id` from the database -- never the
client-supplied value, which is validated/typed but never trusted for
authorization -- then require the caller be an active member (read) or
community-admin (write/execute) of that resolved community, via
`flask_core.community_access` (the same shared BOLA/IDOR fix every other
core service uses, per that module's own docstring).

Usage (controller level, after `@tenant_middleware` + `@auth_required` have
run)::

    ctx = get_tenant_context(request)
    community_id = await resolve_workflow_community_id(dal_raw, workflow_id)
    await require_community_admin(
        async_dal, dal_raw, request, ctx, community_id=community_id, user_id=user_id
    )
"""

from __future__ import annotations

from typing import Any


class WorkflowCommunityNotFoundError(Exception):
    """Raised when a workflow/execution's owning community cannot be resolved.

    Maps to 404 -- the referenced workflow/execution simply doesn't exist,
    same status a direct not-found lookup would already return.
    """

    def __init__(self, resource_id: str) -> None:
        self.resource_id = resource_id
        super().__init__(f"Resource not found: {resource_id}")


async def resolve_workflow_community_id(dal: Any, workflow_id: str) -> int:
    """The workflow's OWN `community_id` column -- never the client-supplied value.

    Args:
        dal: A pydal-compatible object exposing `.executesql()` (the raw
            pydal `DAL`, or `flask_core.database.AsyncDAL`, whose
            `__getattr__` forwards to the same method).
        workflow_id: Workflow UUID.

    Raises:
        WorkflowCommunityNotFoundError: `workflow_id` doesn't exist.
    """
    rows = dal.executesql(
        "SELECT community_id FROM workflows WHERE workflow_id = %s", [workflow_id]
    )
    if not rows or rows[0][0] is None:
        raise WorkflowCommunityNotFoundError(workflow_id)
    return int(rows[0][0])


async def resolve_execution_community_id(dal: Any, execution_id: str) -> int:
    """The execution's owning workflow's `community_id` -- joins through `workflow_executions`.

    Raises:
        WorkflowCommunityNotFoundError: `execution_id` doesn't exist, or its
            workflow no longer does.
    """
    rows = dal.executesql(
        """
        SELECT w.community_id
        FROM workflow_executions e
        JOIN workflows w ON w.workflow_id = e.workflow_id
        WHERE e.execution_id = %s
        """,
        [execution_id],
    )
    if not rows or rows[0][0] is None:
        raise WorkflowCommunityNotFoundError(execution_id)
    return int(rows[0][0])
