"""`POST /overlay/<community>/<surface>/push` -- validation, auth gating, and real SSE fan-out."""

from __future__ import annotations

import asyncio
import json
from dataclasses import replace

import pytest
from quart.typing import TestClientProtocol

from app import create_app
from config import Config


@pytest.mark.asyncio
async def test_push_rejects_invalid_community(client: TestClientProtocol) -> None:
    """Same slug validation as every other overlay route."""
    response = await client.post("/overlay/%3Cscript%3E/full_screen/push", json={"title": "x"})
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_push_rejects_unknown_surface(client: TestClientProtocol) -> None:
    """A surface outside `KNOWN_SURFACES` 404s -- no silent accept-and-drop."""
    response = await client.post("/overlay/testcommunity/not_a_surface/push", json={"title": "x"})
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_push_rejects_non_object_body(client: TestClientProtocol) -> None:
    """A JSON array (or any non-object body) is rejected, not silently coerced."""
    response = await client.post(
        "/overlay/testcommunity/full_screen/push",
        data=json.dumps([1, 2, 3]),
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_push_succeeds_and_publishes(client: TestClientProtocol) -> None:
    """A valid push (no token configured) publishes through the hub and returns 200."""
    hub = client.app.config["PRESENTATION_HUB"]
    queue = hub.register("testcommunity", "crawler")

    response = await client.post(
        "/overlay/testcommunity/crawler/push", json={"text": "breaking news"}
    )
    assert response.status_code == 200
    body = await response.get_json()
    assert body["status"] == "published"

    delivered = await asyncio.wait_for(queue.get(), timeout=1)
    assert delivered == {"text": "breaking news"}


@pytest.mark.asyncio
async def test_push_requires_bearer_token_when_configured(test_config: Config) -> None:
    """A `PRESENTATION_PUSH_TOKEN` gate rejects unauthenticated pushes with 401."""
    token_config = replace(test_config, push_token="s3cr3t-token")
    app = create_app(token_config)
    async with app.test_app() as running:
        gated_client = running.test_client()

        no_auth = await gated_client.post(
            "/overlay/testcommunity/full_screen/push", json={"title": "x"}
        )
        assert no_auth.status_code == 401

        wrong_auth = await gated_client.post(
            "/overlay/testcommunity/full_screen/push",
            json={"title": "x"},
            headers={"Authorization": "Bearer wrong-token"},
        )
        assert wrong_auth.status_code == 401

        correct_auth = await gated_client.post(
            "/overlay/testcommunity/full_screen/push",
            json={"title": "x"},
            headers={"Authorization": "Bearer s3cr3t-token"},
        )
        assert correct_auth.status_code == 200


@pytest.mark.asyncio
async def test_live_rejects_invalid_community(client: TestClientProtocol) -> None:
    """The SSE route applies the same slug validation before ever registering a subscriber."""
    response = await client.get("/overlay/%3Cscript%3E/media/live")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_live_rejects_unknown_surface(client: TestClientProtocol) -> None:
    """An unknown surface 404s -- no SSE connection opened for it."""
    response = await client.get("/overlay/testcommunity/not_a_surface/live")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_push_fans_out_to_a_live_sse_connection(client: TestClientProtocol) -> None:
    """End-to-end: an SSE client receives the bootstrap event, then a real pushed payload."""
    connection = client.request(path="/overlay/testcommunity/media/live")
    async with connection as live:
        first_chunk = await asyncio.wait_for(live.receive(), timeout=3)
        bootstrap = _parse_sse_event(first_chunk)
        assert bootstrap["type"] == "connected"
        assert bootstrap["community"] == "testcommunity"
        assert bootstrap["surface"] == "media"

        push_response = await client.post(
            "/overlay/testcommunity/media/push",
            json={"title": "Now Live", "body": "Thanks for the follow!"},
        )
        assert push_response.status_code == 200

        second_chunk = await asyncio.wait_for(live.receive(), timeout=3)
        pushed = _parse_sse_event(second_chunk)
        assert pushed == {"title": "Now Live", "body": "Thanks for the follow!"}

        await live.disconnect()


def _parse_sse_event(raw_chunk: bytes) -> dict:
    r"""Decode one `data: {...}\n\n` SSE frame back into its dict payload."""
    text = raw_chunk.decode()
    assert text.startswith("data: ")
    return json.loads(text[len("data: ") :].strip())
