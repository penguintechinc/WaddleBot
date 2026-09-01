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
"""

from __future__ import annotations

from typing import Any

import pytest
from flask_core.auth import create_jwt_token
from flask_core.database import AsyncDAL
from pydal import DAL, Field

from services.schema import bind_auth_tables, bind_tenant_tables

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


@pytest.fixture
def tenant_admin_db(tmp_path: Any) -> Any:
    """File-backed `AsyncDAL` with every table the M2 Core Tenant group queries.

    Additive, independent of `auth_db` (own `tmp_path` sqlite file, own
    `AsyncDAL`) -- per `hub_api/PORTING.md`'s Test pattern section, a
    group needing tables `bind_auth_tables()` doesn't cover gets its own
    fixture rather than editing `auth_db` in place. Defines a narrow
    `tenants` table first (mirrors `auth_db`'s own bootstrap step -- in
    production this is `app.py::_bind_reference_tables`, off-limits to
    this port task), then calls the REAL `bind_auth_tables`/
    `bind_tenant_tables` -- the same functions `blueprints/v1/tenant.py`'s
    `_dal()` calls in production -- so this fixture exercises the actual
    binding code path (including `bind_tenant_tables`'s `redefine=True`
    extension of `tenants`/`communities`) rather than a hand-duplicated
    field list that could drift from it.
    """
    async_dal = AsyncDAL(f"sqlite://{tmp_path / 'tenant_test.db'}", pool_size=1)
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
    bind_tenant_tables(dal, migrate=True)
    dal.tenants.insert(slug=TENANT_SLUG, display_name="Acme Corp", is_active=True)
    dal.commit()
    # See auth_db's own comment above -- forces lazy CREATE TABLE DDL to
    # run on the main thread before any async_dal worker thread exists.
    for table_name in dal.tables:
        dal(dal[table_name]).count()
    yield async_dal
    dal.close()


def make_token(*, scope: str = "", tenant: str = TENANT_SLUG, user_id: str = "u1") -> str:
    """Mint a JWT via the real `flask_core.auth.create_jwt_token` -- no hand-rolled JWTs.

    `user_id` defaults to the non-numeric `"u1"` (existing platform tests'
    expectation); Community-module tests exercising `auth_required` +
    `int(get_current_user(request)["user_id"])` pass a numeric string
    (e.g. `user_id="1"`) instead.
    """
    return create_jwt_token(
        user_id=user_id,
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


@pytest.fixture
def auth_headers():
    """Factory fixture: `auth_headers(scope="platform:read")` -> Authorization header dict."""

    def _make(*, scope: str = "", tenant: str = TENANT_SLUG, user_id: str = "u1") -> dict[str, str]:
        return {
            "Authorization": f"Bearer {make_token(scope=scope, tenant=tenant, user_id=user_id)}"
        }

    return _make


#: Matches `services/community_common.py::is_valid_service_key`'s `SERVICE_API_KEY` lookup.
SERVICE_API_KEY = "test-service-key"


@pytest.fixture
def community_db(tenant_db: Any, monkeypatch: Any) -> Any:
    """`tenant_db` + every Community-module (M6) table (`migrate=True`) + one seeded community.

    `ensure_community_tables(dal, migrate=True)` reuses the exact same
    field definitions production binds with `migrate=False` (see
    `community_common.py`'s docstring) -- one schema definition, not a
    second one drifting in test fixtures. Also sets `SERVICE_API_KEY` for
    the internal (X-Service-Key) endpoint tests.
    """
    from services.community_common import ensure_community_tables
    from services.community_relay import _ensure_relay_tables

    monkeypatch.setenv("SERVICE_API_KEY", SERVICE_API_KEY)

    dal = tenant_db
    ensure_community_tables(dal, migrate=True)
    _ensure_relay_tables(dal, migrate=True)

    # `hub_user_identities` is a Core/Identity table (000_create_base_schema.sql),
    # not owned by the Community-module port -- `_find_hub_user_id` (community_
    # activity.py) queries it via raw `executesql`, which needs no pydal
    # `define_table` in production (the physical table already exists via
    # Core's own migration) but does need one here so sqlite:memory has a
    # real backing table to query against.
    if "hub_user_identities" not in dal.tables:
        dal.define_table(
            "hub_user_identities",
            dal.Field("hub_user_id", "integer"),
            dal.Field("platform", "string"),
            dal.Field("platform_user_id", "string"),
            migrate=True,
        )

    tenant_row = dal(dal.tenants.slug == TENANT_SLUG).select().first()
    community_id = dal.communities.insert(name="test-community", tenant_id=tenant_row.id)
    dal.commit()
    return dal, community_id


@pytest.fixture
def service_key_headers() -> dict[str, str]:
    """`X-Service-Key` header matching `community_db`'s `SERVICE_API_KEY`."""
    return {"X-Service-Key": SERVICE_API_KEY}


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
