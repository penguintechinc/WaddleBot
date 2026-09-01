-- Migration 054: User platform context switching
--
-- Allows individual users to override the default community for a channel/server.
-- Context resolution order:
--   1. Per-user override (this table, Redis-cached with 24h TTL)
--   2. Channel/server default (community_servers.is_primary, Redis-cached)
--   3. None → "no community configured" error
--
-- The community must have an approved link to the platform entity (community_servers)
-- before a user may switch to it.

CREATE TABLE IF NOT EXISTS user_platform_context (
    id SERIAL PRIMARY KEY,
    platform VARCHAR(50) NOT NULL,
    platform_user_id VARCHAR(255) NOT NULL,
    platform_entity_id VARCHAR(255) NOT NULL,  -- channel / server / workspace ID
    community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(platform, platform_user_id, platform_entity_id)
);

CREATE INDEX IF NOT EXISTS idx_upc_lookup
    ON user_platform_context(platform, platform_user_id, platform_entity_id);

COMMENT ON TABLE user_platform_context IS
    'Per-user community context override. Only valid for communities with an approved community_servers link to the platform entity.';
COMMENT ON COLUMN user_platform_context.platform_entity_id IS
    'The channel/server/workspace where the user is chatting (matches community_servers.platform_server_id)';
