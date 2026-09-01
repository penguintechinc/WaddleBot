"""Faithful port of `middleware/auth.js::requireCommunityAdmin()`.

Shared by the workflow and github_sync port groups. Both
`routes/workflow.js` and `routes/githubSync.js` gate every
authenticated endpoint with Node's `requireCommunityAdmin`, a real
DB-backed check (join `community_members` -> `community_roles`,
require `community:manage_members` or `community:manage_channels` in
`base_claims.scopes`), not a bare "is logged in" check -- unlike
`blueprints/v1/event.py`'s M8 group, which flattened Node's own
`requireCommunityAdmin` into a single static OIDC scope
(`event.calendar:admin`) because that group's community-admin surfaces
were internal to a single proxied service. This port keeps the real,
per-community DB check faithfully: hub-api OWNS `github_repo_connections`
(this module's community check is the only thing standing between a
caller and another community's GitHub PAT), and `workflowController.js`'s
own missing per-workflow ownership check (see `workflow.py`'s module
docstring) makes a weaker, scope-only gate the wrong tradeoff here.

Bypasses ported 1:1 from Node (`super-admin`, `tenant-admin`,
`platform-admin` roles) -- `roles` is an audit/display claim per
security.md, but these three checks are Node's ALREADY-SHIPPED authz
decisions, not a new role-based check invented by this port; flagged
here rather than silently dropped or silently kept without comment.
"""

from __future__ import annotations

import os
from typing import Any

from flask_core.auth import verify_jwt_token
from flask_core.tenancy import TenantContext, get_tenant_context
from quart import Request

from services.current_user import get_current_user_id
from services.errors import ApiError, forbidden
from services.schema import bind_community_authz_tables

#: Node's `requireCommunityAdmin` accepts either scope (`community:manage_members`
#: OR `community:manage_channels`) as sufficient for "community admin".
_ADMIN_SCOPES = frozenset({"community:manage_members", "community:manage_channels"})


async def require_community_admin(
    async_dal: Any, dal: Any, request: Request, *, community_id: int
) -> None:
    """Raise :class:`ApiError` (401/403) unless the caller admins `community_id`.

    Must run after `tenant_middleware` (needs `request.tenant_context` for
    the tenant-admin bypass) -- matches this group's own Auth pattern
    entry in `hub_api/PORTING.md` ("Admin/elevated action":
    `tenant_middleware` + a scope/authz check).
    """
    bind_community_authz_tables(dal)

    user_id = get_current_user_id(request)  # raises 401 if missing/invalid

    user_rows = await async_dal.select_async(dal(dal.hub_users.id == user_id))
    user_row = user_rows.first() if user_rows else None
    if user_row is not None and bool(user_row.is_super_admin):
        return

    ctx: TenantContext | None = get_tenant_context(request)
    if ctx is not None:
        ta_rows = await async_dal.select_async(
            dal(
                (dal.tenant_admins.tenant_id == ctx.tenant_id)
                & (dal.tenant_admins.user_id == user_id)
            )
        )
        if ta_rows:
            return

    if "platform-admin" in _jwt_roles(request):
        return

    member_rows = await async_dal.select_async(
        dal(
            (dal.community_members.community_id == community_id)
            & (dal.community_members.user_id == str(user_id))
            & (dal.community_members.is_active == True)  # noqa: E712
        ),
        dal.community_members.ALL,
        dal.community_roles.ALL,
        left=dal.community_roles.on(
            dal.community_members.community_role_id == dal.community_roles.id
        ),
    )
    if not member_rows:
        raise forbidden("Community admin access required")

    # Gotcha #6 (hub_api/PORTING.md): selecting fields from TWO tables via
    # `left=` nests the Row under `<tablename>.<field>` -- `community_roles`
    # is all-NULL (not absent) when the LEFT JOIN found no matching row
    # (legacy member with no `community_role_id` set), hence the `.id`
    # None-check rather than an AttributeError/KeyError.
    role_row = member_rows.first().community_roles
    base_claims = role_row.base_claims if role_row.id is not None else None
    scopes = set((base_claims or {}).get("scopes") or [])
    if not scopes & _ADMIN_SCOPES:
        raise forbidden("Community admin access required")


def _jwt_roles(request: Request) -> frozenset[str]:
    """Return the bearer JWT's `roles` claim as a set -- empty if absent/malformed."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return frozenset()
    payload = verify_jwt_token(auth_header[7:], os.getenv("SECRET_KEY", "change-me-in-production"))
    if payload is None:
        return frozenset()
    roles = payload.get("roles")
    if not isinstance(roles, list):
        return frozenset()
    return frozenset(str(r) for r in roles)


def require_valid_community_id(raw: str) -> int:
    """Parse a path-param community id, raising 400 (matching Node's `isNaN` guard) on failure."""
    try:
        community_id = int(raw)
    except (TypeError, ValueError) as exc:
        raise ApiError("Invalid community ID", 400, "BAD_REQUEST") from exc
    return community_id
