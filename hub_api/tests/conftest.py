"""Shared fixtures for hub-api's own tests.

`tenant_db` mirrors `libs/flask_core/tests/test_tenancy.py` and
`test_mcp_routes.py`'s own fixture exactly (in-memory pydal `tenants`
table, `migrate=True`) -- ephemeral, test-only schema. Production never
migrates `tenants` (see `app.py::_bind_reference_tables` -- schema owned
by `config/postgres/migrations/058_tenants_and_claims.sql`); tests need a
real row to resolve against, so they get their own throwaway table
instead of relaxing that production invariant.
"""

from __future__ import annotations

from typing import Any

import pytest
from flask_core.auth import create_jwt_token
from pydal import DAL, Field

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
