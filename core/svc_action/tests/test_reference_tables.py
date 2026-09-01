"""services/reference_tables.py -- minimal tenants/communities FK-target stubs."""

from __future__ import annotations

from pathlib import Path

from flask_core import AsyncDAL

from services.reference_tables import bind_minimal_reference_tables


def test_binds_tenants_and_communities(tmp_path: Path) -> None:
    async_dal = AsyncDAL(f"sqlite://{tmp_path}/ref.db", pool_size=1, migrate=False)
    bind_minimal_reference_tables(async_dal.dal)
    assert "tenants" in async_dal.dal.tables
    assert "communities" in async_dal.dal.tables
    assert "tenant_id" in async_dal.dal.communities.fields


def test_idempotent_when_already_bound(tmp_path: Path) -> None:
    """Calling twice on the same DAL instance must not raise (idempotent no-op)."""
    async_dal = AsyncDAL(f"sqlite://{tmp_path}/ref2.db", pool_size=1, migrate=False)
    bind_minimal_reference_tables(async_dal.dal)
    bind_minimal_reference_tables(async_dal.dal)  # must not raise "table already defined"
    assert "tenants" in async_dal.dal.tables
