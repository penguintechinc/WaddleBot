-- Migration 034: Module database account management
-- Enables dynamic provisioning of scoped PostgreSQL users when superadmins
-- register new modules through the hub admin panel

-- ============================================================================
-- Module DB accounts tracking table
-- ============================================================================
CREATE TABLE IF NOT EXISTS module_db_accounts (
    id SERIAL PRIMARY KEY,
    module_name VARCHAR(100) NOT NULL UNIQUE,
    db_username VARCHAR(63) NOT NULL UNIQUE,
    module_type VARCHAR(30) NOT NULL,
    permission_template VARCHAR(50) NOT NULL DEFAULT 'minimal',
    is_active BOOLEAN DEFAULT TRUE,
    custom_grants TEXT[],
    owned_tables TEXT[],
    readable_tables TEXT[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by_user_id INTEGER REFERENCES hub_users(id),

    CONSTRAINT valid_module_type CHECK (
        module_type IN ('trigger', 'action', 'interactive', 'core', 'custom')
    ),
    CONSTRAINT valid_permission_template CHECK (
        permission_template IN (
            'trigger_readonly',
            'action_platform',
            'interactive_standard',
            'core_broad',
            'core_admin',
            'minimal',
            'custom'
        )
    )
);

CREATE INDEX IF NOT EXISTS idx_module_db_accounts_active
    ON module_db_accounts(is_active, module_type);

-- Audit trigger
CREATE TRIGGER update_module_db_accounts_updated_at
    BEFORE UPDATE ON module_db_accounts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- Permission template definitions
-- Stored as JSONB so templates can be managed without schema changes
-- ============================================================================
CREATE TABLE IF NOT EXISTS db_permission_templates (
    id SERIAL PRIMARY KEY,
    template_name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    grants JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default permission templates
INSERT INTO db_permission_templates (template_name, description, grants) VALUES
(
    'trigger_readonly',
    'Read-only access for trigger/collector modules. Can read servers, communities, and their own platform credentials.',
    '[
        {"action": "GRANT SELECT", "tables": ["servers", "community_servers", "communities", "modules"]},
        {"action": "GRANT SELECT", "columns": ["id", "username", "is_active"], "table": "hub_users"},
        {"action": "GRANT USAGE", "target": "ALL SEQUENCES IN SCHEMA public"}
    ]'::jsonb
),
(
    'action_platform',
    'Read + platform credential access for action/pushing modules. Can read communities and access platform_integrations for their platform.',
    '[
        {"action": "GRANT SELECT", "tables": ["servers", "community_servers", "communities"]},
        {"action": "GRANT SELECT", "columns": ["id", "email", "username", "avatar_url", "is_active"], "table": "hub_users"},
        {"action": "GRANT SELECT", "tables": ["platform_integrations"]},
        {"action": "GRANT USAGE", "target": "ALL SEQUENCES IN SCHEMA public"}
    ]'::jsonb
),
(
    'interactive_standard',
    'Standard access for interactive modules. Can read communities and manage their own feature tables.',
    '[
        {"action": "GRANT SELECT", "tables": ["servers", "community_servers", "communities", "modules"]},
        {"action": "GRANT SELECT", "columns": ["id", "username", "is_active"], "table": "hub_users"},
        {"action": "GRANT USAGE", "target": "ALL SEQUENCES IN SCHEMA public"}
    ]'::jsonb
),
(
    'core_broad',
    'Broad read access for core system modules. Can read most tables and write to their owned tables.',
    '[
        {"action": "GRANT SELECT", "tables": ["servers", "community_servers", "communities", "modules", "commands"]},
        {"action": "GRANT SELECT", "columns": ["id", "username", "email", "is_active"], "table": "hub_users"},
        {"action": "GRANT USAGE", "target": "ALL SEQUENCES IN SCHEMA public"}
    ]'::jsonb
),
(
    'core_admin',
    'Full access for admin-level core modules (hub, analytics, security). Can read and write all tables.',
    '[
        {"action": "GRANT ALL PRIVILEGES", "target": "ALL TABLES IN SCHEMA public"},
        {"action": "GRANT ALL PRIVILEGES", "target": "ALL SEQUENCES IN SCHEMA public"}
    ]'::jsonb
),
(
    'minimal',
    'Minimal access. Can only connect and read basic shared tables.',
    '[
        {"action": "GRANT SELECT", "tables": ["communities", "servers"]},
        {"action": "GRANT USAGE", "target": "ALL SEQUENCES IN SCHEMA public"}
    ]'::jsonb
),
(
    'custom',
    'Custom grants specified per-module. No default grants applied.',
    '[]'::jsonb
)
ON CONFLICT (template_name) DO NOTHING;

