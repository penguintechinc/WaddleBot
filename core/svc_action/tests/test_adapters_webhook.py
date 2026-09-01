"""services/adapters/webhook.py -- SSRF-guarded, HMAC-signed dispatch."""

from __future__ import annotations

import hashlib
import hmac
import json

import httpx
import pytest

from services.action_target import ActionTarget
from services.adapters import webhook
from services.adapters.base import NonRetryableDispatchError, RetryableDispatchError
from services.envelope import ActionEnvelope


def _envelope(payload: dict | None = None) -> ActionEnvelope:
    return ActionEnvelope(
        tenant="1",
        community="42",
        app_id="waddles.bot.shoutout.default",
        stage="action",
        payload=payload or {"user": "alice", "message": "hi"},
        ts="2026-08-31T12:00:00Z",
        raw="{}",
    )


def _target(url: str = "https://8.8.8.8/hook") -> ActionTarget:
    return ActionTarget(type="webhook", url=url, secret_ref="TEST_WEBHOOK_SECRET")


def _client(handler) -> httpx.AsyncClient:  # noqa: ANN001
    return httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=False)


async def test_signs_body_with_hmac_sha256(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_WEBHOOK_SECRET", "s3cr3t")
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["signature"] = request.headers["X-Waddle-Signature"]
        captured["body"] = request.content
        return httpx.Response(200)

    async with _client(handler) as client:
        result = await webhook.dispatch(
            _target(), _envelope(), timeout_seconds=5.0, client=client
        )

    expected_sig = hmac.new(b"s3cr3t", captured["body"], hashlib.sha256).hexdigest()
    assert captured["signature"] == expected_sig
    assert result.target_type == "webhook"
    assert result.http_status == 200


async def test_missing_secret_is_non_retryable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TEST_WEBHOOK_SECRET", raising=False)

    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("must not send a request without a resolvable secret")

    async with _client(handler) as client:
        with pytest.raises(NonRetryableDispatchError):
            await webhook.dispatch(_target(), _envelope(), timeout_seconds=5.0, client=client)


@pytest.mark.parametrize("status", [401, 403])
async def test_auth_rejection_is_non_retryable(monkeypatch: pytest.MonkeyPatch, status: int) -> None:
    monkeypatch.setenv("TEST_WEBHOOK_SECRET", "s3cr3t")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status)

    async with _client(handler) as client:
        with pytest.raises(NonRetryableDispatchError):
            await webhook.dispatch(_target(), _envelope(), timeout_seconds=5.0, client=client)


async def test_other_4xx_is_non_retryable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_WEBHOOK_SECRET", "s3cr3t")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422)

    async with _client(handler) as client:
        with pytest.raises(NonRetryableDispatchError):
            await webhook.dispatch(_target(), _envelope(), timeout_seconds=5.0, client=client)


async def test_5xx_is_retryable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_WEBHOOK_SECRET", "s3cr3t")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    async with _client(handler) as client:
        with pytest.raises(RetryableDispatchError):
            await webhook.dispatch(_target(), _envelope(), timeout_seconds=5.0, client=client)


async def test_network_error_is_retryable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_WEBHOOK_SECRET", "s3cr3t")

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    async with _client(handler) as client:
        with pytest.raises(RetryableDispatchError):
            await webhook.dispatch(_target(), _envelope(), timeout_seconds=5.0, client=client)


async def test_private_host_target_is_blocked_non_retryable(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail-first-verify case: SSRF guard blocks a private-host webhook target."""
    monkeypatch.setenv("TEST_WEBHOOK_SECRET", "s3cr3t")
    called = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return httpx.Response(200)

    async with _client(handler) as client:
        with pytest.raises(NonRetryableDispatchError, match="SSRF"):
            await webhook.dispatch(
                _target(url="http://169.254.169.254/latest/meta-data/"),
                _envelope(),
                timeout_seconds=5.0,
                client=client,
            )
    assert called is False


async def test_body_template_rendered_against_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_WEBHOOK_SECRET", "s3cr3t")
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = request.content
        return httpx.Response(200)

    target = ActionTarget(
        type="webhook",
        url="https://8.8.8.8/hook",
        secret_ref="TEST_WEBHOOK_SECRET",
        body_template='{"greeting": "hi {{user}}"}',
    )
    async with _client(handler) as client:
        await webhook.dispatch(target, _envelope(), timeout_seconds=5.0, client=client)

    assert json.loads(captured["body"]) == {"greeting": "hi alice"}
