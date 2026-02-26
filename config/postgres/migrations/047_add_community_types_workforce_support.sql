-- Migration 047: Add 'workforce' and 'support' community type enum values
-- These are non-transactional DDL operations; IF NOT EXISTS makes them idempotent.
-- 'workforce' — for teams, departments, and organizational groups
-- 'support'   — for help desk / customer support communities

ALTER TYPE community_type ADD VALUE IF NOT EXISTS 'workforce';
ALTER TYPE community_type ADD VALUE IF NOT EXISTS 'support';

COMMENT ON TYPE community_type IS
  'Community classification type. Values: shared_interest_group, gaming, creator, '
  'corporate, other, workforce (teams/departments), support (help desk communities)';
