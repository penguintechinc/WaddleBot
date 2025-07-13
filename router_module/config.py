"""
Configuration for the Router module
"""

import os
from dataclasses import dataclass
from typing import List, Dict, Optional

@dataclass
class RouterConfig:
    """Router configuration"""
    # Database settings
    primary_db_url: str
    read_replica_url: str
    
    # Performance settings
    max_workers: int = 20  # Thread pool size
    max_concurrent_requests: int = 100  # Max concurrent Lambda calls
    request_timeout: int = 30  # Default timeout for Lambda calls
    
    # Rate limiting
    default_rate_limit: int = 60  # Default requests per minute
    rate_limit_window: int = 60   # Rate limit window in seconds
    
    # Caching
    command_cache_ttl: int = 300  # Command cache TTL in seconds
    entity_cache_ttl: int = 600   # Entity cache TTL in seconds
    
    # Retry settings
    max_retries: int = 3
    retry_delay: float = 1.0  # Initial retry delay in seconds
    retry_backoff: float = 2.0  # Backoff multiplier
    
    # Monitoring
    metrics_enabled: bool = True
    stats_retention_days: int = 30

@dataclass
class LambdaConfig:
    """AWS Lambda configuration"""
    aws_region: str
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    lambda_function_prefix: str = "waddlebot-"
    
@dataclass
class OpenWhiskConfig:
    """OpenWhisk configuration"""
    api_host: str
    auth_key: str
    namespace: str = "guest"
    
@dataclass
class WaddleBotConfig:
    """WaddleBot integration configuration"""
    core_api_url: str
    marketplace_api_url: str
    context_api_url: str
    reputation_api_url: str

# Load configuration from environment variables
def load_config() -> tuple[RouterConfig, LambdaConfig, OpenWhiskConfig, WaddleBotConfig]:
    """Load configuration from environment variables"""
    
    # Required environment variables
    required_vars = [
        "DATABASE_URL",
        "CORE_API_URL",
        "MARKETPLACE_API_URL"
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    router_config = RouterConfig(
        primary_db_url=os.getenv("DATABASE_URL"),
        read_replica_url=os.getenv("READ_REPLICA_URL", os.getenv("DATABASE_URL")),
        max_workers=int(os.getenv("ROUTER_MAX_WORKERS", "20")),
        max_concurrent_requests=int(os.getenv("ROUTER_MAX_CONCURRENT", "100")),
        request_timeout=int(os.getenv("ROUTER_REQUEST_TIMEOUT", "30")),
        default_rate_limit=int(os.getenv("ROUTER_DEFAULT_RATE_LIMIT", "60")),
        rate_limit_window=int(os.getenv("ROUTER_RATE_LIMIT_WINDOW", "60")),
        command_cache_ttl=int(os.getenv("ROUTER_COMMAND_CACHE_TTL", "300")),
        entity_cache_ttl=int(os.getenv("ROUTER_ENTITY_CACHE_TTL", "600")),
        max_retries=int(os.getenv("ROUTER_MAX_RETRIES", "3")),
        retry_delay=float(os.getenv("ROUTER_RETRY_DELAY", "1.0")),
        retry_backoff=float(os.getenv("ROUTER_RETRY_BACKOFF", "2.0")),
        metrics_enabled=os.getenv("ROUTER_METRICS_ENABLED", "true").lower() == "true",
        stats_retention_days=int(os.getenv("ROUTER_STATS_RETENTION_DAYS", "30"))
    )
    
    lambda_config = LambdaConfig(
        aws_region=os.getenv("AWS_REGION", "us-east-1"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        lambda_function_prefix=os.getenv("LAMBDA_FUNCTION_PREFIX", "waddlebot-")
    )
    
    openwhisk_config = OpenWhiskConfig(
        api_host=os.getenv("OPENWHISK_API_HOST", ""),
        auth_key=os.getenv("OPENWHISK_AUTH_KEY", ""),
        namespace=os.getenv("OPENWHISK_NAMESPACE", "guest")
    )
    
    waddlebot_config = WaddleBotConfig(
        core_api_url=os.getenv("CORE_API_URL"),
        marketplace_api_url=os.getenv("MARKETPLACE_API_URL"),
        context_api_url=os.getenv("CONTEXT_API_URL", f"{os.getenv('CORE_API_URL')}/api/context"),
        reputation_api_url=os.getenv("REPUTATION_API_URL", f"{os.getenv('CORE_API_URL')}/api/reputation")
    )
    
    return router_config, lambda_config, openwhisk_config, waddlebot_config

# Command prefix definitions
COMMAND_PREFIXES = {
    "!": "local",       # Local container interaction modules
    "#": "community"    # Community marketplace modules (Lambda/OpenWhisk)
}

# Supported execution platforms
EXECUTION_PLATFORMS = [
    "container",    # Local container modules (! prefix)
    "lambda",       # AWS Lambda (# prefix)
    "openwhisk",    # OpenWhisk (# prefix) 
    "webhook",      # Generic webhook (# prefix)
]

# Default command configuration
DEFAULT_COMMAND_CONFIG = {
    "timeout": 30,
    "retries": 3,
    "rate_limit": 60,
    "auth_required": False
}

# Router metrics
ROUTER_METRICS = [
    "commands_processed_total",
    "commands_successful_total", 
    "commands_failed_total",
    "command_execution_duration_seconds",
    "rate_limits_hit_total",
    "cache_hits_total",
    "cache_misses_total",
    "concurrent_requests_gauge",
    "database_query_duration_seconds"
]