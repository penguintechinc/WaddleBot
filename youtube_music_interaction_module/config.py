"""
Configuration for YouTube Music Interaction Module
"""

import os

class Config:
    """Configuration class for YouTube Music module"""
    
    # Module Info
    MODULE_NAME = os.getenv('MODULE_NAME', 'youtube_music_interaction')
    MODULE_VERSION = os.getenv('MODULE_VERSION', '1.0.0')
    MODULE_PORT = int(os.getenv('MODULE_PORT', '8025'))
    
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:memory')
    
    # YouTube API Configuration
    YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY', '')
    YOUTUBE_API_VERSION = os.getenv('YOUTUBE_API_VERSION', 'v3')
    YOUTUBE_SEARCH_PARTS = os.getenv('YOUTUBE_SEARCH_PARTS', 'snippet')
    YOUTUBE_MAX_RESULTS = int(os.getenv('YOUTUBE_MAX_RESULTS', '10'))
    
    # YouTube Music specific
    YOUTUBE_MUSIC_CATEGORY_ID = os.getenv('YOUTUBE_MUSIC_CATEGORY_ID', '10')  # Music category
    YOUTUBE_REGION_CODE = os.getenv('YOUTUBE_REGION_CODE', 'US')
    
    # YouTube Data API v3 endpoints
    YOUTUBE_API_BASE_URL = os.getenv('YOUTUBE_API_BASE_URL', 'https://www.googleapis.com/youtube/v3')
    
    # Router Integration
    ROUTER_API_URL = os.getenv('ROUTER_API_URL', 'http://router:8000/router')
    API_KEY = os.getenv('API_KEY', '')  # For router authentication
    
    # Browser Source Integration
    BROWSER_SOURCE_API_URL = os.getenv('BROWSER_SOURCE_API_URL', 'http://browser-source:8027/browser/source')
    
    # Performance Settings
    MAX_SEARCH_RESULTS = int(os.getenv('MAX_SEARCH_RESULTS', '10'))
    CACHE_TTL = int(os.getenv('CACHE_TTL', '300'))  # 5 minutes
    REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '30'))
    MAX_QUEUE_SIZE = int(os.getenv('MAX_QUEUE_SIZE', '50'))
    MAX_PLAYLIST_SIZE = int(os.getenv('MAX_PLAYLIST_SIZE', '100'))
    
    # Feature Flags
    ENABLE_PLAYLISTS = os.getenv('ENABLE_PLAYLISTS', 'true').lower() == 'true'
    ENABLE_QUEUE = os.getenv('ENABLE_QUEUE', 'true').lower() == 'true'
    ENABLE_HISTORY = os.getenv('ENABLE_HISTORY', 'true').lower() == 'true'
    ENABLE_AUTOPLAY = os.getenv('ENABLE_AUTOPLAY', 'true').lower() == 'true'
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_DIR = os.getenv('LOG_DIR', '/var/log/waddlebotlog')
    ENABLE_SYSLOG = os.getenv('ENABLE_SYSLOG', 'false').lower() == 'true'
    SYSLOG_HOST = os.getenv('SYSLOG_HOST', 'localhost')
    SYSLOG_PORT = int(os.getenv('SYSLOG_PORT', '514'))
    SYSLOG_FACILITY = os.getenv('SYSLOG_FACILITY', 'LOCAL0')
    
    # Rate Limiting
    RATE_LIMIT_SEARCHES = int(os.getenv('RATE_LIMIT_SEARCHES', '30'))  # per minute
    RATE_LIMIT_PLAYS = int(os.getenv('RATE_LIMIT_PLAYS', '20'))  # per minute
    
    # Default Messages
    DEFAULT_HELP_MESSAGE = os.getenv('DEFAULT_HELP_MESSAGE', 
        "YouTube Music commands: !ytmusic search <query>, !ytmusic play <url/number>, "
        "!ytmusic current, !ytmusic queue, !ytmusic skip, !ytmusic stop")
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        errors = []
        
        if not cls.DATABASE_URL:
            errors.append("DATABASE_URL is required")
        
        if not cls.YOUTUBE_API_KEY:
            errors.append("YOUTUBE_API_KEY is required")
        
        if not cls.ROUTER_API_URL:
            errors.append("ROUTER_API_URL is required")
        
        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")
        
        return True