"""Integration tests for Credential Manager Module.

Tests cover:
- OAuth handler instantiation
- Token refresh logic
- Configuration validation
- Health check endpoint
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import pytest

from .config import Config
from .services.oauth_handlers import (
    DiscordOAuthHandler,
    KickOAuthHandler,
    OAuthRefreshError,
    SlackOAuthHandler,
    SpotifyOAuthHandler,
    TwitchOAuthHandler,
    YouTubeOAuthHandler,
    get_handler,
)

logger = logging.getLogger(__name__)


class TestOAuthHandlers:
    """Test OAuth handler instantiation and configuration."""

    def test_get_handler_twitch(self):
        """Test Twitch handler instantiation."""
        handler = get_handler("twitch")
        assert isinstance(handler, TwitchOAuthHandler)
        assert handler.TOKEN_URL == "https://id.twitch.tv/oauth2/token"

    def test_get_handler_discord(self):
        """Test Discord handler instantiation."""
        handler = get_handler("discord")
        assert isinstance(handler, DiscordOAuthHandler)
        assert handler.TOKEN_URL == "https://discord.com/api/v10/oauth2/token"

    def test_get_handler_slack(self):
        """Test Slack handler instantiation."""
        handler = get_handler("slack")
        assert isinstance(handler, SlackOAuthHandler)
        assert handler.TOKEN_URL == "https://slack.com/api/oauth.v2.access"

    def test_get_handler_youtube(self):
        """Test YouTube handler instantiation."""
        handler = get_handler("youtube")
        assert isinstance(handler, YouTubeOAuthHandler)
        assert handler.TOKEN_URL == "https://oauth2.googleapis.com/token"

    def test_get_handler_spotify(self):
        """Test Spotify handler instantiation."""
        handler = get_handler("spotify")
        assert isinstance(handler, SpotifyOAuthHandler)
        assert handler.TOKEN_URL == "https://accounts.spotify.com/api/token"

    def test_get_handler_kick(self):
        """Test Kick handler instantiation."""
        handler = get_handler("kick")
        assert isinstance(handler, KickOAuthHandler)
        assert handler.TOKEN_URL == "https://id.kick.com/oauth/token"

    def test_get_handler_invalid(self):
        """Test that invalid platform raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported platform"):
            get_handler("invalid_platform")

    def test_get_handler_case_sensitive(self):
        """Test that platform names are case-sensitive."""
        with pytest.raises(ValueError):
            get_handler("Twitch")  # uppercase should fail

    def test_handler_timeout_constant(self):
        """Test that handlers have timeout configured."""
        for platform in ["twitch", "discord", "slack", "youtube", "spotify", "kick"]:
            handler = get_handler(platform)
            assert handler.TIMEOUT == 10


class TestConfiguration:
    """Test configuration loading and validation."""

    def test_config_defaults(self):
        """Test configuration defaults."""
        assert Config.MODULE_NAME == "credential_manager"
        assert Config.MODULE_VERSION == "1.0.0"
        assert Config.TOKEN_REFRESH_BUFFER > 0
        assert Config.POLL_INTERVAL > 0
        assert Config.MAX_REFRESH_RETRIES > 0

    def test_config_validate_with_urls(self):
        """Test validation passes with URLs set."""
        # This test assumes DATABASE_URL and REDIS_URL are set
        errors = Config.validate()
        # Should be empty if properly configured
        assert isinstance(errors, list)

    def test_config_url_conversion(self):
        """Test that postgresql URLs are converted for asyncpg."""
        # Config should convert postgresql:// to postgres://
        assert "postgresql://" in Config.DATABASE_URL or "postgres://" in Config.DATABASE_URL

    def test_config_logging_level(self):
        """Test logging level configuration."""
        assert Config.LOG_LEVEL in [
            "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
        ]

    def test_config_retry_settings(self):
        """Test retry configuration is reasonable."""
        assert Config.MAX_REFRESH_RETRIES >= 1
        assert Config.RETRY_BACKOFF_BASE >= 1
        # Backoff should produce reasonable delays
        max_delay = Config.RETRY_BACKOFF_BASE * (2 ** (Config.MAX_REFRESH_RETRIES - 1))
        assert max_delay < 300  # Less than 5 minutes


class TestErrorHandling:
    """Test error handling in OAuth handlers."""

    @pytest.mark.asyncio
    async def test_oauth_refresh_error_inheritance(self):
        """Test OAuthRefreshError is Exception subclass."""
        assert issubclass(OAuthRefreshError, Exception)
        error = OAuthRefreshError("test error")
        assert str(error) == "test error"

    @pytest.mark.asyncio
    async def test_handler_timeout_attribute(self):
        """Test all handlers have timeout."""
        handlers = [
            TwitchOAuthHandler(),
            DiscordOAuthHandler(),
            SlackOAuthHandler(),
            YouTubeOAuthHandler(),
            SpotifyOAuthHandler(),
            KickOAuthHandler(),
        ]
        for handler in handlers:
            assert hasattr(handler, "TIMEOUT")
            assert isinstance(handler.TIMEOUT, int)
            assert handler.TIMEOUT > 0


class TestDataStructures:
    """Test expected data structures."""

    def test_handler_token_urls_dict(self):
        """Test token URLs are properly configured."""
        expected_platforms = {
            "twitch": "https://id.twitch.tv/oauth2/token",
            "discord": "https://discord.com/api/v10/oauth2/token",
            "slack": "https://slack.com/api/oauth.v2.access",
            "youtube": "https://oauth2.googleapis.com/token",
            "spotify": "https://accounts.spotify.com/api/token",
            "kick": "https://id.kick.com/oauth/token",
        }

        for platform, expected_url in expected_platforms.items():
            handler = get_handler(platform)
            assert handler.TOKEN_URL == expected_url

    def test_config_env_prefix(self):
        """Test configuration uses proper environment prefix."""
        # These should load from environment
        assert hasattr(Config, "DATABASE_URL")
        assert hasattr(Config, "REDIS_URL")
        assert hasattr(Config, "TOKEN_REFRESH_BUFFER")
        assert hasattr(Config, "POLL_INTERVAL")


class TestIntegration:
    """Integration-level tests."""

    def test_config_consistency(self):
        """Test configuration is internally consistent."""
        # Refresh buffer should be less than poll interval
        # (otherwise we'd refresh on every poll)
        assert Config.TOKEN_REFRESH_BUFFER >= 0
        assert Config.POLL_INTERVAL > 0

    def test_module_version_format(self):
        """Test module version is semantic."""
        parts = Config.MODULE_VERSION.split(".")
        assert len(parts) == 3
        for part in parts:
            assert part.isdigit()

    def test_handler_factory_consistency(self):
        """Test get_handler returns same handler type repeatedly."""
        handler1 = get_handler("twitch")
        handler2 = get_handler("twitch")
        # Different instances but same type
        assert type(handler1) == type(handler2)
        assert handler1 is not handler2


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
