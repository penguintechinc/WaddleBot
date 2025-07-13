"""
Data classes for Twitch module
Based on existing WaddleBot dataclasses
"""

from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
from datetime import datetime

@dataclass
class IdentityPayload:
    """Payload for identity lookup"""
    identity_name: str

@dataclass 
class Activity:
    """Activity data structure"""
    name: str
    amount: int

@dataclass
class ContextPayload:
    """Payload for context API requests"""
    userid: int
    activity: str
    amount: int
    text: str
    namespace: str
    namespaceid: int
    platform: str = "Twitch"

@dataclass
class TwitchWebhookEvent:
    """Twitch webhook event structure"""
    subscription: Dict[str, Any]
    event: Dict[str, Any]
    challenge: Optional[str] = None

@dataclass
class TwitchUser:
    """Twitch user information"""
    id: str
    login: str
    display_name: str
    type: str
    broadcaster_type: str
    description: str
    profile_image_url: str
    offline_image_url: str
    view_count: int
    email: Optional[str] = None
    created_at: Optional[str] = None

@dataclass
class TwitchToken:
    """Twitch OAuth token"""
    access_token: str
    refresh_token: str
    expires_in: int
    scope: list
    token_type: str = "bearer"

@dataclass
class TwitchSubscription:
    """EventSub subscription"""
    id: str
    status: str
    type: str
    version: str
    condition: Dict[str, Any]
    transport: Dict[str, Any]
    created_at: str
    cost: int

# Event-specific dataclasses
@dataclass
class FollowEvent:
    """Channel follow event"""
    user_id: str
    user_login: str
    user_name: str
    broadcaster_user_id: str
    broadcaster_user_login: str
    broadcaster_user_name: str
    followed_at: str

@dataclass
class SubscribeEvent:
    """Channel subscribe event"""
    user_id: str
    user_login: str
    user_name: str
    broadcaster_user_id: str
    broadcaster_user_login: str
    broadcaster_user_name: str
    tier: str
    is_gift: bool

@dataclass
class CheerEvent:
    """Channel cheer event"""
    is_anonymous: bool
    user_id: Optional[str]
    user_login: Optional[str]
    user_name: Optional[str]
    broadcaster_user_id: str
    broadcaster_user_login: str
    broadcaster_user_name: str
    message: str
    bits: int

@dataclass
class RaidEvent:
    """Channel raid event"""
    from_broadcaster_user_id: str
    from_broadcaster_user_login: str
    from_broadcaster_user_name: str
    to_broadcaster_user_id: str
    to_broadcaster_user_login: str
    to_broadcaster_user_name: str
    viewers: int

@dataclass
class GiftSubscriptionEvent:
    """Channel subscription gift event"""
    user_id: Optional[str]
    user_login: Optional[str]
    user_name: Optional[str]
    broadcaster_user_id: str
    broadcaster_user_login: str
    broadcaster_user_name: str
    total: int
    tier: str
    cumulative_total: Optional[int]
    is_anonymous: bool

def dataclass_to_dict(obj) -> dict:
    """Convert dataclass to dictionary"""
    return asdict(obj)