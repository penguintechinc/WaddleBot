-- Seed Script: Create Default Admin User
-- Run this after init.sql and migrations to create the default admin account
--
-- Default credentials:
--   Email: admin@localhost.net
--   Password: admin123
--
-- IMPORTANT: Change these credentials in production!

-- =============================================================================
-- Create Default Admin User
-- =============================================================================
-- Password hash is bcrypt hash of 'admin123' with cost factor 12
-- You can generate a new hash with: node -e "require('bcrypt').hash('yourpassword', 12).then(console.log)"

INSERT INTO hub_users (
    email,
    username,
    password_hash,
    is_active,
    is_super_admin,
    email_verified,
    created_at,
    updated_at
) VALUES (
    'admin@localhost.net',
    'admin',
    '$2b$12$4bHCtATjQNY//n42FMy/P.Uieygqwj.Hh5FbuPJJweqXcZbaTSK0u',
    true,
    true,
    true,
    NOW(),
    NOW()
) ON CONFLICT (email) DO UPDATE SET
    password_hash = EXCLUDED.password_hash,
    is_super_admin = true,
    is_active = true,
    email_verified = true,
    updated_at = NOW();

-- =============================================================================
-- Create Global Community (if not exists)
-- =============================================================================
INSERT INTO communities (
    name,
    display_name,
    description,
    is_public,
    is_active,
    is_global,
    platform,
    member_count,
    created_at
) VALUES (
    'waddlebot-global',
    'Waddles Global',
    'Global community for cross-community reputation tracking. All users are automatically members.',
    true,
    true,
    true,
    'global',
    1,
    NOW()
) ON CONFLICT (name) DO UPDATE SET
    is_global = true,
    is_active = true;

-- =============================================================================
-- Add Admin to Global Community
-- =============================================================================
INSERT INTO community_members (
    community_id,
    user_id,
    role,
    is_active,
    joined_at
)
SELECT
    c.id,
    u.id,
    'admin',
    true,
    NOW()
FROM hub_users u
CROSS JOIN communities c
WHERE u.email = 'admin@localhost.net'
  AND c.name = 'waddlebot-global'
ON CONFLICT (community_id, user_id) DO UPDATE SET
    role = 'admin',
    is_active = true;

-- =============================================================================
-- Update Global Community Member Count
-- =============================================================================
UPDATE communities
SET member_count = (
    SELECT COUNT(*)
    FROM community_members
    WHERE community_id = communities.id AND is_active = true
)
WHERE name = 'waddlebot-global';

-- =============================================================================
-- Verify Admin User Created
-- =============================================================================
DO $$
DECLARE
    admin_id INTEGER;
BEGIN
    SELECT id INTO admin_id FROM hub_users WHERE email = 'admin@localhost.net';
    IF admin_id IS NULL THEN
        RAISE EXCEPTION 'Failed to create admin user';
    ELSE
        RAISE NOTICE 'Admin user created successfully with ID: %', admin_id;
    END IF;
END $$;

-- Seed Complete
