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

    DATABASE_URL: str = os.getenv(
        'DATABASE_URL',
        'postgresql://waddlebot:password@localhost:5432/waddlebot',
    )
    REDIS_URL: str = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    ROUTER_API_URL: str = os.getenv(
        'ROUTER_API_URL',
        'http://router-service:8000/api/v1/router',
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
