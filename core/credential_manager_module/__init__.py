"""Credential Manager Module - Automatic OAuth token refresh service.

Core service for managing OAuth2 token lifecycle across multiple platforms:
- Twitch
- Discord
- Slack
- YouTube/Google
- Spotify
- Kick

Features:
- Automatic token refresh based on expiration
- Exponential backoff retry logic
- Redis pub/sub notifications
- Per-platform OAuth handler implementations
- Comprehensive error handling and logging
"""

__version__ = "1.0.0"
__all__ = ["RefreshService", "Config"]
