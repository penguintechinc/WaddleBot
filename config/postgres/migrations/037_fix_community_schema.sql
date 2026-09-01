-- Migration 037: Fix community schema for hub user support
-- Adds missing columns that controller code expects but initial schema omits.
-- This migration is safe to run multiple times (all ADD COLUMN use IF NOT EXISTS).

-- Create community_type enum if not exists (idempotent duplicate of migration 008)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'community_type') THEN
        CREATE TYPE community_type AS ENUM (
            'shared_interest_group',
            'gaming',
            'creator',
            'corporate',
            'other'
        );
    END IF;
END $$;

-- communities: add community_type if missing
ALTER TABLE communities
  ADD COLUMN IF NOT EXISTS community_type community_type NOT NULL DEFAULT 'creator';

-- communities: add join_mode used by joinCommunity endpoint
ALTER TABLE communities
  ADD COLUMN IF NOT EXISTS join_mode VARCHAR(50) DEFAULT 'open';

-- community_members: make platform nullable so hub users (no platform) can be inserted
ALTER TABLE community_members
  ALTER COLUMN platform DROP NOT NULL;

-- community_members: add bio for updateProfile endpoint
ALTER TABLE community_members
  ADD COLUMN IF NOT EXISTS bio TEXT;

-- community_members: add social_links for updateProfile endpoint
ALTER TABLE community_members
  ADD COLUMN IF NOT EXISTS social_links JSONB DEFAULT '{}';

-- community_members: add left_at for leaveCommunity endpoint
ALTER TABLE community_members
  ADD COLUMN IF NOT EXISTS left_at TIMESTAMP;

-- Unique index so a hub user can only be a member once per community
CREATE UNIQUE INDEX IF NOT EXISTS idx_community_members_hub_user
  ON community_members (community_id, user_id)
  WHERE user_id IS NOT NULL;

-- Index for community type filtering
CREATE INDEX IF NOT EXISTS idx_communities_type ON communities(community_type);
