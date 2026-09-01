"""v1 `streaming` control-plane group -- config/targets CRUD + real start/stop/status.

Mounted at `/api/v1/streaming/communities/<community_id>/*`, deliberately
its OWN prefix distinct from hub-api's legacy `/api/v1/admin/<community_id>
/streams/*` (`hub_api/blueprints/v1/streaming.py`, a pure reverse-proxy to
the M7-ported `video_proxy_module` standalone service) -- svc-streaming is
a separate, new container with its own owned data model (`services/
schema.py`) and its own real ffmpeg data plane (`services/
ffmpeg_engine.py`), not a replacement for that legacy path tonight (design
spec §6's absorption is staged/future work, see this PR's description).

Auth: `flask_core.tenancy.tenant_middleware` (tenant resolution) THEN
`services.community_access` (community membership/admin, ported from
`hub_api/services/community_access.py`) -- same two-layer ordering
security.md mandates. Writes (`config`, `targets`, `start`, `stop`)
require community-admin; reads (`status`) require any active member.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import cast

from flask_core.api_utils import error_response
from flask_core.tenancy import get_tenant_context, tenant_middleware
from quart import Blueprint, current_app, request
from quart_schema import validate_request

from services import community_access
from services import streaming_service as svc
from services.dto_response import jsonify_dto
from services.errors import ApiError, forbidden, not_found
from services.ffmpeg_engine import FFmpegSupervisor
from services.url_guard import validate_outbound_url

streaming_bp = Blueprint("v1_streaming", __name__, url_prefix="/api/v1/streaming/communities")

BLUEPRINTS: list[Blueprint] = [streaming_bp]


def _err(exc: ApiError) -> tuple[dict[str, object], int]:
    """Convert an `ApiError` into the shared `{success, error}` JSON envelope."""
    return cast(
        tuple[dict[str, object], int], error_response(exc.message, exc.status_code, exc.code)
    )


def _dal() -> tuple[object, object]:
    return current_app.config["async_dal"], current_app.config["dal"]


def _supervisor() -> FFmpegSupervisor:
    return cast(FFmpegSupervisor, current_app.config["FFMPEG_SUPERVISOR"])


def _bearer_token() -> str:
    auth_header = request.headers.get("Authorization", "")
    return auth_header[7:] if auth_header.startswith("Bearer ") else ""


async def _authorize(*, community_id: int, admin: bool) -> None:
    async_dal, dal = _dal()
    ctx = get_tenant_context(request)
    if ctx is None:
        raise forbidden("Tenant context not resolved")
    user_id = community_access.decode_caller_user_id(request)
    check = community_access.require_admin if admin else community_access.require_member
    await check(async_dal, dal, request, ctx, community_id=community_id, user_id=user_id)


# ---------------------------------------------------------------------------
# DTOs
# ---------------------------------------------------------------------------


@dataclass(slots=True, frozen=True)
class StreamConfigDTO:
    """Wire shape for `streaming_service.StreamConfigDTO`."""

    id: int
    community_id: int
    source_url: str
    source_type: str
    enabled: bool
    record_enabled: bool
    transcode_enabled: bool
    transcode_bitrate_kbps: int


@dataclass(slots=True, frozen=True)
class StreamConfigResponse:
    """Response DTO for the get/create/update-config routes."""

    success: bool
    config: StreamConfigDTO


@dataclass(slots=True, frozen=True)
class SetConfigRequest:
    """Request DTO for `PUT .../config`."""

    source_url: str
    source_type: str = "rtmp"
    record_enabled: bool = False
    transcode_enabled: bool = False
    transcode_bitrate_kbps: int = 4000


@dataclass(slots=True, frozen=True)
class ForwardTargetDTO:
    """Wire shape for `streaming_service.ForwardTargetDTO`."""

    id: int
    config_id: int
    platform: str
    forward_url: str
    enabled: bool


@dataclass(slots=True, frozen=True)
class TargetsResponse:
    """Response DTO for the targets-list route."""

    success: bool
    targets: list[ForwardTargetDTO]


@dataclass(slots=True, frozen=True)
class TargetResponse:
    """Response DTO for the add-target route."""

    success: bool
    target: ForwardTargetDTO


@dataclass(slots=True, frozen=True)
class AddTargetRequest:
    """Request DTO for `POST .../targets`."""

    platform: str
    forward_url: str


@dataclass(slots=True, frozen=True)
class StreamStatusDTO:
    """Wire shape for `streaming_service.StreamStatusDTO`."""

    config_id: int
    running: bool
    pid: int | None
    transcode_applied: bool
    fallback_reason: str | None
    started_at: str | None


@dataclass(slots=True, frozen=True)
class StatusResponse:
    """Response DTO for start/stop/status routes."""

    success: bool
    status: StreamStatusDTO


def _config_dto(c: svc.StreamConfigDTO) -> StreamConfigDTO:
    return StreamConfigDTO(
        id=c.id,
        community_id=c.community_id,
        source_url=c.source_url,
        source_type=c.source_type,
        enabled=c.enabled,
        record_enabled=c.record_enabled,
        transcode_enabled=c.transcode_enabled,
        transcode_bitrate_kbps=c.transcode_bitrate_kbps,
    )


def _target_dto(t: svc.ForwardTargetDTO) -> ForwardTargetDTO:
    return ForwardTargetDTO(
        id=t.id,
        config_id=t.config_id,
        platform=t.platform,
        forward_url=t.forward_url,
        enabled=t.enabled,
    )


def _status_dto(s: svc.StreamStatusDTO) -> StreamStatusDTO:
    return StreamStatusDTO(
        config_id=s.config_id,
        running=s.running,
        pid=s.pid,
        transcode_applied=s.transcode_applied,
        fallback_reason=s.fallback_reason,
        started_at=s.started_at,
    )


# ---------------------------------------------------------------------------
# Routes -- config
# ---------------------------------------------------------------------------


@streaming_bp.route("/<int:community_id>/config", methods=["GET"])
@tenant_middleware  # type: ignore[untyped-decorator]
async def get_config(community_id: int) -> tuple[dict[str, object], int]:
    """Get the community's stream configuration."""
    async_dal, dal = _dal()
    try:
        await _authorize(community_id=community_id, admin=False)
        config = await svc.get_config(async_dal, dal, community_id=community_id)
    except ApiError as exc:
        return _err(exc)
    if config is None:
        return {"success": True, "config": None}, 200
    return {"success": True, "config": asdict(_config_dto(config))}, 200


