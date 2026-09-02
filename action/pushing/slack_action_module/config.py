"""
Configuration module for Slack Action Module.
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

    # Slack API Configuration (env var fallback, overridden by DB)
    SLACK_BOT_TOKEN: str = os.getenv("SLACK_BOT_TOKEN", "")
    SLACK_APP_TOKEN: str = os.getenv("SLACK_APP_TOKEN", "")

    # Database Configuration
    _raw_db_url = os.getenv(
        "DATABASE_URL",
        "postgresql://mod_action_slack:mod_action_slack_dev_changeme"
        "@localhost:5432/waddlebot",
    )
    DATABASE_URL: str = _raw_db_url.replace("postgresql://", "postgres://")

    # Redis Configuration (for credential refresh notifications)
    REDIS_URL: str = os.getenv("REDIS_URL", "")
    CREDENTIAL_CHANNEL: str = "credentials:slack:bot:refreshed"

    # gRPC Configuration
    GRPC_PORT: int = int(os.getenv("GRPC_PORT", "50052"))
    GRPC_MAX_WORKERS: int = int(os.getenv("GRPC_MAX_WORKERS", "10"))

    # REST API Configuration
    REST_PORT: int = int(os.getenv("REST_PORT", "8071"))

    # JWT Authentication
    MODULE_SECRET_KEY: str = os.getenv("MODULE_SECRET_KEY", "")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_SECONDS: int = 3600
    # Service identities permitted to call this module's gRPC servicer.
    ALLOWED_SERVICES: list[str] = os.getenv(
        "ALLOWED_SERVICES", "router_module"
    ).split(",")

    # Module Information
    MODULE_NAME: str = "slack_action_module"
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
        """Load Slack credentials from platform_integrations table.

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
                "WHERE platform = 'slack' "
                "AND integration_type = 'bot' "
                "AND is_active = TRUE "
                "LIMIT 1"
            )
            if rows and rows[0]:
                row = rows[0]
                with cls._credential_lock:
                    if row[0]:
                        cls.SLACK_BOT_TOKEN = row[0]
                    cls._credentials_loaded = True
                logger.info(
                    "Slack credentials loaded from platform_integrations"
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

        if not cls.SLACK_BOT_TOKEN:
            warnings.append(
                "SLACK_BOT_TOKEN not configured - "
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
            "has_slack_token": bool(cls.SLACK_BOT_TOKEN),
            "database_configured": bool(cls.DATABASE_URL),
            "credentials_from_db": cls._credentials_loaded,
        }
