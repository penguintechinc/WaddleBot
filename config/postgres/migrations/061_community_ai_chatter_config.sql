-- Migration 061: Community AI Chatter Configuration
-- WaddleBot v2.1.x
-- Depends on: 060_analytics_consumer_role.sql
--
-- Adds opt-in AI proactive chat configuration per community and rate limit
-- state table for chatter tracking. Communities can configure rate limits
-- and response probability for AI-initiated chat responses.

BEGIN;

-- 1. Community AI chatter configuration
CREATE TABLE IF NOT EXISTS community_ai_chatter_config (
  id                      SERIAL PRIMARY KEY,
  community_id            INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
  enabled                 BOOLEAN NOT NULL DEFAULT FALSE,
  max_responses_per_window INTEGER NOT NULL DEFAULT 10,
  window_seconds          INTEGER NOT NULL DEFAULT 600,
  max_per_user_per_window INTEGER NOT NULL DEFAULT 2,
  response_probability    NUMERIC(3,2) NOT NULL DEFAULT 0.30,
  min_message_length      INTEGER NOT NULL DEFAULT 10,
  updated_at              TIMESTAMP DEFAULT NOW(),
  CONSTRAINT unique_community_ai_chatter UNIQUE(community_id)
);

-- 2. Check constraints
DO $$ BEGIN
  ALTER TABLE community_ai_chatter_config
    ADD CONSTRAINT chk_chatter_window_seconds
    CHECK (window_seconds BETWEEN 60 AND 3600);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  ALTER TABLE community_ai_chatter_config
    ADD CONSTRAINT chk_chatter_max_responses
    CHECK (max_responses_per_window BETWEEN 1 AND 100);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  ALTER TABLE community_ai_chatter_config
    ADD CONSTRAINT chk_chatter_max_per_user
    CHECK (max_per_user_per_window BETWEEN 1 AND 20);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  ALTER TABLE community_ai_chatter_config
    ADD CONSTRAINT chk_chatter_probability
    CHECK (response_probability BETWEEN 0.05 AND 1.0);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- 3. Index for fast enabled-community lookups
CREATE INDEX IF NOT EXISTS idx_community_ai_chatter_enabled
  ON community_ai_chatter_config(community_id) WHERE enabled = TRUE;

-- 4. Rate limit state table for AI chatter (Redis primary, DB fallback)
CREATE TABLE IF NOT EXISTS ai_chatter_rate_limit_state (
  key        VARCHAR(255) PRIMARY KEY,
  count      INTEGER NOT NULL DEFAULT 0,
  expires_at TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_ai_chatter_rate_limit_expires
  ON ai_chatter_rate_limit_state(expires_at);

COMMIT;
