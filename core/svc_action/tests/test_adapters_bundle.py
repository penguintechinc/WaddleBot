"""services/adapters/bundle.py -- loads+invokes a bundle-declared script entrypoint."""

from __future__ import annotations

import httpx
import pytest

from services.action_target import ActionTarget
from services.adapters import bundle
from services.adapters.base import AdapterResult, NonRetryableDispatchError, RetryableDispatchError
from services.envelope import ActionEnvelope


def _envelope(payload: dict | None = None) -> ActionEnvelope:
    return ActionEnvelope(
        tenant="1",
        community="42",
        app_id="waddles.bot.discord.default",
        stage="action",
        payload=payload or {"text": "hello"},
        ts="2026-08-31T12:00:00Z",
        raw="{}",
    )


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.MockTransport(lambda r: httpx.Response(200)), follow_redirects=False
    )


async def test_unresolvable_entrypoint_is_non_retryable() -> None:
    target = ActionTarget(type="bundle", entrypoint="not.a.real.module:fn")
    async with _client() as client:
        with pytest.raises(NonRetryableDispatchError, match="entrypoint load failed"):
            await bundle.dispatch(target, _envelope(), http_client=client)


async def test_malformed_entrypoint_string_is_non_retryable() -> None:
    target = ActionTarget(type="bundle", entrypoint="no-colon-here")
    async with _client() as client:
        with pytest.raises(NonRetryableDispatchError, match="entrypoint load failed"):
            await bundle.dispatch(target, _envelope(), http_client=client)


async def test_loads_and_invokes_real_entrypoint(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail-first verification: the adapter genuinely imports+calls a module function."""
    import sys
    import types

    calls = {}

    async def _fake_send(envelope, config, *, http_client):  # noqa: ANN001, ANN202
        calls["envelope"] = envelope
        calls["config"] = config
        calls["http_client"] = http_client
        return AdapterResult(target_type="bundle", detail="sent", http_status=200)

    fake_module = types.ModuleType("tests_fake_bundle_module")
    fake_module.send = _fake_send  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "tests_fake_bundle_module", fake_module)

    target = ActionTarget(
        type="bundle", entrypoint="tests_fake_bundle_module:send", bundle_config={"k": "v"}
    )
    envelope = _envelope()
    async with _client() as client:
        result = await bundle.dispatch(target, envelope, http_client=client)

    assert result.detail == "sent"
    assert calls["envelope"] is envelope
    assert calls["config"] == {"k": "v"}
    assert calls["http_client"] is client


async def test_transport_result_is_normalized_to_adapter_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A bundle script returning `waddle_transports.TransportResult` directly.

    (e.g. `twitch_send_action.py`) is normalized to `AdapterResult`
    before `dispatch()` returns.
    """
    import sys
    import types

    from waddle_transports import TransportResult

    async def _fake_send(envelope, config, *, http_client):  # noqa: ANN001, ANN202, ARG001
        return TransportResult(transport="irc", detail="relayed", http_status=None)

    fake_module = types.ModuleType("tests_fake_bundle_transport_result")
    fake_module.send = _fake_send  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "tests_fake_bundle_transport_result", fake_module)

    target = ActionTarget(type="bundle", entrypoint="tests_fake_bundle_transport_result:send")
    async with _client() as client:
        result = await bundle.dispatch(target, _envelope(), http_client=client)

    assert isinstance(result, AdapterResult)
    assert result.target_type == "irc"
    assert result.detail == "relayed"


async def test_bundle_raising_retryable_propagates() -> None:
    import sys
    import types

    async def _fake_send(envelope, config, *, http_client):  # noqa: ANN001, ANN202, ARG001
        raise RetryableDispatchError("upstream 503")

    fake_module = types.ModuleType("tests_fake_bundle_retryable")
    fake_module.send = _fake_send  # type: ignore[attr-defined]
    sys.modules["tests_fake_bundle_retryable"] = fake_module
    try:
        target = ActionTarget(type="bundle", entrypoint="tests_fake_bundle_retryable:send")
        async with _client() as client:
            with pytest.raises(RetryableDispatchError, match="upstream 503"):
                await bundle.dispatch(target, _envelope(), http_client=client)
    finally:
        del sys.modules["tests_fake_bundle_retryable"]


async def test_bundle_bug_is_wrapped_non_retryable() -> None:
    import sys
    import types

    async def _fake_send(envelope, config, *, http_client):  # noqa: ANN001, ANN202, ARG001
        raise ValueError("unrelated bug")

    fake_module = types.ModuleType("tests_fake_bundle_buggy")
    fake_module.send = _fake_send  # type: ignore[attr-defined]
    sys.modules["tests_fake_bundle_buggy"] = fake_module
    try:
        target = ActionTarget(type="bundle", entrypoint="tests_fake_bundle_buggy:send")
        async with _client() as client:
            with pytest.raises(NonRetryableDispatchError, match="raised: unrelated bug"):
                await bundle.dispatch(target, _envelope(), http_client=client)
    finally:
        del sys.modules["tests_fake_bundle_buggy"]


async def test_bundle_returning_wrong_type_is_non_retryable() -> None:
    import sys
    import types

    async def _fake_send(envelope, config, *, http_client):  # noqa: ANN001, ANN202, ARG001
        return {"not": "an AdapterResult"}

    fake_module = types.ModuleType("tests_fake_bundle_badreturn")
    fake_module.send = _fake_send  # type: ignore[attr-defined]
    sys.modules["tests_fake_bundle_badreturn"] = fake_module
    try:
        target = ActionTarget(type="bundle", entrypoint="tests_fake_bundle_badreturn:send")
        async with _client() as client:
            with pytest.raises(NonRetryableDispatchError, match="expected AdapterResult"):
                await bundle.dispatch(target, _envelope(), http_client=client)
    finally:
        del sys.modules["tests_fake_bundle_badreturn"]
