import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Database Configuration
    DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://waddlebot:waddlebot_password@localhost:5432/waddlebot')
    
    # Core API Configuration
    CORE_API_URL = os.getenv('CORE_API_URL', 'http://localhost:8000')
    ROUTER_API_URL = os.getenv('ROUTER_API_URL', 'http://localhost:8000/router')
    
    # Module Information
    MODULE_NAME = os.getenv('MODULE_NAME', 'chat_filter_module')
    MODULE_VERSION = os.getenv('MODULE_VERSION', '1.0.0')
    MODULE_PORT = int(os.getenv('MODULE_PORT', '8040'))
    
    # Filter Configuration
    ENABLE_PROFANITY_FILTER = os.getenv('ENABLE_PROFANITY_FILTER', 'true').lower() == 'true'
    ENABLE_SPAM_DETECTION = os.getenv('ENABLE_SPAM_DETECTION', 'true').lower() == 'true'
    ENABLE_URL_BLOCKING = os.getenv('ENABLE_URL_BLOCKING', 'false').lower() == 'true'
    
    # Profanity Filter Settings
    DEFAULT_PROFANITY_ACTION = os.getenv('DEFAULT_PROFANITY_ACTION', 'warn')  # warn, censor, block
    PROFANITY_STRIKE_THRESHOLD = int(os.getenv('PROFANITY_STRIKE_THRESHOLD', '3'))
    
    # Spam Detection Settings
    DEFAULT_SPAM_ACTION = os.getenv('DEFAULT_SPAM_ACTION', 'warn')  # warn, flag, block
    SPAM_CONFIDENCE_THRESHOLD = int(os.getenv('SPAM_CONFIDENCE_THRESHOLD', '30'))  # 0-100
    SPAM_STRIKE_THRESHOLD = int(os.getenv('SPAM_STRIKE_THRESHOLD', '3'))
    
    # URL Blocking Settings
    DEFAULT_URL_ACTION = os.getenv('DEFAULT_URL_ACTION', 'block')  # warn, block
    ALLOW_HTTPS_ONLY = os.getenv('ALLOW_HTTPS_ONLY', 'false').lower() == 'true'
    BLOCK_IP_ADDRESSES = os.getenv('BLOCK_IP_ADDRESSES', 'true').lower() == 'true'
    BLOCK_URL_SHORTENERS = os.getenv('BLOCK_URL_SHORTENERS', 'true').lower() == 'true'
    URL_STRIKE_THRESHOLD = int(os.getenv('URL_STRIKE_THRESHOLD', '2'))
    
    # Strike System Settings
    TOTAL_STRIKE_THRESHOLD = int(os.getenv('TOTAL_STRIKE_THRESHOLD', '5'))
    STRIKE_TIMEOUT_DURATION = int(os.getenv('STRIKE_TIMEOUT_DURATION', '300'))  # seconds
    STRIKE_DECAY_HOURS = int(os.getenv('STRIKE_DECAY_HOURS', '24'))  # hours before strikes decay
    
    # Performance Settings
    MAX_WORKERS = int(os.getenv('MAX_WORKERS', '20'))
    REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '30'))
    CACHE_TTL = int(os.getenv('CACHE_TTL', '300'))  # seconds
    
    # Logging Configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_DIR = os.getenv('LOG_DIR', '/var/log/waddlebotlog')
    ENABLE_SYSLOG = os.getenv('ENABLE_SYSLOG', 'false').lower() == 'true'
    SYSLOG_HOST = os.getenv('SYSLOG_HOST', 'localhost')
    SYSLOG_PORT = int(os.getenv('SYSLOG_PORT', '514'))
    SYSLOG_FACILITY = os.getenv('SYSLOG_FACILITY', 'LOCAL0')
    
    # Trusted Domains (built-in whitelist)
    TRUSTED_DOMAINS = os.getenv('TRUSTED_DOMAINS', 'twitch.tv,youtube.com,discord.com,github.com').split(',')
    
    # Trusted URL Shorteners
    TRUSTED_SHORTENERS = os.getenv('TRUSTED_SHORTENERS', 'youtu.be,twitch.tv').split(',')
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS = int(os.getenv('RATE_LIMIT_REQUESTS', '100'))
    RATE_LIMIT_WINDOW = int(os.getenv('RATE_LIMIT_WINDOW', '60'))  # seconds