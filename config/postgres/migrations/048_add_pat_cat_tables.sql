-- Migration 048: Personal Access Tokens (PAT) and Community Access Tokens (CAT)
--
-- PAT: "Be me, programmatically" — acts as the token owner user.
--   Token format: wdl_u_<random32>
--   Limit: one per user (enforced by UNIQUE constraint on user_id)
--
-- CAT: Service/integration accounts — acts as a community service principal.
--   Token format: wdl_c_<random32>
--   Limit: 5 (standard) / 10 (premium), enforced at application layer
--   Scopes must be explicitly granted (non-empty array required)

-- Personal Access Tokens
CREATE TABLE IF NOT EXISTS user_access_tokens (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES hub_users(id) ON DELETE CASCADE,
    name            VARCHAR(100) NOT NULL,
    -- SHA-256 hex of the plaintext token; plaintext is never stored
    token_hash      VARCHAR(64) NOT NULL UNIQUE,
    -- NULL = inherit the user's full permissions; or an explicit restrictive subset
    scope_ceiling   TEXT[],
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    last_used_at    TIMESTAMPTZ,
    expires_at      TIMESTAMPTZ,
    is_revoked      BOOLEAN NOT NULL DEFAULT FALSE,
    -- One PAT per user — enforces the "don't share / single credential" design
    UNIQUE (user_id)
);

CREATE INDEX IF NOT EXISTS idx_user_access_tokens_user_id
    ON user_access_tokens (user_id);
CREATE INDEX IF NOT EXISTS idx_user_access_tokens_token_hash
    ON user_access_tokens (token_hash);

-- Community Access Tokens
CREATE TABLE IF NOT EXISTS community_access_tokens (
    id                  SERIAL PRIMARY KEY,
    community_id        INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    created_by_user_id  INTEGER REFERENCES hub_users(id),
    name                VARCHAR(100) NOT NULL,
    token_hash          VARCHAR(64) NOT NULL UNIQUE,
    -- Required, non-empty — must explicitly grant each scope from permission_scopes catalog
    scopes              TEXT[] NOT NULL DEFAULT '{}',
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    last_used_at        TIMESTAMPTZ,
    expires_at          TIMESTAMPTZ,
    is_revoked          BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_community_access_tokens_community_id
    ON community_access_tokens (community_id);
CREATE INDEX IF NOT EXISTS idx_community_access_tokens_token_hash
    ON community_access_tokens (token_hash);
