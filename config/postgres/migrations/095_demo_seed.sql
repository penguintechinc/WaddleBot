-- Migration 095: Demo seed data
-- Populates the default community with real Discord (Club Penguinz) and Twitch
-- (penguinzplays) connections for WebUI Connected Platforms + Modules pages.
--
-- This migration is idempotent -- all INSERTs use ON CONFLICT DO NOTHING.
-- Running against a database that already has demo data will produce no changes.
--
-- Demo data seeded:
-- - Default community: "waddlebot" (id=1 if fresh DB)
-- - Discord server: Club Penguinz (guild id 474965105759748096)
-- - Twitch channel: penguinzplays
-- - Bot modules: discord_bot, twitch_bot
-- - Module installations: installed for the default community

BEGIN;

-- Seed the default community if it doesn't exist
-- Scoped to the 'global' tenant (communities.tenant_id is NOT NULL), same tenant
-- as the 'default' landing-spot community. This is a SEPARATE demo community --
-- the 'default' community stays clean (no integrations) per the tenancy model.
INSERT INTO communities (
    name,
    display_name,
    description,
    platform,
    platform_server_id,
    community_type,
    is_active,
    is_public,
    config,
    tenant_id,
    created_at
)
SELECT
    'waddlebot',
    'WaddleBot Community',
    'Demo community for WaddleBot connected platforms (Discord + Twitch).',
    'discord',
    '474965105759748096',
    'creator',
    true,
    true,
    '{}',
    t.id,
    NOW()
FROM tenants t
WHERE t.slug = 'global'
ON CONFLICT (name) DO NOTHING;

-- Get the default community ID for use in subsequent operations
-- If it doesn't exist, this will be NULL, and the INSERTs below will fail
-- gracefully with ON CONFLICT DO NOTHING
WITH default_community AS (
    SELECT id FROM communities WHERE name = 'waddlebot' LIMIT 1
)
INSERT INTO community_servers (
    community_id,
    platform,
    platform_server_id,
    platform_server_name,
    link_type,
    status,
    is_primary,
    config,
    created_at
)
SELECT
    dc.id,
    'discord',
    '474965105759748096',
    'Club Penguinz',
    'standard',
    'approved',
    true,
    '{}',
    NOW()
FROM default_community dc
ON CONFLICT (community_id, platform, platform_server_id) DO NOTHING;

-- Seed Twitch connection
WITH default_community AS (
    SELECT id FROM communities WHERE name = 'waddlebot' LIMIT 1
)
INSERT INTO community_servers (
    community_id,
    platform,
    platform_server_id,
    platform_server_name,
    link_type,
    status,
    is_primary,
    config,
    created_at
)
SELECT
    dc.id,
    'twitch',
    'penguinzplays',
    'penguinzplays',
    'standard',
    'approved',
    false,
    '{}',
    NOW()
FROM default_community dc
ON CONFLICT (community_id, platform, platform_server_id) DO NOTHING;

-- Seed bot modules
INSERT INTO hub_modules (
    name,
    display_name,
    description,
    version,
    author,
    category,
    is_published,
    is_core,
    config_schema,
    created_at
) VALUES
    (
        'discord_bot',
        'Discord Bot',
        'Discord bot integration module for community engagement.',
        '1.0.0',
        'WaddleBot',
        'platform',
        true,
        false,
        '{}',
        NOW()
    ),
    (
        'twitch_bot',
        'Twitch Bot',
        'Twitch bot integration module for streaming communities.',
        '1.0.0',
        'WaddleBot',
        'platform',
        true,
        false,
        '{}',
        NOW()
    )
ON CONFLICT (name) DO NOTHING;

-- Seed module installations for the default community
WITH default_community AS (
    SELECT id FROM communities WHERE name = 'waddlebot' LIMIT 1
),
discord_mod AS (
    SELECT id FROM hub_modules WHERE name = 'discord_bot' LIMIT 1
),
twitch_mod AS (
    SELECT id FROM hub_modules WHERE name = 'twitch_bot' LIMIT 1
)
INSERT INTO hub_module_installations (
    community_id,
    module_id,
    config,
    is_enabled,
    installed_at
)
SELECT dc.id, dm.id, '{}'::jsonb, true, NOW()
FROM default_community dc, discord_mod dm
UNION ALL
SELECT dc.id, tm.id, '{}'::jsonb, true, NOW()
FROM default_community dc, twitch_mod tm
ON CONFLICT (community_id, module_id) DO NOTHING;

COMMIT;
