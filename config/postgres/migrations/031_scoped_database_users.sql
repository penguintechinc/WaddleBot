-- Migration 031: Create scoped PostgreSQL users for module isolation
-- Principle of Least Privilege: each module gets its own database user
-- Passwords reference environment variables; defaults are for development only
-- In production, passwords MUST be set via Kubernetes Secrets or secret manager

-- ============================================================================
-- HELPER: Create user if not exists
-- ============================================================================
CREATE OR REPLACE FUNCTION create_user_if_not_exists(
    p_username TEXT,
    p_password TEXT
) RETURNS VOID AS $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = p_username) THEN
        EXECUTE format('CREATE ROLE %I WITH LOGIN PASSWORD %L', p_username, p_password);
    ELSE
        EXECUTE format('ALTER ROLE %I WITH LOGIN PASSWORD %L', p_username, p_password);
    END IF;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- HUB ADMIN (full access - manages all platform integrations)
-- ============================================================================
SELECT create_user_if_not_exists('hub_admin', 'hub_admin_dev_changeme');
GRANT CONNECT ON DATABASE waddlebot TO hub_admin;
GRANT USAGE, CREATE ON SCHEMA public TO hub_admin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO hub_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO hub_admin;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO hub_admin;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO hub_admin;

-- ============================================================================
-- ROUTER MODULE (core routing, needs broad read access)
-- ============================================================================
SELECT create_user_if_not_exists('mod_router', 'mod_router_dev_changeme');
GRANT CONNECT ON DATABASE waddlebot TO mod_router;
GRANT USAGE ON SCHEMA public TO mod_router;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO mod_router;
GRANT INSERT, UPDATE ON commands, command_aliases, module_configs TO mod_router;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO mod_router;

-- ============================================================================
-- TRIGGER MODULES (read-heavy, receive events from platforms)
-- ============================================================================

-- Twitch Trigger
SELECT create_user_if_not_exists('mod_trigger_twitch', 'mod_trigger_twitch_dev_changeme');
GRANT CONNECT ON DATABASE waddlebot TO mod_trigger_twitch;
GRANT USAGE ON SCHEMA public TO mod_trigger_twitch;
GRANT SELECT ON servers, community_servers, communities, modules TO mod_trigger_twitch;
GRANT SELECT (id, username, is_active) ON hub_users TO mod_trigger_twitch;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO mod_trigger_twitch;

-- Discord Trigger
SELECT create_user_if_not_exists('mod_trigger_discord', 'mod_trigger_discord_dev_changeme');
GRANT CONNECT ON DATABASE waddlebot TO mod_trigger_discord;
GRANT USAGE ON SCHEMA public TO mod_trigger_discord;
GRANT SELECT ON servers, community_servers, communities, modules TO mod_trigger_discord;
GRANT SELECT (id, username, is_active) ON hub_users TO mod_trigger_discord;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO mod_trigger_discord;

-- Slack Trigger
SELECT create_user_if_not_exists('mod_trigger_slack', 'mod_trigger_slack_dev_changeme');
GRANT CONNECT ON DATABASE waddlebot TO mod_trigger_slack;
GRANT USAGE ON SCHEMA public TO mod_trigger_slack;
GRANT SELECT ON servers, community_servers, communities, modules TO mod_trigger_slack;
GRANT SELECT (id, username, is_active) ON hub_users TO mod_trigger_slack;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO mod_trigger_slack;

-- YouTube Trigger
SELECT create_user_if_not_exists('mod_trigger_youtube', 'mod_trigger_youtube_dev_changeme');
GRANT CONNECT ON DATABASE waddlebot TO mod_trigger_youtube;
GRANT USAGE ON SCHEMA public TO mod_trigger_youtube;
GRANT SELECT ON servers, community_servers, communities, modules TO mod_trigger_youtube;
GRANT SELECT (id, username, is_active) ON hub_users TO mod_trigger_youtube;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO mod_trigger_youtube;

