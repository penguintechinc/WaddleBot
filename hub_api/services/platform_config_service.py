"""Superadmin platform-config business logic -- ported from `platformConfigController.js`.

Only the subset mounted under `requireSuperAdmin` in Node's
`routes/superadmin.js` (`GET /platform-config`, `PUT /platform-config/
:platform`, `POST /platform-config/:platform/test`, `GET`/`PUT
/settings`) -- `platformConfigController.js`'s other static methods
(`getBotCredentials`, `get/create/update/deleteMyCredential`,
`get/create/update/deleteCommunityCredential`, `testCredential` by row
id) are mounted in `routes/user.js` (self-service) and `routes/admin.js`
(community-scoped), owned by the Identity (M1, self-service oauth) and
Platform-admin/`adminController` (community admin) groups respectively
-- not ported here (migration plan's own controller table lists
`adminController` as a SEPARATE Platform-admin-area controller from
`platformConfigController`; this M3 PR is scoped to the three named
controllers only). `hub_settings` is schema-owned by this group (see
`services/schema.py`'s own note); read access is shared with
`auth_service.get_hub_settings_map()` (register()/resend_verification()
need signup_enabled/email_configured), reused here rather than
duplicated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import httpx

from services.auth_service import get_hub_settings_map
from services.errors import not_found
from services.platform_integrations_crypto import decrypt_if_needed

_TWITCH_VALIDATE_URL = "https://id.twitch.tv/oauth2/validate"
_DISCORD_ME_URL = "https://discord.com/api/users/@me"
_SLACK_AUTH_TEST_URL = "https://slack.com/api/auth.test"
_YOUTUBE_CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels?part=id&mine=true"


@dataclass(slots=True, frozen=True)
class CredentialRow:
    """Shaped view of a `platform_integrations` row -- masked before this leaves the service."""

    id: int
    platform: str
    integration_type: str
    community_id: int | None
    user_id: int | None
    access_token_set: bool
    refresh_token_set: bool
    client_id: str | None
    client_secret_set: bool
    token_type: str | None
    expires_at: Any
    scopes: list[str] = field(default_factory=list)
    config_data: dict[str, Any] | None = None
    is_active: bool = True
    is_encrypted: bool = True
    created_at: Any = None
    updated_at: Any = None
    created_by_user_id: int | None = None
    updated_by_user_id: int | None = None


def _mask(row: Any) -> CredentialRow:
    """Mirror `formatCredential()` -- token/secret fields collapse to a presence flag."""
    return CredentialRow(
        id=row.id,
        platform=row.platform,
        integration_type=row.integration_type,
        community_id=row.community_id,
        user_id=row.user_id,
        access_token_set=bool(row.access_token),
        refresh_token_set=bool(row.refresh_token),
        client_id=row.client_id,
        client_secret_set=bool(row.client_secret),
        token_type=row.token_type,
        expires_at=row.expires_at,
        scopes=list(row.scopes) if row.scopes else [],
        config_data=row.config_data,
        is_active=bool(row.is_active),
        is_encrypted=bool(row.is_encrypted),
        created_at=row.created_at,
        updated_at=row.updated_at,
        created_by_user_id=row.created_by_user_id,
        updated_by_user_id=row.updated_by_user_id,
    )


async def get_platform_configs(
    async_dal: Any, dal: Any, *, integration_type: str | None, platform: str | None
) -> list[CredentialRow]:
    """List active platform integrations, optionally filtered by type/platform."""
    query = dal.platform_integrations.is_active == True  # noqa: E712
    if integration_type:
        query &= dal.platform_integrations.integration_type == integration_type
    if platform:
        query &= dal.platform_integrations.platform == platform

    rows = await async_dal.select_async(
        dal(query),
        orderby=dal.platform_integrations.platform
        | dal.platform_integrations.integration_type
        | ~dal.platform_integrations.created_at,
    )
    return [_mask(r) for r in rows]


async def update_platform_config(async_dal: Any, dal: Any, *, platform: str) -> None:
    """Update a bot credential by platform name.

    Node's own route (`superadmin.js`: `PUT /platform-config/:platform`)
    calls `PlatformConfigController.updatePlatformConfig`, which
    destructures `const { id } = req.params` -- but the route param is
    named `:platform`, not `:id`, so `id` is always `undefined`. The
    resulting `UPDATE platform_integrations ... WHERE id = $1` with
    `$1 = undefined` never matches a row (`id` is a `SERIAL PRIMARY KEY`,
    never NULL) -- this endpoint 404s "Credential not found" for every
    call, in Node, today, regardless of the request body. A faithful port
    reproduces exactly that outcome rather than guessing at a fix for a
    confusingly-underspecified feature (the route's own body validators
    check `client_id`/`client_secret`/`redirect_uri`/`enabled`, but the
    controller reads `clientId`/`clientSecret`/`accessToken`/... --
    disjoint field names -- and the one webui page that calls this
    endpoint, `BotCredentialTab.jsx`, reads `response.data.configs`,
    which doesn't exist on `getPlatformConfigs()`'s real `{success, data,
    count}` response shape either). Three independent, pre-existing
    contract breaks in one feature -- flagged for product/design
    follow-up, not silently patched over with an invented, unverifiable
    semantics here.
    """
    raise not_found("Credential not found")


_TESTERS: dict[str, tuple[str, str]] = {
    "twitch": (_TWITCH_VALIDATE_URL, "OAuth"),
    "discord": (_DISCORD_ME_URL, "Bearer"),
    "youtube": (_YOUTUBE_CHANNELS_URL, "Bearer"),
}


async def _test_token(platform: str, access_token: str) -> tuple[bool, str | None]:
    """Validate a bot access token against its platform's own API. Fails closed on any error."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            if platform == "slack":
                resp = await client.post(
                    _SLACK_AUTH_TEST_URL, headers={"Authorization": f"Bearer {access_token}"}
                )
                body = resp.json()
                return bool(body.get("ok")), None if body.get("ok") else "invalid token"
            if platform in _TESTERS:
                url, scheme = _TESTERS[platform]
                resp = await client.get(url, headers={"Authorization": f"{scheme} {access_token}"})
                return resp.is_success, None if resp.is_success else f"HTTP {resp.status_code}"
            # Unknown platform -- Node's own testPlatformCredential() default case.
            return True, None
    except httpx.HTTPError as exc:
        return False, str(exc)


