"""
Chat Poller Service
===================

Background service that polls YouTube Live Chat for new messages
and forwards them to the router module.
"""

import asyncio
import logging
from typing import Dict, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime

import httpx

from config import Config
from services.youtube_client import YouTubeClient, ChatMessage, LiveBroadcast

logger = logging.getLogger(__name__)


@dataclass
class ActiveChat:
    """Represents an actively polled live chat."""
    channel_id: str
    broadcast_id: str
    live_chat_id: str
    title: str
    page_token: Optional[str] = None
    poll_interval_ms: int = 5000
    last_poll: Optional[datetime] = None
    message_count: int = 0
    error_count: int = 0


@dataclass
class ChatPollerState:
    """State for the chat poller service."""
    active_chats: Dict[str, ActiveChat] = field(default_factory=dict)
    monitored_channels: Set[str] = field(default_factory=set)
    is_running: bool = False


class ChatPoller:
    """
    Background service for polling YouTube Live Chat.

    Polls active live chats for new messages and forwards them
    to the router module for processing.
    """

    def __init__(self, youtube_client: YouTubeClient):
        """Initialize the chat poller."""
        self.youtube = youtube_client
        self.state = ChatPollerState()
        self._poll_task: Optional[asyncio.Task] = None
        self._http_client: Optional[httpx.AsyncClient] = None

    async def start(self):
        """Start the chat poller background task."""
        if self.state.is_running:
            return

        self.state.is_running = True
        self._http_client = httpx.AsyncClient(timeout=30.0)
        self._poll_task = asyncio.create_task(self._poll_loop())
        logger.info("Chat poller started")

    async def stop(self):
        """Stop the chat poller background task."""
        self.state.is_running = False

        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass

        if self._http_client:
            await self._http_client.aclose()

        logger.info("Chat poller stopped")

    def add_channel(self, channel_id: str):
        """Add a channel to monitor for live broadcasts."""
        self.state.monitored_channels.add(channel_id)
        logger.info(f"Added channel to monitoring: {channel_id}")

    def remove_channel(self, channel_id: str):
        """Remove a channel from monitoring."""
        self.state.monitored_channels.discard(channel_id)
        # Remove any active chats for this channel
        to_remove = [
            k for k, v in self.state.active_chats.items()
            if v.channel_id == channel_id
        ]
        for key in to_remove:
            del self.state.active_chats[key]
        logger.info(f"Removed channel from monitoring: {channel_id}")

    def get_status(self) -> Dict:
        """Get current poller status."""
        return {
            'is_running': self.state.is_running,
            'monitored_channels': len(self.state.monitored_channels),
            'active_chats': len(self.state.active_chats),
            'chats': [
                {
                    'channel_id': chat.channel_id,
                    'broadcast_id': chat.broadcast_id,
                    'title': chat.title,
                    'message_count': chat.message_count,
                    'error_count': chat.error_count
                }
                for chat in self.state.active_chats.values()
            ]
        }

    async def _poll_loop(self):
        """Main polling loop."""
        while self.state.is_running:
            try:
                # Check for new live broadcasts
                await self._check_for_broadcasts()

                # Poll active chats
                await self._poll_active_chats()

                # Wait before next iteration
                await asyncio.sleep(Config.CHAT_POLL_INTERVAL)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in poll loop: {e}")
                await asyncio.sleep(5)

    async def _check_for_broadcasts(self):
        """Check monitored channels for new live broadcasts."""
        for channel_id in list(self.state.monitored_channels):
            try:
                broadcasts = await self.youtube.get_live_broadcasts(channel_id)

                for broadcast in broadcasts:
                    if not broadcast.live_chat_id:
                        continue

                    chat_key = broadcast.live_chat_id

                    if chat_key not in self.state.active_chats:
                        # New broadcast found
                        self.state.active_chats[chat_key] = ActiveChat(
                            channel_id=channel_id,
                            broadcast_id=broadcast.broadcast_id,
                            live_chat_id=broadcast.live_chat_id,
                            title=broadcast.title
                        )

                        # Forward stream start event
                        await self._forward_event({
                            'type': 'streamStart',
                            'platform': 'youtube',
                            'channel_id': channel_id,
                            'broadcast_id': broadcast.broadcast_id,
                            'title': broadcast.title,
                            'live_chat_id': broadcast.live_chat_id
                        })

                        logger.info(
                            f"New broadcast detected: {broadcast.title} "
                            f"({broadcast.broadcast_id})"
                        )

            except Exception as e:
                logger.error(f"Error checking broadcasts for {channel_id}: {e}")

    async def _poll_active_chats(self):
        """Poll all active chats for new messages."""
        # Clean up ended broadcasts
        to_remove = []

        for chat_key, chat in list(self.state.active_chats.items()):
            try:
                messages, next_token, poll_interval = (
                    await self.youtube.get_live_chat_messages(
                        chat.live_chat_id,
                        chat.page_token
                    )
                )

                chat.page_token = next_token
                chat.poll_interval_ms = poll_interval
                chat.last_poll = datetime.utcnow()
                chat.error_count = 0

                # Forward messages to router
                for msg in messages:
                    await self._forward_chat_message(chat, msg)
                    chat.message_count += 1

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 403:
                    # Chat ended or access denied
                    logger.info(f"Chat ended: {chat.broadcast_id}")
                    to_remove.append(chat_key)

                    await self._forward_event({
                        'type': 'streamEnd',
                        'platform': 'youtube',
                        'channel_id': chat.channel_id,
                        'broadcast_id': chat.broadcast_id
                    })
                else:
                    chat.error_count += 1
                    logger.error(f"Error polling chat {chat_key}: {e}")

            except Exception as e:
                chat.error_count += 1
                logger.error(f"Error polling chat {chat_key}: {e}")

                # Remove chat if too many errors
                if chat.error_count > 10:
                    to_remove.append(chat_key)

        # Remove ended chats
        for key in to_remove:
            if key in self.state.active_chats:
                del self.state.active_chats[key]

    async def _forward_chat_message(self, chat: ActiveChat, msg: ChatMessage):
        """Forward a chat message to the router."""
        event_type = 'chatMessage'
        if msg.message_type in ('superChatEvent', 'superStickerEvent'):
            event_type = 'superChat'
        elif msg.message_type in ('newSponsorEvent', 'memberMilestoneChatEvent'):
            event_type = 'membership'

        event = {
            'type': event_type,
            'platform': 'youtube',
            'channel_id': chat.channel_id,
            'broadcast_id': chat.broadcast_id,
            'message_id': msg.message_id,
            'user_id': msg.author_channel_id,
            'username': msg.author_name,
            'content': msg.content,
            'timestamp': msg.published_at
        }

        if msg.super_chat_amount:
            event['amount'] = msg.super_chat_amount
            event['currency'] = msg.super_chat_currency

        if msg.membership_months:
            event['membership_months'] = msg.membership_months

        await self._forward_event(event)

    async def _forward_event(self, event: Dict):
        """Forward an event to the router module."""
        if not self._http_client:
            return

        try:
            response = await self._http_client.post(
                f"{Config.ROUTER_API_URL}/events",
                json=event,
                timeout=10.0
            )

            if response.status_code != 200:
                logger.warning(
                    f"Router returned {response.status_code} for event"
                )

        except Exception as e:
            logger.error(f"Failed to forward event to router: {e}")
