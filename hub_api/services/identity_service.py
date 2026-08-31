"""Linked-identity management -- ported from `identityController.js`.

Scoped to the unified-auth model `authController.js` now uses:
`req.user.userId` (this port: the JWT `sub` claim, via
`services.current_user.get_current_user_id`) is already `hub_users.id`.
Node's `identityController.js` still carries a `getOrCreateHubUser()`
helper for a pre-unified-auth, platform-session model (`user.platform ===
'admin'` / bare platform-identity sessions with no `hub_users` row yet)
-- dead code under the current `authController.js` login flow, which
always creates/resolves a `hub_users` row before minting a token. Not
ported: every route here operates directly on the caller's
`hub_users.id`, matching how `authController.js` itself already treats
`req.user.userId`.
"""

from __future__ import annotations

import base64
import json
import secrets
import time
from datetime import UTC, datetime
from typing import Any

from services.errors import bad_request, not_found

VALID_LINK_PLATFORMS = ("discord", "twitch", "slack")
_LINK_STATE_TTL_SECONDS = 10 * 60


async def list_identities(async_dal: Any, dal: Any, *, user_id: int) -> list[Any]:
    """List identities."""
    rows = await async_dal.select_async(
        dal(dal.hub_user_identities.hub_user_id == user_id),
        orderby=(~dal.hub_user_identities.is_primary, ~dal.hub_user_identities.linked_at),
    )
    return list(rows)


async def get_primary_identity(async_dal: Any, dal: Any, *, user_id: int) -> Any | None:
    """Get primary identity."""
    rows = await async_dal.select_async(
        dal(
            (dal.hub_user_identities.hub_user_id == user_id)
            & (dal.hub_user_identities.is_primary == True)  # noqa: E712 - pydal Field comparison
        )
    )
    return rows.first() if rows else None


async def set_primary_identity(async_dal: Any, dal: Any, *, user_id: int, platform: str) -> None:
    """Set primary identity."""
    if not platform:
        raise bad_request("Platform required")

    exists = await async_dal.select_async(
        dal(
            (dal.hub_user_identities.hub_user_id == user_id)
            & (dal.hub_user_identities.platform == platform)
        )
    )
    if not exists:
        raise not_found("Identity not found")

    await async_dal.update_async(dal.hub_user_identities.hub_user_id == user_id, is_primary=False)
    await async_dal.update_async(
        (dal.hub_user_identities.hub_user_id == user_id)
        & (dal.hub_user_identities.platform == platform),
        is_primary=True,
    )


async def unlink_identity(async_dal: Any, dal: Any, *, user_id: int, platform: str) -> None:
    """Unlink identity."""
    count = await async_dal.count_async(dal.hub_user_identities.hub_user_id == user_id)
    if count <= 1:
        raise bad_request("Cannot unlink last identity")

    rows = await async_dal.select_async(
        dal(
            (dal.hub_user_identities.hub_user_id == user_id)
            & (dal.hub_user_identities.platform == platform)
        )
    )
    if not rows:
        raise not_found("Identity not found")
    was_primary = bool(rows.first().is_primary)

    await async_dal.delete_async(
        (dal.hub_user_identities.hub_user_id == user_id)
        & (dal.hub_user_identities.platform == platform)
    )

    if was_primary:
        remaining = await async_dal.select_async(
            dal(dal.hub_user_identities.hub_user_id == user_id),
            orderby=dal.hub_user_identities.linked_at,
            limitby=(0, 1),
        )
        if remaining:
            await async_dal.update_async(
                dal.hub_user_identities.id == remaining.first().id, is_primary=True
            )


# ---------------------------------------------------------------------------
# Identity-linking OAuth flow -- distinct from oauth_service.start_link()/
# link_callback(). Node's identityController.js encodes state as a
# self-contained base64 JSON blob (no DB row) rather than authController.
# js's hub_oauth_states-table approach; both are live, independent routes
# in the frozen v1 contract (`/api/v1/user/identities/link/:platform` here
# vs `/api/v1/auth/oauth/:platform/link` in oauth_service.py) so both are
# ported faithfully rather than merged into one mechanism.
# ---------------------------------------------------------------------------


def _encode_link_state(user_id: int) -> str:
    payload = {
        "hubUserId": user_id,
        "linkingFlow": True,
        "timestamp": int(time.time() * 1000),
        "nonce": secrets.token_hex(8),
    }
    return base64.b64encode(json.dumps(payload).encode()).decode()


def _decode_link_state(state: str) -> dict[str, Any]:
    try:
        data: dict[str, Any] = json.loads(base64.b64decode(state).decode())
    except Exception as exc:  # noqa: BLE001 - any decode failure is "invalid state"
        raise bad_request("Invalid state") from exc
    if not data.get("linkingFlow") or not data.get("hubUserId"):
        raise bad_request("Invalid state")
    age_ms = int(time.time() * 1000) - int(data.get("timestamp", 0))
    if age_ms > _LINK_STATE_TTL_SECONDS * 1000:
        raise bad_request("State expired")
    return data


async def start_identity_link(
    async_dal: Any, dal: Any, *, user_id: int, platform: str, callback_base_url: str
) -> tuple[str, str]:
    """Start an identity-link OAuth flow. Returns `(authorize_url, state)`.

    Delegates URL-building to `oauth_service.build_authorize_url` (shared
    credential lookup + per-platform authorize-URL shape) but keeps its
    own base64 state encoding -- see module docstring.
    """
    from services import oauth_service  # local import: avoids a module-load cycle

    exists = await async_dal.select_async(
        dal(
            (dal.hub_user_identities.hub_user_id == user_id)
            & (dal.hub_user_identities.platform == platform)
        )
    )
    if exists:
        raise bad_request(f"{platform} account already linked")

    state = _encode_link_state(user_id)
    redirect_uri = f"{callback_base_url}/api/v1/user/identities/link/{platform}/callback"
    authorize_url = await oauth_service.build_authorize_url(
        async_dal, dal, platform=platform, redirect_uri=redirect_uri, state=state
    )
    return authorize_url, state


async def identity_link_callback(
    async_dal: Any, dal: Any, *, platform: str, code: str, state: str, callback_base_url: str
) -> None:
    """Complete an identity-link callback: decode state, exchange the code, link the identity."""
    from services import oauth_service  # local import: avoids a module-load cycle

    state_data = _decode_link_state(state)
    hub_user_id = int(state_data["hubUserId"])

    redirect_uri = f"{callback_base_url}/api/v1/user/identities/link/{platform}/callback"
    user_data = await oauth_service.exchange_code(
        async_dal, dal, platform=platform, code=code, redirect_uri=redirect_uri
    )

    existing = await async_dal.select_async(
        dal(
            (dal.hub_user_identities.platform == platform)
            & (dal.hub_user_identities.platform_user_id == user_data["id"])
        )
    )
    if existing:
        if existing.first().hub_user_id != hub_user_id:
            raise bad_request("Already linked to another user")
        return  # already linked to this user

    count = await async_dal.count_async(dal.hub_user_identities.hub_user_id == hub_user_id)
    await async_dal.insert_async(
        dal.hub_user_identities,
        hub_user_id=hub_user_id,
        platform=platform,
        platform_user_id=user_data["id"],
        platform_username=user_data["username"],
        avatar_url=user_data.get("avatar_url"),
        is_primary=(count == 0),
        linked_at=datetime.now(UTC),
        last_used=datetime.now(UTC),
    )
