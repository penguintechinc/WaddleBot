"""Configuration for shoutout_interaction_module"""
import logging
import os
import threading
from typing import Optional

from dotenv import load_dotenv
from flask_core.secrets import require_secret_key

load_dotenv()

logger = logging.getLogger(__name__)


class Config:
    MODULE_NAME = 'shoutout_interaction_module'
    MODULE_VERSION = '2.0.0'
    MODULE_PORT = int(os.getenv('MODULE_PORT', '8011'))
    DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://waddlebot:password@localhost:5432/waddlebot')
    CORE_API_URL = os.getenv('CORE_API_URL', 'http://router-service:8000')
    ROUTER_API_URL = os.getenv('ROUTER_API_URL', 'http://router-service:8000/api/v1/router')
    IDENTITY_URL = os.getenv('IDENTITY_URL', 'http://identity-core:8050')
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    SECRET_KEY = require_secret_key()
    # Twitch API credentials
    TWITCH_CLIENT_ID = os.getenv('TWITCH_CLIENT_ID', '')
    TWITCH_CLIENT_SECRET = os.getenv('TWITCH_CLIENT_SECRET', '')

    # YouTube API credentials
    YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY', '')

    # Video shoutout settings
    VIDEO_SHOUTOUT_DEFAULT_DURATION = int(os.getenv('VIDEO_SHOUTOUT_DEFAULT_DURATION', '30'))
    VIDEO_SHOUTOUT_DEFAULT_COOLDOWN = int(os.getenv('VIDEO_SHOUTOUT_DEFAULT_COOLDOWN', '60'))

    # Redis Configuration (for credential refresh notifications)
    REDIS_URL: str = os.getenv('REDIS_URL', '')

    # Credential state management
    _credentials_loaded: bool = False
    _credential_lock: threading.Lock = threading.Lock()

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
                "SELECT client_id, client_secret, access_token "
                "FROM platform_integrations "
                "WHERE platform IN ('twitch', 'youtube') "
                "AND integration_type = 'bot' "
                "AND is_active = TRUE"
            )
            if rows:
                with cls._credential_lock:
                    for row in rows:
                        if row[0] and row[1]:  # client_id and client_secret (Twitch)
                            cls.TWITCH_CLIENT_ID = row[0]
                            cls.TWITCH_CLIENT_SECRET = row[1]
                        if row[2]:  # access_token (YouTube API key)
                            cls.YOUTUBE_API_KEY = row[2]
                    cls._credentials_loaded = True
                logger.info(
                    "Shoutout module credentials loaded from platform_integrations"
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
                pubsub.subscribe('credentials:twitch:bot:refreshed', 'credentials:youtube:bot:refreshed')
                logger.info(
                    "Listening for credential refresh on: twitch and youtube channels"
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
