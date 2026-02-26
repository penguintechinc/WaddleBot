-- Migration 051: Fix is_core flags — only identity and workflow are truly non-disableable
--
-- Migration 008 incorrectly marked loyalty, leaderboard, shoutout, browser_source,
-- translation, ai_insights, and analytics as is_core=TRUE. These are feature modules
-- that community admins should be able to disable. Only modules whose absence would
-- break authentication or internal orchestration are truly non-disableable.

DO $$
BEGIN
    -- Support both 'modules' and 'hub_modules' table names (schema may differ by deployment)
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'hub_modules') THEN
        -- First, make all modules disableable
        UPDATE hub_modules SET is_core = FALSE WHERE is_core = TRUE;

        -- Only these two are truly non-disableable
        UPDATE hub_modules SET is_core = TRUE
        WHERE name IN ('identity', 'workflow');

    ELSIF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'modules') THEN
        UPDATE modules SET is_core = FALSE WHERE is_core = TRUE;

        UPDATE modules SET is_core = TRUE
        WHERE name IN ('identity', 'workflow');
    END IF;
END $$;

-- Update the comment to reflect the new semantics
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'hub_modules' AND column_name = 'is_core'
    ) THEN
        COMMENT ON COLUMN hub_modules.is_core IS
            'TRUE only for modules that must never be disabled (identity, workflow). All other modules are community-disableable.';
    END IF;
END $$;
