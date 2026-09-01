"""YouTube Data API v3 resolver -- real search/videos.list calls, real response parsing.

Credentials: `YOUTUBE_API_KEY` env var first; falls back to reading
`~/.youtube.token` (line 1 = client id, line 2 = secret -- the same
two-line format the other OAuth token files in this repo use). That file
may hold either a raw server API key on line 1, or an actual OAuth client
id (`*.apps.googleusercontent.com`) -- the latter is not usable as a Data
API v3 `key=` query param (that's a server API key, not an OAuth client
credential), so it is treated the same as "no usable key" and the resolver
raises `ProviderUnavailable` rather than sending a request that would only
fail with a 400 anyway.

Never logs, prints, or otherwise surfaces the key/token value itself.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx

from services.music_providers.errors import ProviderUnavailable, TrackNotFound
from services.music_providers.track import Track

_API_BASE = "https://www.googleapis.com/youtube/v3"
_TIMEOUT_SECONDS = 10.0
_SEARCH_MAX_RESULTS = 10
_TOKEN_FILE = Path.home() / ".youtube.token"

#: Highest-quality-first; `snippet.thumbnails` only guarantees `default`.
_THUMBNAIL_PRIORITY = ("maxres", "standard", "high", "medium", "default")

#: `contentDetails.duration` is ISO-8601 (`PT4M13S`); `P0D` for live streams.
_ISO8601_DURATION_RE = re.compile(
    r"^P(?:\d+D)?T?(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?$"
)


def _load_api_key() -> str | None:
    """Resolve a usable Data API v3 key from env or `~/.youtube.token`; `None` if unusable."""
    env_key = os.getenv("YOUTUBE_API_KEY")
    if env_key:
        return env_key

    if not _TOKEN_FILE.exists():
        return None
    try:
        lines = _TOKEN_FILE.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    if not lines:
        return None

    candidate = lines[0].strip()
    if not candidate or candidate.endswith(".apps.googleusercontent.com"):
        # OAuth client id, not a server API key -- unusable for this flow.
        return None
    return candidate


def _extract_video_id(url: str) -> str | None:
    """Pull a video id out of any of youtube.com/youtu.be's URL shapes."""
    parsed = urlparse(url)
    host = (parsed.netloc or "").lower()

    if host == "youtu.be":
        video_id = parsed.path.lstrip("/")
        return video_id or None

    if host == "youtube.com" or host.endswith(".youtube.com"):
        query = parse_qs(parsed.query)
        if "v" in query and query["v"]:
            return query["v"][0]
        for prefix in ("/embed/", "/shorts/", "/live/"):
            if parsed.path.startswith(prefix):
                video_id = parsed.path[len(prefix) :].split("/")[0]
                return video_id or None

    return None


def _parse_iso8601_duration_ms(duration: str) -> int:
    """Convert `contentDetails.duration` (e.g. `PT4M13S`) to milliseconds."""
    match = _ISO8601_DURATION_RE.match(duration)
    if not match:
        return 0
    hours = int(match.group("hours") or 0)
    minutes = int(match.group("minutes") or 0)
    seconds = int(match.group("seconds") or 0)
    return (hours * 3600 + minutes * 60 + seconds) * 1000


def _best_thumbnail(thumbnails: dict[str, Any]) -> str | None:
    """Pick the highest-resolution thumbnail available, `None` if the dict is empty."""
    for key in _THUMBNAIL_PRIORITY:
        thumb = thumbnails.get(key)
        if isinstance(thumb, dict) and thumb.get("url"):
            return str(thumb["url"])
    return None


def _track_from_video_item(item: dict[str, Any]) -> Track:
    """Map one `videos.list` item into a normalized `Track`."""
    snippet = item.get("snippet") or {}
    content_details = item.get("contentDetails") or {}
    video_id = str(item.get("id") or "")
    return Track(
        provider="youtube",
        external_id=video_id,
        title=str(snippet.get("title") or ""),
        artist=str(snippet.get("channelTitle") or ""),
        duration_ms=_parse_iso8601_duration_ms(str(content_details.get("duration") or "")),
        artwork_url=_best_thumbnail(snippet.get("thumbnails") or {}),
        url=f"https://www.youtube.com/watch?v={video_id}",
    )


async def _get_json(client: httpx.AsyncClient, path: str, params: dict[str, Any]) -> dict[str, Any]:
    """GET one Data API v3 endpoint; maps auth/quota/network failures to `ProviderUnavailable`."""
    try:
        response = await client.get(f"{_API_BASE}{path}", params=params)
    except httpx.HTTPError as exc:
        raise ProviderUnavailable("youtube") from exc

    if response.status_code in (400, 401, 403, 429) or response.status_code >= 500:
        # Invalid/revoked key, quota exceeded, or upstream outage -- all
        # mean "youtube isn't usable right now", same as absent creds.
        raise ProviderUnavailable("youtube") from None
    response.raise_for_status()

    data: Any = response.json()
    return data if isinstance(data, dict) else {}


async def resolve(url: str) -> Track:
    """Resolve a YouTube video URL to a `Track` via `videos.list`."""
    api_key = _load_api_key()
    if api_key is None:
        raise ProviderUnavailable("youtube")

    video_id = _extract_video_id(url)
    if video_id is None:
        raise TrackNotFound(url)

    async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
        data = await _get_json(
            client,
            "/videos",
            {"part": "snippet,contentDetails", "id": video_id, "key": api_key},
        )

    items = data.get("items") or []
    if not items:
        raise TrackNotFound(url)
    return _track_from_video_item(items[0])


async def search(query: str) -> list[Track]:
    """Search YouTube via `search.list`, then hydrate durations via `videos.list`."""
    api_key = _load_api_key()
    if api_key is None:
        raise ProviderUnavailable("youtube")

    async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
        search_data = await _get_json(
            client,
            "/search",
            {
                "part": "snippet",
                "q": query,
                "type": "video",
                "maxResults": _SEARCH_MAX_RESULTS,
                "key": api_key,
            },
        )
        video_ids = [
            str(item["id"]["videoId"])
            for item in search_data.get("items") or []
            if isinstance(item.get("id"), dict) and item["id"].get("videoId")
        ]
        if not video_ids:
            raise TrackNotFound(query)

        videos_data = await _get_json(
            client,
            "/videos",
            {"part": "snippet,contentDetails", "id": ",".join(video_ids), "key": api_key},
        )

    items = videos_data.get("items") or []
    if not items:
        raise TrackNotFound(query)
    return [_track_from_video_item(item) for item in items]
