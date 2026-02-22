-- Add remaining tables referenced by admin controllers but missing from migrations
-- Fixes: server_link_requests, mirror_groups/members, modules, shoutout_config/creators/history
-- Also adds is_active column to community_domains

-- ============================================================================
-- Server Link Requests (for community admin server approval workflow)
-- ============================================================================
CREATE TABLE IF NOT EXISTS server_link_requests (
    id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,
    platform_server_id VARCHAR(255) NOT NULL,
    platform_server_name VARCHAR(255),
    requested_by INTEGER REFERENCES hub_users(id),
    reviewed_by INTEGER REFERENCES hub_users(id),
    status VARCHAR(20) DEFAULT 'pending',
    review_note TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    reviewed_at TIMESTAMPTZ,
    CONSTRAINT valid_slr_status CHECK (status IN ('pending', 'approved', 'rejected'))
);

CREATE INDEX IF NOT EXISTS idx_slr_community_status ON server_link_requests(community_id, status);

-- ============================================================================
-- Mirror Groups (cross-server message mirroring)
-- ============================================================================
CREATE TABLE IF NOT EXISTS mirror_groups (
    id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    description TEXT DEFAULT '',
    is_active BOOLEAN DEFAULT TRUE,
    config JSONB DEFAULT '{}',
    created_by INTEGER REFERENCES hub_users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mirror_groups_community ON mirror_groups(community_id);

CREATE TABLE IF NOT EXISTS mirror_group_members (
    id SERIAL PRIMARY KEY,
    mirror_group_id INTEGER NOT NULL REFERENCES mirror_groups(id) ON DELETE CASCADE,
    community_server_id INTEGER NOT NULL,
    community_server_channel_id INTEGER,
    direction VARCHAR(20) DEFAULT 'both',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mgm_group ON mirror_group_members(mirror_group_id);

-- ============================================================================
-- Modules registry (admin-managed module catalog)
-- ============================================================================
CREATE TABLE IF NOT EXISTS modules (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(255),
    description TEXT,
    category VARCHAR(50),
    version VARCHAR(20) DEFAULT '1.0.0',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- Shoutout Configuration
-- ============================================================================
CREATE TABLE IF NOT EXISTS shoutout_config (
    id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    so_enabled BOOLEAN DEFAULT TRUE,
    so_permission VARCHAR(30) DEFAULT 'mod',
    vso_enabled BOOLEAN DEFAULT TRUE,
    vso_permission VARCHAR(30) DEFAULT 'mod',
    auto_shoutout_mode VARCHAR(30) DEFAULT 'disabled',
    trigger_first_message BOOLEAN DEFAULT FALSE,
    trigger_raid_host BOOLEAN DEFAULT TRUE,
    widget_position VARCHAR(20) DEFAULT 'bottom-right',
    widget_duration_seconds INTEGER DEFAULT 30,
    cooldown_minutes INTEGER DEFAULT 60,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(community_id)
);

CREATE INDEX IF NOT EXISTS idx_shoutout_config_community ON shoutout_config(community_id);

-- ============================================================================
-- Shoutout Creators (auto-shoutout list)
-- ============================================================================
CREATE TABLE IF NOT EXISTS shoutout_creators (
    id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,
    platform_username VARCHAR(255) NOT NULL,
    added_by INTEGER REFERENCES hub_users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(community_id, platform, platform_username)
);

CREATE INDEX IF NOT EXISTS idx_shoutout_creators_community ON shoutout_creators(community_id);

-- ============================================================================
-- Shoutout History (log of shoutouts given)
-- ============================================================================
CREATE TABLE IF NOT EXISTS shoutout_history (
    id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,
    target_username VARCHAR(255) NOT NULL,
    shoutout_type VARCHAR(20) DEFAULT 'text',
    triggered_by_username VARCHAR(255),
    trigger_type VARCHAR(30) DEFAULT 'manual',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_shoutout_history_community ON shoutout_history(community_id);
CREATE INDEX IF NOT EXISTS idx_shoutout_history_created ON shoutout_history(community_id, created_at DESC);