-- ============================================================================
-- Function: Provision a new module database account
-- Called by the hub admin backend when a superadmin creates a new module
-- ============================================================================
CREATE OR REPLACE FUNCTION provision_module_db_account(
    p_module_name TEXT,
    p_module_type TEXT,
    p_permission_template TEXT,
    p_password TEXT,
    p_owned_tables TEXT[] DEFAULT NULL,
    p_readable_tables TEXT[] DEFAULT NULL,
    p_custom_grants TEXT[] DEFAULT NULL,
    p_created_by INTEGER DEFAULT NULL
) RETURNS TABLE(db_username TEXT, success BOOLEAN, message TEXT) AS $$
DECLARE
    v_db_username TEXT;
    v_template JSONB;
    v_grant JSONB;
    v_tables TEXT;
    v_sql TEXT;
BEGIN
    -- Generate database username from module name (max 63 chars for PG)
    v_db_username := 'mod_' || regexp_replace(lower(p_module_name), '[^a-z0-9]', '_', 'g');
    IF length(v_db_username) > 63 THEN
        v_db_username := left(v_db_username, 63);
    END IF;

    -- Check if username already exists
    IF EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = v_db_username) THEN
        -- Update password and ensure login is enabled
        EXECUTE format('ALTER ROLE %I WITH LOGIN PASSWORD %L', v_db_username, p_password);
    ELSE
        -- Create the role
        EXECUTE format('CREATE ROLE %I WITH LOGIN PASSWORD %L', v_db_username, p_password);
    END IF;

    -- Grant basic connection
    EXECUTE format('GRANT CONNECT ON DATABASE waddlebot TO %I', v_db_username);
    EXECUTE format('GRANT USAGE ON SCHEMA public TO %I', v_db_username);

    -- Apply permission template grants
    SELECT grants INTO v_template
    FROM db_permission_templates
    WHERE template_name = p_permission_template;

    IF v_template IS NOT NULL THEN
        FOR v_grant IN SELECT * FROM jsonb_array_elements(v_template)
        LOOP
            -- Handle table-level grants
            IF v_grant ? 'tables' THEN
                SELECT string_agg(t::text, ', ')
                INTO v_tables
                FROM jsonb_array_elements_text(v_grant->'tables') t;

                IF v_tables IS NOT NULL THEN
                    v_sql := format('%s ON %s TO %I',
                        v_grant->>'action', v_tables, v_db_username);
                    BEGIN
                        EXECUTE v_sql;
                    EXCEPTION WHEN OTHERS THEN
                        RAISE WARNING 'Failed to execute grant: % - %', v_sql, SQLERRM;
                    END;
                END IF;

            -- Handle column-level grants
            ELSIF v_grant ? 'columns' THEN
                SELECT string_agg(c::text, ', ')
                INTO v_tables
                FROM jsonb_array_elements_text(v_grant->'columns') c;

                IF v_tables IS NOT NULL AND v_grant ? 'table' THEN
                    v_sql := format('GRANT SELECT (%s) ON %s TO %I',
                        v_tables, v_grant->>'table', v_db_username);
                    BEGIN
                        EXECUTE v_sql;
                    EXCEPTION WHEN OTHERS THEN
                        RAISE WARNING 'Failed to execute grant: % - %', v_sql, SQLERRM;
                    END;
                END IF;

            -- Handle target-based grants (ALL SEQUENCES, etc.)
            ELSIF v_grant ? 'target' THEN
                v_sql := format('%s ON %s TO %I',
                    v_grant->>'action', v_grant->>'target', v_db_username);
                BEGIN
                    EXECUTE v_sql;
                EXCEPTION WHEN OTHERS THEN
                    RAISE WARNING 'Failed to execute grant: % - %', v_sql, SQLERRM;
                END;
            END IF;
        END LOOP;
    END IF;

    -- Apply owned table grants (full CRUD)
    IF p_owned_tables IS NOT NULL THEN
        FOREACH v_tables IN ARRAY p_owned_tables
        LOOP
            v_sql := format('GRANT SELECT, INSERT, UPDATE, DELETE ON %I TO %I',
                v_tables, v_db_username);
            BEGIN
                EXECUTE v_sql;
            EXCEPTION WHEN OTHERS THEN
                RAISE WARNING 'Failed to grant owned table access: % - %', v_sql, SQLERRM;
            END;
        END LOOP;
    END IF;

    -- Apply readable table grants (SELECT only)
    IF p_readable_tables IS NOT NULL THEN
        FOREACH v_tables IN ARRAY p_readable_tables
        LOOP
            v_sql := format('GRANT SELECT ON %I TO %I', v_tables, v_db_username);
            BEGIN
                EXECUTE v_sql;
            EXCEPTION WHEN OTHERS THEN
                RAISE WARNING 'Failed to grant read access: % - %', v_sql, SQLERRM;
            END;
        END LOOP;
    END IF;

    -- Apply custom grants
    IF p_custom_grants IS NOT NULL THEN
        FOREACH v_sql IN ARRAY p_custom_grants
        LOOP
            -- Replace placeholder with actual username
            v_sql := replace(v_sql, '{username}', v_db_username);
            BEGIN
                EXECUTE v_sql;
            EXCEPTION WHEN OTHERS THEN
                RAISE WARNING 'Failed to execute custom grant: % - %', v_sql, SQLERRM;
            END;
        END LOOP;
    END IF;

    -- Record the account in tracking table
    INSERT INTO module_db_accounts (
        module_name, db_username, module_type, permission_template,
        owned_tables, readable_tables, custom_grants, created_by_user_id
    ) VALUES (
        p_module_name, v_db_username, p_module_type, p_permission_template,
        p_owned_tables, p_readable_tables, p_custom_grants, p_created_by
    )
    ON CONFLICT (module_name) DO UPDATE SET
        db_username = v_db_username,
        module_type = p_module_type,
        permission_template = p_permission_template,
        owned_tables = p_owned_tables,
        readable_tables = p_readable_tables,
        custom_grants = p_custom_grants,
        is_active = TRUE,
        updated_at = CURRENT_TIMESTAMP;

    RETURN QUERY SELECT v_db_username, TRUE, 'Account provisioned successfully'::TEXT;

