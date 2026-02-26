-- Migration 049: Auth settings (CAPTCHA, passkeys, community join requests)
-- Adds defaults to hub_settings and new tables for passkeys + join requests

-- Add CAPTCHA and passkey config defaults to hub_settings
INSERT INTO hub_settings (setting_key, setting_value) VALUES
  ('captcha_provider', 'none'),
  ('captcha_site_key', ''),
  ('captcha_secret_key', ''),
  ('passkey_enabled', 'false'),
  ('community_join_review_enabled', 'false')
ON CONFLICT (setting_key) DO NOTHING;

-- Passkeys (WebAuthn credentials for existing users)
CREATE TABLE IF NOT EXISTS user_passkeys (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES hub_users(id) ON DELETE CASCADE,
    credential_id TEXT NOT NULL UNIQUE,
    public_key TEXT NOT NULL,
    sign_count INTEGER NOT NULL DEFAULT 0,
    device_name VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_used_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_user_passkeys_user_id ON user_passkeys(user_id);
CREATE INDEX IF NOT EXISTS idx_user_passkeys_credential_id ON user_passkeys(credential_id);

-- Community join requests (for approval-mode communities)
CREATE TABLE IF NOT EXISTS community_join_requests (
    id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES hub_users(id) ON DELETE CASCADE,
    status VARCHAR(20) DEFAULT 'pending',
    message TEXT,
    reviewed_by INTEGER REFERENCES hub_users(id),
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(community_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_join_requests_community ON community_join_requests(community_id, status);
CREATE INDEX IF NOT EXISTS idx_join_requests_user ON community_join_requests(user_id);
