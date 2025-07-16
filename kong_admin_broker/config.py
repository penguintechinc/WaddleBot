import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Database Configuration
    DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://waddlebot:waddlebot_password@localhost:5432/waddlebot')
    
    # Kong Admin API Configuration
    KONG_ADMIN_URL = os.getenv('KONG_ADMIN_URL', 'http://kong:8001')
    KONG_ADMIN_USERNAME = os.getenv('KONG_ADMIN_USERNAME', 'admin')
    KONG_ADMIN_PASSWORD = os.getenv('KONG_ADMIN_PASSWORD', '')
    
    # Broker Service Configuration
    BROKER_SECRET_KEY = os.getenv('BROKER_SECRET_KEY', 'waddlebot_broker_secret_key_change_me')
    BROKER_API_KEY = os.getenv('BROKER_API_KEY', 'wbot_broker_master_key_placeholder')
    
    # Module Information
    MODULE_NAME = os.getenv('MODULE_NAME', 'kong_admin_broker')
    MODULE_VERSION = os.getenv('MODULE_VERSION', '1.0.0')
    
    # Performance Configuration
    MAX_CONCURRENT_REQUESTS = int(os.getenv('MAX_CONCURRENT_REQUESTS', '10'))
    REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '30'))
    
    # Super Admin Configuration
    SUPER_ADMIN_GROUP = os.getenv('SUPER_ADMIN_GROUP', 'super-admins')
    DEFAULT_SUPER_ADMIN_PERMISSIONS = [
        'kong:admin:read',
        'kong:admin:write', 
        'waddlebot:admin:read',
        'waddlebot:admin:write',
        'waddlebot:users:manage',
        'waddlebot:services:manage'
    ]
    
    # Security Configuration
    API_KEY_LENGTH = int(os.getenv('API_KEY_LENGTH', '64'))
    REQUIRE_EMAIL_VERIFICATION = os.getenv('REQUIRE_EMAIL_VERIFICATION', 'false').lower() == 'true'
    
    # Logging Configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    # Email Configuration (for notifications)
    SMTP_HOST = os.getenv('SMTP_HOST', '')
    SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
    SMTP_USERNAME = os.getenv('SMTP_USERNAME', '')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
    SMTP_TLS = os.getenv('SMTP_TLS', 'true').lower() == 'true'
    FROM_EMAIL = os.getenv('FROM_EMAIL', 'noreply@waddlebot.com')