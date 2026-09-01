-- Migration 076: Metered token billing -- the third metering axis
-- (node/seat/token, critical-rules.md "Licensing Model: Nodes & Seats").
-- Premium metered consumables (e.g. AI routing calls) are sold as
-- pre-paid token packs (`token_products`); a community's balance
-- (`community_token_balances`) is decremented per unit of consumption via
-- an atomic, WHERE-guarded UPDATE (never a read-then-write check), with
-- every credit/debit recorded as an append-only ledger row
-- (`token_transactions`) -- same "the database, not application logic,
-- arbitrates the race" pattern as `hub_oauth_exchange_codes` (migration
-- 075) and `community_welcomed_users` (migration 068). See
-- hub_api/services/token_billing_service.py::debit_tokens.
--
-- Tenant isolation is enforced transitively via `community_id` ->
-- `communities.tenant_id` (the same pattern every other community-scoped
-- table in this schema already uses -- e.g. `inventory_items`,
-- `community_members`) plus `services/community_authz.py`'s
-- `authorize_community()` at the API layer, not a redundant `tenant_id`
-- column on every table here.

CREATE TABLE IF NOT EXISTS token_products (
    id SERIAL PRIMARY KEY,
    key VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    unit VARCHAR(50) NOT NULL DEFAULT 'token',
    price_cents INTEGER NOT NULL CHECK (price_cents >= 0),
    tokens_granted INTEGER NOT NULL CHECK (tokens_granted > 0),
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS community_token_balances (
    id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES token_products(id) ON DELETE RESTRICT,
    balance INTEGER NOT NULL DEFAULT 0 CHECK (balance >= 0),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (community_id, product_id)
);

-- Append-only ledger -- every credit (`delta` > 0) and debit (`delta` < 0)
-- gets one row here, including its resulting `balance_after`, so the
-- ledger alone can reconstruct the balance at any point in time
-- (standard double-entry-adjacent audit trail; no UPDATE/DELETE against
-- this table anywhere in the service layer).
CREATE TABLE IF NOT EXISTS token_transactions (
    id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES token_products(id) ON DELETE RESTRICT,
    delta INTEGER NOT NULL,
    reason VARCHAR(255) NOT NULL,
    ref VARCHAR(255),
    balance_after INTEGER NOT NULL CHECK (balance_after >= 0),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_community_token_balances_community
    ON community_token_balances (community_id);

CREATE INDEX IF NOT EXISTS idx_token_transactions_community_created
    ON token_transactions (community_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_token_transactions_community_product
    ON token_transactions (community_id, product_id, created_at DESC);
