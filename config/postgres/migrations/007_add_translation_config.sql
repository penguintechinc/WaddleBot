-- Migration 007: Add Translation and Closed Captioning Support
-- Description: Adds database infrastructure for translation caching and closed captions
-- Author: Waddles Team
-- Date: 2025-12-12

-- Add GIN index for translation config queries on communities table
-- This allows fast queries on the translation config JSONB field
CREATE INDEX IF NOT EXISTS idx_communities_config_translation
ON communities USING gin ((config->'translation'));

COMMENT ON INDEX idx_communities_config_translation IS
  'GIN index for fast translation configuration queries on communities';

-- Translation cache table to avoid re-translating common phrases
-- Uses SHA-256 hash of source text to handle any text length efficiently
CREATE TABLE IF NOT EXISTS translation_cache (
    id SERIAL PRIMARY KEY,
    source_text_hash CHAR(64) NOT NULL,  -- SHA-256 hash of source text
    source_lang VARCHAR(10) NOT NULL,     -- ISO 639-1 language code (e.g., 'en', 'es', 'fr')
    target_lang VARCHAR(10) NOT NULL,     -- ISO 639-1 language code
    translated_text TEXT NOT NULL,        -- The translated text
    provider VARCHAR(50) NOT NULL,        -- Provider used: 'googletrans', 'google_api', 'waddleai'
    confidence_score DECIMAL(3,2),        -- Language detection confidence (0.00-1.00)
    created_at TIMESTAMPTZ DEFAULT NOW(), -- When translation was first cached
    access_count INTEGER DEFAULT 1,       -- How many times this translation has been accessed
    last_accessed TIMESTAMPTZ DEFAULT NOW(), -- Last time this translation was used
    UNIQUE(source_text_hash, source_lang, target_lang)
);

-- Index for fast cache lookups by hash and languages
CREATE INDEX IF NOT EXISTS idx_translation_cache_lookup
ON translation_cache(source_text_hash, source_lang, target_lang);

-- Index for cleanup operations - finds low-use old translations
CREATE INDEX IF NOT EXISTS idx_translation_cache_cleanup
ON translation_cache(last_accessed)
WHERE access_count < 5;

COMMENT ON TABLE translation_cache IS
  'Cache for translated messages to reduce API calls and improve performance. Uses SHA-256 hash to handle any text length.';

COMMENT ON COLUMN translation_cache.source_text_hash IS
  'SHA-256 hash of the original source text (allows efficient caching of any length text)';

COMMENT ON COLUMN translation_cache.provider IS
  'Translation provider used: googletrans (free), google_api (Google Cloud), waddleai (AI fallback)';

COMMENT ON COLUMN translation_cache.access_count IS
  'Number of times this cached translation has been accessed (used for cache eviction)';

-- Closed caption events table for browser source overlay
-- Stores recent caption history (auto-purged after 7 days)
CREATE TABLE IF NOT EXISTS caption_events (
    id SERIAL PRIMARY KEY,
    community_id INTEGER REFERENCES communities(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,       -- Platform where message originated (twitch, discord, slack, etc.)
    username VARCHAR(255) NOT NULL,      -- Username of message author
    original_message TEXT NOT NULL,      -- Original message before translation
    translated_message TEXT,             -- Translated message (NULL if no translation performed)
    detected_language VARCHAR(10),       -- ISO 639-1 code of detected language
    target_language VARCHAR(10),         -- ISO 639-1 code of target language
    confidence_score DECIMAL(3,2),       -- Language detection confidence (0.00-1.00)
    created_at TIMESTAMPTZ DEFAULT NOW() -- When caption event occurred
);

-- Index for fast retrieval of recent captions per community
-- Only indexes captions from last 7 days (partial index for efficiency)
CREATE INDEX IF NOT EXISTS idx_caption_events_recent
ON caption_events(community_id, created_at DESC)
WHERE created_at > NOW() - INTERVAL '7 days';

-- Index for community-based queries
CREATE INDEX IF NOT EXISTS idx_caption_events_community
ON caption_events(community_id);

COMMENT ON TABLE caption_events IS
  'Recent caption events for overlay display. Auto-purged after 7 days via partial index.';

COMMENT ON COLUMN caption_events.original_message IS
  'Original message text before any translation';

COMMENT ON COLUMN caption_events.translated_message IS
  'Translated message text (NULL if translation was skipped or disabled)';

-- Function to clean up old caption events (keep only last 7 days)
CREATE OR REPLACE FUNCTION cleanup_old_caption_events()
RETURNS void AS $$
BEGIN
    DELETE FROM caption_events
    WHERE created_at < NOW() - INTERVAL '7 days';
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cleanup_old_caption_events() IS
  'Removes caption events older than 7 days to prevent table bloat';

-- Function to clean up low-use translation cache entries (access_count < 5 and > 30 days old)
CREATE OR REPLACE FUNCTION cleanup_translation_cache()
RETURNS void AS $$
BEGIN
    DELETE FROM translation_cache
    WHERE last_accessed < NOW() - INTERVAL '30 days'
    AND access_count < 5;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cleanup_translation_cache() IS
  'Removes rarely-used old translations (< 5 accesses and > 30 days old) to prevent cache bloat';

-- Example community translation config structure (stored in communities.config->translation):
-- {
--   "translation": {
--     "enabled": false,
--     "default_language": "en",
--     "confidence_threshold": 0.7,
--     "min_words": 5,
--     "google_api_key_encrypted": null,
--     "skip_bot_messages": true,
--     "closed_captions": {
--       "enabled": false,
--       "display_duration_ms": 5000,
--       "max_captions_displayed": 3,
--       "show_original": false
--     }
--   }
-- }

-- Grant permissions (adjust based on your setup)
-- GRANT SELECT, INSERT, UPDATE ON translation_cache TO waddlebot_app;
-- GRANT SELECT, INSERT ON caption_events TO waddlebot_app;
