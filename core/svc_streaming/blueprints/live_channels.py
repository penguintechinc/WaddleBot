"""Associated live-channels endpoint -- for the community "live streams" display.

`GET /api/v1/streaming/communities/<community_id>/live-channels`: the
community's connected Twitch/YouTube channels (real `community_servers`
DB read) plus a real, request-time live-status check against each
platform's own public API. See `services/live_channels_service.py`'s
module docstring for why this is the real, buildable-tonight shape of
design spec §4's DISPLAY capability (vs the not-yet-built receiver-side
live/offline projection, §4.1/§8.6).

Member-gated (any active community member), not admin-only -- this is a
read surface every member can see, same posture as `streaming.py`'s
`get_status` route.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from flask_core.api_utils import error_response
from flask_core.tenancy import get_tenant_context, tenant_middleware
from quart import Blueprint, current_app, request

from services import community_access
from services.dto_response import jsonify_dto
from services.errors import ApiError, forbidden
from services.live_channels_service import (
    TwitchLiveClient,
    YouTubeLiveClient,
    list_associated_channels,
)

live_channels_bp = Blueprint(
    "v1_streaming_live_channels", __name__, url_prefix="/api/v1/streaming/communities"
)

BLUEPRINTS: list[Blueprint] = [live_channels_bp]


def _err(exc: ApiError) -> tuple[dict[str, object], int]:
    return cast(
        tuple[dict[str, object], int], error_response(exc.message, exc.status_code, exc.code)
    )


@dataclass(slots=True, frozen=True)
class ChannelStatusDTO:
    """Wire shape for `live_channels_service.ChannelStatusDTO`."""

    platform: str
    channel_id: str
    channel_name: str
    live: bool | None
    title: str | None


@dataclass(slots=True, frozen=True)
class LiveChannelsResponse:
    """Response DTO for the associated-channels route."""

    success: bool
    community_id: int
    channels: list[ChannelStatusDTO]


@live_channels_bp.route("/<int:community_id>/live-channels", methods=["GET"])
@tenant_middleware  # type: ignore[untyped-decorator]
# NOT @validate_response -- see `blueprints/streaming.py`'s `list_targets`
# comment: this select-only route can still hit the quart-schema/
# pydantic-core crash once any insert has happened earlier in the same
# process (e.g. a stream config write) -- `jsonify_dto()` avoids it.
async def get_live_channels(
    community_id: int,
) -> tuple[object, int] | tuple[dict[str, object], int]:
    """The community's connected Twitch/YouTube channels + real live status."""
    async_dal, dal = current_app.config["async_dal"], current_app.config["dal"]
    cfg = current_app.config["APP_CONFIG"]
    try:
        ctx = get_tenant_context(request)
        if ctx is None:
            raise forbidden("Tenant context not resolved")
        user_id = community_access.decode_caller_user_id(request)
        await community_access.require_member(
            async_dal, dal, request, ctx, community_id=community_id, user_id=user_id
        )
        twitch_client = current_app.config.get("TWITCH_LIVE_CLIENT") or TwitchLiveClient(
            client_id=cfg.twitch_client_id, client_secret=cfg.twitch_client_secret
        )
        youtube_client = current_app.config.get("YOUTUBE_LIVE_CLIENT") or YouTubeLiveClient(
            api_key=cfg.youtube_api_key
        )
        channels = await list_associated_channels(
            async_dal,
            dal,
            community_id=community_id,
            twitch_client=twitch_client,
            youtube_client=youtube_client,
        )
    except ApiError as exc:
        return _err(exc)
    return jsonify_dto(
        LiveChannelsResponse(
            success=True,
            community_id=community_id,
            channels=[
                ChannelStatusDTO(
                    platform=c.platform,
                    channel_id=c.channel_id,
                    channel_name=c.channel_name,
                    live=c.live,
                    title=c.title,
                )
                for c in channels
            ],
        )
    )