@streaming_bp.route("/<int:community_id>/config", methods=["PUT"])
@tenant_middleware  # type: ignore[untyped-decorator]
@validate_request(SetConfigRequest)
# NOT @validate_response -- this route awaits a real insert/update then
# returns a nested-dataclass response; `jsonify_dto()` avoids the
# quart-schema/pydantic-core crash `services/dto_response.py` documents
# (ported from `hub_api/PORTING.md` Gotcha #3).
async def set_config(
    data: SetConfigRequest, community_id: int
) -> tuple[object, int] | tuple[dict[str, object], int]:
    """Create or update the community's stream configuration (admin)."""
    async_dal, dal = _dal()
    try:
        await _authorize(community_id=community_id, admin=True)
        config = await svc.create_or_update_config(
            async_dal,
            dal,
            community_id=community_id,
            source_url=data.source_url,
            source_type=data.source_type,
            record_enabled=data.record_enabled,
            transcode_enabled=data.transcode_enabled,
            transcode_bitrate_kbps=data.transcode_bitrate_kbps,
        )
    except ApiError as exc:
        return _err(exc)
    return jsonify_dto(StreamConfigResponse(success=True, config=_config_dto(config)))


# ---------------------------------------------------------------------------
# Routes -- targets
# ---------------------------------------------------------------------------


@streaming_bp.route("/<int:community_id>/targets", methods=["GET"])
@tenant_middleware  # type: ignore[untyped-decorator]
# NOT @validate_response -- empirically hits the same quart-schema/
# pydantic-core crash `set_config`'s comment documents even though THIS
# route is select-only: once ANY insert has happened earlier in the same
# process (e.g. `PUT .../config`, near-certain before a real caller ever
# lists targets), a later nested-dataclass response on ANY route can
# still crash -- confirmed via a failing test in this PR, not assumed.
async def list_targets(
    community_id: int,
) -> tuple[object, int] | tuple[dict[str, object], int]:
    """List forward targets for the community's stream config."""
    async_dal, dal = _dal()
    try:
        await _authorize(community_id=community_id, admin=False)
        config = await svc.get_config(async_dal, dal, community_id=community_id)
        if config is None:
            return {"success": True, "targets": []}, 200
        targets = await svc.list_targets(async_dal, dal, config_id=config.id)
    except ApiError as exc:
        return _err(exc)
    return jsonify_dto(TargetsResponse(success=True, targets=[_target_dto(t) for t in targets]))


