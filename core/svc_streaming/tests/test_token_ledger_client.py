"""Real HTTP client tests against hub-api's token-debit endpoint -- the network call is mocked.

Mocks `httpx.AsyncClient.post` (the ONE call this module ever makes) via
monkeypatch -- asserts the exact URL/payload/headers built for a given
call, and every branch of the BLOCK-WITH-FALLBACK outcome mapping (200 /
402 / unreachable / unexpected status).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import httpx
import pytest

from services.token_ledger_client import (
    REASON_INSUFFICIENT_BALANCE,
    REASON_LEDGER_UNAVAILABLE,
    debit_transcoding_tokens,
)


class _FakeResponse:
    def __init__(self, status_code: int, json_body: dict[str, Any]) -> None:
        self.status_code = status_code
        self._json_body = json_body

    def json(self) -> dict[str, Any]:
        return self._json_body


@pytest.mark.asyncio
async def test_debit_success_builds_correct_request_and_returns_balance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    async def fake_post(self: httpx.AsyncClient, url: str, **kwargs: Any) -> _FakeResponse:
        captured["url"] = url
        captured["headers"] = kwargs["headers"]
        captured["json"] = kwargs["json"]
        return _FakeResponse(200, {"success": True, "balance_after": 55, "transaction_id": 1})

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    result = await debit_transcoding_tokens(
        "http://hub-api-test.invalid:8204",
        bearer_token="the-callers-jwt",
        community_id=7,
        amount=5,
        product_key="transcoding_minutes",
        ref="stream:1:2026-09-01T00:00:00",
    )

    assert result.ok is True
    assert result.balance_after == 55
    assert result.blocked_reason is None
    assert captured["url"] == (
        "http://hub-api-test.invalid:8204/api/v1/marketplace/communities/7/tokens/debit"
    )
    assert captured["headers"] == {"Authorization": "Bearer the-callers-jwt"}
    assert captured["json"] == {
        "product_key": "transcoding_minutes",
        "amount": 5,
        "reason": "svc_streaming_transcode_admission",
        "ref": "stream:1:2026-09-01T00:00:00",
    }


@pytest.mark.asyncio
async def test_debit_insufficient_balance_maps_402_to_blocked_reason(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_post(self: httpx.AsyncClient, url: str, **kwargs: Any) -> _FakeResponse:
        return _FakeResponse(402, {"success": False, "blocked_reason": "insufficient_balance"})

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    result = await debit_transcoding_tokens(
        "http://hub-api-test.invalid:8204",
        bearer_token="tok",
        community_id=7,
        amount=5,
        product_key="transcoding_minutes",
        ref="ref-1",
    )
    assert result.ok is False
    assert result.blocked_reason == REASON_INSUFFICIENT_BALANCE
    assert result.balance_after is None


@pytest.mark.asyncio
async def test_debit_network_failure_is_ledger_unavailable_not_a_raised_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_post(self: httpx.AsyncClient, url: str, **kwargs: Any) -> _FakeResponse:
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    result = await debit_transcoding_tokens(
        "http://hub-api-test.invalid:8204",
        bearer_token="tok",
        community_id=7,
        amount=5,
        product_key="transcoding_minutes",
        ref="ref-2",
    )
    assert result.ok is False
    assert result.blocked_reason == REASON_LEDGER_UNAVAILABLE


@pytest.mark.asyncio
async def test_debit_unexpected_status_degrades_to_ledger_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_post(self: httpx.AsyncClient, url: str, **kwargs: Any) -> _FakeResponse:
        return _FakeResponse(500, {})

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    result = await debit_transcoding_tokens(
        "http://hub-api-test.invalid:8204",
        bearer_token="tok",
        community_id=7,
        amount=5,
        product_key="transcoding_minutes",
        ref="ref-3",
    )
    assert result.ok is False
    assert result.blocked_reason == REASON_LEDGER_UNAVAILABLE


@pytest.mark.asyncio
async def test_debit_never_raises_for_a_blocked_outcome(monkeypatch: pytest.MonkeyPatch) -> None:
    """Contract: callers branch on `.ok`, never wrap this in a try/except for business outcomes."""
    mock_post = AsyncMock(side_effect=httpx.ReadTimeout("timeout"))
    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    result = await debit_transcoding_tokens(
        "http://hub-api-test.invalid:8204",
        bearer_token="tok",
        community_id=7,
        amount=5,
        product_key="transcoding_minutes",
        ref="ref-4",
    )
    assert result.ok is False
