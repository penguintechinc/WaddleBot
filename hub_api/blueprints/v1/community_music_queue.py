"""v1 `music-station` group -- per-community queue, policy, and moderation.

New feature, not a Node port -- the advertised Music Station surface:
song requests + whole-playlist submissions resolved via `services.
music_providers.resolve()` into a normalized `Track`, an intermingled
per-community queue (mixed providers, now-playing + upcoming), a
per-community policy (`songRequestsAllowed`/`requestsCategoryRestricted`),
and community-admin moderation (kick a song, kick a whole playlist,
override the category restriction for one request) -- every moderation
action audited to `music_moderation_log`.

Mounted at `/api/v1/admin/<community_id>/music-station/*`, the same URL
namespace `blueprints/v1/music.py`/`community_raffle.py` already use for
community-management surfaces (not literal superadmin-only -- see those
modules' own docstrings). Auth follows the M7 Streaming group's `_scoped`
pattern (`services.community_authz.authorize_community()`): tenant
ownership of `community_id` is re-validated on every call (IDOR
hardening beyond a bare membership check), then either member (`admin=
False`, self-service song requests/listing) or admin/moderator (`admin=
True`, policy + all moderation actions) scope is required.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

from flask_core.api_utils import error_response
from flask_core.tenancy import get_tenant_context, tenant_middleware
from quart import Blueprint, current_app, request
from quart_schema import validate_request, validate_response

from services import community_music_queue_service as svc
from services.community_authz import authorize_community
from services.current_user import get_current_user_id, get_optional_current_user_id
from services.dto_response import jsonify_dto
from services.errors import ApiError, bad_request

music_queue_bp = Blueprint("v1_community_music_queue", __name__, url_prefix="/api/v1/admin")


def _dal() -> tuple[Any, Any]:
    """Return `(async_dal, dal)` from app config -- tables already bound at startup."""
    return current_app.config["async_dal"], current_app.config["dal"]


def _tenant_id() -> int:
    ctx = get_tenant_context(request)
    assert ctx is not None  # nosec B101 - tenant_middleware always runs first
    return cast(int, ctx.tenant_id)


def _err(exc: ApiError) -> tuple[dict[str, object], int]:
    return cast(
        tuple[dict[str, object], int], error_response(exc.message, exc.status_code, exc.code)
    )


# ---------------------------------------------------------------------------
# Request/response DTOs -- camelCase pinned to this group's own new JSON
# contract (see services/community_music_queue_service.py's own "DTO
# casing" note).
# ---------------------------------------------------------------------------


@dataclass(slots=True, frozen=True)
class SetPolicyRequest:
    """Request DTO for `PUT .../music-station/policy` -- both fields optional (partial update)."""

    songRequestsAllowed: bool | None = None
    requestsCategoryRestricted: bool | None = None


@dataclass(slots=True, frozen=True)
class PolicyResponse:
    """Response DTO wrapping `PolicyDTO`."""

    success: bool
    policy: svc.PolicyDTO


@dataclass(slots=True, frozen=True)
class EnqueueRequestRequest:
    """Request DTO for `POST .../music-station/queue/requests`."""

    urlOrQuery: str
    provider: str | None = None
    overrideCategoryRestriction: bool = False


@dataclass(slots=True, frozen=True)
class EnqueuePlaylistRequest:
    """Request DTO for `POST .../music-station/queue/playlists`."""

    items: list[str]
    provider: str | None = None
    overrideCategoryRestriction: bool = False


@dataclass(slots=True, frozen=True)
class QueueItemResponse:
    """Response DTO wrapping one `QueueItemDTO`."""

    success: bool
    item: svc.QueueItemDTO


@dataclass(slots=True, frozen=True)
class PlaylistEnqueueResponse:
    """Response DTO for a playlist enqueue -- created items plus the shared playlist id."""

    success: bool
    playlistId: str
    items: list[svc.QueueItemDTO]


@dataclass(slots=True, frozen=True)
class QueueListResponse:
    """Response DTO for `GET .../music-station/queue`."""

    success: bool
    nowPlaying: svc.QueueItemDTO | None
    upcoming: list[svc.QueueItemDTO]


@dataclass(slots=True, frozen=True)
class ReorderQueueRequest:
    """Request DTO for `PUT .../music-station/queue/reorder`."""

    orderedQueueIds: list[int]


@dataclass(slots=True, frozen=True)
class AdvanceResponse:
    """Response DTO for `POST .../music-station/queue/advance`."""

    success: bool
    previous: svc.QueueItemDTO | None
    next: svc.QueueItemDTO | None


@dataclass(slots=True, frozen=True)
class MessageResponse:
    """Generic `{success, message}` response DTO."""

    success: bool
    message: str


# ---------------------------------------------------------------------------
# Policy
# ---------------------------------------------------------------------------


@music_queue_bp.route("/<int:community_id>/music-station/policy", methods=["GET"])
@tenant_middleware  # type: ignore[untyped-decorator]
@validate_response(PolicyResponse)
async def get_policy(community_id: int) -> PolicyResponse | tuple[dict[str, object], int]:
    """Get the community's Music Station policy (community admin only)."""
    async_dal, dal = _dal()
    try:
        await authorize_community(request, async_dal, dal, community_id=community_id, admin=True)
        tenant_id = _tenant_id()
        policy = await svc.get_policy(
            async_dal, dal, tenant_id=tenant_id, community_id=community_id
        )
    except ApiError as exc:
        return _err(exc)
    return PolicyResponse(success=True, policy=policy)


