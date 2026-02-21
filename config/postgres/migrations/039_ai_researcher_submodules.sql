-- Migration 039: AI Researcher Sub-Module Search Logs
-- Adds search-log tables for 6 AI researcher sub-modules
-- All follow the same pattern as game_lookup_searches (migration 038)
-- Depends on: communities

BEGIN;

-- ============================================================================
-- Patch Notes Searches — tracks !or/patch and !or/changelog usage
-- ============================================================================
CREATE TABLE IF NOT EXISTS patch_notes_searches (
    id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    user_id VARCHAR(100),
    platform VARCHAR(50),
    query TEXT NOT NULL,
    game_name VARCHAR(200),
    result_count INTEGER DEFAULT 0,
    was_cached BOOLEAN DEFAULT FALSE,
    processing_time_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_patch_notes_searches_community
    ON patch_notes_searches (community_id);

CREATE INDEX IF NOT EXISTS idx_patch_notes_searches_created
    ON patch_notes_searches (created_at);


-- ============================================================================
-- Build Advisor Searches — tracks !or/build and !or/meta usage
-- ============================================================================
CREATE TABLE IF NOT EXISTS build_advisor_searches (
    id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    user_id VARCHAR(100),
    platform VARCHAR(50),
    query TEXT NOT NULL,
    game_name VARCHAR(200),
    class_name VARCHAR(100),
    search_type VARCHAR(20) NOT NULL DEFAULT 'build',  -- 'build' or 'meta'
    result_count INTEGER DEFAULT 0,
    was_cached BOOLEAN DEFAULT FALSE,
    processing_time_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_build_advisor_searches_community
    ON build_advisor_searches (community_id);

CREATE INDEX IF NOT EXISTS idx_build_advisor_searches_created
    ON build_advisor_searches (created_at);


-- ============================================================================
-- Tech Troubleshooter Searches — tracks !or/fix and !or/troubleshoot usage
-- ============================================================================
CREATE TABLE IF NOT EXISTS tech_troubleshooter_searches (
    id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    user_id VARCHAR(100),
    platform VARCHAR(50),
    query TEXT NOT NULL,
    issue_text TEXT,
    safety_flagged BOOLEAN DEFAULT FALSE,
    result_count INTEGER DEFAULT 0,
    was_cached BOOLEAN DEFAULT FALSE,
    processing_time_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tech_troubleshooter_searches_community
    ON tech_troubleshooter_searches (community_id);

CREATE INDEX IF NOT EXISTS idx_tech_troubleshooter_searches_created
    ON tech_troubleshooter_searches (created_at);


-- ============================================================================
-- Price Tracker Searches — tracks !or/price and !game deals usage
-- ============================================================================
CREATE TABLE IF NOT EXISTS price_tracker_searches (
    id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    user_id VARCHAR(100),
    platform VARCHAR(50),
    query TEXT NOT NULL,
    game_name VARCHAR(200),
    result_count INTEGER DEFAULT 0,
    was_cached BOOLEAN DEFAULT FALSE,
    processing_time_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_price_tracker_searches_community
    ON price_tracker_searches (community_id);

CREATE INDEX IF NOT EXISTS idx_price_tracker_searches_created
    ON price_tracker_searches (created_at);


-- ============================================================================
-- Clip Researcher Searches — tracks !or/clips and !or/highlight usage
-- ============================================================================
CREATE TABLE IF NOT EXISTS clip_researcher_searches (
    id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    user_id VARCHAR(100),
    platform VARCHAR(50),
    query TEXT NOT NULL,
    game_name VARCHAR(200),
    topic VARCHAR(200),
    player_name VARCHAR(200),
    search_type VARCHAR(20) NOT NULL DEFAULT 'clips',  -- 'clips' or 'highlight'
    result_count INTEGER DEFAULT 0,
    was_cached BOOLEAN DEFAULT FALSE,
    processing_time_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_clip_researcher_searches_community
    ON clip_researcher_searches (community_id);

CREATE INDEX IF NOT EXISTS idx_clip_researcher_searches_created
    ON clip_researcher_searches (created_at);


-- ============================================================================
-- Event Lookup Searches — tracks !or/events and !or/tournament usage
-- ============================================================================
CREATE TABLE IF NOT EXISTS event_lookup_searches (
    id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    user_id VARCHAR(100),
    platform VARCHAR(50),
    query TEXT NOT NULL,
    game_name VARCHAR(200),
    tournament_name VARCHAR(300),
    search_type VARCHAR(20) NOT NULL DEFAULT 'events',  -- 'events' or 'tournament'
    result_count INTEGER DEFAULT 0,
    was_cached BOOLEAN DEFAULT FALSE,
    processing_time_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_event_lookup_searches_community
    ON event_lookup_searches (community_id);

CREATE INDEX IF NOT EXISTS idx_event_lookup_searches_created
    ON event_lookup_searches (created_at);

COMMIT;
