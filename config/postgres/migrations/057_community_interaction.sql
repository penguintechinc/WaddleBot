-- Migration 057: Community Interaction
-- Creates hub channels, forum system, and wires into mirror groups
-- for unified chat/forum/voice bridging across platforms.

BEGIN;

-- ============================================================
-- 1a. community_server_channels (referenced by 046 but never created)
-- ============================================================
CREATE TABLE IF NOT EXISTS community_server_channels (
    id SERIAL PRIMARY KEY,
    community_server_id INTEGER NOT NULL REFERENCES community_servers(id) ON DELETE CASCADE,
    platform_channel_id VARCHAR(255),
    platform_channel_name VARCHAR(255),
    channel_type VARCHAR(30) DEFAULT 'chat'
        CHECK (channel_type IN ('chat', 'forum', 'voice')),
    config JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(community_server_id, platform_channel_id)
);

CREATE INDEX IF NOT EXISTS idx_csc_community_server
    ON community_server_channels(community_server_id);
CREATE INDEX IF NOT EXISTS idx_csc_platform_channel
    ON community_server_channels(platform_channel_id);

-- ============================================================
-- 1b. hub_channels — admin-created channels for a community
-- ============================================================
CREATE TABLE IF NOT EXISTS hub_channels (
    id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    description TEXT DEFAULT '',
    channel_type VARCHAR(30) DEFAULT 'chat'
        CHECK (channel_type IN ('chat', 'forum', 'voice')),
    sort_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    allow_ad_hoc_voice BOOLEAN DEFAULT FALSE,
    community_server_channel_id INTEGER UNIQUE REFERENCES community_server_channels(id),
    created_by INTEGER REFERENCES hub_users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(community_id, name)
);

CREATE INDEX IF NOT EXISTS idx_hub_channels_community_sort
    ON hub_channels(community_id, sort_order);

-- ============================================================
-- 1c. Forum tables
-- ============================================================
CREATE TABLE IF NOT EXISTS hub_forum_posts (
    id SERIAL PRIMARY KEY,
    hub_channel_id INTEGER NOT NULL REFERENCES hub_channels(id) ON DELETE CASCADE,
    community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    title VARCHAR(300) NOT NULL,
    body TEXT,
    tags JSONB DEFAULT '[]',
    author_hub_user_id INTEGER REFERENCES hub_users(id),
    author_platform VARCHAR(50),
    author_username VARCHAR(255),
    author_avatar_url TEXT,
    is_pinned BOOLEAN DEFAULT FALSE,
    is_locked BOOLEAN DEFAULT FALSE,
    reply_count INTEGER DEFAULT 0,
    last_reply_at TIMESTAMPTZ,
    platform_thread_id VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_hub_forum_posts_channel
    ON hub_forum_posts(hub_channel_id, created_at DESC);

CREATE TABLE IF NOT EXISTS hub_forum_replies (
    id SERIAL PRIMARY KEY,
    post_id INTEGER NOT NULL REFERENCES hub_forum_posts(id) ON DELETE CASCADE,
    author_hub_user_id INTEGER REFERENCES hub_users(id),
    author_platform VARCHAR(50),
    author_username VARCHAR(255),
    author_avatar_url TEXT,
    content TEXT NOT NULL,
    platform_message_id VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_hub_forum_replies_post
    ON hub_forum_replies(post_id, created_at);

-- ============================================================
-- 1d. Extend existing tables
-- ============================================================

-- Link chat messages to hub channels
ALTER TABLE hub_chat_messages
    ADD COLUMN IF NOT EXISTS hub_channel_id INTEGER REFERENCES hub_channels(id);

-- Add channel_type to mirror_groups
ALTER TABLE mirror_groups
    ADD COLUMN IF NOT EXISTS channel_type VARCHAR(30) DEFAULT 'chat'
        CHECK (channel_type IN ('chat', 'forum'));

-- Add FK constraint on mirror_group_members -> community_server_channels
-- (column exists from migration 046 but may lack FK)
DO $$ BEGIN
    ALTER TABLE mirror_group_members
        ADD CONSTRAINT fk_mgm_csc FOREIGN KEY (community_server_channel_id)
        REFERENCES community_server_channels(id);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

COMMIT;
