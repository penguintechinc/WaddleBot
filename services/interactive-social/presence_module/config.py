"""Configuration for presence_module"""
import logging
import os

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class Config:
    MODULE_NAME = 'presence_module'
    MODULE_VERSION = '1.0.0'
    MODULE_PORT = int(os.getenv('MODULE_PORT', '8042'))

    # Database configuration - build URL from components
    DATABASE_HOST = os.getenv('DATABASE_HOST', 'infra-postgres')
    DATABASE_PORT = os.getenv('DATABASE_PORT', '5432')
    DATABASE_NAME = os.getenv('DATABASE_NAME', 'waddlebot')
    DATABASE_USER = os.getenv('DATABASE_USER', 'waddlebot')
    DATABASE_PASSWORD = os.getenv('DATABASE_PASSWORD', '')

    # Redis configuration - build URL from components
    REDIS_HOST = os.getenv('REDIS_HOST', 'infra-redis')
    REDIS_PORT = os.getenv('REDIS_PORT', '6379')
    REDIS_DB = os.getenv('REDIS_DB', '0')

    ROUTER_API_URL: str = os.getenv(
        'ROUTER_API_URL',
        'http://core-router:8000/api/v1/router',
    )
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')

    @classmethod
    def validate(cls) -> None:
        """Validate that required configuration values are present.

        Raises:
            EnvironmentError: If any required environment variable is missing
                or obviously invalid.
        """
        errors = []

        if not cls.DATABASE_URL:
            errors.append("DATABASE_URL must be set")

        if not cls.REDIS_URL:
            errors.append("REDIS_URL must be set")

        if not cls.ROUTER_API_URL:
            errors.append("ROUTER_API_URL must be set")

        if cls.MODULE_PORT < 1 or cls.MODULE_PORT > 65535:
            errors.append(
                f"MODULE_PORT must be a valid port number (got {cls.MODULE_PORT})"
            )

        if errors:
            msg = "Configuration validation failed:\n" + "\n".join(
                f"  - {e}" for e in errors
            )
            logger.error(msg)
            raise EnvironmentError(msg)

        logger.info(
            "Config validated: module=%s version=%s port=%d",
            cls.MODULE_NAME,
            cls.MODULE_VERSION,
            cls.MODULE_PORT,
        )


# Construct DATABASE_URL and REDIS_URL from components
from urllib.parse import quote_plus as _quote_plus
_db_password = Config.DATABASE_PASSWORD
if _db_password:
    _encoded_pw = _quote_plus(_db_password)
    Config.DATABASE_URL = f"postgresql://{Config.DATABASE_USER}:{_encoded_pw}@{Config.DATABASE_HOST}:{Config.DATABASE_PORT}/{Config.DATABASE_NAME}"
else:
    Config.DATABASE_URL = f"postgresql://{Config.DATABASE_USER}@{Config.DATABASE_HOST}:{Config.DATABASE_PORT}/{Config.DATABASE_NAME}"

Config.REDIS_URL = f"redis://{Config.REDIS_HOST}:{Config.REDIS_PORT}/{Config.REDIS_DB}"
