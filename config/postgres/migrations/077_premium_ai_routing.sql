-- Migration 077: Premium-AI model-routing (free-local / premium-local-metered / BYOK)
-- Greenfield feature, no Node precedent -- see
-- docs/plans/2026-08-31-premium-ai-routing-design.md for the full design.
--
-- ai_model_config / ai_byok_keys back hub_api/services/ai_routing/config_service.py
-- (per-community tier choice + AES-256-GCM-encrypted-at-rest BYOK provider keys,
-- services/ai_routing/byok_crypto.py -- same primitive/pattern as
-- services/github_sync_service.py's token-at-rest encryption, never plaintext).
--
-- ai_token_balances / ai_token_transactions back hub_api/services/token_ledger.py's
-- debit_tokens() -- a minimal, real premium-AI-tokens ledger scoped to this PR.
-- Table names are deliberately distinct from the community_token_balances/
-- token_transactions names the parallel metered-token-billing spec
-- (docs/plans/2026-08-31-metered-token-billing-design.md) reserves for the
-- eventual multi-consumable ledger, so the two migrations never collide;
-- that follow-on PR is expected to reconcile/union the two ledgers.

CREATE TABLE IF NOT EXISTS ai_model_config (
    id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    preferred_tier VARCHAR(20) NOT NULL DEFAULT 'free'
        CHECK (preferred_tier IN ('free', 'premium', 'byok')),
    byok_provider VARCHAR(20)
        CHECK (byok_provider IS NULL OR byok_provider IN ('openai', 'anthropic')),
    on_insufficient_balance VARCHAR(20) NOT NULL DEFAULT 'fallback_free'
        CHECK (on_insufficient_balance IN ('block', 'fallback_free')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by_user_id INTEGER REFERENCES hub_users(id),
    UNIQUE (community_id)
);

CREATE TABLE IF NOT EXISTS ai_byok_keys (
    id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    provider VARCHAR(20) NOT NULL CHECK (provider IN ('openai', 'anthropic')),
    encrypted_key TEXT NOT NULL,  -- AES-256-GCM, base64(iv || ciphertext || tag) -- never plaintext
    key_last4 VARCHAR(8) NOT NULL,  -- masked display only, never the real key
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    rotated_at TIMESTAMPTZ,
    created_by_user_id INTEGER REFERENCES hub_users(id),
    UNIQUE (community_id, provider)
);

CREATE INDEX IF NOT EXISTS idx_ai_byok_keys_community_id
    ON ai_byok_keys (community_id);

CREATE TABLE IF NOT EXISTS ai_token_balances (
    id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    consumable_type VARCHAR(50) NOT NULL DEFAULT 'ai_premium_tokens',
    balance_tokens BIGINT NOT NULL DEFAULT 0,
    lifetime_consumed BIGINT NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (community_id, consumable_type)
);

CREATE TABLE IF NOT EXISTS ai_token_transactions (
    id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    consumable_type VARCHAR(50) NOT NULL,
    amount_tokens BIGINT NOT NULL,  -- signed: negative for a debit
    balance_after BIGINT NOT NULL,
    idempotency_key VARCHAR(255) NOT NULL UNIQUE,
    source_ref VARCHAR(255),
    actor_user_id INTEGER REFERENCES hub_users(id),
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Lookup by community (balance history / receipts).
CREATE INDEX IF NOT EXISTS idx_ai_token_transactions_community_id
    ON ai_token_transactions (community_id);
