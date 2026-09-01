"""Community live-stream listings -- ported from `streamController.js`.

Member-scoped (Node: `requireMember`, mounted under `routes/community.js`
at `/:communityId/streams*`, aliased to both `/api/v1/community/*` and
`/api/v1/communities/*` -- `frontend/src/services/api.js`'s `streamApi`
uses the plural form). Reads two real, pre-existing tables --
`coordination` (`004_add_missing_tables.sql`) and `community_servers`
(`000_create_base_schema.sql`) -- no schema gap here, unlike
`music_service.py`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from services.errors import not_found

#: Node hardcodes this filter in every query (`co.platform = 'twitch'`) --
#: byte-faithful, not a platform allowlist this port invented.
_LIVE_PLATFORM = "twitch"


@dataclass(slots=True, frozen=True)
class LiveStreamDTO:
    """Wire DTO for one live stream row -- camelCase pinned to `api.js`."""

    entityId: str
    platform: str
    channelId: str | None
    channelName: str | None
    isLive: bool
    liveSince: str | None
    viewerCount: int
    title: str
    game: str
    thumbnailUrl: str


@dataclass(slots=True, frozen=True)
class StreamDetailsDTO(LiveStreamDTO):
    """`LiveStreamDTO` plus `lastActivity` -- only `getStreamDetails` returns this field."""

    lastActivity: str | None = None


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _join_query(dal: Any, community_id: int) -> Any:
    """Port of the `coordination JOIN community_servers` `WHERE` clause every function shares."""
    return (
        (dal.community_servers.community_id == community_id)
        & (dal.community_servers.status == "approved")
        & (dal.community_servers.platform == dal.coordination.platform)
        & (dal.community_servers.platform_server_id == dal.coordination.server_id)
        & (dal.coordination.platform == _LIVE_PLATFORM)
        & (dal.coordination.is_live == True)  # noqa: E712 - pydal Field comparison
    )


def _stream_dto(row: Any) -> LiveStreamDTO:
    return LiveStreamDTO(
        entityId=row.entity_id,
        platform=row.platform,
        channelId=row.channel_id,
        channelName=row.channel_name or row.channel_id,
        isLive=bool(row.is_live),
        liveSince=_iso(row.live_since),
        viewerCount=row.viewer_count or 0,
        title=row.stream_title or "",
        game=row.game_name or "",
        thumbnailUrl=row.thumbnail_url or "",
    )


async def get_live_streams(async_dal: Any, dal: Any, *, community_id: int) -> list[LiveStreamDTO]:
    """Port of `getLiveStreams` -- ordered by `viewer_count DESC`, no limit."""
    # Implicit-join pydal query builder (Gotcha #6: selecting fields from
    # ONLY `coordination` -> flat rows, `row.entity_id` not
    # `row.coordination.entity_id`) -- not raw SQL (Gotcha #1).
    rows = await async_dal.select_async(
        dal(_join_query(dal, community_id)),
        dal.coordination.ALL,
        orderby=~dal.coordination.viewer_count,
    )
    return [_stream_dto(row) for row in rows]


async def get_featured_streams(
    async_dal: Any, dal: Any, *, community_id: int
) -> list[LiveStreamDTO]:
    """Port of `getFeaturedStreams` -- same query, top 5 by viewer count."""
    rows = await async_dal.select_async(
        dal(_join_query(dal, community_id)),
        dal.coordination.ALL,
        orderby=~dal.coordination.viewer_count,
        limitby=(0, 5),
    )
    return [_stream_dto(row) for row in rows]


async def get_stream_details(
    async_dal: Any, dal: Any, *, community_id: int, entity_id: str
) -> StreamDetailsDTO:
    """Port of `getStreamDetails` -- raises 404 if no matching live stream row."""
    query = _join_query(dal, community_id) & (dal.coordination.entity_id == entity_id)
    rows = await async_dal.select_async(dal(query), dal.coordination.ALL)
    if not rows:
        raise not_found("Stream not found")
    row = rows.first()
    base = _stream_dto(row)
    return StreamDetailsDTO(
        entityId=base.entityId,
        platform=base.platform,
        channelId=base.channelId,
        channelName=base.channelName,
        isLive=base.isLive,
        liveSince=base.liveSince,
        viewerCount=base.viewerCount,
        title=base.title,
        game=base.game,
        thumbnailUrl=base.thumbnailUrl,
        lastActivity=_iso(row.last_updated),
    )
