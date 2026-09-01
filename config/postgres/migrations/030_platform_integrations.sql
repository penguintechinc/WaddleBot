-- Migration 030: Create unified platform_integrations table
-- Purpose: Unify bot credentials, community OAuth, and user OAuth in single table
-- Created: 2026-02-05

BEGIN;

-- Create the platform_integrations table
CREATE TABLE IF NOT EXISTS platform_integrations (
    id SERIAL PRIMARY KEY,
    platform VARCHAR(50) NOT NULL,  -- 'twitch', 'slack', 'discord', 'youtube', 'spotify', 'kick', etc.
    integration_type VARCHAR(20) NOT NULL,  -- 'bot', 'user_oauth', 'community_oauth'

    -- Scope identifiers (one of these will be set depending on integration_type)
    community_id INTEGER REFERENCES communities(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES hub_users(id) ON DELETE CASCADE,

    -- Credential storage (encrypted at rest)
    access_token TEXT,
    refresh_token TEXT,
    client_id VARCHAR(255),
    client_secret TEXT,
    token_type VARCHAR(50) DEFAULT 'Bearer',
    expires_at TIMESTAMP WITH TIME ZONE,
    scopes TEXT[],  -- Array of OAuth scopes granted

    -- Metadata
    config_data JSONB,  -- Platform-specific configuration
    is_active BOOLEAN DEFAULT TRUE,
    is_encrypted BOOLEAN DEFAULT TRUE,

    -- Audit trail
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by_user_id INTEGER REFERENCES hub_users(id) ON DELETE SET NULL,
    updated_by_user_id INTEGER REFERENCES hub_users(id) ON DELETE SET NULL,

    -- Constraints: Ensure only one scope is set per integration type
    CONSTRAINT platform_integrations_scope_check CHECK (
        (integration_type = 'bot' AND community_id IS NULL AND user_id IS NULL) OR
        (integration_type = 'community_oauth' AND community_id IS NOT NULL AND user_id IS NULL) OR
        (integration_type = 'user_oauth' AND user_id IS NOT NULL AND community_id IS NULL)
    ),

    -- Prevent duplicate integrations
    CONSTRAINT platform_integrations_unique_bot UNIQUE (platform, integration_type, community_id, user_id) DEFERRABLE INITIALLY DEFERRED
);

-- Create indexes for common query patterns
CREATE INDEX idx_platform_integrations_lookup
    ON platform_integrations(platform, integration_type, is_active);

CREATE INDEX idx_platform_integrations_community
    ON platform_integrations(community_id)
    WHERE community_id IS NOT NULL;

CREATE INDEX idx_platform_integrations_user
    ON platform_integrations(user_id)
    WHERE user_id IS NOT NULL;

CREATE INDEX idx_platform_integrations_active
    ON platform_integrations(is_active);

-- Audit trigger for updated_at timestamp
CREATE OR REPLACE FUNCTION update_platform_integrations_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS platform_integrations_updated_at ON platform_integrations;
CREATE TRIGGER platform_integrations_updated_at
    BEFORE UPDATE ON platform_integrations
    FOR EACH ROW
    EXECUTE FUNCTION update_platform_integrations_timestamp();

-- Enable Row-Level Security (policies will be created in migration 031)
ALTER TABLE platform_integrations ENABLE ROW LEVEL SECURITY;

-- Grant base access to postgres user for now (will be restricted with RLS policies)
GRANT SELECT, INSERT, UPDATE, DELETE ON platform_integrations TO waddlebot;
GRANT USAGE ON SEQUENCE platform_integrations_id_seq TO waddlebot;

COMMIT;