EXCEPTION WHEN OTHERS THEN
    RETURN QUERY SELECT v_db_username, FALSE, ('Error: ' || SQLERRM)::TEXT;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Only hub_admin can call this function
REVOKE ALL ON FUNCTION provision_module_db_account FROM PUBLIC;
GRANT EXECUTE ON FUNCTION provision_module_db_account TO hub_admin;

-- ============================================================================
-- Function: Deactivate a module database account
-- Revokes login privilege but preserves the role for audit trail
-- ============================================================================
CREATE OR REPLACE FUNCTION deactivate_module_db_account(
    p_module_name TEXT
) RETURNS TABLE(success BOOLEAN, message TEXT) AS $$
DECLARE
    v_db_username TEXT;
BEGIN
    SELECT db_username INTO v_db_username
    FROM module_db_accounts
    WHERE module_name = p_module_name AND is_active = TRUE;

    IF v_db_username IS NULL THEN
        RETURN QUERY SELECT FALSE, 'Module account not found or already inactive'::TEXT;
        RETURN;
    END IF;

    -- Revoke login (user cannot connect but role preserved for audit)
    EXECUTE format('ALTER ROLE %I WITH NOLOGIN', v_db_username);

    -- Mark as inactive in tracking table
    UPDATE module_db_accounts
    SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
    WHERE module_name = p_module_name;

    RETURN QUERY SELECT TRUE, ('Account ' || v_db_username || ' deactivated')::TEXT;

EXCEPTION WHEN OTHERS THEN
    RETURN QUERY SELECT FALSE, ('Error: ' || SQLERRM)::TEXT;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

REVOKE ALL ON FUNCTION deactivate_module_db_account FROM PUBLIC;
GRANT EXECUTE ON FUNCTION deactivate_module_db_account TO hub_admin;

-- ============================================================================
-- Function: Rotate a module database password
-- ============================================================================
CREATE OR REPLACE FUNCTION rotate_module_db_password(
    p_module_name TEXT,
    p_new_password TEXT
) RETURNS TABLE(success BOOLEAN, message TEXT) AS $$
DECLARE
    v_db_username TEXT;
