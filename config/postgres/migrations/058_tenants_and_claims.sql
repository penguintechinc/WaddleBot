-- Migration 058: Multi-tenancy and OIDC-style claims
-- WaddleBot v2.0.0
-- Depends on: 057_community_interaction.sql

BEGIN;

-- ============================================================
-- 1a. Tenants table
-- ============================================================

CREATE TABLE IF NOT EXISTS tenants (
  id            SERIAL PRIMARY KEY,
  slug          VARCHAR(100) NOT NULL UNIQUE,
  display_name  VARCHAR(255) NOT NULL,
  description   TEXT,
  logo_url      TEXT,
  is_global     BOOLEAN NOT NULL DEFAULT FALSE,
  is_active     BOOLEAN NOT NULL DEFAULT TRUE,
  config        JSONB NOT NULL DEFAULT '{}',
  allowed_module_ids INTEGER[] DEFAULT NULL,
  seat_limit    INTEGER DEFAULT NULL,
  created_at    TIMESTAMPTZ DEFAULT NOW(),
  updated_at    TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO tenants (slug, display_name, is_global)
  VALUES ('global', 'Waddles', TRUE)
  ON CONFLICT (slug) DO NOTHING;

-- ============================================================
-- 1b. Tenant admins
-- ============================================================

CREATE TABLE IF NOT EXISTS tenant_admins (
  id          SERIAL PRIMARY KEY,
  tenant_id   INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  user_id     INTEGER NOT NULL REFERENCES hub_users(id) ON DELETE CASCADE,
  role        VARCHAR(50) NOT NULL DEFAULT 'tenant-admin',
  created_at  TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(tenant_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_tenant_admins_tenant_id ON tenant_admins(tenant_id);
CREATE INDEX IF NOT EXISTS idx_tenant_admins_user_id ON tenant_admins(user_id);

-- ============================================================
-- 1c. Add tenant_id to communities
-- ============================================================

ALTER TABLE communities ADD COLUMN IF NOT EXISTS tenant_id INTEGER REFERENCES tenants(id);

UPDATE communities
  SET tenant_id = (SELECT id FROM tenants WHERE is_global = TRUE)
  WHERE tenant_id IS NULL;

ALTER TABLE communities ALTER COLUMN tenant_id SET NOT NULL;

CREATE INDEX IF NOT EXISTS idx_communities_tenant_id ON communities(tenant_id);

-- ============================================================
-- 1d. Tenant-scoped settings
-- ============================================================

CREATE TABLE IF NOT EXISTS tenant_settings (
  id          SERIAL PRIMARY KEY,
  tenant_id   INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  key         VARCHAR(100) NOT NULL,
  value       TEXT,
  created_at  TIMESTAMPTZ DEFAULT NOW(),
  updated_at  TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(tenant_id, key)
);

CREATE INDEX IF NOT EXISTS idx_tenant_settings_tenant_id ON tenant_settings(tenant_id);

-- Migrate existing hub_settings into tenant_settings for global tenant
INSERT INTO tenant_settings (tenant_id, key, value)
  SELECT (SELECT id FROM tenants WHERE is_global = TRUE), setting_key, setting_value
  FROM hub_settings
  ON CONFLICT (tenant_id, key) DO NOTHING;

-- ============================================================
-- 1e. Community roles table
-- ============================================================

CREATE TABLE IF NOT EXISTS community_roles (
  id            SERIAL PRIMARY KEY,
  community_id  INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
  name          VARCHAR(50) NOT NULL,
  display_name  VARCHAR(100),
  description   TEXT,
  is_system     BOOLEAN NOT NULL DEFAULT FALSE,
  priority      INTEGER NOT NULL DEFAULT 0,
  base_claims   JSONB NOT NULL DEFAULT '{"scopes":[]}',
  created_at    TIMESTAMPTZ DEFAULT NOW(),
  updated_at    TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(community_id, name)
);

CREATE INDEX IF NOT EXISTS idx_community_roles_community_id ON community_roles(community_id);

-- ============================================================
-- 1e-2. Function to seed system roles for a community
-- ============================================================

CREATE OR REPLACE FUNCTION seed_community_system_roles(p_community_id INTEGER)
RETURNS VOID AS $$
BEGIN
  -- member
  INSERT INTO community_roles (community_id, name, display_name, is_system, priority, base_claims)
    VALUES (
      p_community_id,
      'member',
      'Member',
      TRUE,
      10,
      '{"scopes":["community:read","channels:read","channels:send_chat","channels:speak","channels:share_video","channels:screenshare"]}'
    )
    ON CONFLICT (community_id, name) DO NOTHING;

  -- speaker
  INSERT INTO community_roles (community_id, name, display_name, is_system, priority, base_claims)
    VALUES (
      p_community_id,
      'speaker',
      'Speaker',
      TRUE,
      20,
      '{"scopes":["community:read","channels:read","channels:send_chat","channels:speak","channels:share_video","channels:screenshare"]}'
    )
    ON CONFLICT (community_id, name) DO NOTHING;

  -- moderator
  INSERT INTO community_roles (community_id, name, display_name, is_system, priority, base_claims)
    VALUES (
      p_community_id,
      'moderator',
      'Moderator',
      TRUE,
      30,
      '{"scopes":["community:read","channels:read","channels:send_chat","channels:speak","channels:share_video","channels:screenshare","community:manage_channels","channels:moderate","channels:override_screenshare"]}'
    )
    ON CONFLICT (community_id, name) DO NOTHING;

  -- community-admin
  INSERT INTO community_roles (community_id, name, display_name, is_system, priority, base_claims)
    VALUES (
      p_community_id,
      'community-admin',
      'Admin',
      TRUE,
      40,
      '{"scopes":["community:read","channels:read","channels:send_chat","channels:speak","channels:share_video","channels:screenshare","community:manage_channels","channels:moderate","channels:override_screenshare","community:manage_members","community:manage_roles"]}'
    )
    ON CONFLICT (community_id, name) DO NOTHING;

  -- community-owner
  INSERT INTO community_roles (community_id, name, display_name, is_system, priority, base_claims)
    VALUES (
      p_community_id,
      'community-owner',
      'Owner',
      TRUE,
      50,
      '{"scopes":["community:read","community:manage_channels","community:manage_members","community:manage_roles","channels:read","channels:send_chat","channels:speak","channels:share_video","channels:screenshare","channels:moderate","channels:override_screenshare","resource:delete_any","resource:pin","resource:moderate"]}'
    )
    ON CONFLICT (community_id, name) DO NOTHING;
END;
$$ LANGUAGE plpgsql;

-- Seed system roles for all existing communities
SELECT seed_community_system_roles(id) FROM communities;

-- ============================================================
-- 1f. Update community_members
-- ============================================================

ALTER TABLE community_members
  ADD COLUMN IF NOT EXISTS community_role_id INTEGER REFERENCES community_roles(id),
  ADD COLUMN IF NOT EXISTS claims_cache JSONB DEFAULT NULL;

CREATE INDEX IF NOT EXISTS idx_community_members_community_role_id ON community_members(community_role_id);

-- Backfill community_role_id from existing role VARCHAR
UPDATE community_members cm
  SET community_role_id = cr.id
  FROM community_roles cr
  WHERE cr.community_id = cm.community_id
    AND cr.name = CASE cm.role
      WHEN 'owner'     THEN 'community-owner'
      WHEN 'admin'     THEN 'community-admin'
      WHEN 'moderator' THEN 'moderator'
      WHEN 'speaker'   THEN 'speaker'
      ELSE 'member'
    END;

-- ============================================================
-- 1g. Channel permission overrides
-- ============================================================

CREATE TABLE IF NOT EXISTS hub_channel_permission_overrides (
  id                SERIAL PRIMARY KEY,
  hub_channel_id    INTEGER NOT NULL REFERENCES hub_channels(id) ON DELETE CASCADE,
  community_role_id INTEGER NOT NULL REFERENCES community_roles(id) ON DELETE CASCADE,
  grant_scopes      JSONB NOT NULL DEFAULT '[]',
  deny_scopes       JSONB NOT NULL DEFAULT '[]',
  scope             VARCHAR(10) NOT NULL DEFAULT 'both'
    CHECK (scope IN ('permanent', 'temporary', 'both')),
  created_at        TIMESTAMPTZ DEFAULT NOW(),
  updated_at        TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(hub_channel_id, community_role_id, scope)
);

CREATE INDEX IF NOT EXISTS idx_hub_channel_perm_overrides_channel_id ON hub_channel_permission_overrides(hub_channel_id);
CREATE INDEX IF NOT EXISTS idx_hub_channel_perm_overrides_role_id ON hub_channel_permission_overrides(community_role_id);

-- ============================================================
-- 1h. Hub channels capability columns
-- ============================================================

ALTER TABLE hub_channels
  ADD COLUMN IF NOT EXISTS has_chat              BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS has_voice             BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS has_video             BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS is_temporary          BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS temp_duration_minutes INTEGER DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS is_broadcast          BOOLEAN NOT NULL DEFAULT FALSE;

UPDATE hub_channels SET has_chat  = TRUE WHERE channel_type = 'chat';
UPDATE hub_channels SET has_voice = TRUE WHERE channel_type = 'voice';
UPDATE hub_channels SET has_chat  = TRUE WHERE channel_type = 'forum';

-- ============================================================
-- 1i. Platform configs tenant_id
-- ============================================================

ALTER TABLE platform_configs ADD COLUMN IF NOT EXISTS tenant_id INTEGER REFERENCES tenants(id);

UPDATE platform_configs
  SET tenant_id = (SELECT id FROM tenants WHERE is_global = TRUE)
  WHERE tenant_id IS NULL;

CREATE INDEX IF NOT EXISTS idx_platform_configs_tenant_id ON platform_configs(tenant_id);

COMMIT;
