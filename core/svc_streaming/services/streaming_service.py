"""Stream-config/target CRUD + real forward-job lifecycle -- the control-plane business logic.

Ties together `services/schema.py` (real pydal CRUD against
`streaming_configs`/`streaming_targets`/`streaming_sessions`), `services/
ffmpeg_engine.py` (the real subprocess), and `services/
token_ledger_client.py` (real transcode-token admission against hub-api).
Every function here is community-scoped by an already-authorized
`community_id` -- the blueprint layer (`blueprints/streaming.py`) is
responsible for calling `services/community_access.py` first.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from services.errors import bad_request, conflict, not_found
from services.ffmpeg_engine import (
    FFmpegSupervisor,
    ForwardTargetSpec,
    StreamJobSpec,
    build_ffmpeg_args,
    ensure_recordings_dir,
    recording_path,
)
from services.schema import bind_streaming_tables
from services.token_ledger_client import TokenDebitResult, debit_transcoding_tokens

_VALID_SOURCE_TYPES = frozenset({"rtmp", "hls"})
_VALID_PLATFORMS = frozenset({"twitch", "youtube", "facebook", "custom"})

#: Injectable signature for the transcode-token debit call -- defaults to
#: the real HTTP client; tests substitute a fake to exercise both the
#: success and BLOCK-WITH-FALLBACK branches without a network call.
DebitFn = Callable[..., Awaitable[TokenDebitResult]]


@dataclass(slots=True, frozen=True)
class StreamConfigDTO:
    """One community's stream configuration."""

    id: int
    community_id: int
    source_url: str
    source_type: str
    enabled: bool
    record_enabled: bool
    transcode_enabled: bool
    transcode_bitrate_kbps: int


@dataclass(slots=True, frozen=True)
class ForwardTargetDTO:
    """One forward destination for a stream config."""

    id: int
    config_id: int
    platform: str
    forward_url: str
    enabled: bool


@dataclass(slots=True, frozen=True)
class StreamStatusDTO:
    """Real, live status of a community's forward job -- reflects the actual subprocess."""

    config_id: int
    running: bool
    pid: int | None
    transcode_applied: bool
    fallback_reason: str | None
    started_at: str | None


def _config_dto(row: Any) -> StreamConfigDTO:
    return StreamConfigDTO(
        id=row.id,
        community_id=row.community_id,
        source_url=row.source_url,
        source_type=row.source_type,
        enabled=row.enabled,
        record_enabled=row.record_enabled,
        transcode_enabled=row.transcode_enabled,
        transcode_bitrate_kbps=row.transcode_bitrate_kbps,
    )


def _target_dto(row: Any) -> ForwardTargetDTO:
    return ForwardTargetDTO(
        id=row.id,
        config_id=row.config_id,
        platform=row.platform,
        forward_url=row.forward_url,
        enabled=row.enabled,
    )


async def get_config(async_dal: Any, dal: Any, *, community_id: int) -> StreamConfigDTO | None:
    """Return the community's stream config, or `None` if never created."""
    bind_streaming_tables(dal)
    rows = await async_dal.select_async(dal(dal.streaming_configs.community_id == community_id))
    return _config_dto(rows.first()) if rows else None


async def create_or_update_config(
    async_dal: Any,
    dal: Any,
    *,
    community_id: int,
    source_url: str,
    source_type: str,
    record_enabled: bool,
    transcode_enabled: bool,
    transcode_bitrate_kbps: int,
) -> StreamConfigDTO:
    """Create or update the community's one stream config (upsert on `community_id`)."""
    bind_streaming_tables(dal)
    if source_type not in _VALID_SOURCE_TYPES:
        raise bad_request(f"source_type must be one of {sorted(_VALID_SOURCE_TYPES)}")
    if transcode_bitrate_kbps <= 0:
        raise bad_request("transcode_bitrate_kbps must be positive")

    now = datetime.now(UTC)
    existing = await async_dal.select_async(dal(dal.streaming_configs.community_id == community_id))
    if existing:
        config_id = int(existing.first().id)
        await async_dal.update_async(
            dal.streaming_configs.community_id == community_id,
            source_url=source_url,
            source_type=source_type,
            record_enabled=record_enabled,
            transcode_enabled=transcode_enabled,
            transcode_bitrate_kbps=transcode_bitrate_kbps,
            updated_at=now,
        )
    else:
        config_id = await async_dal.insert_async(
            dal.streaming_configs,
            community_id=community_id,
            source_url=source_url,
            source_type=source_type,
            enabled=True,
            record_enabled=record_enabled,
            transcode_enabled=transcode_enabled,
            transcode_bitrate_kbps=transcode_bitrate_kbps,
            created_at=now,
            updated_at=now,
        )

    row = (await async_dal.select_async(dal(dal.streaming_configs.id == config_id))).first()
    return _config_dto(row)


