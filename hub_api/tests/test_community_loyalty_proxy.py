"""`services/community_loyalty.py` -- direct unit tests, real `_proxy`/`get_or_default`/`call`.

Same rationale as `test_community_engagement_proxy.py`: mocks
`httpx.AsyncClient` (the actual I/O boundary), exercises the real
service-layer code `test_community_loyalty.py`'s blueprint-level tests
monkeypatch around.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from services import community_loyalty as loyalty


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict[str, Any]) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict[str, Any]:
        return self._payload


def _mock_client(response: _FakeResponse) -> AsyncMock:
    client = AsyncMock()
    client.request = AsyncMock(return_value=response)
    client.__aenter__.return_value = client
    client.__aexit__.return_value = False
    return client


async def test_get_or_default_passes_through_on_success() -> None:
    with patch(
        "httpx.AsyncClient", return_value=_mock_client(_FakeResponse(200, {"config": {"a": 1}}))
    ):
        data = await loyalty.get_or_default("/x", {"config": {}})
    assert data == {"config": {"a": 1}}


async def test_get_or_default_merges_defaults_on_connection_failure() -> None:
    client = AsyncMock()
    client.request = AsyncMock(side_effect=httpx.ConnectError("refused"))
    client.__aenter__.return_value = client
    client.__aexit__.return_value = False
    with patch("httpx.AsyncClient", return_value=client):
        data = await loyalty.get_or_default("/x", {"stats": {"total": 0}})
    assert data == {"success": True, "unavailable": True, "stats": {"total": 0}}


async def test_call_raises_on_non_2xx_with_error_field() -> None:
    with patch(
        "httpx.AsyncClient", return_value=_mock_client(_FakeResponse(400, {"error": "bad input"}))
    ):
        with pytest.raises(loyalty.LoyaltyProxyError, match="bad input"):
            await loyalty.call("POST", "/x", json_body={})


async def test_call_raises_generic_message_when_no_error_field() -> None:
    with patch("httpx.AsyncClient", return_value=_mock_client(_FakeResponse(500, {}))):
        with pytest.raises(loyalty.LoyaltyProxyError, match="Loyalty module request failed"):
            await loyalty.call("POST", "/x")


async def test_call_succeeds_and_sends_service_key_header(monkeypatch: Any) -> None:
    monkeypatch.setenv("SERVICE_API_KEY", "sekrit")
    mock = _mock_client(_FakeResponse(200, {"success": True}))
    with patch("httpx.AsyncClient", return_value=mock):
        data = await loyalty.call("PUT", "/x", json_body={"a": 1})
    assert data == {"success": True}
    assert mock.request.call_args.kwargs["headers"]["X-API-Key"] == "sekrit"


async def test_proxy_handles_non_json_response_body() -> None:
    class _BadJson(_FakeResponse):
        def json(self) -> dict[str, Any]:
            raise ValueError("not json")

    with patch("httpx.AsyncClient", return_value=_mock_client(_BadJson(200, {}))):
        data = await loyalty.call("GET", "/x")
    assert data == {}