async def test_platform_connection(
    async_dal: Any, dal: Any, *, platform: str
) -> tuple[bool, str | None]:
    """Test a platform's bot credential against the real provider API."""
    rows = await async_dal.select_async(
        dal(
            (dal.platform_integrations.platform == platform)
            & (dal.platform_integrations.integration_type == "bot")
            & (dal.platform_integrations.is_active == True)  # noqa: E712
        ),
        limitby=(0, 1),
    )
    if not rows:
        raise not_found(f"No credentials found for platform: {platform}")
    row = rows.first()
    if not row.access_token:
        return True, None
    # SECURITY (HIGH): `credential_manager_module`'s refresh service
    # encrypts this column at rest (`is_encrypted = TRUE`) -- decrypt
    # before sending to the platform's own validation API, or a
    # since-refreshed row sends ciphertext and reports a false
    # "invalid token". See `platform_integrations_crypto`'s own docstring.
    access_token = decrypt_if_needed(row.access_token, is_encrypted=bool(row.is_encrypted))
    return await _test_token(platform, access_token)


async def get_hub_settings(async_dal: Any, dal: Any) -> dict[str, str]:
    """Get every `hub_settings` key/value pair."""
    return await get_hub_settings_map(async_dal, dal)


async def update_hub_settings(
    async_dal: Any, dal: Any, *, updates: dict[str, Any]
) -> dict[str, str]:
    """Upsert `hub_settings` key/value pairs, return the full resulting map."""
    for key, value in updates.items():
        existing = await async_dal.select_async(dal(dal.hub_settings.setting_key == key))
        if existing:
            await async_dal.update_async(
                dal.hub_settings.setting_key == key,
                setting_value=str(value),
                updated_at=datetime.now(UTC),
            )
        else:
            await async_dal.insert_async(
                dal.hub_settings,
                setting_key=key,
                setting_value=str(value),
                updated_at=datetime.now(UTC),
            )
    return await get_hub_settings_map(async_dal, dal)
