-- Migration 063: Add name column to community_servers
-- Required for hub auto-provisioning in interactionController.js (ensureHubServer).
-- Provides a short internal label for server records (distinct from platform_server_name
-- which stores the originating platform's server name).

ALTER TABLE community_servers
    ADD COLUMN IF NOT EXISTS name VARCHAR(255);
