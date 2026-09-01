-- Migration 065: Custom sounds and messages for community raffles and giveaways
-- Allows community admins to configure per-event-type audio cues and message templates
-- with template variable substitution ({{winner_name}}, {{prize_name}}, etc.)

CREATE TABLE IF NOT EXISTS community_raffle_sounds (
  id SERIAL PRIMARY KEY,
  community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
  event_type VARCHAR(50) NOT NULL CHECK (event_type IN (
    'raffle_start',
    'raffle_winner',
    'raffle_end',
    'giveaway_start',
    'giveaway_winner',
    'giveaway_end'
  )),
  sound_url TEXT,
  sound_filename VARCHAR(255),
  sound_size_bytes INTEGER,
  sound_format VARCHAR(10) CHECK (sound_format IN ('mp3', 'ogg', 'wav')),
  message_template TEXT,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(community_id, event_type)
);

-- Lookup by community
CREATE INDEX IF NOT EXISTS idx_community_raffle_sounds_community_id
  ON community_raffle_sounds (community_id);

-- Lookup active sounds per community
CREATE INDEX IF NOT EXISTS idx_community_raffle_sounds_community_active
  ON community_raffle_sounds (community_id, is_active);
