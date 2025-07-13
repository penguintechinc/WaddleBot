"""
Data classes for Discord module
Based on WaddleBot patterns and Discord.py structures
"""

from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, List
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
    platform: str = "Discord"

@dataclass
class DiscordUser:
    """Discord user information"""
    id: str
    username: str
    discriminator: str
    display_name: Optional[str] = None
    avatar: Optional[str] = None
    bot: bool = False
    system: bool = False
    created_at: Optional[str] = None

@dataclass
class DiscordGuild:
    """Discord guild/server information"""
    id: str
    name: str
    owner_id: str
    icon: Optional[str] = None
    description: Optional[str] = None
    member_count: int = 0
    premium_tier: int = 0
    premium_subscription_count: int = 0
    verification_level: int = 0
    created_at: Optional[str] = None

@dataclass
class DiscordChannel:
    """Discord channel information"""
    id: str
    name: str
    type: int  # 0=text, 2=voice, 4=category, etc.
    guild_id: str
    position: int = 0
    topic: Optional[str] = None
    nsfw: bool = False
    parent_id: Optional[str] = None
    created_at: Optional[str] = None

@dataclass
class DiscordMessage:
    """Discord message information"""
    id: str
    channel_id: str
    guild_id: Optional[str]
    author: DiscordUser
    content: str
    timestamp: str
    edited_timestamp: Optional[str] = None
    embeds: List[Dict] = None
    attachments: List[Dict] = None
    reactions: List[Dict] = None
    mentions: List[DiscordUser] = None
    mention_roles: List[str] = None
    reference: Optional[Dict] = None  # For replies

@dataclass
class DiscordReaction:
    """Discord reaction information"""
    emoji: str
    count: int
    me: bool
    message_id: str
    channel_id: str
    guild_id: Optional[str]
    user_id: str

@dataclass
class DiscordVoiceState:
    """Discord voice state information"""
    user_id: str
    guild_id: str
    channel_id: Optional[str]
    session_id: str
    deaf: bool = False
    mute: bool = False
    self_deaf: bool = False
    self_mute: bool = False
    self_stream: bool = False
    self_video: bool = False
    suppress: bool = False

@dataclass
class DiscordMember:
    """Discord member information"""
    user: DiscordUser
    guild_id: str
    nick: Optional[str] = None
    roles: List[str] = None
    joined_at: Optional[str] = None
    premium_since: Optional[str] = None  # Boost date
    deaf: bool = False
    mute: bool = False
    pending: bool = False
    permissions: Optional[str] = None

@dataclass
class DiscordInvite:
    """Discord invite information"""
    code: str
    guild_id: str
    channel_id: str
    inviter_id: Optional[str]
    target_user_id: Optional[str] = None
    target_type: Optional[int] = None
    approximate_presence_count: Optional[int] = None
    approximate_member_count: Optional[int] = None
    expires_at: Optional[str] = None
    max_age: int = 0
    max_uses: int = 0
    temporary: bool = False
    uses: int = 0
    created_at: Optional[str] = None

@dataclass
class DiscordThread:
    """Discord thread information"""
    id: str
    name: str
    parent_id: str
    guild_id: str
    owner_id: str
    type: int
    message_count: int = 0
    member_count: int = 0
    rate_limit_per_user: int = 0
    thread_metadata: Optional[Dict] = None
    created_at: Optional[str] = None

# Event-specific dataclasses
@dataclass
class MessageEvent:
    """Message event data"""
    message: DiscordMessage
    event_type: str = "message"

@dataclass
class ReactionEvent:
    """Reaction event data"""
    reaction: DiscordReaction
    user: DiscordUser
    event_type: str = "reaction_add"

@dataclass
class MemberEvent:
    """Member join/leave event data"""
    member: DiscordMember
    event_type: str  # member_join, member_remove

@dataclass
class VoiceEvent:
    """Voice state change event data"""
    before: Optional[DiscordVoiceState]
    after: Optional[DiscordVoiceState]
    member: DiscordMember
    event_type: str = "voice_state_update"

@dataclass
class GuildEvent:
    """Guild join/leave event data"""
    guild: DiscordGuild
    event_type: str  # guild_join, guild_remove

@dataclass
class ThreadEvent:
    """Thread creation event data"""
    thread: DiscordThread
    event_type: str = "thread_create"

@dataclass
class InviteEvent:
    """Invite creation event data"""
    invite: DiscordInvite
    event_type: str = "invite_create"

@dataclass
class SlashCommand:
    """Slash command information"""
    name: str
    description: str
    guild_id: Optional[str] = None
    options: List[Dict] = None
    default_member_permissions: Optional[str] = None
    dm_permission: bool = True
    nsfw: bool = False

def dataclass_to_dict(obj) -> dict:
    """Convert dataclass to dictionary"""
    return asdict(obj)