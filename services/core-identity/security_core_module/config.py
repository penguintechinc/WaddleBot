"""
Security Core Module Configuration
"""
import logging
import os
import threading
from typing import Optional
from urllib.parse import quote_plus as _quote_plus

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class Config:
    """Security module configuration from environment variables."""

    # Module identity
    MODULE_NAME = 'security-core'
    MODULE_VERSION = '1.0.0'
    MODULE_PORT = int(os.getenv('MODULE_PORT', '8041'))

    # Database - build URL from components
    DATABASE_HOST = os.getenv('DATABASE_HOST', 'infra-postgres')
    DATABASE_PORT = os.getenv('DATABASE_PORT', '5432')
    DATABASE_NAME = os.getenv('DATABASE_NAME', 'waddlebot')
    DATABASE_USER = os.getenv('DATABASE_USER', 'waddlebot')
    DATABASE_PASSWORD = os.getenv('DATABASE_PASSWORD', '')

    # Redis for rate limiting and caching - build URL from components
    REDIS_HOST = os.getenv('REDIS_HOST', 'infra-redis')
    REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
    REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', '')
    REDIS_DB = int(os.getenv('REDIS_DB', '1'))  # Use DB 1 for security

    # Credential state management
    _credentials_loaded: bool = False
    _credential_lock: threading.Lock = threading.Lock()

    # Internal service URLs
    ROUTER_API_URL = os.getenv(
        'ROUTER_API_URL',
        'http://router-service:8000/api/v1/router'
    )
    REPUTATION_API_URL = os.getenv(
        'REPUTATION_API_URL',
        'http://reputation:8021/api/v1/reputation'
    )

    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    SECRET_KEY = os.getenv('SECRET_KEY', 'change-me-in-production')
    SERVICE_API_KEY = os.getenv('SERVICE_API_KEY', '')

    # Default profanity filter (opt-in)
    DEFAULT_USE_BUILTIN_PROFANITY = False

    # Default spam detection settings
    DEFAULT_SPAM_MESSAGE_THRESHOLD = 5  # messages per interval
    DEFAULT_SPAM_INTERVAL_SECONDS = 10
    DEFAULT_SPAM_DUPLICATE_THRESHOLD = 3

    # Default rate limiting
    DEFAULT_RATE_LIMIT_MESSAGES_PER_MINUTE = 30
    DEFAULT_RATE_LIMIT_COMMANDS_PER_MINUTE = 10

    # Default warning system
    DEFAULT_WARNING_THRESHOLD_TIMEOUT = 3
    DEFAULT_WARNING_THRESHOLD_BAN = 5
    DEFAULT_WARNING_DECAY_DAYS = 30

    # Auto-timeout escalation (minutes)
    DEFAULT_AUTO_TIMEOUT_FIRST = 5
    DEFAULT_AUTO_TIMEOUT_SECOND = 60
    DEFAULT_AUTO_TIMEOUT_THIRD = 1440  # 24 hours

    # Reputation impact per action
    REPUTATION_IMPACT = {
        'warn': -25.0,
        'timeout': -50.0,
        'kick': -75.0,
        'ban': -200.0
    }

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
                "WHERE platform = 'security_core' "
                "AND integration_type = 'bot' "
                "AND is_active = TRUE "
                "LIMIT 1"
            )
            if rows and rows[0]:
                with cls._credential_lock:
                    cls._credentials_loaded = True
                logger.info(
                    "Credentials loaded from platform_integrations for security_core"
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

        channel = "credentials:security_core:bot:refreshed"

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
