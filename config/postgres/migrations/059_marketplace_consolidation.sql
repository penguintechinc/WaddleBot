-- Migration 059: Marketplace Consolidation
-- WaddleBot v2.0.x
-- Depends on: 058_tenants_and_claims.sql
--
-- Unifies hub_modules, marketplace_modules, and approved_vendor_modules into a
-- single catalog view.  Adds REST-pull communication, integration type
-- classification, community premium subscriptions, and tenant scoping.

BEGIN;

-- ============================================================
-- 1. Extend marketplace_modules for REST pull + integration type
-- ============================================================

ALTER TABLE marketplace_modules
  ADD COLUMN IF NOT EXISTS api_base_url VARCHAR(500),
  ADD COLUMN IF NOT EXISTS auth_type VARCHAR(50) DEFAULT 'hmac',
  ADD COLUMN IF NOT EXISTS auth_config JSONB DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS communication_model VARCHAR(50) DEFAULT 'webhook_push',
  ADD COLUMN IF NOT EXISTS integration_type VARCHAR(50) DEFAULT 'command_handler',
  ADD COLUMN IF NOT EXISTS seller_id INTEGER REFERENCES marketplace_sellers(id),
  ADD COLUMN IF NOT EXISTS tenant_id INTEGER REFERENCES tenants(id);

-- Add CHECK constraints separately (IF NOT EXISTS not supported for constraints)
DO $$ BEGIN
  ALTER TABLE marketplace_modules
    ADD CONSTRAINT chk_marketplace_modules_auth_type
    CHECK (auth_type IN ('api_key', 'oauth2_client_credentials', 'hmac'));
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  ALTER TABLE marketplace_modules
    ADD CONSTRAINT chk_marketplace_modules_communication_model
    CHECK (communication_model IN ('webhook_push', 'rest_pull'));
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  ALTER TABLE marketplace_modules
    ADD CONSTRAINT chk_marketplace_modules_integration_type
    CHECK (integration_type IN ('action', 'trigger', 'interaction', 'command_handler'));
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Backfill tenant_id for existing marketplace_modules
UPDATE marketplace_modules
  SET tenant_id = (SELECT id FROM tenants WHERE is_global = TRUE)
  WHERE tenant_id IS NULL;

CREATE INDEX IF NOT EXISTS idx_marketplace_modules_tenant_id
  ON marketplace_modules(tenant_id);
CREATE INDEX IF NOT EXISTS idx_marketplace_modules_seller_id
  ON marketplace_modules(seller_id);
CREATE INDEX IF NOT EXISTS idx_marketplace_modules_comm_model
  ON marketplace_modules(communication_model);
CREATE INDEX IF NOT EXISTS idx_marketplace_modules_integration_type
  ON marketplace_modules(integration_type);

-- ============================================================
-- 2. Add tenant_id to other marketplace tables
-- ============================================================

ALTER TABLE marketplace_subscriptions
  ADD COLUMN IF NOT EXISTS tenant_id INTEGER REFERENCES tenants(id);
UPDATE marketplace_subscriptions
  SET tenant_id = (SELECT id FROM tenants WHERE is_global = TRUE)
  WHERE tenant_id IS NULL;
CREATE INDEX IF NOT EXISTS idx_marketplace_subscriptions_tenant_id
  ON marketplace_subscriptions(tenant_id);

ALTER TABLE marketplace_payments
  ADD COLUMN IF NOT EXISTS tenant_id INTEGER REFERENCES tenants(id);
UPDATE marketplace_payments
  SET tenant_id = (SELECT id FROM tenants WHERE is_global = TRUE)
  WHERE tenant_id IS NULL;
CREATE INDEX IF NOT EXISTS idx_marketplace_payments_tenant_id
  ON marketplace_payments(tenant_id);

ALTER TABLE marketplace_sellers
  ADD COLUMN IF NOT EXISTS tenant_id INTEGER REFERENCES tenants(id);
UPDATE marketplace_sellers
  SET tenant_id = (SELECT id FROM tenants WHERE is_global = TRUE)
  WHERE tenant_id IS NULL;
CREATE INDEX IF NOT EXISTS idx_marketplace_sellers_tenant_id
  ON marketplace_sellers(tenant_id);

-- ============================================================
-- 3. Community Premium Subscriptions table
-- ============================================================

