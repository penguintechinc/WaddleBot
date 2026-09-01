"""`services/music_providers/__init__.py` -- provider-resolution contract unit tests.

Exercises `resolve()`/`detect_provider()` directly (not through the
blueprint) to cover every dispatch branch: local `"direct"` success/
failure, unsupported provider key, missing submodule (`ImportError` ->
`ProviderUnavailable`), a submodule that raises, and a submodule that
returns something that isn't a `Track`. The blueprint-level tests
(`test_v1_community_music_queue_blueprint.py`) only exercise the
`"direct"` success path and the "module genuinely absent" path -- this
file covers the remaining branches a real YouTube/Spotify/SoundCloud
submodule landing later would hit.
"""

from __future__ import annotations

import sys
import types
from typing import Any

import pytest

from services.music_providers import ProviderUnavailable, detect_provider, resolve
from services.music_providers.track import Track


class TestDetectProvider:
    def test_youtube_urls(self) -> None:
        assert detect_provider("https://www.youtube.com/watch?v=abc") == "youtube"
        assert detect_provider("https://youtu.be/abc") == "youtube"

    def test_spotify_urls(self) -> None:
        assert detect_provider("https://open.spotify.com/track/abc") == "spotify"
        assert detect_provider("spotify:track:abc") == "spotify"

    def test_soundcloud_urls(self) -> None:
        assert detect_provider("https://soundcloud.com/artist/track") == "soundcloud"

    def test_unknown_falls_back_to_direct(self) -> None:
        assert detect_provider("https://cdn.example.com/song.mp3") == "direct"


class TestDirectResolver:
    async def test_resolves_supported_extension(self) -> None:
        track = await resolve("https://cdn.example.com/Artist - Title.mp3", "direct")
        assert track.provider == "direct"
        assert track.artist == "Artist"
        assert track.title == "Title"
        assert track.duration_ms == 0

    async def test_rejects_non_http_scheme(self) -> None:
        with pytest.raises(ValueError, match="Not a valid http"):
            await resolve("ftp://cdn.example.com/song.mp3", "direct")

    async def test_rejects_unsupported_extension(self) -> None:
        with pytest.raises(ValueError, match="does not point at a supported"):
            await resolve("https://cdn.example.com/document.pdf", "direct")

    async def test_filename_without_separator_falls_back_to_unknown_artist(self) -> None:
        track = await resolve("https://cdn.example.com/CoolSong.mp3", "direct")
        assert track.artist == "Unknown Artist"
        assert track.title == "CoolSong"

    async def test_empty_url_or_query_is_value_error(self) -> None:
        with pytest.raises(ValueError, match="required"):
            await resolve("   ", "direct")


class TestProviderDispatch:
    async def test_unsupported_provider_is_unavailable(self) -> None:
        with pytest.raises(ProviderUnavailable, match="Unsupported provider"):
            await resolve("some query", "napster")

    async def test_uninstalled_provider_module_is_unavailable(self) -> None:
        """No `services/music_providers/youtube.py` exists yet -- real `ImportError`, not a stub."""
        with pytest.raises(ProviderUnavailable, match="not available"):
            await resolve("https://www.youtube.com/watch?v=abc", "youtube")

    async def test_provider_module_without_resolve_is_unavailable(self, monkeypatch: Any) -> None:
        fake_module = types.ModuleType("services.music_providers.youtube")
        monkeypatch.setitem(sys.modules, "services.music_providers.youtube", fake_module)
        try:
            with pytest.raises(ProviderUnavailable, match="has no resolve"):
                await resolve("query", "youtube")
        finally:
            del sys.modules["services.music_providers.youtube"]

    async def test_provider_resolver_exception_is_unavailable(self, monkeypatch: Any) -> None:
        fake_module = types.ModuleType("services.music_providers.spotify")

        async def _boom(_: str) -> Track:
            raise RuntimeError("expired OAuth token")

        fake_module.resolve = _boom  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, "services.music_providers.spotify", fake_module)
        try:
            with pytest.raises(ProviderUnavailable, match="expired OAuth token"):
                await resolve("query", "spotify")
        finally:
            del sys.modules["services.music_providers.spotify"]

    async def test_provider_resolver_bad_return_shape_is_unavailable(
        self, monkeypatch: Any
    ) -> None:
        fake_module = types.ModuleType("services.music_providers.soundcloud")

        async def _bad_return(_: str) -> dict[str, str]:
            return {"not": "a track"}

        fake_module.resolve = _bad_return  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, "services.music_providers.soundcloud", fake_module)
        try:
            with pytest.raises(ProviderUnavailable, match="invalid track shape"):
                await resolve("query", "soundcloud")
        finally:
            del sys.modules["services.music_providers.soundcloud"]

    async def test_provider_resolver_success(self, monkeypatch: Any) -> None:
        fake_module = types.ModuleType("services.music_providers.youtube")
        expected = Track(
            provider="youtube",
            external_id="abc123",
            title="Song",
            artist="Band",
            duration_ms=180000,
            artwork_url="https://img.example.com/abc123.jpg",
            url="https://www.youtube.com/watch?v=abc123",
        )

        async def _ok(_: str) -> Track:
            return expected

        fake_module.resolve = _ok  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, "services.music_providers.youtube", fake_module)
        try:
            track = await resolve("https://www.youtube.com/watch?v=abc123", "youtube")
            assert track is expected
        finally:
            del sys.modules["services.music_providers.youtube"]

    async def test_provider_unavailable_raised_by_resolver_propagates_unchanged(
        self, monkeypatch: Any
    ) -> None:
        fake_module = types.ModuleType("services.music_providers.spotify")

        async def _unavailable(_: str) -> Track:
            raise ProviderUnavailable("missing SPOTIFY_CLIENT_ID")

        fake_module.resolve = _unavailable  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, "services.music_providers.spotify", fake_module)
        try:
            with pytest.raises(ProviderUnavailable, match="missing SPOTIFY_CLIENT_ID"):
                await resolve("query", "spotify")
        finally:
            del sys.modules["services.music_providers.spotify"]
