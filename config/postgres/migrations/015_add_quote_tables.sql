-- Migration 015: Add Quote Module Tables
-- For tracking and managing community quotes with moderation support

-- Quotes table
CREATE TABLE IF NOT EXISTS quotes (
    id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    quote_text TEXT NOT NULL,
    quoted_user_id INTEGER REFERENCES hub_users(id) ON DELETE SET NULL,
    quoted_username VARCHAR(255),
    added_by_user_id INTEGER REFERENCES hub_users(id) ON DELETE SET NULL,
    platform VARCHAR(50),
    context TEXT,
    tags TEXT[],
    is_approved BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,

    -- Full-text search index
    search_vector tsvector GENERATED ALWAYS AS (
        immutable_to_tsvector('english'::regconfig, coalesce(quote_text, '') || ' ' || coalesce(context, '') || ' ' || coalesce(immutable_array_to_string(tags, ' '::text), ''))
    ) STORED
);

-- Indexes for quotes table
CREATE INDEX IF NOT EXISTS idx_quotes_community
    ON quotes(community_id, created_at DESC)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_quotes_quoted_user
    ON quotes(quoted_user_id, community_id)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_quotes_created_at
    ON quotes(created_at DESC)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_quotes_deleted_at
    ON quotes(deleted_at)
    WHERE deleted_at IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_quotes_approved
    ON quotes(community_id, is_approved)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_quotes_tags
    ON quotes USING GIN(tags)
    WHERE deleted_at IS NULL;

-- Full-text search index
CREATE INDEX IF NOT EXISTS idx_quotes_search
    ON quotes USING GIN(search_vector)
    WHERE deleted_at IS NULL;

-- Analyze table
ANALYZE quotes;
