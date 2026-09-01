"""HTTP-level tests for `/api/v1/streaming/communities/<id>/*` -- real app, fake ffmpeg exec only.

Covers: auth-required (401), admin-vs-member gating (403), cross-community
IDOR (403, never 404 -- never confirms another tenant's community exists),
full config/target CRUD, and the real start/stop/status lifecycle
including the transcode BLOCK-WITH-FALLBACK path (hub-api's debit HTTP
call is mocked at the `httpx.AsyncClient.post` layer -- everything else
in the request path is real).
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from tests.conftest import (
    OTHER_TENANT_SLUG,
    TENANT_SLUG,
    auth_header,
    make_user_token,
    seed_community,
    seed_membership,
    seed_tenant,
)


def _base(community_id: int) -> str:
    return f"/api/v1/streaming/communities/{community_id}"


@pytest.mark.asyncio
async def test_get_config_requires_auth(app_and_client: Any) -> None:
    _, client = app_and_client
    response = await client.get(_base(1) + "/config")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_config_rejects_non_member(app_and_client: Any, dal_pair: Any) -> None:
    app, client = app_and_client
    _, dal = dal_pair
    tenant_id = seed_tenant(dal, slug=TENANT_SLUG)
    community_id = seed_community(dal, tenant_id=tenant_id)
    token = make_user_token(user_id=1)  # never seeded as a member

    response = await client.get(_base(community_id) + "/config", headers=auth_header(token))
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_set_config_requires_admin_not_just_member(
    app_and_client: Any, dal_pair: Any
) -> None:
    app, client = app_and_client
    _, dal = dal_pair
    tenant_id = seed_tenant(dal, slug=TENANT_SLUG)
    community_id = seed_community(dal, tenant_id=tenant_id)
    seed_membership(dal, community_id=community_id, user_id=2, role="member")
    token = make_user_token(user_id=2)

    response = await client.put(
        _base(community_id) + "/config",
        headers=auth_header(token),
        json={"source_url": "rtmp://ingest/live/k", "source_type": "rtmp"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_set_config_then_get_round_trips_for_admin(
    app_and_client: Any, dal_pair: Any
) -> None:
    app, client = app_and_client
    _, dal = dal_pair
    tenant_id = seed_tenant(dal, slug=TENANT_SLUG)
    community_id = seed_community(dal, tenant_id=tenant_id)
    seed_membership(dal, community_id=community_id, user_id=1, role="community-owner")
    token = make_user_token(user_id=1)

    put_response = await client.put(
        _base(community_id) + "/config",
        headers=auth_header(token),
        json={"source_url": "rtmp://ingest/live/k", "source_type": "rtmp", "record_enabled": False},
    )
    assert put_response.status_code == 200
    put_body = await put_response.get_json()
    assert put_body["config"]["source_url"] == "rtmp://ingest/live/k"

    get_response = await client.get(_base(community_id) + "/config", headers=auth_header(token))
    assert get_response.status_code == 200
    get_body = await get_response.get_json()
    assert get_body["config"]["source_url"] == "rtmp://ingest/live/k"


@pytest.mark.asyncio
async def test_cross_community_idor_returns_403_not_404(app_and_client: Any, dal_pair: Any) -> None:
    """A tenant-A admin token can never read/write tenant-B's community, even by guessing an id."""
    app, client = app_and_client
    _, dal = dal_pair
    seed_tenant(dal, slug=TENANT_SLUG)
    tenant_b = seed_tenant(dal, slug=OTHER_TENANT_SLUG)
    community_in_b = seed_community(dal, tenant_id=tenant_b)
    seed_membership(dal, community_id=community_in_b, user_id=1, role="community-owner")
    token_for_tenant_a = make_user_token(user_id=1, tenant=TENANT_SLUG)

    response = await client.get(
        _base(community_in_b) + "/config", headers=auth_header(token_for_tenant_a)
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_add_target_rejects_ssrf_target(app_and_client: Any, dal_pair: Any) -> None:
    app, client = app_and_client
    _, dal = dal_pair
    tenant_id = seed_tenant(dal, slug=TENANT_SLUG)
    community_id = seed_community(dal, tenant_id=tenant_id)
    seed_membership(dal, community_id=community_id, user_id=1, role="community-owner")
    token = make_user_token(user_id=1)
    await client.put(
        _base(community_id) + "/config",
        headers=auth_header(token),
        json={"source_url": "rtmp://ingest/live/k", "source_type": "rtmp"},
    )

    response = await client.post(
        _base(community_id) + "/targets",
        headers=auth_header(token),
        json={"platform": "custom", "forward_url": "rtmp://127.0.0.1/live/k"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_add_target_then_list_then_remove(app_and_client: Any, dal_pair: Any) -> None:
    app, client = app_and_client
    _, dal = dal_pair
    tenant_id = seed_tenant(dal, slug=TENANT_SLUG)
    community_id = seed_community(dal, tenant_id=tenant_id)
    seed_membership(dal, community_id=community_id, user_id=1, role="community-owner")
    token = make_user_token(user_id=1)
    await client.put(
        _base(community_id) + "/config",
        headers=auth_header(token),
        json={"source_url": "rtmp://ingest/live/k", "source_type": "rtmp"},
    )

    add_response = await client.post(
        _base(community_id) + "/targets",
        headers=auth_header(token),
        json={"platform": "twitch", "forward_url": "rtmp://8.8.8.8/live/tkey"},
    )
    assert add_response.status_code == 201
    target_id = (await add_response.get_json())["target"]["id"]

    list_response = await client.get(_base(community_id) + "/targets", headers=auth_header(token))
    assert len((await list_response.get_json())["targets"]) == 1

    delete_response = await client.delete(
        _base(community_id) + f"/targets/{target_id}", headers=auth_header(token)
    )
    assert delete_response.status_code == 200

    list_after = await client.get(_base(community_id) + "/targets", headers=auth_header(token))
    assert (await list_after.get_json())["targets"] == []


@pytest.mark.asyncio
async def test_start_stop_status_lifecycle_passthrough(
    app_and_client: Any, dal_pair: Any, fake_subprocess: Any
) -> None:
    app, client = app_and_client
    _, dal = dal_pair
    tenant_id = seed_tenant(dal, slug=TENANT_SLUG)
    community_id = seed_community(dal, tenant_id=tenant_id)
    seed_membership(dal, community_id=community_id, user_id=1, role="community-owner")
    token = make_user_token(user_id=1)
    await client.put(
        _base(community_id) + "/config",
        headers=auth_header(token),
        json={"source_url": "rtmp://ingest/live/k", "source_type": "rtmp"},
    )
    await client.post(
        _base(community_id) + "/targets",
        headers=auth_header(token),
        json={"platform": "twitch", "forward_url": "rtmp://8.8.8.8/live/tkey"},
    )

    start_response = await client.post(_base(community_id) + "/start", headers=auth_header(token))
    assert start_response.status_code == 200
    start_body = await start_response.get_json()
    assert start_body["status"]["running"] is True
    assert len(fake_subprocess.calls) == 1

    status_response = await client.get(_base(community_id) + "/status", headers=auth_header(token))
    assert (await status_response.get_json())["status"]["running"] is True

    stop_response = await client.post(_base(community_id) + "/stop", headers=auth_header(token))
    assert (await stop_response.get_json())["status"]["running"] is False

    status_after = await client.get(_base(community_id) + "/status", headers=auth_header(token))
    assert (await status_after.get_json())["status"]["running"] is False


@pytest.mark.asyncio
async def test_start_with_transcode_debits_real_token_ledger_http_call(
    app_and_client: Any, dal_pair: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    app, client = app_and_client
    _, dal = dal_pair
    tenant_id = seed_tenant(dal, slug=TENANT_SLUG)
    community_id = seed_community(dal, tenant_id=tenant_id)
    seed_membership(dal, community_id=community_id, user_id=1, role="community-owner")
    token = make_user_token(user_id=1)
    await client.put(
        _base(community_id) + "/config",
        headers=auth_header(token),
        json={
            "source_url": "rtmp://ingest/live/k",
            "source_type": "rtmp",
            "transcode_enabled": True,
        },
    )
    await client.post(
        _base(community_id) + "/targets",
        headers=auth_header(token),
        json={"platform": "twitch", "forward_url": "rtmp://8.8.8.8/live/tkey"},
    )

    captured: dict[str, Any] = {}

    async def fake_post(self: httpx.AsyncClient, url: str, **kwargs: Any) -> Any:
        captured["url"] = url
        captured["auth_header"] = kwargs["headers"]["Authorization"]

        class _Resp:
            status_code = 200

            def json(self) -> dict[str, Any]:
                return {"success": True, "balance_after": 55, "transaction_id": 1}

        return _Resp()

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    start_response = await client.post(_base(community_id) + "/start", headers=auth_header(token))
    body = await start_response.get_json()
    assert body["status"]["transcode_applied"] is True
    # The caller's own bearer token is passed through -- see
    # `services/token_ledger_client.py`'s module docstring on the auth model.
    assert captured["auth_header"] == f"Bearer {token}"
    assert captured["url"] == (
        f"http://hub-api-test.invalid:8204/api/v1/marketplace/communities/{community_id}/tokens/debit"
    )


@pytest.mark.asyncio
async def test_start_with_transcode_falls_back_when_ledger_unreachable(
    app_and_client: Any, dal_pair: Any, monkeypatch: pytest.MonkeyPatch, fake_subprocess: Any
) -> None:
    app, client = app_and_client
    _, dal = dal_pair
    tenant_id = seed_tenant(dal, slug=TENANT_SLUG)
    community_id = seed_community(dal, tenant_id=tenant_id)
    seed_membership(dal, community_id=community_id, user_id=1, role="community-owner")
    token = make_user_token(user_id=1)
    await client.put(
        _base(community_id) + "/config",
        headers=auth_header(token),
        json={
            "source_url": "rtmp://ingest/live/k",
            "source_type": "rtmp",
            "transcode_enabled": True,
        },
    )
    await client.post(
        _base(community_id) + "/targets",
        headers=auth_header(token),
        json={"platform": "twitch", "forward_url": "rtmp://8.8.8.8/live/tkey"},
    )

    async def fake_post(self: httpx.AsyncClient, url: str, **kwargs: Any) -> Any:
        raise httpx.ConnectError("hub-api unreachable")

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    start_response = await client.post(_base(community_id) + "/start", headers=auth_header(token))
    assert start_response.status_code == 200
    body = await start_response.get_json()
    # The job still starts -- BLOCK-WITH-FALLBACK, never a hard failure.
    assert body["status"]["running"] is True
    assert body["status"]["transcode_applied"] is False
    assert body["status"]["fallback_reason"] == "ledger_unavailable"
    assert "libx264" not in fake_subprocess.calls[0]


@pytest.mark.asyncio
async def test_start_returns_409_when_already_running(
    app_and_client: Any, dal_pair: Any, fake_subprocess: Any
) -> None:
    app, client = app_and_client
    _, dal = dal_pair
    tenant_id = seed_tenant(dal, slug=TENANT_SLUG)
    community_id = seed_community(dal, tenant_id=tenant_id)
    seed_membership(dal, community_id=community_id, user_id=1, role="community-owner")
    token = make_user_token(user_id=1)
    await client.put(
        _base(community_id) + "/config",
        headers=auth_header(token),
        json={"source_url": "rtmp://ingest/live/k", "source_type": "rtmp"},
    )
    await client.post(
        _base(community_id) + "/targets",
        headers=auth_header(token),
        json={"platform": "twitch", "forward_url": "rtmp://8.8.8.8/live/tkey"},
    )
    await client.post(_base(community_id) + "/start", headers=auth_header(token))

    second = await client.post(_base(community_id) + "/start", headers=auth_header(token))
    assert second.status_code == 409
