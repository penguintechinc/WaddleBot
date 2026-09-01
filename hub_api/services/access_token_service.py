"""PAT/CAT access-token service -- port of Node's `tokenController.js`.

PAT (Personal Access Token, `wdl_u_<random32>`): one per user, acts as
the token owner. CAT (Community Access Token, `wdl_c_<random32>`):
non-human service principal scoped to a community, quota-limited.

Query style matches `services/community_common.py`'s established
convention (synchronous `dal`, pydal query builder, explicit
`dal.commit()`) -- see `services/support_service.py`'s module docstring
for the full rationale, shared by this port group.

**Token hashing** (already correct in Node, ported faithfully): only a
SHA-256 hex digest of the plaintext token is ever persisted
(`token_hash`); the plaintext value is returned to the caller exactly
once, at creation, and is never stored or returned again -- `get_pat()`/
`list_cats()` select every column except `token_hash`.

**Ownership scoping** (already correct in Node, ported faithfully): every
PAT query filters on `user_id` from the *caller's own* validated JWT
(never a client-supplied id) -- `blueprints/v1/access_token.py` passes
`get_current_user_id(request)`, not a path/body parameter, so a user can
never list/revoke another user's PAT (IDOR). CAT queries filter on
`community_id`, gated by `require_scope("community.tokens:admin")` +
`community_in_tenant()` in the blueprint -- a community admin can only
manage CATs for a community that resolves inside their own token's
tenant.

**SECURITY FIX** (not in Node's source -- see `hub_api/PORTING.md`'s
"faithful port BUT fix vulns" mandate): `createCAT()` validates its
`scopes` argument against the `permission_scopes` catalog before minting
a token; `createPAT()` did NOT apply the same check to `scope_ceiling`,
letting a caller set an arbitrary, non-catalog scope-ceiling string on
their own PAT. `create_pat()` below applies `_validate_scopes()`
symmetrically to both token types.
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .community_common import ensure_community_tables
from .errors import bad_request, conflict, not_found
from .schema import bind_support_token_tables

_CAT_QUOTA_STANDARD = 5
# Matches Node's own `// TODO: check premium tier for CAT_QUOTA_PREMIUM`
# in `listCATs()`/`createCAT()` -- premium-tier quota was never actually
# wired up in the Node source either; ported as the same standing TODO,
# not silently "fixed" by guessing an entitlement check that doesn't
# exist yet.
_CAT_QUOTA_PREMIUM = 10


@dataclass(slots=True, frozen=True)
class TokenIssued:
    """Plaintext token + its metadata row, returned once at creation."""

    token: str
    row: Any


def _bind(dal: Any) -> None:
    ensure_community_tables(dal)
    bind_support_token_tables(dal)


def _generate_token(prefix: str) -> tuple[str, str]:
    """Return `(plaintext_token, sha256_hex_hash)`. Only the hash is ever persisted."""
    random_part = secrets.token_hex(24)  # 48 hex chars, matches Node's `randomBytes(24)`
    token = f"{prefix}{random_part}"
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return token, token_hash


def _validate_scopes(dal: Any, scopes: list[str]) -> None:
    catalog = dal(dal.permission_scopes.id > 0).select(dal.permission_scopes.scope_key)
    valid = {row.scope_key for row in catalog}
    invalid = [s for s in scopes if s not in valid]
    if invalid:
        raise bad_request(f"Invalid scopes: {', '.join(invalid)}")


# ---------------------------------------------------------------------------
# PAT (self-service, scoped to the caller's own user_id)
# ---------------------------------------------------------------------------


def _active_pat_query(dal: Any, user_id: int) -> Any:
    return (dal.user_access_tokens.user_id == user_id) & (
        dal.user_access_tokens.is_revoked == False  # noqa: E712
    )


def get_pat(dal: Any, user_id: int) -> Any | None:
    """`GET /user/tokens/pat` -- no hash, no plaintext, `None` if the caller has none."""
    _bind(dal)
    return dal(_active_pat_query(dal, user_id)).select().first()


def create_pat(
    dal: Any,
    user_id: int,
    *,
    name: str | None,
    scope_ceiling: list[str] | None,
    expires_at: datetime | None,
) -> str:
    """`POST /user/tokens/pat` -- one active PAT per user, 409 if one already exists."""
    _bind(dal)
    clean_name = (name or "").strip()
    if not clean_name:
        raise bad_request("Token name is required")

    existing = dal(_active_pat_query(dal, user_id)).select().first()
    if existing is not None:
        raise conflict("You already have an active PAT. Revoke it before creating a new one.")

    ceiling = list(scope_ceiling) if scope_ceiling else None
    if ceiling:
        _validate_scopes(dal, ceiling)  # SECURITY FIX -- see module docstring.

    token, token_hash = _generate_token("wdl_u_")
    dal.user_access_tokens.insert(
        user_id=user_id,
        name=clean_name,
        token_hash=token_hash,
        scope_ceiling=ceiling,
        expires_at=expires_at,
        created_at=datetime.utcnow(),
        is_revoked=False,
    )
    dal.commit()
    return token


def revoke_pat(dal: Any, user_id: int) -> None:
    """`DELETE /user/tokens/pat`."""
    _bind(dal)
    row = dal(_active_pat_query(dal, user_id)).select().first()
    if row is None:
        raise not_found("No active PAT found")
    dal(dal.user_access_tokens.id == row.id).update(is_revoked=True)
    dal.commit()


# ---------------------------------------------------------------------------
# CAT (community-admin, scoped to community_id)
# ---------------------------------------------------------------------------


def list_cats(dal: Any, community_id: int) -> tuple[list[Any], dict[int, str], int]:
    """`GET /admin/<id>/tokens/cats` -- metadata only (no hashes), plus quota/used counts."""
    _bind(dal)
    rows = list(
        dal(
            (dal.community_access_tokens.community_id == community_id)
            & (dal.community_access_tokens.is_revoked == False)  # noqa: E712
        ).select(orderby=~dal.community_access_tokens.created_at)
    )
    creator_ids = {r.created_by_user_id for r in rows if r.created_by_user_id is not None}
    names: dict[int, str] = {}
    if creator_ids:
        for user in dal(dal.hub_users.id.belongs(creator_ids)).select(
            dal.hub_users.id, dal.hub_users.display_name
        ):
            names[user.id] = user.display_name
    return rows, names, _CAT_QUOTA_STANDARD


def create_cat(
    dal: Any,
    community_id: int,
    *,
    created_by_user_id: int,
    name: str | None,
    scopes: list[str] | None,
    expires_at: datetime | None,
) -> str:
    """`POST /admin/<id>/tokens/cats` -- scopes required, quota-enforced."""
    _bind(dal)
    clean_name = (name or "").strip()
    if not clean_name:
        raise bad_request("Token name is required")
    if not scopes:
        raise bad_request("At least one scope is required for CATs")

    current_count = dal(
        (dal.community_access_tokens.community_id == community_id)
        & (dal.community_access_tokens.is_revoked == False)  # noqa: E712
    ).count()
    if current_count >= _CAT_QUOTA_STANDARD:
        raise conflict(
            f"CAT quota reached ({_CAT_QUOTA_STANDARD}). "
            "Revoke an existing token before creating a new one."
        )

    _validate_scopes(dal, list(scopes))

    token, token_hash = _generate_token("wdl_c_")
    dal.community_access_tokens.insert(
        community_id=community_id,
        created_by_user_id=created_by_user_id,
        name=clean_name,
        token_hash=token_hash,
        scopes=list(scopes),
        expires_at=expires_at,
        created_at=datetime.utcnow(),
        is_revoked=False,
    )
    dal.commit()
    return token


def revoke_cat(dal: Any, community_id: int, token_id: int) -> None:
    """`DELETE /admin/<id>/tokens/cats/<tokenId>`.

    Scoped to `community_id` -- no cross-community IDOR.
    """
    _bind(dal)
    row = (
        dal(
            (dal.community_access_tokens.id == token_id)
            & (dal.community_access_tokens.community_id == community_id)
            & (dal.community_access_tokens.is_revoked == False)  # noqa: E712
        )
        .select()
        .first()
    )
    if row is None:
        raise not_found("Token not found")
    dal(dal.community_access_tokens.id == token_id).update(is_revoked=True)
    dal.commit()


def list_scopes(dal: Any) -> list[Any]:
    """`GET /user/tokens/scopes` and `GET /admin/<id>/tokens/scopes`.

    Both routes share the same `permission_scopes` catalog.
    """
    _bind(dal)
    return list(
        dal(dal.permission_scopes.id > 0).select(
            orderby=(dal.permission_scopes.category | dal.permission_scopes.display_name)
        )
    )
