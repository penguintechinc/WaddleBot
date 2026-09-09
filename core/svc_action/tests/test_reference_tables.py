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


def test_tenants_table_binds_slug_for_slug_to_id_resolution(tmp_path: Path) -> None:
    """`runner.py::_resolve_tenant_id` selects on `tenants.slug` -- must be bound, not id-only.

    `bind_minimal_reference_tables` always passes `migrate=False` (schema
    owned by migration 058, never this process) so this only proves the
    field is exposed for query construction (`dal.tenants.slug == ...`),
    not that a physical column exists -- `test_runner.py`'s own `dal`
    fixture (a throwaway, actually-migrated sqlite schema) exercises the
    real slug -> id lookup end to end.
    """
    async_dal = AsyncDAL(f"sqlite://{tmp_path}/ref3.db", pool_size=1, migrate=False)
    bind_minimal_reference_tables(async_dal.dal)
    assert "slug" in async_dal.dal.tenants.fields
    query = async_dal.dal.tenants.slug == "global"
    assert query.first.name == "slug"


def test_idempotent_when_already_bound(tmp_path: Path) -> None:
    """Calling twice on the same DAL instance must not raise (idempotent no-op)."""
    async_dal = AsyncDAL(f"sqlite://{tmp_path}/ref2.db", pool_size=1, migrate=False)
    bind_minimal_reference_tables(async_dal.dal)
    bind_minimal_reference_tables(async_dal.dal)  # must not raise "table already defined"
    assert "tenants" in async_dal.dal.tables
