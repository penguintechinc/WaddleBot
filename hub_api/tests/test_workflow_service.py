"""`services/workflow_service.py` -- unit tests for the real HTTP client + owned license logic.

`tests/test_v1_workflow_blueprint.py` monkeypatches `WorkflowCoreProxyClient`
entirely (`FakeWorkflowCore`, no real network I/O) -- which means the
actual `httpx` call and success/failure/timeout branching inside
`WorkflowCoreProxyClient.request()` is exercised nowhere else. This file
closes that gap with `httpx.MockTransport` (real `httpx` request/response
objects, no real socket), mirroring `tests/test_event_calendar_proxy.py`'s
own pattern for the sibling Event group's proxy client. Also covers
`validate_license()`'s DB-driven branches directly (no HTTP involved).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest
from pydal import DAL, Field

from services.errors import ApiError
from services.workflow_service import (
    ProxyResult,
    WorkflowCoreProxyClient,
    error_from_proxy,
    validate_license,
)


def _patch_transport(
    monkeypatch: pytest.MonkeyPatch, handler: Callable[[httpx.Request], httpx.Response]
) -> None:
    """Force every `httpx.AsyncClient` in `workflow_service.py` onto a mock transport."""
    transport = httpx.MockTransport(handler)
    original_init = httpx.AsyncClient.__init__

    def patched_init(self: httpx.AsyncClient, *args: object, **kwargs: object) -> None:
        kwargs["transport"] = transport
        original_init(self, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(httpx.AsyncClient, "__init__", patched_init)


class TestWorkflowCoreProxyClientRequest:
    async def test_success_relays_status_and_body(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"id": "wf-1", "name": "My Workflow"})

        _patch_transport(monkeypatch, handler)
        client = WorkflowCoreProxyClient(base_url="http://workflow-core:8070")
        result = await client.request("GET", "/workflows/wf-1")
        assert result == ProxyResult(
            ok=True, status_code=200, body={"id": "wf-1", "name": "My Workflow"}
        )

    async def test_sends_expected_method_and_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured: dict[str, object] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["method"] = request.method
            captured["url"] = str(request.url)
            return httpx.Response(201, json={})

        _patch_transport(monkeypatch, handler)
        client = WorkflowCoreProxyClient(base_url="http://workflow-core:8070")
        await client.request("POST", "/workflows", json_body={"name": "x"})
        assert captured["method"] == "POST"
        assert captured["url"] == "http://workflow-core:8070/api/v1/workflows"

    async def test_query_params_are_forwarded(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured: dict[str, object] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["query"] = dict(request.url.params)
            return httpx.Response(200, json={})

        _patch_transport(monkeypatch, handler)
        client = WorkflowCoreProxyClient(base_url="http://workflow-core:8070")
        await client.request("GET", "/workflows", params={"communityId": 1, "page": 2})
        assert captured["query"] == {"communityId": "1", "page": "2"}

    async def test_downstream_4xx_is_ok_false_with_relayed_status(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404, json={"message": "not found"})

        _patch_transport(monkeypatch, handler)
        client = WorkflowCoreProxyClient(base_url="http://workflow-core:8070")
        result = await client.request("GET", "/workflows/missing")
        assert result.ok is False
        assert result.status_code == 404
        assert result.body == {"message": "not found"}

    async def test_non_json_response_body_is_none_not_a_crash(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=b"not json")

        _patch_transport(monkeypatch, handler)
        client = WorkflowCoreProxyClient(base_url="http://workflow-core:8070")
        result = await client.request("GET", "/workflows")
        assert result.ok is True
        assert result.body is None

    async def test_transport_error_raises_service_unavailable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectTimeout("connection timed out", request=request)

        _patch_transport(monkeypatch, handler)
        client = WorkflowCoreProxyClient(base_url="http://workflow-core:8070")
        with pytest.raises(ApiError) as exc_info:
            await client.request("GET", "/workflows")
        assert exc_info.value.status_code == 500
        assert exc_info.value.code == "SERVICE_UNAVAILABLE"

    def test_base_url_defaults_to_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("WORKFLOW_CORE_URL", "http://workflow-core.svc:9000")
        client = WorkflowCoreProxyClient()
        assert client._base_url == "http://workflow-core.svc:9000"  # noqa: SLF001


class TestErrorFromProxy:
    def test_404_maps_to_not_found(self) -> None:
        result = ProxyResult(ok=False, status_code=404, body={"message": "gone"})
        err = error_from_proxy(result, not_found_message="Widget not found")
        assert err.status_code == 404
        assert err.message == "Widget not found"

    def test_non_404_maps_to_generic_internal_error_with_relayed_message(self) -> None:
        result = ProxyResult(ok=False, status_code=500, body={"message": "boom"})
        err = error_from_proxy(result, not_found_message="Widget not found")
        assert err.status_code == 500
        assert err.code == "INTERNAL_ERROR"
        assert err.message == "boom"

    def test_non_dict_body_falls_back_to_generic_message(self) -> None:
        result = ProxyResult(ok=False, status_code=500, body=None)
        err = error_from_proxy(result, not_found_message="Widget not found")
        assert err.message == "Workflow service error"


@pytest.fixture
def communities_dal() -> Any:
    dal = DAL("sqlite:memory")
    dal.define_table(
        "communities",
        Field("license_key", "string"),
        Field("license_expires_at", "datetime"),
        Field("license_tier", "string"),
    )
    yield dal
    dal.close()


class _SyncAsAsync:
    """Wraps a sync pydal `DAL` so `select_async(query)` works without a real `AsyncDAL`."""

    def __init__(self, dal: Any) -> None:
        self.dal = dal

    async def select_async(self, query: Any) -> Any:
        return query.select()


class TestValidateLicense:
    async def test_community_not_found(self, communities_dal: Any) -> None:
        async_dal = _SyncAsAsync(communities_dal)
        result = await validate_license(async_dal, communities_dal, community_id=999)
        assert result.valid is False
        assert result.reason == "Community not found"

    async def test_no_license_key(self, communities_dal: Any) -> None:
        cid = communities_dal.communities.insert(license_key=None)
        async_dal = _SyncAsAsync(communities_dal)
        result = await validate_license(async_dal, communities_dal, community_id=cid)
        assert result.valid is False
        assert result.reason == "No license configured"

    async def test_expired_license(self, communities_dal: Any) -> None:
        cid = communities_dal.communities.insert(
            license_key="lic-1",
            license_expires_at=datetime.now(UTC) - timedelta(days=1),
            license_tier="pro",
        )
        async_dal = _SyncAsAsync(communities_dal)
        result = await validate_license(async_dal, communities_dal, community_id=cid)
        assert result.valid is False
        assert result.reason == "License expired"

    async def test_unlicensed_tier_rejected(self, communities_dal: Any) -> None:
        cid = communities_dal.communities.insert(license_key="lic-1", license_tier="free")
        async_dal = _SyncAsAsync(communities_dal)
        result = await validate_license(async_dal, communities_dal, community_id=cid)
        assert result.valid is False
        assert result.reason == "Workflows not included in current license tier"

    async def test_valid_license_passes(self, communities_dal: Any) -> None:
        cid = communities_dal.communities.insert(
            license_key="lic-1",
            license_expires_at=datetime.now(UTC) + timedelta(days=30),
            license_tier="enterprise",
        )
        async_dal = _SyncAsAsync(communities_dal)
        result = await validate_license(async_dal, communities_dal, community_id=cid)
        assert result.valid is True
        assert result.reason is None

    async def test_naive_expires_at_does_not_crash(self, communities_dal: Any) -> None:
        """`_is_expired()` handles a naive (non-tz-aware) `license_expires_at` too."""
        cid = communities_dal.communities.insert(
            license_key="lic-1",
            license_expires_at=datetime.now() + timedelta(days=30),  # noqa: DTZ005
            license_tier="pro",
        )
        async_dal = _SyncAsAsync(communities_dal)
        result = await validate_license(async_dal, communities_dal, community_id=cid)
        assert result.valid is True
