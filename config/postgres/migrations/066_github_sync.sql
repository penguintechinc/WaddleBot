-- Migration 066: Bidirectional GitHub Issues sync for support tickets
-- Allows community admins and vendors to connect GitHub repos to the support
-- ticket system, syncing tickets as GitHub Issues and receiving inbound events
-- via webhooks.

CREATE TABLE IF NOT EXISTS github_repo_connections (
  id SERIAL PRIMARY KEY,
  community_id INTEGER REFERENCES communities(id) ON DELETE CASCADE,
  vendor_id INTEGER REFERENCES hub_users(id),  -- vendor-level connection (NULL if community-level)
  module_id INTEGER REFERENCES approved_vendor_modules(id),  -- linked module (optional)
  repo_owner VARCHAR(255) NOT NULL,
  repo_name VARCHAR(255) NOT NULL,
  sync_mode VARCHAR(30) NOT NULL DEFAULT 'tickets_only' CHECK (sync_mode IN ('tickets_only', 'tickets_and_discussions', 'off')),
  default_labels TEXT[] DEFAULT ARRAY['waddles', 'support'],
  auto_close_on_github_close BOOLEAN DEFAULT true,
  auth_type VARCHAR(20) NOT NULL CHECK (auth_type IN ('github_app', 'pat')),
  encrypted_token TEXT NOT NULL,  -- AES-256-GCM encrypted PAT or app installation token
  webhook_secret VARCHAR(255) NOT NULL,
  installation_id VARCHAR(255),  -- GitHub App installation ID
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(community_id, repo_owner, repo_name),
  UNIQUE(vendor_id, repo_owner, repo_name)
);

-- Lookup by community
CREATE INDEX IF NOT EXISTS idx_github_repo_connections_community_id
  ON github_repo_connections (community_id);

-- Lookup by vendor
CREATE INDEX IF NOT EXISTS idx_github_repo_connections_vendor_id
  ON github_repo_connections (vendor_id);

-- Lookup active connections
CREATE INDEX IF NOT EXISTS idx_github_repo_connections_active
  ON github_repo_connections (is_active);

-- Lookup by repo owner + name (for inbound webhooks)
CREATE INDEX IF NOT EXISTS idx_github_repo_connections_repo
  ON github_repo_connections (repo_owner, repo_name);

CREATE TABLE IF NOT EXISTS ticket_github_sync (
  id SERIAL PRIMARY KEY,
  ticket_id INTEGER NOT NULL,  -- references support_tickets(id)
  github_repo_connection_id INTEGER NOT NULL REFERENCES github_repo_connections(id) ON DELETE CASCADE,
  github_issue_number INTEGER NOT NULL,
  github_issue_node_id VARCHAR(255),
  sync_status VARCHAR(30) DEFAULT 'synced' CHECK (sync_status IN ('synced', 'pending', 'failed', 'conflict')),
  last_synced_at TIMESTAMPTZ DEFAULT NOW(),
  last_error TEXT,
  retry_count INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Lookup by ticket
CREATE INDEX IF NOT EXISTS idx_ticket_github_sync_ticket_id
  ON ticket_github_sync (ticket_id);

-- Lookup by connection
CREATE INDEX IF NOT EXISTS idx_ticket_github_sync_connection_id
  ON ticket_github_sync (github_repo_connection_id);

-- Lookup failed syncs for retry job
CREATE INDEX IF NOT EXISTS idx_ticket_github_sync_failed
  ON ticket_github_sync (sync_status, retry_count)
  WHERE sync_status = 'failed';

-- Lookup by github issue number within a connection
CREATE INDEX IF NOT EXISTS idx_ticket_github_sync_issue
  ON ticket_github_sync (github_repo_connection_id, github_issue_number);

CREATE TABLE IF NOT EXISTS github_sync_log (
  id SERIAL PRIMARY KEY,
  ticket_github_sync_id INTEGER REFERENCES ticket_github_sync(id),
  direction VARCHAR(10) NOT NULL CHECK (direction IN ('outbound', 'inbound')),
  event_type VARCHAR(50) NOT NULL,
  payload JSONB,
  success BOOLEAN NOT NULL,
  error_message TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Lookup logs by sync record
CREATE INDEX IF NOT EXISTS idx_github_sync_log_sync_id
  ON github_sync_log (ticket_github_sync_id);

-- Lookup recent failures for alerting
CREATE INDEX IF NOT EXISTS idx_github_sync_log_failures
  ON github_sync_log (created_at DESC)
  WHERE success = false;
