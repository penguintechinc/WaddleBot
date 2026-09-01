"""Community-membership authorization -- the IDOR/token-takeover fix this port group adds.

Node's `requireCommunityAdmin` middleware (`admin/hub_module/backend/src/
middleware/auth.js`) verifies the caller is an active owner/admin member
of the exact `:communityId` in the URL before `overlayController.js`'s
four routes run -- every one of them is mounted behind it in `admin.js`.
`hub_api/PORTING.md`'s documented Auth pattern table only covers
tenant+scope (`tenant_middleware` + `require_scope`), which is NOT the
same guarantee: a caller holding a global `streaming.overlay:admin` /
`streaming.calls:admin` scope grant would pass `require_scope` for ANY
`community_id` path parameter -- including one in a different tenant
entirely, or one they have no membership in at all. Overlay URLs
(unguessable but not access-controlled) and RTC join tokens (a live
LiveKit credential) are exactly what security.md's Output Validation and
Service-to-Service Auth sections both warn against minting for the wrong
caller. `require_community_admin()`/`require_community_member()` below
are this group's own addition, layered strictly AFTER `tenant_middleware`
/`require_scope`, never a replacement for either.

Worse gap, member-facing surface: Node's `memberVoiceRouter`
(`routes/calls.js`) applies `requireAuth` ONLY -- no community-membership
check of any kind -- to `POST .../voice/rooms/:roomName/join`. ANY
authenticated user, member of the target community or not, could mint a
LiveKit join token for ANY `community_id` by supplying it in the URL.
`require_community_member()` closes this; ported in
`blueprints/v1/calls.py`.

Simplification vs. Node's full model (documented, not silently dropped --
`hub_api/PORTING.md` Gotcha #4's own precedent for "document, don't
silently invent"): Node resolves the caller's admin-ness via a
`community_roles.base_claims` JSON scopes join
(`community:manage_members` / `community:manage_channels`); this port
checks `community_members.role` directly against the two system-seeded
admin-tier role names instead (`communityController.js`/
`adminController.js`/`platformController.js` all also check
`role === 'community-owner'` directly in several places, so this is not
an invented convention). Binding `community_roles` +
`hub_channel_permission_overrides` for a claims graph neither overlay
nor calls otherwise needs is out of scope for this port group.
"""

from __future__ import annotations

import os
from typing import Any

from flask_core.auth import verify_jwt_token
from flask_core.tenancy import TenantContext, tenant_scoped
from quart import Request

from services.errors import forbidden

#: `community_members.role` values Node's own controllers treat as
#: community-admin-tier (see module docstring).
_ADMIN_ROLES = ("community-owner", "community-admin")


def _is_super_admin(request: Request) -> bool:
    """True if the caller's JWT `roles` claim names `super_admin`.

    Independent re-decode -- same self-contained pattern
    `services/current_user.py` and `blueprints/v1/event.py::
    _build_user_context` already use, rather than reaching into
    `tenant_middleware`'s request-local state. Super admins bypass BOTH
    checks below entirely, matching Node's `requireCommunityAdmin`
    bypass (security.md: "Admin tokens also tenant-scoped (except
    super-admin)").
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return False
    secret_key = os.getenv("SECRET_KEY", "change-me-in-production")
    payload = verify_jwt_token(auth_header[7:], secret_key)
    if payload is None:
        return False
    return "super_admin" in (payload.get("roles") or [])


async def _require_community_in_tenant(
    async_dal: Any, dal: Any, ctx: TenantContext, *, community_id: int
) -> None:
    """Raise 403 unless `community_id` resolves to a real row inside `ctx`'s tenant.

    `tenant_scoped()` (`flask_core.tenancy`, the one ORM-layer
    tenant-scoping primitive security.md mandates) constrains the lookup
    via `communities.tenant_id` -- a same-numbered community belonging to
    a DIFFERENT tenant can never match, closing the cross-tenant half of
    the IDOR. 403, not 404: matches Node's `requireCommunityAdmin`
    ("Community admin access required" for both "doesn't exist" and "not
    a member"), and avoids confirming to an unauthorized caller that a
    given community_id exists at all in another tenant.
    """
    query = tenant_scoped(dal.communities.id == community_id, ctx)
    rows = await async_dal.select_async(dal(query), dal.communities.id)
    if not rows:
        raise forbidden("Community admin access required")


async def require_community_admin(
    async_dal: Any,
    dal: Any,
    request: Request,
    ctx: TenantContext,
    *,
    community_id: int,
    user_id: int,
) -> None:
    """Raise 403 unless `user_id` is an active owner/admin of `community_id` in `ctx`'s tenant.

    Port of Node's `requireCommunityAdmin` -- gates every overlay route
    and every admin-facing calls route (`blueprints/v1/overlay.py`,
    `blueprints/v1/calls.py`'s `calls_admin_bp`).
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


async def require_community_member(
    async_dal: Any,
    dal: Any,
    request: Request,
    ctx: TenantContext,
    *,
    community_id: int,
    user_id: int,
) -> None:
    """Raise 403 unless `user_id` is an ACTIVE member (any role) of `community_id`.

    The fix `blueprints/v1/calls.py`'s member-facing voice routes add
    that Node never had at all -- see module docstring's "Worse gap"
    paragraph. Any active role qualifies (unlike
    `require_community_admin`): a regular member is allowed to list
    rooms, create an ad-hoc room, and join/leave voice, matching the
    feature intent (member-facing voice, not an admin surface) while
    still refusing a caller with no membership in the target community
    at all.
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
