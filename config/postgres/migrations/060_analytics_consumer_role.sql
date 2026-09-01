-- Migration 060: Analytics Consumer Role
-- WaddleBot v2.1.x
-- Depends on: 059_marketplace_consolidation.sql
--
-- Adds is_analytics_consumer flag to hub_users for GDPR-safe aggregate-only
-- platform analytics access, plus performance indexes for analytics queries.

BEGIN;

-- 1. Add analytics consumer role flag to hub_users
ALTER TABLE hub_users
  ADD COLUMN IF NOT EXISTS is_analytics_consumer BOOLEAN NOT NULL DEFAULT FALSE;

-- 2. Partial index on hub_users for analytics consumer lookups
CREATE INDEX IF NOT EXISTS idx_hub_users_analytics_consumer
  ON hub_users(is_analytics_consumer) WHERE is_analytics_consumer = TRUE;

-- 3. Index on activity_message_events for user-scoped analytics queries
CREATE INDEX IF NOT EXISTS idx_activity_message_events_hub_user_id
  ON activity_message_events(hub_user_id) WHERE hub_user_id IS NOT NULL;

-- 4. Index on activity_watch_sessions for user-scoped analytics queries
CREATE INDEX IF NOT EXISTS idx_activity_watch_sessions_hub_user_id
  ON activity_watch_sessions(hub_user_id) WHERE hub_user_id IS NOT NULL;

COMMIT;
