"""
Trigger Streaming Service Configuration

Unified configuration for all 3 streaming platforms:
- Twitch (IRC bot + EventSub webhooks)
- YouTube Live (chat polling + PubSubHubbub webhooks)
- Kick (webhook events)
"""
import os
from dataclasses import dataclass


@dataclass
class Config:
    """Unified configuration for trigger-streaming service."""

    # Service Identity
    MODULE_NAME = os.getenv('MODULE_NAME', 'trigger-streaming')
    MODULE_VERSION = os.getenv('MODULE_VERSION', '0.0.1')
    MODULE_PORT = int(os.getenv('MODULE_PORT', '8101'))
    MODULE_HOST = os.getenv('MODULE_HOST', '0.0.0.0')

    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://localhost/waddlebot')
    DB_POOL_SIZE = int(os.getenv('DB_POOL_SIZE', '10'))
    DB_MAX_RETRIES = int(os.getenv('DB_MAX_RETRIES', '5'))
    DB_RETRY_DELAY = int(os.getenv('DB_RETRY_DELAY', '5'))

    # Security
    SERVICE_API_KEY = os.getenv('SERVICE_API_KEY', '')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'development-secret-key')
    JWT_ALGORITHM = os.getenv('JWT_ALGORITHM', 'HS256')

    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

    # Redis (for caching, rate limiting, etc.)
    REDIS_URL = os.getenv('REDIS_URL', '')

    # Router/API endpoints
    ROUTER_URL = os.getenv('ROUTER_URL', 'http://localhost:8000')
    ROUTER_API_URL = os.getenv('ROUTER_API_URL', 'http://router-service:8000')

    # License Server (optional, for feature gating)
    LICENSE_SERVER_URL = os.getenv('LICENSE_SERVER_URL', '')
    RELEASE_MODE = os.getenv('RELEASE_MODE', 'false').lower() == 'true'

    # Hub/API endpoints for cross-service communication
    HUB_API_URL = os.getenv('HUB_API_URL', 'http://hub-api:8003')

    def validate(self):
        """Validate required configuration."""
        if not self.DATABASE_URL:
            raise ValueError("DATABASE_URL environment variable is required")
        if not self.SERVICE_API_KEY:
            raise ValueError("SERVICE_API_KEY environment variable is required")
