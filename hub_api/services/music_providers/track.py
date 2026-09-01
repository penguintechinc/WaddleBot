"""Normalized cross-provider Track -- the shared shape every music provider resolves into.

Kept byte-identical to the sibling music-station agent's own `Track` (same
module built independently against the same spec) so the two land in the
same queue without a translation layer between them.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Track:
    """A single playable unit, normalized across music providers.

    `provider` is the resolver's own name (`"youtube"`/`"spotify"`),
    `external_id` is that provider's native id (YouTube video id, Spotify
    track id), and `url` is the canonical link back to the track on that
    provider.
    """

    provider: str
    external_id: str
    title: str
    artist: str
    duration_ms: int
    artwork_url: str | None
    url: str
