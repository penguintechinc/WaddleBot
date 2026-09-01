"""Provider-agnostic resolve()/search() contract for real YouTube/Spotify music resolvers.

This is the seam the music-station queue (`services/music_service.py` and
friends) calls through -- callers never import `youtube`/`spotify` directly.
`resolve()` auto-detects the provider from a URL (youtube.com/youtu.be ->
youtube, open.spotify.com -> spotify) and falls back to the explicit
`provider` argument for bare search text (e.g. a chat `!songrequest` query
with no URL). Every resolver call is real network I/O against the live
YouTube Data API v3 / Spotify Web API -- there is no stub/fake path; the
only non-network outcome is `ProviderUnavailable` when that provider's
credentials are absent or unusable, which callers are expected to catch and
degrade on (e.g. "Spotify isn't configured for this community" instead of a
500).
"""

from __future__ import annotations

from urllib.parse import urlparse

from services.music_providers import spotify, youtube
from services.music_providers.errors import ProviderUnavailable, TrackNotFound
from services.music_providers.track import Track

__all__ = ["ProviderUnavailable", "Track", "TrackNotFound", "resolve", "search"]

_KNOWN_PROVIDERS = frozenset({"youtube", "spotify"})


def _detect_provider(url_or_query: str) -> str | None:
    """Sniff a provider from a URL's host; returns None for bare search text."""
    parsed = urlparse(url_or_query)
    host = (parsed.netloc or "").lower()
    if not host and "://" not in url_or_query:
        # No scheme (e.g. "youtu.be/xyz" pasted without "https://") --
        # urlparse can't find a netloc without one; re-parse as
        # scheme-relative so the same host logic below still applies.
        parsed = urlparse(f"//{url_or_query}")
        host = (parsed.netloc or "").lower()

    if host == "youtu.be" or host == "youtube.com" or host.endswith(".youtube.com"):
        return "youtube"
    if host == "spotify.com" or host.endswith(".spotify.com"):
        return "spotify"
    return None


async def resolve(url_or_query: str, provider: str | None = None) -> Track:
    """Resolve one URL or bare query to a single `Track`.

    Provider is auto-detected from the URL host when possible; otherwise
    the caller-supplied `provider` is used (required for bare search text).
    Raises `ProviderUnavailable` if the resolved provider has no usable
    credentials, `TrackNotFound` if the provider found nothing.
    """
    resolved_provider = _detect_provider(url_or_query) or provider
    if resolved_provider is None or resolved_provider not in _KNOWN_PROVIDERS:
        raise TrackNotFound(url_or_query)

    if resolved_provider == "youtube":
        return await youtube.resolve(url_or_query)
    return await spotify.resolve(url_or_query)


async def search(query: str, provider: str) -> list[Track]:
    """Search a specific provider for `query`, returning every match found.

    Raises `ProviderUnavailable` if `provider` has no usable credentials,
    `TrackNotFound` if the search returns zero results.
    """
    if provider not in _KNOWN_PROVIDERS:
        raise TrackNotFound(query)

    if provider == "youtube":
        return await youtube.search(query)
    return await spotify.search(query)
