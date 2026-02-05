"""
Configuration module for Twitch Action Module.
Loads configuration from environment variables with fallback to
platform_integrations database table for credentials.
"""
import logging
import os
import threading
from typing import Optional

logger = logging.getLogger(__name__)


class Config:
    """Configuration class for Twitch Action Module."""

    # Twitch API Configuration (env var fallback, overridden by DB)
    TWITCH_CLIENT_ID: str = os.getenv("TWITCH_CLIENT_ID", "")
    TWITCH_CLIENT_SECRET: str = os.getenv("TWITCH_CLIENT_SECRET", "")
    TWITCH_API_BASE_URL: str = "https://api.twitch.tv/helix"

    # Database Configuration
    _raw_db_url = os.getenv(
        "DATABASE_URL",
        "postgresql://mod_action_twitch:mod_action_twitch_dev_changeme"
        "@localhost:5432/waddlebot",
    )
    DATABASE_URL: str = _raw_db_url.replace("postgresql://", "postgres://")

    # Redis Configuration (for credential refresh notifications)
    REDIS_URL: str = os.getenv("REDIS_URL", "")
    CREDENTIAL_CHANNEL: str = "credentials:twitch:bot:refreshed"

    # Server Configuration
    GRPC_PORT: int = int(os.getenv("GRPC_PORT", "50053"))
    REST_PORT: int = int(os.getenv("REST_PORT", "8072"))
    MODULE_PORT: int = int(os.getenv("MODULE_PORT", "8072"))

    # Security Configuration
    MODULE_SECRET_KEY: str = os.getenv(
        "MODULE_SECRET_KEY",
        "waddlebot_twitch_action_secret_change_me_in_production",
    )
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_SECONDS: int = 3600

    # Module Information
    MODULE_NAME: str = "twitch_action_module"
    MODULE_VERSION: str = "1.0.0"

    # Performance Settings
    MAX_WORKERS: int = int(os.getenv("MAX_WORKERS", "20"))
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "30"))
    MAX_BATCH_SIZE: int = int(os.getenv("MAX_BATCH_SIZE", "100"))

    # Token Management
    TOKEN_REFRESH_BUFFER: int = int(os.getenv("TOKEN_REFRESH_BUFFER", "300"))

    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_DIR: str = os.getenv("LOG_DIR", "/var/log/waddlebotlog")
    ENABLE_SYSLOG: bool = os.getenv("ENABLE_SYSLOG", "false").lower() == "true"
    SYSLOG_HOST: str = os.getenv("SYSLOG_HOST", "localhost")
    SYSLOG_PORT: int = int(os.getenv("SYSLOG_PORT", "514"))
    SYSLOG_FACILITY: str = os.getenv("SYSLOG_FACILITY", "LOCAL0")

    # Credential state
    _credentials_loaded: bool = False
    _credential_lock: threading.Lock = threading.Lock()

    @classmethod
    def load_credentials_from_db(cls, db_connection) -> bool:
        """Load Twitch credentials from platform_integrations table.

        Falls back to environment variables if DB lookup fails.

        Args:
            db_connection: A database connection with executesql support.

        Returns:
            True if credentials were loaded from DB.
        """
        try:
            rows = db_connection.executesql(
                "SELECT client_id, client_secret, access_token, config_data "
                "FROM platform_integrations "
                "WHERE platform = 'twitch' "
                "AND integration_type = 'bot' "
                "AND is_active = TRUE "
                "LIMIT 1"
            )
            if rows and rows[0]:
                row = rows[0]
                with cls._credential_lock:
                    if row[0]:
                        cls.TWITCH_CLIENT_ID = row[0]
                    if row[1]:
                        cls.TWITCH_CLIENT_SECRET = row[1]
                    cls._credentials_loaded = True
                logger.info(
                    "Twitch credentials loaded from platform_integrations"
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

        def _listen():
            try:
                pubsub = redis_client.pubsub()
                pubsub.subscribe(cls.CREDENTIAL_CHANNEL)
                logger.info(
                    "Listening for credential refresh on: %s",
                    cls.CREDENTIAL_CHANNEL,
                )
                for message in pubsub.listen():
                    if message["type"] == "message":
                        logger.info(
                            "Credential refresh notification received, "
                            "reloading credentials"
                        )
                        # Signal that credentials need reloading
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
        warnings = []

        if not cls.TWITCH_CLIENT_ID:
            warnings.append(
                "TWITCH_CLIENT_ID not configured - "
                "awaiting admin configuration via hub"
            )
        if not cls.TWITCH_CLIENT_SECRET:
            warnings.append(
                "TWITCH_CLIENT_SECRET not configured - "
                "awaiting admin configuration via hub"
            )

        if (
            not cls.MODULE_SECRET_KEY
            or cls.MODULE_SECRET_KEY
            == "waddlebot_twitch_action_secret_change_me_in_production"
        ):
            warnings.append(
                "MODULE_SECRET_KEY should be set to a secure value "
                "in production"
            )

        if not cls.DATABASE_URL:
            errors.append("DATABASE_URL is required")

        if warnings:
            for warning in warnings:
                logger.warning(warning)

        return errors

    @classmethod
    def to_dict(cls) -> dict:
        """Convert configuration to dictionary (excluding secrets)."""
        return {
            "module_name": cls.MODULE_NAME,
            "module_version": cls.MODULE_VERSION,
            "grpc_port": cls.GRPC_PORT,
            "rest_port": cls.REST_PORT,
            "max_workers": cls.MAX_WORKERS,
            "max_batch_size": cls.MAX_BATCH_SIZE,
            "log_level": cls.LOG_LEVEL,
            "credentials_from_db": cls._credentials_loaded,
        }
