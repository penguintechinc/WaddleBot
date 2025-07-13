"""
WaddleBot Slack Module - py4web implementation
Handles Slack events, slash commands, and message processing using Slack SDK
"""

from py4web import action, Field, DAL, HTTP, request, response
from py4web.core import Fixture
from .models import db
from .controllers import events, api, auth

__version__ = "1.0.0"
__all__ = ["events", "api", "auth", "db"]