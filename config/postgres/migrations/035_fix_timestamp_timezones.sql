-- Migration: Fix timezone-naive TIMESTAMP columns to TIMESTAMP WITH TIME ZONE
-- Issue: Python datetime.now(timezone.utc) creates timezone-aware datetimes,
--        but PostgreSQL TIMESTAMP columns are timezone-naive, causing comparison errors
-- Fix: Convert all timestamp columns to TIMESTAMPTZ (TIMESTAMP WITH TIME ZONE)

-- platform_integrations table
ALTER TABLE platform_integrations
    ALTER COLUMN expires_at TYPE TIMESTAMP WITH TIME ZONE USING expires_at AT TIME ZONE 'UTC';

ALTER TABLE platform_integrations
    ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE USING created_at AT TIME ZONE 'UTC';

ALTER TABLE platform_integrations
    ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE USING updated_at AT TIME ZONE 'UTC';

-- Verify the changes
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'platform_integrations'
  AND column_name IN ('expires_at', 'created_at', 'updated_at')
ORDER BY ordinal_position;
