-- Migration 003: Add Shoutout Module Tables
-- For tracking shoutout history and custom templates

-- Shoutout history table
CREATE TABLE IF NOT EXISTS shoutout_history (
    id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    target_username VARCHAR(255) NOT NULL,
    target_user_id VARCHAR(255),
    platform VARCHAR(50) NOT NULL DEFAULT 'twitch',
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for shoutout_history
CREATE INDEX IF NOT EXISTS idx_shoutout_history_community
    ON shoutout_history(community_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_shoutout_history_target
    ON shoutout_history(target_username, community_id);

-- Custom shoutout templates table
CREATE TABLE IF NOT EXISTS shoutout_templates (
    id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL DEFAULT 'twitch',
    is_live BOOLEAN NOT NULL DEFAULT true,
    template TEXT NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Only one template per community/platform/is_live combination
    UNIQUE(community_id, platform, is_live)
);

-- Index for template lookups
CREATE INDEX IF NOT EXISTS idx_shoutout_templates_lookup
    ON shoutout_templates(community_id, platform, is_live)
    WHERE is_active = true;

-- Analyze
ANALYZE shoutout_history;
ANALYZE shoutout_templates;
