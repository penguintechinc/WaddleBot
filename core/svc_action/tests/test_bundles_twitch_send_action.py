"""bundles/twitch_send_action.py -- OUTBOUND `irc` transport relay, Valkey-backed.

`_get_redis_client` is monkeypatched to a real `fakeredis.FakeAsyncRedis`
-- genuine LPUSH semantics exercised end to end (this bundle -> the
shared `waddle_transports.irc.RelayOutboundIrcTransport` -> the real
Valkey key `receivers/twitch_irc.py`'s outbound drain loop reads), not a
mocked call.
"""

from __future__ import annotations

import json
from typing import Any

import fakeredis
import httpx
import pytest
from waddle_transports.base import NonRetryableTransportError, RetryableTransportError
from waddle_transports.irc import outbound_queue_key

import bundles.twitch_send_action as twitch_bundle
from bundles.twitch_send_action import _get_redis_client, send_message
from services.adapters.base import NonRetryableDispatchError, RetryableDispatchError
from services.envelope import ActionEnvelope


def _envelope(payload: dict | None = None) -> ActionEnvelope:
    return ActionEnvelope(
        tenant="1",
        community="42",
        app_id="waddles.bot.twitch.default",
        stage="action",
        payload=payload if payload is not None else {"text": "hello from waddlebot"},
        ts="2026-09-02T12:00:00Z",
        raw="{}",
    )


def _config(**overrides: object) -> dict:
    base = {"channel": "waddlebot"}
    base.update(overrides)
    return base


@pytest.fixture
async def fake_redis() -> Any:
    client = fakeredis.FakeAsyncRedis(decode_responses=True)
    yield client
    await client.aclose()


@pytest.fixture(autouse=True)
def _patch_redis_client(monkeypatch: pytest.MonkeyPatch, fake_redis: Any) -> None:
    monkeypatch.setattr(twitch_bundle, "_get_redis_client", lambda config: fake_redis)


def _noop_http_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200)))


async def test_missing_channel_is_non_retryable() -> None:
    async with _noop_http_client() as client:
        with pytest.raises(NonRetryableDispatchError, match="channel"):
            await send_message(_envelope(), _config(channel=None), http_client=client)


async def test_missing_payload_text_is_non_retryable() -> None:
    async with _noop_http_client() as client:
        with pytest.raises(NonRetryableDispatchError, match="'text'"):
            await send_message(_envelope(payload={}), _config(), http_client=client)


async def test_sends_relays_channel_and_text_onto_the_outbound_irc_queue(
    fake_redis: Any,
) -> None:
    """Fail-first verification: the bundle relays through the real shared IRC transport."""
    async with _noop_http_client() as client:
        result = await send_message(_envelope(), _config(), http_client=client)

    assert result.target_type == "bundle"
    assert "waddlebot" in result.detail

    raw = await fake_redis.rpop(outbound_queue_key("twitch"))
    assert raw is not None
    assert json.loads(raw) == {"channel": "waddlebot", "text": "hello from waddlebot"}


async def test_empty_string_channel_is_non_retryable() -> None:
    async with _noop_http_client() as client:
        with pytest.raises(NonRetryableDispatchError, match="channel"):
            await send_message(_envelope(), _config(channel=""), http_client=client)


def test_get_redis_client_builds_and_caches_a_real_client(monkeypatch: pytest.MonkeyPatch) -> None:
    """The real (unpatched) `_get_redis_client`.

    Production path, not exercised by any monkeypatched test above.
    """
    monkeypatch.setattr(twitch_bundle, "_redis_client", None)
    monkeypatch.setenv("VALKEY_URL", "redis://example-valkey:6379/0")

    client = _get_redis_client({})

    assert client is not None
    # Cached -- a second call returns the SAME instance, not a fresh connection.
    assert _get_redis_client({}) is client


async def test_transport_non_retryable_error_maps_to_dispatch_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A `NonRetryableTransportError` from the shared transport maps to the adapter's own type.

    Callers (`services/adapters/bundle.py::dispatch`) only ever catch the
    `*DispatchError` family, never `waddle_transports`' own error types
    directly.
    """

    async def _raise(self, *, channel: str, text: str):  # noqa: ANN001, ANN202, ARG001
        raise NonRetryableTransportError("bad channel", http_status=400)

    monkeypatch.setattr(twitch_bundle.RelayOutboundIrcTransport, "send", _raise)

    async with _noop_http_client() as client:
        with pytest.raises(NonRetryableDispatchError, match="bad channel"):
            await send_message(_envelope(), _config(), http_client=client)


async def test_transport_retryable_error_maps_to_dispatch_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _raise(self, *, channel: str, text: str):  # noqa: ANN001, ANN202, ARG001
        raise RetryableTransportError("valkey unavailable", http_status=503)

    monkeypatch.setattr(twitch_bundle.RelayOutboundIrcTransport, "send", _raise)

    async with _noop_http_client() as client:
        with pytest.raises(RetryableDispatchError, match="valkey unavailable"):
            await send_message(_envelope(), _config(), http_client=client)
