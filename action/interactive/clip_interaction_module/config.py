"""Configuration for clip_interaction_module"""
import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    MODULE_NAME = 'clip_interaction_module'
    MODULE_VERSION = '1.0.0'
    MODULE_PORT = int(os.getenv('MODULE_PORT', '8098'))
    DATABASE_URL = os.getenv(
        'DATABASE_URL',
        'postgresql://waddlebot:password@localhost:5432/waddlebot'
    )
    REDIS_URL = os.getenv('REDIS_URL', '')
    CORE_API_URL = os.getenv('CORE_API_URL', 'http://router-service:8000')
    ROUTER_API_URL = os.getenv(
        'ROUTER_API_URL',
        'http://router-service:8000/api/v1/router'
    )
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    SECRET_KEY = os.getenv('SECRET_KEY', 'change-me-in-production')

    # Twitch module URL for proxying clip creation
    TWITCH_MODULE_URL = os.getenv(
        'TWITCH_MODULE_URL',
        'http://action-twitch:8010'
    )

    # Clip limits
    MAX_CLIPS_PER_REEL = 20
    MAX_TAGS_PER_CLIP = 10
