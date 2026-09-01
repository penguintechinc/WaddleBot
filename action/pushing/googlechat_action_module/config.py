"""
Configuration module for Google Chat Action Module.
Loads configuration from environment variables with fallback to
platform_integrations database table for credentials.
"""
import logging
import os
import threading
from typing import Optional

logger = logging.getLogger(__name__)


class Config:
    """Configuration from environment variables."""

    # Google Chat API Configuration (env var fallback, overridden by DB)
    GOOGLE_CHAT_SERVICE_ACCOUNT_KEY: str = os.getenv("GOOGLE_CHAT_SERVICE_ACCOUNT_KEY", "")
    GOOGLE_CHAT_PROJECT_ID: str = os.getenv("GOOGLE_CHAT_PROJECT_ID", "")

    # Database Configuration
    _raw_db_url = os.getenv(
        "DATABASE_URL",
        "postgresql://mod_action_googlechat:mod_action_googlechat_dev_changeme"
        "@localhost:5432/waddlebot",
    )
    DATABASE_URL: str = _raw_db_url.replace("postgresql://", "postgres://")

    # Redis Configuration (for credential refresh notifications)
    REDIS_URL: str = os.getenv("REDIS_URL", "")
    CREDENTIAL_CHANNEL: str = "credentials:googlechat:bot:refreshed"

    # gRPC Configuration
    GRPC_PORT: int = int(os.getenv("GRPC_PORT", "50059"))
    GRPC_MAX_WORKERS: int = int(os.getenv("GRPC_MAX_WORKERS", "10"))

    # REST API Configuration
    REST_PORT: int = int(os.getenv("REST_PORT", "8076"))

    # JWT Authentication
    MODULE_SECRET_KEY: str = os.getenv("MODULE_SECRET_KEY", "")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_SECONDS: int = 3600

    # Module Information
    MODULE_NAME: str = "googlechat_action_module"
    MODULE_VERSION: str = "1.0.0"

    # Performance Settings
    MAX_CONCURRENT_REQUESTS: int = int(
        os.getenv("MAX_CONCURRENT_REQUESTS", "100")
    )
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "30"))

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
        """Load Google Chat credentials from platform_integrations table.

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
                "WHERE platform = 'googlechat' "
                "AND integration_type = 'bot' "
                "AND is_active = TRUE "
                "LIMIT 1"
            )
            if rows and rows[0]:
                row = rows[0]
                with cls._credential_lock:
                    if row[0]:
                        cls.GOOGLE_CHAT_SERVICE_ACCOUNT_KEY = row[0]
                    cls._credentials_loaded = True
                logger.info(
                    "Google Chat credentials loaded from platform_integrations"
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

        if not cls.GOOGLE_CHAT_SERVICE_ACCOUNT_KEY:
            warnings.append(
                "GOOGLE_CHAT_SERVICE_ACCOUNT_KEY not configured - "
                "awaiting admin configuration via hub"
            )

        if not cls.GOOGLE_CHAT_PROJECT_ID:
            warnings.append(
                "GOOGLE_CHAT_PROJECT_ID not configured - "
                "awaiting admin configuration via hub"
            )

        if not cls.MODULE_SECRET_KEY:
            warnings.append(
                "MODULE_SECRET_KEY not configured - "
                "awaiting admin configuration via hub"
            )

        if not cls.DATABASE_URL:
            errors.append("DATABASE_URL is required")

        if warnings:
            for warning in warnings:
                logger.warning(warning)

        return errors

    @classmethod
    def get_info(cls) -> dict:
        """Get module information."""
        return {
            "module_name": cls.MODULE_NAME,
            "module_version": cls.MODULE_VERSION,
            "grpc_port": cls.GRPC_PORT,
            "rest_port": cls.REST_PORT,
            "has_service_account_key": bool(cls.GOOGLE_CHAT_SERVICE_ACCOUNT_KEY),
            "has_project_id": bool(cls.GOOGLE_CHAT_PROJECT_ID),
            "database_configured": bool(cls.DATABASE_URL),
            "credentials_from_db": cls._credentials_loaded,
        }
