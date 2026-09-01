-- Migration 072: Music Station (normalized queue + per-community policy + moderation audit)
--
-- New feature schema, not a port -- backs hub_api/blueprints/v1/community_music_queue.py.
--
-- `music_station_queue` is deliberately NOT named `music_queue`: migration
-- 012_add_music_providers.sql already created a real, live `music_queue`
-- table (denormalized track fields inline, no tenant_id/playlist grouping)
-- that is not referenced by any application code today (verified via
-- repo-wide grep -- see hub_api/services/schema.py's bind_streaming_tables()
-- docstring for the sibling schema-gap analysis of the same M7 group).
-- Re-declaring `music_queue` here with a different column set would be a
-- silent no-op in any environment where 012 already ran (`CREATE TABLE IF
-- NOT EXISTS` does not ALTER), leaving this feature's own queries 500ing
-- against the old schema -- so this migration uses its own table name
-- instead of colliding with dead-but-deployed schema (hub_api/PORTING.md
-- Gotcha #4's rule: "document it, don't silently invent a column, don't
-- silently drop the whole feature either" -- applied here to a whole
-- table name instead of a single column).

CREATE TABLE IF NOT EXISTS music_tracks (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL,
    provider VARCHAR(20) NOT NULL,
    external_id VARCHAR(512) NOT NULL,
    title VARCHAR(500) NOT NULL,
    artist VARCHAR(500) NOT NULL,
    duration_ms INTEGER NOT NULL DEFAULT 0,
    artwork_url TEXT,
    url TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, provider, external_id)
);

COMMENT ON TABLE music_tracks IS
    'Normalized, deduplicated track cache -- one row per (tenant, provider, external_id), resolved via services/music_providers/resolve().';

CREATE TABLE IF NOT EXISTS music_station_queue (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL,
    community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    track_id INTEGER NOT NULL REFERENCES music_tracks(id) ON DELETE CASCADE,
    position INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'queued'
        CHECK (status IN ('queued', 'playing', 'played', 'removed')),
    source VARCHAR(20) NOT NULL DEFAULT 'request'
        CHECK (source IN ('request', 'playlist')),
    playlist_id VARCHAR(64),
    requested_by INTEGER REFERENCES hub_users(id) ON DELETE SET NULL,
    added_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ
);

COMMENT ON TABLE music_station_queue IS
    'Per-community intermingled playback queue (song requests + playlist entries, mixed providers). See this migration file header for why it is not named music_queue.';
COMMENT ON COLUMN music_station_queue.playlist_id IS
    'Opaque grouping id shared by every track enqueued from one playlist submission -- lets moderation kick the whole playlist in one action.';

CREATE INDEX IF NOT EXISTS idx_music_station_queue_community
    ON music_station_queue (tenant_id, community_id, status, position);
CREATE INDEX IF NOT EXISTS idx_music_station_queue_playlist
    ON music_station_queue (community_id, playlist_id)
    WHERE playlist_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS music_policy (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL,
    community_id INTEGER NOT NULL UNIQUE REFERENCES communities(id) ON DELETE CASCADE,
    song_requests_allowed BOOLEAN NOT NULL DEFAULT TRUE,
    requests_category_restricted BOOLEAN NOT NULL DEFAULT FALSE,
    updated_by INTEGER REFERENCES hub_users(id) ON DELETE SET NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE music_policy IS
    'Per-community Music Station policy -- whether members may submit song requests, and whether requests are restricted to the live "Music" stream category.';

CREATE TABLE IF NOT EXISTS music_moderation_log (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL,
    community_id INTEGER NOT NULL,
    actor_user_id INTEGER REFERENCES hub_users(id) ON DELETE SET NULL,
    action VARCHAR(30) NOT NULL
        CHECK (action IN ('kick_song', 'kick_playlist', 'category_override')),
    target_queue_id INTEGER REFERENCES music_station_queue(id) ON DELETE SET NULL,
    target_playlist_id VARCHAR(64),
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE music_moderation_log IS
    'Audit trail for every Music Station moderation action (kick a song, kick a playlist, override the category restriction for a request).';

CREATE INDEX IF NOT EXISTS idx_music_moderation_log_community
    ON music_moderation_log (tenant_id, community_id, created_at DESC);

ANALYZE music_tracks;
ANALYZE music_station_queue;
ANALYZE music_policy;
ANALYZE music_moderation_log;
