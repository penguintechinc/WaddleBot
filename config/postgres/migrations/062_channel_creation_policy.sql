-- !! MIGRATED TO ALEMBIC — revision 0002_channel_creation !!
-- This file is kept for reference only. The canonical migration is:
--   alembic/versions/0002_channel_creation_policy.py
-- ============================================================
-- 062: Add communicator role + channel_creation_policy config
-- ============================================================
-- Adds a "communicator" system role (priority 15) between member (10)
-- and speaker (20) with the channels:create scope.
-- Also documents the communities.config JSONB key
-- "channel_creation_policy" (admin_only | communicator | all_members).
-- ============================================================

-- Re-create the seed function with the new communicator role
CREATE OR REPLACE FUNCTION seed_community_system_roles(p_community_id INTEGER)
RETURNS VOID AS $$
BEGIN
  -- member (priority 10)
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

  -- communicator (priority 15) — member scopes + channels:create
  INSERT INTO community_roles (community_id, name, display_name, is_system, priority, base_claims)
    VALUES (
      p_community_id,
      'communicator',
      'Communicator',
      TRUE,
      15,
      '{"scopes":["community:read","channels:read","channels:send_chat","channels:speak","channels:share_video","channels:screenshare","channels:create"]}'
    )
    ON CONFLICT (community_id, name) DO NOTHING;

  -- speaker (priority 20)
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

  -- moderator (priority 30)
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

  -- community-admin (priority 40)
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

  -- community-owner (priority 50)
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

-- Backfill: add communicator role to all existing communities
SELECT seed_community_system_roles(id) FROM communities;
