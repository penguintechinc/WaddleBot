"""Spotify Web API resolver -- real client-credentials OAuth + real track/search calls.

Credentials: `SPOTIFY_CLIENT_ID`/`SPOTIFY_CLIENT_SECRET` env vars first;
falls back to `~/.spotify.token` (line 1 = client id, line 2 = secret) if
present. The client-credentials bearer token is cached in-process until 60
seconds before its reported expiry, refreshed on demand under a lock so
concurrent resolve()/search() calls don't each mint their own token.

Never logs, prints, or otherwise surfaces the client secret or bearer token.
"""

from __future__ import annotations

import asyncio
import base64
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

from services.music_providers.errors import ProviderUnavailable, TrackNotFound
from services.music_providers.track import Track

_TOKEN_URL = "https://accounts.spotify.com/api/token"
_API_BASE = "https://api.spotify.com/v1"
_TIMEOUT_SECONDS = 10.0
_SEARCH_LIMIT = 10
_TOKEN_FILE = Path.home() / ".spotify.token"
#: Refresh this many seconds before the token's reported expiry, to avoid
#: a request racing an about-to-expire token.
_EXPIRY_SAFETY_MARGIN_SECONDS = 60


@dataclass(slots=True)
class _CachedToken:
    """In-process bearer-token cache entry; `expires_at` is a `time.monotonic()` deadline."""

    value: str
    expires_at: float


_token_cache: _CachedToken | None = None
_token_lock = asyncio.Lock()


def _load_credentials() -> tuple[str, str] | None:
    """Resolve `(client_id, client_secret)` from env or `~/.spotify.token`; `None` if absent."""
    env_id = os.getenv("SPOTIFY_CLIENT_ID")
    env_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    if env_id and env_secret:
        return env_id, env_secret

    if not _TOKEN_FILE.exists():
        return None
    try:
        lines = _TOKEN_FILE.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    if len(lines) < 2:
        return None

    file_id, file_secret = lines[0].strip(), lines[1].strip()
    if not file_id or not file_secret:
        return None
    return file_id, file_secret


async def _get_bearer_token(client: httpx.AsyncClient) -> str:
    """Return a cached or freshly-minted client-credentials bearer token."""
    global _token_cache
    async with _token_lock:
        if _token_cache is not None and _token_cache.expires_at > time.monotonic():
            return _token_cache.value

        credentials = _load_credentials()
        if credentials is None:
            raise ProviderUnavailable("spotify")
        client_id, client_secret = credentials

        basic_auth = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        try:
            response = await client.post(
                _TOKEN_URL,
                data={"grant_type": "client_credentials"},
                headers={
                    "Authorization": f"Basic {basic_auth}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )
        except httpx.HTTPError as exc:
            raise ProviderUnavailable("spotify") from exc

        if response.status_code in (400, 401, 403) or response.status_code >= 500:
            # Invalid/revoked client credentials, or upstream outage --
            # both mean "spotify isn't usable right now".
            raise ProviderUnavailable("spotify") from None
        response.raise_for_status()

        payload: Any = response.json()
        token = payload.get("access_token") if isinstance(payload, dict) else None
        expires_in = payload.get("expires_in", 3600) if isinstance(payload, dict) else 3600
        if not token:
            raise ProviderUnavailable("spotify")

        _token_cache = _CachedToken(
            value=str(token),
            expires_at=time.monotonic() + max(0, int(expires_in) - _EXPIRY_SAFETY_MARGIN_SECONDS),
        )
        return _token_cache.value


def _extract_track_id(url: str) -> str | None:
    """Pull a track id out of an `open.spotify.com/track/<id>` URL."""
    parsed = urlparse(url)
    parts = [segment for segment in parsed.path.split("/") if segment]
    if len(parts) >= 2 and parts[-2] == "track":
        return parts[-1]
    return None


def _best_image(images: list[Any]) -> str | None:
    """Pick the widest album image available, `None` if the list is empty."""
    candidates = [img for img in images if isinstance(img, dict) and img.get("url")]
    if not candidates:
        return None
    best = max(candidates, key=lambda img: img.get("width") or 0)
    return str(best["url"])


def _track_from_item(item: dict[str, Any]) -> Track:
    """Map one Spotify track object (from `/tracks/{id}` or `/search`) into a `Track`."""
    artists = item.get("artists") or []
    artist_name = str(artists[0]["name"]) if artists and artists[0].get("name") else ""
    album = item.get("album") or {}
    track_id = str(item.get("id") or "")
    external_urls = item.get("external_urls") or {}
    return Track(
        provider="spotify",
        external_id=track_id,
        title=str(item.get("name") or ""),
        artist=artist_name,
        duration_ms=int(item.get("duration_ms") or 0),
        artwork_url=_best_image(album.get("images") or []),
        url=str(external_urls.get("spotify") or f"https://open.spotify.com/track/{track_id}"),
    )


async def resolve(url: str) -> Track:
    """Resolve a Spotify track URL to a `Track` via `GET /v1/tracks/{id}`."""
    track_id = _extract_track_id(url)
    if track_id is None:
        raise TrackNotFound(url)

    async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
        token = await _get_bearer_token(client)
        try:
            response = await client.get(
                f"{_API_BASE}/tracks/{track_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
        except httpx.HTTPError as exc:
            raise ProviderUnavailable("spotify") from exc

    if response.status_code == 404:
        raise TrackNotFound(url)
    if response.status_code in (400, 401, 403, 429) or response.status_code >= 500:
        raise ProviderUnavailable("spotify")
    response.raise_for_status()

    data: Any = response.json()
    if not isinstance(data, dict):
        raise TrackNotFound(url)
    return _track_from_item(data)


async def search(query: str) -> list[Track]:
    """Search Spotify tracks via `GET /v1/search?type=track`."""
    async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
        token = await _get_bearer_token(client)
        try:
            response = await client.get(
                f"{_API_BASE}/search",
                params={"q": query, "type": "track", "limit": _SEARCH_LIMIT},
                headers={"Authorization": f"Bearer {token}"},
            )
        except httpx.HTTPError as exc:
            raise ProviderUnavailable("spotify") from exc

    if response.status_code in (400, 401, 403, 429) or response.status_code >= 500:
        raise ProviderUnavailable("spotify")
    response.raise_for_status()

    data: Any = response.json()
    tracks = data.get("tracks") if isinstance(data, dict) else None
    items = (tracks.get("items") if isinstance(tracks, dict) else None) or []
    if not items:
        raise TrackNotFound(query)
    return [_track_from_item(item) for item in items if isinstance(item, dict)]
