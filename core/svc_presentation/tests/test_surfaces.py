"""`services.surfaces` -- known-surface set + community-slug validation."""

from __future__ import annotations

from services.surfaces import KNOWN_SURFACES, is_valid_community


def test_known_surfaces_contains_core_and_music() -> None:
    """The four surfaces this scaffold actually renders/pushes to."""
    assert KNOWN_SURFACES == {"full_screen", "media", "crawler", "music"}


def test_is_valid_community_accepts_slug() -> None:
    assert is_valid_community("acme-corp_123") is True


def test_is_valid_community_rejects_special_characters() -> None:
    assert is_valid_community("<script>") is False
    assert is_valid_community("../../etc") is False
    assert is_valid_community("") is False