-- Kick Trigger
SELECT create_user_if_not_exists('mod_trigger_kick', 'mod_trigger_kick_dev_changeme');
GRANT CONNECT ON DATABASE waddlebot TO mod_trigger_kick;
GRANT USAGE ON SCHEMA public TO mod_trigger_kick;
GRANT SELECT ON servers, community_servers, communities, modules TO mod_trigger_kick;
GRANT SELECT (id, username, is_active) ON hub_users TO mod_trigger_kick;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO mod_trigger_kick;

-- ============================================================================
-- ACTION MODULES (push messages to platforms)
-- ============================================================================

-- Twitch Action
SELECT create_user_if_not_exists('mod_action_twitch', 'mod_action_twitch_dev_changeme');
GRANT CONNECT ON DATABASE waddlebot TO mod_action_twitch;
GRANT USAGE ON SCHEMA public TO mod_action_twitch;
GRANT SELECT ON servers, community_servers, communities TO mod_action_twitch;
GRANT SELECT (id, email, username, avatar_url, is_active) ON hub_users TO mod_action_twitch;
GRANT SELECT ON platform_integrations TO mod_action_twitch;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO mod_action_twitch;

-- Discord Action
SELECT create_user_if_not_exists('mod_action_discord', 'mod_action_discord_dev_changeme');
GRANT CONNECT ON DATABASE waddlebot TO mod_action_discord;
GRANT USAGE ON SCHEMA public TO mod_action_discord;
GRANT SELECT ON servers, community_servers, communities TO mod_action_discord;
GRANT SELECT (id, email, username, avatar_url, is_active) ON hub_users TO mod_action_discord;
GRANT SELECT ON platform_integrations TO mod_action_discord;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO mod_action_discord;

-- Slack Action
SELECT create_user_if_not_exists('mod_action_slack', 'mod_action_slack_dev_changeme');
GRANT CONNECT ON DATABASE waddlebot TO mod_action_slack;
GRANT USAGE ON SCHEMA public TO mod_action_slack;
GRANT SELECT ON servers, community_servers, communities TO mod_action_slack;
GRANT SELECT (id, email, username, avatar_url, is_active) ON hub_users TO mod_action_slack;
GRANT SELECT ON platform_integrations TO mod_action_slack;
GRANT SELECT, INSERT, UPDATE, DELETE ON slack_actions TO mod_action_slack;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO mod_action_slack;

-- YouTube Action
SELECT create_user_if_not_exists('mod_action_youtube', 'mod_action_youtube_dev_changeme');
GRANT CONNECT ON DATABASE waddlebot TO mod_action_youtube;
GRANT USAGE ON SCHEMA public TO mod_action_youtube;
GRANT SELECT ON servers, community_servers, communities TO mod_action_youtube;
GRANT SELECT (id, email, username, avatar_url, is_active) ON hub_users TO mod_action_youtube;
GRANT SELECT ON platform_integrations TO mod_action_youtube;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO mod_action_youtube;

-- Lambda Action
SELECT create_user_if_not_exists('mod_action_lambda', 'mod_action_lambda_dev_changeme');
GRANT CONNECT ON DATABASE waddlebot TO mod_action_lambda;
GRANT USAGE ON SCHEMA public TO mod_action_lambda;
GRANT SELECT ON servers, community_servers, communities, modules TO mod_action_lambda;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO mod_action_lambda;

-- GCP Functions Action
SELECT create_user_if_not_exists('mod_action_gcp', 'mod_action_gcp_dev_changeme');
GRANT CONNECT ON DATABASE waddlebot TO mod_action_gcp;
GRANT USAGE ON SCHEMA public TO mod_action_gcp;
GRANT SELECT ON servers, community_servers, communities, modules TO mod_action_gcp;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO mod_action_gcp;

-- ============================================================================
-- INTERACTIVE MODULES
-- ============================================================================

