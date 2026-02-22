-- Migration 044: Add activity tracking tables for leaderboard system
-- Required by: activityController.js (watch sessions, message events, daily stats)

-- Watch session tracking (stream viewers joining/leaving)
CREATE TABLE IF NOT EXISTS activity_watch_sessions (
    id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    hub_user_id INTEGER REFERENCES hub_users(id) ON DELETE SET NULL,
    platform VARCHAR(50) NOT NULL,
    platform_user_id VARCHAR(255) NOT NULL,
    platform_username VARCHAR(255),
    channel_id VARCHAR(255) NOT NULL,
    session_start TIMESTAMPTZ DEFAULT NOW(),
    session_end TIMESTAMPTZ,
    duration_seconds INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Message event log (individual chat messages)
CREATE TABLE IF NOT EXISTS activity_message_events (
    id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    hub_user_id INTEGER REFERENCES hub_users(id) ON DELETE SET NULL,
    platform VARCHAR(50) NOT NULL,
    platform_user_id VARCHAR(255) NOT NULL,
    platform_username VARCHAR(255),
    channel_id VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Daily aggregated stats (used by leaderboard queries)
CREATE TABLE IF NOT EXISTS activity_stats_daily (
    id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    hub_user_id INTEGER REFERENCES hub_users(id) ON DELETE SET NULL,
    platform_user_id VARCHAR(255),
    platform_username VARCHAR(255),
    stat_date DATE NOT NULL DEFAULT CURRENT_DATE,
    watch_time_seconds INTEGER DEFAULT 0,
    message_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Unique constraint for upsert in updateDailyStats()
-- Uses COALESCE to handle NULL hub_user_id and platform_user_id
CREATE UNIQUE INDEX IF NOT EXISTS idx_activity_stats_daily_upsert
    ON activity_stats_daily (community_id, COALESCE(hub_user_id, -1), COALESCE(platform_user_id, ''), stat_date);

-- Performance indexes for leaderboard queries
CREATE INDEX IF NOT EXISTS idx_activity_stats_daily_community
    ON activity_stats_daily (community_id, stat_date);

CREATE INDEX IF NOT EXISTS idx_activity_stats_daily_watch_time
    ON activity_stats_daily (community_id, stat_date, watch_time_seconds DESC);

CREATE INDEX IF NOT EXISTS idx_activity_stats_daily_messages
    ON activity_stats_daily (community_id, stat_date, message_count DESC);

-- Watch session indexes for active session lookups
CREATE INDEX IF NOT EXISTS idx_activity_watch_sessions_active
    ON activity_watch_sessions (community_id, platform, platform_user_id, channel_id)
    WHERE is_active = true;

-- Message events index for time-range queries
CREATE INDEX IF NOT EXISTS idx_activity_message_events_community
    ON activity_message_events (community_id, created_at);
