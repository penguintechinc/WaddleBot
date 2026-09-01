"""Resolve a bundle's declared `action_target` from the App Bundle 3-tier config.

Reads `app_activations.config` (community-scoped, migration
069_app_bundle_tiers.sql) first, falling back to `app_tenant_availability.
config_defaults` (tenant-wide) -- same narrowest-wins precedence
`flask_core.app_installations_db.DBInstallationLookup.find` documents for
`resolve_apps` (libs/flask_core/flask_core/app_binding.py), specialized
here to a single known `app_id` (the queue envelope already carries it, so
there's no `feature`-based fan-out to do) rather than reused directly.

Read-only: this module's `AsyncDAL` is constructed against a read-only DB
account (`Config.database_url`, `DB_USER=svc-action-ro` by default,
config.py) -- svc-action never writes `app_catalog`/`app_activations`.

Table binding reuses `flask_core.app_bundle_tables.init_app_bundle_tables`
(the same DDL-owning migration, `migrate=False` throughout) rather than
re-declaring the schema locally, per this repo's established
"pydal maps onto the already-migrated table, it never owns this DDL"
convention (see that module's own docstring). Callers must call
`init_app_bundle_tables(dal.dal)` themselves *before* constructing this
class (`runner.py`'s `start()` does so alongside
`init_action_dispatch_log_table`) -- not done in `__init__` here so tests
can pre-migrate the same tables with `migrate=True` against sqlite
(PORTING.md Gotcha #2) without a duplicate `define_table` call colliding
with this class's own.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from flask_core import AsyncDAL


class ActionConfigLookup:
    """Read-only lookup of one (tenant, community, app_id)'s `action_target` config.

    Requires `flask_core.app_bundle_tables.init_app_bundle_tables(dal.dal)`
    to have already been called on `dal` -- see module docstring.
    """

    def __init__(self, dal: AsyncDAL) -> None:
        """Wrap `dal` (its C3 tables already bound by the caller -- see class docstring)."""
        self._dal = dal

    async def get_action_target_config(
        self, *, tenant: str, community: str | None, app_id: str
    ) -> Mapping[str, Any] | None:
        """Return the raw `action_target` dict for `app_id`, or `None` if unconfigured.

        `community=None` (tenant-wide activation, `c:_tenant` in the queue
        key namespace -- stream_pipeline.py's
        `_TENANT_WIDE_COMMUNITY_SEGMENT`) skips the community-scoped lookup
        entirely and reads `app_tenant_availability.config_defaults`
        directly. A community-scoped activation with no `action_target` key
        in its own `config` also falls back to the tenant-wide default --
        matches the "bundle default -> tenant -> community" precedence
        `app_installations_db.py`'s module docstring describes (design doc
        §10 open decision #2), narrowest non-empty wins.
        """
        tenant_id = int(tenant)
        dal = self._dal.dal

        if community is not None:
            # PORTING.md Gotcha #1: select_async's `query` arg must already be a
            # pydal Set (`dal(condition)`), not a bare Query.
            activation_set = dal(
                (dal.app_activations.tenant_id == tenant_id)
                & (dal.app_activations.community_id == int(community))
                & (dal.app_activations.app_id == app_id)
                & (dal.app_activations.enabled == True)  # noqa: E712 -- pydal query operator
            )
            rows = await self._dal.select_async(
                activation_set, dal.app_activations.config, limitby=(0, 1)
            )
            if rows:
                target: Mapping[str, Any] | None = dict(rows[0].config or {}).get("action_target")
                if target:
                    return target

        avail_set = dal(
            (dal.app_tenant_availability.tenant_id == tenant_id)
            & (dal.app_tenant_availability.app_id == app_id)
            & (dal.app_tenant_availability.available == True)  # noqa: E712
        )
        avail_rows = await self._dal.select_async(
            avail_set, dal.app_tenant_availability.config_defaults, limitby=(0, 1)
        )
        if avail_rows:
            avail_target: Mapping[str, Any] | None = dict(avail_rows[0].config_defaults or {}).get(
                "action_target"
            )
            if avail_target:
                return avail_target

        return None
