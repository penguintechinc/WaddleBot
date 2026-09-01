"""
Tests for YouTubeProvider URL-host validation.

Regression coverage for CodeQL py/incomplete-url-substring-sanitization
(alert #416): `get_track()` used to decide "is this a URL" via
`"youtube.com" in track_id or "youtu.be" in track_id`, a substring check
that a crafted string could satisfy without the value actually being a
youtube.com/youtu.be URL. The fix replaces it with
`YouTubeProvider.is_youtube_url()`, which resolves the real host via
`urlparse().hostname` and allowlists it exactly.
"""

from providers.youtube_provider import YouTubeProvider


def test_is_youtube_url_accepts_genuine_hosts():
    """Real youtube.com/youtu.be URLs (with or without www/subdomain) pass."""
    assert YouTubeProvider.is_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert YouTubeProvider.is_youtube_url("https://youtube.com/watch?v=dQw4w9WgXcQ")
    assert YouTubeProvider.is_youtube_url("https://youtu.be/dQw4w9WgXcQ")
    assert YouTubeProvider.is_youtube_url("http://m.youtube.com/watch?v=dQw4w9WgXcQ")
    # Scheme-less paste, as a user might type it into chat
    assert YouTubeProvider.is_youtube_url("youtu.be/dQw4w9WgXcQ")


def test_is_youtube_url_rejects_substring_spoofs():
    """Strings that merely CONTAIN 'youtube.com'/'youtu.be' as a substring,
    without that being the actual host, must be rejected.

    This is the exact bypass the old substring check
    (`"youtube.com" in track_id`) let through -- CodeQL flags it as
    py/incomplete-url-substring-sanitization.
    """
    spoofs = [
        "https://evil.com/?redirect=youtube.com/watch?v=dQw4w9WgXcQ",
        "https://notyoutube.com.evil.com/watch?v=dQw4w9WgXcQ",
        "https://youtube.com.attacker.net/watch?v=dQw4w9WgXcQ",
        "https://evil.com/youtu.be/dQw4w9WgXcQ",
        "https://attacker.example/path?x=youtu.be",
    ]
    for spoof in spoofs:
        assert not YouTubeProvider.is_youtube_url(spoof), f"should reject: {spoof}"


def test_is_youtube_url_rejects_bare_video_id():
    """A bare 11-char video ID (no host at all) is not a URL."""
    assert not YouTubeProvider.is_youtube_url("dQw4w9WgXcQ")


def test_is_youtube_url_rejects_empty_string():
    assert not YouTubeProvider.is_youtube_url("")
