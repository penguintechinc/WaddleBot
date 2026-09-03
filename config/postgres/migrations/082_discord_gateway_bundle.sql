-- Migration 082: seed the Discord gateway ingest bundle (svc-gateway).
--
-- Proves the INGEST half of the Discord connector running through the new
-- 9-container/bundle model end to end: svc-gateway holds the real
-- persistent Discord bot gateway socket (platform-level, one connection
-- serving every community) and, on each inbound message, fans it out via
-- `flask_core.app_binding.resolve_apps` to every bundle whose ingest stage
-- `consumes` `"discord.message"` -- LPUSHing onto that bundle's own
-- `:ingest` Valkey key (`bundle_stream_key`). svc-gateway resolves that
-- fan-out against its OWN in-process registry (`core/svc_gateway/bundles/
-- discord_gateway_manifest.py`), not this table -- this row exists so
-- svc-ingest's stage-runner poll (`GET /api/v1/distribution/bundles?
-- stage=ingest`, `core/svc_ingest/runner.py`) ALSO discovers the same
-- bundle and runs its real `bundles.discord_ingest:normalize` entrypoint
-- against whatever svc-gateway LPUSHed -- same seed shape as migration
-- 071's `waddles.core.demo.echo` bundle, one more App added to the
-- catalog, not a schema change.
--
-- `stages.ingest` mirrors flask_core.app_manifest.StageSpec's field names
-- (071's own convention) plus this PR's two new fields --
-- `consumes`/`communication_model` -- so the in-process manifest
-- (`discord_gateway_manifest.py`'s `DISCORD_GATEWAY_MANIFEST`) and this DB
-- row describe the identical bundle, never two different vocabularies.
--
-- `is_default = TRUE` for `waddles.bot.discord` -- global tier only,
-- ON CONFLICT DO NOTHING keeps this idempotent across re-applies, same
-- posture as 071.
--
-- Encryption at rest: engine-level (PostgreSQL volume/TDE per security.md
-- Encryption -- Storage baseline). No column-level action needed here.

INSERT INTO app_catalog (
    app_id, manifest_version, module, feature, provider, execution_model,
    is_default, platform_compatibility, status, stages
) VALUES (
    'waddles.bot.discord.gateway',
    '1.0.0',
    'bot',
    'waddles.bot.discord',
    'builtin',
    'native',
    TRUE,
    '{"tested_with": "release/v3.0.X", "min_version": null, "max_version": null}'::jsonb,
    'active',
    (
        '{"ingest": {"entrypoint": "bundles.discord_ingest:normalize", "config": {}, ' ||
        '"spec": {}, "consumes": ["discord.message"], "communication_model": "gateway_socket"}}'
    )::jsonb
)
ON CONFLICT (app_id) DO NOTHING;
