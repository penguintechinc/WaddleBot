"""
WaddleBot Marketplace Module - py4web implementation
Manages community modules, permissions, and module marketplace
"""

from py4web import action, Field, DAL, HTTP, request, response
from py4web.core import Fixture
from .models import db
from .controllers import marketplace, modules, permissions, api

__version__ = "1.0.0"
__all__ = ["marketplace", "modules", "permissions", "api", "db"]