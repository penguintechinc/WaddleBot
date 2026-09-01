"""svc-action app.py boot test -- health blueprint wiring, runner not started."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_health_endpoint_returns_200() -> None:
    """flask_core's health blueprint wiring boots and reports healthy.

    Deliberately does not start the app's `before_serving`/`after_serving`
    hooks (which open real Valkey/DB connections) -- `test_client()`'s
    plain request dispatch never triggers them, matching
    core/svc_streaming's own scaffold boot-test pattern.
    """
    from app import app

    client = app.test_client()
    response = await client.get("/health")
    assert response.status_code == 200
    data = await response.get_json()
    assert data["status"] == "healthy"
    assert data["module"] == "svc-action"
