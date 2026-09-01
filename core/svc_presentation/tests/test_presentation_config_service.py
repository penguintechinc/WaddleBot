"""`presentation_config_service` -- surface-enabled + theme-config lookups."""

from __future__ import annotations

import pytest
from quart.typing import TestClientProtocol

from services.presentation_config_service import get_theme_config, is_surface_enabled


@pytest.mark.asyncio
async def test_is_surface_enabled_defaults_true_with_no_row(client: TestClientProtocol) -> None:
    """No `overlay_surfaces` row at all -- enabled by default, not "not found"."""
    async_dal, dal = client.app.config["async_dal"], client.app.config["dal"]
    enabled = await is_surface_enabled(async_dal, dal, community="123", surface="crawler")
    assert enabled is True


@pytest.mark.asyncio
async def test_is_surface_enabled_non_numeric_community_defaults_true(
    client: TestClientProtocol,
) -> None:
    """A non-numeric `community` slug has no FK to look up -- defaults True, not an error."""
    async_dal, dal = client.app.config["async_dal"], client.app.config["dal"]
    enabled = await is_surface_enabled(async_dal, dal, community="not-a-number", surface="media")
    assert enabled is True


@pytest.mark.asyncio
async def test_is_surface_enabled_respects_disabled_row(client: TestClientProtocol) -> None:
    """An explicit `enabled=False` row wins over the default."""
    async_dal, dal = client.app.config["async_dal"], client.app.config["dal"]
    await async_dal.insert_async(
        dal.overlay_surfaces, community_id=55, surface="media", enabled=False
    )
    enabled = await is_surface_enabled(async_dal, dal, community="55", surface="media")
    assert enabled is False


@pytest.mark.asyncio
async def test_get_theme_config_defaults_to_none_with_no_row(client: TestClientProtocol) -> None:
    """No `presentation_config` row -- every theme field is `None`, renderer applies defaults."""
    async_dal, dal = client.app.config["async_dal"], client.app.config["dal"]
    theme = await get_theme_config(async_dal, dal, community="123")
    assert theme.primary_color is None
    assert theme.secondary_color is None
    assert theme.font_family is None


@pytest.mark.asyncio
async def test_get_theme_config_reads_seeded_row(client: TestClientProtocol) -> None:
    """A seeded row's colors/font come back verbatim."""
    async_dal, dal = client.app.config["async_dal"], client.app.config["dal"]
    await async_dal.insert_async(
        dal.presentation_config,
        community_id=61,
        primary_color="#112233",
        secondary_color="#445566",
        font_family="Comic Sans MS",
    )
    theme = await get_theme_config(async_dal, dal, community="61")
    assert theme.primary_color == "#112233"
    assert theme.secondary_color == "#445566"
    assert theme.font_family == "Comic Sans MS"
