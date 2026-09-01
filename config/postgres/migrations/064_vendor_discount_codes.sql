-- Migration 064: Vendor discount codes and redemptions for marketplace
-- Implements vendor discount code management with support for percentage, fixed amount,
-- and free tier discounts. Tracks code usage and redemption history.

CREATE TABLE IF NOT EXISTS vendor_discount_codes (
  id SERIAL PRIMARY KEY,
  code VARCHAR(50) NOT NULL,
  vendor_id INTEGER NOT NULL REFERENCES hub_users(id),
  module_id INTEGER REFERENCES approved_vendor_modules(id),
  discount_type VARCHAR(20) NOT NULL CHECK (discount_type IN ('percentage', 'fixed_amount', 'free')),
  discount_value DECIMAL(10,2) DEFAULT 0,
  max_uses INTEGER,
  current_uses INTEGER NOT NULL DEFAULT 0,
  usage_window_days INTEGER,
  application_months INTEGER,
  valid_from TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  valid_until TIMESTAMPTZ,
  is_active BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Case-insensitive uniqueness constraint per vendor
CREATE UNIQUE INDEX IF NOT EXISTS idx_vendor_discount_codes_code_vendor
  ON vendor_discount_codes (UPPER(code), vendor_id);

-- Lookup by vendor
CREATE INDEX IF NOT EXISTS idx_vendor_discount_codes_vendor_id
  ON vendor_discount_codes (vendor_id);

-- Lookup by module
CREATE INDEX IF NOT EXISTS idx_vendor_discount_codes_module_id
  ON vendor_discount_codes (module_id);

-- Filter active codes
CREATE INDEX IF NOT EXISTS idx_vendor_discount_codes_is_active
  ON vendor_discount_codes (is_active);

CREATE TABLE IF NOT EXISTS discount_code_redemptions (
  id SERIAL PRIMARY KEY,
  discount_code_id INTEGER NOT NULL REFERENCES vendor_discount_codes(id),
  community_id INTEGER NOT NULL REFERENCES communities(id),
  subscription_id INTEGER REFERENCES community_premium_subscriptions(id),
  original_price_cents INTEGER NOT NULL,
  discounted_price_cents INTEGER NOT NULL,
  discount_amount_cents INTEGER NOT NULL,
  redeemed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expires_at TIMESTAMPTZ
);

-- Lookup by discount code
CREATE INDEX IF NOT EXISTS idx_discount_code_redemptions_code_id
  ON discount_code_redemptions (discount_code_id);

-- Lookup by community
CREATE INDEX IF NOT EXISTS idx_discount_code_redemptions_community_id
  ON discount_code_redemptions (community_id);

-- One redemption per community per code
CREATE UNIQUE INDEX IF NOT EXISTS idx_discount_code_redemptions_code_community
  ON discount_code_redemptions (discount_code_id, community_id);