@music_queue_bp.route("/<int:community_id>/music-station/policy", methods=["PUT"])
@tenant_middleware  # type: ignore[untyped-decorator]
@validate_request(SetPolicyRequest)
# NOT @validate_response -- writes via insert_async/update_async then
# returns a nested-dataclass response (services/dto_response.py's
# documented crash class). jsonify_dto() is the workaround.
async def set_policy(data: SetPolicyRequest, community_id: int) -> Any:
    """Set the community's Music Station policy (community admin only)."""
    async_dal, dal = _dal()
    try:
        await authorize_community(request, async_dal, dal, community_id=community_id, admin=True)
        actor_id = get_optional_current_user_id(request)
        policy = await svc.set_policy(
            async_dal,
            dal,
            tenant_id=_tenant_id(),
            community_id=community_id,
            song_requests_allowed=data.songRequestsAllowed,
            requests_category_restricted=data.requestsCategoryRestricted,
            updated_by=actor_id,
        )
    except ApiError as exc:
        return _err(exc)
    return jsonify_dto(PolicyResponse(success=True, policy=policy))


# ---------------------------------------------------------------------------
# Queue: enqueue
# ---------------------------------------------------------------------------


@music_queue_bp.route("/<int:community_id>/music-station/queue/requests", methods=["POST"])
@tenant_middleware  # type: ignore[untyped-decorator]
@validate_request(EnqueueRequestRequest)
async def enqueue_song_request(data: EnqueueRequestRequest, community_id: int) -> Any:
    """Submit a single song request -- self-service, gated by community policy."""
    async_dal, dal = _dal()
    try:
        await authorize_community(
            request,
            async_dal,
            dal,
            community_id=community_id,
            admin=data.overrideCategoryRestriction,
        )
        requester_id = get_current_user_id(request)
        item = await svc.enqueue_request(
            async_dal,
            dal,
            tenant_id=_tenant_id(),
            community_id=community_id,
            url_or_query=data.urlOrQuery,
            provider=data.provider,
            requested_by=requester_id,
            is_admin_override=data.overrideCategoryRestriction,
        )
    except ApiError as exc:
        return _err(exc)
    return jsonify_dto(QueueItemResponse(success=True, item=item), 201)


@music_queue_bp.route("/<int:community_id>/music-station/queue/playlists", methods=["POST"])
@tenant_middleware  # type: ignore[untyped-decorator]
@validate_request(EnqueuePlaylistRequest)
async def enqueue_playlist_request(data: EnqueuePlaylistRequest, community_id: int) -> Any:
    """Submit a whole playlist (list of URLs/queries) -- self-service, gated by community policy."""
    async_dal, dal = _dal()
    try:
        await authorize_community(
            request,
            async_dal,
            dal,
            community_id=community_id,
            admin=data.overrideCategoryRestriction,
        )
        requester_id = get_current_user_id(request)
        playlist_id, items = await svc.enqueue_playlist(
            async_dal,
            dal,
            tenant_id=_tenant_id(),
            community_id=community_id,
            items=data.items,
            provider=data.provider,
            requested_by=requester_id,
            is_admin_override=data.overrideCategoryRestriction,
        )
    except ApiError as exc:
        return _err(exc)
    return jsonify_dto(
        PlaylistEnqueueResponse(success=True, playlistId=playlist_id, items=items), 201
    )


# ---------------------------------------------------------------------------
# Queue: list
# ---------------------------------------------------------------------------


