"""
Configuration for Browser Source Core Module
"""

import os

class Config:
    """Configuration class for Browser Source module"""
    
    # Module Info
    MODULE_NAME = os.getenv('MODULE_NAME', 'browser_source_core')
    MODULE_VERSION = os.getenv('MODULE_VERSION', '1.0.0')
    MODULE_PORT = int(os.getenv('MODULE_PORT', '8027'))
    
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:memory')
    
    # WebSocket Configuration
    WEBSOCKET_HOST = os.getenv('WEBSOCKET_HOST', '0.0.0.0')
    WEBSOCKET_PORT = int(os.getenv('WEBSOCKET_PORT', '8028'))
    MAX_CONNECTIONS = int(os.getenv('MAX_CONNECTIONS', '1000'))
    
    # Router Integration
    ROUTER_API_URL = os.getenv('ROUTER_API_URL', 'http://router:8000/router')
    API_KEY = os.getenv('API_KEY', '')  # For router authentication
    
    # Performance Settings
    MAX_WORKERS = int(os.getenv('MAX_WORKERS', '50'))
    QUEUE_PROCESSING_INTERVAL = int(os.getenv('QUEUE_PROCESSING_INTERVAL', '1'))  # seconds
    CLEANUP_INTERVAL = int(os.getenv('CLEANUP_INTERVAL', '300'))  # 5 minutes
    TICKER_QUEUE_SIZE = int(os.getenv('TICKER_QUEUE_SIZE', '100'))
    
    # Browser Source Settings
    BASE_URL = os.getenv('BASE_URL', 'http://localhost:8027')
    TOKEN_LENGTH = int(os.getenv('TOKEN_LENGTH', '32'))
    ACCESS_LOG_RETENTION_DAYS = int(os.getenv('ACCESS_LOG_RETENTION_DAYS', '30'))
    
    # Display Settings
    DEFAULT_TICKER_DURATION = int(os.getenv('DEFAULT_TICKER_DURATION', '10'))  # seconds
    DEFAULT_MEDIA_DURATION = int(os.getenv('DEFAULT_MEDIA_DURATION', '30'))  # seconds
    MAX_TICKER_LENGTH = int(os.getenv('MAX_TICKER_LENGTH', '200'))  # characters
    
    # Ticker Settings
    TICKER_SCROLL_SPEED = int(os.getenv('TICKER_SCROLL_SPEED', '50'))  # pixels per second
    TICKER_FONT_SIZE = int(os.getenv('TICKER_FONT_SIZE', '24'))  # pixels
    TICKER_HEIGHT = int(os.getenv('TICKER_HEIGHT', '60'))  # pixels
    
    # Media Settings
    MEDIA_FADE_DURATION = int(os.getenv('MEDIA_FADE_DURATION', '500'))  # milliseconds
    MEDIA_AUTO_HIDE_DELAY = int(os.getenv('MEDIA_AUTO_HIDE_DELAY', '3000'))  # milliseconds
    SHOW_PROGRESS_BAR = os.getenv('SHOW_PROGRESS_BAR', 'true').lower() == 'true'
    
    # General Settings
    GENERAL_TRANSITION_DURATION = int(os.getenv('GENERAL_TRANSITION_DURATION', '300'))  # milliseconds
    ENABLE_ANIMATIONS = os.getenv('ENABLE_ANIMATIONS', 'true').lower() == 'true'
    
    # Theme Settings
    DEFAULT_THEME = os.getenv('DEFAULT_THEME', 'default')
    ENABLE_CUSTOM_CSS = os.getenv('ENABLE_CUSTOM_CSS', 'true').lower() == 'true'
    
    # Security Settings
    ENABLE_CORS = os.getenv('ENABLE_CORS', 'true').lower() == 'true'
    ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', '*').split(',')
    
    # Feature Flags
    ENABLE_TICKER = os.getenv('ENABLE_TICKER', 'true').lower() == 'true'
    ENABLE_MEDIA = os.getenv('ENABLE_MEDIA', 'true').lower() == 'true'
    ENABLE_GENERAL = os.getenv('ENABLE_GENERAL', 'true').lower() == 'true'
    ENABLE_ANALYTICS = os.getenv('ENABLE_ANALYTICS', 'true').lower() == 'true'
    ENABLE_TEMPLATES = os.getenv('ENABLE_TEMPLATES', 'true').lower() == 'true'
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_DIR = os.getenv('LOG_DIR', '/var/log/waddlebotlog')
    ENABLE_SYSLOG = os.getenv('ENABLE_SYSLOG', 'false').lower() == 'true'
    SYSLOG_HOST = os.getenv('SYSLOG_HOST', 'localhost')
    SYSLOG_PORT = int(os.getenv('SYSLOG_PORT', '514'))
    SYSLOG_FACILITY = os.getenv('SYSLOG_FACILITY', 'LOCAL0')
    
    # Rate Limiting
    RATE_LIMIT_CONNECTIONS = int(os.getenv('RATE_LIMIT_CONNECTIONS', '10'))  # per minute per IP
    RATE_LIMIT_MESSAGES = int(os.getenv('RATE_LIMIT_MESSAGES', '100'))  # per minute per connection
    
    # Caching
    CACHE_TTL = int(os.getenv('CACHE_TTL', '300'))  # 5 minutes
    ENABLE_REDIS_CACHE = os.getenv('ENABLE_REDIS_CACHE', 'false').lower() == 'true'
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
    REDIS_DB = int(os.getenv('REDIS_DB', '0'))
    
    # Monitoring
    ENABLE_METRICS = os.getenv('ENABLE_METRICS', 'true').lower() == 'true'
    METRICS_PORT = int(os.getenv('METRICS_PORT', '8029'))
    
    # CSS Framework Settings
    CSS_FRAMEWORK = os.getenv('CSS_FRAMEWORK', 'custom')  # bootstrap, tailwind, custom
    
    # Default Colors (can be overridden per community)
    DEFAULT_BACKGROUND_COLOR = os.getenv('DEFAULT_BACKGROUND_COLOR', 'transparent')
    DEFAULT_TEXT_COLOR = os.getenv('DEFAULT_TEXT_COLOR', '#ffffff')
    DEFAULT_ACCENT_COLOR = os.getenv('DEFAULT_ACCENT_COLOR', '#007bff')
    
    # Audio Settings
    ENABLE_SOUND_EFFECTS = os.getenv('ENABLE_SOUND_EFFECTS', 'false').lower() == 'true'
    DEFAULT_VOLUME = int(os.getenv('DEFAULT_VOLUME', '50'))  # 0-100
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        errors = []
        
        if not cls.DATABASE_URL:
            errors.append("DATABASE_URL is required")
        
        if not cls.ROUTER_API_URL:
            errors.append("ROUTER_API_URL is required")
        
        if not cls.API_KEY:
            errors.append("API_KEY is required")
        
        if not cls.BASE_URL:
            errors.append("BASE_URL is required")
        
        if cls.WEBSOCKET_PORT == cls.MODULE_PORT:
            errors.append("WEBSOCKET_PORT must be different from MODULE_PORT")
        
        if cls.MAX_WORKERS <= 0:
            errors.append("MAX_WORKERS must be greater than 0")
        
        if cls.TOKEN_LENGTH < 16:
            errors.append("TOKEN_LENGTH must be at least 16 characters")
        
        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")
        
        return True
    
    @classmethod
    def get_websocket_url(cls, token: str, source_type: str) -> str:
        """Get WebSocket URL for a browser source"""
        ws_protocol = 'wss' if cls.BASE_URL.startswith('https') else 'ws'
        host = cls.BASE_URL.replace('http://', '').replace('https://', '')
        return f"{ws_protocol}://{host}:{cls.WEBSOCKET_PORT}/ws/{token}/{source_type}"
    
    @classmethod
    def get_browser_source_url(cls, token: str, source_type: str) -> str:
        """Get browser source URL"""
        return f"{cls.BASE_URL}/browser/source/{token}/{source_type}"