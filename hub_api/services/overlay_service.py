"""Overlay business logic -- ported from `overlayController.js` (Streaming module, M7).

Manages the per-community browser-source overlay token
`community_overlay_tokens` renders against (svc-presentation reads
`overlay_key` to resolve which community's `full_screen`/`media`/
`crawler` sections to serve -- see `docs/plans/2026-08-31-svc-streaming-
design.md`). Every function here assumes its caller (`blueprints/v1/
overlay.py`) has already run `services.community_access.
require_community_admin()` -- this module has no authz of its own, same
division of responsibility `auth_service.py`/`event_calendar_proxy.py`
already establish (blueprint owns auth + HTTP shape, service owns the
query).

Overlay key generation: `secrets.token_hex(32)` (64 hex chars) is the
direct Python equivalent of Node's `crypto.randomBytes(32).toString
('hex')` -- both cryptographically-random, unguessable, same length.
Never derived from `community_id` or any other predictable input
(security.md: URLs/tokens must be unguessable, not merely unlisted).

Write paths (`get_or_create_overlay`'s create branch, `update_overlay`,
`rotate_overlay_key`) deliberately build their return value from the
field values already known in Python rather than re-`select_async`-ing
immediately after an `insert_async`/`update_async` -- `hub_api/PORTING.md`
Gotcha #2/#3's uncommitted-write-visibility class of bug, sidestepped the
same way `auth_service.register()` already does (see that function's own
comment), not re-discovered here.

Timestamps are serialized to ISO-8601 strings (`_iso()`) at the DTO
boundary, not left as raw `datetime` objects: `blueprints/v1/overlay.py`
routes all use `services/dto_response.py::jsonify_dto()` (Gotcha #3, a
real `insert_async`/`update_async` + nested-dataclass response), which
bypasses quart-schema's pydantic `TypeAdapter` -- the ONE thing that
would otherwise give `datetime` fields consistent ISO formatting for
free. Left as raw `datetime`, Quart's own default JSON provider formats
dates as an RFC 822 string instead, which parses fine via JS `new
Date(...)` (`AdminStreamOverlays.jsx`) but isn't the ISO 8601 string
Node's `pg` driver + `JSON.stringify` produce today -- `_iso()` matches
that shape instead of leaving it to whichever serializer happens to run.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from config import HubAPIConfig
from services.errors import not_found
from services.schema import bind_streaming_tables

_DEFAULT_ENABLED_SOURCES: tuple[str, ...] = ("alerts", "chat", "goals", "ticker")


def _iso(value: datetime | None) -> str | None:
    """Format a `datetime` as an ISO-8601 UTC string (`...Z`), matching JS's `toISOString()`."""
    if value is None:
        return None
    aware = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    return aware.astimezone(UTC).isoformat().replace("+00:00", "Z")


@dataclass(slots=True, frozen=True)
class OverlayRecord:
    """Row-shaped view of `community_overlay_tokens` -- mirrors Node's spread-plus-`overlayUrl`.

    Field names are DELIBERATELY mixed-case: every DB-column field stays
    snake_case (Node spreads the raw pg row verbatim), only `overlayUrl`
    is camelCase (Node's own added field) -- `AdminStreamOverlays.jsx`
    reads both conventions from the same object (`overlay.is_active`,
    `overlay.overlay_key`, `overlay.overlayUrl`), so this DTO matches
    the pinned wire contract byte-for-byte rather than "fixing" the
    casing on one side. See `hub_api/PORTING.md`'s DTO casing note.
    Timestamp fields are pre-formatted ISO strings -- see module
    docstring's `_iso()` note.
    """

    id: int
    community_id: int
    overlay_key: str
    previous_key: str | None
    is_active: bool
    theme_config: dict[str, Any]
    enabled_sources: list[str]
    last_accessed: str | None
    access_count: int
    created_at: str | None
    updated_at: str | None
    rotated_at: str | None
    overlayUrl: str


