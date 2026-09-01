-- Migration 010: Add Emote Cache for Translation Pre-Processing
-- Description: Stores platform emotes for token preservation during translation
-- Author: Waddles Team
-- Date: 2025-12-15

-- =============================================================================
-- EMOTE CACHE TABLE
-- =============================================================================
-- Caches platform-specific emotes (Twitch, BTTV, FFZ, 7TV, Discord, Slack)
-- Used by translation preprocessor to identify tokens that should not be translated

CREATE TABLE IF NOT EXISTS emote_cache (
    id SERIAL PRIMARY KEY,
    platform VARCHAR(20) NOT NULL,              -- 'twitch', 'discord', 'slack', 'kick'
    channel_id VARCHAR(100),                    -- NULL for global emotes
    emote_source VARCHAR(50) NOT NULL,          -- 'global', 'bttv', 'ffz', '7tv', 'native'
    emote_code VARCHAR(100) NOT NULL,           -- The emote text (e.g., 'Kappa', 'LUL')
    emote_id VARCHAR(100),                      -- Platform-specific emote ID
    emote_url TEXT,                             -- URL to emote image (optional)
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,            -- Cache expiration
    UNIQUE(platform, channel_id, emote_source, emote_code)
);

-- Index for fast emote lookups by platform and channel
CREATE INDEX IF NOT EXISTS idx_emote_cache_lookup
ON emote_cache(platform, channel_id, emote_code);

-- Index for cache cleanup (expired entries)
CREATE INDEX IF NOT EXISTS idx_emote_cache_expiry
ON emote_cache(expires_at);

-- Partial index for global emotes (channel_id is NULL)
CREATE INDEX IF NOT EXISTS idx_emote_cache_global
ON emote_cache(platform, emote_code)
WHERE channel_id IS NULL;

-- Index for source-based queries
CREATE INDEX IF NOT EXISTS idx_emote_cache_source
ON emote_cache(platform, emote_source);

COMMENT ON TABLE emote_cache IS
    'Cache for platform-specific emotes used during translation pre-processing';

COMMENT ON COLUMN emote_cache.platform IS
    'Platform name: twitch, discord, slack, kick';

COMMENT ON COLUMN emote_cache.channel_id IS
    'Channel ID for channel-specific emotes, NULL for global emotes';

COMMENT ON COLUMN emote_cache.emote_source IS
    'Source of emote: global (platform native), bttv, ffz, 7tv, or native (Discord/Slack)';

COMMENT ON COLUMN emote_cache.emote_code IS
    'The text code that triggers the emote (e.g., Kappa, PogChamp)';

COMMENT ON COLUMN emote_cache.expires_at IS
    'Cache expiration time - typically 1-2 hours for channel emotes, 24h for global';


-- =============================================================================
-- AI DECISION CACHE TABLE
-- =============================================================================
-- Caches AI decisions about whether uncertain patterns should be translated
-- Reduces redundant AI API calls for repeated patterns

CREATE TABLE IF NOT EXISTS ai_translation_decision_cache (
    id SERIAL PRIMARY KEY,
    pattern_hash CHAR(64) NOT NULL,             -- SHA-256 hash of pattern+context
    pattern TEXT NOT NULL,                      -- The uncertain pattern
    platform VARCHAR(20) NOT NULL,              -- Platform context
    should_translate BOOLEAN NOT NULL,          -- AI decision
    confidence DECIMAL(3,2) NOT NULL,           -- AI confidence score
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    access_count INTEGER DEFAULT 1,
    UNIQUE(pattern_hash, platform)
);

CREATE INDEX IF NOT EXISTS idx_ai_decision_lookup
ON ai_translation_decision_cache(pattern_hash, platform);

CREATE INDEX IF NOT EXISTS idx_ai_decision_expiry
ON ai_translation_decision_cache(expires_at);

COMMENT ON TABLE ai_translation_decision_cache IS
    'Cache for AI decisions about translating uncertain patterns';


-- =============================================================================
-- CLEANUP FUNCTIONS
-- =============================================================================

-- Function to clean up expired emote cache entries
CREATE OR REPLACE FUNCTION cleanup_expired_emotes()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM emote_cache
    WHERE expires_at < NOW();

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cleanup_expired_emotes() IS
    'Removes expired emote cache entries and returns count of deleted rows';


-- Function to clean up expired AI decision cache entries
CREATE OR REPLACE FUNCTION cleanup_expired_ai_decisions()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM ai_translation_decision_cache
    WHERE expires_at < NOW();

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cleanup_expired_ai_decisions() IS
    'Removes expired AI decision cache entries and returns count of deleted rows';


-- Combined cleanup function
CREATE OR REPLACE FUNCTION cleanup_translation_preprocessing_cache()
RETURNS TABLE(emotes_deleted INTEGER, ai_decisions_deleted INTEGER) AS $$
BEGIN
    emotes_deleted := cleanup_expired_emotes();
    ai_decisions_deleted := cleanup_expired_ai_decisions();
    RETURN NEXT;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cleanup_translation_preprocessing_cache() IS
    'Cleans up all translation preprocessing caches (emotes and AI decisions)';


-- =============================================================================
-- HELPER FUNCTIONS
-- =============================================================================

-- Function to check if an emote exists in cache
CREATE OR REPLACE FUNCTION is_cached_emote(
    p_platform VARCHAR(20),
    p_channel_id VARCHAR(100),
    p_emote_code VARCHAR(100)
)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM emote_cache
        WHERE platform = p_platform
          AND (channel_id = p_channel_id OR channel_id IS NULL)
          AND emote_code = p_emote_code
          AND expires_at > NOW()
    );
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION is_cached_emote(VARCHAR, VARCHAR, VARCHAR) IS
    'Check if an emote code exists in cache for a platform/channel';


-- Function to get cached AI decision
CREATE OR REPLACE FUNCTION get_cached_ai_decision(
    p_pattern_hash CHAR(64),
    p_platform VARCHAR(20)
)
RETURNS TABLE(should_translate BOOLEAN, confidence DECIMAL(3,2)) AS $$
BEGIN
    RETURN QUERY
    SELECT adc.should_translate, adc.confidence
    FROM ai_translation_decision_cache adc
    WHERE adc.pattern_hash = p_pattern_hash
      AND adc.platform = p_platform
      AND adc.expires_at > NOW();

    -- Update access count if found
    UPDATE ai_translation_decision_cache
    SET access_count = access_count + 1
    WHERE pattern_hash = p_pattern_hash
      AND platform = p_platform;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_cached_ai_decision(CHAR, VARCHAR) IS
    'Get cached AI translation decision for a pattern hash';
