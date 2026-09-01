"""Credential Manager services.

Includes:
- refresh_service: Main token refresh polling and update logic
- oauth_handlers: Platform-specific OAuth token refresh implementations
"""

from .oauth_handlers import (
    BaseOAuthHandler,
    DiscordOAuthHandler,
    KickOAuthHandler,
    OAuthRefreshError,
    SlackOAuthHandler,
    SpotifyOAuthHandler,
    TwitchOAuthHandler,
    YouTubeOAuthHandler,
    get_handler,
)
from .refresh_service import RefreshService

__all__ = [
    "RefreshService",
    "BaseOAuthHandler",
    "OAuthRefreshError",
    "TwitchOAuthHandler",
    "DiscordOAuthHandler",
    "SlackOAuthHandler",
    "YouTubeOAuthHandler",
    "SpotifyOAuthHandler",
    "KickOAuthHandler",
    "get_handler",
]
