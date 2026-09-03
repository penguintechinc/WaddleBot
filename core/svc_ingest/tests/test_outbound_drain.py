"""Tests for `outbound_drain.TwitchOutboundDrain`.

`IrcTransport.send()` is monkeypatched (real socket connection out of
scope for this container's unit tests, same precedent as
`test_receivers_twitch_irc.py`). `redis_client` is a real
`fakeredis.FakeAsyncRedis` -- genuine LPUSH/BRPOP round trip.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest
from waddle_transports import TransportResult
from waddle_transports.transports.irc_relay import outbound_queue_key

from outbound_drain import TwitchOutboundDrain

_IRC_CONFIG_BASE = {
    "host": "irc.chat.twitch.tv",
    "port": 6697,
    "nick": "waddlebot",
    "password_ref": "TEST_TWITCH_TOKEN_REF",
}


def _drain(redis_client: Any) -> TwitchOutboundDrain:
    return TwitchOutboundDrain(redis_client=redis_client, irc_config_base=_IRC_CONFIG_BASE)


class TestSendOne:
    async def test_sends_a_well_formed_message(
        self, redis_client: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        drain = _drain(redis_client)
        captured = {}

        async def _fake_send(config, payload):  # noqa: ANN001, ANN202
            captured["config"] = config
            captured["payload"] = payload
            return TransportResult(transport="irc", detail="sent")

        monkeypatch.setattr(drain._irc, "send", _fake_send)  # noqa: SLF001

        await drain._send_one(json.dumps({"channel": "waddlebot", "text": "hi chat"}))  # noqa: SLF001

        assert captured["config"] == {**_IRC_CONFIG_BASE, "channel": "waddlebot"}
        assert captured["payload"] == {"text": "hi chat"}

    async def test_malformed_json_is_dropped(
        self, redis_client: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        drain = _drain(redis_client)
        called = False

        async def _fake_send(config, payload):  # noqa: ANN001, ANN202
            nonlocal called
            called = True

        monkeypatch.setattr(drain._irc, "send", _fake_send)  # noqa: SLF001

        await drain._send_one("not json")  # noqa: SLF001 - must not raise
        assert called is False

    async def test_missing_channel_key_is_dropped(
        self, redis_client: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        drain = _drain(redis_client)
        called = False

        async def _fake_send(config, payload):  # noqa: ANN001, ANN202
            nonlocal called
            called = True

        monkeypatch.setattr(drain._irc, "send", _fake_send)  # noqa: SLF001

        await drain._send_one(json.dumps({"text": "hi"}))  # noqa: SLF001 - must not raise
        assert called is False

    async def test_send_failure_does_not_propagate(
        self, redis_client: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        drain = _drain(redis_client)

        async def _raise(config, payload):  # noqa: ANN001, ANN202, ARG001
            raise ConnectionError("irc unreachable")

        monkeypatch.setattr(drain._irc, "send", _raise)  # noqa: SLF001

        await drain._send_one(json.dumps({"channel": "waddlebot", "text": "hi"}))  # noqa: SLF001


class TestRunStop:
    async def test_run_drains_a_queued_message_end_to_end(
        self, redis_client: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Fail-first proof: a message relayed via `outbound_queue_key` is delivered.

        Via the same queue `bundles/twitch_send_action.py` LPUSHes onto
        from svc-action.
        """
        drain = _drain(redis_client)
        sent: list[tuple[str, str]] = []

        async def _fake_send(config, payload):  # noqa: ANN001, ANN202
            sent.append((config["channel"], payload["text"]))
            return TransportResult(transport="irc", detail="sent")

        monkeypatch.setattr(drain._irc, "send", _fake_send)  # noqa: SLF001

        await redis_client.lpush(
            outbound_queue_key("twitch"), json.dumps({"channel": "waddlebot", "text": "relayed!"})
        )

        # `drain.run()`'s loop blocks on BRPOP with a real (multi-second)
        # timeout when the queue is empty -- `stop()` only takes effect
        # between BRPOP calls, so it can't interrupt one already in
        # flight. Cancel the task directly instead of a graceful stop()
        # to keep this test fast and deterministic.
        task = asyncio.ensure_future(drain.run())
        await asyncio.sleep(0.05)
        task.cancel()
        try:
            await asyncio.wait_for(task, timeout=2.0)
        except asyncio.CancelledError:
            pass

        assert sent == [("waddlebot", "relayed!")]

    async def test_stop_never_raises(self, redis_client: Any) -> None:
        drain = _drain(redis_client)
        await drain.stop()  # must not raise
