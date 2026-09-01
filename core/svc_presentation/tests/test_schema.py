"""`bind_presentation_tables` -- table shape + idempotency guard."""

from __future__ import annotations

from pydal import DAL

from services.schema import bind_presentation_tables


def test_bind_presentation_tables_creates_expected_tables() -> None:
    """Both tables exist with the fields the rest of this service reads/writes."""
    dal = DAL("sqlite:memory")
    bind_presentation_tables(dal, migrate=True)

    assert "overlay_surfaces" in dal.tables
    assert "presentation_config" in dal.tables
    assert set(dal.overlay_surfaces.fields) >= {
        "community_id",
        "surface",
        "enabled",
        "config",
        "created_at",
        "updated_at",
    }
    assert set(dal.presentation_config.fields) >= {
        "community_id",
        "theme",
        "primary_color",
        "secondary_color",
        "font_family",
        "music_enabled",
        "crawler_speed_seconds",
    }
    dal.close()


def test_bind_presentation_tables_is_idempotent() -> None:
    """A second call against the same DAL instance is a safe no-op, not a re-definition error."""
    dal = DAL("sqlite:memory")
    bind_presentation_tables(dal, migrate=True)
    bind_presentation_tables(dal, migrate=True)  # must not raise
    assert "presentation_config" in dal.tables
    dal.close()