-- AI Interaction
SELECT create_user_if_not_exists('mod_interactive_ai', 'mod_interactive_ai_dev_changeme');
GRANT CONNECT ON DATABASE waddlebot TO mod_interactive_ai;
GRANT USAGE ON SCHEMA public TO mod_interactive_ai;
GRANT SELECT ON servers, community_servers, communities, modules, commands TO mod_interactive_ai;
GRANT SELECT (id, username, is_active) ON hub_users TO mod_interactive_ai;
GRANT SELECT, INSERT, UPDATE ON ai_insights TO mod_interactive_ai;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO mod_interactive_ai;

-- Alias Interaction
SELECT create_user_if_not_exists('mod_interactive_alias', 'mod_interactive_alias_dev_changeme');
GRANT CONNECT ON DATABASE waddlebot TO mod_interactive_alias;
GRANT USAGE ON SCHEMA public TO mod_interactive_alias;
GRANT SELECT ON servers, community_servers, communities, modules TO mod_interactive_alias;
GRANT SELECT, INSERT, UPDATE, DELETE ON command_aliases TO mod_interactive_alias;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO mod_interactive_alias;

-- Shoutout Interaction
SELECT create_user_if_not_exists('mod_interactive_shoutout', 'mod_interactive_shoutout_dev_changeme');
GRANT CONNECT ON DATABASE waddlebot TO mod_interactive_shoutout;
GRANT USAGE ON SCHEMA public TO mod_interactive_shoutout;
GRANT SELECT ON servers, community_servers, communities TO mod_interactive_shoutout;
GRANT SELECT (id, username, is_active) ON hub_users TO mod_interactive_shoutout;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO mod_interactive_shoutout;

-- Inventory Interaction
SELECT create_user_if_not_exists('mod_interactive_inventory', 'mod_interactive_inventory_dev_changeme');
GRANT CONNECT ON DATABASE waddlebot TO mod_interactive_inventory;
GRANT USAGE ON SCHEMA public TO mod_interactive_inventory;
GRANT SELECT ON servers, community_servers, communities TO mod_interactive_inventory;
GRANT SELECT (id, username, is_active) ON hub_users TO mod_interactive_inventory;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO mod_interactive_inventory;

-- Calendar Interaction
SELECT create_user_if_not_exists('mod_interactive_calendar', 'mod_interactive_calendar_dev_changeme');
GRANT CONNECT ON DATABASE waddlebot TO mod_interactive_calendar;
GRANT USAGE ON SCHEMA public TO mod_interactive_calendar;
GRANT SELECT ON servers, community_servers, communities TO mod_interactive_calendar;
GRANT SELECT (id, username, is_active) ON hub_users TO mod_interactive_calendar;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO mod_interactive_calendar;

-- Memories Interaction
SELECT create_user_if_not_exists('mod_interactive_memories', 'mod_interactive_memories_dev_changeme');
GRANT CONNECT ON DATABASE waddlebot TO mod_interactive_memories;
GRANT USAGE ON SCHEMA public TO mod_interactive_memories;
GRANT SELECT ON servers, community_servers, communities TO mod_interactive_memories;
GRANT SELECT (id, username, is_active) ON hub_users TO mod_interactive_memories;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO mod_interactive_memories;

-- YouTube Music Interaction
SELECT create_user_if_not_exists('mod_interactive_ytmusic', 'mod_interactive_ytmusic_dev_changeme');
GRANT CONNECT ON DATABASE waddlebot TO mod_interactive_ytmusic;
GRANT USAGE ON SCHEMA public TO mod_interactive_ytmusic;
GRANT SELECT ON servers, community_servers, communities TO mod_interactive_ytmusic;
GRANT SELECT ON platform_integrations TO mod_interactive_ytmusic;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO mod_interactive_ytmusic;

