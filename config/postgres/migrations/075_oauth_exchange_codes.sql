-- Migration 075: OAuth exchange codes (short-lived, single-use token handoff)
-- Fixes a HIGH-severity leak: the OAuth login callback used to redirect with
-- the session JWT directly in the URL query string (?token=...), which leaks
-- into proxy/access logs, browser history, and the Referer header of any
-- outbound request the callback page makes. The backend now mints an opaque,
-- high-entropy, single-use code instead and hands the real JWT back over the
-- POST /api/v1/auth/exchange response BODY. See
-- hub_api/blueprints/v1/auth.py::oauth_callback and
-- hub_api/services/oauth_service.py::create_oauth_exchange_code /
-- redeem_oauth_exchange_code.

CREATE TABLE IF NOT EXISTS hub_oauth_exchange_codes (
    id SERIAL PRIMARY KEY,
    code VARCHAR(255) NOT NULL UNIQUE,
    token TEXT NOT NULL,
    platform VARCHAR(50),
    used BOOLEAN DEFAULT FALSE,
    used_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Single-use claim: UPDATE ... WHERE code = ? AND used = FALSE AND
-- expires_at > NOW() is the atomic operation that makes a code single-use
-- even under concurrent exchange attempts -- the database, not application
-- logic, arbitrates the race (same pattern as community_welcomed_users in
-- migration 068).
CREATE INDEX IF NOT EXISTS idx_hub_oauth_exchange_codes_code
    ON hub_oauth_exchange_codes (code);

-- Supports a future cleanup job purging expired/used codes.
CREATE INDEX IF NOT EXISTS idx_hub_oauth_exchange_codes_expires
    ON hub_oauth_exchange_codes (expires_at);
