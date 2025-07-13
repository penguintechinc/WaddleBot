"""
WaddleBot Twitch Module - py4web implementation
Handles Twitch webhooks, API connections, and authentication
"""

from py4web import action, Field, DAL, HTTP, request, response
from py4web.core import Fixture
from .models import db
from .controllers import webhooks, api, auth

__version__ = "1.0.0"
__all__ = ["webhooks", "api", "auth", "db"]