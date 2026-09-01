-- Migration 025: Add Translation Settings Table
-- Provides community-level configuration for real-time translation and closed captions

BEGIN;

-- Create translation settings table
CREATE TABLE IF NOT EXISTS community_translation_settings (
  id SERIAL PRIMARY KEY,
  community_id INTEGER NOT NULL UNIQUE REFERENCES communities(id) ON DELETE CASCADE,

  -- Translation toggle and language selection
  enabled BOOLEAN NOT NULL DEFAULT FALSE,
  target_language VARCHAR(5) NOT NULL DEFAULT 'en',

  -- Language detection configuration
  confidence_threshold DECIMAL(3,2) NOT NULL DEFAULT 0.7,
  min_words INTEGER NOT NULL DEFAULT 5,
  detection_method VARCHAR(50) NOT NULL DEFAULT 'ensemble' CHECK (detection_method IN ('ensemble', 'fasttext_only', 'provider')),

  -- API configuration
  google_api_key TEXT, -- Encrypted via backend

  -- Token preservation settings (JSON)
  preprocessing JSONB NOT NULL DEFAULT '{
    "enabled": true,
    "preserve_mentions": true,
    "preserve_commands": true,
    "preserve_emails": true,
    "preserve_urls": true,
    "preserve_emotes": true,
    "emote_sources": ["global", "bttv", "ffz", "7tv"]
  }',

  -- Closed captions configuration (JSON)
  captions JSONB NOT NULL DEFAULT '{
    "enabled": false,
    "display_duration": 5000,
    "max_captions": 3,
    "show_original": false
  }',

  -- AI-powered decision making (JSON)
  ai_decision JSONB NOT NULL DEFAULT '{
    "mode": "never",
    "confidence_threshold": 0.7
  }',

  -- Timestamps
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_community_translation_enabled
    ON community_translation_settings(community_id, enabled);
CREATE INDEX IF NOT EXISTS idx_community_translation_method
    ON community_translation_settings(community_id, detection_method);

-- Create updated_at trigger
CREATE OR REPLACE FUNCTION update_translation_settings_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_translation_settings_timestamp
BEFORE UPDATE ON community_translation_settings
FOR EACH ROW
EXECUTE FUNCTION update_translation_settings_timestamp();

-- Add comment documenting the detection methods
COMMENT ON COLUMN community_translation_settings.detection_method IS
'Language detection method:
- ensemble: Uses fastText, Lingua, and langdetect with consensus voting (recommended, most accurate)
- fasttext_only: Uses fastText only (fastest, good for long messages >30 chars)
- provider: Falls back to Google Cloud or googletrans API';

COMMENT ON COLUMN community_translation_settings.preprocessing IS
'Token preservation configuration:
- preserve_mentions, preserve_commands, preserve_emails, preserve_urls: Exact patterns
- preserve_emotes: Detect platform emotes from Twitch, Discord, Slack
- emote_sources: Which emote providers to check (global, bttv, ffz, 7tv)';

COMMENT ON COLUMN community_translation_settings.captions IS
'Closed captions overlay configuration:
- enabled: Turn captions on/off
- display_duration: How long (ms) each caption shows
- max_captions: Max number of caption lines on screen
- show_original: Display original text alongside translation';

COMMENT ON COLUMN community_translation_settings.ai_decision IS
'AI-powered uncertain pattern detection:
- mode: never (cached only), uncertain_only (AI for unknowns), always (AI checks all)
- confidence_threshold: Minimum confidence (0.5-0.95) required to trust AI decision';

COMMIT;
