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
platform-level inbound transports (`receivers/discord_gateway.py`'s
`waddle_transports.Transport` today) as `supervisor.ReceiverSupervisor`-
supervised tasks -- 8-container decision: these receivers were briefly a
standalone `svc-gateway` 9th container, folded back into svc-ingest since
a Discord bot connection is exactly the same "hold a persistent inbound
socket, normalize, feed the pipeline" shape this container already owns.
Each transport is guarded by a `socket_lease.SocketLease`
(`waddles:socket-owner:{provider}:{community}`, Valkey `SET NX PX`) so
scaling `pipeline.svcIngest.replicas` never opens duplicate sockets for
the same `(provider, community)` -- see `socket_lease.py`'s own module
docstring for the full design.

Fan-out (T9): every item the Discord transport yields is routed at
`community=None` (tenant-wide) for this demo -- `item["guild_id"]` is
carried in the normalized dict for FUTURE use, but no
guild->community mapping table exists yet anywhere in this codebase
(documented, deferred slot; see `receivers/discord_gateway.py`'s own
docstring).
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Mapping
from typing import Any, cast

import httpx
import redis.asyncio as redis
from flask_core import create_health_blueprint, install_security_headers, setup_aaa_logging
from flask_core.app_registry import AppRegistry
from flask_core.auth import create_jwt_token
from flask_core.stage_runner import BundlePoller
from quart import Quart

from bundles.discord_gateway_manifest import register_default_bundles
from config import Config
from fanout import fan_out_event
from receivers.discord_gateway import CONSUMES_TAG, DiscordGatewayReceiver
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

    # Socket-owning transports (inbound waddle_transports.Transport
    # connections) -- supervised alongside the poll-drain loop above, each
    # guarded by a Valkey lease so scaling svc-ingest to N replicas never
    # opens N duplicate sockets for the same (provider, community). See
    # this module's own docstring and socket_lease.py for the full design.
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
        discord_receiver = DiscordGatewayReceiver()

        async def _on_discord_item(item: Mapping[str, Any]) -> None:
            """Fan one normalized Discord message dict out to every consuming bundle.

            T9: `community=None` (tenant-wide) for this demo -- see this
            module's own docstring for the deferred guild->community
            mapping slot.
            """
            await fan_out_event(
                item,
                consumes_tag=CONSUMES_TAG,
                tenant=Config.RUNNER_TENANT_SLUG,
                community=None,
                redis_client=redis_client,
                registry=registry,
            )

        leased_discord = LeasedReceiver(
            transport=discord_receiver,
            # `token_ref` is an env var *name*, resolved by `receive()`
            # via `waddle_transports.signing.resolve_secret` -- never a
            # raw token in this config dict.
            config={"token_ref": "DISCORD_BOT_TOKEN"},
            on_item=_on_discord_item,
            redis_client=redis_client,
            provider="discord",
            community=PLATFORM_COMMUNITY,
            owner_id=replica_id,
            ttl_s=Config.SOCKET_LEASE_TTL_S,
            renew_interval_s=Config.SOCKET_LEASE_RENEW_INTERVAL_S,
        )
        app.config["discord_leased_receiver"] = leased_discord
        supervisor.register("discord_gateway", leased_discord.run, transport=discord_receiver)
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
