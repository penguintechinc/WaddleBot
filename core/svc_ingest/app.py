"""svc-ingest -- Quart control-plane + background stage-runner loop + supervised socket receivers.

Real async loop (`runner.IngestRunner`, started in `@app.before_serving`):
polls hub-api's distribution endpoint for the `ingest` stage's active
bundles (`flask_core.stage_runner.BundlePoller` -- interval + exponential
backoff on failure, graceful-degrade to the last-known bundle set, never
crashes on a hub-api outage), RPOPs each bundle's raw inbound events off
its own Valkey `:ingest` key, runs the bundle's real `normalize()`
entrypoint, and LPUSHes the normalized result onto that bundle's `:process`
key as a JSON envelope. `/health`/`/healthz`/`/metrics` come from
`flask_core`'s standard health blueprint, same as every other pipeline-
stage container (`core/svc_streaming/app.py`).

Alongside that poll-drain loop, svc-ingest ALSO runs any registered
platform-level socket receivers (`receivers/discord_gateway.py` today) as
`supervisor.ReceiverSupervisor`-supervised tasks -- 8-container decision:
these receivers were briefly a standalone `svc-gateway` 9th container,
folded back into svc-ingest since a Discord bot connection is exactly the
same "hold a persistent inbound socket, normalize, feed the pipeline"
shape this container already owns. Each receiver is guarded by a
`socket_lease.SocketLease` (`waddles:socket-owner:{provider}:{community}`,
Valkey `SET NX PX`) so scaling `pipeline.svcIngest.replicas` never opens
duplicate sockets for the same `(provider, community)` -- see
`socket_lease.py`'s own module docstring for the full design.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import cast

import httpx
import redis.asyncio as redis
from flask_core import create_health_blueprint, install_security_headers, setup_aaa_logging
from flask_core.app_registry import AppRegistry
from flask_core.auth import create_jwt_token
from flask_core.stage_runner import BundlePoller
from quart import Quart

from bundles.discord_gateway_manifest import register_default_bundles
from config import Config
from receivers.discord_gateway import DiscordGatewayReceiver
from runner import IngestRunner
from socket_lease import PLATFORM_COMMUNITY, LeasedReceiver
from supervisor import ReceiverSupervisor

app = Quart(__name__)
# security.md A05 hardening -- JSON-only service, default deny-everything CSP.
install_security_headers(app)

health_bp = create_health_blueprint(Config.MODULE_NAME, Config.MODULE_VERSION)
app.register_blueprint(health_bp)

logger = setup_aaa_logging(Config.MODULE_NAME, Config.MODULE_VERSION)


def _jwt_provider() -> str:
    """Mint a fresh 1h service JWT for this runner's own tenant scope.

    Minted fresh on every call rather than cached-and-refreshed -- cheap
    (HS256 signing, no network round trip) and always valid, so there is no
    token-refresh-on-expiry state machine to get wrong. `expiration_hours=1`
    matches security.md's machine-access-token ceiling.
    """
    return cast(
        str,
        create_jwt_token(
            user_id="svc-ingest",
            username="svc-ingest",
            email="svc-ingest@internal.waddlebot",
            roles=["service"],
            secret_key=Config.SECRET_KEY,
            tenant=Config.RUNNER_TENANT_SLUG,
            scope=Config.JWT_SCOPE,
            expiration_hours=1,
        ),
    )


@app.before_serving
async def startup() -> None:
    """Wire the httpx/Valkey clients, poller, and start the poll-drain loop + socket receivers."""
    http_client = httpx.AsyncClient()
    redis_client = redis.from_url(Config.VALKEY_URL, encoding="utf-8", decode_responses=True)

    poller = BundlePoller(
        http_client,
        Config.DISTRIBUTION_URL,
        stage=Config.PIPELINE_STAGE,
        jwt_provider=_jwt_provider,
        community_id=Config.RUNNER_COMMUNITY_ID,
        poll_interval_s=Config.POLL_INTERVAL_S,
        base_backoff_s=Config.BASE_BACKOFF_S,
        max_backoff_s=Config.MAX_BACKOFF_S,
    )
    runner = IngestRunner(
        poller=poller, redis_client=redis_client, tenant_slug=Config.RUNNER_TENANT_SLUG
    )

    app.config["http_client"] = http_client
    app.config["redis_client"] = redis_client
    app.config["runner"] = runner
    app.config["runner_task"] = asyncio.ensure_future(runner.run_forever())

    # Socket-owning receivers (App Bundle SDK gateway_socket ingest) --
    # supervised alongside the poll-drain loop above, each guarded by a
    # Valkey lease so scaling svc-ingest to N replicas never opens N
    # duplicate sockets for the same (provider, community). See this
    # module's own docstring and socket_lease.py for the full design.
    registry = AppRegistry()
    register_default_bundles(registry)
    app.config["registry"] = registry

    supervisor = ReceiverSupervisor(
        base_backoff_s=Config.RECEIVER_BASE_BACKOFF_S,
        max_backoff_s=Config.RECEIVER_MAX_BACKOFF_S,
    )
    app.config["supervisor"] = supervisor

    if Config.DISCORD_BOT_TOKEN:
        replica_id = uuid.uuid4().hex
        discord_receiver = DiscordGatewayReceiver(
            token=Config.DISCORD_BOT_TOKEN,
            redis_client=redis_client,
            registry=registry,
            tenant_slug=Config.RUNNER_TENANT_SLUG,
        )
        leased_discord = LeasedReceiver(
            receiver=discord_receiver,
            redis_client=redis_client,
            provider="discord",
            community=PLATFORM_COMMUNITY,
            owner_id=replica_id,
            ttl_s=Config.SOCKET_LEASE_TTL_S,
            renew_interval_s=Config.SOCKET_LEASE_RENEW_INTERVAL_S,
        )
        app.config["discord_leased_receiver"] = leased_discord
        supervisor.register("discord_gateway", leased_discord.run)
        logger.system(
            "svc-ingest registered Discord gateway receiver",
            action="startup",
            replica_id=replica_id,
        )
    else:
        logger.system(
            "svc-ingest starting with no socket receivers -- DISCORD_BOT_TOKEN not configured",
            action="startup",
            result="SKIPPED",
        )

    await supervisor.start()
    logger.system("svc-ingest started", action="startup", result="SUCCESS")


@app.after_serving
async def shutdown() -> None:
    """Stop the background loop, every supervised receiver, and close both clients."""
    supervisor = app.config.get("supervisor")
    if supervisor is not None:
        await supervisor.stop()

    runner = app.config.get("runner")
    if runner is not None:
        runner.stop()
    task = app.config.get("runner_task")
    if task is not None:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass  # expected -- this is our own cancel() above, not a failure
        except Exception as exc:  # noqa: BLE001 - shutdown must not raise
            logger.warning(f"Error stopping runner task: {exc}")

    http_client = app.config.get("http_client")
    if http_client is not None:
        await http_client.aclose()
    redis_client = app.config.get("redis_client")
    if redis_client is not None:
        await redis_client.aclose()
    logger.system("svc-ingest shutdown complete", action="shutdown", result="SUCCESS")


if __name__ == "__main__":  # pragma: no cover - process entrypoint, not exercised by unit tests
    import hypercorn.asyncio
    from hypercorn.config import Config as HyperConfig

    hyper_config = HyperConfig()
    hyper_config.bind = [f"0.0.0.0:{Config.MODULE_PORT}"]
    asyncio.run(hypercorn.asyncio.serve(app, hyper_config))
