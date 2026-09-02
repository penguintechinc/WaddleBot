"""
YouTube Action Module Configuration.
Loads configuration from environment variables with fallback to
platform_integrations database table for credentials.
"""
import logging
import os
import threading
from typing import Optional

logger = logging.getLogger(__name__)


class Config:
    """Configuration management for YouTube Action Module"""

    # Module Info
    MODULE_NAME: str = "youtube_action_module"
    MODULE_VERSION: str = "1.0.0"

    # Server Ports
    GRPC_PORT: int = int(os.getenv("GRPC_PORT", "50054"))
    REST_PORT: int = int(os.getenv("REST_PORT", "8073"))

    # Database
    _raw_db_url = os.getenv(
        "DATABASE_URL",
        "postgresql://user:pass@localhost:5432/waddlebot"
    )
    DATABASE_URL: str = _raw_db_url.replace("postgresql://", "postgres://")

    # Redis Configuration (for credential refresh notifications)
    REDIS_URL: str = os.getenv("REDIS_URL", "")

    # YouTube API Configuration
    YOUTUBE_API_KEY: Optional[str] = os.getenv("YOUTUBE_API_KEY")
    YOUTUBE_CLIENT_ID: Optional[str] = os.getenv("YOUTUBE_CLIENT_ID")
    YOUTUBE_CLIENT_SECRET: Optional[str] = os.getenv("YOUTUBE_CLIENT_SECRET")
    YOUTUBE_API_VERSION: str = os.getenv("YOUTUBE_API_VERSION", "v3")

    # OAuth Configuration
    YOUTUBE_REDIRECT_URI: str = os.getenv(
        "YOUTUBE_REDIRECT_URI",
        "http://localhost:8073/oauth/callback"
    )
    YOUTUBE_SCOPES: list[str] = [
        "https://www.googleapis.com/auth/youtube",
        "https://www.googleapis.com/auth/youtube.force-ssl",
    ]

    # Security
    MODULE_SECRET_KEY: str = os.getenv(
        "MODULE_SECRET_KEY",
        "youtube_action_secret_key_change_me_in_production"
    )
    JWT_ALGORITHM: str = "HS256"
    # Service identities permitted to call this module's gRPC servicer.
    ALLOWED_SERVICES: list[str] = os.getenv(
        "ALLOWED_SERVICES", "router_module"
    ).split(",")

    # Performance Settings
    MAX_WORKERS: int = int(os.getenv("MAX_WORKERS", "20"))
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "30"))
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))

    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
    RATE_LIMIT_WINDOW: int = int(os.getenv("RATE_LIMIT_WINDOW", "60"))

    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_DIR: str = os.getenv("LOG_DIR", "/var/log/waddlebotlog")
    ENABLE_SYSLOG: bool = os.getenv("ENABLE_SYSLOG", "false").lower() == "true"
    SYSLOG_HOST: str = os.getenv("SYSLOG_HOST", "localhost")
    SYSLOG_PORT: int = int(os.getenv("SYSLOG_PORT", "514"))
    SYSLOG_FACILITY: str = os.getenv("SYSLOG_FACILITY", "LOCAL0")

    # Feature Flags
    ENABLE_CHAT_ACTIONS: bool = os.getenv(
        "ENABLE_CHAT_ACTIONS", "true"
    ).lower() == "true"
    ENABLE_VIDEO_ACTIONS: bool = os.getenv(
        "ENABLE_VIDEO_ACTIONS", "true"
    ).lower() == "true"
    ENABLE_PLAYLIST_ACTIONS: bool = os.getenv(
        "ENABLE_PLAYLIST_ACTIONS", "true"
    ).lower() == "true"
    ENABLE_BROADCAST_ACTIONS: bool = os.getenv(
        "ENABLE_BROADCAST_ACTIONS", "true"
    ).lower() == "true"
    ENABLE_COMMENT_ACTIONS: bool = os.getenv(
        "ENABLE_COMMENT_ACTIONS", "true"
    ).lower() == "true"

    # Credential state management
    _credentials_loaded: bool = False
    _credential_lock: threading.Lock = threading.Lock()

    @classmethod
    def load_credentials_from_db(cls, db_connection) -> bool:
        """Load YouTube credentials from platform_integrations table.

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
                "WHERE platform = 'youtube' "
                "AND integration_type = 'bot' "
                "AND is_active = TRUE "
                "LIMIT 1"
            )
            if rows and rows[0]:
                row = rows[0]
                with cls._credential_lock:
                    if row[0]:
                        cls.YOUTUBE_CLIENT_ID = row[0]
                    if row[1]:
                        cls.YOUTUBE_CLIENT_SECRET = row[1]
                    if row[2]:
                        cls.YOUTUBE_API_KEY = row[2]
                    cls._credentials_loaded = True
                logger.info(
                    "YouTube credentials loaded from platform_integrations"
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

        channel = "credentials:youtube:bot:refreshed"

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
    def validate(cls) -> None:
        """Validate configuration"""
        errors = []

        if not cls.YOUTUBE_CLIENT_ID:
            errors.append("YOUTUBE_CLIENT_ID is required")

        if not cls.YOUTUBE_CLIENT_SECRET:
            errors.append("YOUTUBE_CLIENT_SECRET is required")

        if not cls.DATABASE_URL:
            errors.append("DATABASE_URL is required")

        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")
