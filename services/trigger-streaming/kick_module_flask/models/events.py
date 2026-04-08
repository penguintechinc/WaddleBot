"""
KICK Event Data Models
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime


@dataclass
class KickSender:
    """Represents a KICK user who sent a message or triggered an event."""
    id: int
    username: str
    slug: str
    identity: Optional[Dict[str, Any]] = None
    is_staff: bool = False
    is_channel_owner: bool = False
    is_moderator: bool = False
    is_subscriber: bool = False


@dataclass
class KickEvent:
    """Base class for KICK events."""
    type: str
    channel_id: int
    chatroom_id: int
    timestamp: datetime = field(default_factory=datetime.utcnow)
    raw_data: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_webhook(cls, data: dict) -> 'KickEvent':
        """Create event from webhook payload."""
        return cls(
            type=data.get('type', 'unknown'),
            channel_id=data.get('channel_id', 0),
            chatroom_id=data.get('chatroom_id', 0),
            raw_data=data
        )


@dataclass
class ChatMessageEvent(KickEvent):
    """Represents a chat message event."""
    message_id: str = ''
    content: str = ''
    sender: Optional[KickSender] = None

    @classmethod
    def from_webhook(cls, data: dict) -> 'ChatMessageEvent':
        """Create chat message event from webhook payload."""
        sender_data = data.get('sender', {})
        sender = KickSender(
            id=sender_data.get('id', 0),
            username=sender_data.get('username', ''),
            slug=sender_data.get('slug', ''),
            identity=sender_data.get('identity'),
            is_staff=sender_data.get('is_staff', False),
            is_channel_owner=sender_data.get('is_channel_owner', False),
            is_moderator=sender_data.get('is_moderator', False),
            is_subscriber=sender_data.get('is_subscriber', False),
        )

        return cls(
            type='ChatMessage',
            channel_id=data.get('channel_id', 0),
            chatroom_id=data.get('chatroom_id', 0),
            message_id=data.get('id', ''),
            content=data.get('content', ''),
            sender=sender,
            raw_data=data
        )


@dataclass
class SubscriptionEvent(KickEvent):
    """Represents a subscription event."""
    subscriber_username: str = ''
    months: int = 1
    is_gift: bool = False
    gifter_username: Optional[str] = None

    @classmethod
    def from_webhook(cls, data: dict) -> 'SubscriptionEvent':
        """Create subscription event from webhook payload."""
        return cls(
            type='Subscription',
            channel_id=data.get('channel_id', 0),
            chatroom_id=data.get('chatroom_id', 0),
            subscriber_username=data.get('username', ''),
            months=data.get('months', 1),
            is_gift=data.get('is_gift', False),
            gifter_username=data.get('gifter_username'),
            raw_data=data
        )


@dataclass
class FollowEvent(KickEvent):
    """Represents a follow event."""
    follower_id: int = 0
    follower_username: str = ''

    @classmethod
    def from_webhook(cls, data: dict) -> 'FollowEvent':
        """Create follow event from webhook payload."""
        return cls(
            type='Follow',
            channel_id=data.get('channel_id', 0),
            chatroom_id=data.get('chatroom_id', 0),
            follower_id=data.get('follower_id', 0),
            follower_username=data.get('username', ''),
            raw_data=data
        )


@dataclass
class StreamEvent(KickEvent):
    """Represents a stream start/end event."""
    stream_id: Optional[str] = None
    title: str = ''
    category: str = ''
    viewer_count: int = 0
    is_live: bool = False

    @classmethod
    def from_webhook(cls, data: dict, is_start: bool = True) -> 'StreamEvent':
        """Create stream event from webhook payload."""
        return cls(
            type='StreamStart' if is_start else 'StreamEnd',
            channel_id=data.get('channel_id', 0),
            chatroom_id=data.get('chatroom_id', 0),
            stream_id=data.get('stream_id'),
            title=data.get('title', ''),
            category=data.get('category', ''),
            viewer_count=data.get('viewer_count', 0),
            is_live=is_start,
            raw_data=data
        )
