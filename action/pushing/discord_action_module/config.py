"""
Configuration management for Discord Action Module

Loads configuration from environment variables with fallback to
platform_integrations database table for credentials.
"""

import logging
import os
import threading
from typing import Optional

logger = logging.getLogger(__name__)


class Config:
    """Configuration class for Discord Action Module"""

    # Discord API Configuration
    DISCORD_BOT_TOKEN: str = os.getenv("DISCORD_BOT_TOKEN", "")
    DISCORD_API_VERSION: str = os.getenv("DISCORD_API_VERSION", "10")
    DISCORD_API_BASE: str = f"https://discord.com/api/v{DISCORD_API_VERSION}"

    # Database Configuration
    _raw_db_url = os.getenv(
        "DATABASE_URL",
        "postgresql://user:pass@localhost:5432/waddlebot"
    )
    DATABASE_URL: str = _raw_db_url.replace("postgresql://", "postgres://")

    # Redis Configuration (for credential refresh notifications)
    REDIS_URL: str = os.getenv("REDIS_URL", "")

    # Server Configuration
    GRPC_PORT: int = int(os.getenv("GRPC_PORT", "50051"))
    REST_PORT: int = int(os.getenv("REST_PORT", "8070"))
    HOST: str = os.getenv("HOST", "0.0.0.0")

    # Security Configuration
    MODULE_SECRET_KEY: str = os.getenv(
        "MODULE_SECRET_KEY",
        "change_me_in_production_64_char_key_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    )
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_SECONDS: int = int(os.getenv("JWT_EXPIRATION_SECONDS", "3600"))
    # Service identities permitted to call this module's gRPC servicer.
    ALLOWED_SERVICES: list[str] = os.getenv(
        "ALLOWED_SERVICES", "router_module"
    ).split(",")

    # Module Information
    MODULE_NAME: str = "discord_action_module"
    MODULE_VERSION: str = os.getenv("MODULE_VERSION", "1.0.0")

    # Performance Settings
    MAX_CONCURRENT_REQUESTS: int = int(os.getenv("MAX_CONCURRENT_REQUESTS", "100"))
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "30"))

    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_DIR: str = os.getenv("LOG_DIR", "/var/log/waddlebotlog")
    ENABLE_SYSLOG: bool = os.getenv("ENABLE_SYSLOG", "false").lower() == "true"
    SYSLOG_HOST: str = os.getenv("SYSLOG_HOST", "localhost")
    SYSLOG_PORT: int = int(os.getenv("SYSLOG_PORT", "514"))
    SYSLOG_FACILITY: str = os.getenv("SYSLOG_FACILITY", "LOCAL0")

    # Discord Rate Limiting
    DISCORD_RATE_LIMIT_GLOBAL: int = int(os.getenv("DISCORD_RATE_LIMIT_GLOBAL", "50"))
    DISCORD_RATE_LIMIT_PER_CHANNEL: int = int(
        os.getenv("DISCORD_RATE_LIMIT_PER_CHANNEL", "5")
    )

    # Retry Configuration
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    RETRY_DELAY: float = float(os.getenv("RETRY_DELAY", "1.0"))

    # Credential state management
    _credentials_loaded: bool = False
    _credential_lock: threading.Lock = threading.Lock()

    @classmethod
    def load_credentials_from_db(cls, db_connection) -> bool:
        """Load Discord credentials from platform_integrations table.

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
                "WHERE platform = 'discord' "
                "AND integration_type = 'bot' "
                "AND is_active = TRUE "
                "LIMIT 1"
            )
            if rows and rows[0]:
                row = rows[0]
                with cls._credential_lock:
                    if row[0]:
                        cls.DISCORD_BOT_TOKEN = row[0]
                    cls._credentials_loaded = True
                logger.info(
                    "Discord credentials loaded from platform_integrations"
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

        channel = "credentials:discord:bot:refreshed"

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
                            "Credential refresh notification received, "
                            "reloading credentials"
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
    def validate(cls) -> tuple[list[str], list[str]]:
        """
        Validate configuration and return errors and warnings separately

        Returns:
            Tuple of (error_list, warning_list)
        """
        errors = []
        warnings = []

        if not cls.DATABASE_URL:
            errors.append("DATABASE_URL is required")

        if cls.GRPC_PORT < 1 or cls.GRPC_PORT > 65535:
            errors.append("GRPC_PORT must be between 1 and 65535")

        if cls.REST_PORT < 1 or cls.REST_PORT > 65535:
            errors.append("REST_PORT must be between 1 and 65535")

        # Optional credentials - warn but don't fail startup
        if not cls.DISCORD_BOT_TOKEN:
            warnings.append("DISCORD_BOT_TOKEN not configured - Discord API calls will fail")

        if len(cls.MODULE_SECRET_KEY) < 64:
            warnings.append("MODULE_SECRET_KEY less than 64 chars - consider setting for production")

        return errors, warnings

    @classmethod
    def get_summary(cls) -> dict:
        """
        Get configuration summary (without sensitive data)

        Returns:
            Dictionary with configuration summary
        """
        return {
            "module_name": cls.MODULE_NAME,
            "module_version": cls.MODULE_VERSION,
            "grpc_port": cls.GRPC_PORT,
            "rest_port": cls.REST_PORT,
            "database_configured": bool(cls.DATABASE_URL),
            "discord_token_configured": bool(cls.DISCORD_BOT_TOKEN),
            "max_concurrent_requests": cls.MAX_CONCURRENT_REQUESTS,
            "request_timeout": cls.REQUEST_TIMEOUT,
            "log_level": cls.LOG_LEVEL,
            "credentials_from_db": cls._credentials_loaded,
        }
