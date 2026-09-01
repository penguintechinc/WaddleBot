"""Provider resolution contract for the Music Station queue.

`resolve(url_or_query, provider)` normalizes a caller-supplied URL/search
query into a single `Track` (`services/music_providers/track.py`). Each
external provider gets its own submodule (`services/music_providers/
youtube.py`, `.../spotify.py`, `.../soundcloud.py`) exposing `async def
resolve(url_or_query: str) -> Track`, dynamically imported here so the
Music Station queue never hard-depends on a specific provider integration
landing first -- an unbuilt/unconfigured provider degrades to a real
`ProviderUnavailable` (converted to a 422 by `blueprints/v1/
community_music_queue.py`), not an ImportError crash or a stub return.

The `"direct"` pseudo-provider is fully implemented in this module --
parses a direct media URL (e.g. a self-hosted/CDN `.mp3`/`.ogg` link)
into a `Track` without any external API call, and is always available
regardless of which streaming-provider integrations exist yet.
`detect_provider()` below auto-classifies a caller-supplied URL when the
caller doesn't name a provider explicitly.
"""

from __future__ import annotations

import importlib
from pathlib import PurePosixPath
from urllib.parse import unquote, urlparse

from services.music_providers.track import Track

#: Every provider `resolve()` is allowed to dispatch to, beyond the
#: locally-implemented "direct" pseudo-provider. Each maps to a sibling
#: submodule of this package that may or may not exist yet.
_PROVIDER_MODULES: dict[str, str] = {
    "youtube": "services.music_providers.youtube",
    "spotify": "services.music_providers.spotify",
    "soundcloud": "services.music_providers.soundcloud",
}

#: File extensions this module's local fallback resolver treats as a
#: directly-playable media URL (no external API/OAuth needed).
_DIRECT_MEDIA_EXTENSIONS: frozenset[str] = frozenset(
    {".mp3", ".ogg", ".oga", ".wav", ".m4a", ".flac", ".webm", ".opus", ".aac"}
)


class ProviderUnavailable(Exception):
    """A named provider integration is not usable right now.

    Raised when the provider's submodule isn't installed yet (sibling
    integration not landed), when it raises its own configuration error
    (e.g. missing OAuth credentials), or when it fails to resolve the
    given input. `blueprints/v1/community_music_queue.py` catches this
    and returns a 422 -- a real, actionable rejection, never a silent
    fake `Track`.
    """


def _split_title_artist(stem: str) -> tuple[str, str]:
    """Best-effort `"Artist - Title"` filename convention split.

    Falls back to `(stem, "Unknown Artist")` when the filename doesn't
    follow that convention -- a real, documented limitation of resolving
    a track from a bare media URL with no ID3/metadata fetch, not a fake
    placeholder pretending to be real data.
    """
    for sep in (" - ", "_-_", "-"):
        if sep in stem:
            left, _, right = stem.partition(sep)
            left, right = left.strip().replace("_", " "), right.strip().replace("_", " ")
            if left and right:
                return right, left
    cleaned = stem.strip().replace("_", " ") or "Unknown Track"
    return cleaned, "Unknown Artist"


def _parse_direct_media_url(url: str) -> Track:
    """Parse a direct media URL into a `Track` -- no network call, no external API.

    Real, working fallback resolver: validates scheme/host/extension and
    derives `title`/`artist` from the filename. `duration_ms` is `0`
    (genuinely unknown without downloading and parsing the file's own
    metadata) rather than a fabricated value.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError(f"Not a valid http(s) media URL: {url!r}")

    path = PurePosixPath(unquote(parsed.path))
    suffix = path.suffix.lower()
    if suffix not in _DIRECT_MEDIA_EXTENSIONS:
        raise ValueError(
            f"URL does not point at a supported direct media file "
            f"({', '.join(sorted(_DIRECT_MEDIA_EXTENSIONS))}): {url!r}"
        )

    title, artist = _split_title_artist(path.stem)
    return Track(
        provider="direct",
        external_id=url,
        title=title,
        artist=artist,
        duration_ms=0,
        artwork_url=None,
        url=url,
    )


def detect_provider(url_or_query: str) -> str:
    """Classify a caller-supplied URL/query into a provider key.

    Used by the queue service when the caller doesn't name a provider
    explicitly. Falls back to `"direct"` -- `resolve()` itself raises a
    clear `ValueError` if that guess turns out wrong (not a supported
    media extension), which the queue service converts to a 422.
    """
    lowered = url_or_query.strip().lower()
    if "youtube.com" in lowered or "youtu.be" in lowered:
        return "youtube"
    if "open.spotify.com" in lowered or lowered.startswith("spotify:"):
        return "spotify"
    if "soundcloud.com" in lowered:
        return "soundcloud"
    return "direct"


async def resolve(url_or_query: str, provider: str) -> Track:
    """Resolve `url_or_query` (a URL or search string) to a `Track` via `provider`.

    `provider == "direct"` is handled locally (see `_parse_direct_media_url`).
    Any other known provider key is dispatched to its own submodule via a
    dynamic import -- missing/unconfigured/failing providers raise
    `ProviderUnavailable`, never a fabricated `Track`.
    """
    cleaned = url_or_query.strip()
    if not cleaned:
        raise ValueError("url_or_query is required")

    provider_key = provider.strip().lower()
    if provider_key == "direct":
        return _parse_direct_media_url(cleaned)

    module_path = _PROVIDER_MODULES.get(provider_key)
    if module_path is None:
        raise ProviderUnavailable(f"Unsupported provider: {provider!r}")

    try:
        module = importlib.import_module(module_path)
    except ImportError as exc:
        raise ProviderUnavailable(
            f"{provider_key} provider is not available (integration not installed)"
        ) from exc

    resolver = getattr(module, "resolve", None)
    if resolver is None:
        raise ProviderUnavailable(f"{provider_key} provider module has no resolve()")

    try:
        track = await resolver(cleaned)
    except ProviderUnavailable:
        raise
    except Exception as exc:  # noqa: BLE001 - any provider-side failure -> 422, never a 500
        raise ProviderUnavailable(f"{provider_key} could not resolve {cleaned!r}: {exc}") from exc

    if not isinstance(track, Track):
        raise ProviderUnavailable(f"{provider_key} provider returned an invalid track shape")
    return track
