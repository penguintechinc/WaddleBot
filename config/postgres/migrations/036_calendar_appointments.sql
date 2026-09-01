-- Migration 036: Calendar Appointments & Booking System
-- Adds tables for Calendly-like appointment scheduling within Waddles
-- Depends on: calendar_events, hub_users, platform_integrations, communities

BEGIN;

-- ============================================================================
-- User Calendar Settings (Phase 4B)
-- Controls how a user's availability is displayed and what can be booked
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_calendar_settings (
    id SERIAL PRIMARY KEY,
    hub_user_id INTEGER NOT NULL REFERENCES hub_users(id) ON DELETE CASCADE,

    -- Visibility scopes: 'hidden', 'free_busy', 'details'
    visibility_public VARCHAR(20) DEFAULT 'hidden',
    visibility_registered VARCHAR(20) DEFAULT 'free_busy',
    visibility_community VARCHAR(20) DEFAULT 'details',

    -- Slot configuration (stored as integer minutes)
    slot_durations INTEGER[] DEFAULT '{30}',  -- e.g. {15, 30, 60}
    default_slot_duration INTEGER DEFAULT 30,

    -- Booking constraints
    min_notice_hours INTEGER DEFAULT 4,
    max_future_days INTEGER DEFAULT 30,
    buffer_minutes INTEGER DEFAULT 0,  -- gap between appointments

    -- Weekly availability (JSONB: {"monday": [{"start":"09:00","end":"17:00"}], ...})
    weekly_availability JSONB DEFAULT '{}',
    timezone VARCHAR(50) DEFAULT 'UTC',

    -- Booking page
    booking_enabled BOOLEAN DEFAULT FALSE,
    booking_slug VARCHAR(100) UNIQUE,
    booking_page_title VARCHAR(255),
    booking_page_description TEXT,

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT user_calendar_settings_unique_user UNIQUE (hub_user_id),
    CONSTRAINT user_calendar_settings_visibility_public_check
        CHECK (visibility_public IN ('hidden', 'free_busy', 'details')),
    CONSTRAINT user_calendar_settings_visibility_registered_check
        CHECK (visibility_registered IN ('hidden', 'free_busy', 'details')),
    CONSTRAINT user_calendar_settings_visibility_community_check
        CHECK (visibility_community IN ('hidden', 'free_busy', 'details'))
);

CREATE INDEX idx_user_calendar_settings_user ON user_calendar_settings(hub_user_id);
CREATE INDEX idx_user_calendar_settings_slug ON user_calendar_settings(booking_slug)
    WHERE booking_slug IS NOT NULL;

-- ============================================================================
-- Connected Calendars (Phase 4A)
-- Tracks external calendar OAuth connections (Google, Microsoft)
-- OAuth tokens stored in platform_integrations table
-- ============================================================================
CREATE TABLE IF NOT EXISTS connected_calendars (
    id SERIAL PRIMARY KEY,
    hub_user_id INTEGER NOT NULL REFERENCES hub_users(id) ON DELETE CASCADE,
    platform_integration_id INTEGER NOT NULL REFERENCES platform_integrations(id) ON DELETE CASCADE,

    provider VARCHAR(20) NOT NULL,  -- 'google', 'microsoft'
    calendar_id VARCHAR(255) NOT NULL,  -- external calendar ID
    calendar_name VARCHAR(255),
    is_primary BOOLEAN DEFAULT FALSE,
    sync_enabled BOOLEAN DEFAULT TRUE,
    last_sync_at TIMESTAMPTZ,
    sync_error TEXT,

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT connected_calendars_unique UNIQUE (hub_user_id, provider, calendar_id)
);

CREATE INDEX idx_connected_calendars_user ON connected_calendars(hub_user_id);
CREATE INDEX idx_connected_calendars_sync ON connected_calendars(sync_enabled, last_sync_at)
    WHERE sync_enabled = TRUE;