CREATE TABLE IF NOT EXISTS community_premium_subscriptions (
  id SERIAL PRIMARY KEY,
  community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE UNIQUE,
  tenant_id INTEGER REFERENCES tenants(id),
  status VARCHAR(50) DEFAULT 'active',
  stripe_subscription_id VARCHAR(255),
  paypal_subscription_id VARCHAR(255),
  current_seat_count INTEGER DEFAULT 0,
  base_price_cents INTEGER NOT NULL DEFAULT 500,
  overage_price_cents INTEGER NOT NULL DEFAULT 10,
  base_seat_limit INTEGER NOT NULL DEFAULT 50,
  current_period_start TIMESTAMPTZ,
  current_period_end TIMESTAMPTZ,
  cancel_at_period_end BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

DO $$ BEGIN
  ALTER TABLE community_premium_subscriptions
    ADD CONSTRAINT chk_community_premium_status
    CHECK (status IN ('active', 'past_due', 'canceled', 'trialing'));
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

CREATE INDEX IF NOT EXISTS idx_community_premium_subs_tenant_id
  ON community_premium_subscriptions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_community_premium_subs_status
  ON community_premium_subscriptions(status);

-- ============================================================
-- 4. Premium pricing defaults in marketplace_settings
-- ============================================================

INSERT INTO marketplace_settings (setting_key, setting_value) VALUES
  ('community_premium_base_price_cents', '500'),
  ('community_premium_base_seat_limit', '50'),
  ('community_premium_overage_price_cents', '10')
ON CONFLICT (setting_key) DO NOTHING;

-- ============================================================
-- 5. Unified catalog view
-- ============================================================
-- Merges core hub_modules + approved marketplace_modules into a
-- single queryable view for the frontend catalog.

CREATE OR REPLACE VIEW marketplace_catalog AS
  -- Core modules (always free, from hub_modules)
  SELECT
    'core'::text              AS source,
    m.id                      AS source_id,
    m.name,
    COALESCE(m.display_name, m.name) AS display_name,
    m.description,
    m.category,
    m.icon_url,
    m.is_core,
    'free'::text              AS pricing_type,
    0                         AS price_cents,
    'flat'::text              AS pricing_model,
    m.version,
    m.author,
    NULL::text                AS webhook_url,
    NULL::text                AS communication_model,
    NULL::text                AS integration_type,
    COALESCE(AVG(r.rating), 0)        AS avg_rating,
    COUNT(DISTINCT r.id)::int         AS review_count,
    COUNT(DISTINCT inst.id)::int      AS install_count,
    m.created_at,
    m.updated_at,
    NULL::int                 AS tenant_id
  FROM hub_modules m
  LEFT JOIN hub_module_reviews r ON r.module_id = m.id
  LEFT JOIN hub_module_installations inst ON inst.module_id = m.id
  WHERE m.is_published = true
  GROUP BY m.id

  UNION ALL

  -- Marketplace vendor modules (free or paid)
  SELECT
    'marketplace'::text       AS source,
    mm.id                     AS source_id,
    mm.name,
    mm.name                   AS display_name,
    mm.description,
    mm.category,
    mm.icon_url,
    false                     AS is_core,
    mm.pricing_type,
    mm.price_cents,
    mm.pricing_model,
    mm.version,
    COALESCE(ms.display_name, 'Independent') AS author,
    mm.webhook_url,
    mm.communication_model,
    mm.integration_type,
    CASE WHEN mm.rating_count > 0
      THEN mm.rating_sum::numeric / mm.rating_count
      ELSE 0 END             AS avg_rating,
    mm.rating_count           AS review_count,
    mm.install_count,
    mm.created_at,
    mm.updated_at,
    mm.tenant_id
  FROM marketplace_modules mm
  LEFT JOIN marketplace_sellers ms ON ms.id = mm.seller_id
  WHERE mm.status = 'approved'
    AND mm.deleted_at IS NULL;

COMMENT ON VIEW marketplace_catalog IS
  'Unified read-only catalog merging core hub_modules and approved marketplace vendor modules';

-- ============================================================
-- 6. Vendor role requests tenant_id (from hub vendor_submissions)
-- ============================================================

ALTER TABLE vendor_submissions
  ADD COLUMN IF NOT EXISTS tenant_id INTEGER REFERENCES tenants(id);
UPDATE vendor_submissions
  SET tenant_id = (SELECT id FROM tenants WHERE is_global = TRUE)
  WHERE tenant_id IS NULL;
CREATE INDEX IF NOT EXISTS idx_vendor_submissions_tenant_id
  ON vendor_submissions(tenant_id);

COMMIT;
