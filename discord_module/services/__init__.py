"""
Service modules for the Discord collector
"""

from .core_api import core_api, CoreAPIClient
from .discord_bot import bot, WaddleBotDiscord

__all__ = ["core_api", "CoreAPIClient", "bot", "WaddleBotDiscord"]