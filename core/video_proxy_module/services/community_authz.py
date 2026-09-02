"""Community-membership authorization for video_proxy_module -- BOLA/IDOR fix (A01).

Every route in `app.py` decodes and verifies a bearer JWT (`require_auth`)
but never checked the caller actually belongs to the `community_id` (or the
community that owns the `config_id`/`destination_id`) they're operating on
-- any authenticated caller, from any community, could read/write ANY
community's stream config, regenerate ANY community's stream key, and add/
remove/toggle destinations on ANY community's config, all by supplying (or
guessing -- `config_id`/`destination_id` are sequential integer primary
keys) an ID they hold no relationship to.

This is the generic BOLA/IDOR fix `flask_core.community_access` already
provides for every other core service (see that module's own docstring) --
duplicated here in a self-contained form rather than imported, because
`video_proxy_module` ships its own standalone Dockerfile with no
`flask_core` in `requirements.txt` (it must also import cleanly when
bundled into `services/core-community`'s image, where flask_core IS
available -- see `config.py`'s own `_require_secret_key` docstring for the
identical constraint on that file). Deliberately synchronous, matching
every other pydal call already made directly (unwrapped, no `AsyncDAL`)
throughout this module's `app.py`.

Every table this module reads (`communities`, `community_members`) is owned
by hub-api's own migrations -- never created here (`migrate=False`
unconditionally in production, matching `flask_core.community_access.
bind_shared_read_tables`); tests pass `migrate=True` against a throwaway
sqlite DB.
"""

from __future__ import annotations

from typing import Any

from pydal import Field

#: `community_members.role` values treated as admin-tier -- matches
#: `flask_core/community_access.py`'s `_ADMIN_ROLES` (the two system-seeded
#: owner/admin role names).
_ADMIN_ROLES = ("community-owner", "community-admin")


class CommunityAccessError(Exception):
    """Raised when the caller isn't authorized for the given community. Maps to 403."""

    def __init__(self, message: str = "Community access required") -> None:
        self.message = message
        super().__init__(message)


def bind_shared_read_tables(db: Any, *, migrate: bool = False) -> None:
    """Define the read-only field subset of `communities`/`community_members`.

    Idempotent (guarded on `community_members`). `migrate=False` in
    production always -- these tables are never this service's to create.
    """
    if "community_members" in db.tables:
        return

    if "communities" not in db.tables:
        db.define_table(
            "communities",
            Field("tenant_id", "integer", notnull=True),
            migrate=migrate,
        )

    db.define_table(
        "community_members",
        Field("community_id", "integer", notnull=True),
        # VARCHAR in Postgres (legacy platform-identity membership model),
        # not a FK -- matches `flask_core/community_access.py`'s own note;
        # compared as `str(user_id)` at every call site.
        Field("user_id", "string", length=255),
        Field("role", "string", length=50, default="member"),
        Field("is_active", "boolean", default=True),
        migrate=migrate,
    )


def _require_membership(db: Any, *, community_id: int, user_id: str, admin_only: bool) -> None:
    bind_shared_read_tables(db)
    query = (
        (db.community_members.community_id == community_id)
        & (db.community_members.user_id == str(user_id))
        & (db.community_members.is_active == True)  # noqa: E712 -- pydal query operand
    )
    if admin_only:
        query &= db.community_members.role.belongs(_ADMIN_ROLES)
    row = db(query).select(db.community_members.id).first()
    if row is None:
        raise CommunityAccessError(
            "Community admin access required" if admin_only else "Community membership required"
        )


def require_member(db: Any, *, community_id: int, user_id: str) -> None:
    """Raise `CommunityAccessError` unless `user_id` is an ACTIVE member (any role) of `community_id`.

    Gates read-only paths.
    """
    _require_membership(db, community_id=community_id, user_id=user_id, admin_only=False)


def require_admin(db: Any, *, community_id: int, user_id: str) -> None:
    """Raise `CommunityAccessError` unless `user_id` is an active owner/admin of `community_id`.

    Gates every write path (create/update/delete stream config or destination).
    """
    _require_membership(db, community_id=community_id, user_id=user_id, admin_only=True)


def extract_user_id(payload: dict[str, Any]) -> str:
    """The caller's identity from a verified JWT payload.

    This module's own `create_jwt_token(data, ...)` accepts an arbitrary
    `data` dict, so both `sub` (the platform-wide convention -- security.md
    JWT Claims) and `user_id` (this module's pre-existing local convention,
    still accepted for backward compatibility) are checked.

    Raises:
        CommunityAccessError: neither claim is present -- treated as a 403
            (never authorized), not a separate 401, since this always runs
            after `require_auth` has already verified the token itself.
    """
    user_id = payload.get("sub") or payload.get("user_id")
    if not user_id:
        raise CommunityAccessError("Token missing subject claim")
    return str(user_id)
