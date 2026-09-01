-- Migration 068: First-message welcome guard
-- Backs social.welcome (action/interactive/welcome_interaction_module). Records
-- that a user has already been welcomed in a community so the welcome fires
-- at most once, ever, even under concurrent duplicate first-messages. The
-- UNIQUE constraint + INSERT ... ON CONFLICT DO NOTHING at the call site is
-- what makes the guard race-safe -- the database, not application logic,
-- arbitrates the race.

CREATE TABLE IF NOT EXISTS community_welcomed_users (
    id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,
    platform_user_id VARCHAR(255) NOT NULL,
    welcomed_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enforces "welcomed at most once per user per community" at the DB layer;
-- INSERT ... ON CONFLICT (community_id, platform, platform_user_id) DO NOTHING
-- relies on this index to make the guard atomic under concurrent writers.
CREATE UNIQUE INDEX IF NOT EXISTS idx_community_welcomed_users_unique
    ON community_welcomed_users (community_id, platform, platform_user_id);

-- Lookup/audit index for "who has been welcomed in this community"
CREATE INDEX IF NOT EXISTS idx_community_welcomed_users_community
    ON community_welcomed_users (community_id, welcomed_at);
