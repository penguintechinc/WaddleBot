"""
Configuration for the Discord module
"""

import os
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class DiscordConfig:
    """Discord Bot configuration"""
    bot_token: str
    application_id: str
    public_key: str
    
    # Bot settings
    command_prefix: str = "!"
    intents_value: int = None  # Will be calculated based on required intents
    
    # Required intents for the bot
    required_intents: List[str] = None
    
    def __post_init__(self):
        if self.required_intents is None:
            self.required_intents = [
                "guilds",
                "guild_messages", 
                "guild_reactions",
                "guild_members",
                "guild_voice_states",
                "message_content"  # Required for message content access
            ]

@dataclass
class WaddleBotConfig:
    """WaddleBot integration configuration"""
    core_api_url: str
    context_api_url: str
    reputation_api_url: str
    gateway_activate_url: str

# Load configuration from environment variables
def load_config() -> tuple[DiscordConfig, WaddleBotConfig]:
    """Load configuration from environment variables"""
    
    # Required environment variables
    required_vars = [
        "DISCORD_BOT_TOKEN",
        "DISCORD_APPLICATION_ID",
        "DISCORD_PUBLIC_KEY",
        "CORE_API_URL",
        "CONTEXT_API_URL", 
        "REPUTATION_API_URL",
        "GATEWAY_ACTIVATE_URL"
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    discord_config = DiscordConfig(
        bot_token=os.getenv("DISCORD_BOT_TOKEN"),
        application_id=os.getenv("DISCORD_APPLICATION_ID"),
        public_key=os.getenv("DISCORD_PUBLIC_KEY"),
        command_prefix=os.getenv("DISCORD_COMMAND_PREFIX", "!")
    )
    
    waddlebot_config = WaddleBotConfig(
        core_api_url=os.getenv("CORE_API_URL"),
        context_api_url=os.getenv("CONTEXT_API_URL"),
        reputation_api_url=os.getenv("REPUTATION_API_URL"),
        gateway_activate_url=os.getenv("GATEWAY_ACTIVATE_URL")
    )
    
    return discord_config, waddlebot_config

# Activity points mapping for Discord
ACTIVITY_POINTS = {
    "message": 5,
    "reaction": 2,
    "member_join": 10,
    "voice_join": 8,
    "voice_time": 1,  # Per minute
    "command_use": 3,
    "thread_create": 15,
    "invite_create": 20,
    "boost": 100,
    "ban": -50,
    "kick": -25
}

# Discord event types we handle
MONITORED_EVENTS = [
    "on_message",
    "on_reaction_add", 
    "on_member_join",
    "on_member_remove",
    "on_voice_state_update",
    "on_guild_join",
    "on_guild_remove",
    "on_thread_create",
    "on_invite_create",
    "on_member_update"  # For boost detection
]