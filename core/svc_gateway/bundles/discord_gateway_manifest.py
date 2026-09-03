"""The Discord gateway ingest bundle's manifest -- registered into svc-gateway's own in-process
`flask_core.app_registry.AppRegistry` at startup (`app.py`), NOT loaded from hub-api's
distribution HTTP endpoint the way `core/svc_ingest`'s stage-runner loads its bundles.

svc-gateway is platform-level (one Discord bot gateway connection serving
every community), so its fan-out (`fanout.py`) has to answer "which
bundles want a `discord.message` event" BEFORE it knows which single
(tenant, community) a stage-runner's own `RUNNER_TENANT_SLUG`/
`RUNNER_COMMUNITY_ID` env vars would scope it to -- it needs the full
in-memory manifest set (`flask_core.app_binding.resolve_apps`, per this
PR's own task spec), not one poll against one stage-runner's fixed scope.

`is_default=True` + no real `InstallationLookup` wiring (`fanout.py`'s
`_NullInstallationLookup`) is a deliberate, documented MVP scope choice:
`resolve_apps` falls back to the Feature's shipped default whenever the
lookup returns no rows, exactly like migration 071's `waddles.core.demo.
echo` bundle does for the ingest/process stage-runners. A real per-(tenant,
community) activation table for gateway-socket bundles is follow-up work,
same posture the rest of this PR documents for guild->community mapping.
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
            # Run by svc-ingest, NOT svc-gateway -- svc-gateway only fans
            # the raw event out onto this bundle's `:ingest` Valkey key
            # (`bundle_stream_key`); svc-ingest's own poll loop
            # (`core/svc_ingest/runner.py`) RPOPs it and calls this
            # entrypoint exactly like every other ingest bundle.
            "entrypoint": "bundles.discord_ingest:normalize",
            "consumes": ["discord.message"],
            "communication_model": "gateway_socket",
        }
    },
}


def register_default_bundles(registry: AppRegistry) -> AppManifest:
    """Load + register `DISCORD_GATEWAY_MANIFEST` into `registry`. Returns the parsed manifest."""
    return registry.load(DISCORD_GATEWAY_MANIFEST)
