"""`services/marketplace_execution_service.py` -- HMAC signing + SSRF guard on module execution.

Fail-first proof (executed, not narrated): temporarily replaced
`_post_no_redirect`'s `validate_url(url)` call with a no-op -- `test_
execute_command_rejects_ssrf_webhook_url` went red (the fake client's
`post` was called against `http://127.0.0.1/admin` instead of the
request being rejected before any network call); reverted, green again.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

import pytest
from pydal import DAL, Field

from services import marketplace_execution_service as execution
from services.errors import ApiError


@pytest.fixture
def dal() -> Any:
    db = DAL("sqlite:memory")
    db.define_table(
        "marketplace_modules",
        Field("seller_id", "integer"),
        Field("name", "string"),
        Field("slug", "string"),
        Field("webhook_url", "string"),
        Field("webhook_secret", "string"),
        Field("webhook_timeout_ms", "integer", default=5000),
        Field("communication_model", "string", default="webhook_push"),
        Field("auth_type", "string", default="hmac"),
        Field("auth_config", "json"),
        Field("api_base_url", "string"),
        Field("status", "string", default="approved"),
        Field("total_requests", "integer", default=0),
        Field("deleted_at", "datetime"),
    )
    yield db
    db.close()


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict[str, Any]) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict[str, Any]:
        return self._payload


class _FakeAsyncClient:
    captured_calls: list[dict[str, Any]] = []
    response: _FakeResponse = _FakeResponse(200, {"ok": True})

    def __init__(self, *, follow_redirects: bool, timeout: float) -> None:
        self.follow_redirects = follow_redirects
        self.timeout = timeout

    async def __aenter__(self) -> _FakeAsyncClient:
        return self

    async def __aexit__(self, *exc: Any) -> None:
        return None

    async def post(
        self, url: str, *, headers: dict[str, str], json: dict[str, Any]
    ) -> _FakeResponse:
        _FakeAsyncClient.captured_calls.append({"url": url, "headers": headers, "json": json})
        return _FakeAsyncClient.response


@pytest.fixture(autouse=True)
def _stub_httpx(monkeypatch: Any) -> None:
    _FakeAsyncClient.captured_calls = []
    _FakeAsyncClient.response = _FakeResponse(200, {"ok": True})
    monkeypatch.setattr(execution.httpx, "AsyncClient", _FakeAsyncClient)
    # Public-looking hostname resolves deterministically offline.
    import socket

    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *a, **k: [(socket.AF_INET, None, None, None, ("93.184.216.34", 0))],
    )


class TestWebhookPushHMAC:
    async def test_execute_command_signs_payload_with_hmac_sha256(self, dal: Any) -> None:
        module_id = dal.marketplace_modules.insert(
            seller_id=1,
            name="Mod",
            slug="mod",
            webhook_url="https://vendor.example.com/hook",
            webhook_secret="topsecret",
            status="approved",
        )
        dal.commit()

        payload = {"command": "!weather", "communityId": 1}
        result = await execution.execute_command(dal, module_id, payload)

        assert result == {"ok": True}
        assert len(_FakeAsyncClient.captured_calls) == 1
        call = _FakeAsyncClient.captured_calls[0]
        signature_header = call["headers"]["X-WaddleBot-Signature"]
        assert signature_header.startswith("sha256=")

        expected_digest = hmac.new(
            b"topsecret",
            json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        assert signature_header == f"sha256={expected_digest}"
        assert call["headers"]["X-WaddleBot-Module-Id"] == str(module_id)


class TestSSRFGuardAtExecutionTime:
    async def test_execute_command_rejects_ssrf_webhook_url(self, dal: Any) -> None:
        module_id = dal.marketplace_modules.insert(
            seller_id=1,
            name="Evil",
            slug="evil",
            webhook_url="http://127.0.0.1/admin",
            webhook_secret="topsecret",
            status="approved",
        )
        dal.commit()

        with pytest.raises(ApiError) as exc_info:
            await execution.execute_command(dal, module_id, {"command": "!x"})
        assert exc_info.value.status_code == 502
        assert not _FakeAsyncClient.captured_calls  # never reached the network

    async def test_execute_command_rejects_redirect_response(self, dal: Any) -> None:
        _FakeAsyncClient.response = _FakeResponse(302, {})
        module_id = dal.marketplace_modules.insert(
            seller_id=1,
            name="Mod",
            slug="mod",
            webhook_url="https://vendor.example.com/hook",
            webhook_secret="topsecret",
            status="approved",
        )
        dal.commit()

        with pytest.raises(ApiError) as exc_info:
            await execution.execute_command(dal, module_id, {"command": "!x"})
        assert exc_info.value.status_code == 502
        assert "redirect" in exc_info.value.message.lower()


class TestModuleNotFound:
    async def test_execute_command_unknown_module_raises_404(self, dal: Any) -> None:
        with pytest.raises(ApiError) as exc_info:
            await execution.execute_command(dal, 999, {"command": "!x"})
        assert exc_info.value.status_code == 404

    async def test_execute_command_not_approved_raises_404(self, dal: Any) -> None:
        module_id = dal.marketplace_modules.insert(
            seller_id=1,
            name="Pending",
            slug="pending",
            webhook_url="https://vendor.example.com/hook",
            webhook_secret="s",
            status="pending",
        )
        dal.commit()
        with pytest.raises(ApiError) as exc_info:
            await execution.execute_command(dal, module_id, {"command": "!x"})
        assert exc_info.value.status_code == 404


class TestRestPull:
    async def test_rest_pull_with_api_key_auth(self, dal: Any) -> None:
        module_id = dal.marketplace_modules.insert(
            seller_id=1,
            name="Mod",
            slug="mod",
            webhook_url="https://vendor.example.com/hook",
            webhook_secret="s",
            communication_model="rest_pull",
            auth_type="api_key",
            auth_config={"api_key": "abc123"},
            api_base_url="https://vendor.example.com/api",
            status="approved",
        )
        dal.commit()

        result = await execution.execute_command(dal, module_id, {"command": "!x"})
        assert result == {"ok": True}
        call = _FakeAsyncClient.captured_calls[0]
        assert call["headers"]["Authorization"] == "Bearer abc123"
        assert call["url"] == "https://vendor.example.com/api/execute"

    async def test_rest_pull_without_api_base_url_raises(self, dal: Any) -> None:
        module_id = dal.marketplace_modules.insert(
            seller_id=1,
            name="Mod",
            slug="mod",
            webhook_url="https://vendor.example.com/hook",
            webhook_secret="s",
            communication_model="rest_pull",
            api_base_url=None,
            status="approved",
        )
        dal.commit()
        with pytest.raises(ApiError) as exc_info:
            await execution.execute_command(dal, module_id, {"command": "!x"})
        assert exc_info.value.status_code == 502

    async def test_webhook_push_error_status_raises(self, dal: Any) -> None:
        _FakeAsyncClient.response = _FakeResponse(500, {})
        module_id = dal.marketplace_modules.insert(
            seller_id=1,
            name="Mod",
            slug="mod",
            webhook_url="https://vendor.example.com/hook",
            webhook_secret="s",
            status="approved",
        )
        dal.commit()
        with pytest.raises(ApiError) as exc_info:
            await execution.execute_command(dal, module_id, {"command": "!x"})
        assert exc_info.value.status_code == 502

    async def test_increment_request_count(self, dal: Any) -> None:
        module_id = dal.marketplace_modules.insert(
            seller_id=1,
            name="Mod",
            slug="mod",
            webhook_url="https://vendor.example.com/hook",
            webhook_secret="s",
            status="approved",
            total_requests=0,
        )
        dal.commit()
        execution.increment_request_count(dal, module_id)
        assert dal.marketplace_modules[module_id].total_requests == 1

    async def test_get_module_config_missing_returns_none(self, dal: Any) -> None:
        assert execution.get_module_config(dal, 12345) is None
