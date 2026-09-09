"""Tests for `receivers.discord_gateway.DiscordGatewayReceiver`.

`discord.Bot` itself is monkeypatched to a fake class (records registered
event handlers, controllable `start()`/`close()`) rather than opening a
real gateway connection -- the fake still exercises the REAL
`_build_bot`/`receive()` wiring (queue bridging, `on_message` filtering,
`_build_raw_event` normalization), only the actual py-cord network layer
is replaced, matching the task's own "mock the gateway in tests" scope.
Duck-typed fake `discord.Message`/`Author`/`Guild`/`Channel` objects
(py-cord's own `Message` needs live HTTP state to construct).
"""

from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass, field
from typing import Any

import pytest
from waddle_transports import Direction, NonRetryableTransportError, Transport

import receivers.discord_gateway as discord_gateway_module
from receivers.discord_gateway import CONSUMES_TAG, DiscordGatewayReceiver

TOKEN = "fake-token-not-a-real-discord-token"  # noqa: S105 - test literal, not a secret


@dataclass
class _FakeAuthor:
    id: int
    name: str
    bot: bool = False


@dataclass
class _FakeGuild:
    id: int


@dataclass
class _FakeChannel:
    id: int


@dataclass
class _FakeMessage:
    id: int
    author: _FakeAuthor
    channel: _FakeChannel
    content: str
    guild: _FakeGuild | None = None


@dataclass
class _FakeClientUser:
    """Stand-in for `discord.ClientUser` -- real py-cord only exposes `.id` here that matters."""

    id: int


@dataclass
class _FakeBot:
    """Stand-in for `discord.Bot` -- records registered handlers, controllable lifecycle."""

    intents: Any = None
    # `None` until `on_ready` -- mirrors real py-cord's `bot.user` being unset
    # until the gateway handshake completes (see `_is_self`'s pre-ready edge).
    user: _FakeClientUser | None = None
    handlers: dict[str, Any] = field(default_factory=dict)
    start_calls: list[str] = field(default_factory=list)
    close_calls: int = 0
    _stop_event: asyncio.Event = field(default_factory=asyncio.Event)

    def event(self, func: Any) -> Any:
        """Mirror `discord.Bot.event`'s decorator -- register by function name."""
        self.handlers[func.__name__] = func
        return func

    async def start(self, token: str) -> None:
        """Block until `close()` is called -- mirrors a real gateway connection staying open."""
        self.start_calls.append(token)
        await self._stop_event.wait()

    async def close(self) -> None:
        self.close_calls += 1
        self._stop_event.set()


@pytest.fixture
def fake_bots(monkeypatch: pytest.MonkeyPatch) -> list[_FakeBot]:
    """Every `discord.Bot(...)` constructed during the test lands in this list."""
    created: list[_FakeBot] = []

    def _fake_bot_ctor(*, intents: Any) -> _FakeBot:
        bot = _FakeBot(intents=intents)
        created.append(bot)
        return bot

    monkeypatch.setattr(discord_gateway_module.discord, "Bot", _fake_bot_ctor)
    return created


async def _advance_to_bot_started(gen: Any, fake_bots: list[_FakeBot]) -> asyncio.Task[Any]:
    """Start `gen.__anext__()` as a task and yield control until `receive()`'s bot has started.

    A single `asyncio.sleep(0)` only lets `receive()`'s OWN synchronous
    code (through its first real await, `asyncio.wait(...)`) run --
    `bot.start(token)` was merely scheduled via `ensure_future`, not
    actually entered, at that point. Polling (bounded) until
    `start_calls` is populated avoids that one-yield-is-enough
    assumption breaking silently on an unrelated asyncio internals change.
    """
    next_task = asyncio.ensure_future(gen.__anext__())
    for _ in range(50):
        await asyncio.sleep(0)
        if fake_bots and fake_bots[-1].start_calls:
            return next_task
    raise AssertionError("bot.start() was never actually entered")


async def _cancel_and_close(next_task: asyncio.Task[Any], gen: Any) -> None:
    """Cancel `next_task`, await its cancellation, then close `gen` -- safe teardown order.

    `gen.aclose()` while `next_task` (wrapping the same generator's
    `__anext__()`) hasn't finished processing its own cancellation yet
    raises `RuntimeError: aclose(): asynchronous generator is already
    running` -- cancel-and-await first, THEN close (a no-op by that point,
    the generator's own `finally` already tore it down).
    """
    next_task.cancel()
    with contextlib.suppress(asyncio.CancelledError, StopAsyncIteration):
        await next_task
    await gen.aclose()


