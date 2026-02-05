-- Migration 027: Add Streamer Role to Community Members
-- Description: Adds 'streamer' as a valid role option for community members
-- Author: Waddles Engineering
-- Date: 2026-01-21

BEGIN;

-- Drop the existing role constraint if it exists
DO $$
BEGIN
    ALTER TABLE community_members
    DROP CONSTRAINT IF EXISTS community_members_role_check;
EXCEPTION WHEN OTHERS THEN
    NULL;
END
$$;

-- Add the new constraint with streamer role included
ALTER TABLE community_members
ADD CONSTRAINT community_members_role_check
CHECK (role IN ('owner', 'admin', 'moderator', 'member', 'streamer'));

COMMENT ON CONSTRAINT community_members_role_check ON community_members IS
'Valid roles for community members: owner, admin, moderator, member, streamer';

COMMIT;
