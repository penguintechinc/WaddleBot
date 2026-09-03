-- Migration 082: seed the Twitch chat + EventSub ingest bundles (svc-ingest).
--
-- Proves the INGEST half of the Twitch connector running through the
-- 8-container/bundle model end to end: svc-ingest's Twitch IRC receiver
-- (`core/svc_ingest/receivers/twitch_irc.py`) holds the real, persistent
-- twitchio IRC chat connection (platform-level, one connection serving
-- every joined channel, lease-owned per `core/svc_ingest/socket_lease.py`
-- so scaling svc-ingest never opens a duplicate) and, on each inbound
-- chat message, fans it out via `flask_core.app_binding.resolve_apps` to
-- every bundle whose ingest stage `consumes` `"twitch.message"` --
-- LPUSHing onto that bundle's own `:ingest` Valkey key
-- (`bundle_stream_key`). Alongside it, `core/svc_ingest/eventsub.py`'s
-- `POST /eventsub/twitch/webhook` handler is a genuine inbound HTTP push
-- (not a persistent socket) that fans a normalized EventSub notification
-- out the same way, tagged `"twitch.eventsub"`.
--
-- Both receivers resolve their fan-out against svc-ingest's OWN
-- in-process registry (`core/svc_ingest/bundles/twitch_gateway_manifest.
-- py`), not this table -- these rows exist so the SAME container's
-- poll-drain loop (`GET /api/v1/distribution/bundles?stage=ingest`,
-- `core/svc_ingest/runner.py`) ALSO discovers each bundle and runs its
-- real `normalize()` entrypoint against whatever the receiver LPUSHed --
-- same seed shape as migration 071's `waddles.core.demo.echo` bundle
-- (and migration 082's Discord gateway bundle on the parallel
-- `feature/v3-svc-gateway-discord` branch, not yet merged as of this
-- migration -- see that branch's own 082 file; migration-number
-- coordination is a known follow-up once both land), one more pair of
-- Apps added to the catalog, not a schema change.
--
-- `stages.ingest` mirrors flask_core.app_manifest.StageSpec's field names
-- (071's own convention) plus `consumes`/`communication_model` so the
-- in-process manifest (`twitch_gateway_manifest.py`'s
-- `TWITCH_GATEWAY_MANIFEST`/`TWITCH_EVENTSUB_MANIFEST`) and these DB rows
-- describe the identical bundles, never two different vocabularies.
--
-- `is_default = TRUE` for both -- each is the sole App under its own
-- Feature (`waddles.bot.twitch` / `waddles.bot.twitchevents`), so there
-- is no default-collision the way there would be if both shared one
-- Feature (see `twitch_gateway_manifest.py`'s own docstring for why two
-- Features, not two Apps under one -- and why `feature` must stay a
-- single token per `flask_core.app_manifest`'s `_FEATURE_RE`).
-- ON CONFLICT DO NOTHING keeps this idempotent across re-applies, same
-- posture as 071.
--
-- Encryption at rest: engine-level (PostgreSQL volume/TDE per security.md
-- Encryption -- Storage baseline). No column-level action needed here.

INSERT INTO app_catalog (
    app_id, manifest_version, module, feature, provider, execution_model,
    is_default, platform_compatibility, status, stages
) VALUES (
    'waddles.bot.twitch.gateway',
    '1.0.0',
    'bot',
    'waddles.bot.twitch',
    'builtin',
    'native',
    TRUE,
    '{"tested_with": "release/v3.0.X", "min_version": null, "max_version": null}'::jsonb,
    'active',
    (
        '{"ingest": {"entrypoint": "bundles.twitch_ingest:normalize", "config": {}, ' ||
        '"spec": {}, "consumes": ["twitch.message"], "communication_model": "gateway_socket"}}'
    )::jsonb
)
ON CONFLICT (app_id) DO NOTHING;

INSERT INTO app_catalog (
    app_id, manifest_version, module, feature, provider, execution_model,
    is_default, platform_compatibility, status, stages
) VALUES (
    'waddles.bot.twitchevents.eventsub',
    '1.0.0',
    'bot',
    'waddles.bot.twitchevents',
    'builtin',
    'native',
    TRUE,
    '{"tested_with": "release/v3.0.X", "min_version": null, "max_version": null}'::jsonb,
    'active',
    (
        '{"ingest": {"entrypoint": "bundles.twitch_eventsub_ingest:normalize", "config": {}, ' ||
        '"spec": {}, "consumes": ["twitch.eventsub"], "communication_model": "webhook_push"}}'
    )::jsonb
)
ON CONFLICT (app_id) DO NOTHING;
