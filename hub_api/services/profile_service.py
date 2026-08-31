"""Self-service profile management -- ported from `profileController.js`.

Only the owner-scoped subset mounted under `routes/user.js` in Node
(`getMyProfile`/`updateMyProfile`/`uploadAvatar`/`deleteAvatar`/
`getMyLinkedPlatforms`) -- `getPublicProfile` (`/api/v1/public/users/
:userId/profile`) and `getMemberProfile` (`/api/v1/communities/:id/
members/:userId/profile`) are mounted under `public.js`/`community.js`
routes respectively, which belong to the Public and Tenancy groups (M2/
elsewhere in the migration plan), not M1. Ported when those groups land.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from services.errors import bad_request, unauthorized
from services.storage_service import (
    MAX_AVATAR_SIZE_BYTES,
    delete_object,
    is_allowed_image_type,
    upload_avatar,
)

VALID_VISIBILITIES = ("public", "registered", "shared_communities", "community_leaders")
_COUNTRY_CODE_RE = re.compile(r"^[A-Z]{2}$")


def _is_valid_url(value: str) -> bool:
    return value.startswith("http://") or value.startswith("https://")


async def get_my_profile(async_dal: Any, dal: Any, *, user_id: int) -> dict[str, Any] | None:
    """Get my profile."""
    # pydal query builder + LEFT JOIN (not raw SQL) -- portable across
    # DB_TYPE backends and the only form testable against sqlite; see
    # user_management_service.py's list_users() for the same rationale and
    # hub_api/PORTING.md's async_dal-raw-SQL-is-Postgres-only gotcha.
    rows = await async_dal.select_async(
        dal((dal.hub_users.id == user_id) & (dal.hub_users.is_active == True)),  # noqa: E712
        dal.hub_users.ALL,
        dal.hub_user_profiles.ALL,
        left=dal.hub_user_profiles.on(dal.hub_users.id == dal.hub_user_profiles.hub_user_id),
    )
    if not rows:
        return None
    u, p = rows[0].hub_users, rows[0].hub_user_profiles
    return {
        "userId": u.id,
        "username": u.username,
        "displayName": p.display_name,
        "avatarUrl": p.custom_avatar_url or u.avatar_url,
        "bannerUrl": p.banner_url,
        "bio": p.bio,
        "location": p.location,
        "locationCity": p.location_city,
        "locationState": p.location_state,
        "locationCountry": p.location_country,
        "websiteUrl": p.website_url,
        "visibility": p.visibility or "shared_communities",
        "showActivity": p.show_activity is not False,
        "showCommunities": p.show_communities is not False,
        "memberSince": u.created_at,
    }


async def update_my_profile(
    async_dal: Any, dal: Any, *, user_id: int, fields: dict[str, Any]
) -> dict[str, Any]:
    """Update my profile."""
    visibility = fields.get("visibility")
    if visibility and visibility not in VALID_VISIBILITIES:
        raise bad_request("Invalid visibility setting")

    website_url = fields.get("websiteUrl")
    if website_url and not _is_valid_url(website_url):
        raise bad_request("Invalid website URL")

    bio = fields.get("bio")
    if bio and len(bio) > 2000:
        raise bad_request("Bio must be 2000 characters or less")

    country = fields.get("locationCountry")
    if country and not _COUNTRY_CODE_RE.match(country):
        raise bad_request("Invalid country code (use ISO 3166-1 alpha-2)")

    existing = await async_dal.select_async(dal(dal.hub_user_profiles.hub_user_id == user_id))
    update_fields = {
        "display_name": fields.get("displayName"),
        "bio": bio,
        "location": fields.get("location"),
        "location_city": fields.get("locationCity"),
        "location_state": fields.get("locationState"),
        "location_country": country,
        "website_url": website_url,
        "visibility": visibility,
        "show_activity": fields.get("showActivity"),
        "show_communities": fields.get("showCommunities"),
        "updated_at": datetime.now(UTC),
    }
    # COALESCE semantics: only overwrite fields explicitly provided (non-None).
    update_fields = {k: v for k, v in update_fields.items() if v is not None}

    if existing:
        await async_dal.update_async(dal.hub_user_profiles.hub_user_id == user_id, **update_fields)
    else:
        await async_dal.insert_async(dal.hub_user_profiles, hub_user_id=user_id, **update_fields)

    profile = await get_my_profile(async_dal, dal, user_id=user_id)
    assert profile is not None  # nosec B101 - user_id is the caller's own, already authenticated
    return profile


async def upload_my_avatar(
    async_dal: Any,
    dal: Any,
    *,
    user_id: int,
    data: bytes,
    filename: str,
    content_type: str,
    size: int,
) -> str:
    """Upload my avatar."""
    if not is_allowed_image_type(content_type):
        raise bad_request("Invalid file type. Allowed: JPEG, PNG, GIF, WebP")
    if size > MAX_AVATAR_SIZE_BYTES:
        raise bad_request("File too large. Maximum size: 5MB")

    old = await async_dal.select_async(dal(dal.hub_user_profiles.hub_user_id == user_id))
    if old and old.first().custom_avatar_url:
        await delete_object(old.first().custom_avatar_url)

    avatar_url = await upload_avatar(data, filename, content_type)

    if old:
        await async_dal.update_async(
            dal.hub_user_profiles.hub_user_id == user_id,
            custom_avatar_url=avatar_url,
            updated_at=datetime.now(UTC),
        )
    else:
        await async_dal.insert_async(
            dal.hub_user_profiles,
            hub_user_id=user_id,
            custom_avatar_url=avatar_url,
            updated_at=datetime.now(UTC),
        )
    await async_dal.update_async(
        dal.hub_users.id == user_id, avatar_url=avatar_url, updated_at=datetime.now(UTC)
    )
    return avatar_url


async def delete_my_avatar(async_dal: Any, dal: Any, *, user_id: int) -> str | None:
    """Delete my avatar."""
    rows = await async_dal.select_async(dal(dal.hub_user_profiles.hub_user_id == user_id))
    if rows and rows.first().custom_avatar_url:
        await delete_object(rows.first().custom_avatar_url)
        await async_dal.update_async(
            dal.hub_user_profiles.hub_user_id == user_id,
            custom_avatar_url=None,
            updated_at=datetime.now(UTC),
        )

    fallback_rows = await async_dal.select_async(
        dal(
            (dal.hub_user_identities.hub_user_id == user_id)
            & (dal.hub_user_identities.avatar_url != None)  # noqa: E711 - pydal Field comparison
        ),
        orderby=~dal.hub_user_identities.linked_at,
        limitby=(0, 1),
    )
    fallback_avatar = fallback_rows[0].avatar_url if fallback_rows else None

    await async_dal.update_async(
        dal.hub_users.id == user_id, avatar_url=fallback_avatar, updated_at=datetime.now(UTC)
    )
    return fallback_avatar


@dataclass(slots=True, frozen=True)
class LinkedPlatform:
    """One linked platform identity (`platform` is always populated; the rest may be null)."""

    platform: str
    username: str | None
    avatar_url: str | None


async def get_my_linked_platforms(
    async_dal: Any, dal: Any, *, user_id: int
) -> list[LinkedPlatform]:
    """Get my linked platforms."""
    rows = await async_dal.select_async(
        dal(dal.hub_user_identities.hub_user_id == user_id),
        orderby=~dal.hub_user_identities.linked_at,
    )
    return [
        LinkedPlatform(platform=r.platform, username=r.platform_username, avatar_url=r.avatar_url)
        for r in rows
    ]


def require_user_id(user_id: int | None) -> int:
    """Require user id."""
    if user_id is None:
        raise unauthorized("Authentication required")
    return user_id
