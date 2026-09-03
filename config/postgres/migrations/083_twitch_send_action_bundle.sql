-- Migration 083: seed the Twitch chat-send ACTION bundle (svc-action).
--
-- Proof-of-work port of the Twitch connector's OUTBOUND half into the
-- App Bundle SDK's action-stage script-entrypoint model
-- (`core/svc_action/services/adapters/bundle.py`, same bundle-script
-- dispatch mechanism the Discord action bundle uses on the parallel,
-- not-yet-merged `feature/v3-bundle-discord-action` branch --
-- `stages.action.entrypoint` follows the exact `bundles.<module>:
-- <function>` convention migration 071's demo echo bundles established
-- for ingest/process: `bundles.twitch_send_action:send_message`
-- (core/svc_action/bundles/twitch_send_action.py).
--
-- Per the 2026-09-02 transport-unification coordination note (see
-- `libs/waddle_transports/waddle_transports/irc.py`), this bundle's own
-- `send_message()` does NOT call an HTTP API -- it relays the chat send
-- through Valkey to svc-ingest's own live Twitch IRC connection
-- (`waddle_transports.irc.RelayOutboundIrcTransport`), the OUTBOUND half
-- of the same `irc` transport whose INBOUND half migration 082 seeds.
-- `stages.action.config` therefore carries only `channel` (the Twitch
-- channel name svc-ingest's receiver has joined) -- no secret/token
-- config at all, unlike Discord's bot-token-ref shape, since this
-- connector's demo scope has no second, independently-authenticated
-- connection to secure.
--
-- Encryption at rest: engine-level (security.md Storage baseline). No
-- column-level action needed here.

INSERT INTO app_catalog (
    app_id, manifest_version, module, feature, provider, execution_model,
    is_default, platform_compatibility, status, stages
) VALUES (
    'waddles.bot.twitch.default',
    '1.0.0',
    'bot',
    'waddles.bot.twitch',
    'builtin',
    'native',
    FALSE,
    '{"tested_with": "release/v3.0.X", "min_version": null, "max_version": null}'::jsonb,
    'active',
    (
        '{"action": {"entrypoint": "bundles.twitch_send_action:send_message", ' ||
        '"config": {"channel": "waddlebot"}, "spec": {"required_config": ["channel"]}}}'
    )::jsonb
)
ON CONFLICT (app_id) DO NOTHING;
