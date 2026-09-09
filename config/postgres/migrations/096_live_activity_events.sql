-- Migration 096: live_activity_events -- the in-WebUI live activity feed.
--
-- Captures one row per processed message: the inbound message AND the bot's
-- reply, community-scoped, for the real-time "watch it interact" feed.
-- (activity_message_events is a leaderboard message-COUNTER with no text
-- column, so it cannot back a conversation feed -- hence this table.)

CREATE TABLE IF NOT EXISTS live_activity_events (
    id          BIGSERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    platform    VARCHAR(50) NOT NULL,
    actor       VARCHAR(255),
    message_in  TEXT,
    reply_out   TEXT,
    channel_id  VARCHAR(255),
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_live_activity_events_community_id
    ON live_activity_events (community_id, id);
