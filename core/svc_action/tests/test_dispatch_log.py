"""services/dispatch_log.py -- action_dispatch_log pydal binding + write helper."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest
from flask_core import AsyncDAL

from services.dispatch_log import init_action_dispatch_log_table, record_dispatch


@pytest.fixture
def dal(tmp_path: Path) -> AsyncDAL:
    """AsyncDAL against a throwaway file-backed sqlite DB, pool_size=1 (Gotcha #2)."""
    async_dal = AsyncDAL(f"sqlite://{tmp_path}/test.db", pool_size=1, migrate=True)
    d = async_dal.dal
    d.define_table("tenants", migrate=True)
    d.define_table("communities", d.Field("tenant_id", "reference tenants"), migrate=True)
    d.define_table(
        "action_dispatch_log",
        d.Field("tenant_id", "reference tenants", notnull=True),
        d.Field("community_id", "reference communities"),
        d.Field("app_id", "string", notnull=True),
        d.Field("target_type", "string", notnull=True),
        d.Field("status", "string", notnull=True),
        d.Field("attempt", "integer", default=1),
        d.Field("http_status", "integer"),
        d.Field("detail", "string", default=""),
        d.Field("envelope_ts", "datetime"),
        d.Field("dispatched_at", "datetime", default=datetime.utcnow),
        migrate=True,
    )
    return async_dal


def test_init_action_dispatch_log_table_defines_expected_fields(tmp_path: Path) -> None:
    async_dal = AsyncDAL(f"sqlite://{tmp_path}/init_test.db", pool_size=1, migrate=True)
    d = async_dal.dal
    d.define_table("tenants", migrate=True)
    d.define_table("communities", d.Field("tenant_id", "reference tenants"), migrate=True)
    init_action_dispatch_log_table(d)
    assert "action_dispatch_log" in d.tables
    assert set(d.action_dispatch_log.fields) >= {
        "tenant_id",
        "community_id",
        "app_id",
        "target_type",
        "status",
        "attempt",
        "http_status",
        "detail",
        "envelope_ts",
        "dispatched_at",
    }


async def test_record_dispatch_inserts_a_row(dal: AsyncDAL) -> None:
    dal.dal.tenants.insert()
    dal.dal.communities.insert(tenant_id=1)
    dal.dal.commit()

    await record_dispatch(
        dal,
        tenant_id=1,
        community_id=1,
        app_id="waddles.bot.shoutout.default",
        target_type="webhook",
        status="success",
        attempt=1,
        http_status=200,
        detail="delivered, HTTP 200",
        envelope_ts=datetime(2026, 8, 31, 12, 0, 0),
    )

    rows = await dal.select_async(dal.dal(dal.dal.action_dispatch_log.id > 0))
    assert len(rows) == 1
    assert rows[0].status == "success"
    assert rows[0].target_type == "webhook"
    assert rows[0].http_status == 200


async def test_record_dispatch_truncates_long_detail(dal: AsyncDAL) -> None:
    dal.dal.tenants.insert()
    dal.dal.commit()

    long_detail = "x" * 1000
    await record_dispatch(
        dal,
        tenant_id=1,
        community_id=None,
        app_id="waddles.bot.shoutout.default",
        target_type="webhook",
        status="non_retryable_failure",
        attempt=1,
        http_status=None,
        detail=long_detail,
        envelope_ts=None,
    )

    rows = await dal.select_async(dal.dal(dal.dal.action_dispatch_log.id > 0))
    assert len(rows[0].detail) == 500
