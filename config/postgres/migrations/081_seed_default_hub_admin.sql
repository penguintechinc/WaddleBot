-- Migration 081: Seed default hub admin user + default hub_settings/cookie
-- policy, migrated out of admin/hub_module/backend/src/index.js's
-- initializeDatabase(). That function is now skipped in every deployment
-- (docker-compose.yml/Helm set SKIP_DB_INIT=true) because it unconditionally
-- ran CREATE TABLE/INDEX/ALTER against tables it does not own -- most
-- notably `CREATE INDEX ... ON hub_chat_messages`, which 500s with
-- "must be owner of table hub_chat_messages" (hub_admin only owns
-- hub_users/hub_settings, granted by config/postgres/init.sql; every other
-- app table is owned by the migration-runner role that runs this file).
-- These SQL migrations already own the schema (as documented in
-- hub_api/PORTING.md's "the house pattern") -- so the one thing
-- initializeDatabase() did that SQL migrations don't yet cover, the
-- one-time dev/demo admin-user + default-settings seed, moves here instead
-- of being silently lost when SKIP_DB_INIT=true.
--
-- Uses pgcrypto's crypt(..., gen_salt('bf', 12)) to produce a real bcrypt
-- hash ($2a$/$2b$) -- interoperable with Node's `bcrypt` package
-- (admin/hub_module/backend/src/middleware/auth or similar calls
-- bcrypt.compare() against whatever is in password_hash; bcrypt's hash
-- format isn't implementation-specific).
--
-- Dev/demo bootstrap credential only (admin@localhost.local / admin123),
-- matching the exact account initializeDatabase() used to create -- not a
-- new credential, just relocated. NODE_ENV defaults to "development"
-- (docker-compose.yml) in every environment this migration currently runs
-- in; the login page itself doesn't pre-fill or display these values.

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

DO $$
DECLARE
    v_admin_id INTEGER;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM hub_users WHERE email = 'admin@localhost.local') THEN
        INSERT INTO hub_users (email, username, password_hash, is_super_admin, is_active, email_verified)
        VALUES (
            'admin@localhost.local',
            'admin@localhost.local',
            crypt('admin123', gen_salt('bf', 12)),
            true,
            true,
            true
        )
        RETURNING id INTO v_admin_id;
    END IF;
END
$$;

INSERT INTO hub_settings (setting_key, setting_value, updated_at) VALUES
    ('signup_enabled', 'true', NOW()),
    ('email_configured', 'false', NOW()),
    ('signup_allowed_domains', '', NOW()),
    ('require_email_verification', 'false', NOW()),
    ('storage_type', 'local', NOW())
ON CONFLICT (setting_key) DO NOTHING;

INSERT INTO cookie_policy_versions (version, content, changes_summary, is_active, effective_date)
SELECT
    '1.0.0',
    E'# Cookie Policy\n\n## What Are Cookies\nCookies are small text files stored on your device when you visit our website.\n\n## Types of Cookies We Use\n\n### Necessary Cookies (Required)\nThese cookies are essential for the website to function properly. They enable basic features like page navigation and access to secure areas.\n\n### Functional Cookies (Optional)\nThese cookies enable enhanced functionality and personalization, such as remembering your preferences and settings.\n\n### Analytics Cookies (Optional)\nThese cookies help us understand how visitors interact with our website by collecting and reporting information anonymously.\n\n### Marketing Cookies (Optional)\nThese cookies are used to track visitors across websites to display relevant advertisements.\n\n## Your Choices\nYou can manage your cookie preferences at any time through the cookie settings panel. Note that disabling certain cookies may affect website functionality.\n\n## Contact Us\nIf you have questions about our cookie policy, please contact us at privacy@waddlebot.io.',
    'Initial cookie policy',
    true,
    NOW()
WHERE NOT EXISTS (SELECT 1 FROM cookie_policy_versions);

COMMIT;
