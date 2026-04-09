"""
Core Community Service Configuration

Unified configuration for all 4 modules:
- community_module
- workflow_core_module
- browser_source_core_module
- video_proxy_module
"""
import os


class Config:
    """Unified configuration for core-community service."""

    # Service Identity
    MODULE_NAME = os.getenv('MODULE_NAME', 'core-community')
    MODULE_VERSION = os.getenv('MODULE_VERSION', '0.0.1')
    MODULE_PORT = int(os.getenv('MODULE_PORT', '8020'))
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

    # Redis (for credential refresh notifications, cache, etc.)
    REDIS_URL = os.getenv('REDIS_URL', '')

    # Router/API endpoints
    ROUTER_URL = os.getenv('ROUTER_URL', 'http://localhost:8000')
    CORE_API_URL = os.getenv('CORE_API_URL', 'http://router-service:8000')

    # License Server (optional, for feature gating)
    LICENSE_SERVER_URL = os.getenv('LICENSE_SERVER_URL', '')
    RELEASE_MODE = os.getenv('RELEASE_MODE', 'false').lower() == 'true'

    # Workflow Engine configuration
    MAX_LOOP_ITERATIONS = int(os.getenv('MAX_LOOP_ITERATIONS', '100'))
    MAX_TOTAL_OPERATIONS = int(os.getenv('MAX_TOTAL_OPERATIONS', '1000'))
    MAX_LOOP_DEPTH = int(os.getenv('MAX_LOOP_DEPTH', '10'))
    WORKFLOW_TIMEOUT = int(os.getenv('WORKFLOW_TIMEOUT', '300'))
    MAX_PARALLEL_NODES = int(os.getenv('MAX_PARALLEL_NODES', '50'))

    # Workflow feature flags
    FEATURE_WORKFLOWS_ENABLED = os.getenv('FEATURE_WORKFLOWS_ENABLED', 'true').lower() == 'true'

    # Video Proxy configuration
    FREE_MAX_DESTINATIONS = int(os.getenv('FREE_MAX_DESTINATIONS', '3'))

    def validate(self):
        """Validate required configuration."""
        if not self.DATABASE_URL:
            raise ValueError("DATABASE_URL environment variable is required")
        if not self.SERVICE_API_KEY:
            raise ValueError("SERVICE_API_KEY environment variable is required")
