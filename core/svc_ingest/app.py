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
`DiscordGatewayReceiver`, `receivers/twitch_irc.py`'s `TwitchIrcReceiver`
-- one instance per configured channel, see that module's own docstring)
as `supervisor.ReceiverSupervisor`-supervised tasks -- 8-container
decision: these receivers were briefly a standalone `svc-gateway` 9th
container, folded back into svc-ingest since a persistent bot/IRC
connection is exactly the same "hold a persistent inbound socket,
normalize, feed the pipeline" shape this container already owns. Each
transport is guarded by a `socket_lease.SocketLease` (`waddles:socket-
owner:{provider}:{community}`, Valkey `SET NX PX`) so scaling
`pipeline.svcIngest.replicas` never opens duplicate sockets for the same
`(provider, community)` -- see `socket_lease.py`'s own module docstring
for the full design.

Fan-out (T9): every item either transport yields is routed at
`community=None` (tenant-wide) for this demo -- Discord's `guild_id`/
Twitch's `channel_name` are both carried in their own normalized dicts for
FUTURE use, but no guild/channel->community mapping table exists yet
anywhere in this codebase (documented, deferred slot; see each receiver's
own docstring).

Twitch's outbound chat sends for svc-action are handled by a SEPARATE
`outbound_drain.py` task, ALSO supervised and ALSO lease-guarded (2026-09-04
fix -- see that module's own docstring) -- `provider="twitch",
community=socket_lease.PLATFORM_COMMUNITY`, since the underlying relay
queue is provider-scoped, not per-channel, so only one live replica ever
drains/sends at a time. It opens a fresh short-lived `waddle_transports.
transports.irc.IrcTransport` connection per relayed message rather than
reusing any receiver's socket, and runs on its OWN dedicated Valkey
connection (`socket_timeout=outbound_drain.DRAIN_SOCKET_TIMEOUT_S`, built
below) rather than the shared `redis_client` -- sharing it would leave the
blocking BRPOP racing that client's own (shorter) default socket timeout,
which is exactly what caused the `Timeout reading from ...` false failures
this fix addresses.

The EventSub webhook (`POST /eventsub/twitch/webhook`, `eventsub.py`) is a
genuine inbound HTTP push (not a persistent socket) -- registered as a
plain Quart route, wired to the same `fanout.fan_out_event` machinery the
IRC receivers use.
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
from quart import Blueprint, Quart, request

from bundles.discord_gateway_manifest import register_default_bundles as register_discord_bundles
from bundles.twitch_gateway_manifest import register_default_bundles as register_twitch_bundles
from config import Config
from eventsub import TwitchEventSubHandler
from fanout import fan_out_event
from outbound_drain import DRAIN_SOCKET_TIMEOUT_S, TwitchOutboundDrain
from receivers.discord_gateway import CONSUMES_TAG as DISCORD_CONSUMES_TAG
from receivers.discord_gateway import DiscordGatewayReceiver
from receivers.twitch_irc import CONSUMES_TAG as TWITCH_CONSUMES_TAG
from receivers.twitch_irc import TwitchIrcReceiver
from runner import IngestRunner
from socket_lease import PLATFORM_COMMUNITY, LeasedReceiver
from supervisor import ReceiverSupervisor

app = Quart(__name__)
# security.md A05 hardening -- JSON-only service, default deny-everything CSP.
install_security_headers(app)

health_bp = create_health_blueprint(Config.MODULE_NAME, Config.MODULE_VERSION)
app.register_blueprint(health_bp)

eventsub_bp = Blueprint("eventsub", __name__, url_prefix="/eventsub")

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


def _register_discord_receiver(
    supervisor: ReceiverSupervisor,
    *,
    redis_client: Any,
    registry: AppRegistry,
) -> None:
    """Build + lease-guard + supervise the Discord gateway receiver, if configured."""
    if not Config.DISCORD_BOT_TOKEN:
        logger.system(
            "svc-ingest starting with no Discord receiver -- DISCORD_BOT_TOKEN not configured",
            action="startup",
            result="SKIPPED",
        )
        return

    replica_id = uuid.uuid4().hex
    discord_receiver = DiscordGatewayReceiver()

    async def _on_discord_item(item: Mapping[str, Any]) -> None:
        """Fan one normalized Discord message dict out to every consuming bundle.

        T9: `community=None` (tenant-wide) for this demo -- see this
        module's own docstring for the deferred guild->community mapping
        slot.
        """
        await fan_out_event(
            item,
            consumes_tag=DISCORD_CONSUMES_TAG,
            tenant=Config.RUNNER_TENANT_SLUG,
            community=None,
            redis_client=redis_client,
            registry=registry,
        )

    leased_discord = LeasedReceiver(
        transport=discord_receiver,
        # `token_ref` is an env var *name*, resolved by `receive()` via
        # `waddle_transports.signing.resolve_secret` -- never a raw token
        # in this config dict.
        config={"token_ref": "DISCORD_BOT_TOKEN"},  # nosec B105 -- env var name, not a token value
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
        "svc-ingest registered Discord gateway receiver", action="startup", replica_id=replica_id
    )


def _register_twitch_receivers(
    supervisor: ReceiverSupervisor,
    *,
    redis_client: Any,
    registry: AppRegistry,
) -> None:
    """Build + lease-guard + supervise one Twitch IRC receiver per channel, if configured."""
    if not (Config.TWITCH_BOT_TOKEN_REF and Config.TWITCH_CHANNELS):
        logger.system(
            "svc-ingest starting with no Twitch IRC receivers -- "
            "TWITCH_BOT_TOKEN_REF/TWITCH_CHANNELS not configured",
            action="startup",
            result="SKIPPED",
        )
        return

    replica_id = uuid.uuid4().hex
    irc_config_base = Config.twitch_irc_config_base()
    leased_receivers = []

    async def _on_twitch_item(item: Mapping[str, Any]) -> None:
        """Fan one normalized Twitch chat message dict out to every consuming bundle.

        T9: `community=None` (tenant-wide) for this demo -- see this
        module's own docstring for the deferred channel->community
        mapping slot.
        """
        await fan_out_event(
            item,
            consumes_tag=TWITCH_CONSUMES_TAG,
            tenant=Config.RUNNER_TENANT_SLUG,
            community=None,
            redis_client=redis_client,
            registry=registry,
        )

    for channel in Config.TWITCH_CHANNELS:
        twitch_receiver = TwitchIrcReceiver()
        # ONE lease per channel -- IrcTransport.receive() is a single-
        # channel-per-connection contract, so two replicas must never
        # both hold the SAME channel's connection, but different channels
        # are entirely independent (never contend for the same lease
        # key). See receivers/twitch_irc.py's own docstring.
        leased = LeasedReceiver(
            transport=twitch_receiver,
            config={**irc_config_base, "channel": channel},
            on_item=_on_twitch_item,
            redis_client=redis_client,
            provider="twitch",
            community=channel,
            owner_id=replica_id,
            ttl_s=Config.SOCKET_LEASE_TTL_S,
            renew_interval_s=Config.SOCKET_LEASE_RENEW_INTERVAL_S,
        )
        leased_receivers.append(leased)
        supervisor.register(f"twitch_irc:{channel}", leased.run, transport=twitch_receiver)

    app.config["twitch_leased_receivers"] = leased_receivers

    # Dedicated Valkey connection for the drain's own blocking BRPOP --
    # NOT the shared redis_client above, whose default socket_timeout
    # (redis-py: 5s) equals the BRPOP block timeout and races it on every
    # idle poll (see outbound_drain.py's own module docstring for the
    # full root-cause). Closed in shutdown() below alongside redis_client.
    drain_redis_client = redis.from_url(
        Config.VALKEY_URL,
        encoding="utf-8",
        decode_responses=True,
        socket_timeout=DRAIN_SOCKET_TIMEOUT_S,
    )
    app.config["twitch_outbound_drain_redis_client"] = drain_redis_client

    outbound_drain = TwitchOutboundDrain(
        redis_client=drain_redis_client,
        # The ORDINARY shared client (same one every other Twitch/Discord
        # lease already uses) for the drain's own claim/renew/release --
        # deliberately NOT drain_redis_client, see outbound_drain.py's own
        # "Two separate Valkey clients" docstring section for why sharing
        # one connection between a blocking BRPOP and lease SET/EVAL calls
        # is unsafe.
        lease_redis_client=redis_client,
        irc_config_base=irc_config_base,
        # Same replica_id as this replica's own per-channel leases above --
        # one owner identity per svc-ingest process across every Twitch
        # lease it may hold (inbound receive AND outbound transmit).
        owner_id=replica_id,
        ttl_s=Config.SOCKET_LEASE_TTL_S,
        renew_interval_s=Config.SOCKET_LEASE_RENEW_INTERVAL_S,
    )
    app.config["twitch_outbound_drain"] = outbound_drain
    supervisor.register("twitch_outbound_drain", outbound_drain.run)

    logger.system(
        "svc-ingest registered Twitch IRC receivers",
        action="startup",
        replica_id=replica_id,
        channels=len(Config.TWITCH_CHANNELS),
    )


def _register_twitch_eventsub(*, redis_client: Any, registry: AppRegistry) -> None:
    """Build the Twitch EventSub webhook handler, if configured."""
    if not Config.TWITCH_EVENTSUB_SECRET:
        logger.system(
            "svc-ingest starting with no Twitch EventSub handler -- "
            "TWITCH_EVENTSUB_SECRET not configured",
            action="startup",
            result="SKIPPED",
        )
        return

    app.config["twitch_eventsub_handler"] = TwitchEventSubHandler(
        secret=Config.TWITCH_EVENTSUB_SECRET,
        redis_client=redis_client,
        registry=registry,
        tenant_slug=Config.RUNNER_TENANT_SLUG,
    )
    logger.system("svc-ingest registered Twitch EventSub handler", action="startup")


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
    register_discord_bundles(registry)
    register_twitch_bundles(registry)
    app.config["registry"] = registry

    supervisor = ReceiverSupervisor(
        base_backoff_s=Config.RECEIVER_BASE_BACKOFF_S,
        max_backoff_s=Config.RECEIVER_MAX_BACKOFF_S,
    )
    app.config["supervisor"] = supervisor

    _register_discord_receiver(supervisor, redis_client=redis_client, registry=registry)
    _register_twitch_receivers(supervisor, redis_client=redis_client, registry=registry)
    _register_twitch_eventsub(redis_client=redis_client, registry=registry)

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
    drain_redis_client = app.config.get("twitch_outbound_drain_redis_client")
    if drain_redis_client is not None:
        await drain_redis_client.aclose()
    logger.system("svc-ingest shutdown complete", action="shutdown", result="SUCCESS")


@eventsub_bp.route("/twitch/webhook", methods=["POST"])
async def twitch_eventsub_webhook():  # type: ignore[no-untyped-def]
    """Real Twitch EventSub webhook endpoint -- signature-verified, fans out via `fanout.py`.

    `webhook_callback_verification` (subscription-setup handshake) must
    echo the bare challenge string back as `text/plain`, NOT JSON-wrapped
    -- Twitch's own subscription-verification contract, ported verbatim
    from the legacy module's identical special case
    (`trigger/receiver/twitch_module/app.py`'s `eventsub_webhook`).
    """
    handler = app.config.get("twitch_eventsub_handler")
    if handler is None:
        return {"error": "EventSub not configured"}, 503

    body = await request.get_data()
    body_json = await request.get_json()
    headers = dict(request.headers)

    response_body, status = await handler.handle_webhook(
        headers=headers, body=body, body_json=body_json or {}
    )
    if "challenge" in response_body:
        return response_body["challenge"], status, {"Content-Type": "text/plain"}
    return response_body, status


app.register_blueprint(eventsub_bp)


if __name__ == "__main__":  # pragma: no cover - process entrypoint, not exercised by unit tests
    import hypercorn.asyncio
    from hypercorn.config import Config as HyperConfig

    hyper_config = HyperConfig()
    hyper_config.bind = [f"0.0.0.0:{Config.MODULE_PORT}"]
    asyncio.run(hypercorn.asyncio.serve(app, hyper_config))
