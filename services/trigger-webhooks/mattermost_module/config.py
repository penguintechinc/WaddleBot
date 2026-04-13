"""Configuration for mattermost_module"""
import logging
import os
import threading
from typing import Optional
from urllib.parse import quote_plus as _quote_plus

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class Config:
    """Mattermost module configuration from environment variables."""

    MODULE_NAME = 'mattermost_module'
    MODULE_VERSION = '1.0.0'
    MODULE_PORT = int(os.getenv('MODULE_PORT', '8009'))

    # Database - build URL from components
    DATABASE_HOST = os.getenv('DATABASE_HOST', 'infra-postgres')
    DATABASE_PORT = os.getenv('DATABASE_PORT', '5432')
    DATABASE_NAME = os.getenv('DATABASE_NAME', 'waddlebot')
    DATABASE_USER = os.getenv('DATABASE_USER', 'waddlebot')
    DATABASE_PASSWORD = os.getenv('DATABASE_PASSWORD', '')

    CORE_API_URL = os.getenv('CORE_API_URL',
                             'http://router-service:8000')
    ROUTER_API_URL = os.getenv(
        'ROUTER_API_URL',
        'http://router-service:8000/api/v1/router'
    )
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    SECRET_KEY = os.getenv('SECRET_KEY', 'change-me-in-production')

    # Mattermost Bot Configuration
    MATTERMOST_URL = os.getenv('MATTERMOST_URL', '')
    MATTERMOST_BOT_TOKEN = os.getenv('MATTERMOST_BOT_TOKEN', '')
    MATTERMOST_WEBHOOK_SECRET = os.getenv('MATTERMOST_WEBHOOK_SECRET', '')

    # Redis Configuration - build URL from components
    REDIS_HOST = os.getenv('REDIS_HOST', 'infra-redis')
    REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
    REDIS_DB = int(os.getenv('REDIS_DB', '0'))
    REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', '')

    # Credential state management
    _credentials_loaded: bool = False
    _credential_lock: threading.Lock = threading.Lock()

    @classmethod
    def load_credentials_from_db(cls, db_connection) -> bool:
        """Load Mattermost credentials from platform_integrations table.

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
                "WHERE platform = 'mattermost' "
                "AND integration_type = 'bot' "
                "AND is_active = TRUE "
                "LIMIT 1"
            )
            if rows and rows[0]:
                row = rows[0]
                with cls._credential_lock:
                    if row[0]:
                        cls.MATTERMOST_BOT_TOKEN = row[0]
                    if row[1]:  # config_data may contain URL and webhook secret
                        import json
                        try:
                            config = json.loads(row[1])
                            if 'mattermost_url' in config:
                                cls.MATTERMOST_URL = config['mattermost_url']
                            if 'webhook_secret' in config:
                                cls.MATTERMOST_WEBHOOK_SECRET = config['webhook_secret']
                        except (json.JSONDecodeError, ValueError):
                            pass
                    cls._credentials_loaded = True
                logger.info(
                    "Mattermost credentials loaded from platform_integrations"
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

        channel = "credentials:mattermost:bot:refreshed"

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

    @classmethod
    def validate(cls):
        """
        Validate configuration and return errors and warnings separately.

        Returns:
            Tuple of (error_list, warning_list)
        """
        errors = []
        warnings = []

        if not cls.DATABASE_URL:
            errors.append("DATABASE_URL is required")

        # Optional credentials - warn but don't fail startup
        if not cls.MATTERMOST_URL:
            warnings.append("MATTERMOST_URL not configured - Mattermost API calls will fail")

        if not cls.MATTERMOST_BOT_TOKEN:
            warnings.append("MATTERMOST_BOT_TOKEN not configured - Mattermost API calls will fail")

        if not cls.MATTERMOST_WEBHOOK_SECRET:
            warnings.append("MATTERMOST_WEBHOOK_SECRET not configured - webhook verification will be skipped")

        return errors, warnings


# Construct DATABASE_URL from components after class definition
_db_user = Config.DATABASE_USER
_db_password = Config.DATABASE_PASSWORD
_db_host = Config.DATABASE_HOST
_db_port = Config.DATABASE_PORT
_db_name = Config.DATABASE_NAME
if _db_password:
    _encoded_pw = _quote_plus(_db_password)
    Config.DATABASE_URL = f"postgresql://{_db_user}:{_encoded_pw}@{_db_host}:{_db_port}/{_db_name}"
else:
    Config.DATABASE_URL = f"postgresql://{_db_user}@{_db_host}:{_db_port}/{_db_name}"

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
