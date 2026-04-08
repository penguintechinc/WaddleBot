"""
YouTube API Client
==================

Wrapper for YouTube Data API v3 for reading live broadcasts and chat.
"""

import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

import httpx

from config import Config

logger = logging.getLogger(__name__)


@dataclass
class YouTubeChannel:
    """YouTube channel information."""
    channel_id: str
    title: str
    thumbnail_url: Optional[str] = None
    subscriber_count: Optional[int] = None


@dataclass
class LiveBroadcast:
    """YouTube live broadcast information."""
    broadcast_id: str
    channel_id: str
    title: str
    live_chat_id: Optional[str] = None
    status: str = 'unknown'
    viewer_count: int = 0
    start_time: Optional[str] = None


@dataclass
class ChatMessage:
    """YouTube live chat message."""
    message_id: str
    author_channel_id: str
    author_name: str
    content: str
    published_at: str
    message_type: str = 'textMessage'
    super_chat_amount: Optional[float] = None
    super_chat_currency: Optional[str] = None
    membership_months: Optional[int] = None


class YouTubeClient:
    """
    YouTube Data API v3 client for reading live broadcast data.

    Uses API key for read-only operations. OAuth tokens from the
    youtube_action_module can be used for authenticated operations.
    """

    BASE_URL = 'https://www.googleapis.com/youtube/v3'

    def __init__(self, api_key: str = None):
        """Initialize the YouTube client."""
        self.api_key = api_key or Config.YOUTUBE_API_KEY
        self._http_client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client

    async def close(self):
        """Close the HTTP client."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()

    async def _request(
        self,
        endpoint: str,
        params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Make an authenticated request to the YouTube API."""
        client = await self._get_client()

        url = f"{self.BASE_URL}/{endpoint}"
        request_params = params or {}
        request_params['key'] = self.api_key

        try:
            response = await client.get(url, params=request_params)
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"YouTube API error: {e.response.status_code}")
            raise
        except Exception as e:
            logger.error(f"YouTube API request failed: {e}")
            raise

    async def get_channel_info(self, channel_id: str) -> Optional[YouTubeChannel]:
        """
        Get channel information.

        Args:
            channel_id: YouTube channel ID

        Returns:
            YouTubeChannel object or None if not found
        """
        try:
            data = await self._request('channels', {
                'part': 'snippet,statistics',
                'id': channel_id
            })

            items = data.get('items', [])
            if not items:
                return None

            item = items[0]
            snippet = item.get('snippet', {})
            statistics = item.get('statistics', {})

            return YouTubeChannel(
                channel_id=channel_id,
                title=snippet.get('title', ''),
                thumbnail_url=snippet.get('thumbnails', {}).get(
                    'default', {}
                ).get('url'),
                subscriber_count=int(statistics.get('subscriberCount', 0))
            )

        except Exception as e:
            logger.error(f"Failed to get channel info: {e}")
            return None

    async def get_live_broadcasts(
        self, channel_id: str
    ) -> List[LiveBroadcast]:
        """
        Get active live broadcasts for a channel.

        Args:
            channel_id: YouTube channel ID

        Returns:
            List of LiveBroadcast objects
        """
        try:
            # Search for live broadcasts
            data = await self._request('search', {
                'part': 'id,snippet',
                'channelId': channel_id,
                'eventType': 'live',
                'type': 'video',
                'maxResults': 5
            })

            broadcasts = []
            for item in data.get('items', []):
                video_id = item['id'].get('videoId')
                if not video_id:
                    continue

                snippet = item.get('snippet', {})

                # Get live chat ID for this broadcast
                live_chat_id = await self._get_live_chat_id(video_id)

                broadcasts.append(LiveBroadcast(
                    broadcast_id=video_id,
                    channel_id=channel_id,
                    title=snippet.get('title', ''),
                    live_chat_id=live_chat_id,
                    status='live',
                    start_time=snippet.get('publishedAt')
                ))

            return broadcasts

        except Exception as e:
            logger.error(f"Failed to get live broadcasts: {e}")
            return []

    async def _get_live_chat_id(self, video_id: str) -> Optional[str]:
        """
        Get the live chat ID for a video/broadcast.

        Args:
            video_id: YouTube video ID

        Returns:
            Live chat ID or None
        """
        try:
            data = await self._request('videos', {
                'part': 'liveStreamingDetails',
                'id': video_id
            })

            items = data.get('items', [])
            if not items:
                return None

            live_details = items[0].get('liveStreamingDetails', {})
            return live_details.get('activeLiveChatId')

        except Exception as e:
            logger.error(f"Failed to get live chat ID: {e}")
            return None

    async def get_live_chat_messages(
        self,
        live_chat_id: str,
        page_token: str = None
    ) -> tuple[List[ChatMessage], Optional[str], int]:
        """
        Get live chat messages.

        Args:
            live_chat_id: YouTube live chat ID
            page_token: Page token for pagination

        Returns:
            Tuple of (messages, next_page_token, polling_interval_ms)
        """
        try:
            params = {
                'part': 'id,snippet,authorDetails',
                'liveChatId': live_chat_id,
                'maxResults': Config.CHAT_MAX_RESULTS
            }
            if page_token:
                params['pageToken'] = page_token

            data = await self._request('liveChat/messages', params)

            messages = []
            for item in data.get('items', []):
                msg = self._parse_chat_message(item)
                if msg:
                    messages.append(msg)

            next_token = data.get('nextPageToken')
            # YouTube suggests polling interval in milliseconds
            poll_interval = data.get('pollingIntervalMillis', 5000)

            return messages, next_token, poll_interval

        except Exception as e:
            logger.error(f"Failed to get chat messages: {e}")
            return [], None, 5000

    def _parse_chat_message(self, item: Dict[str, Any]) -> Optional[ChatMessage]:
        """Parse a chat message from API response."""
        try:
            snippet = item.get('snippet', {})
            author = item.get('authorDetails', {})

            message_type = snippet.get('type', 'textMessageEvent')

            # Extract message content based on type
            content = ''
            super_chat_amount = None
            super_chat_currency = None
            membership_months = None

            if message_type == 'textMessageEvent':
                content = snippet.get('textMessageDetails', {}).get(
                    'messageText', ''
                )
            elif message_type == 'superChatEvent':
                details = snippet.get('superChatDetails', {})
                content = details.get('userComment', '')
                super_chat_amount = float(details.get('amountMicros', 0)) / 1e6
                super_chat_currency = details.get('currency', 'USD')
            elif message_type == 'superStickerEvent':
                details = snippet.get('superStickerDetails', {})
                super_chat_amount = float(details.get('amountMicros', 0)) / 1e6
                super_chat_currency = details.get('currency', 'USD')
                content = '[Super Sticker]'
            elif message_type == 'memberMilestoneChatEvent':
                details = snippet.get('memberMilestoneChatDetails', {})
                membership_months = details.get('memberMonth', 0)
                content = details.get('userComment', '')
            elif message_type == 'newSponsorEvent':
                message_type = 'membership'
                content = '[New Member]'

            return ChatMessage(
                message_id=item.get('id', ''),
                author_channel_id=author.get('channelId', ''),
                author_name=author.get('displayName', ''),
                content=content,
                published_at=snippet.get('publishedAt', ''),
                message_type=message_type,
                super_chat_amount=super_chat_amount,
                super_chat_currency=super_chat_currency,
                membership_months=membership_months
            )

        except Exception as e:
            logger.error(f"Failed to parse chat message: {e}")
            return None

    async def subscribe_to_channel(self, channel_id: str) -> bool:
        """
        Subscribe to PubSubHubbub notifications for a channel.

        Args:
            channel_id: YouTube channel ID

        Returns:
            True if subscription request was sent successfully
        """
        client = await self._get_client()

        topic_url = (
            f"https://www.youtube.com/xml/feeds/videos.xml"
            f"?channel_id={channel_id}"
        )

        try:
            response = await client.post(
                Config.YOUTUBE_PUBSUB_HUB,
                data={
                    'hub.mode': 'subscribe',
                    'hub.topic': topic_url,
                    'hub.callback': Config.YOUTUBE_WEBHOOK_CALLBACK_URL,
                    'hub.verify': 'async',
                    'hub.lease_seconds': 432000  # 5 days
                }
            )

            if response.status_code in (202, 204):
                logger.info(f"Subscribed to channel: {channel_id}")
                return True

            logger.error(
                f"PubSubHubbub subscribe failed: {response.status_code}"
            )
            return False

        except Exception as e:
            logger.error(f"Failed to subscribe to channel: {e}")
            return False

    async def unsubscribe_from_channel(self, channel_id: str) -> bool:
        """
        Unsubscribe from PubSubHubbub notifications for a channel.

        Args:
            channel_id: YouTube channel ID

        Returns:
            True if unsubscription request was sent successfully
        """
        client = await self._get_client()

        topic_url = (
            f"https://www.youtube.com/xml/feeds/videos.xml"
            f"?channel_id={channel_id}"
        )

        try:
            response = await client.post(
                Config.YOUTUBE_PUBSUB_HUB,
                data={
                    'hub.mode': 'unsubscribe',
                    'hub.topic': topic_url,
                    'hub.callback': Config.YOUTUBE_WEBHOOK_CALLBACK_URL,
                }
            )

            if response.status_code in (202, 204):
                logger.info(f"Unsubscribed from channel: {channel_id}")
                return True

            logger.error(
                f"PubSubHubbub unsubscribe failed: {response.status_code}"
            )
            return False

        except Exception as e:
            logger.error(f"Failed to unsubscribe from channel: {e}")
            return False
