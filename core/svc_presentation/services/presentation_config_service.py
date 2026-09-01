"""Read-only lookups against svc-presentation's own `overlay_surfaces`/`presentation_config`.

Both tables (`services/schema.py::bind_presentation_tables`, migration
`073_svc_presentation_overlays.sql`) are read here to make two real
decisions at render time: whether a surface is enabled for a community
(`overlay_surfaces.enabled`), and which theme/palette to inject into the
rendered HTML (`presentation_config`). No write path exists in this PR --
provisioning rows is admin/hub-webui follow-up work, out of this task's
scope.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True, frozen=True)
class ThemeConfig:
    """The subset of `presentation_config` that `services/render.py` injects as CSS variables."""

    primary_color: str | None
    secondary_color: str | None
    font_family: str | None


def _community_id(community: str) -> int | None:
    """Best-effort parse of the URL path's `community` segment as an integer FK.

    `overlay_surfaces.community_id`/`presentation_config.community_id` are
    both `INTEGER REFERENCES communities(id)` (migration 073) -- the URL
    path segment itself stays a generic slug-validated string (matching
    this scaffold's pre-existing `community` param shape, and the same
    OBS-browser-source-URL convention `browser_source_core_module` already
    uses, `docs/browser_source_core_module/API.md:118` `community_id` in
    the path). A non-numeric community (e.g. test fixtures using a plain
    slug) simply has no config/surface row to look up -- callers get
    `None` and apply defaults, never an error.
    """
    try:
        return int(community)
    except ValueError:
        return None


async def is_surface_enabled(async_dal: Any, dal: Any, *, community: str, surface: str) -> bool:
    """True unless an explicit `overlay_surfaces` row disables this surface for this community.

    No row at all (the common case -- no admin has touched per-community
    surface config yet) means "enabled by default", not "not found".
    """
    community_id = _community_id(community)
    if community_id is None:
        return True
    rows = await async_dal.select_async(
        dal(
            (dal.overlay_surfaces.community_id == community_id)
            & (dal.overlay_surfaces.surface == surface)
        )
    )
    if not rows:
        return True
    return bool(rows.first().enabled)


async def get_theme_config(async_dal: Any, dal: Any, *, community: str) -> ThemeConfig:
    """Return this community's theme overrides, or all-`None` defaults if unset."""
    community_id = _community_id(community)
    if community_id is None:
        return ThemeConfig(primary_color=None, secondary_color=None, font_family=None)
    rows = await async_dal.select_async(
        dal(dal.presentation_config.community_id == community_id)
    )
    if not rows:
        return ThemeConfig(primary_color=None, secondary_color=None, font_family=None)
    row = rows.first()
    return ThemeConfig(
        primary_color=row.primary_color,
        secondary_color=row.secondary_color,
        font_family=row.font_family,
    )
