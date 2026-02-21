-- Migration 041: Calendar Tournament Brackets
-- Adds tournament bracket system with single/double elimination,
-- round robin, and swiss formats
-- Depends on: communities, calendar_events (optional FK)

BEGIN;

-- ============================================================================
-- Calendar Tournaments — top-level tournament configuration
-- ============================================================================
CREATE TABLE IF NOT EXISTS calendar_tournaments (
    id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    event_id INTEGER,  -- optional link to calendar_events
    name VARCHAR(300) NOT NULL,
    description TEXT,
    bracket_type VARCHAR(20) NOT NULL DEFAULT 'single_elim',
    status VARCHAR(20) NOT NULL DEFAULT 'registration',
    max_participants INTEGER DEFAULT 64,
    prize_pool_points INTEGER DEFAULT 0,
    prize_giveaway_id INTEGER,  -- optional link to loyalty_giveaways
    current_round INTEGER DEFAULT 0,
    total_rounds INTEGER DEFAULT 0,
    seeding_method VARCHAR(20) DEFAULT 'random',  -- random, manual, ranked
    check_in_required BOOLEAN DEFAULT FALSE,
    registration_closes_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Validate bracket_type
ALTER TABLE calendar_tournaments
    ADD CONSTRAINT chk_tournament_bracket_type
    CHECK (bracket_type IN ('single_elim', 'double_elim', 'round_robin', 'swiss'));

-- Validate status
ALTER TABLE calendar_tournaments
    ADD CONSTRAINT chk_tournament_status
    CHECK (status IN ('registration', 'seeding', 'active', 'completed', 'cancelled'));

CREATE INDEX IF NOT EXISTS idx_calendar_tournaments_community
    ON calendar_tournaments (community_id);

CREATE INDEX IF NOT EXISTS idx_calendar_tournaments_status
    ON calendar_tournaments (community_id, status)
    WHERE status NOT IN ('completed', 'cancelled');


-- ============================================================================
-- Calendar Tournament Participants — registered players
-- ============================================================================
CREATE TABLE IF NOT EXISTS calendar_tournament_participants (
    id SERIAL PRIMARY KEY,
    tournament_id INTEGER NOT NULL REFERENCES calendar_tournaments(id) ON DELETE CASCADE,
    user_id VARCHAR(100) NOT NULL,
    platform VARCHAR(50) NOT NULL,
    display_name VARCHAR(200),
    seed INTEGER,
    checked_in BOOLEAN DEFAULT FALSE,
    is_eliminated BOOLEAN DEFAULT FALSE,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    draws INTEGER DEFAULT 0,
    registered_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT uq_tournament_participant
        UNIQUE (tournament_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_tournament_participants_tournament
    ON calendar_tournament_participants (tournament_id);

CREATE INDEX IF NOT EXISTS idx_tournament_participants_active
    ON calendar_tournament_participants (tournament_id)
    WHERE is_eliminated = FALSE;


-- ============================================================================
-- Calendar Tournament Matches — individual bracket matches
-- ============================================================================
CREATE TABLE IF NOT EXISTS calendar_tournament_matches (
    id SERIAL PRIMARY KEY,
    tournament_id INTEGER NOT NULL REFERENCES calendar_tournaments(id) ON DELETE CASCADE,
    round_number INTEGER NOT NULL,
    match_number INTEGER NOT NULL,
    bracket_position VARCHAR(10) DEFAULT 'WB',  -- WB (winners) or LB (losers) for double-elim
    participant_a_id INTEGER REFERENCES calendar_tournament_participants(id) ON DELETE SET NULL,
    participant_b_id INTEGER REFERENCES calendar_tournament_participants(id) ON DELETE SET NULL,
    winner_id INTEGER REFERENCES calendar_tournament_participants(id) ON DELETE SET NULL,
    score_a INTEGER DEFAULT 0,
    score_b INTEGER DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    scheduled_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Validate match status
ALTER TABLE calendar_tournament_matches
    ADD CONSTRAINT chk_match_status
    CHECK (status IN ('pending', 'ready', 'active', 'completed', 'bye'));

-- Validate bracket_position
ALTER TABLE calendar_tournament_matches
    ADD CONSTRAINT chk_bracket_position
    CHECK (bracket_position IN ('WB', 'LB'));

CREATE INDEX IF NOT EXISTS idx_tournament_matches_tournament
    ON calendar_tournament_matches (tournament_id);

CREATE INDEX IF NOT EXISTS idx_tournament_matches_round
    ON calendar_tournament_matches (tournament_id, round_number);

CREATE INDEX IF NOT EXISTS idx_tournament_matches_active
    ON calendar_tournament_matches (tournament_id, status)
    WHERE status NOT IN ('completed', 'bye');


-- ============================================================================
-- Updated-at trigger for tournaments
-- ============================================================================
DO $$
BEGIN
    EXECUTE format(
        'DROP TRIGGER IF EXISTS trg_calendar_tournaments_updated_at ON calendar_tournaments; '
        'CREATE TRIGGER trg_calendar_tournaments_updated_at '
        'BEFORE UPDATE ON calendar_tournaments '
        'FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();'
    );
END;
$$;

COMMIT;
