-- Migration 004: Add Memories Module Tables
-- For tracking quotes, bookmarks, and reminders

-- Quotes table
CREATE TABLE IF NOT EXISTS memories_quotes (
    id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    quote_text TEXT NOT NULL,
    author_username VARCHAR(255),
    author_user_id INTEGER,
    category VARCHAR(100),
    created_by_username VARCHAR(255) NOT NULL,
    created_by_user_id INTEGER,
    votes INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Full-text search index
    search_vector tsvector GENERATED ALWAYS AS (
        immutable_to_tsvector('english'::regconfig, coalesce(quote_text, '') || ' ' || coalesce(author_username, '') || ' ' || coalesce(category, ''))
    ) STORED
);

-- Indexes for quotes
CREATE INDEX idx_memories_quotes_community ON memories_quotes(community_id, created_at DESC);
CREATE INDEX idx_memories_quotes_author ON memories_quotes(author_username, community_id);
CREATE INDEX idx_memories_quotes_category ON memories_quotes(category, community_id) WHERE category IS NOT NULL;
CREATE INDEX idx_memories_quotes_votes ON memories_quotes(community_id, votes DESC);
CREATE INDEX idx_memories_quotes_search ON memories_quotes USING GIN(search_vector);

-- Bookmarks table
CREATE TABLE IF NOT EXISTS memories_bookmarks (
    id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    title VARCHAR(500),
    description TEXT,
    tags TEXT[],
    created_by_username VARCHAR(255) NOT NULL,
    created_by_user_id INTEGER,
    visits INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Full-text search index
    search_vector tsvector GENERATED ALWAYS AS (
        immutable_to_tsvector('english'::regconfig, coalesce(title, '') || ' ' || coalesce(description, '') || ' ' || coalesce(immutable_array_to_string(tags, ' '::text), ''))
    ) STORED
);

-- Indexes for bookmarks
CREATE INDEX idx_memories_bookmarks_community ON memories_bookmarks(community_id, created_at DESC);
CREATE INDEX idx_memories_bookmarks_creator ON memories_bookmarks(created_by_username, community_id);
CREATE INDEX idx_memories_bookmarks_tags ON memories_bookmarks USING GIN(tags);
CREATE INDEX idx_memories_bookmarks_search ON memories_bookmarks USING GIN(search_vector);
CREATE INDEX idx_memories_bookmarks_visits ON memories_bookmarks(community_id, visits DESC);

-- Reminders table
CREATE TABLE IF NOT EXISTS memories_reminders (
    id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL,
    username VARCHAR(255) NOT NULL,
    reminder_text TEXT NOT NULL,
    remind_at TIMESTAMP NOT NULL,
    recurring_rule VARCHAR(200),  -- RRULE format for recurring reminders
    is_sent BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    channel VARCHAR(100),  -- Where to send reminder (twitch, discord, slack)
    platform_channel_id VARCHAR(255),  -- Platform-specific channel ID
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sent_at TIMESTAMP,

    -- Index for pending reminders
    CONSTRAINT chk_remind_at_future CHECK (remind_at > created_at)
);

-- Indexes for reminders
CREATE INDEX idx_memories_reminders_pending ON memories_reminders(community_id, remind_at)
    WHERE is_sent = FALSE AND is_active = TRUE;
CREATE INDEX idx_memories_reminders_user ON memories_reminders(user_id, community_id, is_active);
CREATE INDEX idx_memories_reminders_channel ON memories_reminders(community_id, channel, platform_channel_id)
    WHERE is_active = TRUE;

-- Quote vote tracking table (prevent duplicate votes)
CREATE TABLE IF NOT EXISTS memories_quote_votes (
    id SERIAL PRIMARY KEY,
    quote_id INTEGER NOT NULL REFERENCES memories_quotes(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL,
    username VARCHAR(255) NOT NULL,
    vote_type VARCHAR(10) NOT NULL CHECK (vote_type IN ('up', 'down')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(quote_id, user_id)
);

CREATE INDEX idx_memories_quote_votes_lookup ON memories_quote_votes(quote_id, user_id);

-- Analyze tables
ANALYZE memories_quotes;
ANALYZE memories_bookmarks;
ANALYZE memories_reminders;
ANALYZE memories_quote_votes;
