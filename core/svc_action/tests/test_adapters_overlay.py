"""services/adapters/overlay.py -- SSRF-guarded push to svc-presentation."""

from __future__ import annotations

import httpx
import pytest

from services.action_target import ActionTarget
from services.adapters import overlay
from services.adapters.base import NonRetryableDispatchError, RetryableDispatchError
from services.envelope import ActionEnvelope


def _envelope(community: str | None = "42") -> ActionEnvelope:
    return ActionEnvelope(
        tenant="1",
        community=community,
        app_id="waddles.bot.shoutout.default",
        stage="action",
        payload={"entrant_count": 12},
        ts="2026-08-31T12:00:00Z",
        raw="{}",
    )


def _client(handler) -> httpx.AsyncClient:  # noqa: ANN001
    return httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=False)


async def test_pushes_to_community_surface_path() -> None:
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(200)

    target = ActionTarget(type="overlay", surface="giveaway")
    async with _client(handler) as client:
        result = await overlay.dispatch(
            target,
            _envelope(),
            presentation_base_url="https://8.8.8.8",
            timeout_seconds=5.0,
            client=client,
        )

    assert captured["url"] == "https://8.8.8.8/overlay/42/giveaway/push"
    assert result.http_status == 200


async def test_target_community_overrides_envelope_community() -> None:
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(200)

    target = ActionTarget(type="overlay", community="99", surface="giveaway")
    async with _client(handler) as client:
        await overlay.dispatch(
            target,
            _envelope(community="42"),
            presentation_base_url="https://8.8.8.8",
            timeout_seconds=5.0,
            client=client,
        )

    assert captured["url"] == "https://8.8.8.8/overlay/99/giveaway/push"


async def test_no_resolvable_community_raises_non_retryable() -> None:
    target = ActionTarget(type="overlay", surface="giveaway")
    async with _client(lambda r: httpx.Response(200)) as client:
        with pytest.raises(NonRetryableDispatchError, match="community"):
            await overlay.dispatch(
                target,
                _envelope(community=None),
                presentation_base_url="https://8.8.8.8",
                timeout_seconds=5.0,
                client=client,
            )


async def test_network_error_is_retryable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    target = ActionTarget(type="overlay", surface="giveaway")
    async with _client(handler) as client:
        with pytest.raises(RetryableDispatchError):
            await overlay.dispatch(
                target,
                _envelope(),
                presentation_base_url="https://8.8.8.8",
                timeout_seconds=5.0,
                client=client,
            )


async def test_auth_rejection_is_non_retryable() -> None:
    target = ActionTarget(type="overlay", surface="giveaway")
    async with _client(lambda r: httpx.Response(401)) as client:
        with pytest.raises(NonRetryableDispatchError):
            await overlay.dispatch(
                target,
                _envelope(),
                presentation_base_url="https://8.8.8.8",
                timeout_seconds=5.0,
                client=client,
            )


async def test_5xx_is_retryable() -> None:
    target = ActionTarget(type="overlay", surface="giveaway")
    async with _client(lambda r: httpx.Response(503)) as client:
        with pytest.raises(RetryableDispatchError):
            await overlay.dispatch(
                target,
                _envelope(),
                presentation_base_url="https://8.8.8.8",
                timeout_seconds=5.0,
                client=client,
            )


async def test_private_presentation_url_blocked_non_retryable() -> None:
    target = ActionTarget(type="overlay", surface="giveaway")
    async with _client(lambda r: httpx.Response(200)) as client:
        with pytest.raises(NonRetryableDispatchError, match="SSRF"):
            await overlay.dispatch(
                target,
                _envelope(),
                presentation_base_url="http://127.0.0.1:8207",
                timeout_seconds=5.0,
                client=client,
            )
