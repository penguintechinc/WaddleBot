-- Migration 011: Add Scoped Tokens and Permission System
-- Description: Implements OAuth-like scoped token system for module access control
-- Author: Waddles Team
-- Date: 2025-12-15

-- Permission scopes catalog
-- Defines all available permission scopes that modules can request
CREATE TABLE IF NOT EXISTS permission_scopes (
    id SERIAL PRIMARY KEY,
    scope_name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    category VARCHAR(50),  -- 'chat', 'overlay', 'music', 'obs', 'moderation', 'admin', 'desktop'
    risk_level VARCHAR(20) DEFAULT 'low'  -- 'low', 'medium', 'high', 'critical'
);

COMMENT ON TABLE permission_scopes IS
  'Catalog of all available permission scopes that modules can request';

COMMENT ON COLUMN permission_scopes.scope_name IS
  'Unique identifier for the scope (e.g., send_message, read_chat)';

COMMENT ON COLUMN permission_scopes.category IS
  'Category of functionality: chat, overlay, music, obs, moderation, admin, or desktop';

COMMENT ON COLUMN permission_scopes.risk_level IS
  'Security risk level: low (safe), medium (caution), high (dangerous), critical (critical ops)';

-- Module scope requirements
-- Defines which scopes each module requires (globally, not per-community)
CREATE TABLE IF NOT EXISTS module_required_scopes (
    id SERIAL PRIMARY KEY,
    module_name VARCHAR(255) NOT NULL,
    scope_id INTEGER REFERENCES permission_scopes(id),
    is_optional BOOLEAN DEFAULT FALSE,
    UNIQUE(module_name, scope_id)
);

COMMENT ON TABLE module_required_scopes IS
  'Global configuration of which scopes each module requires';

COMMENT ON COLUMN module_required_scopes.module_name IS
  'Name of the module (e.g., music_player, obs_controller)';

COMMENT ON COLUMN module_required_scopes.is_optional IS
  'Whether this scope is optional (can still function without it) or required';

-- Community scope grants
-- Per-community permission grants for modules
CREATE TABLE IF NOT EXISTS scope_grants (
    id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    module_name VARCHAR(255) NOT NULL,
    scope_id INTEGER REFERENCES permission_scopes(id),
    granted_by_user_id INTEGER REFERENCES hub_users(id),
    granted_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE(community_id, module_name, scope_id)
);

COMMENT ON TABLE scope_grants IS
  'Per-community permission grants for modules. Allows selective scope granting per community.';

COMMENT ON COLUMN scope_grants.community_id IS
  'Community where this scope grant applies';

COMMENT ON COLUMN scope_grants.module_name IS
  'Module that received this scope grant';

COMMENT ON COLUMN scope_grants.granted_by_user_id IS
  'Community admin user who granted this permission';

COMMENT ON COLUMN scope_grants.expires_at IS
  'Optional expiration date for temporary grants';

COMMENT ON COLUMN scope_grants.is_active IS
  'Whether this grant is currently active (allows soft-delete)';

-- Module access tokens
-- Scoped JWT-like tokens for modules to authenticate requests
CREATE TABLE IF NOT EXISTS module_access_tokens (
    id SERIAL PRIMARY KEY,
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    module_name VARCHAR(255) NOT NULL,
    scopes TEXT[],  -- Array of granted scope names
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    last_used_at TIMESTAMPTZ,
    is_revoked BOOLEAN DEFAULT FALSE
);

COMMENT ON TABLE module_access_tokens IS
  'Scoped access tokens for modules. Similar to OAuth tokens, each token has specific permissions.';

COMMENT ON COLUMN module_access_tokens.token_hash IS
  'SHA-256 hash of the token (only hash is stored, not the actual token)';

COMMENT ON COLUMN module_access_tokens.scopes IS
  'Array of granted scope names (e.g., {send_message, read_chat})';

COMMENT ON COLUMN module_access_tokens.last_used_at IS
  'Timestamp of the last time this token was used (for auditing)';

COMMENT ON COLUMN module_access_tokens.is_revoked IS
  'Whether this token has been revoked (soft-delete)';

-- Index for efficient token lookups and cleanup
CREATE INDEX IF NOT EXISTS idx_module_tokens_community
ON module_access_tokens(community_id, module_name);

-- Index for finding active tokens
CREATE INDEX IF NOT EXISTS idx_module_tokens_active
ON module_access_tokens(community_id, is_revoked, expires_at)
WHERE is_revoked = FALSE;

-- Index for token cleanup queries
CREATE INDEX IF NOT EXISTS idx_module_tokens_expired
ON module_access_tokens(expires_at)
WHERE is_revoked = FALSE;

-- Index for scope grants lookups
CREATE INDEX IF NOT EXISTS idx_scope_grants_community
ON scope_grants(community_id, module_name, is_active);

COMMENT ON INDEX idx_module_tokens_community IS
  'Efficient lookup of tokens by community and module';

COMMENT ON INDEX idx_module_tokens_active IS
  'Efficient lookup of active (non-revoked, non-expired) tokens';

COMMENT ON INDEX idx_module_tokens_expired IS
  'Efficient identification of expired tokens for cleanup';

COMMENT ON INDEX idx_scope_grants_community IS
  'Efficient lookup of scope grants for a module within a community';

-- Predefined scopes
-- These are the core scopes available in the system
INSERT INTO permission_scopes (scope_name, description, category, risk_level) VALUES
-- Chat and moderation scopes
('send_message', 'Send messages to chat', 'chat', 'low'),
('read_chat', 'Read chat messages', 'chat', 'low'),
('moderate_chat', 'Delete messages, timeout users', 'moderation', 'high'),
-- Music scopes
('control_music', 'Play, pause, skip music', 'music', 'medium'),
('request_songs', 'Add songs to queue', 'music', 'low'),
-- OBS/Streaming scopes
('change_scene', 'Change OBS scenes', 'obs', 'medium'),
('control_sources', 'Show/hide OBS sources', 'obs', 'medium'),
('start_stream', 'Start streaming', 'obs', 'critical'),
('stop_stream', 'Stop streaming', 'obs', 'critical'),
-- Overlay scopes
('overlay_write', 'Update overlay content', 'overlay', 'low'),
-- Desktop control scopes
('desktop_control', 'Send keypresses, control apps', 'desktop', 'high'),
-- Admin scopes
('community_config', 'Modify community settings', 'admin', 'high')
ON CONFLICT (scope_name) DO NOTHING;

COMMENT ON TABLE permission_scopes IS
  'This INSERT statement populates the core scopes available in the system';
