-- Migration 038: Game Lookup Sub-Module
-- Adds tables for game data lookup via SearXNG metasearch + AI synthesis
-- Depends on: communities

BEGIN;

-- ============================================================================
-- Game Lookup Games — Community-configured game registry
-- Each community opts in to specific games for targeted search
-- ============================================================================
CREATE TABLE IF NOT EXISTS game_lookup_games (
    id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    name_normalized VARCHAR(200) NOT NULL,  -- lowercase for matching
    abbreviations TEXT[],                   -- e.g., {'SC', 'Star Citizen'}
    search_keywords TEXT[],                 -- extra SearXNG terms
    wiki_url VARCHAR(500),                  -- primary wiki URL
    preferred_engines TEXT[],               -- SearXNG engines to prioritize
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT uq_game_lookup_community_name
        UNIQUE (community_id, name_normalized)
);

CREATE INDEX IF NOT EXISTS idx_game_lookup_games_community
    ON game_lookup_games (community_id) WHERE is_active = TRUE;

CREATE INDEX IF NOT EXISTS idx_game_lookup_games_name_norm
    ON game_lookup_games (name_normalized);


-- ============================================================================
-- Game Lookup Items — Cached item/entity data from searches
-- Stores structured results from SearXNG for faster repeat lookups
-- ============================================================================
CREATE TABLE IF NOT EXISTS game_lookup_items (
    id SERIAL PRIMARY KEY,
    game_id INTEGER NOT NULL REFERENCES game_lookup_games(id) ON DELETE CASCADE,
    community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    name VARCHAR(300) NOT NULL,
    item_type VARCHAR(50),   -- ship, weapon, npc, location, item, vehicle, character, quest
    description TEXT,
    source_url VARCHAR(1000),
    source_engine VARCHAR(100),
    metadata JSONB DEFAULT '{}',
    hit_count INTEGER DEFAULT 0,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    search_vector tsvector GENERATED ALWAYS AS (
        immutable_to_tsvector('english'::regconfig, coalesce(name, '') || ' ' || coalesce(description, ''))
    ) STORED
);

CREATE INDEX IF NOT EXISTS idx_game_lookup_items_game
    ON game_lookup_items (game_id);

CREATE INDEX IF NOT EXISTS idx_game_lookup_items_community
    ON game_lookup_items (community_id);

CREATE INDEX IF NOT EXISTS idx_game_lookup_items_type
    ON game_lookup_items (game_id, item_type);

CREATE INDEX IF NOT EXISTS idx_game_lookup_items_expires
    ON game_lookup_items (expires_at) WHERE expires_at IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_game_lookup_items_search
    ON game_lookup_items USING GIN (search_vector);


-- ============================================================================
-- Game Lookup Searches — Search analytics and history
-- Tracks usage for rate limiting visibility and cache hit analysis
-- ============================================================================
CREATE TABLE IF NOT EXISTS game_lookup_searches (
    id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    game_id INTEGER REFERENCES game_lookup_games(id) ON DELETE SET NULL,
    user_id VARCHAR(100),
    platform VARCHAR(50),
    query TEXT NOT NULL,
    search_type VARCHAR(20) NOT NULL,  -- 'full' or 'quick'
    result_count INTEGER DEFAULT 0,
    was_cached BOOLEAN DEFAULT FALSE,
    processing_time_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_game_lookup_searches_community
    ON game_lookup_searches (community_id);

CREATE INDEX IF NOT EXISTS idx_game_lookup_searches_game
    ON game_lookup_searches (game_id);

CREATE INDEX IF NOT EXISTS idx_game_lookup_searches_created
    ON game_lookup_searches (created_at);


-- ============================================================================
-- Updated-at trigger (reuse existing function if available)
-- ============================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
DECLARE
    tbl TEXT;
BEGIN
    FOR tbl IN SELECT unnest(ARRAY[
        'game_lookup_games',
        'game_lookup_items'
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


-- ============================================================================
-- Pre-seed popular games as templates (community_id = 1, is_active = FALSE)
-- Communities copy these via the /copy-templates endpoint
-- ============================================================================
INSERT INTO game_lookup_games
    (community_id, name, name_normalized, abbreviations, search_keywords, wiki_url, preferred_engines, is_active)
VALUES
    (1, 'Star Citizen', 'star citizen',
     '{"SC"}', '{"RSI", "Roberts Space Industries"}',
     'https://starcitizen.tools', '{"google", "wikipedia"}', FALSE),

    (1, 'Elite Dangerous', 'elite dangerous',
     '{"ED", "E:D"}', '{"Frontier Developments"}',
     'https://elite-dangerous.fandom.com', '{"google", "wikipedia"}', FALSE),

    (1, 'Fortnite', 'fortnite',
     '{"FN"}', '{"Epic Games"}',
     'https://fortnite.fandom.com', '{"google", "wikipedia"}', FALSE),

    (1, 'Call of Duty', 'call of duty',
     '{"CoD"}', '{"Activision"}',
     'https://callofduty.fandom.com', '{"google", "wikipedia"}', FALSE),

    (1, 'Battlefield', 'battlefield',
     '{"BF"}', '{"DICE", "EA"}',
     'https://battlefield.fandom.com', '{"google", "wikipedia"}', FALSE),

    (1, 'Roblox', 'roblox',
     '{}', '{"Roblox Corporation"}',
     'https://roblox.fandom.com', '{"google", "wikipedia"}', FALSE),

    (1, 'Minecraft', 'minecraft',
     '{"MC"}', '{"Mojang"}',
     'https://minecraft.wiki', '{"google", "wikipedia"}', FALSE),

    (1, 'Destiny 2', 'destiny 2',
     '{"D2"}', '{"Bungie"}',
     'https://www.light.gg', '{"google", "wikipedia"}', FALSE),

    (1, 'Escape from Tarkov', 'escape from tarkov',
     '{"EFT", "Tarkov"}', '{"BSG"}',
     'https://escapefromtarkov.fandom.com', '{"google", "wikipedia"}', FALSE),

    (1, 'Valorant', 'valorant',
     '{"Val"}', '{"Riot Games"}',
     'https://valorant.fandom.com', '{"google", "wikipedia"}', FALSE)
ON CONFLICT (community_id, name_normalized) DO NOTHING;

COMMIT;
