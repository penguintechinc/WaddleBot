"""
Configuration for the Slack module
"""

import os
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class SlackConfig:
    """Slack App configuration"""
    bot_token: str
    app_token: str
    client_id: str
    client_secret: str
    signing_secret: str
    
    # OAuth settings
    oauth_redirect_uri: str
    oauth_scopes: List[str] = None
    
    # Socket mode (for development)
    socket_mode: bool = False
    
    def __post_init__(self):
        if self.oauth_scopes is None:
            self.oauth_scopes = [
                "app_mentions:read",
                "channels:history",
                "channels:read",
                "chat:write",
                "commands",
                "files:read",
                "groups:history",
                "groups:read",
                "im:history",
                "im:read",
                "mpim:history", 
                "mpim:read",
                "reactions:read",
                "reactions:write",
                "team:read",
                "users:read",
                "users:read.email"
            ]

@dataclass
class WaddleBotConfig:
    """WaddleBot integration configuration"""
    core_api_url: str
    context_api_url: str
    reputation_api_url: str
    gateway_activate_url: str

# Load configuration from environment variables
def load_config() -> tuple[SlackConfig, WaddleBotConfig]:
    """Load configuration from environment variables"""
    
    # Required environment variables
    required_vars = [
        "SLACK_BOT_TOKEN",
        "SLACK_APP_TOKEN", 
        "SLACK_CLIENT_ID",
        "SLACK_CLIENT_SECRET",
        "SLACK_SIGNING_SECRET",
        "CORE_API_URL",
        "CONTEXT_API_URL",
        "REPUTATION_API_URL", 
        "GATEWAY_ACTIVATE_URL"
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    slack_config = SlackConfig(
        bot_token=os.getenv("SLACK_BOT_TOKEN"),
        app_token=os.getenv("SLACK_APP_TOKEN"),
        client_id=os.getenv("SLACK_CLIENT_ID"),
        client_secret=os.getenv("SLACK_CLIENT_SECRET"),
        signing_secret=os.getenv("SLACK_SIGNING_SECRET"),
        oauth_redirect_uri=os.getenv("SLACK_OAUTH_REDIRECT_URI", ""),
        socket_mode=os.getenv("SLACK_SOCKET_MODE", "false").lower() == "true"
    )
    
    waddlebot_config = WaddleBotConfig(
        core_api_url=os.getenv("CORE_API_URL"),
        context_api_url=os.getenv("CONTEXT_API_URL"),
        reputation_api_url=os.getenv("REPUTATION_API_URL"),
        gateway_activate_url=os.getenv("GATEWAY_ACTIVATE_URL")
    )
    
    return slack_config, waddlebot_config

# Activity points mapping for Slack
ACTIVITY_POINTS = {
    "message": 5,
    "file_share": 15,
    "reaction": 3,
    "member_joined_channel": 10,
    "app_mention": 8,
    "thread_message": 6,
    "slash_command": 5,
    "pin_added": 10,
    "workflow_step_execute": 20,
    "link_shared": 5,
    "emoji_changed": 2,
    "channel_created": 25,
    "call_joined": 12
}

# Slack event types we handle
MONITORED_EVENTS = [
    "message",
    "file_shared",
    "reaction_added",
    "member_joined_channel",
    "member_left_channel", 
    "app_mention",
    "pin_added",
    "pin_removed",
    "link_shared",
    "emoji_changed",
    "channel_created",
    "channel_deleted",
    "channel_rename",
    "workflow_step_execute"
]

# Slack channel types
CHANNEL_TYPES = {
    "C": "public_channel",
    "G": "private_channel", 
    "D": "direct_message",
    "M": "group_message"
}