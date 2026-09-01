"""Normalized track representation shared by every Music Station provider integration.

`Track` is the single wire-and-storage shape every provider resolver
(`services/music_providers/__init__.py::resolve()` and its YouTube/
Spotify/SoundCloud implementations) returns -- the Music Station queue,
`music_tracks` cache table, and moderation log all key off these exact
fields, never a provider-specific shape. Kept byte-identical across the
Music Station port group's parallel worktrees so the queue/moderation
side and the provider-integration side merge without a field-shape
conflict.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Track:
    """One resolved, playable track -- provider-agnostic."""

    provider: str  # "youtube"|"spotify"|"soundcloud"
    external_id: str
    title: str
    artist: str
    duration_ms: int
    artwork_url: str | None
    url: str
