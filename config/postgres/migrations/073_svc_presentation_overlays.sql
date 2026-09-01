-- Migration 073: svc-presentation per-community overlay surfaces + config.
-- Backs core/svc_presentation/services/schema.py::bind_presentation_tables()
-- (own pydal DAL, own scoped DB account -- backend-database.md Per-Service
-- Database Accounts; this is NOT hub_api's schema -- svc-presentation is
-- its own container/DB grant, not appended to hub_api/services/schema.py).
--
-- `overlay_surfaces`: which surfaces (full_screen | media | crawler | music)
-- are enabled per community, plus per-surface styling/theme overrides.
-- `presentation_config`: per-community global theme/palette + the Music
-- Station on/off toggle and crawler scroll speed.
--
-- Encryption at rest: engine-level (PostgreSQL volume/TDE per security.md
-- Encryption -- Storage baseline). No column-level action needed -- no PII
-- (backend-database.md PII Tokenization: only community_id, an internal
-- integer FK, is stored here; no user-identifying data).

CREATE TABLE IF NOT EXISTS overlay_surfaces (
    id                SERIAL PRIMARY KEY,
    community_id      INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    surface           TEXT NOT NULL,              -- full_screen | media | crawler | music
    enabled           BOOLEAN DEFAULT TRUE,
    config            JSONB DEFAULT '{}',          -- per-surface styling/theme override
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    updated_at        TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(community_id, surface)
);

CREATE TABLE IF NOT EXISTS presentation_config (
    id                     SERIAL PRIMARY KEY,
    community_id           INTEGER NOT NULL UNIQUE REFERENCES communities(id) ON DELETE CASCADE,
    theme                  TEXT DEFAULT 'default',
    primary_color          TEXT,
    secondary_color        TEXT,
    font_family            TEXT,
    music_enabled          BOOLEAN DEFAULT TRUE,
    crawler_speed_seconds  INTEGER DEFAULT 30,
    config                 JSONB DEFAULT '{}',
    created_at             TIMESTAMPTZ DEFAULT NOW(),
    updated_at             TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_overlay_surfaces_community
    ON overlay_surfaces (community_id);
