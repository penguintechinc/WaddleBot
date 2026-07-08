-- Migration 068: Feature flag system
-- Adds scoped feature flags (global / per-community / per-platform) with
-- percentage-based rollout, plus an append-only audit trail of flag changes.

CREATE TABLE IF NOT EXISTS feature_flags (
  id SERIAL PRIMARY KEY,
  flag_key VARCHAR(100) NOT NULL,                 -- dot-namespaced, e.g. 'module.loyalty_interaction'
  community_id INTEGER REFERENCES communities(id) ON DELETE CASCADE,  -- NULL = global default
  platform VARCHAR(50),                           -- NULL = all platforms (e.g. 'twitch','discord','slack')
  is_enabled BOOLEAN NOT NULL DEFAULT false,
  rollout_pct SMALLINT NOT NULL DEFAULT 100 CHECK (rollout_pct BETWEEN 0 AND 100),
  description TEXT,
  updated_by VARCHAR(255),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE feature_flags IS 'Scoped feature flags with percentage rollout. Scope resolves most-specific-wins: (community + platform) > community > platform > global.';
COMMENT ON COLUMN feature_flags.flag_key IS 'Dot-namespaced flag identifier, e.g. ''module.loyalty_interaction''.';
COMMENT ON COLUMN feature_flags.community_id IS 'Owning community; NULL = global default (same convention as commands table).';
COMMENT ON COLUMN feature_flags.platform IS 'Platform scope; NULL = all platforms.';
COMMENT ON COLUMN feature_flags.rollout_pct IS 'Percentage of the scoped audience the flag is active for (0-100).';

-- Uniqueness across the nullable scope columns (flag_key + community + platform).
-- COALESCE sentinels let NULL community/platform participate in the unique constraint.
CREATE UNIQUE INDEX IF NOT EXISTS idx_feature_flags_scope
  ON feature_flags (flag_key, COALESCE(community_id, -1), COALESCE(platform, '*'));

-- Lookup index for flag resolution by key + community scope.
CREATE INDEX IF NOT EXISTS idx_feature_flags_lookup
  ON feature_flags (flag_key, community_id);

CREATE TABLE IF NOT EXISTS feature_flag_audit (
  id SERIAL PRIMARY KEY,
  flag_key VARCHAR(100) NOT NULL,
  community_id INTEGER,                            -- no FK: audit history is retained even if the community is deleted
  platform VARCHAR(50),
  action VARCHAR(20) NOT NULL,                     -- 'created', 'updated', 'deleted'
  old_value JSONB,
  new_value JSONB,
  changed_by VARCHAR(255),
  changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE feature_flag_audit IS 'Append-only audit trail of feature flag changes. Retained independently of feature_flags rows.';

-- Audit history lookup by flag, newest first.
CREATE INDEX IF NOT EXISTS idx_feature_flag_audit_flag_key
  ON feature_flag_audit (flag_key, changed_at);

-- Analyze
ANALYZE feature_flags;
