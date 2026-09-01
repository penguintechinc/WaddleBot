-- Migration 060: Create presence sync tables
-- Timestamp: 2026-02-27

-- Table for user presence sync settings
CREATE TABLE user_presence_settings (
    id SERIAL PRIMARY KEY,
    hub_user_id INTEGER UNIQUE NOT NULL REFERENCES hub_users(id) ON DELETE CASCADE,
    sync_enabled BOOLEAN DEFAULT TRUE,
    sync_direction VARCHAR(20) DEFAULT 'bidirectional' CHECK (sync_direction IN ('bidirectional', 'collect_only', 'push_only')),
    platform_overrides JSONB DEFAULT '{}',
    show_in_hub BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Table for logging presence events across platforms
CREATE TABLE presence_events_log (
    id BIGSERIAL PRIMARY KEY,
    hub_user_id INTEGER NOT NULL REFERENCES hub_users(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,
    old_status VARCHAR(20),
    new_status VARCHAR(20) NOT NULL,
    custom_text TEXT,
    source VARCHAR(20) DEFAULT 'platform',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Index for efficient querying of presence events by user and time
CREATE INDEX idx_presence_log_user ON presence_events_log(hub_user_id, created_at DESC);

-- Index for platform-based queries
CREATE INDEX idx_presence_log_platform ON presence_events_log(platform, created_at DESC);

-- Index for source-based queries
CREATE INDEX idx_presence_log_source ON presence_events_log(source, created_at DESC);
