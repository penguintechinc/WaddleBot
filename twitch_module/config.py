"""
Configuration for the Twitch module
"""

import os
from dataclasses import dataclass
from typing import List

@dataclass
class TwitchConfig:
    """Twitch API configuration"""
    app_id: str
    app_secret: str
    redirect_uri: str
    webhook_secret: str
    webhook_callback_url: str
    
    # API endpoints
    api_base_url: str = "https://api.twitch.tv/helix"
    auth_base_url: str = "https://id.twitch.tv/oauth2"
    
    # Required scopes for the application
    required_scopes: List[str] = None
    
    def __post_init__(self):
        if self.required_scopes is None:
            self.required_scopes = [
                "channel:read:subscriptions",
                "bits:read",
                "channel:read:redemptions",
                "channel:read:hype_train",
                "moderator:read:followers",
                "user:read:email"
            ]

@dataclass
class WaddleBotConfig:
    """WaddleBot integration configuration"""
    context_api_url: str
    reputation_api_url: str
    gateway_activate_url: str

# Load configuration from environment variables
def load_config() -> tuple[TwitchConfig, WaddleBotConfig]:
    """Load configuration from environment variables"""
    
    # Required environment variables
    required_vars = [
        "TWITCH_APP_ID",
        "TWITCH_APP_SECRET", 
        "TWITCH_REDIRECT_URI",
        "TWITCH_WEBHOOK_SECRET",
        "TWITCH_WEBHOOK_CALLBACK_URL",
        "CONTEXT_API_URL",
        "REPUTATION_API_URL",
        "GATEWAY_ACTIVATE_URL"
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    twitch_config = TwitchConfig(
        app_id=os.getenv("TWITCH_APP_ID"),
        app_secret=os.getenv("TWITCH_APP_SECRET"),
        redirect_uri=os.getenv("TWITCH_REDIRECT_URI"),
        webhook_secret=os.getenv("TWITCH_WEBHOOK_SECRET"),
        webhook_callback_url=os.getenv("TWITCH_WEBHOOK_CALLBACK_URL")
    )
    
    waddlebot_config = WaddleBotConfig(
        context_api_url=os.getenv("CONTEXT_API_URL"),
        reputation_api_url=os.getenv("REPUTATION_API_URL"),
        gateway_activate_url=os.getenv("GATEWAY_ACTIVATE_URL")
    )
    
    return twitch_config, waddlebot_config

# Activity points mapping
ACTIVITY_POINTS = {
    "bits": 20,
    "follow": 10,
    "sub": 50,
    "raid": 30,
    "ban": -10,
    "subgift": 60,
    "cheer": 15,
    "hypetrain": 25
}