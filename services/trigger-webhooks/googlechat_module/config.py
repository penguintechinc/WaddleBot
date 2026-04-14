"""Configuration for googlechat_module"""
import json
import logging
import os
import threading
from typing import Optional
from urllib.parse import quote_plus as _quote_plus

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class Config:
    """Google Chat module configuration from environment variables."""

    MODULE_NAME = 'googlechat_module'
    MODULE_VERSION = '1.0.0'
    MODULE_PORT = int(os.getenv('MODULE_PORT', '8012'))

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

    # Google Chat Bot Configuration
    GOOGLE_CHAT_SERVICE_ACCOUNT_KEY = os.getenv('GOOGLE_CHAT_SERVICE_ACCOUNT_KEY', '')
    GOOGLE_CHAT_PROJECT_ID = os.getenv('GOOGLE_CHAT_PROJECT_ID', '')

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
                    if row[1]:  # config_data contains service account key
                        try:
                            config = json.loads(row[1])
                            if 'service_account_key' in config:
                                cls.GOOGLE_CHAT_SERVICE_ACCOUNT_KEY = json.dumps(config['service_account_key'])
                            if 'project_id' in config:
                                cls.GOOGLE_CHAT_PROJECT_ID = config['project_id']
                        except (json.JSONDecodeError, ValueError):
                            pass
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

        channel = "credentials:googlechat:bot:refreshed"

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
        if not cls.GOOGLE_CHAT_SERVICE_ACCOUNT_KEY:
            warnings.append("GOOGLE_CHAT_SERVICE_ACCOUNT_KEY not configured - Google Chat API calls will fail")

        if not cls.GOOGLE_CHAT_PROJECT_ID:
            warnings.append("GOOGLE_CHAT_PROJECT_ID not configured - Google Chat API calls will fail")

        return errors, warnings


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
