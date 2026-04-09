"""
Interactive Gaming Service Configuration

Unified configuration for all 4 modules:
- lfg_interaction_module
- inventory_interaction_module
- server_manager_interaction_module
- server_status_interaction_module
"""
import os
from dataclasses import dataclass


@dataclass
class Config:
    """Unified configuration for interactive-gaming service."""

    # Service Identity
    MODULE_NAME = os.getenv('MODULE_NAME', 'interactive-gaming')
    MODULE_VERSION = os.getenv('MODULE_VERSION', '0.0.1')
    MODULE_PORT = int(os.getenv('MODULE_PORT', '8104'))
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

    # Redis (for cache, notifications, etc.)
    REDIS_URL = os.getenv('REDIS_URL', '')

    # Router/API endpoints
    ROUTER_URL = os.getenv('ROUTER_URL', 'http://localhost:8000')
    CORE_API_URL = os.getenv('CORE_API_URL', 'http://router-service:8000')
    ROUTER_API_URL = os.getenv('ROUTER_API_URL', 'http://router-service:8000/api/v1/router')

    # Legacy compatibility - alternative to JWT_SECRET_KEY
    SECRET_KEY = os.getenv('SECRET_KEY', 'change-me-in-production')

    # License Server (optional, for feature gating)
    LICENSE_SERVER_URL = os.getenv('LICENSE_SERVER_URL', '')
    RELEASE_MODE = os.getenv('RELEASE_MODE', 'false').lower() == 'true'

    # LFG-specific settings
    LFG_DEFAULT_EXPIRY_MINUTES = int(os.getenv('LFG_DEFAULT_EXPIRY_MINUTES', '120'))
    LFG_MAX_ACTIVE_POSTS_PER_USER = int(os.getenv('LFG_MAX_ACTIVE_POSTS_PER_USER', '3'))

    # Server Manager & Server Status polling settings
    DEFAULT_POLL_INTERVAL_MINUTES = int(os.getenv('DEFAULT_POLL_INTERVAL_MINUTES', '5'))
    STATUS_CHECK_TIMEOUT = int(os.getenv('STATUS_CHECK_TIMEOUT', '10'))

    # Server Manager RCON settings
    RCON_ENCRYPTION_KEY = os.getenv('RCON_ENCRYPTION_KEY', '')
    RCON_CONNECTION_TTL = int(os.getenv('RCON_CONNECTION_TTL', '60'))

    # Security service endpoint
    SECURITY_CORE_URL = os.getenv('SECURITY_CORE_URL', 'http://security-core-service:8010')

    def validate(self):
        """Validate required configuration."""
        if not self.DATABASE_URL:
            raise ValueError("DATABASE_URL environment variable is required")
        if not self.SERVICE_API_KEY:
            raise ValueError("SERVICE_API_KEY environment variable is required")
