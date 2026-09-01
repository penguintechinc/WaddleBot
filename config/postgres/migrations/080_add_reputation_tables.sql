-- Migration 080: Reputation event log + global reputation score
-- reputation_events and reputation_global are read/written by
-- core/reputation_module/services/reputation_service.py (get_reputation,
-- get_global_reputation, adjust, _update_global_reputation, set_reputation,
-- get_history, get_leaderboard, get_global_leaderboard) and
-- core/reputation_module/services/policy_enforcer.py (_execute_auto_ban,
-- _notify_low_score) but were never given a CREATE TABLE migration -- every
-- read/write against them fails at runtime. This adds both tables matching
-- the columns those call sites actually reference.
--
-- reputation_global is the per-user, cross-community FICO-style score
-- (Config.REPUTATION_DEFAULT/MIN/MAX = 600/300/850, see
-- core/reputation_module/config.py); reputation_events is the append-only
-- audit trail of every scoring event feeding both the per-community history
-- (community_members.reputation, unaffected by this migration) and the
-- global score.

BEGIN;

CREATE TABLE IF NOT EXISTS reputation_events (
    id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    hub_user_id INTEGER REFERENCES hub_users(id) ON DELETE SET NULL,
    platform VARCHAR(50) NOT NULL,
    platform_user_id VARCHAR(255) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    score_change DECIMAL(10,4) NOT NULL DEFAULT 0,
    score_before INTEGER NOT NULL,
    score_after INTEGER NOT NULL,
    reason TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- get_reputation()/get_history(): COUNT(*)/MAX(created_at)/history list
-- scoped by (community_id, hub_user_id), newest first.
CREATE INDEX IF NOT EXISTS idx_reputation_events_community_user
    ON reputation_events(community_id, hub_user_id, created_at DESC);

-- policy_enforcer._notify_low_score(): spam-guard lookup by
-- (community_id, hub_user_id, event_type, created_at).
CREATE INDEX IF NOT EXISTS idx_reputation_events_user_event_type
    ON reputation_events(community_id, hub_user_id, event_type, created_at DESC);

-- No CHECK on score: ReputationService._update_global_reputation()'s
-- INSERT ... ON CONFLICT DO UPDATE passes the raw (unclamped)
-- REPUTATION_DEFAULT + score_change as the candidate row's score; Postgres
-- validates CHECK constraints against that candidate row before the
-- ON CONFLICT branch's own LEAST/GREATEST clamp ever runs, so a CHECK here
-- would reject legitimate large-swing events (e.g. a big donation) that the
-- UPDATE path would otherwise clamp correctly. Same reasoning
-- community_members.reputation already follows (000_create_base_schema.sql)
-- -- bounds are enforced in application code
-- (ReputationService._clamp_score()/the upsert's own LEAST/GREATEST), not
-- the schema. tier is intentionally omitted: it is never stored, only
-- computed on read from score via ReputationService._get_tier().
CREATE TABLE IF NOT EXISTS reputation_global (
    hub_user_id INTEGER PRIMARY KEY REFERENCES hub_users(id) ON DELETE CASCADE,
    score INTEGER NOT NULL DEFAULT 600,
    total_events INTEGER NOT NULL DEFAULT 0,
    last_event_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- get_global_leaderboard(): RANK() OVER (ORDER BY score DESC).
CREATE INDEX IF NOT EXISTS idx_reputation_global_score
    ON reputation_global(score DESC);

-- Reputation Module (mod_core_reputation, see 031_scoped_database_users.sql)
-- reads/writes both new tables: reputation_events is an append-only audit
-- log (SELECT/INSERT only, never UPDATE/DELETE); reputation_global is
-- upserted via INSERT ... ON CONFLICT DO UPDATE (needs UPDATE too).
--
-- Guarded by a role-existence check rather than a bare GRANT: on a fresh DB
-- bootstrapped via alembic/versions/0001_baseline_from_sql_migrations.py,
-- 031_scoped_database_users.sql currently fails before it reaches the
-- mod_core_reputation CREATE ROLE statement (pre-existing, unrelated --
-- module_configs referenced at that file's mod_router GRANT has no
-- CREATE TABLE migration of its own). Since the baseline runner executes
-- each migration file as a single savepoint-scoped statement block, an
-- unguarded GRANT to a not-yet-created role would abort and roll back this
-- entire file -- including the CREATE TABLEs above. Skipping gracefully
-- here (like the baseline runner already does for other legacy ordering
-- gaps) keeps table creation independent of that separate bug; a re-run
-- once 031 is fixed picks up the grant normally since GRANT is idempotent
-- and this file is safe to apply again.
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'mod_core_reputation') THEN
        GRANT SELECT, INSERT ON reputation_events TO mod_core_reputation;
        GRANT SELECT, INSERT, UPDATE ON reputation_global TO mod_core_reputation;
        GRANT USAGE ON SEQUENCE reputation_events_id_seq TO mod_core_reputation;
    END IF;
END
$$;

COMMIT;
