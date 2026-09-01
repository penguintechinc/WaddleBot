"""Shared fixtures for hub-api's own tests.

`tenant_db` mirrors `libs/flask_core/tests/test_tenancy.py` and
`test_mcp_routes.py`'s own fixture exactly (in-memory pydal `tenants`
table, `migrate=True`) -- ephemeral, test-only schema. Production never
migrates `tenants` (see `app.py::_bind_reference_tables` -- schema owned
by `config/postgres/migrations/058_tenants_and_claims.sql`); tests need a
real row to resolve against, so they get their own throwaway table
instead of relaxing that production invariant.

`auth_db` (M1 Core Identity/Auth group) extends the same pattern with
`services.schema.bind_auth_tables()` -- every future port group that
needs its own tables should add its own `<group>_db` fixture here the
same way, rather than editing `tenant_db`/`auth_db` in place (keeps this
shared file append-only across the parallel port wave).

`streaming_db` (M7 Streaming/overlay+calls group) is this port's own
additive fixture, mirroring `auth_db`'s file-backed-sqlite/`migrate=True`
shape but also calling `services.schema.bind_streaming_tables()` for
`community_overlay_tokens`/`overlay_access_log` -- new tables `auth_db`
doesn't bind. `_seed_community`/`_seed_membership` are this group's own
seeding helpers for `communities`/`community_members`
(`services.community_access`'s authz checks).
"""

from __future__ import annotations

from typing import Any

import pytest
from flask_core.auth import create_jwt_token
from flask_core.database import AsyncDAL
from pydal import DAL, Field

from services.schema import bind_auth_tables, bind_streaming_tables

#: Matches flask_core.tenancy/authz's own os.getenv("SECRET_KEY", ...) fallback.
SECRET_KEY = "change-me-in-production"

TENANT_SLUG = "acme-corp"


@pytest.fixture
def tenant_db() -> Any:
    """In-memory pydal DB with one active tenant -- `tenants.slug`/`is_active` only."""
    dal = DAL("sqlite:memory")
    dal.define_table(
        "tenants",
        Field("slug", unique=True),
        Field("is_active", "boolean", default=True),
    )
    dal.tenants.insert(slug=TENANT_SLUG, is_active=True)
    dal.commit()
    yield dal
    dal.close()


@pytest.fixture
def auth_db(tmp_path: Any) -> Any:
    """File-backed `AsyncDAL` with `tenants` + every M1 auth/identity/passkey/profile table.

    Services in this group call `async_dal.select_async`/`insert_async`/etc,
    which run on `AsyncDAL`'s own `ThreadPoolExecutor` (a different OS
    thread per call, see `flask_core.database.AsyncDAL`) -- `sqlite:memory`
    (as `tenant_db` above uses) is connection-scoped, so a worker thread
    opening its own connection sees a BLANK database, not the one the main
    thread just seeded (`sqlite3.OperationalError: no such table`, caught
    the hard way -- see `hub_api/PORTING.md`'s async_dal testing gotcha). A
    `tmp_path`-backed sqlite FILE is shared across connections/threads like
    real Postgres would be, so it exercises the exact code path
    `select_async`/`insert_async`/etc actually run in production.
    """
    # pool_size=1 -- sqlite file DBs serialize writes across connections;
    # AsyncDAL's own ThreadPoolExecutor otherwise opens up to `pool_size`
    # concurrent connections, which raced into "database is locked" against
    # a plain (non-WAL) sqlite file during this suite's own test-writing.
    # Real deployments target Postgres (see this fixture's own docstring),
    # where connection pooling has no such lock-contention behavior.
    async_dal = AsyncDAL(f"sqlite://{tmp_path / 'auth_test.db'}", pool_size=1)
    dal = async_dal.dal
    dal.define_table(
        "tenants",
        Field("slug", unique=True),
        Field("display_name"),
        Field("logo_url"),
        Field("is_global", "boolean", default=False),
        Field("is_active", "boolean", default=True),
        Field("config", "json"),
    )
    bind_auth_tables(dal, migrate=True)
    dal.tenants.insert(slug=TENANT_SLUG, display_name="Acme Corp", is_active=True)
    dal.commit()
    # `lazy_tables=True` (AsyncDAL's own default) defers each table's
    # actual `CREATE TABLE` until first ORM access -- left lazy, the FIRST
    # access could happen on an `async_dal.*_async()` worker thread mid-
    # request, racing its own `CREATE TABLE` against the main thread's
    # still-open sqlite file handle ("database is locked"). Touching every
    # table once here, still on the main thread, forces that DDL to run
    # before any worker thread exists -- a test-only concern (production
    # Postgres has no such lazy-CREATE-races-a-thread failure mode).
    for table_name in dal.tables:
        dal(dal[table_name]).count()
    yield async_dal
    dal.close()


