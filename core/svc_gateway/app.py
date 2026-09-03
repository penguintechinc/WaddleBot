"""svc-gateway -- Quart control-plane holding svc-gateway's persistent inbound sockets.

The 9th pipeline container: unlike svc-ingest/svc-process (short-lived
poll-drain-normalize cycles, `flask_core.stage_runner.BundlePoller`),
svc-gateway's job is holding PLATFORM-level, long-lived socket connections
(one Discord bot gateway connection serving every community today, more
platforms later) as supervised background tasks
(`supervisor.ReceiverSupervisor`) and fanning each inbound event out to
every bundle that wants it (`fanout.fan_out_event`, `flask_core.
app_binding.resolve_apps`-based routing -- see that module's own docstring
for why this does NOT go through hub-api's distribution HTTP endpoint the
way svc-ingest/svc-process do). `/health`/`/healthz`/`/metrics` come from
`flask_core`'s standard health blueprint, same as every other pipeline-
stage container.
"""

from __future__ import annotations

import asyncio

import redis.asyncio as redis
from flask_core import create_health_blueprint, install_security_headers, setup_aaa_logging
from flask_core.app_registry import AppRegistry
from quart import Quart

from bundles.discord_gateway_manifest import register_default_bundles
from config import Config
from receivers.discord_gateway import DiscordGatewayReceiver
from supervisor import ReceiverSupervisor

app = Quart(__name__)
# security.md A05 hardening -- JSON-only service, default deny-everything CSP.
install_security_headers(app)

health_bp = create_health_blueprint(Config.MODULE_NAME, Config.MODULE_VERSION)
app.register_blueprint(health_bp)

logger = setup_aaa_logging(Config.MODULE_NAME, Config.MODULE_VERSION)


@app.before_serving
async def startup() -> None:
    """Wire the Valkey client, this process's own AppRegistry, and start supervised receivers."""
    redis_client = redis.from_url(Config.VALKEY_URL, encoding="utf-8", decode_responses=True)

    registry = AppRegistry()
    register_default_bundles(registry)

    supervisor = ReceiverSupervisor(
        base_backoff_s=Config.BASE_BACKOFF_S, max_backoff_s=Config.MAX_BACKOFF_S
    )

    app.config["redis_client"] = redis_client
    app.config["registry"] = registry
    app.config["supervisor"] = supervisor

    if Config.DISCORD_BOT_TOKEN:
        receiver = DiscordGatewayReceiver(
            token=Config.DISCORD_BOT_TOKEN,
            redis_client=redis_client,
            registry=registry,
            tenant_slug=Config.RUNNER_TENANT_SLUG,
        )
        app.config["discord_receiver"] = receiver
        supervisor.register("discord_gateway", receiver.run)
        logger.system("svc-gateway starting Discord gateway receiver", action="startup")
    else:
        logger.system(
            "svc-gateway starting with no receivers -- DISCORD_BOT_TOKEN not configured",
            action="startup",
            result="SKIPPED",
        )

    await supervisor.start()
    logger.system("svc-gateway started", action="startup", result="SUCCESS")


@app.after_serving
async def shutdown() -> None:
    """Stop every supervised receiver and close the Valkey client -- must never raise."""
    supervisor = app.config.get("supervisor")
    if supervisor is not None:
        await supervisor.stop()

    receiver = app.config.get("discord_receiver")
    if receiver is not None:
        await receiver.stop()

    redis_client = app.config.get("redis_client")
    if redis_client is not None:
        await redis_client.aclose()
    logger.system("svc-gateway shutdown complete", action="shutdown", result="SUCCESS")


if __name__ == "__main__":  # pragma: no cover - process entrypoint, not exercised by unit tests
    import hypercorn.asyncio
    from hypercorn.config import Config as HyperConfig

    hyper_config = HyperConfig()
    hyper_config.bind = [f"0.0.0.0:{Config.MODULE_PORT}"]
    asyncio.run(hypercorn.asyncio.serve(app, hyper_config))
