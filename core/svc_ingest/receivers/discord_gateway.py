"""DiscordGatewayReceiver -- holds the real py-cord Discord bot gateway connection.

Real py-cord (`discord.Bot`) connection + intents setup, deliberately
reusing `trigger/receiver/discord_module/services/discord_bot.py`'s own
`_setup_events` shape (default intents + `message_content`/`guilds`, an
`on_ready` log, an `on_message` handler that ignores bot-authored messages)
rather than reimplementing the py-cord gateway protocol -- per this PR's
own task spec. This receiver does NOT replicate that legacy module's
slash/prefix command routing (`_register_slash_commands` and friends) --
that command-router surface is a separate, much larger migration, out of
scope here; this receiver's only job is turning one inbound message into
one fan-out call (`fanout.fan_out_event`).

Modeled as a `transport_boundary.Transport` (`TransportType.SOCKET`,
`Direction.INBOUND`) -- see that module's own docstring for why this is a
shim for the shared `waddle_transports` library rather than the receiver
declaring its own bespoke classification.
"""

from __future__ import annotations

import logging
from typing import Any

import discord
from flask_core.app_registry import AppRegistry

from fanout import RedisLike, fan_out_event
from transport_boundary import Direction, Transport, TransportType

logger = logging.getLogger(__name__)

#: The `consumes` tag every ingest bundle wanting a raw Discord message
#: declares (`bundles/discord_gateway_manifest.py`'s own `stages.ingest.
#: consumes`) -- this receiver's half of that contract.
CONSUMES_TAG = "discord.message"


class DiscordGatewayReceiver(Transport):
    """Holds ONE persistent Discord bot gateway connection, fans every inbound message out.

    PLATFORM-level, not per-community: one `discord.Bot` connection serves
    every guild the bot has been invited to, so `run()` is called exactly
    once (`ReceiverSupervisor` restarts it on failure, never runs a second
    concurrent instance).
    """

    transport_type = TransportType.SOCKET
    direction = Direction.INBOUND

    def __init__(
        self,
        *,
        token: str,
        redis_client: RedisLike,
        registry: AppRegistry,
        tenant_slug: str,
    ) -> None:
        """Build the receiver and its `discord.Bot` -- does not connect yet, see `run()`."""
        self._token = token
        self._redis = redis_client
        self._registry = registry
        self._tenant_slug = tenant_slug

        intents = discord.Intents.default()
        intents.message_content = True  # required to read message text, not just metadata
        intents.guilds = True
        self.bot = discord.Bot(intents=intents)
        self._setup_events()

    def _setup_events(self) -> None:
        """Register the gateway event handlers py-cord dispatches to."""

        @self.bot.event  # type: ignore[untyped-decorator]
        async def on_ready() -> None:
            logger.info("gateway.discord_ready user=%s", self.bot.user)

        @self.bot.event  # type: ignore[untyped-decorator]
        async def on_message(message: discord.Message) -> None:
            await self._handle_message(message)

    async def _handle_message(self, message: discord.Message) -> None:
        """Fan a real inbound message out; one bad event must never kill the gateway connection."""
        if message.author.bot:
            return
        raw_event = self._build_raw_event(message)
        community = message.guild.id if message.guild else None
        try:
            count = await fan_out_event(
                raw_event,
                consumes_tag=CONSUMES_TAG,
                tenant=self._tenant_slug,
                community=community,
                redis_client=self._redis,
                registry=self._registry,
            )
            logger.debug("gateway.discord_message_fanned count=%s", count)
        except Exception as exc:  # noqa: BLE001 - one bad event must never kill the gateway
            logger.error("gateway.fanout_failed error=%s", exc)

    @staticmethod
    def _build_raw_event(message: discord.Message) -> dict[str, Any]:
        """Build the raw event dict LPUSHed onto each matching bundle's `:ingest` key.

        Consumed downstream by `core/svc_ingest/bundles/discord_ingest.py`'s
        `normalize()` -- field names here are this receiver's own contract
        with that entrypoint, not a repo-wide "raw Discord event" schema
        (none exists yet, matching `bundles/echo_ingest.py`'s own precedent
        of documenting its own minimal shape rather than inventing one).

        `community_id` in the App Bundle schema is an internal integer, not
        the raw platform guild id -- no guild->community lookup table
        exists yet anywhere in this codebase (documented gap, see the PR
        description); the guild id passes straight through as a
        best-effort community scope for this MVP proof, not a real mapping.
        """
        guild_id = str(message.guild.id) if message.guild else None
        return {
            "platform": "discord",
            "guild_id": guild_id,
            "channel_id": str(message.channel.id),
            "message_id": str(message.id),
            "author_id": str(message.author.id),
            "author_username": message.author.name,
            "content": message.content,
        }

    async def run(self) -> None:
        """Connect and run until the gateway connection ends or `stop()` cancels it.

        `ReceiverSupervisor` calls this in a loop -- a raised exception or
        a normal return (connection dropped) both trigger a supervised
        restart with backoff, see `supervisor.py`'s own docstring.
        """
        await self.bot.start(self._token)

    async def stop(self) -> None:
        """Close the gateway connection. Never raises -- shutdown must not fail."""
        try:
            await self.bot.close()
        except Exception as exc:  # noqa: BLE001 - shutdown must not raise
            logger.warning("gateway.discord_close_error error=%s", exc)
