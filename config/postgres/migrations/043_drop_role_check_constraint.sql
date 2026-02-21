-- Migration 043: Drop rigid role CHECK constraint
-- Allow custom community roles (e.g., community-owner, community-admin, or any name)
-- Role validation is handled at the application level, not the database level.

BEGIN;

ALTER TABLE community_members
DROP CONSTRAINT IF EXISTS community_members_role_check;

COMMIT;
