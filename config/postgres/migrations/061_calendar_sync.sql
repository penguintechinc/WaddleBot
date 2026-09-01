-- Migration 061: Create calendar sync tables and extend connected_calendars
-- Timestamp: 2026-02-27

-- Extend connected_calendars table with sync fields
DO $$
BEGIN
    -- Add sync_token if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'connected_calendars' AND column_name = 'sync_token'
    ) THEN
        ALTER TABLE connected_calendars ADD COLUMN sync_token TEXT;
    END IF;

    -- Add sync_direction if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'connected_calendars' AND column_name = 'sync_direction'
    ) THEN
        ALTER TABLE connected_calendars
        ADD COLUMN sync_direction VARCHAR(20) DEFAULT 'bidirectional'
        CHECK (sync_direction IN ('bidirectional', 'collect_only', 'push_only'));
    END IF;

    -- Add provider_calendar_id if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'connected_calendars' AND column_name = 'provider_calendar_id'
    ) THEN
        ALTER TABLE connected_calendars ADD COLUMN provider_calendar_id TEXT;
    END IF;
END $$;

-- Table for community calendar subscriptions
CREATE TABLE IF NOT EXISTS community_calendar_subscriptions (
    id SERIAL PRIMARY KEY,
    hub_user_id INTEGER NOT NULL REFERENCES hub_users(id) ON DELETE CASCADE,
    community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    connected_calendar_id INTEGER NOT NULL REFERENCES connected_calendars(id) ON DELETE CASCADE,
    external_calendar_id TEXT NOT NULL,
    name TEXT NOT NULL,
    sync_enabled BOOLEAN DEFAULT TRUE,
    last_sync_at TIMESTAMPTZ,
    sync_token TEXT,
    sync_error TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(community_id, external_calendar_id)
);

-- Table for mapping calendar events between systems
CREATE TABLE IF NOT EXISTS calendar_event_sync_map (
    id SERIAL PRIMARY KEY,
    calendar_event_id INTEGER NOT NULL REFERENCES calendar_events(id) ON DELETE CASCADE,
    connected_calendar_id INTEGER NOT NULL REFERENCES connected_calendars(id) ON DELETE CASCADE,
    external_event_id TEXT NOT NULL,
    sync_direction VARCHAR(20) NOT NULL DEFAULT 'bidirectional',
    last_synced_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    etag TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(external_event_id, connected_calendar_id)
);

-- Indexes for community_calendar_subscriptions
CREATE INDEX idx_community_calendar_subs_user ON community_calendar_subscriptions(hub_user_id);
CREATE INDEX idx_community_calendar_subs_community ON community_calendar_subscriptions(community_id);
CREATE INDEX idx_community_calendar_subs_calendar ON community_calendar_subscriptions(connected_calendar_id);
CREATE INDEX idx_community_calendar_subs_sync ON community_calendar_subscriptions(sync_enabled, last_sync_at)
WHERE sync_enabled = TRUE;

-- Indexes for calendar_event_sync_map
CREATE INDEX idx_calendar_event_sync_map_event ON calendar_event_sync_map(calendar_event_id);
CREATE INDEX idx_calendar_event_sync_map_calendar ON calendar_event_sync_map(connected_calendar_id);
CREATE INDEX idx_calendar_event_sync_map_external ON calendar_event_sync_map(external_event_id);
CREATE INDEX idx_calendar_event_sync_map_synced ON calendar_event_sync_map(last_synced_at DESC);
