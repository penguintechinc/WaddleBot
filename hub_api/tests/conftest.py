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


@pytest.fixture
def auth_headers():
    """Factory fixture: `auth_headers(scope="platform:read")` -> Authorization header dict."""

    def _make(*, scope: str = "", tenant: str = TENANT_SLUG) -> dict[str, str]:
        return {"Authorization": f"Bearer {make_token(scope=scope, tenant=tenant)}"}

    return _make
