"""
svc-streaming scaffold boot tests.

Proves the skeleton actually boots and serves: flask_core's /health
blueprint responds 200, and every control-plane route is reachable and
returns a documented 501 (not a 500/unhandled exception). Does NOT
exercise real MarchProxy/LiveKit fronting, token consumption, or
live-status aggregation -- those are unimplemented TODOs in app.py by
design (scaffold only).
"""
from __future__ import annotations

import pytest
from app import app


@pytest.mark.asyncio
async def test_health_endpoint_returns_200() -> None:
    """flask_core's health blueprint wiring boots and reports healthy."""
    client = app.test_client()
    response = await client.get("/health")
    assert response.status_code == 200
    data = await response.get_json()
    assert data["status"] == "healthy"
    assert data["module"] == "svc-streaming"


@pytest.mark.asyncio
async def test_list_streams_returns_501() -> None:
    """GET /streams is a documented stub, not a crash."""
    client = app.test_client()
    response = await client.get("/streams")
    assert response.status_code == 501
    data = await response.get_json()
    assert data["status"] == "not_implemented"


@pytest.mark.asyncio
async def test_create_stream_returns_501() -> None:
    """POST /streams (INGEST) is a documented stub, not a crash."""
    client = app.test_client()
    response = await client.post("/streams", json={})
    assert response.status_code == 501
    data = await response.get_json()
    assert data["status"] == "not_implemented"


@pytest.mark.asyncio
async def test_add_forward_target_returns_501() -> None:
    """POST /streams/{id}/forward (FORWARD) is a documented stub, not a crash."""
    client = app.test_client()
    response = await client.post("/streams/teststream/forward", json={})
    assert response.status_code == 501
    data = await response.get_json()
    assert data["status"] == "not_implemented"


@pytest.mark.asyncio
async def test_add_forward_target_rejects_invalid_stream_id() -> None:
    """
    Malformed stream_id is rejected before reaching the stub -- guards the
    route against being a foothold even before real validation/auth exists
    (security.md Input Validation: server-side validation on client input).
    """
    client = app.test_client()
    response = await client.post("/streams/../../etc/forward", json={})
    assert response.status_code in (400, 404)


@pytest.mark.asyncio
async def test_live_status_returns_501() -> None:
    """GET /streams/live (DISPLAY aggregation projection) is a documented stub."""
    client = app.test_client()
    response = await client.get("/streams/live")
    assert response.status_code == 501
    data = await response.get_json()
    assert data["status"] == "not_implemented"
