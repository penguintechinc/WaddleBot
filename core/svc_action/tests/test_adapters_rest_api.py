"""services/adapters/rest_api.py -- SSRF-guarded, configurable-method dispatch."""

from __future__ import annotations

import httpx
import pytest

from services.action_target import ActionTarget
from services.adapters import rest_api
from services.adapters.base import NonRetryableDispatchError, RetryableDispatchError
from services.envelope import ActionEnvelope


def _envelope() -> ActionEnvelope:
    return ActionEnvelope(
        tenant="1",
        community="42",
        app_id="waddles.bot.shoutout.default",
        stage="action",
        payload={"user": "alice"},
        ts="2026-08-31T12:00:00Z",
        raw="{}",
    )


def _client(handler) -> httpx.AsyncClient:  # noqa: ANN001
    return httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=False)


async def test_get_sends_no_body() -> None:
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["body"] = request.content
        return httpx.Response(200)

    target = ActionTarget(type="rest_api", url="https://8.8.8.8/api", method="GET")
    async with _client(handler) as client:
        result = await rest_api.dispatch(target, _envelope(), timeout_seconds=5.0, client=client)

    assert captured["method"] == "GET"
    assert captured["body"] == b""
    assert result.http_status == 200


async def test_post_sends_json_payload_body() -> None:
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = request.content
        captured["content_type"] = request.headers.get("content-type")
        return httpx.Response(201)

    target = ActionTarget(type="rest_api", url="https://8.8.8.8/api", method="POST")
    async with _client(handler) as client:
        result = await rest_api.dispatch(target, _envelope(), timeout_seconds=5.0, client=client)

    assert captured["body"] == b'{"user": "alice"}'
    assert captured["content_type"] == "application/json"
    assert result.http_status == 201


@pytest.mark.parametrize("status", [401, 403, 400])
async def test_4xx_is_non_retryable(status: int) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status)

    target = ActionTarget(type="rest_api", url="https://8.8.8.8/api", method="POST")
    async with _client(handler) as client:
        with pytest.raises(NonRetryableDispatchError):
            await rest_api.dispatch(target, _envelope(), timeout_seconds=5.0, client=client)


async def test_5xx_is_retryable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    target = ActionTarget(type="rest_api", url="https://8.8.8.8/api", method="POST")
    async with _client(handler) as client:
        with pytest.raises(RetryableDispatchError):
            await rest_api.dispatch(target, _envelope(), timeout_seconds=5.0, client=client)


async def test_network_error_is_retryable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    target = ActionTarget(type="rest_api", url="https://8.8.8.8/api", method="GET")
    async with _client(handler) as client:
        with pytest.raises(RetryableDispatchError):
            await rest_api.dispatch(target, _envelope(), timeout_seconds=5.0, client=client)


async def test_private_target_blocked_non_retryable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("must not be called")

    target = ActionTarget(type="rest_api", url="http://10.0.0.5/internal", method="GET")
    async with _client(handler) as client:
        with pytest.raises(NonRetryableDispatchError, match="SSRF"):
            await rest_api.dispatch(target, _envelope(), timeout_seconds=5.0, client=client)