class TestResolveToken:
    async def test_literal_token_is_used_directly(self, fake_bots: list[_FakeBot]) -> None:
        receiver = DiscordGatewayReceiver()
        gen = receiver.receive({"token": TOKEN})
        next_task = await _advance_to_bot_started(gen, fake_bots)
        assert fake_bots[0].start_calls == [TOKEN]
        await _cancel_and_close(next_task, gen)

    async def test_token_ref_is_resolved_from_env(
        self, fake_bots: list[_FakeBot], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SOME_DISCORD_TOKEN_VAR", TOKEN)
        receiver = DiscordGatewayReceiver()
        gen = receiver.receive({"token_ref": "SOME_DISCORD_TOKEN_VAR"})
        next_task = await _advance_to_bot_started(gen, fake_bots)
        assert fake_bots[0].start_calls == [TOKEN]
        await _cancel_and_close(next_task, gen)

    async def test_missing_token_and_token_ref_raises(self) -> None:
        receiver = DiscordGatewayReceiver()
        gen = receiver.receive({})
        with pytest.raises(NonRetryableTransportError, match="token"):
            await gen.__anext__()

    async def test_unresolvable_token_ref_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("UNSET_TOKEN_VAR", raising=False)
        receiver = DiscordGatewayReceiver()
        gen = receiver.receive({"token_ref": "UNSET_TOKEN_VAR"})
        with pytest.raises(NonRetryableTransportError, match="resolution failed"):
            await gen.__anext__()


class TestReceive:
    async def test_yields_normalized_dict_for_human_guild_message(
        self, fake_bots: list[_FakeBot]
    ) -> None:
        receiver = DiscordGatewayReceiver()
        gen = receiver.receive({"token": TOKEN})
        next_task = await _advance_to_bot_started(gen, fake_bots)
        bot = fake_bots[0]

        message = _FakeMessage(
            id=123,
            author=_FakeAuthor(id=555, name="alice"),
            channel=_FakeChannel(id=42),
            content="hello waddlebot",
            guild=_FakeGuild(id=7),
        )
        await bot.handlers["on_message"](message)

        item = await asyncio.wait_for(next_task, timeout=2.0)
        assert item == {
            "platform": "discord",
            "guild_id": "7",
            "channel_id": "42",
            "message_id": "123",
            "author_id": "555",
            "author_username": "alice",
            "content": "hello waddlebot",
        }
        await gen.aclose()

    async def test_dm_message_has_no_guild_id(self, fake_bots: list[_FakeBot]) -> None:
        receiver = DiscordGatewayReceiver()
        gen = receiver.receive({"token": TOKEN})
        next_task = await _advance_to_bot_started(gen, fake_bots)
        bot = fake_bots[0]

        message = _FakeMessage(
            id=124,
            author=_FakeAuthor(id=555, name="alice"),
            channel=_FakeChannel(id=99),
            content="dm text",
            guild=None,
        )
        await bot.handlers["on_message"](message)

        item = await asyncio.wait_for(next_task, timeout=2.0)
        assert item["guild_id"] is None
        await gen.aclose()

    async def test_self_authored_message_is_ignored(self, fake_bots: list[_FakeBot]) -> None:
        """A message from THIS bot's own id (echoed back by the gateway) is dropped."""
        receiver = DiscordGatewayReceiver()
        gen = receiver.receive({"token": TOKEN})
        next_task = await _advance_to_bot_started(gen, fake_bots)
        bot = fake_bots[0]
        bot.user = _FakeClientUser(id=999)

        self_message = _FakeMessage(
            id=1,
            author=_FakeAuthor(id=999, name="WaddleBot", bot=True),
            channel=_FakeChannel(id=42),
            content="Hey alice! 👋",
            guild=_FakeGuild(id=7),
        )
        await bot.handlers["on_message"](self_message)
        # Immediately followed by a real human message -- if the self
        # message had been queued, THAT would be the first item yielded.
        human_message = _FakeMessage(
            id=2,
            author=_FakeAuthor(id=555, name="alice"),
            channel=_FakeChannel(id=42),
            content="hi",
            guild=_FakeGuild(id=7),
        )
        await bot.handlers["on_message"](human_message)

        item = await asyncio.wait_for(next_task, timeout=2.0)
        assert item["author_id"] == "555"
        await gen.aclose()

    async def test_other_bot_authored_message_is_not_dropped(
        self, fake_bots: list[_FakeBot]
    ) -> None:
        """Scope is self-only -- a DIFFERENT bot's message must still be fanned out."""
        receiver = DiscordGatewayReceiver()
        gen = receiver.receive({"token": TOKEN})
        next_task = await _advance_to_bot_started(gen, fake_bots)
        bot = fake_bots[0]
        bot.user = _FakeClientUser(id=999)

        other_bot_message = _FakeMessage(
            id=3,
            author=_FakeAuthor(id=888, name="OtherBot", bot=True),
            channel=_FakeChannel(id=42),
            content="I am a different bot",
            guild=_FakeGuild(id=7),
        )
        await bot.handlers["on_message"](other_bot_message)

        item = await asyncio.wait_for(next_task, timeout=2.0)
        assert item["author_id"] == "888"
        await gen.aclose()

    async def test_unready_bot_does_not_drop_any_message(self, fake_bots: list[_FakeBot]) -> None:
        """Pre-`on_ready` (`bot.user is None`) -- unknown identity errs toward NOT dropping."""
        receiver = DiscordGatewayReceiver()
        gen = receiver.receive({"token": TOKEN})
        next_task = await _advance_to_bot_started(gen, fake_bots)
        bot = fake_bots[0]
        assert bot.user is None  # not yet readied

        message = _FakeMessage(
            id=4,
            author=_FakeAuthor(id=42, name="anyone"),
            channel=_FakeChannel(id=42),
            content="early message",
            guild=_FakeGuild(id=7),
        )
        await bot.handlers["on_message"](message)

        item = await asyncio.wait_for(next_task, timeout=2.0)
        assert item["author_id"] == "42"
        await gen.aclose()

    async def test_on_ready_handler_does_not_raise(self, fake_bots: list[_FakeBot]) -> None:
        receiver = DiscordGatewayReceiver()
        gen = receiver.receive({"token": TOKEN})
        next_task = await _advance_to_bot_started(gen, fake_bots)
        bot = fake_bots[0]

        await bot.handlers["on_ready"]()  # must not raise

        await _cancel_and_close(next_task, gen)

    async def test_generator_ends_cleanly_when_bot_connection_closes(
        self, fake_bots: list[_FakeBot]
    ) -> None:
        """A clean `bot.close()` (connection ended, no error) ends iteration, not an exception."""
        receiver = DiscordGatewayReceiver()
        gen = receiver.receive({"token": TOKEN})
        next_task = await _advance_to_bot_started(gen, fake_bots)
        bot = fake_bots[0]

        await bot.close()

        with pytest.raises(StopAsyncIteration):
            await asyncio.wait_for(next_task, timeout=2.0)

    async def test_cancelling_the_consumer_closes_the_bot(self, fake_bots: list[_FakeBot]) -> None:
        receiver = DiscordGatewayReceiver()
        gen = receiver.receive({"token": TOKEN})
        next_task = await _advance_to_bot_started(gen, fake_bots)
        bot = fake_bots[0]
        assert bot.close_calls == 0

        await _cancel_and_close(next_task, gen)

        assert bot.close_calls == 1


class TestIsSelf:
    """Direct unit coverage of `DiscordGatewayReceiver._is_self`, independent of `receive()`."""

    def test_matching_id_is_self(self) -> None:
        message = _FakeMessage(
            id=1,
            author=_FakeAuthor(id=999, name="WaddleBot"),
            channel=_FakeChannel(id=1),
            content="hi",
        )
        bot = _FakeBot(user=_FakeClientUser(id=999))
        assert DiscordGatewayReceiver._is_self(message, bot) is True  # noqa: SLF001

    def test_different_id_is_not_self(self) -> None:
        message = _FakeMessage(
            id=1,
            author=_FakeAuthor(id=555, name="alice"),
            channel=_FakeChannel(id=1),
            content="hi",
        )
        bot = _FakeBot(user=_FakeClientUser(id=999))
        assert DiscordGatewayReceiver._is_self(message, bot) is False  # noqa: SLF001

    def test_other_bot_id_is_not_self(self) -> None:
        message = _FakeMessage(
            id=1,
            author=_FakeAuthor(id=888, name="OtherBot", bot=True),
            channel=_FakeChannel(id=1),
            content="hi",
        )
        bot = _FakeBot(user=_FakeClientUser(id=999))
        assert DiscordGatewayReceiver._is_self(message, bot) is False  # noqa: SLF001

    def test_unready_bot_user_none_is_not_self(self) -> None:
        message = _FakeMessage(
            id=1,
            author=_FakeAuthor(id=999, name="WaddleBot"),
            channel=_FakeChannel(id=1),
            content="hi",
        )
        bot = _FakeBot(user=None)
        assert DiscordGatewayReceiver._is_self(message, bot) is False  # noqa: SLF001


class TestTransportClassification:
    """`DiscordGatewayReceiver` maps to `waddle_transports.Transport`.

    `name="discord_gateway"`, `directions={Direction.INBOUND}`.
    """

    def test_is_a_transport_subclass(self) -> None:
        assert isinstance(DiscordGatewayReceiver(), Transport)

    def test_name_is_discord_gateway(self) -> None:
        assert DiscordGatewayReceiver().name == "discord_gateway"

    def test_directions_is_inbound_only(self) -> None:
        assert DiscordGatewayReceiver().directions == frozenset({Direction.INBOUND})

    def test_consumes_tag_matches_manifest(self) -> None:
        assert CONSUMES_TAG == "discord.message"
