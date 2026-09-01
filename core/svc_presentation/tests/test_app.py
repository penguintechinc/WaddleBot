"""Boots-and-serves tests: flask_core's `/health` blueprint + app factory wiring."""

from __future__ import annotations

import pytest
from quart.typing import TestClientProtocol


@pytest.mark.asyncio
async def test_health_endpoint_returns_200(client: TestClientProtocol) -> None:
    """flask_core's health blueprint wiring boots and reports healthy."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = await response.get_json()
    assert data["status"] == "healthy"
    assert data["module"] == "svc-presentation"


@pytest.mark.asyncio
async def test_startup_wires_dal_hub_and_queue_reader(client: TestClientProtocol) -> None:
    """`before_serving` populated every app.config key routes depend on."""
    app = client.app
    assert app.config["async_dal"] is not None
    assert app.config["dal"] is not None
    assert app.config["PRESENTATION_HUB"] is not None
    assert app.config["MUSIC_QUEUE_READER"] is not None
    # No VALKEY_URL configured in tests -- both fall back to in-process mode.
    assert app.config["PRESENTATION_HUB"].fallback_mode is True
    assert app.config["MUSIC_QUEUE_READER"].connected is False
