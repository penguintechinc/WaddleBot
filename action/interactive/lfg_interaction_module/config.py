"""Configuration for lfg_interaction_module"""
import os

from dotenv import load_dotenv
from flask_core.secrets import require_secret_key

load_dotenv()


class Config:
    MODULE_NAME = 'lfg_interaction_module'
    MODULE_VERSION = '1.0.0'
    MODULE_PORT = int(os.getenv('MODULE_PORT', '8096'))
    DATABASE_URL = os.getenv(
        'DATABASE_URL',
        'postgresql://waddlebot:password@localhost:5432/waddlebot'
    )
    REDIS_URL = os.getenv('REDIS_URL', '')
    CORE_API_URL = os.getenv(
        'CORE_API_URL', 'http://router-service:8000'
    )
    ROUTER_API_URL = os.getenv(
        'ROUTER_API_URL', 'http://router-service:8000/api/v1/router'
    )
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    SECRET_KEY = require_secret_key()
    # LFG-specific settings
    LFG_DEFAULT_EXPIRY_MINUTES = int(
        os.getenv('LFG_DEFAULT_EXPIRY_MINUTES', '120')
    )
    LFG_MAX_ACTIVE_POSTS_PER_USER = int(
        os.getenv('LFG_MAX_ACTIVE_POSTS_PER_USER', '3')
    )
