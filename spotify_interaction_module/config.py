"""
Configuration for Spotify Interaction Module
"""

import os

class Config:
    """Configuration class for Spotify module"""
    
    # Module Info
    MODULE_NAME = os.getenv('MODULE_NAME', 'spotify_interaction')
    MODULE_VERSION = os.getenv('MODULE_VERSION', '1.0.0')
    MODULE_PORT = int(os.getenv('MODULE_PORT', '8026'))
    
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:memory')
    
    # Spotify API Configuration
    SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID', '')
    SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET', '')
    SPOTIFY_REDIRECT_URI = os.getenv('SPOTIFY_REDIRECT_URI', 'http://localhost:8026/spotify/auth/callback')
    
    # Spotify API endpoints
    SPOTIFY_API_BASE_URL = os.getenv('SPOTIFY_API_BASE_URL', 'https://api.spotify.com/v1')
    SPOTIFY_ACCOUNTS_BASE_URL = os.getenv('SPOTIFY_ACCOUNTS_BASE_URL', 'https://accounts.spotify.com')
    
    # OAuth scopes
    SPOTIFY_SCOPES = os.getenv('SPOTIFY_SCOPES', 
        'user-read-playback-state user-modify-playback-state user-read-currently-playing '
        'streaming user-read-email user-read-private playlist-read-private playlist-modify-public '
        'playlist-modify-private user-library-read user-library-modify')
    
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
    TOKEN_REFRESH_BUFFER = int(os.getenv('TOKEN_REFRESH_BUFFER', '300'))  # 5 minutes before expiry
    
    # Feature Flags
    ENABLE_PLAYLISTS = os.getenv('ENABLE_PLAYLISTS', 'true').lower() == 'true'
    ENABLE_QUEUE = os.getenv('ENABLE_QUEUE', 'true').lower() == 'true'
    ENABLE_HISTORY = os.getenv('ENABLE_HISTORY', 'true').lower() == 'true'
    ENABLE_DEVICE_CONTROL = os.getenv('ENABLE_DEVICE_CONTROL', 'true').lower() == 'true'
    
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
    RATE_LIMIT_SKIPS = int(os.getenv('RATE_LIMIT_SKIPS', '10'))  # per minute
    
    # Default Messages
    DEFAULT_HELP_MESSAGE = os.getenv('DEFAULT_HELP_MESSAGE', 
        "Spotify commands: !spotify search <query>, !spotify play <uri/number>, "
        "!spotify current, !spotify pause, !spotify resume, !spotify skip, !spotify devices")
    
    # Media Browser Source Settings
    MEDIA_DISPLAY_DURATION = int(os.getenv('MEDIA_DISPLAY_DURATION', '30'))  # seconds
    SHOW_ALBUM_ART = os.getenv('SHOW_ALBUM_ART', 'true').lower() == 'true'
    SHOW_PROGRESS_BAR = os.getenv('SHOW_PROGRESS_BAR', 'true').lower() == 'true'
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        errors = []
        
        if not cls.DATABASE_URL:
            errors.append("DATABASE_URL is required")
        
        if not cls.SPOTIFY_CLIENT_ID:
            errors.append("SPOTIFY_CLIENT_ID is required")
        
        if not cls.SPOTIFY_CLIENT_SECRET:
            errors.append("SPOTIFY_CLIENT_SECRET is required")
        
        if not cls.ROUTER_API_URL:
            errors.append("ROUTER_API_URL is required")
        
        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")
        
        return True