"""Table-binding idempotency + real DDL against an ephemeral sqlite DB."""

from __future__ import annotations

from pydal import DAL

from services.schema import bind_shared_read_tables, bind_streaming_tables


def test_bind_streaming_tables_creates_all_three_tables() -> None:
    dal = DAL("sqlite:memory")
    bind_streaming_tables(dal, migrate=True)
    assert {"streaming_configs", "streaming_targets", "streaming_sessions"} <= set(dal.tables)


def test_bind_streaming_tables_is_idempotent() -> None:
    dal = DAL("sqlite:memory")
    bind_streaming_tables(dal, migrate=True)
    bind_streaming_tables(dal, migrate=True)  # must not raise (guarded on streaming_sessions)


def test_bind_shared_read_tables_creates_expected_tables() -> None:
    dal = DAL("sqlite:memory")
    bind_shared_read_tables(dal, migrate=True)
    assert {"tenants", "communities", "community_members", "community_servers"} <= set(dal.tables)


def test_bind_shared_read_tables_is_idempotent() -> None:
    dal = DAL("sqlite:memory")
    bind_shared_read_tables(dal, migrate=True)
    bind_shared_read_tables(dal, migrate=True)  # must not raise (guarded on community_members)


def test_streaming_config_row_round_trips() -> None:
    from datetime import UTC, datetime

    dal = DAL("sqlite:memory")
    bind_streaming_tables(dal, migrate=True)
    now = datetime.now(UTC)
    config_id = dal.streaming_configs.insert(
        community_id=1,
        source_url="rtmp://ingest.example.com/live/key",
        source_type="rtmp",
        enabled=True,
        record_enabled=False,
        transcode_enabled=False,
        transcode_bitrate_kbps=4000,
        created_at=now,
        updated_at=now,
    )
    dal.commit()
    row = dal(dal.streaming_configs.id == config_id).select().first()
    assert row.community_id == 1
    assert row.source_type == "rtmp"