BEGIN
    SELECT db_username INTO v_db_username
    FROM module_db_accounts
    WHERE module_name = p_module_name AND is_active = TRUE;

    IF v_db_username IS NULL THEN
        RETURN QUERY SELECT FALSE, 'Module account not found or inactive'::TEXT;
        RETURN;
    END IF;

    EXECUTE format('ALTER ROLE %I WITH PASSWORD %L', v_db_username, p_new_password);

    UPDATE module_db_accounts
    SET updated_at = CURRENT_TIMESTAMP
    WHERE module_name = p_module_name;

    RETURN QUERY SELECT TRUE, ('Password rotated for ' || v_db_username)::TEXT;

EXCEPTION WHEN OTHERS THEN
    RETURN QUERY SELECT FALSE, ('Error: ' || SQLERRM)::TEXT;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

REVOKE ALL ON FUNCTION rotate_module_db_password FROM PUBLIC;
GRANT EXECUTE ON FUNCTION rotate_module_db_password TO hub_admin;

-- ============================================================================
-- Backfill: Register existing static module accounts from migration 031
-- This records the statically-created users so they appear in the hub admin
-- ============================================================================
INSERT INTO module_db_accounts (module_name, db_username, module_type, permission_template) VALUES
    ('hub-api', 'hub_admin', 'core', 'core_admin'),
    ('router', 'mod_router', 'core', 'core_broad'),
    ('trigger-twitch', 'mod_trigger_twitch', 'trigger', 'trigger_readonly'),
    ('trigger-discord', 'mod_trigger_discord', 'trigger', 'trigger_readonly'),
    ('trigger-slack', 'mod_trigger_slack', 'trigger', 'trigger_readonly'),
    ('trigger-youtube', 'mod_trigger_youtube', 'trigger', 'trigger_readonly'),
    ('trigger-kick', 'mod_trigger_kick', 'trigger', 'trigger_readonly'),
    ('action-twitch', 'mod_action_twitch', 'action', 'action_platform'),
    ('action-discord', 'mod_action_discord', 'action', 'action_platform'),
    ('action-slack', 'mod_action_slack', 'action', 'action_platform'),
    ('action-youtube', 'mod_action_youtube', 'action', 'action_platform'),
    ('action-lambda', 'mod_action_lambda', 'action', 'minimal'),
    ('action-gcp-functions', 'mod_action_gcp', 'action', 'minimal'),
    ('interactive-ai', 'mod_interactive_ai', 'interactive', 'interactive_standard'),
    ('interactive-alias', 'mod_interactive_alias', 'interactive', 'interactive_standard'),
    ('interactive-shoutout', 'mod_interactive_shoutout', 'interactive', 'interactive_standard'),
    ('interactive-inventory', 'mod_interactive_inventory', 'interactive', 'interactive_standard'),
    ('interactive-calendar', 'mod_interactive_calendar', 'interactive', 'interactive_standard'),
    ('interactive-memories', 'mod_interactive_memories', 'interactive', 'interactive_standard'),
    ('interactive-youtube-music', 'mod_interactive_ytmusic', 'interactive', 'interactive_standard'),
    ('interactive-spotify', 'mod_interactive_spotify', 'interactive', 'interactive_standard'),
    ('interactive-loyalty', 'mod_interactive_loyalty', 'interactive', 'interactive_standard'),
    ('interactive-quote', 'mod_interactive_quote', 'interactive', 'interactive_standard'),
    ('core-labels', 'mod_core_labels', 'core', 'core_broad'),
    ('core-browser-source', 'mod_core_browser_source', 'core', 'core_broad'),
    ('core-identity', 'mod_core_identity', 'core', 'core_broad'),
    ('core-ai-researcher', 'mod_core_ai_researcher', 'core', 'core_broad'),
    ('core-workflow', 'mod_core_workflow', 'core', 'core_broad'),
    ('core-community', 'mod_core_community', 'core', 'core_broad'),
    ('core-reputation', 'mod_core_reputation', 'core', 'core_broad'),
    ('core-analytics', 'mod_core_analytics', 'core', 'core_admin'),
    ('core-security', 'mod_core_security', 'core', 'core_admin'),
    ('core-video-proxy', 'mod_core_video_proxy', 'core', 'core_broad'),
    ('core-engagement', 'mod_core_engagement', 'core', 'core_broad'),
    ('core-module-rtc', 'mod_core_rtc', 'core', 'core_broad'),
    ('credential-manager', 'mod_credential_manager', 'core', 'custom')
ON CONFLICT (module_name) DO NOTHING;

-- Grant hub_admin access to module_db_accounts management
GRANT SELECT, INSERT, UPDATE ON module_db_accounts TO hub_admin;
GRANT SELECT ON db_permission_templates TO hub_admin;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO hub_admin;
