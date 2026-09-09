"""Tests for `receivers.twitch_irc.TwitchIrcReceiver`.

`IrcTransport.receive()` (the real wire protocol -- a genuine asyncio TCP/
TLS socket) is monkeypatched to a fake async generator on the receiver's
own `self._irc` instance -- opening a real connection is out of scope for
this container's unit tests, same precedent `test_discord_gateway.py`
sets for py-cord's own network layer. Unlike Discord's callback-driven
`discord.Bot`, `IrcTransport.receive()` is already a native async
generator, so no queue-bridging harness is needed here -- `receive()`
just needs to prove it normalizes each yielded item correctly.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Mapping

import pytest
from waddle_transports import Direction, Transport

from receivers.twitch_irc import CONSUMES_TAG, TwitchIrcReceiver

_IRC_CONFIG = {
    "host": "irc.chat.twitch.tv",
    "port": 6697,
    "nick": "waddlebot",
    "channel": "waddlebot",
    "password_ref": "TEST_TWITCH_TOKEN_REF",
}


async def _fake_privmsgs(*items: Mapping[str, str]) -> AsyncIterator[Mapping[str, str]]:
    for item in items:
        yield item


class TestTransportClassification:
    """`TwitchIrcReceiver` maps to `waddle_transports.Transport`.

    `name="twitch_irc"`, `directions={Direction.INBOUND}`.
    """

    def test_is_a_transport_subclass(self) -> None:
        assert isinstance(TwitchIrcReceiver(), Transport)

    def test_name_is_twitch_irc(self) -> None:
        assert TwitchIrcReceiver().name == "twitch_irc"

    def test_directions_is_inbound_only(self) -> None:
        assert TwitchIrcReceiver().directions == frozenset({Direction.INBOUND})

    def test_consumes_tag_matches_manifest(self) -> None:
        assert CONSUMES_TAG == "twitch.message"


class TestReceive:
    async def test_normalizes_raw_irc_transport_output(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        receiver = TwitchIrcReceiver()
        raw_privmsg = {"channel": "#waddlebot", "sender": "alice", "text": "hello chat"}
        monkeypatch.setattr(
            receiver._irc,  # noqa: SLF001 - test override of the real IrcTransport instance
            "receive",
            lambda config: _fake_privmsgs(raw_privmsg),
        )

        items = [item async for item in receiver.receive(_IRC_CONFIG)]

        assert items == [
            {
                "platform": "twitch",
                "channel_name": "waddlebot",
                "author_username": "alice",
                "content": "hello chat",
            }
        ]

    async def test_strips_leading_hash_from_channel(self, monkeypatch: pytest.MonkeyPatch) -> None:
        receiver = TwitchIrcReceiver()
        raw_privmsg = {"channel": "#somechannel", "sender": "bob", "text": "hi"}
        monkeypatch.setattr(
            receiver._irc,  # noqa: SLF001
            "receive",
            lambda config: _fake_privmsgs(raw_privmsg),
        )

        items = [item async for item in receiver.receive(_IRC_CONFIG)]
        assert items[0]["channel_name"] == "somechannel"

    async def test_yields_multiple_messages_in_order(self, monkeypatch: pytest.MonkeyPatch) -> None:
        receiver = TwitchIrcReceiver()
        monkeypatch.setattr(
            receiver._irc,  # noqa: SLF001
            "receive",
            lambda config: _fake_privmsgs(
                {"channel": "#waddlebot", "sender": "alice", "text": "one"},
                {"channel": "#waddlebot", "sender": "bob", "text": "two"},
            ),
        )

        items = [item async for item in receiver.receive(_IRC_CONFIG)]
        assert [i["author_username"] for i in items] == ["alice", "bob"]

    async def test_no_messages_ends_cleanly(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A connection that yields nothing before ending just ends iteration -- no error."""
        receiver = TwitchIrcReceiver()
        monkeypatch.setattr(receiver._irc, "receive", lambda config: _fake_privmsgs())  # noqa: SLF001

        items = [item async for item in receiver.receive(_IRC_CONFIG)]
        assert items == []

    async def test_self_authored_message_is_dropped(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A PRIVMSG whose sender matches `config["nick"]` (case-insensitive) is not fanned out."""
        receiver = TwitchIrcReceiver()
        monkeypatch.setattr(
            receiver._irc,  # noqa: SLF001
            "receive",
            lambda config: _fake_privmsgs(
                {"channel": "#waddlebot", "sender": "WaddleBot", "text": "Hey alice! 👋"},
                {"channel": "#waddlebot", "sender": "alice", "text": "hi"},
            ),
        )

        items = [item async for item in receiver.receive(_IRC_CONFIG)]

        assert [i["author_username"] for i in items] == ["alice"]

    async def test_other_bot_authored_message_is_not_dropped(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Scope is self-only -- a DIFFERENT sender's message must still be fanned out."""
        receiver = TwitchIrcReceiver()
        monkeypatch.setattr(
            receiver._irc,  # noqa: SLF001
            "receive",
            lambda config: _fake_privmsgs(
                {"channel": "#waddlebot", "sender": "othergreetbot", "text": "hi there"},
            ),
        )

        items = [item async for item in receiver.receive(_IRC_CONFIG)]

        assert [i["author_username"] for i in items] == ["othergreetbot"]

    async def test_missing_nick_in_config_does_not_drop_anything(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Unknown self-identity (no `nick` in config) errs toward NOT dropping."""
        receiver = TwitchIrcReceiver()
        monkeypatch.setattr(
            receiver._irc,  # noqa: SLF001
            "receive",
            lambda config: _fake_privmsgs(
                {"channel": "#waddlebot", "sender": "waddlebot", "text": "hi"},
            ),
        )
        config_without_nick = {k: v for k, v in _IRC_CONFIG.items() if k != "nick"}

        items = [item async for item in receiver.receive(config_without_nick)]

        assert [i["author_username"] for i in items] == ["waddlebot"]

    async def test_passes_config_through_to_irc_transport(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        receiver = TwitchIrcReceiver()
        captured: dict[str, Mapping[str, object]] = {}

        def _fake_receive(config: Mapping[str, object]) -> AsyncIterator[Mapping[str, str]]:
            captured["config"] = config
            return _fake_privmsgs()

        monkeypatch.setattr(receiver._irc, "receive", _fake_receive)  # noqa: SLF001

        async for _item in receiver.receive(_IRC_CONFIG):
            pass  # pragma: no cover -- no items yielded

        assert captured["config"] == _IRC_CONFIG
