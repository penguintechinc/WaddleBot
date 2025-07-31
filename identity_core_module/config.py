"""
Configuration for WaddleBot Identity Core Module
"""

import os

class Config:
    # Module Info
    MODULE_NAME = os.environ.get('MODULE_NAME', 'identity_core_module')
    MODULE_VERSION = os.environ.get('MODULE_VERSION', '1.0.0')
    MODULE_PORT = int(os.environ.get('MODULE_PORT', '8050'))
    
    # Database
    DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://user:pass@localhost:5432/waddlebot')
    
    # Redis Configuration
    REDIS_HOST = os.environ.get('REDIS_HOST', 'redis')
    REDIS_PORT = int(os.environ.get('REDIS_PORT', '6379'))
    REDIS_DB = int(os.environ.get('REDIS_DB', '0'))
    REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD', '')
    
    # Session and Security
    SECRET_KEY = os.environ.get('SECRET_KEY', 'waddlebot_identity_secret_key_change_me_in_production')
    SESSION_TTL = int(os.environ.get('SESSION_TTL', '3600'))
    
    # API Keys
    VALID_API_KEYS = set(filter(None, os.environ.get('VALID_API_KEYS', '').split(',')))
    MAX_API_KEYS_PER_USER = int(os.environ.get('MAX_API_KEYS_PER_USER', '5'))
    API_KEY_DEFAULT_EXPIRY_DAYS = int(os.environ.get('API_KEY_DEFAULT_EXPIRY_DAYS', '365'))
    
    # Core API Integration
    CORE_API_URL = os.environ.get('CORE_API_URL', 'http://router-service:8000')
    ROUTER_API_URL = os.environ.get('ROUTER_API_URL', 'http://router-service:8000/router')
    
    # Platform APIs (for whisper/DM functionality)
    TWITCH_API_URL = os.environ.get('TWITCH_API_URL', 'http://twitch-collector:8002')
    DISCORD_API_URL = os.environ.get('DISCORD_API_URL', 'http://discord-collector:8003')
    SLACK_API_URL = os.environ.get('SLACK_API_URL', 'http://slack-collector:8004')
    
    # Verification Settings
    VERIFICATION_CODE_LENGTH = int(os.environ.get('VERIFICATION_CODE_LENGTH', '6'))
    VERIFICATION_TIMEOUT_MINUTES = int(os.environ.get('VERIFICATION_TIMEOUT_MINUTES', '10'))
    RESEND_COOLDOWN_SECONDS = int(os.environ.get('RESEND_COOLDOWN_SECONDS', '60'))
    MAX_VERIFICATION_ATTEMPTS = int(os.environ.get('MAX_VERIFICATION_ATTEMPTS', '5'))
    
    # Email Configuration (for py4web mailer)
    SMTP_HOST = os.environ.get('SMTP_HOST', 'smtp.company.com')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
    SMTP_USERNAME = os.environ.get('SMTP_USERNAME', 'identity@company.com')
    SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
    SMTP_TLS = os.environ.get('SMTP_TLS', 'true').lower() == 'true'
    FROM_EMAIL = os.environ.get('FROM_EMAIL', 'noreply@waddlebot.com')
    
    # Performance Settings
    MAX_WORKERS = int(os.environ.get('MAX_WORKERS', '20'))
    CACHE_TTL = int(os.environ.get('CACHE_TTL', '300'))
    REQUEST_TIMEOUT = int(os.environ.get('REQUEST_TIMEOUT', '30'))
    BULK_OPERATION_SIZE = int(os.environ.get('BULK_OPERATION_SIZE', '100'))
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS = int(os.environ.get('RATE_LIMIT_REQUESTS', '60'))
    RATE_LIMIT_WINDOW = int(os.environ.get('RATE_LIMIT_WINDOW', '60'))
    
    # Platform Whisper/DM Settings
    WHISPER_RETRY_ATTEMPTS = int(os.environ.get('WHISPER_RETRY_ATTEMPTS', '3'))
    WHISPER_RETRY_DELAY = int(os.environ.get('WHISPER_RETRY_DELAY', '5'))
    
    # Logging Configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_DIR = os.environ.get('LOG_DIR', '/var/log/waddlebotlog')
    ENABLE_SYSLOG = os.environ.get('ENABLE_SYSLOG', 'false').lower() == 'true'
    SYSLOG_HOST = os.environ.get('SYSLOG_HOST', 'localhost')
    SYSLOG_PORT = int(os.environ.get('SYSLOG_PORT', '514'))
    SYSLOG_FACILITY = os.environ.get('SYSLOG_FACILITY', 'LOCAL0')
    
    # Feature Flags
    ENABLE_EMAIL_VERIFICATION = os.environ.get('ENABLE_EMAIL_VERIFICATION', 'false').lower() == 'true'
    ENABLE_TWO_FACTOR = os.environ.get('ENABLE_TWO_FACTOR', 'false').lower() == 'true'
    ENABLE_OAUTH_PROVIDERS = os.environ.get('ENABLE_OAUTH_PROVIDERS', 'true').lower() == 'true'
    
    # OAuth Provider Configurations
    OAUTH_PROVIDERS = {
        'twitch': {
            'client_id': os.environ.get('TWITCH_OAUTH_CLIENT_ID', ''),
            'client_secret': os.environ.get('TWITCH_OAUTH_CLIENT_SECRET', ''),
            'authorize_url': 'https://id.twitch.tv/oauth2/authorize',
            'token_url': 'https://id.twitch.tv/oauth2/token',
            'user_info_url': 'https://api.twitch.tv/helix/users',
            'scope': ['user:read:email'],
            'redirect_uri': os.environ.get('TWITCH_OAUTH_REDIRECT_URI', 'http://localhost:8050/auth/oauth/twitch/callback'),
            'enabled': os.environ.get('ENABLE_TWITCH_OAUTH', 'true').lower() == 'true'
        },
        'discord': {
            'client_id': os.environ.get('DISCORD_OAUTH_CLIENT_ID', ''),
            'client_secret': os.environ.get('DISCORD_OAUTH_CLIENT_SECRET', ''),
            'authorize_url': 'https://discord.com/api/oauth2/authorize',
            'token_url': 'https://discord.com/api/oauth2/token',
            'user_info_url': 'https://discord.com/api/users/@me',
            'scope': ['identify', 'email'],
            'redirect_uri': os.environ.get('DISCORD_OAUTH_REDIRECT_URI', 'http://localhost:8050/auth/oauth/discord/callback'),
            'enabled': os.environ.get('ENABLE_DISCORD_OAUTH', 'true').lower() == 'true'
        },
        'slack': {
            'client_id': os.environ.get('SLACK_OAUTH_CLIENT_ID', ''),
            'client_secret': os.environ.get('SLACK_OAUTH_CLIENT_SECRET', ''),
            'authorize_url': 'https://slack.com/oauth/v2/authorize',
            'token_url': 'https://slack.com/api/oauth.v2.access',
            'user_info_url': 'https://slack.com/api/users.identity',
            'scope': ['identity.basic', 'identity.email'],
            'redirect_uri': os.environ.get('SLACK_OAUTH_REDIRECT_URI', 'http://localhost:8050/auth/oauth/slack/callback'),
            'enabled': os.environ.get('ENABLE_SLACK_OAUTH', 'true').lower() == 'true'
        }
    }
    
    # OAuth Session Settings
    OAUTH_STATE_TTL = int(os.environ.get('OAUTH_STATE_TTL', '600'))  # 10 minutes
    OAUTH_CODE_TTL = int(os.environ.get('OAUTH_CODE_TTL', '300'))    # 5 minutes