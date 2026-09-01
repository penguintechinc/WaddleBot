"""Per-community authorization -- faithful async port of `middleware/auth.js`'s DB-backed checks.

`requireMember`/`requireCommunityAdmin` (Node) resolve authorization from a
DB row scoped to the specific `:communityId` in the request path, not from
a global JWT scope claim -- there is no `teams` claim in this codebase's
actual `flask_core.auth.create_jwt_token` payload (`sub`, `username`,
`email`, `roles`, `tenant`, `scope`, `iat`, `exp`, `type` only) to carry a
community-scoped grant, so `flask_core.authz.require_scope`'s global-scope
check cannot express "admin of community 42" the way it expresses
"users:admin" -- and Node's own model was never a global scope check to
begin with. This module is deliberately the third auth primitive alongside
`tenant_middleware`/`require_scope` for this exact reason.

Load-bearing for IDOR (security.md security review): every route this
group owns takes `:communityId` from the URL path. Without this check, a
caller with ANY valid JWT could pass an arbitrary `communityId` and reach
another tenant's/another community's admin-gated data -- `require_scope`
alone (checking the caller's OWN global scope claim) would not catch this,
because it never looks at the specific resource being addressed.
`tenant_middleware` narrows to "some community in the caller's tenant" via
`flask_core.tenancy.tenant_scoped()`; this module narrows further to
"caller is an active member of THIS SPECIFIC community, with the DB-backed
role that Node's own two-scope admin gate requires" -- both checks are
required, neither alone is sufficient.

Bypass chain mirrors `requireMember`/`requireCommunityAdmin` exactly:
super-admin / platform-admin (Node: `req.user.isSuperAdmin` /
`req.user.roles.includes('platform-admin')`, ported here as the closest
available JWT signal -- the `roles` claim, audit/display-only per
security.md but the only per-caller admin signal this JWT carries) and
tenant-admin (Node: `req.isTenantAdmin`, ported as a `tenant_admins` row
lookup for the resolved tenant) both bypass the per-community DB check
entirely, same as Node.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from flask_core.auth import verify_jwt_token
from flask_core.tenancy import get_tenant_context

from services.errors import forbidden, unauthorized

#: Node's `requireCommunityAdmin` treats either of these two scopes as
#: sufficient for an admin-gated action (`middleware/auth.js`). Per
#: `058_tenants_and_claims.sql`'s seeded system roles, the `moderator`
#: role bundle already carries `community:manage_channels` -- so a
#: community moderator (not just a full community-admin) satisfies this
#: gate, matching the M7 port instruction's "moderator scope" requirement
#: for music-station admin actions.
ADMIN_SCOPES: frozenset[str] = frozenset({"community:manage_members", "community:manage_channels"})

#: JWT `roles` claim entries that bypass the per-community DB check
#: entirely -- mirrors Node's `req.user.isSuperAdmin` /
#: `req.user.roles.includes('platform-admin')` bypasses in both
#: `requireMember` and `requireCommunityAdmin`.
_BYPASS_ROLES: frozenset[str] = frozenset({"super_admin", "platform-admin"})


@dataclass(slots=True, frozen=True)
class CommunityMembership:
    """The caller's resolved role/scopes for one specific community."""

    role: str
    scopes: frozenset[str]
    is_admin: bool
    bypass: bool


def _parse_claims_scopes(raw: Any) -> frozenset[str]:
    """Port of Node's claims_cache/base_claims parsing (array or `{scopes: [...]}` shape)."""
    if raw is None:
        return frozenset()
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (TypeError, ValueError):
            return frozenset()
    if isinstance(raw, list):
        return frozenset(str(s) for s in raw)
    if isinstance(raw, dict):
        return frozenset(str(s) for s in raw.get("scopes", []))
    return frozenset()


async def _is_tenant_admin(async_dal: Any, dal: Any, *, user_id: int, tenant_id: int) -> bool:
    """Port of Node's `req.isTenantAdmin` -- a `tenant_admins` row for this tenant."""
    rows = await async_dal.select_async(
        dal((dal.tenant_admins.user_id == user_id) & (dal.tenant_admins.tenant_id == tenant_id))
    )
    return bool(rows)


