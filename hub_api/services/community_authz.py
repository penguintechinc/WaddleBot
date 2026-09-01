"""Per-community authorization -- DB-backed, mirrors Node's `requireCommunityAdmin`.

`flask_core.authz.require_scope` checks a flat JWT `scope` claim -- correct
for tenant-level gates, but wrong here: `flask_core.auth.SCOPE_BUNDLES
["community"]["admin"]` is never granted at JWT-issuance time anywhere in
this port (`auth_service.create_session_token` only ever grants the
`global`/`tenant` bundles), and even if it were, a flat scope claim can't
answer "admin of *which* community" -- using it alone for a `communityId`
URL path param would let any caller holding a broad community-shaped scope
act on a community they don't actually belong to. That is the exact IDOR
class this module exists to prevent (see `hub_api/PORTING.md`'s "SECURITY"
note on this port: "IDOR from request-param community_id instead of JWT").

Node's real authorization for these routes
(`middleware/auth.js::requireCommunityAdmin`/`requireMember`) is a live DB
lookup -- `community_members` JOIN `community_roles` on
`(community_id, user_id)`, `is_active = true` -- never the JWT scope claim
alone. This module ports that check faithfully: `community_id` always
comes from the URL (as Node's own routes take it), but the caller's
*membership and role in that specific community* is resolved from the
database using `user_id` sourced from the validated JWT
(`services.current_user.get_current_user_id`), never trusted from the
request itself. A caller with no active membership row for that exact
`community_id`, or an active membership whose role doesn't carry one of
the required scopes, is rejected -- regardless of what scope claims their
JWT carries for *other* communities or the tenant at large.

Scope strings (`community:manage_members`, `community:manage_channels`,
...) come from `community_roles.base_claims.scopes`
(`config/postgres/migrations/058_tenants_and_claims.sql`'s
`seed_community_system_roles()`), not from `flask_core.auth.SCOPE_BUNDLES`
-- a different, DB-seeded vocabulary Node's own controllers already use,
kept as-is rather than remapped to the (unrelated, unwired-for-community)
JWT bundle names.

Scope explicitly NOT covered by this module (see `hub_api/PORTING.md`
"What M2 does NOT cover"): Node's tenant-admin/platform-admin bypasses in
`requireCommunityAdmin` (`req.isTenantAdmin`, `req.user.roles.includes
('platform-admin')`). Neither concept is fully wired to a JWT claim in
this port yet (tenant-admin grants `SCOPE_BUNDLES["tenant"]["admin"]`,
which does not include any `community:*` scope; "platform-admin" is never
granted as a role anywhere in `auth_service.py`) -- porting a bypass for a
claim nothing ever issues would be dead code, and inventing new
scope-grant wiring is out of scope for a controller-group port PR. Only
the global `hub_users.is_super_admin` bypass is ported (mirrors Node's
`req.user?.isSuperAdmin` check, sourced the same DB-authoritative way
Node's own JWT payload is populated at login).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from services.errors import forbidden


@dataclass(slots=True, frozen=True)
class CommunityRole:
    """The caller's resolved role + granted scopes for one specific community."""

    name: str
    priority: int
    scopes: frozenset[str]


async def _is_super_admin(async_dal: Any, dal: Any, *, user_id: int) -> bool:
    """Look up `hub_users.is_super_admin` for `user_id`. False if the user row is missing."""
    rows = await async_dal.select_async(dal(dal.hub_users.id == user_id))
    if not rows:
        return False
    return bool(rows.first().is_super_admin)


async def get_caller_community_role(
    async_dal: Any, dal: Any, *, community_id: int, user_id: int
) -> CommunityRole | None:
    """Resolve the caller's active `community_members` row + its `community_roles` scopes.

    Mirrors `middleware/auth.js`'s `requireCommunityAdmin`/`requireMember`
    query (LEFT JOIN on `community_role_id`, `is_active = true`).
    `community_members.user_id` is a legacy VARCHAR column (see
    `services/schema.py`'s own note on that field) -- compared as a string
    here to match how Node's pg driver serializes it and how every other
    `community_members.user_id` query in this port already does.

    Returns `None` if the caller has no active membership row for this
    community at all (never raises -- callers decide whether "no role" is
    an error).
    """
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
    cm, cr = rows[0].community_members, rows[0].community_roles
    base_claims = cr.base_claims if cr is not None else None
    scopes = base_claims.get("scopes", []) if isinstance(base_claims, dict) else []
    role_name = (cr.name if cr is not None and cr.name else None) or cm.role or "member"
    priority = (cr.priority if cr is not None and cr.priority is not None else 0) or 0
    return CommunityRole(name=role_name, priority=priority, scopes=frozenset(scopes))


async def require_community_scope(
    async_dal: Any,
    dal: Any,
    *,
    community_id: int,
    user_id: int,
    any_of: tuple[str, ...],
) -> CommunityRole:
    """Require the caller hold at least one of `any_of` scopes for `community_id`.

    Global super admins bypass (`hub_users.is_super_admin`, DB-authoritative
    -- mirrors Node's `req.user?.isSuperAdmin` bypass). Fails closed: no
    active membership, or a membership whose role grants none of the
    required scopes, is a 403 (`forbidden()`) -- never a silent pass. This
    is the ONLY place `community_id` from a URL param is trusted to mean
    anything -- it is always cross-checked against a real
    `community_members` row for the caller's own `user_id`, never assumed.
    """
    if await _is_super_admin(async_dal, dal, user_id=user_id):
        return CommunityRole(name="super-admin", priority=999, scopes=frozenset(any_of))

    role = await get_caller_community_role(
        async_dal, dal, community_id=community_id, user_id=user_id
    )
    if role is None or not (role.scopes & set(any_of)):
        raise forbidden("Community admin access required")
    return role