async def list_targets(async_dal: Any, dal: Any, *, config_id: int) -> list[ForwardTargetDTO]:
    """Every forward target configured for `config_id`, enabled or not."""
    bind_streaming_tables(dal)
    rows = await async_dal.select_async(
        dal(dal.streaming_targets.config_id == config_id), orderby=dal.streaming_targets.id
    )
    return [_target_dto(r) for r in rows]


async def add_target(
    async_dal: Any, dal: Any, *, config_id: int, platform: str, forward_url: str
) -> ForwardTargetDTO:
    """Add one forward target -- caller (blueprint layer) must SSRF-validate `forward_url` first."""
    bind_streaming_tables(dal)
    if platform not in _VALID_PLATFORMS:
        raise bad_request(f"platform must be one of {sorted(_VALID_PLATFORMS)}")

    config_rows = await async_dal.select_async(dal(dal.streaming_configs.id == config_id))
    if not config_rows:
        raise not_found("Stream configuration not found")

    now = datetime.now(UTC)
    target_id = await async_dal.insert_async(
        dal.streaming_targets,
        config_id=config_id,
        platform=platform,
        forward_url=forward_url,
        enabled=True,
        created_at=now,
        updated_at=now,
    )
    row = (await async_dal.select_async(dal(dal.streaming_targets.id == target_id))).first()
    return _target_dto(row)


async def remove_target(async_dal: Any, dal: Any, *, config_id: int, target_id: int) -> None:
    """Remove a forward target; raises 404 if it doesn't belong to `config_id`."""
    bind_streaming_tables(dal)
    rows = await async_dal.select_async(
        dal(
            (dal.streaming_targets.id == target_id) & (dal.streaming_targets.config_id == config_id)
        )
    )
    if not rows:
        raise not_found("Forward target not found")
    await async_dal.delete_async(dal.streaming_targets.id == target_id)


