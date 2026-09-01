-- Migration 042: New Interactive Modules (LFG, Server Status, Clip Manager)
-- Adds tables for three new standalone interactive modules
-- Depends on: communities

BEGIN;

-- ============================================================================
-- LFG (Looking for Group) Posts
-- ============================================================================
CREATE TABLE IF NOT EXISTS lfg_posts (
    id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    user_id VARCHAR(100) NOT NULL,
    platform VARCHAR(50) NOT NULL,
    game VARCHAR(200) NOT NULL,
    activity VARCHAR(200),
    role VARCHAR(100),
    rank_or_level VARCHAR(100),
    player_count_needed INTEGER DEFAULT 1,
    message TEXT,
    platform_message_id VARCHAR(200),
    status VARCHAR(20) NOT NULL DEFAULT 'open',
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Validate LFG post status
ALTER TABLE lfg_posts
    ADD CONSTRAINT chk_lfg_post_status
    CHECK (status IN ('open', 'filled', 'expired', 'cancelled'));

CREATE INDEX IF NOT EXISTS idx_lfg_posts_community
    ON lfg_posts (community_id);

CREATE INDEX IF NOT EXISTS idx_lfg_posts_active
    ON lfg_posts (community_id, status, expires_at)
    WHERE status = 'open';

CREATE INDEX IF NOT EXISTS idx_lfg_posts_user
    ON lfg_posts (community_id, user_id)
    WHERE status = 'open';


-- ============================================================================
-- LFG Joins — players who joined an LFG post
-- ============================================================================
CREATE TABLE IF NOT EXISTS lfg_joins (
    id SERIAL PRIMARY KEY,
    post_id INTEGER NOT NULL REFERENCES lfg_posts(id) ON DELETE CASCADE,
    user_id VARCHAR(100) NOT NULL,
    platform VARCHAR(50) NOT NULL,
    display_name VARCHAR(200),
    joined_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT uq_lfg_join
        UNIQUE (post_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_lfg_joins_post
    ON lfg_joins (post_id);


-- ============================================================================
-- Server Status Configs — community-configured game servers to monitor
-- ============================================================================
CREATE TABLE IF NOT EXISTS server_status_configs (
    id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    game_name VARCHAR(200) NOT NULL,
    status_api_type VARCHAR(20) NOT NULL DEFAULT 'custom_url',
    status_url VARCHAR(1000),
    alert_on_outage BOOLEAN DEFAULT TRUE,
    poll_interval_minutes INTEGER DEFAULT 5,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT uq_server_status_config
        UNIQUE (community_id, game_name)
);

-- Validate status_api_type
ALTER TABLE server_status_configs
    ADD CONSTRAINT chk_status_api_type
    CHECK (status_api_type IN ('steam', 'riot', 'custom_url'));

CREATE INDEX IF NOT EXISTS idx_server_status_configs_community
    ON server_status_configs (community_id)
    WHERE is_active = TRUE;


-- ============================================================================
-- Server Status Events — outage/restored/degraded events
-- ============================================================================
CREATE TABLE IF NOT EXISTS server_status_events (
    id SERIAL PRIMARY KEY,
    config_id INTEGER NOT NULL REFERENCES server_status_configs(id) ON DELETE CASCADE,
    game_name VARCHAR(200) NOT NULL,
    event_type VARCHAR(20) NOT NULL,
    details TEXT,
    alerted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Validate event_type
ALTER TABLE server_status_events
    ADD CONSTRAINT chk_status_event_type
    CHECK (event_type IN ('outage', 'restored', 'degraded'));

CREATE INDEX IF NOT EXISTS idx_server_status_events_config
    ON server_status_events (config_id);

CREATE INDEX IF NOT EXISTS idx_server_status_events_created
    ON server_status_events (created_at);


-- ============================================================================
-- Clip Bookmarks — community-curated clip collection
-- ============================================================================
CREATE TABLE IF NOT EXISTS clip_bookmarks (
    id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    clip_id VARCHAR(200) NOT NULL,  -- Twitch clip ID or external ID
    clip_url VARCHAR(1000) NOT NULL,
    title VARCHAR(500),
    game VARCHAR(200),
    tags TEXT[],
    is_highlight BOOLEAN DEFAULT FALSE,
    view_count INTEGER DEFAULT 0,
    bookmarked_by VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT uq_clip_bookmark
        UNIQUE (community_id, clip_id)
);

CREATE INDEX IF NOT EXISTS idx_clip_bookmarks_community
    ON clip_bookmarks (community_id);

CREATE INDEX IF NOT EXISTS idx_clip_bookmarks_tags
    ON clip_bookmarks USING GIN (tags);

CREATE INDEX IF NOT EXISTS idx_clip_bookmarks_highlights
    ON clip_bookmarks (community_id)
    WHERE is_highlight = TRUE;


-- ============================================================================
-- Clip Highlight Reels — curated playlists of clips
-- ============================================================================
CREATE TABLE IF NOT EXISTS clip_highlight_reels (
    id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    name VARCHAR(300) NOT NULL,
    description TEXT,
    clip_ids INTEGER[],  -- references clip_bookmarks.id
    is_published BOOLEAN DEFAULT FALSE,
    created_by VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_clip_reels_community
    ON clip_highlight_reels (community_id);


-- ============================================================================
-- Updated-at triggers
-- ============================================================================
DO $$
DECLARE
    tbl TEXT;
BEGIN
    FOR tbl IN SELECT unnest(ARRAY[
        'server_status_configs',
        'clip_highlight_reels'
    ])
    LOOP
        EXECUTE format(
            'DROP TRIGGER IF EXISTS trg_%s_updated_at ON %I; '
            'CREATE TRIGGER trg_%s_updated_at '
            'BEFORE UPDATE ON %I '
            'FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();',
            tbl, tbl, tbl, tbl
        );
    END LOOP;
END;
$$;

COMMIT;