async def resolve_membership(
    async_dal: Any,
    dal: Any,
    *,
    community_id: int,
    user_id: int,
    tenant_id: int,
    roles_claim: list[str],
) -> CommunityMembership | None:
    """Resolve the caller's role/scopes for `community_id`, or `None` if not a member.

    Bypass chain first (super-admin / platform-admin / tenant-admin), then
    a tenant-ownership check (security.md Tenant Isolation -- IDOR
    hardening beyond Node's own model, which never re-validated that the
    path's `:communityId` actually belongs to the caller's tenant), then a
    `community_members` LEFT JOIN `community_roles` lookup scoped to
    `(community_id, user_id, is_active=True)` -- `community_members.
    user_id` is a legacy VARCHAR column (see `services/schema.py`), so
    `user_id` is compared as `str(user_id)`, matching how Node's pg driver
    serializes the JWT `sub` claim into that column.
    """
    if any(r in _BYPASS_ROLES for r in roles_claim):
        return CommunityMembership(
            role="super-admin", scopes=frozenset(), is_admin=True, bypass=True
        )

    if await _is_tenant_admin(async_dal, dal, user_id=user_id, tenant_id=tenant_id):
        return CommunityMembership(
            role="tenant-admin", scopes=frozenset(), is_admin=True, bypass=True
        )

    community_rows = await async_dal.select_async(
        dal((dal.communities.id == community_id) & (dal.communities.tenant_id == tenant_id))
    )
    if not community_rows:
        # Either the community doesn't exist, or it belongs to a different
        # tenant than the caller's JWT -- both collapse to the same "not a
        # member" outcome Node's own DB-not-found path produces, never
        # leaking whether the community exists under another tenant.
        return None

    rows = await async_dal.select_async(
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
    if not rows:
        return None

    row = rows[0]
    member, role_row = row.community_members, row.community_roles
    scopes = _parse_claims_scopes(member.claims_cache)
    if not scopes and role_row is not None:
        scopes = _parse_claims_scopes(role_row.base_claims)
    role_name = (role_row.name if role_row is not None else None) or member.role
    return CommunityMembership(
        role=role_name, scopes=scopes, is_admin=bool(scopes & ADMIN_SCOPES), bypass=False
    )


async def require_member(
    async_dal: Any,
    dal: Any,
    *,
    community_id: int,
    user_id: int,
    tenant_id: int,
    roles_claim: list[str],
) -> CommunityMembership:
    """Port of `requireMember` -- raise 403 unless the caller is an active member."""
    membership = await resolve_membership(
        async_dal,
        dal,
        community_id=community_id,
        user_id=user_id,
        tenant_id=tenant_id,
        roles_claim=roles_claim,
    )
    if membership is None:
        raise forbidden("Community membership required")
    return membership


async def require_community_admin(
    async_dal: Any,
    dal: Any,
    *,
    community_id: int,
    user_id: int,
    tenant_id: int,
    roles_claim: list[str],
) -> CommunityMembership:
    """Port of `requireCommunityAdmin` -- raise 403 unless bypass or an admin/moderator scope."""
    membership = await resolve_membership(
        async_dal,
        dal,
        community_id=community_id,
        user_id=user_id,
        tenant_id=tenant_id,
        roles_claim=roles_claim,
    )
    if membership is None or not (membership.bypass or membership.is_admin):
        raise forbidden("Community admin access required")
    return membership


def _decode_caller(request: Any) -> tuple[int, list[str]]:
    """Re-decode the bearer JWT for `(user_id, roles)`.

    Same self-contained, independent-of-`tenant_middleware`-state pattern
    `services.current_user`/`flask_core.authz.require_scope` already use
    (see their own docstrings) -- kept local here rather than importing
    `services.current_user.get_current_user_id` so this module also
    recovers the `roles` claim in the same decode, without a second
    round-trip through the token.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise unauthorized("Authentication required")
    secret_key = os.getenv("SECRET_KEY", "change-me-in-production")
    payload = verify_jwt_token(auth_header[7:], secret_key)
    if payload is None:
        raise unauthorized("Invalid or expired token")
    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise unauthorized("Token missing subject claim") from exc
    roles = payload.get("roles") or []
    return user_id, [str(r) for r in roles]


async def authorize_community(
    request: Any, async_dal: Any, dal: Any, *, community_id: int, admin: bool
) -> CommunityMembership:
    """One-call authz gate for a `:communityId`-scoped route.

    Must run after `tenant_middleware` (reads `request.tenant_context`,
    published by that decorator -- security.md ordering contract: tenant
    before scope/resource checks). `admin=True` runs the
    `requireCommunityAdmin` port; `admin=False` runs the `requireMember`
    port.
    """
    ctx = get_tenant_context(request)
    if ctx is None:
        raise forbidden("Tenant context not resolved")
    user_id, roles = _decode_caller(request)
    check = require_community_admin if admin else require_member
    return await check(
        async_dal,
        dal,
        community_id=community_id,
        user_id=user_id,
        tenant_id=ctx.tenant_id,
        roles_claim=roles,
    )
