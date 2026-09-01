-- Migration: Add Module Scopes Table
-- Description: Creates table for storing OAuth-like scope permissions for modules
-- Dependencies: None
-- Author: Waddles Team
-- Date: 2025-12-15

-- Create module_scopes table for scope-based permissions
CREATE TABLE IF NOT EXISTS module_scopes (
    id SERIAL PRIMARY KEY,
    community_id VARCHAR(255) NOT NULL,
    module_name VARCHAR(255) NOT NULL,
    scope VARCHAR(100) NOT NULL,
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    granted_by_user_id VARCHAR(255),
    revoked_at TIMESTAMP,
    revoked_by_user_id VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB,
    CONSTRAINT unique_community_module_scope UNIQUE(community_id, module_name, scope)
);

-- Create indexes for efficient lookups
CREATE INDEX IF NOT EXISTS idx_module_scopes_lookup
ON module_scopes(community_id, module_name)
WHERE is_active = TRUE;

CREATE INDEX IF NOT EXISTS idx_module_scopes_community
ON module_scopes(community_id)
WHERE is_active = TRUE;

CREATE INDEX IF NOT EXISTS idx_module_scopes_module
ON module_scopes(module_name)
WHERE is_active = TRUE;

CREATE INDEX IF NOT EXISTS idx_module_scopes_scope
ON module_scopes(scope)
WHERE is_active = TRUE;

-- Create table for storing revoked tokens
CREATE TABLE IF NOT EXISTS revoked_tokens (
    id SERIAL PRIMARY KEY,
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    jti VARCHAR(64) NOT NULL UNIQUE,
    community_id VARCHAR(255) NOT NULL,
    module_name VARCHAR(255) NOT NULL,
    revoked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    revoked_by_user_id VARCHAR(255),
    reason VARCHAR(255),
    expires_at TIMESTAMP NOT NULL
);

-- Index for efficient token revocation checks
CREATE INDEX IF NOT EXISTS idx_revoked_tokens_hash
ON revoked_tokens(token_hash);

CREATE INDEX IF NOT EXISTS idx_revoked_tokens_jti
ON revoked_tokens(jti);

-- Index for cleanup of expired revocations
CREATE INDEX IF NOT EXISTS idx_revoked_tokens_expires
ON revoked_tokens(expires_at);

-- Create table for audit log of scope changes
CREATE TABLE IF NOT EXISTS module_scope_audit (
    id SERIAL PRIMARY KEY,
    community_id VARCHAR(255) NOT NULL,
    module_name VARCHAR(255) NOT NULL,
    scope VARCHAR(100) NOT NULL,
    action VARCHAR(50) NOT NULL,  -- 'granted', 'revoked'
    performed_by_user_id VARCHAR(255),
    performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);

-- Index for audit log queries
CREATE INDEX IF NOT EXISTS idx_module_scope_audit_lookup
ON module_scope_audit(community_id, module_name, performed_at DESC);

CREATE INDEX IF NOT EXISTS idx_module_scope_audit_user
ON module_scope_audit(performed_by_user_id, performed_at DESC);

-- Function to automatically audit scope changes
CREATE OR REPLACE FUNCTION audit_module_scope_changes()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO module_scope_audit (
            community_id,
            module_name,
            scope,
            action,
            performed_by_user_id,
            metadata
        ) VALUES (
            NEW.community_id,
            NEW.module_name,
            NEW.scope,
            'granted',
            NEW.granted_by_user_id,
            NEW.metadata
        );
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        IF OLD.is_active = TRUE AND NEW.is_active = FALSE THEN
            INSERT INTO module_scope_audit (
                community_id,
                module_name,
                scope,
                action,
                performed_by_user_id,
                metadata
            ) VALUES (
                NEW.community_id,
                NEW.module_name,
                NEW.scope,
                'revoked',
                NEW.revoked_by_user_id,
                NEW.metadata
            );
        END IF;
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO module_scope_audit (
            community_id,
            module_name,
            scope,
            action,
            performed_by_user_id
        ) VALUES (
            OLD.community_id,
            OLD.module_name,
            OLD.scope,
            'deleted',
            NULL
        );
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for audit logging
DROP TRIGGER IF EXISTS trigger_audit_module_scope_changes ON module_scopes;
CREATE TRIGGER trigger_audit_module_scope_changes
    AFTER INSERT OR UPDATE OR DELETE ON module_scopes
    FOR EACH ROW
    EXECUTE FUNCTION audit_module_scope_changes();

-- Function to clean up expired revoked tokens
CREATE OR REPLACE FUNCTION cleanup_expired_revoked_tokens()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM revoked_tokens
    WHERE expires_at < CURRENT_TIMESTAMP;

    GET DIAGNOSTICS deleted_count = ROW_COUNT;

    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Comments for documentation
COMMENT ON TABLE module_scopes IS 'Stores OAuth-like scope permissions for modules per community';
COMMENT ON COLUMN module_scopes.community_id IS 'Community identifier';
COMMENT ON COLUMN module_scopes.module_name IS 'Module name (e.g., music_module, chat_bot)';
COMMENT ON COLUMN module_scopes.scope IS 'Permission scope (e.g., read, write, users:manage)';
COMMENT ON COLUMN module_scopes.granted_at IS 'When the scope was granted';
COMMENT ON COLUMN module_scopes.granted_by_user_id IS 'User ID who granted the scope';
COMMENT ON COLUMN module_scopes.is_active IS 'Whether the scope is currently active';
COMMENT ON COLUMN module_scopes.metadata IS 'Additional metadata about the scope grant';

COMMENT ON TABLE revoked_tokens IS 'Stores revoked JWT tokens to prevent reuse';
COMMENT ON COLUMN revoked_tokens.token_hash IS 'SHA-256 hash of the revoked token';
COMMENT ON COLUMN revoked_tokens.jti IS 'JWT ID (jti claim) for the revoked token';
COMMENT ON COLUMN revoked_tokens.expires_at IS 'When the token would naturally expire';

COMMENT ON TABLE module_scope_audit IS 'Audit log for all scope changes';

-- Insert some example scopes for documentation
-- These are commented out and should only be used for development
/*
INSERT INTO module_scopes (community_id, module_name, scope, granted_by_user_id) VALUES
    ('global', 'music_module', 'playlist:read', 'system'),
    ('global', 'music_module', 'playlist:write', 'system'),
    ('global', 'chat_bot', 'messages:read', 'system'),
    ('global', 'chat_bot', 'messages:write', 'system'),
    ('global', 'admin_module', '*', 'system')
ON CONFLICT (community_id, module_name, scope) DO NOTHING;
*/

-- Note: Permissions are granted to scoped roles in 031_scoped_database_users.sql