@dataclass(slots=True, frozen=True)
class OverlayDailyStat:
    """One row of `overlay_access_log`'s per-day aggregation."""

    date: str
    access_count: int
    unique_ips: int


@dataclass(slots=True, frozen=True)
class OverlayStats:
    """Response shape for `getOverlayStats` -- `{total: {...}, daily: [...]}`."""

    total_access_count: int
    last_accessed: str | None
    daily: list[OverlayDailyStat] = field(default_factory=list)


def _overlay_url(cfg: HubAPIConfig, overlay_key: str) -> str:
    """Port of `${baseUrl}/${overlay.overlay_key}` -- `OVERLAY_BASE_URL` env var, see config.py."""
    return f"{cfg.overlay_base_url}/{overlay_key}"


def _to_record(row: Any, cfg: HubAPIConfig) -> OverlayRecord:
    """Build an `OverlayRecord` from a freshly-selected `community_overlay_tokens` row."""
    return OverlayRecord(
        id=row.id,
        community_id=row.community_id,
        overlay_key=row.overlay_key,
        previous_key=row.previous_key,
        is_active=bool(row.is_active),
        theme_config=row.theme_config or {},
        enabled_sources=row.enabled_sources or list(_DEFAULT_ENABLED_SOURCES),
        last_accessed=_iso(row.last_accessed),
        access_count=row.access_count or 0,
        created_at=_iso(row.created_at),
        updated_at=_iso(row.updated_at),
        rotated_at=_iso(row.rotated_at),
        overlayUrl=_overlay_url(cfg, row.overlay_key),
    )


async def get_or_create_overlay(
    async_dal: Any, dal: Any, cfg: HubAPIConfig, *, community_id: int
) -> OverlayRecord:
    """Get the overlay token for `community_id`, creating one on first access.

    Port of `getOverlay` (`GET /:communityId/overlay`) -- Node's
    `SELECT ... ; if no rows, INSERT ... RETURNING`.
    """
    bind_streaming_tables(dal)
    rows = await async_dal.select_async(
        dal(dal.community_overlay_tokens.community_id == community_id)
    )
    if rows:
        return _to_record(rows.first(), cfg)

    overlay_key = secrets.token_hex(32)
    now = datetime.now(UTC)
    new_id = await async_dal.insert_async(
        dal.community_overlay_tokens,
        community_id=community_id,
        overlay_key=overlay_key,
        previous_key=None,
        is_active=True,
        theme_config={},
        enabled_sources=list(_DEFAULT_ENABLED_SOURCES),
        access_count=0,
        created_at=now,
        updated_at=now,
    )
    return OverlayRecord(
        id=new_id,
        community_id=community_id,
        overlay_key=overlay_key,
        previous_key=None,
        is_active=True,
        theme_config={},
        enabled_sources=list(_DEFAULT_ENABLED_SOURCES),
        last_accessed=None,
        access_count=0,
        created_at=_iso(now),
        updated_at=_iso(now),
        rotated_at=None,
        overlayUrl=_overlay_url(cfg, overlay_key),
    )


async def update_overlay(
    async_dal: Any,
    dal: Any,
    cfg: HubAPIConfig,
    *,
    community_id: int,
    is_active: bool | None,
    theme_config: dict[str, Any] | None,
    enabled_sources: list[str] | None,
) -> OverlayRecord:
    """Update overlay settings. Port of `updateOverlay` (`PUT /:communityId/overlay`)."""
    bind_streaming_tables(dal)
    rows = await async_dal.select_async(
        dal(dal.community_overlay_tokens.community_id == community_id)
    )
    if not rows:
        raise not_found("Overlay not found")
    existing = rows.first()

    updates: dict[str, Any] = {"updated_at": datetime.now(UTC)}
    if is_active is not None:
        updates["is_active"] = is_active
    if theme_config is not None:
        updates["theme_config"] = theme_config
    if enabled_sources is not None:
        updates["enabled_sources"] = enabled_sources

    await async_dal.update_async(
        dal.community_overlay_tokens.community_id == community_id, **updates
    )

    return OverlayRecord(
        id=existing.id,
        community_id=community_id,
        overlay_key=existing.overlay_key,
        previous_key=existing.previous_key,
        is_active=bool(updates.get("is_active", existing.is_active)),
        theme_config=updates.get("theme_config", existing.theme_config or {}),
        enabled_sources=updates.get(
            "enabled_sources", existing.enabled_sources or list(_DEFAULT_ENABLED_SOURCES)
        ),
        last_accessed=_iso(existing.last_accessed),
        access_count=existing.access_count or 0,
        created_at=_iso(existing.created_at),
        updated_at=_iso(updates["updated_at"]),
        rotated_at=_iso(existing.rotated_at),
        overlayUrl=_overlay_url(cfg, existing.overlay_key),
    )


