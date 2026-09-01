-- Migration 026: Add Video Proxy and WebRTC Call Tables
-- Description: Add video stream proxy configurations, WebRTC call rooms, and premium feature tracking
-- Author: Waddles Engineering
-- Date: 2026-01-21

BEGIN;

-- Create visibility_level enum if not exists
DO $$ BEGIN
    CREATE TYPE visibility_level AS ENUM ('public', 'registered', 'community', 'admins');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Video stream configurations table
CREATE TABLE IF NOT EXISTS video_stream_configs (
    id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    stream_key VARCHAR(64) UNIQUE NOT NULL,
    stream_key_hash VARCHAR(128) NOT NULL,
    is_active BOOLEAN DEFAULT FALSE,
    max_destinations INTEGER DEFAULT 3,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_video_stream_configs_community_id ON video_stream_configs(community_id);
CREATE INDEX IF NOT EXISTS idx_video_stream_configs_stream_key_hash ON video_stream_configs(stream_key_hash);
CREATE INDEX IF NOT EXISTS idx_video_stream_configs_is_active ON video_stream_configs(is_active);

-- Video stream destinations table
CREATE TABLE IF NOT EXISTS video_stream_destinations (
    id SERIAL PRIMARY KEY,
    config_id INTEGER NOT NULL REFERENCES video_stream_configs(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,
    rtmp_url TEXT NOT NULL,
    stream_key_encrypted TEXT NOT NULL,
    resolution VARCHAR(20) DEFAULT '1080p',
    is_enabled BOOLEAN DEFAULT TRUE,
    force_cut BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT chk_platform CHECK (platform IN ('twitch', 'kick', 'youtube', 'custom'))
);

CREATE INDEX IF NOT EXISTS idx_video_stream_destinations_config_id ON video_stream_destinations(config_id);
CREATE INDEX IF NOT EXISTS idx_video_stream_destinations_platform ON video_stream_destinations(platform);
CREATE INDEX IF NOT EXISTS idx_video_stream_destinations_is_enabled ON video_stream_destinations(is_enabled);

-- Video stream sessions table
CREATE TABLE IF NOT EXISTS video_stream_sessions (
    id SERIAL PRIMARY KEY,
    config_id INTEGER NOT NULL REFERENCES video_stream_configs(id) ON DELETE CASCADE,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    viewer_count_peak INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'active',
    CONSTRAINT chk_status CHECK (status IN ('active', 'ended', 'error'))
);

CREATE INDEX IF NOT EXISTS idx_video_stream_sessions_config_id ON video_stream_sessions(config_id);
CREATE INDEX IF NOT EXISTS idx_video_stream_sessions_status ON video_stream_sessions(status);
CREATE INDEX IF NOT EXISTS idx_video_stream_sessions_started_at ON video_stream_sessions(started_at);

-- Community call rooms table
CREATE TABLE IF NOT EXISTS community_call_rooms (
    id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    livekit_room_id VARCHAR(128) UNIQUE,
    room_name VARCHAR(255) NOT NULL,
    created_by INTEGER NOT NULL REFERENCES hub_users(id) ON DELETE CASCADE,
    is_active BOOLEAN DEFAULT TRUE,
    is_locked BOOLEAN DEFAULT FALSE,
    recording_enabled BOOLEAN DEFAULT FALSE,
    recording_path TEXT,
    max_participants INTEGER DEFAULT 100,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_community_call_rooms_community_id ON community_call_rooms(community_id);
CREATE INDEX IF NOT EXISTS idx_community_call_rooms_livekit_room_id ON community_call_rooms(livekit_room_id);
CREATE INDEX IF NOT EXISTS idx_community_call_rooms_created_by ON community_call_rooms(created_by);
CREATE INDEX IF NOT EXISTS idx_community_call_rooms_is_active ON community_call_rooms(is_active);

-- Community call participants table
CREATE TABLE IF NOT EXISTS community_call_participants (
    id SERIAL PRIMARY KEY,
    room_id INTEGER NOT NULL REFERENCES community_call_rooms(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES hub_users(id) ON DELETE CASCADE,
    role VARCHAR(20) DEFAULT 'viewer',
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    left_at TIMESTAMPTZ,
    CONSTRAINT chk_role CHECK (role IN ('host', 'moderator', 'speaker', 'viewer')),
    CONSTRAINT unique_room_user UNIQUE(room_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_community_call_participants_room_id ON community_call_participants(room_id);
CREATE INDEX IF NOT EXISTS idx_community_call_participants_user_id ON community_call_participants(user_id);
CREATE INDEX IF NOT EXISTS idx_community_call_participants_role ON community_call_participants(role);

-- Call raised hands table
CREATE TABLE IF NOT EXISTS call_raised_hands (
    id SERIAL PRIMARY KEY,
    room_id INTEGER NOT NULL REFERENCES community_call_rooms(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES hub_users(id) ON DELETE CASCADE,
    raised_at TIMESTAMPTZ DEFAULT NOW(),
    acknowledged_at TIMESTAMPTZ,
    acknowledged_by INTEGER REFERENCES hub_users(id) ON DELETE SET NULL,
    CONSTRAINT unique_raised_hand UNIQUE(room_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_call_raised_hands_room_id ON call_raised_hands(room_id);
CREATE INDEX IF NOT EXISTS idx_call_raised_hands_user_id ON call_raised_hands(user_id);
CREATE INDEX IF NOT EXISTS idx_call_raised_hands_raised_at ON call_raised_hands(raised_at);

-- Call annotations table
CREATE TABLE IF NOT EXISTS call_annotations (
    id SERIAL PRIMARY KEY,
    room_id INTEGER NOT NULL REFERENCES community_call_rooms(id) ON DELETE CASCADE,
    annotation_data JSONB NOT NULL,
    created_by INTEGER NOT NULL REFERENCES hub_users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_call_annotations_room_id ON call_annotations(room_id);
CREATE INDEX IF NOT EXISTS idx_call_annotations_created_by ON call_annotations(created_by);
CREATE INDEX IF NOT EXISTS idx_call_annotations_created_at ON call_annotations(created_at);

-- Video feature usage table (premium tracking)
CREATE TABLE IF NOT EXISTS video_feature_usage (
    id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    feature_type VARCHAR(50) NOT NULL,
    usage_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMPTZ,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    CONSTRAINT unique_community_feature_period UNIQUE(community_id, feature_type, period_start)
);

CREATE INDEX IF NOT EXISTS idx_video_feature_usage_community_id ON video_feature_usage(community_id);
CREATE INDEX IF NOT EXISTS idx_video_feature_usage_feature_type ON video_feature_usage(feature_type);
CREATE INDEX IF NOT EXISTS idx_video_feature_usage_period ON video_feature_usage(period_start, period_end);

COMMIT;