-- ============================================================================
-- Free/Busy Cache (Phase 4A)
-- Cached free/busy blocks from connected calendars
-- ============================================================================
CREATE TABLE IF NOT EXISTS calendar_free_busy (
    id SERIAL PRIMARY KEY,
    hub_user_id INTEGER NOT NULL REFERENCES hub_users(id) ON DELETE CASCADE,
    connected_calendar_id INTEGER REFERENCES connected_calendars(id) ON DELETE CASCADE,

    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    status VARCHAR(20) DEFAULT 'busy',  -- 'busy', 'tentative'
    title VARCHAR(255),  -- only stored if visibility allows

    fetched_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_calendar_free_busy_user_time
    ON calendar_free_busy(hub_user_id, start_time, end_time);
CREATE INDEX idx_calendar_free_busy_calendar
    ON calendar_free_busy(connected_calendar_id);

-- ============================================================================
-- Booking Pages (Phase 4F)
-- Shareable booking page configurations (individual or group)
-- ============================================================================
CREATE TABLE IF NOT EXISTS booking_pages (
    id SERIAL PRIMARY KEY,
    slug VARCHAR(100) UNIQUE NOT NULL,
    page_type VARCHAR(20) NOT NULL DEFAULT 'individual',  -- 'individual', 'group'

    -- Owner: user for individual, community for group
    hub_user_id INTEGER REFERENCES hub_users(id) ON DELETE CASCADE,
    community_id INTEGER REFERENCES communities(id) ON DELETE CASCADE,

    title VARCHAR(255) NOT NULL,
    description TEXT,
    slot_duration INTEGER NOT NULL DEFAULT 30,  -- minutes

    -- Access control
    access_scope VARCHAR(20) DEFAULT 'public',  -- 'public', 'registered', 'community'

    -- Custom form fields (Phase 4E) - up to 8 fields
    form_fields JSONB DEFAULT '[]',
    -- Format: [{"name":"reason","type":"textarea","label":"Reason","required":true}, ...]

    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT booking_pages_owner_check CHECK (
        (page_type = 'individual' AND hub_user_id IS NOT NULL AND community_id IS NULL) OR
        (page_type = 'group' AND community_id IS NOT NULL)
    ),
    CONSTRAINT booking_pages_access_scope_check
        CHECK (access_scope IN ('public', 'registered', 'community'))
);

CREATE INDEX idx_booking_pages_slug ON booking_pages(slug) WHERE is_active = TRUE;
CREATE INDEX idx_booking_pages_user ON booking_pages(hub_user_id)
    WHERE hub_user_id IS NOT NULL;
CREATE INDEX idx_booking_pages_community ON booking_pages(community_id)
    WHERE community_id IS NOT NULL;

-- ============================================================================
-- Group Booking Members (Phase 4D)
-- Members whose availability is aggregated for group booking pages
-- ============================================================================
CREATE TABLE IF NOT EXISTS booking_page_members (
    id SERIAL PRIMARY KEY,
    booking_page_id INTEGER NOT NULL REFERENCES booking_pages(id) ON DELETE CASCADE,
    hub_user_id INTEGER NOT NULL REFERENCES hub_users(id) ON DELETE CASCADE,
    is_required BOOLEAN DEFAULT TRUE,  -- must be available for slot to show

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT booking_page_members_unique UNIQUE (booking_page_id, hub_user_id)
);

-- ============================================================================
-- Bookings (Phase 4C)
-- Individual appointment bookings
-- ============================================================================
CREATE TABLE IF NOT EXISTS bookings (
    id SERIAL PRIMARY KEY,
    booking_uuid UUID DEFAULT gen_random_uuid() UNIQUE NOT NULL,
    booking_page_id INTEGER NOT NULL REFERENCES booking_pages(id) ON DELETE CASCADE,

    -- The person being booked (host)
    host_user_id INTEGER NOT NULL REFERENCES hub_users(id),

    -- The person booking (guest)
    guest_user_id INTEGER REFERENCES hub_users(id),  -- null if public/anonymous
    guest_name VARCHAR(255) NOT NULL,
    guest_email VARCHAR(255),

    -- Time slot
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    timezone VARCHAR(50) DEFAULT 'UTC',

    -- Status
    status VARCHAR(20) DEFAULT 'confirmed',
    -- 'pending', 'confirmed', 'cancelled_by_host', 'cancelled_by_guest', 'completed', 'no_show'

    -- Custom form responses (Phase 4E)
    form_responses JSONB DEFAULT '{}',

    -- Cancellation
    cancelled_at TIMESTAMPTZ,
    cancellation_reason TEXT,

    -- Notes
    host_notes TEXT,
    guest_notes TEXT,

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT bookings_status_check CHECK (
        status IN ('pending', 'confirmed', 'cancelled_by_host', 'cancelled_by_guest', 'completed', 'no_show')
    )
);

CREATE INDEX idx_bookings_page ON bookings(booking_page_id);
CREATE INDEX idx_bookings_host ON bookings(host_user_id, start_time);
CREATE INDEX idx_bookings_guest ON bookings(guest_user_id) WHERE guest_user_id IS NOT NULL;
CREATE INDEX idx_bookings_time ON bookings(start_time, end_time)
    WHERE status IN ('pending', 'confirmed');
CREATE INDEX idx_bookings_uuid ON bookings(booking_uuid);

-- ============================================================================
-- Updated_at trigger function (reuse if exists)
-- ============================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at triggers
DO $$
DECLARE
    tbl TEXT;
BEGIN
    FOR tbl IN SELECT unnest(ARRAY[
        'user_calendar_settings',
        'connected_calendars',
        'booking_pages',
        'bookings'
    ])
    LOOP
        EXECUTE format(
            'CREATE TRIGGER update_%s_updated_at
             BEFORE UPDATE ON %I
             FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()',
            tbl, tbl
        );
    END LOOP;
END;
$$;

COMMIT;