#: Second tenant slug -- exists only in `streaming_db`, for cross-tenant IDOR tests
#: (`services.community_access._require_community_in_tenant`).
OTHER_TENANT_SLUG = "other-corp"


@pytest.fixture
def streaming_db(tmp_path: Any) -> Any:
    """File-backed `AsyncDAL` with `tenants` + auth tables + M7's own overlay/calls tables.

    Same connection-visibility rationale as `auth_db` (see its own
    docstring) -- a fresh file, not shared with `auth_db`, so tests in
    this group don't collide with M1's own fixture instance.
    """
    async_dal = AsyncDAL(f"sqlite://{tmp_path / 'streaming_test.db'}", pool_size=1)
    dal = async_dal.dal
    dal.define_table(
        "tenants",
        Field("slug", unique=True),
        Field("display_name"),
        Field("logo_url"),
        Field("is_global", "boolean", default=False),
        Field("is_active", "boolean", default=True),
        Field("config", "json"),
    )
    bind_auth_tables(dal, migrate=True)
    bind_streaming_tables(dal, migrate=True)
    dal.tenants.insert(slug=TENANT_SLUG, display_name="Acme Corp", is_active=True)
    dal.tenants.insert(slug=OTHER_TENANT_SLUG, display_name="Other Corp", is_active=True)
    dal.commit()
    for table_name in dal.tables:
        dal(dal[table_name]).count()
    yield async_dal
    dal.close()


def seed_community(
    streaming_db: Any, *, tenant_slug: str = TENANT_SLUG, name: str = "acme-community"
) -> int:
    """Insert one `communities` row scoped to `tenant_slug`; returns its id."""
    dal = streaming_db.dal
    tenant = dal(dal.tenants.slug == tenant_slug).select().first()
    community_id: int = dal.communities.insert(
        name=name, display_name=name, tenant_id=tenant.id, is_active=True
    )
    dal.commit()
    return community_id


def seed_membership(
    streaming_db: Any, *, community_id: int, user_id: int, role: str = "community-owner"
) -> None:
    """Insert one active `community_members` row for `user_id` in `community_id`."""
    dal = streaming_db.dal
    dal.community_members.insert(
        community_id=community_id, user_id=str(user_id), role=role, is_active=True
    )
    dal.commit()


def make_token(*, scope: str = "", tenant: str = TENANT_SLUG) -> str:
    """Mint a JWT via the real `flask_core.auth.create_jwt_token` -- no hand-rolled JWTs."""
    return create_jwt_token(
        user_id="u1",
        username="alice",
        email="alice@example.com",
        roles=["viewer"],
        secret_key=SECRET_KEY,
        tenant=tenant,
        scope=scope,
    )


def make_user_token(*, user_id: int, scope: str = "", tenant: str = TENANT_SLUG) -> str:
    """Mint a JWT whose `sub` is a real `hub_users.id` -- for `services.current_user` callers."""
    return create_jwt_token(
        user_id=str(user_id),
        username="alice",
        email="alice@example.com",
        roles=["viewer"],
        secret_key=SECRET_KEY,
        tenant=tenant,
        scope=scope,
    )


def make_super_admin_token(*, user_id: int, scope: str = "", tenant: str = TENANT_SLUG) -> str:
    """Mint a JWT with `roles=["super_admin"]` -- `services.community_access._is_super_admin`."""
    return create_jwt_token(
        user_id=str(user_id),
        username="root",
        email="root@example.com",
        roles=["super_admin"],
        secret_key=SECRET_KEY,
        tenant=tenant,
        scope=scope,
    )


@pytest.fixture
def auth_headers():
    """Factory fixture: `auth_headers(scope="platform:read")` -> Authorization header dict."""

    def _make(*, scope: str = "", tenant: str = TENANT_SLUG) -> dict[str, str]:
        return {"Authorization": f"Bearer {make_token(scope=scope, tenant=tenant)}"}

    return _make


@pytest.fixture
def user_auth_headers():
    """Factory fixture: `user_auth_headers(user_id=42)` -> Authorization header dict.

    Unlike `auth_headers` (fixed `sub="u1"`, for `blueprints/v2/platform.py`-
    style scope tests), this mints a token whose `sub` is a real
    `hub_users.id` -- required by every M1 self-service route, which
    resolves the caller via `services.current_user.get_current_user_id`.
    """

    def _make(*, user_id: int, scope: str = "", tenant: str = TENANT_SLUG) -> dict[str, str]:
        token = make_user_token(user_id=user_id, scope=scope, tenant=tenant)
        return {"Authorization": f"Bearer {token}"}

    return _make
