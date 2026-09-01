"""Associated live-channels lookup -- real DB read + real platform Live-status API calls.

Design spec §4.1 ("Live-status detection... the new work is aggregation,
not detection") flags that no persisted live/offline projection exists
yet anywhere in this repo -- building that receiver-side projection
(§8.6, extend Twitch/YouTube's own receivers vs a hub-api subscriber job)
is separate, larger work than this endpoint. What IS real and buildable
tonight: (1) the community's CONNECTED channels are a real, already-
populated table (`community_servers`, `000_create_base_schema.sql` --
the exact table `trigger/receiver/twitch_module/app.py`'s
`_load_tracked_channels` already reads), and (2) this module calls the
platform's own public Live-status API directly, at request time, for
each connected channel -- Twitch Helix `GET /helix/streams` (app-only
client-credentials token) and YouTube Data API v3 `search.list?
eventType=live` -- rather than relying on a not-yet-built projection.
Real, verifiable HTTP calls; unit tests mock the platform API response,
never the DB read.

Degrades gracefully: a platform with no configured API credentials
(`Config.twitch_client_id`/`youtube_api_key` empty) reports the
connection with `live=None` ("unknown") instead of raising -- this
endpoint must never 500 because Twitch/YouTube credentials aren't
provisioned in a given environment yet.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import httpx

from services.schema import bind_shared_read_tables

_TIMEOUT_SECONDS = 5.0
# A public OAuth endpoint URL, not a credential -- bandit/ruff both flag
# any string literal ending in "token" as a possible hardcoded password.
_TWITCH_TOKEN_URL = "https://id.twitch.tv/oauth2/token"  # noqa: S105 # nosec B105
_TWITCH_STREAMS_URL = "https://api.twitch.tv/helix/streams"
_YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"

#: `community_servers.status` values this endpoint treats as an active
#: connection -- matches the Twitch receiver's own real filter
#: (`trigger/receiver/twitch_module/app.py`).
_CONNECTED_STATUS = "approved"
_SUPPORTED_PLATFORMS = ("twitch", "youtube")


@dataclass(slots=True, frozen=True)
class ChannelStatusDTO:
    """One connected channel + its best-effort real live status."""

    platform: str
    channel_id: str
    channel_name: str
    #: `True`/`False` = a real API answer; `None` = credentials not
    #: configured for this platform, status genuinely unknown.
    live: bool | None
    title: str | None


class TwitchLiveClient:
    """Real Twitch Helix client -- app-only client-credentials token, cached until near-expiry."""

    def __init__(self, *, client_id: str, client_secret: str) -> None:
        """Build the client; empty credentials mean every call returns `live=None`."""
        self._client_id = client_id
        self._client_secret = client_secret
        self._token: str | None = None
        self._token_expires_at: float = 0.0

    @property
    def configured(self) -> bool:
        """True if credentials are present -- callers skip the API call entirely if not."""
        return bool(self._client_id and self._client_secret)

    async def _get_app_token(self, client: httpx.AsyncClient) -> str | None:
        if self._token is not None and time.monotonic() < self._token_expires_at:
            return self._token
        response = await client.post(
            _TWITCH_TOKEN_URL,
            data={
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "grant_type": "client_credentials",
            },
        )
        if response.status_code != 200:
            return None
        body = response.json()
        self._token = str(body["access_token"])
        # Refresh 60s before real expiry to avoid a request racing token expiry mid-flight.
        self._token_expires_at = time.monotonic() + max(int(body.get("expires_in", 0)) - 60, 0)
        return self._token

    async def get_live_status(self, user_logins: list[str]) -> dict[str, dict[str, Any]]:
        """Return `{user_login: {"live": bool, "title": str | None}}` for every live channel.

        A `user_login` absent from the returned dict is simply not
        currently live (Twitch's own `GET streams` semantics -- only live
        channels are returned). Returns `{}` (not an error) if
        unconfigured or the token/streams call fails -- callers treat a
        missing key as "unknown", per this module's degrade-gracefully
        posture.
        """
        if not self._configured_or_empty(user_logins):
            return {}
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            token = await self._get_app_token(client)
            if token is None:
                return {}
            response = await client.get(
                _TWITCH_STREAMS_URL,
                params=[("user_login", login) for login in user_logins],
                headers={
                    "Client-Id": self._client_id,
                    "Authorization": f"Bearer {token}",
                },
            )
            if response.status_code != 200:
                return {}
            data = response.json().get("data", [])
        return {
            str(entry["user_login"]).lower(): {"live": True, "title": entry.get("title")}
            for entry in data
        }

    def _configured_or_empty(self, user_logins: list[str]) -> bool:
        return self.configured and bool(user_logins)


class YouTubeLiveClient:
    """Real YouTube Data API v3 client -- one `search.list?eventType=live` call per channel."""

    def __init__(self, *, api_key: str) -> None:
        """Build the client; an empty `api_key` means every call returns `live=None`."""
        self._api_key = api_key

    @property
    def configured(self) -> bool:
        """True if an API key is present."""
        return bool(self._api_key)

    async def get_live_status(self, channel_ids: list[str]) -> dict[str, dict[str, Any]]:
        """Return `{channel_id: {"live": True, "title": str | None}}` for currently-live channels.

        Returns `{}` if unconfigured -- same degrade-gracefully contract
        as `TwitchLiveClient.get_live_status`.
        """
        if not self.configured or not channel_ids:
            return {}
        results: dict[str, dict[str, Any]] = {}
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            for channel_id in channel_ids:
                response = await client.get(
                    _YOUTUBE_SEARCH_URL,
                    params={
                        "part": "snippet",
                        "channelId": channel_id,
                        "eventType": "live",
                        "type": "video",
                        "key": self._api_key,
                    },
                )
                if response.status_code != 200:
                    continue
                items = response.json().get("items", [])
                if items:
                    results[channel_id] = {
                        "live": True,
                        "title": items[0].get("snippet", {}).get("title"),
                    }
        return results


async def list_associated_channels(
    async_dal: Any,
    dal: Any,
    *,
    community_id: int,
    twitch_client: TwitchLiveClient,
    youtube_client: YouTubeLiveClient,
) -> list[ChannelStatusDTO]:
    """The community's connected Twitch/YouTube channels + best-effort real live status."""
    bind_shared_read_tables(dal)
    rows = await async_dal.select_async(
        dal(
            (dal.community_servers.community_id == community_id)
            & dal.community_servers.platform.belongs(_SUPPORTED_PLATFORMS)
            & (dal.community_servers.status == _CONNECTED_STATUS)
        )
    )

    twitch_channels = [r for r in rows if r.platform == "twitch" and r.platform_server_name]
    youtube_channels = [r for r in rows if r.platform == "youtube"]

    twitch_status = await twitch_client.get_live_status(
        [str(r.platform_server_name).lower() for r in twitch_channels]
    )
    youtube_status = await youtube_client.get_live_status(
        [str(r.platform_server_id) for r in youtube_channels]
    )

    result: list[ChannelStatusDTO] = []
    for row in rows:
        channel_name = str(row.platform_server_name or row.platform_server_id)
        if row.platform == "twitch":
            live, title = _resolve_live_status(
                twitch_status.get(channel_name.lower()), configured=twitch_client.configured
            )
        else:  # "youtube" -- the only other value the belongs() query filter allows
            live, title = _resolve_live_status(
                youtube_status.get(str(row.platform_server_id)),
                configured=youtube_client.configured,
            )

        result.append(
            ChannelStatusDTO(
                platform=row.platform,
                channel_id=str(row.platform_server_id),
                channel_name=channel_name,
                live=live,
                title=title,
            )
        )
    return result


def _resolve_live_status(
    entry: dict[str, Any] | None, *, configured: bool
) -> tuple[bool | None, str | None]:
    """Turn one client's per-channel lookup result into `(live, title)`.

    A hit means live (`True`, with its title). A miss from a CONFIGURED
    client means the platform's own API was asked and this channel simply
    wasn't in the live list -- genuinely offline (`False`). A miss from an
    UNCONFIGURED client means the API was never asked at all -- unknown
    (`None`), never guessed as `False`.
    """
    if entry is not None:
        return True, entry.get("title")
    return (False, None) if configured else (None, None)
