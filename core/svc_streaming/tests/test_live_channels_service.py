"""Associated live-channels: real DB read (`community_servers`) + mocked platform API responses."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from services.live_channels_service import (
    TwitchLiveClient,
    YouTubeLiveClient,
    list_associated_channels,
)
from tests.conftest import TENANT_SLUG, seed_community, seed_connected_channel, seed_tenant


class _FakeResponse:
    def __init__(self, status_code: int, json_body: dict[str, Any]) -> None:
        self.status_code = status_code
        self._json_body = json_body

    def json(self) -> dict[str, Any]:
        return self._json_body


# ---------------------------------------------------------------------------
# TwitchLiveClient
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_twitch_unconfigured_client_returns_empty_without_any_http_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    async def fake_post(self: httpx.AsyncClient, url: str, **kwargs: Any) -> _FakeResponse:
        calls.append(url)
        return _FakeResponse(200, {})

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    client = TwitchLiveClient(client_id="", client_secret="")
    assert client.configured is False
    result = await client.get_live_status(["somechannel"])
    assert result == {}
    assert calls == []


@pytest.mark.asyncio
async def test_twitch_configured_client_fetches_token_then_streams(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_post(self: httpx.AsyncClient, url: str, **kwargs: Any) -> _FakeResponse:
        assert url == "https://id.twitch.tv/oauth2/token"
        return _FakeResponse(200, {"access_token": "app-token", "expires_in": 3600})

    captured_get: dict[str, Any] = {}

    async def fake_get(self: httpx.AsyncClient, url: str, **kwargs: Any) -> _FakeResponse:
        captured_get["url"] = url
        captured_get["params"] = kwargs["params"]
        captured_get["headers"] = kwargs["headers"]
        return _FakeResponse(
            200,
            {"data": [{"user_login": "SomeChannel", "title": "Live now!"}]},
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    client = TwitchLiveClient(client_id="cid", client_secret="csecret")
    result = await client.get_live_status(["somechannel"])

    assert result == {"somechannel": {"live": True, "title": "Live now!"}}
    assert captured_get["url"] == "https://api.twitch.tv/helix/streams"
    assert captured_get["headers"]["Authorization"] == "Bearer app-token"


@pytest.mark.asyncio
async def test_twitch_token_fetch_failure_returns_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_post(self: httpx.AsyncClient, url: str, **kwargs: Any) -> _FakeResponse:
        return _FakeResponse(401, {})

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    client = TwitchLiveClient(client_id="cid", client_secret="bad-secret")
    result = await client.get_live_status(["somechannel"])
    assert result == {}


@pytest.mark.asyncio
async def test_twitch_empty_channel_list_short_circuits(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    async def fake_post(self: httpx.AsyncClient, url: str, **kwargs: Any) -> _FakeResponse:
        calls.append(url)
        return _FakeResponse(200, {"access_token": "t", "expires_in": 3600})

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    client = TwitchLiveClient(client_id="cid", client_secret="csecret")
    result = await client.get_live_status([])
    assert result == {}
    assert calls == []


# ---------------------------------------------------------------------------
# YouTubeLiveClient
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_youtube_unconfigured_client_returns_empty() -> None:
    client = YouTubeLiveClient(api_key="")
    assert client.configured is False
    result = await client.get_live_status(["UCabc123"])
    assert result == {}


@pytest.mark.asyncio
async def test_youtube_configured_client_returns_live_channel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_get(self: httpx.AsyncClient, url: str, **kwargs: Any) -> _FakeResponse:
        assert url == "https://www.googleapis.com/youtube/v3/search"
        assert kwargs["params"]["channelId"] == "UCabc123"
        assert kwargs["params"]["eventType"] == "live"
        return _FakeResponse(200, {"items": [{"snippet": {"title": "YT Live Title"}}]})

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    client = YouTubeLiveClient(api_key="ytkey")
    result = await client.get_live_status(["UCabc123"])
    assert result == {"UCabc123": {"live": True, "title": "YT Live Title"}}


@pytest.mark.asyncio
async def test_youtube_no_live_items_omits_channel(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_get(self: httpx.AsyncClient, url: str, **kwargs: Any) -> _FakeResponse:
        return _FakeResponse(200, {"items": []})

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    client = YouTubeLiveClient(api_key="ytkey")
    result = await client.get_live_status(["UCabc123"])
    assert result == {}


# ---------------------------------------------------------------------------
# list_associated_channels -- real DB + injected (mocked) platform clients
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_associated_channels_merges_db_and_live_status(
    app_and_client: Any, dal_pair: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    async_dal, dal = dal_pair
    tenant_id = seed_tenant(dal, slug=TENANT_SLUG)
    community_id = seed_community(dal, tenant_id=tenant_id)
    seed_connected_channel(
        dal,
        community_id=community_id,
        platform="twitch",
        platform_server_id="123",
        platform_server_name="CoolStreamer",
    )
    seed_connected_channel(
        dal,
        community_id=community_id,
        platform="youtube",
        platform_server_id="UCabc123",
        platform_server_name="Cool YT Channel",
    )

    async def fake_twitch_status(user_logins: list[str]) -> dict[str, Any]:
        assert user_logins == ["coolstreamer"]
        return {"coolstreamer": {"live": True, "title": "Live!"}}

    async def fake_youtube_status(channel_ids: list[str]) -> dict[str, Any]:
        assert channel_ids == ["UCabc123"]
        return {}  # configured, but not currently live

    twitch_client = TwitchLiveClient(client_id="cid", client_secret="csecret")
    youtube_client = YouTubeLiveClient(api_key="ytkey")
    monkeypatch.setattr(twitch_client, "get_live_status", fake_twitch_status)
    monkeypatch.setattr(youtube_client, "get_live_status", fake_youtube_status)

    channels = await list_associated_channels(
        async_dal,
        dal,
        community_id=community_id,
        twitch_client=twitch_client,
        youtube_client=youtube_client,
    )

    by_platform = {c.platform: c for c in channels}
    assert by_platform["twitch"].live is True
    assert by_platform["twitch"].title == "Live!"
    assert by_platform["youtube"].live is False  # configured client, genuinely not live
    assert by_platform["youtube"].title is None


@pytest.mark.asyncio
async def test_list_associated_channels_unconfigured_clients_report_unknown(
    app_and_client: Any, dal_pair: Any
) -> None:
    async_dal, dal = dal_pair
    tenant_id = seed_tenant(dal, slug=TENANT_SLUG)
    community_id = seed_community(dal, tenant_id=tenant_id)
    seed_connected_channel(
        dal,
        community_id=community_id,
        platform="twitch",
        platform_server_id="123",
        platform_server_name="CoolStreamer",
    )

    channels = await list_associated_channels(
        async_dal,
        dal,
        community_id=community_id,
        twitch_client=TwitchLiveClient(client_id="", client_secret=""),
        youtube_client=YouTubeLiveClient(api_key=""),
    )
    assert channels[0].live is None  # unconfigured -- genuinely unknown, never guessed False


@pytest.mark.asyncio
async def test_list_associated_channels_ignores_unapproved_status(
    app_and_client: Any, dal_pair: Any
) -> None:
    async_dal, dal = dal_pair
    tenant_id = seed_tenant(dal, slug=TENANT_SLUG)
    community_id = seed_community(dal, tenant_id=tenant_id)
    seed_connected_channel(
        dal,
        community_id=community_id,
        platform="twitch",
        platform_server_id="123",
        platform_server_name="Pending",
        status="pending",
    )

    channels = await list_associated_channels(
        async_dal,
        dal,
        community_id=community_id,
        twitch_client=TwitchLiveClient(client_id="", client_secret=""),
        youtube_client=YouTubeLiveClient(api_key=""),
    )
    assert channels == []
