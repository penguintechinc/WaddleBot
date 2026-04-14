"""Configuration for the Credential Manager Module.

Manages:
- Database and Redis connectivity
- Token refresh timing and retry behavior
- Logging and error handling
- Credential state tracking
"""

from __future__ import annotations

import logging
import os
import threading
from typing import Optional
from urllib.parse import quote_plus as _quote_plus

logger = logging.getLogger(__name__)


class Config:
    """Configuration from environment variables."""

    MODULE_NAME: str = "credential_manager"
    MODULE_VERSION: str = "1.0.0"
    MODULE_PORT: int = int(os.getenv("MODULE_PORT", "8095"))

    # Database - build URL from components
    DATABASE_HOST = os.getenv("DATABASE_HOST", "infra-postgres")
    DATABASE_PORT = os.getenv("DATABASE_PORT", "5432")
    DATABASE_NAME = os.getenv("DATABASE_NAME", "waddlebot")
    DATABASE_USER = os.getenv("DATABASE_USER", "waddlebot")
    DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD", "")

    # Redis - build URL from components
    REDIS_HOST = os.getenv("REDIS_HOST", "infra-redis")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
    REDIS_KEY_PREFIX: str = os.getenv("REDIS_KEY_PREFIX", "credentials:")

    # Credential state management
    _credentials_loaded: bool = False
    _credential_lock: threading.Lock = threading.Lock()

    # Token refresh settings
    TOKEN_REFRESH_BUFFER: int = int(
        os.getenv("TOKEN_REFRESH_BUFFER", "300")
    )  # 5 minutes before expiry
    POLL_INTERVAL: int = int(
        os.getenv("POLL_INTERVAL", "60")
    )  # Check every 60 seconds
    MAX_REFRESH_RETRIES: int = int(
        os.getenv("MAX_REFRESH_RETRIES", "3")
    )
    RETRY_BACKOFF_BASE: int = int(
        os.getenv("RETRY_BACKOFF_BASE", "5")
    )  # 5s, 10s, 20s backoff

    # Encryption
    ENCRYPTION_KEY: str = os.getenv("PLATFORM_ENCRYPTION_KEY", "")

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    @classmethod
    def load_credentials_from_db(cls, db_connection) -> bool:
        """Load credentials from platform_integrations table.

        Falls back to environment variables if DB lookup fails.

        Args:
            db_connection: A database connection with executesql support.

        Returns:
            True if credentials were loaded from DB.
        """
        try:
            rows = db_connection.executesql(
                "SELECT access_token, config_data "
                "FROM platform_integrations "
                "WHERE platform = 'credential_manager' "
                "AND integration_type = 'bot' "
                "AND is_active = TRUE "
                "LIMIT 1"
            )
            if rows and rows[0]:
                with cls._credential_lock:
                    cls._credentials_loaded = True
                logger.info(
                    "Credentials loaded from platform_integrations for credential_manager"
                )
                return True
        except Exception as e:
            logger.warning(
                "Failed to load credentials from DB, using env vars: %s", e
            )
        return False

    @classmethod
    def start_credential_listener(cls, redis_client) -> Optional[threading.Thread]:
        """Start a background thread that listens for credential refresh events.

        Args:
            redis_client: A Redis client instance.

        Returns:
            The listener thread, or None if Redis is not configured.
        """
        if not cls.REDIS_URL:
            return None

        channel = "credentials:credential_manager:bot:refreshed"

        def _listen():
            try:
                pubsub = redis_client.pubsub()
                pubsub.subscribe(channel)
                logger.info(
                    "Listening for credential refresh on: %s",
                    channel,
                )
                for message in pubsub.listen():
                    if message["type"] == "message":
                        logger.info(
                            "Credential refresh notification received"
                        )
                        with cls._credential_lock:
                            cls._credentials_loaded = False
            except Exception as e:
                logger.error("Credential listener error: %s", e)

        thread = threading.Thread(
            target=_listen, daemon=True, name="credential-listener"
        )
        thread.start()
        return thread

    @classmethod
    def validate(cls) -> list[str]:
        """Validate required configuration."""
        errors = []
        if not cls.DATABASE_URL:
            errors.append("DATABASE_URL is required")
        if not cls.REDIS_URL:
            errors.append("REDIS_URL is required")
        return errors


# Construct DATABASE_URL from components after class definition
_db_user = Config.DATABASE_USER
_db_password = Config.DATABASE_PASSWORD
_db_host = Config.DATABASE_HOST
_db_port = Config.DATABASE_PORT
_db_name = Config.DATABASE_NAME
if _db_password:
    _encoded_pw = _quote_plus(_db_password)
    Config.DATABASE_URL = f"postgres://{_db_user}:{_encoded_pw}@{_db_host}:{_db_port}/{_db_name}"
else:
    Config.DATABASE_URL = f"postgres://{_db_user}@{_db_host}:{_db_port}/{_db_name}"

# Construct REDIS_URL from components
_redis_password = Config.REDIS_PASSWORD
_redis_host = Config.REDIS_HOST
_redis_port = Config.REDIS_PORT
_redis_db = Config.REDIS_DB
if _redis_password:
    _encoded_redis_pw = _quote_plus(_redis_password)
    Config.REDIS_URL = f"redis://:{_encoded_redis_pw}@{_redis_host}:{_redis_port}/{_redis_db}"
else:
    Config.REDIS_URL = f"redis://{_redis_host}:{_redis_port}/{_redis_db}"
