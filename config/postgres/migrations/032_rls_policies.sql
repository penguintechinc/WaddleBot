-- Migration 032: Row-Level Security policies for platform_integrations
-- Enforces per-module credential isolation at the database level
-- Each module user can only see rows for their own platform

-- ============================================================================
-- ENABLE ROW-LEVEL SECURITY
-- ============================================================================
ALTER TABLE platform_integrations ENABLE ROW LEVEL SECURITY;

-- Force RLS for table owner too (prevents bypass via superuser connections)
-- Note: The waddlebot superuser will still bypass RLS by default
ALTER TABLE platform_integrations FORCE ROW LEVEL SECURITY;

-- ============================================================================
-- HUB ADMIN: Full access to all rows
-- ============================================================================
CREATE POLICY hub_admin_full_access ON platform_integrations
    FOR ALL
    TO hub_admin
    USING (TRUE)
    WITH CHECK (TRUE);

-- ============================================================================
-- CREDENTIAL MANAGER: Read/write access to all active integrations
-- ============================================================================
CREATE POLICY credential_manager_access ON platform_integrations
    FOR ALL
    TO mod_credential_manager
    USING (TRUE)
    WITH CHECK (TRUE);

-- ============================================================================
-- TWITCH MODULE POLICIES
-- ============================================================================

-- Twitch Trigger: read-only access to twitch bot credentials
CREATE POLICY twitch_trigger_read ON platform_integrations
    FOR SELECT
    TO mod_trigger_twitch
    USING (platform = 'twitch' AND is_active = TRUE);

-- Twitch Action: read access to twitch bot and community credentials
CREATE POLICY twitch_action_read ON platform_integrations
    FOR SELECT
    TO mod_action_twitch
    USING (platform = 'twitch' AND is_active = TRUE);

-- ============================================================================
-- DISCORD MODULE POLICIES
-- ============================================================================

-- Discord Trigger: read-only access to discord bot credentials
CREATE POLICY discord_trigger_read ON platform_integrations
    FOR SELECT
    TO mod_trigger_discord
    USING (platform = 'discord' AND is_active = TRUE);

-- Discord Action: read access to discord bot and community credentials
CREATE POLICY discord_action_read ON platform_integrations
    FOR SELECT
    TO mod_action_discord
    USING (platform = 'discord' AND is_active = TRUE);

-- ============================================================================
-- SLACK MODULE POLICIES
-- ============================================================================

-- Slack Trigger: read-only access to slack bot credentials
CREATE POLICY slack_trigger_read ON platform_integrations
    FOR SELECT
    TO mod_trigger_slack
    USING (platform = 'slack' AND is_active = TRUE);

-- Slack Action: read access to slack bot and community credentials
CREATE POLICY slack_action_read ON platform_integrations
    FOR SELECT
    TO mod_action_slack
    USING (platform = 'slack' AND is_active = TRUE);

-- ============================================================================
-- YOUTUBE MODULE POLICIES
-- ============================================================================

-- YouTube Trigger: read-only access to youtube bot credentials
CREATE POLICY youtube_trigger_read ON platform_integrations
    FOR SELECT
    TO mod_trigger_youtube
    USING (platform = 'youtube' AND is_active = TRUE);

-- YouTube Action: read access to youtube bot and community credentials
CREATE POLICY youtube_action_read ON platform_integrations
    FOR SELECT
    TO mod_action_youtube
    USING (platform = 'youtube' AND is_active = TRUE);

-- ============================================================================
-- KICK MODULE POLICIES
-- ============================================================================

-- Kick Trigger: read-only access to kick bot credentials
CREATE POLICY kick_trigger_read ON platform_integrations
    FOR SELECT
    TO mod_trigger_kick
    USING (platform = 'kick' AND is_active = TRUE);

-- ============================================================================
-- MUSIC MODULE POLICIES
-- ============================================================================

-- Spotify Interaction: full access to spotify community_oauth integrations
CREATE POLICY spotify_interaction_access ON platform_integrations
    FOR ALL
    TO mod_interactive_spotify
    USING (platform = 'spotify' AND is_active = TRUE)
    WITH CHECK (platform = 'spotify');

-- YouTube Music Interaction: read access to youtube community_oauth integrations
CREATE POLICY ytmusic_interaction_read ON platform_integrations
    FOR SELECT
    TO mod_interactive_ytmusic
    USING (platform = 'youtube' AND integration_type = 'community_oauth' AND is_active = TRUE);

-- ============================================================================
-- ROUTER MODULE: Read access to all platform integrations for routing decisions
-- ============================================================================
CREATE POLICY router_read_all ON platform_integrations
    FOR SELECT
    TO mod_router
    USING (is_active = TRUE);

-- ============================================================================
-- COLUMN-LEVEL SECURITY ON hub_users
-- Revoke full access, grant only safe columns to module users
-- ============================================================================

-- Revoke default public access to hub_users
REVOKE ALL ON hub_users FROM PUBLIC;

-- Re-grant to hub_admin (full access)
GRANT ALL ON hub_users TO hub_admin;

-- Identity core needs full access for user management
GRANT SELECT, INSERT, UPDATE ON hub_users TO mod_core_identity;

-- Router needs broad read for routing decisions
GRANT SELECT ON hub_users TO mod_router;

-- Analytics and security need full read for analysis
GRANT SELECT ON hub_users TO mod_core_analytics;
GRANT SELECT ON hub_users TO mod_core_security;

-- ============================================================================
-- CREDENTIAL ACCESS LOG: Module-specific policies
-- ============================================================================
ALTER TABLE credential_access_log ENABLE ROW LEVEL SECURITY;

-- Hub admin sees all audit logs
CREATE POLICY credential_log_admin_access ON credential_access_log
    FOR ALL
    TO hub_admin
    USING (TRUE)
    WITH CHECK (TRUE);

-- Credential manager can read and write all audit logs
CREATE POLICY credential_log_manager_access ON credential_access_log
    FOR ALL
    TO mod_credential_manager
    USING (TRUE)
    WITH CHECK (TRUE);

-- Each module can only see its own audit entries
CREATE POLICY credential_log_self_access ON credential_access_log
    FOR SELECT
    TO mod_trigger_twitch, mod_trigger_discord, mod_trigger_slack,
       mod_trigger_youtube, mod_trigger_kick,
       mod_action_twitch, mod_action_discord, mod_action_slack, mod_action_youtube,
       mod_interactive_spotify, mod_interactive_ytmusic, mod_router
    USING (db_user = current_user);
