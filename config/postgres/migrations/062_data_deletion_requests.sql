-- Migration 062: GDPR Data Deletion Requests
-- WaddleBot v2.1.x
-- Depends on: 061_community_ai_chatter_config.sql
--
-- Audit trail for GDPR data deletion compliance. Proves deletion was honored
-- while storing no PII. hub_user_id is retained as integer (not FK) because
-- the user row is anonymized in-place, not deleted.

BEGIN;

CREATE TABLE IF NOT EXISTS data_deletion_requests (
  id             SERIAL PRIMARY KEY,
  hub_user_id    INTEGER NOT NULL,
  requested_at   TIMESTAMP NOT NULL DEFAULT NOW(),
  completed_at   TIMESTAMP,
  status         VARCHAR(20) NOT NULL DEFAULT 'pending',
  deletion_scope JSONB,
  error_detail   TEXT
);

-- Status check constraint
DO $$ BEGIN
  ALTER TABLE data_deletion_requests
    ADD CONSTRAINT chk_deletion_status
    CHECK (status IN ('pending', 'completed', 'failed'));
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Index for looking up a user's deletion history
CREATE INDEX IF NOT EXISTS idx_data_deletion_requests_user
  ON data_deletion_requests(hub_user_id);

-- Index for status-based queries (pending requests, support lookups)
CREATE INDEX IF NOT EXISTS idx_data_deletion_requests_status
  ON data_deletion_requests(status) WHERE status != 'completed';

COMMIT;
