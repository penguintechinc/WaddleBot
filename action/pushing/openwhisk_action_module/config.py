"""
Configuration module for OpenWhisk Action Module.
Loads configuration from environment variables with fallback to
platform_integrations database table for credentials.
"""
import logging
import os
import threading
from typing import Optional

logger = logging.getLogger(__name__)


class Config:
    """Configuration class for OpenWhisk Action Module."""

    # OpenWhisk Configuration
    OPENWHISK_API_HOST: str = os.getenv(
        "OPENWHISK_API_HOST",
        "https://openwhisk.example.com"
    )
    OPENWHISK_AUTH_KEY: str = os.getenv("OPENWHISK_AUTH_KEY", "")  # namespace:key format
    OPENWHISK_NAMESPACE: str = os.getenv("OPENWHISK_NAMESPACE", "guest")
    OPENWHISK_INSECURE: bool = os.getenv("OPENWHISK_INSECURE", "false").lower() == "true"

    # Database Configuration
    # PyDAL expects 'postgres://' not 'postgresql://'
    _raw_db_url: str = os.getenv(
        "DATABASE_URL",
        "postgres://waddlebot:password@localhost:5432/waddlebot"
    )
    DATABASE_URL: str = _raw_db_url.replace("postgresql://", "postgres://")

    # Redis Configuration (for credential refresh notifications)
    REDIS_URL: str = os.getenv("REDIS_URL", "")

    # Server Configuration
    GRPC_PORT: int = int(os.getenv("GRPC_PORT", "50062"))
    REST_PORT: int = int(os.getenv("REST_PORT", "8082"))
    MODULE_PORT: int = int(os.getenv("MODULE_PORT", "8082"))  # Alias for REST_PORT

    # Security Configuration
    MODULE_SECRET_KEY: str = os.getenv(
        "MODULE_SECRET_KEY",
        "waddlebot_openwhisk_action_secret_change_me_in_production"
    )
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_SECONDS: int = 3600
    # Service identities permitted to call this module's gRPC servicer.
    ALLOWED_SERVICES: list[str] = os.getenv(
        "ALLOWED_SERVICES", "router_module"
    ).split(",")

    # Module Information
    MODULE_NAME: str = "openwhisk_action_module"
    MODULE_VERSION: str = "1.0.0"

    # Performance Settings
    MAX_WORKERS: int = int(os.getenv("MAX_WORKERS", "20"))
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "30"))
    MAX_BATCH_SIZE: int = int(os.getenv("MAX_BATCH_SIZE", "100"))

    # OpenWhisk Settings
    DEFAULT_ACTION_TIMEOUT: int = int(os.getenv("DEFAULT_ACTION_TIMEOUT", "60000"))  # 60 seconds
    MAX_ACTION_TIMEOUT: int = int(os.getenv("MAX_ACTION_TIMEOUT", "600000"))  # 10 minutes

    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_DIR: str = os.getenv("LOG_DIR", "/var/log/waddlebotlog")
    ENABLE_SYSLOG: bool = os.getenv("ENABLE_SYSLOG", "false").lower() == "true"
    SYSLOG_HOST: str = os.getenv("SYSLOG_HOST", "localhost")
    SYSLOG_PORT: int = int(os.getenv("SYSLOG_PORT", "514"))
    SYSLOG_FACILITY: str = os.getenv("SYSLOG_FACILITY", "LOCAL0")

    # Testing/Development mode - skips strict validation
    TESTING_MODE: bool = os.getenv("TESTING_MODE", "true").lower() == "true"

    # Credential state management
    _credentials_loaded: bool = False
    _credential_lock: threading.Lock = threading.Lock()

    @classmethod
    def load_credentials_from_db(cls, db_connection) -> bool:
        """Load OpenWhisk credentials from platform_integrations table.

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
                "WHERE platform = 'openwhisk' "
                "AND integration_type = 'bot' "
                "AND is_active = TRUE "
                "LIMIT 1"
            )
            if rows and rows[0]:
                row = rows[0]
                with cls._credential_lock:
                    if row[0]:
                        cls.OPENWHISK_AUTH_KEY = row[0]
                    if row[1]:  # config_data may contain api_host, namespace, etc.
                        import json
                        try:
                            config = json.loads(row[1])
                            if 'api_host' in config:
                                cls.OPENWHISK_API_HOST = config['api_host']
                            if 'namespace' in config:
                                cls.OPENWHISK_NAMESPACE = config['namespace']
                            if 'insecure' in config:
                                cls.OPENWHISK_INSECURE = config['insecure']
                        except (json.JSONDecodeError, ValueError):
                            pass
                    cls._credentials_loaded = True
                logger.info(
                    "OpenWhisk credentials loaded from platform_integrations"
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

        channel = "credentials:openwhisk:bot:refreshed"

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
        """Validate required configuration."""
        if cls.TESTING_MODE:
            # Lenient validation for testing
            if not cls.DATABASE_URL:
                raise ValueError("DATABASE_URL is required")
            return

        # Strict validation for production
        if not cls.OPENWHISK_API_HOST:
            raise ValueError("OPENWHISK_API_HOST is required")
        if not cls.OPENWHISK_AUTH_KEY:
            raise ValueError("OPENWHISK_AUTH_KEY is required (format: namespace:key)")
        if not cls.DATABASE_URL:
            raise ValueError("DATABASE_URL is required")
        if not cls.MODULE_SECRET_KEY or cls.MODULE_SECRET_KEY == "waddlebot_openwhisk_action_secret_change_me_in_production":
            raise ValueError("MODULE_SECRET_KEY must be set to a secure value in production")

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
            "openwhisk_namespace": cls.OPENWHISK_NAMESPACE,
            "openwhisk_api_host": cls.OPENWHISK_API_HOST,
            "credentials_from_db": cls._credentials_loaded,
        }