@streaming_bp.route("/<int:community_id>/targets", methods=["POST"])
@tenant_middleware  # type: ignore[untyped-decorator]
@validate_request(AddTargetRequest)
# NOT @validate_response -- see `set_config`'s own comment; this route
# also awaits a real insert before a nested-dataclass response.
async def add_target(
    data: AddTargetRequest, community_id: int
) -> tuple[object, int] | tuple[dict[str, object], int]:
    """Add a forward target -- SSRF-validated before it's ever persisted or forwarded to."""
    async_dal, dal = _dal()
    try:
        await _authorize(community_id=community_id, admin=True)
        config = await svc.get_config(async_dal, dal, community_id=community_id)
        if config is None:
            raise not_found("Create a stream configuration before adding targets")
        await validate_outbound_url(data.forward_url, allowed_schemes=("rtmp", "rtmps"))
        target = await svc.add_target(
            async_dal,
            dal,
            config_id=config.id,
            platform=data.platform,
            forward_url=data.forward_url,
        )
    except ApiError as exc:
        return _err(exc)
    return jsonify_dto(TargetResponse(success=True, target=_target_dto(target)), 201)


@streaming_bp.route("/<int:community_id>/targets/<int:target_id>", methods=["DELETE"])
@tenant_middleware  # type: ignore[untyped-decorator]
async def remove_target(community_id: int, target_id: int) -> tuple[dict[str, object], int]:
    """Remove a forward target (admin)."""
    async_dal, dal = _dal()
    try:
        await _authorize(community_id=community_id, admin=True)
        config = await svc.get_config(async_dal, dal, community_id=community_id)
        if config is None:
            raise not_found("Stream configuration not found")
        await svc.remove_target(async_dal, dal, config_id=config.id, target_id=target_id)
    except ApiError as exc:
        return _err(exc)
    return {"success": True, "message": "Forward target removed"}, 200


# ---------------------------------------------------------------------------
# Routes -- real forward-job lifecycle
# ---------------------------------------------------------------------------


@streaming_bp.route("/<int:community_id>/start", methods=["POST"])
@tenant_middleware  # type: ignore[untyped-decorator]
# NOT @validate_response -- awaits a real session insert then returns a
# nested-dataclass response, see `set_config`'s own comment.
async def start_forwarding(
    community_id: int,
) -> tuple[object, int] | tuple[dict[str, object], int]:
    """Start the real ffmpeg forward job (admin). See `streaming_service.start_forwarding`."""
    async_dal, dal = _dal()
    cfg = current_app.config["APP_CONFIG"]
    try:
        await _authorize(community_id=community_id, admin=True)
        status = await svc.start_forwarding(
            async_dal,
            dal,
            _supervisor(),
            community_id=community_id,
            bearer_token=_bearer_token(),
            hub_api_url=cfg.hub_api_url,
            transcode_token_cost=cfg.transcode_token_cost,
            transcode_product_key=cfg.transcode_product_key,
            ffmpeg_binary=cfg.ffmpeg_binary,
            recordings_dir=cfg.recordings_dir,
        )
    except ApiError as exc:
        return _err(exc)
    return jsonify_dto(StatusResponse(success=True, status=_status_dto(status)))


@streaming_bp.route("/<int:community_id>/stop", methods=["POST"])
@tenant_middleware  # type: ignore[untyped-decorator]
# NOT @validate_response -- awaits a real session update then returns a
# nested-dataclass response, see `set_config`'s own comment.
async def stop_forwarding(
    community_id: int,
) -> tuple[object, int] | tuple[dict[str, object], int]:
    """Stop the running forward job for this community (admin, idempotent)."""
    async_dal, dal = _dal()
    try:
        await _authorize(community_id=community_id, admin=True)
        status = await svc.stop_forwarding(async_dal, dal, _supervisor(), community_id=community_id)
    except ApiError as exc:
        return _err(exc)
    return jsonify_dto(StatusResponse(success=True, status=_status_dto(status)))


@streaming_bp.route("/<int:community_id>/status", methods=["GET"])
@tenant_middleware  # type: ignore[untyped-decorator]
# NOT @validate_response -- see `list_targets`'s own comment.
async def get_status(community_id: int) -> tuple[object, int] | tuple[dict[str, object], int]:
    """Real, live forward-job status (any active community member)."""
    async_dal, dal = _dal()
    try:
        await _authorize(community_id=community_id, admin=False)
        status = await svc.get_status(async_dal, dal, _supervisor(), community_id=community_id)
    except ApiError as exc:
        return _err(exc)
    return jsonify_dto(StatusResponse(success=True, status=_status_dto(status)))
