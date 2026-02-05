-- Migration 033: Migrate existing credentials to platform_integrations
-- Source: platform_configs (bot credentials) and music_oauth_tokens (community OAuth)
-- This is a data migration - source tables are preserved for rollback safety

-- ============================================================================
-- STEP 1: Migrate platform_configs → platform_integrations (bot credentials)
-- The platform_configs table stores key-value pairs per platform.
-- We need to pivot them into single rows in platform_integrations.
-- ============================================================================

-- Migrate bot credentials for each platform that has at least one config entry
-- We use a CTE to pivot the key-value pairs into columns
INSERT INTO platform_integrations (
    platform, integration_type, access_token, client_id, client_secret,
    config_data, is_active, is_encrypted, created_at, updated_at, updated_by_user_id
)
SELECT
    pc.platform,
    'bot' AS integration_type,
    MAX(CASE WHEN pc.config_key = 'bot_token' THEN pc.config_value END) AS access_token,
    MAX(CASE WHEN pc.config_key = 'client_id' THEN pc.config_value END) AS client_id,
    MAX(CASE WHEN pc.config_key = 'client_secret' THEN pc.config_value END) AS client_secret,
    jsonb_object_agg(
        pc.config_key,
        CASE
            WHEN pc.config_key IN ('bot_token', 'client_id', 'client_secret') THEN NULL
            ELSE pc.config_value
        END
    ) FILTER (
        WHERE pc.config_key NOT IN ('bot_token', 'client_id', 'client_secret')
        AND pc.config_value IS NOT NULL
    ) AS config_data,
    TRUE AS is_active,
    -- Mark as encrypted if any secret field was encrypted
    bool_or(pc.is_encrypted) AS is_encrypted,
    MIN(pc.updated_at) AS created_at,
    MAX(pc.updated_at) AS updated_at,
    MAX(pc.updated_by) AS updated_by_user_id
FROM platform_configs pc
WHERE pc.platform IN ('discord', 'twitch', 'slack', 'youtube', 'kick')
GROUP BY pc.platform
ON CONFLICT DO NOTHING;

-- Migrate email configuration as a special 'email' bot integration
INSERT INTO platform_integrations (
    platform, integration_type, config_data, is_active, is_encrypted,
    created_at, updated_at, updated_by_user_id
)
SELECT
    'email' AS platform,
    'bot' AS integration_type,
    jsonb_object_agg(pc.config_key, pc.config_value) AS config_data,
    TRUE AS is_active,
    bool_or(pc.is_encrypted) AS is_encrypted,
    MIN(pc.updated_at) AS created_at,
    MAX(pc.updated_at) AS updated_at,
    MAX(pc.updated_by) AS updated_by_user_id
FROM platform_configs pc
WHERE pc.platform = 'email'
HAVING COUNT(*) > 0
ON CONFLICT DO NOTHING;

-- Migrate storage configuration as a special 'storage' bot integration
INSERT INTO platform_integrations (
    platform, integration_type, client_id, client_secret, config_data,
    is_active, is_encrypted, created_at, updated_at, updated_by_user_id
)
SELECT
    'storage' AS platform,
    'bot' AS integration_type,
    MAX(CASE WHEN pc.config_key = 's3_access_key' THEN pc.config_value END) AS client_id,
    MAX(CASE WHEN pc.config_key = 's3_secret_key' THEN pc.config_value END) AS client_secret,
    jsonb_object_agg(
        pc.config_key,
        CASE
            WHEN pc.config_key IN ('s3_access_key', 's3_secret_key') THEN NULL
            ELSE pc.config_value
        END
    ) FILTER (
        WHERE pc.config_key NOT IN ('s3_access_key', 's3_secret_key')
        AND pc.config_value IS NOT NULL
    ) AS config_data,
    TRUE AS is_active,
    bool_or(pc.is_encrypted) AS is_encrypted,
    MIN(pc.updated_at) AS created_at,
    MAX(pc.updated_at) AS updated_at,
    MAX(pc.updated_by) AS updated_by_user_id
FROM platform_configs pc
WHERE pc.platform = 'storage'
HAVING COUNT(*) > 0
ON CONFLICT DO NOTHING;

-- ============================================================================
-- STEP 2: Migrate music_oauth_tokens → platform_integrations (community OAuth)
-- ============================================================================

INSERT INTO platform_integrations (
    platform, integration_type, community_id, access_token, refresh_token,
    token_type, expires_at, scopes, is_active, is_encrypted,
    created_at, updated_at
)
SELECT
    mot.platform,
    'community_oauth' AS integration_type,
    mot.community_id,
    mot.access_token,
    mot.refresh_token,
    mot.token_type,
    mot.expires_at,
    CASE
        WHEN mot.scope IS NOT NULL THEN string_to_array(mot.scope, ' ')
        ELSE NULL
    END AS scopes,
    TRUE AS is_active,
    FALSE AS is_encrypted,
    mot.created_at,
    mot.updated_at
FROM music_oauth_tokens mot
ON CONFLICT DO NOTHING;

-- ============================================================================
-- STEP 3: Verify migration counts
-- ============================================================================
DO $$
DECLARE
    source_platform_count INTEGER;
    source_music_count INTEGER;
    target_bot_count INTEGER;
    target_community_count INTEGER;
BEGIN
    SELECT COUNT(DISTINCT platform) INTO source_platform_count
    FROM platform_configs
    WHERE platform IN ('discord', 'twitch', 'slack', 'youtube', 'kick', 'email', 'storage');

    SELECT COUNT(*) INTO source_music_count FROM music_oauth_tokens;

    SELECT COUNT(*) INTO target_bot_count
    FROM platform_integrations WHERE integration_type = 'bot';

    SELECT COUNT(*) INTO target_community_count
    FROM platform_integrations WHERE integration_type = 'community_oauth';

    RAISE NOTICE 'Migration Summary:';
    RAISE NOTICE '  Source platform_configs platforms: %', source_platform_count;
    RAISE NOTICE '  Source music_oauth_tokens rows: %', source_music_count;
    RAISE NOTICE '  Target bot integrations: %', target_bot_count;
    RAISE NOTICE '  Target community_oauth integrations: %', target_community_count;
END $$;

-- ============================================================================
-- NOTE: Source tables (platform_configs, music_oauth_tokens) are NOT dropped.
-- They remain available for rollback. Drop them in a future migration after
-- the new system is validated in production.
-- ============================================================================