async def start_forwarding(
    async_dal: Any,
    dal: Any,
    supervisor: FFmpegSupervisor,
    *,
    community_id: int,
    bearer_token: str,
    hub_api_url: str,
    transcode_token_cost: int,
    transcode_product_key: str,
    ffmpeg_binary: str,
    recordings_dir: str,
    debit_fn: DebitFn = debit_transcoding_tokens,
) -> StreamStatusDTO:
    """Start the real ffmpeg forward job for `community_id`'s stream config.

    TRANSCODE admission (BLOCK-WITH-FALLBACK): if `config.transcode_enabled`,
    attempts a real token debit first. An affordable debit runs the job
    transcoded; an unaffordable one (`insufficient_balance`) OR an
    unreachable ledger (`ledger_unavailable`) falls back to passthrough
    (`-c copy`) rather than blocking stream start -- the job still starts.
    Raises `conflict()` if a job is already running for this community
    (call `stop_forwarding` first), `not_found()` if no config exists, and
    `bad_request()` if the config has zero enabled targets and recording
    is off (nothing for ffmpeg to do).
    """
    bind_streaming_tables(dal)
    config_rows = await async_dal.select_async(
        dal(dal.streaming_configs.community_id == community_id)
    )
    if not config_rows:
        raise not_found("Stream configuration not found")
    config_row = config_rows.first()
    config_id = int(config_row.id)

    if supervisor.is_running(config_id):
        raise conflict("A forward job is already running for this community")

    target_rows = await async_dal.select_async(
        dal(
            (dal.streaming_targets.config_id == config_id) & (dal.streaming_targets.enabled == True)  # noqa: E712 - pydal query operator
        )
    )
    targets = [ForwardTargetSpec(forward_url=r.forward_url) for r in target_rows]

    now = datetime.now(UTC)
    record_path: str | None = None
    if config_row.record_enabled:
        ensure_recordings_dir(recordings_dir)
        record_path = recording_path(recordings_dir, config_id, now.isoformat())

    if not targets and record_path is None:
        raise bad_request("Cannot start: no enabled forward targets and recording is disabled")

    transcode_applied = False
    fallback_reason: str | None = None
    if config_row.transcode_enabled:
        debit_result = await debit_fn(
            hub_api_url,
            bearer_token=bearer_token,
            community_id=community_id,
            amount=transcode_token_cost,
            product_key=transcode_product_key,
            ref=f"stream:{config_id}:{now.isoformat()}",
        )
        if debit_result.ok:
            transcode_applied = True
        else:
            fallback_reason = debit_result.blocked_reason

    spec = StreamJobSpec(
        source_url=config_row.source_url,
        targets=targets,
        transcode=transcode_applied,
        transcode_bitrate_kbps=config_row.transcode_bitrate_kbps,
        record_path=record_path,
    )
    args = build_ffmpeg_args(spec, ffmpeg_binary=ffmpeg_binary)
    managed = await supervisor.start(config_id, args)

    session_id = await async_dal.insert_async(
        dal.streaming_sessions,
        config_id=config_id,
        pid=managed.pid,
        status="running",
        transcode_applied=transcode_applied,
        fallback_reason=fallback_reason,
        started_at=now,
        created_at=now,
    )
    del session_id  # not returned today; row exists for audit/history queries

    return StreamStatusDTO(
        config_id=config_id,
        running=True,
        pid=managed.pid,
        transcode_applied=transcode_applied,
        fallback_reason=fallback_reason,
        started_at=now.isoformat(),
    )


async def stop_forwarding(
    async_dal: Any, dal: Any, supervisor: FFmpegSupervisor, *, community_id: int
) -> StreamStatusDTO:
    """Stop the running forward job for `community_id`, if any (idempotent)."""
    bind_streaming_tables(dal)
    config_rows = await async_dal.select_async(
        dal(dal.streaming_configs.community_id == community_id)
    )
    if not config_rows:
        raise not_found("Stream configuration not found")
    config_id = int(config_rows.first().id)

    await supervisor.stop(config_id)

    now = datetime.now(UTC)
    running_session_query = (dal.streaming_sessions.config_id == config_id) & (
        dal.streaming_sessions.status == "running"
    )
    await async_dal.update_async(running_session_query, status="stopped", ended_at=now)

    return StreamStatusDTO(
        config_id=config_id,
        running=False,
        pid=None,
        transcode_applied=False,
        fallback_reason=None,
        started_at=None,
    )


async def get_status(
    async_dal: Any, dal: Any, supervisor: FFmpegSupervisor, *, community_id: int
) -> StreamStatusDTO:
    """Real, live status -- reflects the actual supervised subprocess, not just the DB row."""
    bind_streaming_tables(dal)
    config_rows = await async_dal.select_async(
        dal(dal.streaming_configs.community_id == community_id)
    )
    if not config_rows:
        raise not_found("Stream configuration not found")
    config_id = int(config_rows.first().id)

    running = supervisor.is_running(config_id)
    if not running:
        return StreamStatusDTO(
            config_id=config_id,
            running=False,
            pid=None,
            transcode_applied=False,
            fallback_reason=None,
            started_at=None,
        )

    session_rows = await async_dal.select_async(
        dal(
            (dal.streaming_sessions.config_id == config_id)
            & (dal.streaming_sessions.status == "running")
        ),
        orderby=~dal.streaming_sessions.id,
        limitby=(0, 1),
    )
    session = session_rows.first() if session_rows else None
    managed = supervisor.get(config_id)
    return StreamStatusDTO(
        config_id=config_id,
        running=True,
        pid=managed.pid if managed else None,
        transcode_applied=bool(session.transcode_applied) if session else False,
        fallback_reason=session.fallback_reason if session else None,
        started_at=session.started_at.isoformat() if session and session.started_at else None,
    )