async def rotate_overlay_key(
    async_dal: Any, dal: Any, cfg: HubAPIConfig, *, community_id: int
) -> OverlayRecord:
    """Rotate the overlay key, keeping the old one as `previous_key` for a grace period.

    Port of `rotateKey` (`POST /:communityId/overlay/rotate`) -- Node's
    comment ("Previous key valid for 5 more minutes") describes
    svc-presentation's own grace-period enforcement when resolving an
    overlay_key against BOTH `overlay_key` and `previous_key` within
    `rotated_at + 5m`; out of scope for hub-api's own write path (this
    function's job is only to rotate the columns).
    """
    bind_streaming_tables(dal)
    rows = await async_dal.select_async(
        dal(dal.community_overlay_tokens.community_id == community_id)
    )
    if not rows:
        raise not_found("Overlay not found")
    existing = rows.first()

    new_key = secrets.token_hex(32)
    now = datetime.now(UTC)
    await async_dal.update_async(
        dal.community_overlay_tokens.community_id == community_id,
        previous_key=existing.overlay_key,
        overlay_key=new_key,
        rotated_at=now,
        updated_at=now,
    )

    return OverlayRecord(
        id=existing.id,
        community_id=community_id,
        overlay_key=new_key,
        previous_key=existing.overlay_key,
        is_active=bool(existing.is_active),
        theme_config=existing.theme_config or {},
        enabled_sources=existing.enabled_sources or list(_DEFAULT_ENABLED_SOURCES),
        last_accessed=_iso(existing.last_accessed),
        access_count=existing.access_count or 0,
        created_at=_iso(existing.created_at),
        updated_at=_iso(now),
        rotated_at=_iso(now),
        overlayUrl=_overlay_url(cfg, new_key),
    )


async def get_overlay_stats(
    async_dal: Any, dal: Any, *, community_id: int, days: int
) -> OverlayStats:
    """Get overlay access statistics. Port of `getOverlayStats` (`GET .../overlay/stats`)."""
    bind_streaming_tables(dal)
    cutoff = datetime.now(UTC) - timedelta(days=days)

    log_rows = await async_dal.select_async(
        dal(
            (dal.overlay_access_log.community_id == community_id)
            & (dal.overlay_access_log.accessed_at > cutoff)
        )
    )
    daily: dict[str, dict[str, Any]] = {}
    for row in log_rows:
        accessed_at = row.accessed_at
        day_key = accessed_at.date().isoformat() if accessed_at else "unknown"
        bucket = daily.setdefault(day_key, {"access_count": 0, "ips": set()})
        bucket["access_count"] += 1
        if row.ip_address:
            bucket["ips"].add(row.ip_address)

    daily_stats = [
        OverlayDailyStat(date=day, access_count=data["access_count"], unique_ips=len(data["ips"]))
        for day, data in sorted(daily.items(), reverse=True)
    ]

    total_rows = await async_dal.select_async(
        dal(dal.community_overlay_tokens.community_id == community_id)
    )
    total = total_rows.first() if total_rows else None

    return OverlayStats(
        total_access_count=(total.access_count or 0) if total is not None else 0,
        last_accessed=_iso(total.last_accessed) if total is not None else None,
        daily=daily_stats,
    )
