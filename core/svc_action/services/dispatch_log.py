"""ACTION stage-runner dispatch audit log -- pydal binding + write helper.

Schema owned by `config/postgres/migrations/074_action_dispatch_log.sql`
(the source of truth) -- this module's `define_table` passes
`migrate=False` throughout, matching `flask_core.app_bundle_tables`'
established "pydal maps onto the already-migrated table, it never owns
this DDL" convention.

`detail` is always a short, human-readable status string -- request/
response bodies and resolved secrets are never persisted here (security.md
"log masked, never raw PII"; this task's "never log secrets/tokens/full
bodies").
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from flask_core import AsyncDAL


def init_action_dispatch_log_table(dal: Any) -> None:
    """Define `action_dispatch_log` on `dal`. Call once per process during startup."""
    dal.define_table(
        "action_dispatch_log",
        dal.Field("tenant_id", "reference tenants", notnull=True),
        dal.Field("community_id", "reference communities", ondelete="CASCADE"),
        dal.Field("app_id", "string", notnull=True),
        dal.Field("target_type", "string", notnull=True),
        dal.Field("status", "string", notnull=True),
        dal.Field("attempt", "integer", default=1),
        dal.Field("http_status", "integer"),
        dal.Field("detail", "string", default=""),
        dal.Field("envelope_ts", "datetime"),
        dal.Field("dispatched_at", "datetime", default=datetime.utcnow),
        migrate=False,
    )


async def record_dispatch(
    dal: AsyncDAL,
    *,
    tenant_id: int,
    community_id: Optional[int],
    app_id: str,
    target_type: str,
    status: str,
    attempt: int,
    http_status: Optional[int],
    detail: str,
    envelope_ts: Optional[datetime],
) -> None:
    """Insert one audit row. Never raises into the caller's dispatch flow --

    an audit-log write failure must not mask (or retry-loop) the dispatch
    outcome it's trying to record; the runner logs (via structured
    logging, not this table) and moves on if this insert itself fails.
    """
    await dal.insert_async(
        dal.dal.action_dispatch_log,
        tenant_id=tenant_id,
        community_id=community_id,
        app_id=app_id,
        target_type=target_type,
        status=status,
        attempt=attempt,
        http_status=http_status,
        detail=detail[:500],  # bounded -- this is a status string, not a body dump
        envelope_ts=envelope_ts,
    )