-- Spotify Interaction
SELECT create_user_if_not_exists('mod_interactive_spotify', 'mod_interactive_spotify_dev_changeme');
GRANT CONNECT ON DATABASE waddlebot TO mod_interactive_spotify;
GRANT USAGE ON SCHEMA public TO mod_interactive_spotify;
GRANT SELECT ON servers, community_servers, communities TO mod_interactive_spotify;
GRANT SELECT, INSERT, UPDATE, DELETE ON platform_integrations TO mod_interactive_spotify;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO mod_interactive_spotify;

-- Loyalty Interaction
SELECT create_user_if_not_exists('mod_interactive_loyalty', 'mod_interactive_loyalty_dev_changeme');
GRANT CONNECT ON DATABASE waddlebot TO mod_interactive_loyalty;
GRANT USAGE ON SCHEMA public TO mod_interactive_loyalty;
GRANT SELECT ON servers, community_servers, communities TO mod_interactive_loyalty;
GRANT SELECT (id, username, is_active) ON hub_users TO mod_interactive_loyalty;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO mod_interactive_loyalty;

-- Quote Interaction
SELECT create_user_if_not_exists('mod_interactive_quote', 'mod_interactive_quote_dev_changeme');
GRANT CONNECT ON DATABASE waddlebot TO mod_interactive_quote;
GRANT USAGE ON SCHEMA public TO mod_interactive_quote;
GRANT SELECT ON servers, community_servers, communities TO mod_interactive_quote;
GRANT SELECT (id, username, is_active) ON hub_users TO mod_interactive_quote;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO mod_interactive_quote;

-- ============================================================================
-- CORE MODULES
-- ============================================================================

-- Labels Core
SELECT create_user_if_not_exists('mod_core_labels', 'mod_core_labels_dev_changeme');
GRANT CONNECT ON DATABASE waddlebot TO mod_core_labels;
GRANT USAGE ON SCHEMA public TO mod_core_labels;
GRANT SELECT ON servers, community_servers, communities, modules TO mod_core_labels;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO mod_core_labels;

-- Browser Source Core
SELECT create_user_if_not_exists('mod_core_browser_source', 'mod_core_browser_source_dev_changeme');
GRANT CONNECT ON DATABASE waddlebot TO mod_core_browser_source;
GRANT USAGE ON SCHEMA public TO mod_core_browser_source;
GRANT SELECT ON servers, community_servers, communities TO mod_core_browser_source;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO mod_core_browser_source;

-- Identity Core
SELECT create_user_if_not_exists('mod_core_identity', 'mod_core_identity_dev_changeme');
GRANT CONNECT ON DATABASE waddlebot TO mod_core_identity;
GRANT USAGE ON SCHEMA public TO mod_core_identity;
GRANT SELECT ON servers, community_servers, communities TO mod_core_identity;
GRANT SELECT, INSERT, UPDATE ON hub_users, hub_user_identities TO mod_core_identity;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO mod_core_identity;

-- AI Researcher
SELECT create_user_if_not_exists('mod_core_ai_researcher', 'mod_core_ai_researcher_dev_changeme');
GRANT CONNECT ON DATABASE waddlebot TO mod_core_ai_researcher;
GRANT USAGE ON SCHEMA public TO mod_core_ai_researcher;
GRANT SELECT ON servers, community_servers, communities, modules TO mod_core_ai_researcher;
GRANT SELECT, INSERT, UPDATE ON ai_insights TO mod_core_ai_researcher;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO mod_core_ai_researcher;

-- Workflow Core
SELECT create_user_if_not_exists('mod_core_workflow', 'mod_core_workflow_dev_changeme');
GRANT CONNECT ON DATABASE waddlebot TO mod_core_workflow;
GRANT USAGE ON SCHEMA public TO mod_core_workflow;
GRANT SELECT ON servers, community_servers, communities, modules TO mod_core_workflow;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO mod_core_workflow;

