"""TwitchIrcReceiver -- a `waddle_transports.Transport` for inbound Twitch IRC chat receipt.

Delegates the real IRC wire protocol entirely to `waddle_transports.
transports.irc.IrcTransport` (a real, from-scratch, Twitch-agnostic
asyncio TCP/TLS IRC client -- see that module's own docstring; NOT a port
of twitchio or any Twitch-specific library). This receiver's only job is
normalizing each raw `{channel, sender, text}` dict `IrcTransport.
receive()` yields into the platform event shape `bundles/twitch_ingest.py`
consumes.

ONE connection per channel (`IrcTransport.receive()`'s own single-channel-
per-call contract) -- `app.py`'s startup builds one `TwitchIrcReceiver`
per `Config.TWITCH_CHANNELS` entry, each wrapped in its own `socket_lease.
LeasedReceiver` (`provider="twitch", community=<channel>`) and registered
under its own `ReceiverSupervisor` name, so scaling `pipeline.svcIngest.
replicas` never opens two connections to the same channel, and one
channel's connection dying/restarting never affects another's.

Like `DiscordGatewayReceiver`, this class owns ONLY `receive()` -- no
bespoke `run()`/`stop()`, fan-out, or Valkey/registry dependency; the
lease-guarded consume loop (`socket_lease.LeasedReceiver`) and the fan-out
callback (`app.py`'s own `_on_twitch_item`) both live at the wiring layer
now, matching the shared `waddle_transports.Transport` ABC contract
exactly.

Outbound sends are NOT handled here -- see `outbound_drain.py`
(`IrcTransport.send()` opens its own short-lived connection per message,
so relaying through a receiver's already-open socket is unnecessary; the
earlier draft's "reuse the held socket" premise doesn't apply once the
real transport's `send()` semantics are known -- it never held a
persistent connection to reuse in the first place).
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Mapping
from typing import Any, ClassVar

from waddle_transports import Direction, Transport
from waddle_transports.transports.irc import IrcTransport

#: The `consumes` tag every ingest bundle wanting a raw Twitch chat message
#: declares (`bundles/twitch_gateway_manifest.py`'s own `stages.ingest.
#: consumes`) -- this receiver's half of that contract.
CONSUMES_TAG = "twitch.message"


# The ignore comment below suppresses mypy --strict's "cannot subclass Any" complaint --
# Transport resolves to Any since waddle_transports ships no py.typed marker (see
# pyproject.toml's follow_imports="skip" override); the real ABC contract
# (name/directions/receive()) is still honored regardless.
class TwitchIrcReceiver(Transport):  # type: ignore[misc]
    """One persistent Twitch IRC connection (one channel) per `receive()` call.

    Not platform-level like Discord -- `IrcTransport.receive()` is a
    single-channel-per-connection contract, so `app.py` constructs one
    `TwitchIrcReceiver` per configured channel; each one's own
    `socket_lease.LeasedReceiver` ensures only one live svc-ingest replica
    ever holds an active iteration for that channel.
    """

    name: ClassVar[str] = "twitch_irc"
    directions: ClassVar[frozenset[Direction]] = frozenset({Direction.INBOUND})

    def __init__(self) -> None:
        """Build the receiver -- does not connect yet, see `receive()`."""
        self._irc = IrcTransport()

    async def receive(self, config: Mapping[str, Any]) -> AsyncIterator[Mapping[str, Any]]:
        """Delegate to `IrcTransport.receive()`, normalizing each raw PRIVMSG dict.

        `config` is one channel's full `IrcTransport` config (`host`/
        `port`/`nick`/`password_ref`/`use_tls`/`channel` -- see `config.py`
        `Config.twitch_irc_config_base()` + `app.py`'s per-channel wiring).

        Real transform (not a stub) of `IrcTransport`'s own `{channel,
        sender, text}` shape into the raw event dict `bundles/
        twitch_ingest.py::normalize()` consumes -- field names here are
        this receiver's own contract with that entrypoint, matching
        `receivers/discord_gateway.py`'s own precedent (no repo-wide "raw
        platform event" schema exists yet).
        """
        async for raw in self._irc.receive(config):
            yield {
                "platform": "twitch",
                "channel_name": raw.get("channel", "").lstrip("#"),
                "author_username": raw.get("sender"),
                "content": raw.get("text"),
            }
