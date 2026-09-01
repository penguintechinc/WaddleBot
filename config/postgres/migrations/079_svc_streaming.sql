-- Migration 079: svc-streaming's own control-plane tables + the
-- transcoding-token catalog seed.
--
-- Per-community stream configuration (`streaming_configs`), its forward
-- targets (`streaming_targets`), and a real session history
-- (`streaming_sessions`) for the Streaming module's control plane +
-- ffmpeg data plane (docs/plans/2026-08-31-svc-streaming-design.md).
-- `core/svc_streaming` owns these tables outright (its own per-service DB
-- account, backend-database.md Per-Service Database Accounts) -- separate
-- from the legacy `video_proxy_module`'s own `stream_configurations`/
-- `stream_destinations` (core/video_proxy_module/services/database.py,
-- fronted by hub-api's `/api/v1/admin/<id>/streams/*` reverse-proxy) which
-- remain untouched; absorbing that legacy path is staged/future work
-- (design spec §6).
--
-- Tenant isolation is enforced transitively via `community_id` ->
-- `communities.tenant_id`, same pattern migration 076 (token billing)
-- documents, plus `services/community_access.py`'s authz checks at the
-- API layer.

CREATE TABLE IF NOT EXISTS streaming_configs (
    id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL UNIQUE REFERENCES communities(id) ON DELETE CASCADE,
    source_url VARCHAR(1024) NOT NULL,
    source_type VARCHAR(20) NOT NULL DEFAULT 'rtmp' CHECK (source_type IN ('rtmp', 'hls')),
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    record_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    transcode_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    transcode_bitrate_kbps INTEGER NOT NULL DEFAULT 4000 CHECK (transcode_bitrate_kbps > 0),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS streaming_targets (
    id SERIAL PRIMARY KEY,
    config_id INTEGER NOT NULL REFERENCES streaming_configs(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,
    forward_url VARCHAR(1024) NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Real session history -- one row per start/stop lifecycle, including
-- whether TRANSCODE was actually admitted (`transcode_applied`) or the
-- job fell back to passthrough (`fallback_reason`, e.g.
-- 'insufficient_balance'/'ledger_unavailable' -- see
-- hub_api/services/streaming_service.py's BLOCK-WITH-FALLBACK admission
-- logic, `services/token_ledger_client.py`).
CREATE TABLE IF NOT EXISTS streaming_sessions (
    id SERIAL PRIMARY KEY,
    config_id INTEGER NOT NULL REFERENCES streaming_configs(id) ON DELETE CASCADE,
    pid INTEGER,
    status VARCHAR(20) NOT NULL DEFAULT 'stopped' CHECK (status IN ('running', 'stopped', 'failed')),
    transcode_applied BOOLEAN NOT NULL DEFAULT FALSE,
    fallback_reason VARCHAR(100),
    started_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_streaming_targets_config
    ON streaming_targets (config_id);

CREATE INDEX IF NOT EXISTS idx_streaming_sessions_config
    ON streaming_sessions (config_id);

CREATE INDEX IF NOT EXISTS idx_streaming_sessions_config_status
    ON streaming_sessions (config_id, status);

-- Seed the transcoding token product -- svc-streaming's TRANSCODE
-- admission (services/token_ledger_client.py) debits against this real
-- catalog entry via hub-api's real ledger
-- (hub_api/services/token_billing_service.py, migration 076's
-- token_products/community_token_balances/token_transactions). Pricing
-- here is a real, usable starting point for tonight's demo, not a final
-- number -- hub-api/marketplace owns pricing per that module's own
-- docstring (design spec §5).
INSERT INTO token_products (key, name, unit, price_cents, tokens_granted, active)
VALUES ('transcoding_minutes', 'Transcoding Minutes', 'minute', 100, 60, true)
ON CONFLICT (key) DO NOTHING;
