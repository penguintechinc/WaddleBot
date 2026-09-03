-- Migration 082: seed the Discord gateway ingest bundle (svc-ingest).
--
-- Proves the INGEST half of the Discord connector running through the
-- 8-container/bundle model end to end: svc-ingest's Discord gateway
-- receiver (`core/svc_ingest/receivers/discord_gateway.py`) holds the real
-- persistent Discord bot gateway socket (platform-level, one connection
-- serving every community, lease-owned per `core/svc_ingest/socket_lease.
-- py` so scaling svc-ingest never opens a duplicate) and, on each inbound
-- message, fans it out via `flask_core.app_binding.resolve_apps` to every
-- bundle whose ingest stage `consumes` `"discord.message"` -- LPUSHing
-- onto that bundle's own `:ingest` Valkey key (`bundle_stream_key`). The
-- receiver resolves that fan-out against svc-ingest's OWN in-process
-- registry (`core/svc_ingest/bundles/discord_gateway_manifest.py`), not
-- this table -- this row exists so the SAME container's poll-drain loop
-- (`GET /api/v1/distribution/bundles?stage=ingest`, `core/svc_ingest/
-- runner.py`) ALSO discovers the bundle and runs its real
-- `bundles.discord_ingest:normalize` entrypoint against whatever the
-- receiver LPUSHed -- same seed shape as migration 071's `waddles.core.
-- demo.echo` bundle, one more App added to the catalog, not a schema
-- change.
--
-- `stages.ingest` mirrors flask_core.app_manifest.StageSpec's field names
-- (071's own convention) plus this PR's new `consumes` field -- so the
-- in-process manifest (`discord_gateway_manifest.py`'s
-- `DISCORD_GATEWAY_MANIFEST`) and this DB row describe the identical
-- bundle, never two different vocabularies. Deliberately no
-- `communication_model` here: that field is thirdparty-vendor-only
-- (`webhook_push`/`rest_pull`); this bundle's persistent-socket transport
-- shape is declared in CODE instead (`core/svc_ingest/receivers/
-- discord_gateway.py`'s `DiscordGatewayReceiver`, a `libs/waddle_transports`
-- `Transport` subclass -- `name="discord_gateway"`,
-- `directions={Direction.INBOUND}`).
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
        '"spec": {}, "consumes": ["discord.message"]}}'
    )::jsonb
)
ON CONFLICT (app_id) DO NOTHING;
