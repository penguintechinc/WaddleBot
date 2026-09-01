"""services/config_lookup.py -- ActionConfigLookup against a file-backed sqlite AsyncDAL.

File-backed (not `sqlite:memory`) + `pool_size=1`, per hub_api/PORTING.md
Gotcha #2: `AsyncDAL`'s calls run in a ThreadPoolExecutor (a different OS
thread per call), and sqlite's `:memory:` DB is connection-scoped -- a
second connection (i.e. a second executor thread) would see a blank DB.

Tables are defined here with `migrate=True` (mirroring
`test_app_bundle_tables.py`/`test_app_installations_db.py`'s own fixture
pattern) rather than via `init_app_bundle_tables`/
`bind_minimal_reference_tables` directly -- both of those hardcode
`migrate=False` (production: schema owned by the SQL migration files), so
calling them against a fresh throwaway sqlite file would never issue the
`CREATE TABLE` DDL and every query would 500 with "no such table". Field
names/types below are kept byte-identical to those two modules'
declarations so this is exercising the same schema `ActionConfigLookup`
queries in production, just self-migrated for the test.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from flask_core import AsyncDAL

from services.config_lookup import ActionConfigLookup


@pytest.fixture
def dal(tmp_path: Path) -> AsyncDAL:
    """AsyncDAL against a throwaway file-backed sqlite DB with the C3 tables migrated."""
    async_dal = AsyncDAL(f"sqlite://{tmp_path}/test.db", pool_size=1, migrate=True)
    d = async_dal.dal

    d.define_table("tenants", migrate=True)
    d.define_table("communities", d.Field("tenant_id", "reference tenants"), migrate=True)

    d.define_table(
        "app_catalog",
        d.Field("app_id", "string", notnull=True),
        d.Field("manifest_version", "string", notnull=True),
        d.Field("module", "string", notnull=True),
        d.Field("feature", "string", notnull=True),
        d.Field("provider", "string", notnull=True),
        d.Field("execution_model", "string", notnull=True),
        d.Field("is_default", "boolean", default=False),
        d.Field("compatible_with", "list:string", default=[]),
        d.Field("incompatible_with", "list:string", default=[]),
        d.Field("platform_compatibility", "json", notnull=True),
        d.Field("status", "string", default="active"),
        migrate=True,
    )
    d.define_table(
        "app_tenant_availability",
        d.Field("tenant_id", "reference tenants", notnull=True),
        d.Field("app_id", "string", notnull=True),
        d.Field("available", "boolean", default=True),
        d.Field("config_defaults", "json", default={}),
        migrate=True,
    )
    d.define_table(
        "app_activations",
        d.Field("community_id", "reference communities", notnull=True),
        d.Field("tenant_id", "reference tenants", notnull=True),
        d.Field("app_id", "string", notnull=True),
        d.Field("enabled", "boolean", default=True),
        d.Field("config", "json", default={}),
        migrate=True,
    )

    # FK targets -- app_activations/app_tenant_availability reference these by
    # id, sqlite enforces the FK, so every test's tenant_id=1/community_id=42
    # needs a matching row to exist first.
    d.tenants.insert(id=1)
    d.communities.insert(id=42, tenant_id=1)
    d.commit()

    return async_dal


async def test_returns_community_scoped_action_target(dal: AsyncDAL) -> None:
    async_dal_table = dal.dal.app_activations
    async_dal_table.insert(
        community_id=42,
        tenant_id=1,
        app_id="waddles.bot.shoutout.default",
        enabled=True,
        config={"action_target": {"type": "webhook", "url": "https://example.com/hook"}},
    )
    dal.dal.commit()

    lookup = ActionConfigLookup(dal)
    target = await lookup.get_action_target_config(
        tenant="1", community="42", app_id="waddles.bot.shoutout.default"
    )
    assert target == {"type": "webhook", "url": "https://example.com/hook"}


async def test_falls_back_to_tenant_wide_default(dal: AsyncDAL) -> None:
    dal.dal.app_tenant_availability.insert(
        tenant_id=1,
        app_id="waddles.bot.shoutout.default",
        available=True,
        config_defaults={"action_target": {"type": "message_queue", "channel": "waddles:notify"}},
    )
    dal.dal.commit()

    lookup = ActionConfigLookup(dal)
    target = await lookup.get_action_target_config(
        tenant="1", community="42", app_id="waddles.bot.shoutout.default"
    )
    assert target == {"type": "message_queue", "channel": "waddles:notify"}


async def test_community_scoped_takes_precedence_over_tenant_wide(dal: AsyncDAL) -> None:
    dal.dal.app_tenant_availability.insert(
        tenant_id=1,
        app_id="waddles.bot.shoutout.default",
        available=True,
        config_defaults={"action_target": {"type": "message_queue", "channel": "tenant-default"}},
    )
    dal.dal.app_activations.insert(
        community_id=42,
        tenant_id=1,
        app_id="waddles.bot.shoutout.default",
        enabled=True,
        config={"action_target": {"type": "message_queue", "channel": "community-override"}},
    )
    dal.dal.commit()

    lookup = ActionConfigLookup(dal)
    target = await lookup.get_action_target_config(
        tenant="1", community="42", app_id="waddles.bot.shoutout.default"
    )
    assert target == {"type": "message_queue", "channel": "community-override"}


async def test_tenant_wide_envelope_skips_community_scoped_lookup(dal: AsyncDAL) -> None:
    dal.dal.app_tenant_availability.insert(
        tenant_id=1,
        app_id="waddles.bot.shoutout.default",
        available=True,
        config_defaults={"action_target": {"type": "message_queue", "channel": "tenant-default"}},
    )
    dal.dal.commit()

    lookup = ActionConfigLookup(dal)
    target = await lookup.get_action_target_config(
        tenant="1", community=None, app_id="waddles.bot.shoutout.default"
    )
    assert target == {"type": "message_queue", "channel": "tenant-default"}


async def test_no_config_returns_none(dal: AsyncDAL) -> None:
    lookup = ActionConfigLookup(dal)
    target = await lookup.get_action_target_config(
        tenant="1", community="42", app_id="waddles.bot.shoutout.default"
    )
    assert target is None


async def test_disabled_activation_is_ignored(dal: AsyncDAL) -> None:
    dal.dal.app_activations.insert(
        community_id=42,
        tenant_id=1,
        app_id="waddles.bot.shoutout.default",
        enabled=False,
        config={"action_target": {"type": "message_queue", "channel": "should-not-see-this"}},
    )
    dal.dal.commit()

    lookup = ActionConfigLookup(dal)
    target = await lookup.get_action_target_config(
        tenant="1", community="42", app_id="waddles.bot.shoutout.default"
    )
    assert target is None