@music_queue_bp.route("/<int:community_id>/music-station/queue", methods=["GET"])
@tenant_middleware  # type: ignore[untyped-decorator]
@validate_response(QueueListResponse)
async def list_queue(community_id: int) -> QueueListResponse | tuple[dict[str, object], int]:
    """List the community's queue -- now-playing (if any) plus upcoming, in order."""
    async_dal, dal = _dal()
    try:
        await authorize_community(request, async_dal, dal, community_id=community_id, admin=False)
        now_playing, upcoming = await svc.list_queue(async_dal, dal, community_id=community_id)
    except ApiError as exc:
        return _err(exc)
    return QueueListResponse(success=True, nowPlaying=now_playing, upcoming=upcoming)


# ---------------------------------------------------------------------------
# Moderation: kick song / kick playlist
# ---------------------------------------------------------------------------


@music_queue_bp.route("/<int:community_id>/music-station/queue/<int:queue_id>", methods=["DELETE"])
@tenant_middleware  # type: ignore[untyped-decorator]
async def kick_song(community_id: int, queue_id: int) -> Any:
    """Kick a single song off the queue (community admin only) -- audited."""
    async_dal, dal = _dal()
    try:
        await authorize_community(request, async_dal, dal, community_id=community_id, admin=True)
        actor_id = get_current_user_id(request)
        reason = request.args.get("reason")
        await svc.kick_song(
            async_dal,
            dal,
            tenant_id=_tenant_id(),
            community_id=community_id,
            queue_id=queue_id,
            actor_user_id=actor_id,
            reason=reason,
        )
    except ApiError as exc:
        return _err(exc)
    return jsonify_dto(MessageResponse(success=True, message=f"Queue item {queue_id} removed"))


@music_queue_bp.route(
    "/<int:community_id>/music-station/queue/playlists/<playlist_id>", methods=["DELETE"]
)
@tenant_middleware  # type: ignore[untyped-decorator]
async def kick_playlist(community_id: int, playlist_id: str) -> Any:
    """Kick an entire playlist off the queue (community admin only) -- audited once."""
    async_dal, dal = _dal()
    try:
        await authorize_community(request, async_dal, dal, community_id=community_id, admin=True)
        actor_id = get_current_user_id(request)
        reason = request.args.get("reason")
        removed = await svc.kick_playlist(
            async_dal,
            dal,
            tenant_id=_tenant_id(),
            community_id=community_id,
            playlist_id=playlist_id,
            actor_user_id=actor_id,
            reason=reason,
        )
    except ApiError as exc:
        return _err(exc)
    return jsonify_dto(
        MessageResponse(success=True, message=f"Removed {removed} item(s) from playlist")
    )


# ---------------------------------------------------------------------------
# Queue: reorder / advance
# ---------------------------------------------------------------------------


@music_queue_bp.route("/<int:community_id>/music-station/queue/reorder", methods=["PUT"])
@tenant_middleware  # type: ignore[untyped-decorator]
@validate_request(ReorderQueueRequest)
async def reorder_queue(data: ReorderQueueRequest, community_id: int) -> Any:
    """Reorder the community's upcoming queue (community admin only)."""
    async_dal, dal = _dal()
    try:
        await authorize_community(request, async_dal, dal, community_id=community_id, admin=True)
        if not data.orderedQueueIds:
            raise bad_request("orderedQueueIds must not be empty")
        upcoming = await svc.reorder_queue(
            async_dal, dal, community_id=community_id, ordered_queue_ids=data.orderedQueueIds
        )
    except ApiError as exc:
        return _err(exc)
    now_playing, _ = await svc.list_queue(async_dal, dal, community_id=community_id)
    return jsonify_dto(QueueListResponse(success=True, nowPlaying=now_playing, upcoming=upcoming))


@music_queue_bp.route("/<int:community_id>/music-station/queue/advance", methods=["POST"])
@tenant_middleware  # type: ignore[untyped-decorator]
async def advance_queue(community_id: int) -> Any:
    """Advance the queue: mark now-playing played, promote the next queued track (admin only)."""
    async_dal, dal = _dal()
    try:
        await authorize_community(request, async_dal, dal, community_id=community_id, admin=True)
        previous, next_item = await svc.advance_queue(async_dal, dal, community_id=community_id)
    except ApiError as exc:
        return _err(exc)
    return jsonify_dto(AdvanceResponse(success=True, previous=previous, next=next_item))


BLUEPRINTS: list[Blueprint] = [music_queue_bp]
