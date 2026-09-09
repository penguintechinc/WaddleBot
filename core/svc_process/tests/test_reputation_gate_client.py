"""Tests for `services.reputation_gate_client` -- the real HTTP client to `reputation_module`.

Mocks `httpx.AsyncClient.post` (the ONE call this module ever makes),
mirroring `core/svc_streaming/tests/test_token_ledger_client.py`'s own
established pattern for this exact shape of real-HTTP-client test: asserts
the exact URL/payload/headers built for a given call, and every branch of
the graceful-degradation outcome mapping (200 / non-2xx / unreachable /
malformed body / application-level failure).
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from services.reputation_gate_client import (
    ReputationGateClient,
    get_reputation_service,
    reset_for_tests,
)


class _FakeResponse:
    def __init__(self, status_code: int, json_body: Any) -> None:
        self.status_code = status_code
        self._json_body = json_body
        self.text = str(json_body)

    def json(self) -> Any:
        if isinstance(self._json_body, Exception):
            raise self._json_body
        return self._json_body


class TestAdjustSuccess:
    async def test_adjust_success_builds_correct_request_and_returns_ok(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        captured: dict[str, Any] = {}

        async def fake_post(self: httpx.AsyncClient, url: str, **kwargs: Any) -> _FakeResponse:
            captured["url"] = url
            captured["headers"] = kwargs["headers"]
            captured["json"] = kwargs["json"]
            return _FakeResponse(200, {"success": True, "data": {"total": 1, "failed": 0}})

        monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

        client = ReputationGateClient(
            base_url="http://reputation-test.invalid:8021", service_api_key="sekrit"
        )
        result = await client.adjust(
            community_id=42,
            user_id=None,
            event_type="warn",
            platform="twitch",
            platform_user_id="u-1",
            metadata={"moderation_category": "hate_speech"},
            reason="content moderation match: hate_speech",
            amount_multiplier=1.0,
        )

        assert result.ok is True
        assert result.error is None
        assert captured["url"] == "http://reputation-test.invalid:8021/api/v1/internal/events"
        assert captured["headers"] == {"X-Service-Key": "sekrit"}
        assert captured["json"] == {
            "community_id": 42,
            "user_id": None,
            "platform": "twitch",
            "platform_user_id": "u-1",
            "event_type": "warn",
            "metadata": {
                "moderation_category": "hate_speech",
                "reason": "content moderation match: hate_speech",
            },
        }

    async def test_reason_not_overwritten_when_metadata_already_carries_one(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        captured: dict[str, Any] = {}

        async def fake_post(self: httpx.AsyncClient, url: str, **kwargs: Any) -> _FakeResponse:
            captured["json"] = kwargs["json"]
            return _FakeResponse(200, {"success": True, "data": {"total": 1, "failed": 0}})

        monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

        client = ReputationGateClient(base_url="http://reputation-test.invalid:8021")
        await client.adjust(
            community_id=1,
            user_id=None,
            event_type="warn",
            platform="discord",
            platform_user_id="u-2",
            metadata={"reason": "explicit metadata reason"},
            reason="gate-level reason",
        )

        assert captured["json"]["metadata"]["reason"] == "explicit metadata reason"

    async def test_amount_multiplier_is_never_sent_over_the_wire(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        captured: dict[str, Any] = {}

        async def fake_post(self: httpx.AsyncClient, url: str, **kwargs: Any) -> _FakeResponse:
            captured["json"] = kwargs["json"]
            return _FakeResponse(200, {"success": True, "data": {"total": 1, "failed": 0}})

        monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

        client = ReputationGateClient(base_url="http://reputation-test.invalid:8021")
        await client.adjust(
            community_id=1,
            user_id=None,
            event_type="warn",
            platform="discord",
            platform_user_id="u-2",
            amount_multiplier=3.5,
        )

        assert "amount_multiplier" not in captured["json"]


class TestGracefulDegradation:
    """Every branch degrades to `ok=False` -- never raise (the poll_failed lesson)."""

    async def test_network_failure_never_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        async def fake_post(self: httpx.AsyncClient, url: str, **kwargs: Any) -> _FakeResponse:
            raise httpx.ConnectError("connection refused")

        monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

        client = ReputationGateClient(base_url="http://reputation-test.invalid:8021")
        result = await client.adjust(
            community_id=1,
            user_id=None,
            event_type="warn",
            platform="discord",
            platform_user_id="u-2",
        )

        assert result.ok is False
        assert result.error is not None

    async def test_timeout_never_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        async def fake_post(self: httpx.AsyncClient, url: str, **kwargs: Any) -> _FakeResponse:
            raise httpx.ReadTimeout("timeout")

        monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

        client = ReputationGateClient(base_url="http://reputation-test.invalid:8021")
        result = await client.adjust(
            community_id=1,
            user_id=None,
            event_type="warn",
            platform="discord",
            platform_user_id="u-2",
        )
        assert result.ok is False

    async def test_non_2xx_status_degrades_to_ok_false(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def fake_post(self: httpx.AsyncClient, url: str, **kwargs: Any) -> _FakeResponse:
            return _FakeResponse(401, {"success": False, "error": "Unauthorized"})

        monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

        client = ReputationGateClient(base_url="http://reputation-test.invalid:8021")
        result = await client.adjust(
            community_id=1,
            user_id=None,
            event_type="warn",
            platform="discord",
            platform_user_id="u-2",
        )

        assert result.ok is False
        assert "401" in (result.error or "")

    async def test_malformed_json_response_degrades_to_ok_false(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def fake_post(self: httpx.AsyncClient, url: str, **kwargs: Any) -> _FakeResponse:
            return _FakeResponse(200, ValueError("not json"))

        monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

        client = ReputationGateClient(base_url="http://reputation-test.invalid:8021")
        result = await client.adjust(
            community_id=1,
            user_id=None,
            event_type="warn",
            platform="discord",
            platform_user_id="u-2",
        )

        assert result.ok is False

    async def test_application_level_failed_event_degrades_to_ok_false(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """reputation_module accepted the HTTP request but reported `failed >= 1` in the body."""

        async def fake_post(self: httpx.AsyncClient, url: str, **kwargs: Any) -> _FakeResponse:
            return _FakeResponse(
                200, {"success": True, "data": {"total": 1, "processed": 0, "failed": 1}}
            )

        monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

        client = ReputationGateClient(base_url="http://reputation-test.invalid:8021")
        result = await client.adjust(
            community_id=1,
            user_id=None,
            event_type="warn",
            platform="discord",
            platform_user_id="u-2",
        )

        assert result.ok is False


class TestGetReputationService:
    def teardown_method(self) -> None:
        reset_for_tests()

    def test_returns_a_reputation_gate_client(self) -> None:
        reset_for_tests()
        service = get_reputation_service()
        assert isinstance(service, ReputationGateClient)

    def test_singleton_reused_across_calls(self) -> None:
        reset_for_tests()
        first = get_reputation_service()
        second = get_reputation_service()
        assert first is second

    def test_reset_for_tests_clears_singleton(self) -> None:
        reset_for_tests()
        first = get_reputation_service()
        reset_for_tests()
        second = get_reputation_service()
        assert first is not second


class TestConfigDefaults:
    def test_constructor_defaults_come_from_config(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import services.reputation_gate_client as gate_client_module

        monkeypatch.setattr(
            gate_client_module.Config, "REPUTATION_API_URL", "http://from-config.invalid:9000"
        )
        monkeypatch.setattr(gate_client_module.Config, "SERVICE_API_KEY", "config-key")

        client = gate_client_module.ReputationGateClient()

        assert client._base_url == "http://from-config.invalid:9000"  # noqa: SLF001
        assert client._service_api_key == "config-key"  # noqa: SLF001

    def test_constructor_args_override_config_defaults(self) -> None:
        client = ReputationGateClient(
            base_url="http://explicit.invalid:1234", service_api_key="explicit-key"
        )

        assert client._base_url == "http://explicit.invalid:1234"  # noqa: SLF001
        assert client._service_api_key == "explicit-key"  # noqa: SLF001
