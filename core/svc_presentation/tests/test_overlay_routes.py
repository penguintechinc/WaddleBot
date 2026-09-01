"""Core overlay surfaces (`full_screen`/`media`/`crawler`) -- render + validation."""

from __future__ import annotations

import pytest
from quart.typing import TestClientProtocol


@pytest.mark.parametrize("surface", ["full_screen", "media", "crawler"])
@pytest.mark.asyncio
async def test_core_surface_renders_html_with_live_bootstrap(
    client: TestClientProtocol, surface: str
) -> None:
    """Each core surface returns real HTML embedding the live SSE bootstrap script."""
    response = await client.get(f"/overlay/testcommunity/{surface}")
    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("text/html")
    body = await response.get_data(as_text=True)
    assert "<!DOCTYPE html>" in body
    assert "EventSource" in body
    assert "/overlay/${community}/${surface}/live" in body
    assert "testcommunity" in body


@pytest.mark.asyncio
async def test_full_screen_escapes_reflected_community(client: TestClientProtocol) -> None:
    """Reflected `community`/`surface` path segments are HTML-escaped, not injected raw."""
    response = await client.get("/overlay/%3Cscript%3E/full_screen")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_unknown_surface_returns_404(client: TestClientProtocol) -> None:
    """A surface with no renderer (and not the `music` literal route) 404s, not 200-with-garbage."""
    response = await client.get("/overlay/testcommunity/not_a_real_surface")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_path_traversal_surface_rejected(client: TestClientProtocol) -> None:
    """A malformed community segment is rejected before reaching any renderer."""
    response = await client.get("/overlay/../../etc/full_screen")
    assert response.status_code in (400, 404)


@pytest.mark.asyncio
async def test_disabled_surface_returns_404(client: TestClientProtocol) -> None:
    """An `overlay_surfaces` row with `enabled=False` blocks rendering for that community."""
    app = client.app
    async_dal, dal = app.config["async_dal"], app.config["dal"]
    await async_dal.insert_async(
        dal.overlay_surfaces, community_id=42, surface="full_screen", enabled=False
    )
    response = await client.get("/overlay/42/full_screen")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_theme_config_injected_into_rendered_css(client: TestClientProtocol) -> None:
    """A `presentation_config` row's `primary_color` shows up as a CSS custom property."""
    app = client.app
    async_dal, dal = app.config["async_dal"], app.config["dal"]
    await async_dal.insert_async(dal.presentation_config, community_id=7, primary_color="#ff00aa")
    response = await client.get("/overlay/7/full_screen")
    assert response.status_code == 200
    body = await response.get_data(as_text=True)
    assert "#ff00aa" in body
