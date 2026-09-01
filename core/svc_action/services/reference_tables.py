"""Minimal `tenants`/`communities` pydal stubs -- FK-resolution only, no DDL.

svc-action is its own standalone process with its own pydal `DAL` instance
(per-service DB account, backend.md Database Tier Architecture) -- it never
shares hub-api's in-process `DAL` object, so it must bind its own
placeholder `tenants`/`communities` tables before `flask_core.
app_bundle_tables.init_app_bundle_tables`/`services.dispatch_log.
init_action_dispatch_log_table` can define `reference tenants`/
`reference communities` fields against them. Mirrors hub_api/app.py's
`_bind_reference_tables` pattern (`migrate=False` always -- schema owned by
`config/postgres/migrations/058_tenants_and_claims.sql` /
`047_add_community_types_workforce_support.sql`, never by this process) --
trimmed to zero extra columns since svc-action never selects a `tenants`/
`communities` field, only uses them as FK targets for `app_activations.
tenant_id`/`community_id` and `action_dispatch_log.tenant_id`/
`community_id`.
"""

from __future__ import annotations

from typing import Any


def bind_minimal_reference_tables(dal: Any) -> None:
    """Define bare `tenants`/`communities` tables (id only) on `dal`.

    Idempotent no-op if already bound.
    """
    if "tenants" not in dal.tables:
        dal.define_table("tenants", migrate=False)
    if "communities" not in dal.tables:
        dal.define_table("communities", dal.Field("tenant_id", "reference tenants"), migrate=False)
