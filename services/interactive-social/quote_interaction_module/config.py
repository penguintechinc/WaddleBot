"""
Configuration for Quote Interaction Module
"""
import logging
import os
import threading
from typing import Optional

logger = logging.getLogger(__name__)


class Config:
    """Quote module configuration"""

    # Module metadata
    MODULE_NAME = os.getenv('QUOTE_MODULE_NAME', 'quote_interaction_module')
    MODULE_VERSION = os.getenv('QUOTE_MODULE_VERSION', '1.0.0')
    MODULE_PORT = int(os.getenv('QUOTE_MODULE_PORT', 5012))

    # Database configuration
    DATABASE_URL = os.getenv(
        'DATABASE_URL',
        'postgresql://waddlebot:waddlebot@localhost:5432/waddlebot'
    )

    # Optional read replica for queries
    READ_REPLICA_URL = os.getenv('READ_REPLICA_URL')

    # Redis Configuration (for credential refresh notifications)
    REDIS_URL: str = os.getenv('REDIS_URL', '')

    # Credential state management
    _credentials_loaded: bool = False
    _credential_lock: threading.Lock = threading.Lock()

    # Connection pool settings
    DB_POOL_SIZE = int(os.getenv('DB_POOL_SIZE', 10))

    # API settings
    API_TIMEOUT = int(os.getenv('API_TIMEOUT', 30))
    MAX_PAGE_SIZE = int(os.getenv('MAX_PAGE_SIZE', 100))
    DEFAULT_PAGE_SIZE = int(os.getenv('DEFAULT_PAGE_SIZE', 50))

    # Full-text search settings
    SEARCH_LANGUAGE = 'english'
    MIN_SEARCH_QUERY_LENGTH = 2

    # Quote moderation
    AUTO_APPROVE_QUOTES = os.getenv('AUTO_APPROVE_QUOTES', 'true').lower() == 'true'

    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

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
                "WHERE platform = 'quote_interaction' "
                "AND integration_type = 'bot' "
                "AND is_active = TRUE "
                "LIMIT 1"
            )
            if rows and rows[0]:
                with cls._credential_lock:
                    cls._credentials_loaded = True
                logger.info(
                    "Credentials loaded from platform_integrations for quote_interaction"
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

        channel = "credentials:quote_interaction:bot:refreshed"

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
