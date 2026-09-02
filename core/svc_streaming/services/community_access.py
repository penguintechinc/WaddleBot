"""Community-membership authorization -- ported from `hub_api/services/community_access.py`.

svc-streaming is a separate deployable/DB-grant from hub-api (backend-
database.md Per-Service Database Accounts) so hub-api's authz module can't
be imported directly; this is a faithful, minimal port against the SAME
shared Postgres instance's `communities`/`community_members` tables
(`services/schema.py::bind_shared_read_tables`), reusing `flask_core.
tenancy`'s `tenant_scoped()`/`TenantContext` exactly as the original does.

Every stream-config/target-CRUD/start/stop route is community-scoped
(`community_id` from the URL) -- this module is what stops a caller who
merely holds a valid tenant JWT from configuring or starting a FORWARD job
for a community they don't belong to (the IDOR class `hub_api/services/
community_access.py`'s own docstring documents at length). `require_admin`
gates config/target/start/stop writes; `require_member` gates read-only
status/associated-channels lookups.
"""

from __future__ import annotations

from typing import Any

from flask_core.auth import verify_jwt_token
from flask_core.secrets import require_secret_key
from flask_core.tenancy import TenantContext, tenant_scoped
from quart import Request

from services.errors import forbidden
from services.schema import bind_shared_read_tables

#: `community_members.role` values treated as admin-tier for this service's
#: own write paths -- matches `hub_api/services/community_access.py`'s
#: `_ADMIN_ROLES` (the two system-seeded owner/admin role names Node's
#: controllers already check directly).
_ADMIN_ROLES = ("community-owner", "community-admin")


def _is_super_admin(request: Request) -> bool:
    """True if the caller's JWT `roles` claim names `super_admin` -- bypasses both checks below."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return False
    secret_key = require_secret_key()
    payload = verify_jwt_token(auth_header[7:], secret_key)
    if payload is None:
        return False
    return "super_admin" in (payload.get("roles") or [])


async def _require_community_in_tenant(
    async_dal: Any, dal: Any, ctx: TenantContext, *, community_id: int
) -> None:
    """Raise 403 unless `community_id` resolves to a real row inside `ctx`'s tenant.

    `tenant_scoped()` constrains the lookup via `communities.tenant_id` --
    a same-numbered community belonging to a DIFFERENT tenant can never
    match, closing the cross-tenant half of the IDOR. 403, not 404: never
    confirms to an unauthorized caller that a given `community_id` exists
    at all in another tenant.
    """
    bind_shared_read_tables(dal)
    query = tenant_scoped(dal.communities.id == community_id, ctx)
    rows = await async_dal.select_async(dal(query), dal.communities.id)
    if not rows:
        raise forbidden("Community access required")


async def require_admin(
    async_dal: Any,
    dal: Any,
    request: Request,
    ctx: TenantContext,
    *,
    community_id: int,
    user_id: int,
) -> None:
    """Raise 403 unless `user_id` is an active owner/admin of `community_id` in `ctx`'s tenant.

    Gates every write path: config create/update, target add/remove,
    start/stop forwarding.
    """
    if _is_super_admin(request):
        return

    await _require_community_in_tenant(async_dal, dal, ctx, community_id=community_id)

    membership_query = dal(
        (dal.community_members.community_id == community_id)
        & (dal.community_members.user_id == str(user_id))
        & (dal.community_members.is_active == True)  # noqa: E712 - pydal query operator
        & (dal.community_members.role.belongs(_ADMIN_ROLES))
    )
    rows = await async_dal.select_async(membership_query, dal.community_members.id)
    if not rows:
        raise forbidden("Community admin access required")


async def require_member(
    async_dal: Any,
    dal: Any,
    request: Request,
    ctx: TenantContext,
    *,
    community_id: int,
    user_id: int,
) -> None:
    """Raise 403 unless `user_id` is an ACTIVE member (any role) of `community_id`.

    Gates read-only paths: stream status, associated live-channels list.
    """
    if _is_super_admin(request):
        return

    await _require_community_in_tenant(async_dal, dal, ctx, community_id=community_id)

    membership_query = dal(
        (dal.community_members.community_id == community_id)
        & (dal.community_members.user_id == str(user_id))
        & (dal.community_members.is_active == True)  # noqa: E712 - pydal query operator
    )
    rows = await async_dal.select_async(membership_query, dal.community_members.id)
    if not rows:
        raise forbidden("Community membership required")


def decode_caller_user_id(request: Request) -> int:
    """Re-decode the bearer JWT for the caller's `sub` (user id). Raises 401 if missing/invalid."""
    from services.errors import unauthorized

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise unauthorized("Authentication required")
    secret_key = require_secret_key()
    payload = verify_jwt_token(auth_header[7:], secret_key)
    if payload is None:
        raise unauthorized("Invalid or expired token")
    try:
        return int(payload["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise unauthorized("Token missing subject claim") from exc
