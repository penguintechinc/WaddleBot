"""Configuration for youtube_live_module"""
import logging
import os
import threading
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class Config:
    """YouTube Live module configuration from environment variables."""

    MODULE_NAME = 'youtube_live_module'
    MODULE_VERSION = '1.0.0'
    MODULE_PORT = int(os.getenv('MODULE_PORT', '8006'))

    DATABASE_URL = os.getenv(
        'DATABASE_URL',
        'postgresql://waddlebot:password@localhost:5432/waddlebot'
    )
    ROUTER_API_URL = os.getenv(
        'ROUTER_API_URL',
        'http://router-service:8000/api/v1/router'
    )

    # YouTube API Configuration
    YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY', '')
    YOUTUBE_CLIENT_ID = os.getenv('YOUTUBE_CLIENT_ID', '')
    YOUTUBE_CLIENT_SECRET = os.getenv('YOUTUBE_CLIENT_SECRET', '')
    YOUTUBE_API_VERSION = 'v3'

    # Webhook Configuration
    YOUTUBE_WEBHOOK_CALLBACK_URL = os.getenv(
        'YOUTUBE_WEBHOOK_CALLBACK_URL',
        'http://localhost:8006/api/v1/webhook'
    )
    YOUTUBE_PUBSUB_HUB = 'https://pubsubhubbub.appspot.com/subscribe'

    # Chat Polling Configuration
    CHAT_POLL_INTERVAL = int(os.getenv('CHAT_POLL_INTERVAL', '5'))
    CHAT_MAX_RESULTS = int(os.getenv('CHAT_MAX_RESULTS', '200'))

    # OAuth Scopes (read-only for trigger module)
    YOUTUBE_SCOPES = [
        'https://www.googleapis.com/auth/youtube.readonly',
    ]

    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    SECRET_KEY = os.getenv('SECRET_KEY', 'change-me-in-production')

    # Redis Configuration (for credential refresh notifications)
    REDIS_URL: str = os.getenv('REDIS_URL', '')

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
                "SELECT client_id, client_secret, access_token "
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
