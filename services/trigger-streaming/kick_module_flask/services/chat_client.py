"""
KICK Chat Client
Real-time chat integration using Pusher WebSocket
"""
import asyncio
import json
import logging
from typing import Callable, Optional

try:
    import pysher
    PYSHER_AVAILABLE = True
except ImportError:
    PYSHER_AVAILABLE = False

logger = logging.getLogger(__name__)


class KickChatClient:
    """
    KICK chat client using Pusher for real-time messages.

    KICK uses Pusher for its WebSocket-based chat system.
    """

    # KICK's public Pusher configuration
    DEFAULT_PUSHER_KEY = 'eb1d5f283081a78b932c'
    DEFAULT_CLUSTER = 'us2'

    def __init__(
        self,
        channel_id: int,
        on_message_callback: Callable,
        pusher_key: Optional[str] = None,
        cluster: Optional[str] = None
    ):
        """
        Initialize KICK chat client.

        Args:
            channel_id: The KICK channel's chatroom ID
            on_message_callback: Async function to call when messages arrive
            pusher_key: Pusher app key (default: KICK's public key)
            cluster: Pusher cluster (default: us2)
        """
        if not PYSHER_AVAILABLE:
            raise ImportError("pysher package required for chat integration")

        self.channel_id = channel_id
        self.on_message = on_message_callback
        self.pusher_key = pusher_key or self.DEFAULT_PUSHER_KEY
        self.cluster = cluster or self.DEFAULT_CLUSTER

        self.pusher = pysher.Pusher(
            key=self.pusher_key,
            cluster=self.cluster
        )

        self._connected = False
        self._channel = None

    def connect(self):
        """Connect to KICK chat via Pusher."""
        self.pusher.connection.bind(
            'pusher:connection_established',
            self._on_connect
        )
        self.pusher.connection.bind(
            'pusher:error',
            self._on_error
        )
        self.pusher.connect()
        logger.info(f"Connecting to KICK chat for channel {self.channel_id}")

    def disconnect(self):
        """Disconnect from KICK chat."""
        if self._channel:
            self.pusher.unsubscribe(f'chatrooms.{self.channel_id}.v2')
        self.pusher.disconnect()
        self._connected = False
        logger.info(f"Disconnected from KICK chat for channel {self.channel_id}")

    def _on_connect(self, data):
        """Handle successful Pusher connection."""
        self._connected = True
        logger.info(f"Connected to Pusher, subscribing to chatroom {self.channel_id}")

        # Subscribe to chatroom channel
        channel_name = f'chatrooms.{self.channel_id}.v2'
        self._channel = self.pusher.subscribe(channel_name)

        # Bind to chat events
        self._channel.bind('ChatMessage', self._handle_chat_message)
        self._channel.bind('Subscription', self._handle_subscription)
        self._channel.bind('GiftedSubscription', self._handle_gift_subscription)
        self._channel.bind('UserBanned', self._handle_ban)
        self._channel.bind('MessageDeleted', self._handle_message_deleted)

    def _on_error(self, data):
        """Handle Pusher connection errors."""
        logger.error(f"Pusher error: {data}")
        self._connected = False

    def _handle_chat_message(self, data):
        """Handle incoming chat message."""
        try:
            message_data = json.loads(data) if isinstance(data, str) else data
            message_data['type'] = 'ChatMessage'
            asyncio.create_task(self.on_message(message_data))
        except Exception as e:
            logger.error(f"Error handling chat message: {e}")

    def _handle_subscription(self, data):
        """Handle subscription event."""
        try:
            event_data = json.loads(data) if isinstance(data, str) else data
            event_data['type'] = 'Subscription'
            asyncio.create_task(self.on_message(event_data))
        except Exception as e:
            logger.error(f"Error handling subscription: {e}")

    def _handle_gift_subscription(self, data):
        """Handle gifted subscription event."""
        try:
            event_data = json.loads(data) if isinstance(data, str) else data
            event_data['type'] = 'GiftedSubscription'
            asyncio.create_task(self.on_message(event_data))
        except Exception as e:
            logger.error(f"Error handling gift subscription: {e}")

    def _handle_ban(self, data):
        """Handle user ban event."""
        try:
            event_data = json.loads(data) if isinstance(data, str) else data
            event_data['type'] = 'Ban'
            asyncio.create_task(self.on_message(event_data))
        except Exception as e:
            logger.error(f"Error handling ban: {e}")

    def _handle_message_deleted(self, data):
        """Handle message deleted event."""
        try:
            event_data = json.loads(data) if isinstance(data, str) else data
            event_data['type'] = 'MessageDeleted'
            asyncio.create_task(self.on_message(event_data))
        except Exception as e:
            logger.error(f"Error handling message deleted: {e}")

    @property
    def is_connected(self) -> bool:
        """Check if connected to chat."""
        return self._connected
