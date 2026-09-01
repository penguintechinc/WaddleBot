"""pydal table bindings for svc-streaming's own tables + read-only shared tables.

svc-streaming owns three tables -- `streaming_configs`, `streaming_targets`,
`streaming_sessions` -- physically created by `config/postgres/migrations/
078_svc_streaming.sql` in the same shared Postgres instance every other
stage-runner writes to (`backend-database.md` Per-Service Database
Accounts: same DB, per-service scoped credentials -- this service's own
`DATABASE_URL`/`DB_USER`). `bind_streaming_tables()` mirrors `core/
svc_presentation/services/schema.py`'s `bind_presentation_tables()` shape
exactly: idempotent per-DAL-instance, `migrate=False` in production (the
migration file is schema's single source of truth -- `backend-database.md`
rule 9), `migrate=True` in tests against a throwaway sqlite DB.

`bind_shared_read_tables()` defines the minimal read-only field subset of
`tenants`/`communities`/`community_members` this service needs for its own
tenant + community-membership authorization checks
(`services/community_access.py`, ported from `hub_api/services/
community_access.py`/`community_authz.py`) -- these tables are OWNED by
hub-api's own migrations (000/058), never created here (`migrate=False`
unconditionally, even in tests that seed rows into them directly).
"""

from __future__ import annotations

from typing import Any

from pydal import Field


def bind_streaming_tables(dal: Any, *, migrate: bool = False) -> None:
    """Define `streaming_configs`/`streaming_targets`/`streaming_sessions` on `dal`.

    Idempotent: a second call against the same DAL instance is a no-op
    (guarded on `streaming_sessions`, a table unique to this service).
    """
    if "streaming_sessions" in dal.tables:
        return

    dal.define_table(
        "streaming_configs",
        Field("community_id", "integer", notnull=True, unique=True),
        Field("source_url", "string", length=1024, notnull=True),
        Field("source_type", "string", length=20, default="rtmp", notnull=True),
        Field("enabled", "boolean", default=True, notnull=True),
        Field("record_enabled", "boolean", default=False, notnull=True),
        Field("transcode_enabled", "boolean", default=False, notnull=True),
        Field("transcode_bitrate_kbps", "integer", default=4000, notnull=True),
        Field("created_at", "datetime"),
        Field("updated_at", "datetime"),
        migrate=migrate,
    )

    dal.define_table(
        "streaming_targets",
        Field("config_id", "reference streaming_configs", notnull=True, ondelete="CASCADE"),
        Field("platform", "string", length=50, notnull=True),
        Field("forward_url", "string", length=1024, notnull=True),
        Field("enabled", "boolean", default=True, notnull=True),
        Field("created_at", "datetime"),
        Field("updated_at", "datetime"),
        migrate=migrate,
    )

    dal.define_table(
        "streaming_sessions",
        Field("config_id", "reference streaming_configs", notnull=True, ondelete="CASCADE"),
        Field("pid", "integer"),
        Field("status", "string", length=20, default="stopped", notnull=True),
        Field("transcode_applied", "boolean", default=False, notnull=True),
        Field("fallback_reason", "string", length=100),
        Field("started_at", "datetime"),
        Field("ended_at", "datetime"),
        Field("created_at", "datetime"),
        migrate=migrate,
    )


def bind_shared_read_tables(dal: Any, *, migrate: bool = False) -> None:
    """Define the read-only field subset of hub-api-owned tables this service's authz needs.

    Covers `tenants`/`communities`/`community_members`/`community_servers`.
    `migrate=False` always in production (these tables are never this
    service's to create); tests pass `migrate=True` against the same
    throwaway sqlite DB `bind_streaming_tables()` uses so the two halves
    of the schema coexist in one file-backed test DB, matching how
    `hub_api/tests/conftest.py` seeds its own fixtures directly into
    tables it owns.
    """
    if "community_members" in dal.tables:
        return

    dal.define_table(
        "tenants",
        Field("slug", "string", length=100),
        Field("is_active", "boolean", default=True),
        migrate=migrate,
    )

    dal.define_table(
        "communities",
        Field("tenant_id", "integer", notnull=True),
        migrate=migrate,
    )

    dal.define_table(
        "community_members",
        Field("community_id", "integer", notnull=True),
        # VARCHAR in Postgres (legacy platform-identity membership model),
        # not a FK -- matches `hub_api/services/community_authz.py`'s own
        # note; compared as `str(user_id)` at every call site.
        Field("user_id", "string", length=255),
        Field("role", "string", length=50, default="member"),
        Field("is_active", "boolean", default=True),
        migrate=migrate,
    )

    # Connected external-platform channels for the DISPLAY/associated-
    # channels endpoint (`services/live_channels_service.py`) -- real
    # table, owned by `000_create_base_schema.sql`; read-only here.
    # `status = 'approved'` is the real filter value the Twitch receiver
    # already uses (`trigger/receiver/twitch_module/app.py`'s
    # `_load_tracked_channels`).
    dal.define_table(
        "community_servers",
        Field("community_id", "integer", notnull=True),
        Field("platform", "string", length=50, notnull=True),
        Field("platform_server_id", "string", length=255, notnull=True),
        Field("platform_server_name", "string", length=255),
        Field("status", "string", length=50, default="pending"),
        migrate=migrate,
    )
