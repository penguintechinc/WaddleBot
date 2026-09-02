import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class Config:
    """Configuration for Mattermost Action Module."""

    # Module identification
    MODULE_NAME = os.getenv('MODULE_NAME', 'mattermost_action_module')
    MODULE_VERSION = os.getenv('MODULE_VERSION', '1.0.0')

    # Mattermost configuration
    MATTERMOST_URL = os.getenv('MATTERMOST_URL', 'https://mattermost.example.com')
    MATTERMOST_BOT_TOKEN = os.getenv('MATTERMOST_BOT_TOKEN', '')

    # Database configuration
    DATABASE_URL = os.getenv(
        'DATABASE_URL',
        'postgres://user:password@localhost:5432/mattermost_action_db'
    )

    # Server configuration
    REST_PORT = int(os.getenv('REST_PORT', '8075'))
    GRPC_PORT = int(os.getenv('GRPC_PORT', '50058'))

    # JWT/Auth configuration
    JWT_SECRET = os.getenv('JWT_SECRET', 'your-secret-key-change-in-production')
    JWT_ALGORITHM = os.getenv('JWT_ALGORITHM', 'HS256')
    # Service identities permitted to call this module's gRPC servicer.
    ALLOWED_SERVICES = os.getenv('ALLOWED_SERVICES', 'router_module').split(',')

    # Logging configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

    # Timeout configuration (in seconds)
    MATTERMOST_REQUEST_TIMEOUT = int(os.getenv('MATTERMOST_REQUEST_TIMEOUT', '30'))

    @classmethod
    def validate(cls) -> bool:
        """Validate critical configuration values."""
        if not cls.MATTERMOST_URL or cls.MATTERMOST_URL == 'https://mattermost.example.com':
            logger.error('MATTERMOST_URL is not configured')
            return False

        if not cls.MATTERMOST_BOT_TOKEN:
            logger.error('MATTERMOST_BOT_TOKEN is not set')
            return False

        if not cls.DATABASE_URL or cls.DATABASE_URL == 'postgres://user:password@localhost:5432/mattermost_action_db':
            logger.error('DATABASE_URL is not properly configured')
            return False

        if cls.JWT_SECRET == 'your-secret-key-change-in-production':
            logger.warning('JWT_SECRET is set to default value - change this in production!')

        return True

    @classmethod
    def get_info(cls) -> Dict[str, Any]:
        """Return configuration info for debugging/logging."""
        return {
            'module_name': cls.MODULE_NAME,
            'module_version': cls.MODULE_VERSION,
            'mattermost_url': cls.MATTERMOST_URL,
            'rest_port': cls.REST_PORT,
            'grpc_port': cls.GRPC_PORT,
            'log_level': cls.LOG_LEVEL,
            'database_configured': bool(cls.DATABASE_URL),
            'bot_token_configured': bool(cls.MATTERMOST_BOT_TOKEN),
            'jwt_secret_configured': bool(cls.JWT_SECRET != 'your-secret-key-change-in-production'),
        }
