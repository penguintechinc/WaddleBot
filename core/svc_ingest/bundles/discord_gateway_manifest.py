"""The Discord gateway ingest bundle's manifest.

Registered into svc-ingest's own in-process `flask_core.app_registry.
AppRegistry` at startup (`app.py`), separate from -- and NOT loaded via --
hub-api's distribution HTTP endpoint the way the poll-drain loop
(`runner.py`) loads its bundles.

The Discord gateway receiver (`receivers/discord_gateway.py`) is
platform-level (one Discord bot gateway connection serving every
community), so its fan-out (`fanout.py`) has to answer "which bundles
want a `discord.message` event" BEFORE it knows which single (tenant,
community) the poll-drain loop's own `RUNNER_TENANT_SLUG`/
`RUNNER_COMMUNITY_ID` env vars would scope it to -- it needs the full
in-memory manifest set (`flask_core.app_binding.resolve_apps`, per this
PR's own task spec), not one poll against one fixed scope.

`is_default=True` + no real `InstallationLookup` wiring (`fanout.py`'s
`_NullInstallationLookup`) is a deliberate, documented MVP scope choice:
`resolve_apps` falls back to the Feature's shipped default whenever the
lookup returns no rows, exactly like migration 071's `waddles.core.demo.
echo` bundle does for the ingest/process stage-runners. A real per-(tenant,
community) activation table for persistent-socket bundles is follow-up
work, same posture the rest of this PR documents for guild->community
mapping.

This manifest does NOT set `stages.ingest.communication_model` -- that
field is thirdparty-vendor-only (`webhook_push`/`rest_pull`,
`hub_api/services/marketplace_execution_service.py`), not a place to
classify a native/builtin bundle's own transport. The receiver's transport
shape (a persistent inbound socket) is declared in CODE instead --
`receivers/discord_gateway.py`'s `DiscordGatewayReceiver` subclasses
`transport_boundary.Transport` and sets `transport_type = TransportType.
SOCKET`, `direction = Direction.INBOUND` (placeholder for the shared
`waddle_transports` library, landing separately).
"""

from __future__ import annotations

from typing import Any

from flask_core.app_manifest import AppManifest
from flask_core.app_registry import AppRegistry

#: Raw manifest dict -- validated + parsed via `flask_core.app_manifest.
#: parse_manifest` at registration time, never constructed as an
#: `AppManifest` directly (see that module's own docstring on why).
DISCORD_GATEWAY_MANIFEST: dict[str, Any] = {
    "app_id": "waddles.bot.discord.gateway",
    "name": "Discord Gateway Ingest",
    "version": "1.0.0",
    "feature": "waddles.bot.discord",
    "module": "bot",
    "provider": "builtin",
    "is_default": True,
    "stages": {
        "ingest": {
            # Run by the poll-drain loop (runner.py), NOT the gateway
            # receiver directly -- the receiver only fans the raw event
            # out onto this bundle's `:ingest` Valkey key
            # (`bundle_stream_key`); `runner.py`'s own poll loop RPOPs it
            # and calls this entrypoint exactly like every other ingest
            # bundle.
            "entrypoint": "bundles.discord_ingest:normalize",
            "consumes": ["discord.message"],
        }
    },
}


def register_default_bundles(registry: AppRegistry) -> AppManifest:
    """Load + register `DISCORD_GATEWAY_MANIFEST` into `registry`. Returns the parsed manifest."""
    return registry.load(DISCORD_GATEWAY_MANIFEST)
