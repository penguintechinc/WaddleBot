-- Migration 069: App Bundle 3-tier persistence (install -> available -> activate)
-- Per docs/plans/2026-08-31-app-bundle-sdk-design.md Sec5.1 (Phase C3 groundwork).
-- Three tiers narrowing global -> tenant -> community, with the hard subset
-- invariant "activated is a subset of available is a subset of installed". The invariant is
-- enforced at the application layer, at write time (see
-- libs/flask_core/flask_core/app_installations_db.py's check_availability_insert_allowed
-- / check_activation_insert_allowed) -- it is not expressible as a single SQL
-- constraint spanning three tables (design doc Sec5.1).
--
-- Supersedes `hub_module_installations` (000_create_base_schema.sql:259-269) per
-- the base design doc's note: "Renaming `hub_module_installations` to
-- `app_installations` is part of P1... only the name stops lying." That rename
-- and any backfill from `hub_module_installations`/`marketplace_subscriptions`
-- is design doc Sec10 open decision #5 -- not performed by this migration, which
-- only adds the three new tables alongside the existing ones.
--
-- Encryption at rest: engine-level (PostgreSQL volume/TDE per security.md
-- Encryption -- Storage baseline). No column-level action needed here.

-- GLOBAL: installed -- hub-api is the sole writer (design doc Sec6.1), primary/write DB only.
CREATE TABLE IF NOT EXISTS app_catalog (
    app_id                  TEXT PRIMARY KEY,          -- waddles.<module>.<feature>.<app>
    manifest_version        TEXT NOT NULL,              -- bundle.yaml `version`
    module                  TEXT NOT NULL,
    feature                 TEXT NOT NULL,
    provider                TEXT NOT NULL,               -- builtin | thirdparty
    execution_model         TEXT NOT NULL,               -- native | thirdparty
    is_default               BOOLEAN DEFAULT FALSE,
    compatible_with          TEXT[] DEFAULT '{}',
    incompatible_with        TEXT[] DEFAULT '{}',
    platform_compatibility   JSONB NOT NULL,             -- {tested_with,min_version,max_version}
    status                   TEXT DEFAULT 'active',       -- active | deprecated | yanked
    installed_at              TIMESTAMPTZ DEFAULT NOW()
);

-- TENANT: available -- which installed bundles a tenant may activate.
CREATE TABLE IF NOT EXISTS app_tenant_availability (
    id             SERIAL PRIMARY KEY,
    tenant_id      INTEGER NOT NULL REFERENCES tenants(id),
    app_id         TEXT NOT NULL REFERENCES app_catalog(app_id),
    available      BOOLEAN DEFAULT TRUE,
    config_defaults JSONB DEFAULT '{}',                  -- tenant-level override of bundle.yaml defaults
    UNIQUE(tenant_id, app_id)
);

-- COMMUNITY: activated (the set) -- coexistence, not a single-winner binding
-- (design doc Sec5.2/Sec7.1); resolve_apps fans out to every enabled row.
CREATE TABLE IF NOT EXISTS app_activations (
    id            SERIAL PRIMARY KEY,
    community_id  INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    tenant_id     INTEGER NOT NULL REFERENCES tenants(id),   -- denormalized, for ACL/stream scoping
    app_id        TEXT NOT NULL REFERENCES app_catalog(app_id),
    enabled       BOOLEAN DEFAULT TRUE,
    config        JSONB DEFAULT '{}',
    activated_by  INTEGER,
    activated_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(community_id, app_id)
);

-- Indexes: by feature, by community, by tenant (per task spec) -- the UNIQUE
-- constraints above already index (tenant_id, app_id) and (community_id, app_id)
-- for the exact-match lookups; these cover the single-column axes used by
-- DBInstallationLookup.find() and the admin/marketplace listing endpoints.
CREATE INDEX IF NOT EXISTS idx_app_catalog_feature
    ON app_catalog (feature);

CREATE INDEX IF NOT EXISTS idx_app_tenant_availability_tenant
    ON app_tenant_availability (tenant_id);

CREATE INDEX IF NOT EXISTS idx_app_activations_community
    ON app_activations (community_id);

CREATE INDEX IF NOT EXISTS idx_app_activations_tenant
    ON app_activations (tenant_id);
