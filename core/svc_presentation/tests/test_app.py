"""
svc-presentation scaffold boot tests.

Proves the skeleton actually boots and serves: flask_core's /health
blueprint responds 200, and the stub per-community overlay route returns
HTML. Does NOT exercise real rendering, hub-api polling, or read-replica
routing -- those are unimplemented TODOs in app.py by design (scaffold
only).
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
    assert data["module"] == "svc-presentation"


@pytest.mark.asyncio
async def test_overlay_stub_route_returns_html() -> None:
    """Stub per-community overlay route serves a placeholder HTML page."""
    client = app.test_client()
    response = await client.get("/overlay/testcommunity/full_screen")
    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("text/html")
    body = await response.get_data(as_text=True)
    assert "testcommunity" in body
    assert "full_screen" in body


@pytest.mark.asyncio
async def test_overlay_stub_route_escapes_path_params() -> None:
    """
    Reflected path params are escaped in the placeholder HTML -- guards the
    stub against being a reflected-XSS foothold even before real auth/
    rendering exists (security.md Input Validation: escape outputs).
    """
    client = app.test_client()
    response = await client.get("/overlay/%3Cscript%3E/full_screen")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_overlay_stub_route_rejects_invalid_surface() -> None:
    """Malformed surface segment is rejected before reaching the renderer."""
    client = app.test_client()
    response = await client.get("/overlay/testcommunity/../../etc")
    assert response.status_code in (400, 404)
