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

`overlay_db` (M7 Streaming/overlay+calls group) is this port's own
additive fixture, mirroring `auth_db`'s file-backed-sqlite/`migrate=True`
shape but also calling `services.schema.bind_overlay_tables()` for
`community_overlay_tokens`/`overlay_access_log` -- new tables `auth_db`
doesn't bind. Named `overlay_db` (not `streaming_db`) to avoid colliding
with the M7 Streaming (music/stream/streaming) group's own `streaming_db`
fixture below, which binds an unrelated table set via a same-named-but-
different `bind_streaming_tables()`/`bind_overlay_tables()` split (see
`services/schema.py`'s own docstring on that rename). `_seed_community`/
`_seed_membership` are this group's own seeding helpers for
`communities`/`community_members` (`services.community_access`'s authz
checks).
"""

from __future__ import annotations

from typing import Any

import pytest
from flask_core.auth import create_jwt_token
from flask_core.database import AsyncDAL
from pydal import DAL, Field

from services.schema import (
    bind_admin_tables,
    bind_auth_tables,
    bind_community_authz_tables,
    bind_github_sync_tables,
    bind_overlay_tables,
    bind_platform_tables,
    bind_privacy_tables,
    bind_streaming_tables,
    bind_superadmin_tenant_fields,
    bind_tenant_tables,
)

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


#: Second tenant slug -- exists only in `overlay_db`, for cross-tenant IDOR tests
#: (`services.community_access._require_community_in_tenant`).
OTHER_TENANT_SLUG = "other-corp"


@pytest.fixture
def overlay_db(tmp_path: Any) -> Any:
    """File-backed `AsyncDAL` with `tenants` + auth tables + M7's own overlay/calls tables.

    Same connection-visibility rationale as `auth_db` (see its own
    docstring) -- a fresh file, not shared with `auth_db`, so tests in
    this group don't collide with M1's own fixture instance.
    """
    async_dal = AsyncDAL(f"sqlite://{tmp_path / 'overlay_test.db'}", pool_size=1)
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
    bind_overlay_tables(dal, migrate=True)
    dal.tenants.insert(slug=TENANT_SLUG, display_name="Acme Corp", is_active=True)
    dal.tenants.insert(slug=OTHER_TENANT_SLUG, display_name="Other Corp", is_active=True)
    dal.commit()
    for table_name in dal.tables:
        dal(dal[table_name]).count()
    yield async_dal
    dal.close()


@pytest.fixture
def streaming_db(tmp_path: Any) -> Any:
    """File-backed `AsyncDAL` for the M7 Streaming group (music/stream/streaming).

    Additive fixture (`hub_api/PORTING.md`: "add your own bind_<group>_
    tables() call to auth_db (or a new fixture) ... additive only, never
    edit the M1 group's own fixture logic") -- extends `auth_db`'s exact
    pattern with `services.schema.bind_streaming_tables()` on top of
    `bind_auth_tables()`, since `services.community_authz` needs both M1's
    `community_members`/`tenant_admins`/`communities` tables AND M7's own
    `community_roles`/`coordination`/`community_servers`/music tables in
    the same DAL instance.
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
    dal.commit()
    # See auth_db's own docstring -- forces lazy-table DDL to run on the
    # main thread before any AsyncDAL executor thread exists.
    for table_name in dal.tables:
        dal(dal[table_name]).count()
    yield async_dal
    dal.close()


@pytest.fixture
def automation_db(tmp_path: Any) -> Any:
    """File-backed `AsyncDAL` for the M-automation port group (workflow + github_sync).

    Same file-backed-sqlite/`pool_size=1`/lazy-table-touch rationale as
    `auth_db` above -- see that fixture's own docstring for the full
    gotcha writeup. Extends `bind_auth_tables()` with
    `bind_community_authz_tables()` (`community_roles`, for
    `services.community_authz.require_community_admin()`) and
    `bind_github_sync_tables()` (`github_repo_connections` and friends).
    """
    async_dal = AsyncDAL(f"sqlite://{tmp_path / 'automation_test.db'}", pool_size=1)
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
    bind_community_authz_tables(dal, migrate=True)
    bind_github_sync_tables(dal, migrate=True)
    dal.tenants.insert(slug=TENANT_SLUG, display_name="Acme Corp", is_active=True)
    dal.commit()
    for table_name in dal.tables:
        dal(dal[table_name]).count()
    yield async_dal
    dal.close()


def seed_community(
    overlay_db: Any, *, tenant_slug: str = TENANT_SLUG, name: str = "acme-community"
) -> int:
    """Insert one `communities` row scoped to `tenant_slug`; returns its id."""
    dal = overlay_db.dal
    tenant = dal(dal.tenants.slug == tenant_slug).select().first()
    community_id: int = dal.communities.insert(
        name=name, display_name=name, tenant_id=tenant.id, is_active=True
    )
    dal.commit()
    return community_id


def seed_membership(
    overlay_db: Any, *, community_id: int, user_id: int, role: str = "community-owner"
) -> None:
    """Insert one active `community_members` row for `user_id` in `community_id`."""
    dal = overlay_db.dal
    dal.community_members.insert(
        community_id=community_id, user_id=str(user_id), role=role, is_active=True
    )
    dal.commit()


@pytest.fixture
def privacy_db(tmp_path: Any) -> Any:
    """`auth_db`'s tables PLUS the Privacy/Compliance group's own.

    See `services.schema.bind_privacy_tables`.

    Same file-backed-sqlite/`pool_size=1`/eager-table-touch rationale as
    `auth_db` -- see that fixture's own docstring for the full gotcha
    writeup. A separate fixture (not a mutation of `auth_db`) per `hub_api/
    PORTING.md`'s Test pattern: additive-only, never edit another group's
    fixture in place.
    """
    async_dal = AsyncDAL(f"sqlite://{tmp_path / 'privacy_test.db'}", pool_size=1)
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
    bind_privacy_tables(dal, migrate=True)
    dal.tenants.insert(slug=TENANT_SLUG, display_name="Acme Corp", is_active=True)
    dal.commit()
    for table_name in dal.tables:
        dal(dal[table_name]).count()
    yield async_dal
    dal.close()


@pytest.fixture
def platform_db(tmp_path: Any) -> Any:
    """File-backed `AsyncDAL` for the M3 Platform-admin/Public group.

    Same `tmp_path`-backed-sqlite-file / `pool_size=1` / touch-every-table
    rationale as `auth_db` above (see its own docstring) -- additive, new
    fixture rather than editing `auth_db` in place (`hub_api/PORTING.md`'s
    Test pattern: "add your own `bind_<group>_tables()` call ... never
    edit the M1 group's own fixture logic"). `bind_platform_tables()`
    calls `bind_auth_tables()` itself, so this fixture alone covers every
    table this group's blueprints query.
    """
    async_dal = AsyncDAL(f"sqlite://{tmp_path / 'platform_test.db'}", pool_size=1)
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
    bind_platform_tables(dal, migrate=True)
    dal.tenants.insert(slug=TENANT_SLUG, display_name="Acme Corp", is_active=True)
    dal.commit()
    for table_name in dal.tables:
        dal(dal[table_name]).count()
    yield async_dal
    dal.close()


@pytest.fixture
def admin_db(tmp_path: Any) -> Any:
    """File-backed `AsyncDAL` for the M3 Platform-admin group (admin/superadmin blueprints).

    Extends `auth_db`'s exact pattern (file-backed sqlite -- see that
    fixture's own docstring for the connection-scoping/`pool_size=1`
    rationale) with `bind_admin_tables()` + `bind_superadmin_tenant_fields()`,
    additive per `hub_api/PORTING.md`'s test-pattern guidance rather than
    editing `auth_db` in place.
    """
    async_dal = AsyncDAL(f"sqlite://{tmp_path / 'admin_test.db'}", pool_size=1)
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
    bind_admin_tables(dal, migrate=True)
    bind_superadmin_tenant_fields(dal, migrate=True)
    dal.tenants.insert(slug=TENANT_SLUG, display_name="Acme Corp", is_active=True)
    dal.commit()
    # See auth_db's own comment above -- forces lazy CREATE TABLE DDL to
    # run on the main thread before any async_dal worker thread exists.
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


def make_user_token_with_roles(
    *, user_id: int, roles: list[str], scope: str = "", tenant: str = TENANT_SLUG
) -> str:
    """Like `make_user_token`, but with a caller-supplied `roles` claim.

    Additive helper (new function, not an edit to `make_user_token`) --
    needed by `services.community_authz`'s super-admin/platform-admin
    bypass tests (`roles=["super_admin"]`), which the fixed
    `roles=["viewer"]` in `make_user_token` can't express.
    """
    return create_jwt_token(
        user_id=str(user_id),
        username="alice",
        email="alice@example.com",
        roles=roles,
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
