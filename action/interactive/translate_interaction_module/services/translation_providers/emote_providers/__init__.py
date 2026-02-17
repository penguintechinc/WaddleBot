"""
Emote Providers - Platform-specific emote fetching
==================================================

Provides emote data from various platforms and third-party services:
- Twitch Global emotes
- BTTV (BetterTTV)
- FFZ (FrankerFaceZ)
- 7TV
- Discord (regex-based)
- Slack (regex-based)
"""

from .base_emote_provider import BaseEmoteProvider, Emote
from .twitch_emote_provider import TwitchEmoteProvider
from .discord_emote_provider import DiscordEmoteProvider
from .slack_emote_provider import SlackEmoteProvider

__all__ = [
    'BaseEmoteProvider',
    'Emote',
    'TwitchEmoteProvider',
    'DiscordEmoteProvider',
    'SlackEmoteProvider',
]
