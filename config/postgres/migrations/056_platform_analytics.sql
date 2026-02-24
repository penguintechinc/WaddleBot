-- Migration 056: Platform Analytics
-- Creates platform-level reputation view and analytics snapshot table
-- Global community reputation = platform reputation (via SQL view, no data migration)

-- View: platform_user_reputation
-- Joins community_members (where community is_global = TRUE) with hub_users
-- to expose platform-level reputation without moving data
CREATE OR REPLACE VIEW platform_user_reputation AS
SELECT
    hu.id AS hub_user_id,
    hu.username AS display_name,
    hu.email,
    COALESCE(cm.reputation, 600) AS platform_reputation,
    cm.joined_at,
    hu.last_active_at,
    hu.created_at
FROM hub_users hu
LEFT JOIN community_members cm ON cm.hub_user_id = hu.id
LEFT JOIN communities c ON c.id = cm.community_id AND c.is_global = TRUE
WHERE hu.is_active = TRUE;

-- Table: platform_analytics_snapshots
-- Stores daily metric rollups for historical trend data that's expensive to compute live
CREATE TABLE IF NOT EXISTS platform_analytics_snapshots (
    id SERIAL PRIMARY KEY,
    metric_name VARCHAR(100) NOT NULL,
    metric_value NUMERIC NOT NULL DEFAULT 0,
    snapshot_date DATE NOT NULL DEFAULT CURRENT_DATE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(metric_name, snapshot_date)
);

CREATE INDEX IF NOT EXISTS idx_analytics_snapshots_date
    ON platform_analytics_snapshots(snapshot_date DESC);

CREATE INDEX IF NOT EXISTS idx_analytics_snapshots_metric
    ON platform_analytics_snapshots(metric_name, snapshot_date DESC);

-- Index on hub_users.created_at for efficient growth queries
CREATE INDEX IF NOT EXISTS idx_hub_users_created_at
    ON hub_users(created_at);

-- Index on hub_users.last_active_at for activity breakdown queries
CREATE INDEX IF NOT EXISTS idx_hub_users_last_active_at
    ON hub_users(last_active_at);