-- Community Module
SELECT create_user_if_not_exists('mod_core_community', 'mod_core_community_dev_changeme');
GRANT CONNECT ON DATABASE waddlebot TO mod_core_community;
GRANT USAGE ON SCHEMA public TO mod_core_community;
GRANT SELECT, INSERT, UPDATE, DELETE ON communities, community_servers, community_members TO mod_core_community;
GRANT SELECT ON servers, modules TO mod_core_community;
GRANT SELECT (id, username, email, is_active) ON hub_users TO mod_core_community;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO mod_core_community;

-- Reputation Module
SELECT create_user_if_not_exists('mod_core_reputation', 'mod_core_reputation_dev_changeme');
GRANT CONNECT ON DATABASE waddlebot TO mod_core_reputation;
GRANT USAGE ON SCHEMA public TO mod_core_reputation;
GRANT SELECT ON servers, community_servers, communities TO mod_core_reputation;
GRANT SELECT (id, username, is_active) ON hub_users TO mod_core_reputation;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO mod_core_reputation;

-- Analytics Core
SELECT create_user_if_not_exists('mod_core_analytics', 'mod_core_analytics_dev_changeme');
GRANT CONNECT ON DATABASE waddlebot TO mod_core_analytics;
GRANT USAGE ON SCHEMA public TO mod_core_analytics;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO mod_core_analytics;
GRANT INSERT, UPDATE ON ai_insights TO mod_core_analytics;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO mod_core_analytics;

-- Security Core
SELECT create_user_if_not_exists('mod_core_security', 'mod_core_security_dev_changeme');
GRANT CONNECT ON DATABASE waddlebot TO mod_core_security;
GRANT USAGE ON SCHEMA public TO mod_core_security;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO mod_core_security;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO mod_core_security;

-- Video Proxy
SELECT create_user_if_not_exists('mod_core_video_proxy', 'mod_core_video_proxy_dev_changeme');
GRANT CONNECT ON DATABASE waddlebot TO mod_core_video_proxy;
GRANT USAGE ON SCHEMA public TO mod_core_video_proxy;
GRANT SELECT ON servers, community_servers, communities TO mod_core_video_proxy;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO mod_core_video_proxy;

-- Engagement Module
SELECT create_user_if_not_exists('mod_core_engagement', 'mod_core_engagement_dev_changeme');
GRANT CONNECT ON DATABASE waddlebot TO mod_core_engagement;
GRANT USAGE ON SCHEMA public TO mod_core_engagement;
GRANT SELECT ON servers, community_servers, communities TO mod_core_engagement;
GRANT SELECT (id, username, is_active) ON hub_users TO mod_core_engagement;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO mod_core_engagement;

-- Module RTC
SELECT create_user_if_not_exists('mod_core_rtc', 'mod_core_rtc_dev_changeme');
GRANT CONNECT ON DATABASE waddlebot TO mod_core_rtc;
GRANT USAGE ON SCHEMA public TO mod_core_rtc;
GRANT SELECT ON servers, community_servers, communities TO mod_core_rtc;
GRANT SELECT (id, username, is_active) ON hub_users TO mod_core_rtc;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO mod_core_rtc;

-- Credential Manager (needs full access to platform_integrations)
SELECT create_user_if_not_exists('mod_credential_manager', 'mod_credential_manager_dev_changeme');
GRANT CONNECT ON DATABASE waddlebot TO mod_credential_manager;
GRANT USAGE ON SCHEMA public TO mod_credential_manager;
GRANT SELECT, INSERT, UPDATE ON platform_integrations TO mod_credential_manager;
GRANT SELECT, INSERT ON credential_access_log TO mod_credential_manager;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO mod_credential_manager;

-- ============================================================================
-- CLEANUP: Drop the helper function (not needed at runtime)
-- ============================================================================
DROP FUNCTION IF EXISTS create_user_if_not_exists(TEXT, TEXT);
