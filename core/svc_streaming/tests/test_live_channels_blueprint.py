"""HTTP-level tests for the associated live-channels endpoint."""

from __future__ import annotations

from typing import Any

import pytest

from services.live_channels_service import TwitchLiveClient, YouTubeLiveClient
from tests.conftest import (
    TENANT_SLUG,
    auth_header,
    make_user_token,
    seed_community,
    seed_connected_channel,
    seed_membership,
    seed_tenant,
)


@pytest.mark.asyncio
async def test_live_channels_requires_auth(app_and_client: Any) -> None:
    _, client = app_and_client
    response = await client.get("/api/v1/streaming/communities/1/live-channels")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_live_channels_member_can_read(app_and_client: Any, dal_pair: Any) -> None:
    app, client = app_and_client
    _, dal = dal_pair
    tenant_id = seed_tenant(dal, slug=TENANT_SLUG)
    community_id = seed_community(dal, tenant_id=tenant_id)
    seed_membership(dal, community_id=community_id, user_id=1, role="member")
    seed_connected_channel(
        dal,
        community_id=community_id,
        platform="twitch",
        platform_server_id="123",
        platform_server_name="CoolStreamer",
    )
    # Inject pre-built (unconfigured -- deterministic, no real HTTP) clients.
    app.config["TWITCH_LIVE_CLIENT"] = TwitchLiveClient(client_id="", client_secret="")
    app.config["YOUTUBE_LIVE_CLIENT"] = YouTubeLiveClient(api_key="")
    token = make_user_token(user_id=1)

    response = await client.get(
        f"/api/v1/streaming/communities/{community_id}/live-channels", headers=auth_header(token)
    )
    assert response.status_code == 200
    body = await response.get_json()
    assert body["channels"][0]["platform"] == "twitch"
    assert body["channels"][0]["live"] is None  # unconfigured client -- genuinely unknown


@pytest.mark.asyncio
async def test_live_channels_rejects_non_member(app_and_client: Any, dal_pair: Any) -> None:
    app, client = app_and_client
    _, dal = dal_pair
    tenant_id = seed_tenant(dal, slug=TENANT_SLUG)
    community_id = seed_community(dal, tenant_id=tenant_id)
    token = make_user_token(user_id=1)  # not seeded as a member

    response = await client.get(
        f"/api/v1/streaming/communities/{community_id}/live-channels", headers=auth_header(token)
    )
    assert response.status_code == 403
