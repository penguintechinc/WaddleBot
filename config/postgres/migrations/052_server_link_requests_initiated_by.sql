-- Migration 052: Add initiated_by to server_link_requests
--
-- Tracks whether a link request was initiated by a community admin (via WebUI)
-- or by a platform owner (via bot command like /join or !join). This is used
-- to display the correct badge in AdminServers.jsx and to route notifications
-- when the request is approved or rejected.
--
-- Also adds platform_channel_id for platforms (Twitch, Kick) that use channels
-- rather than guild/workspace as their primary container.

ALTER TABLE server_link_requests
    ADD COLUMN IF NOT EXISTS initiated_by VARCHAR(20) DEFAULT 'community'
        CHECK (initiated_by IN ('community', 'platform')),
    ADD COLUMN IF NOT EXISTS platform_channel_id VARCHAR(255),
    ADD COLUMN IF NOT EXISTS link_type VARCHAR(30) DEFAULT 'standard'
        CHECK (link_type IN ('standard', 'read_only', 'announcement_only')),
    ADD COLUMN IF NOT EXISTS initiator_platform_user_id VARCHAR(255),
    ADD COLUMN IF NOT EXISTS initiator_platform_username VARCHAR(255);

COMMENT ON COLUMN server_link_requests.initiated_by IS
    'Who started the link request: community=admin via WebUI, platform=server owner via bot command';
COMMENT ON COLUMN server_link_requests.platform_channel_id IS
    'For stream platforms (Twitch, Kick) where the channel is the primary entity, not the workspace';
COMMENT ON COLUMN server_link_requests.link_type IS
    'Type of link: standard (full interaction), read_only (events only), announcement_only (one-way push)';
COMMENT ON COLUMN server_link_requests.initiator_platform_user_id IS
    'Platform user ID of the person who initiated the request (used for DM notification on approval)';
COMMENT ON COLUMN server_link_requests.initiator_platform_username IS
    'Platform username of the initiator (display only)';

-- Index for looking up requests by platform server quickly (used by bot /link status command)
CREATE INDEX IF NOT EXISTS idx_slr_platform_server
    ON server_link_requests(platform, platform_server_id, status);
