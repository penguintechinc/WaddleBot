"""
Twitch Helix API service for executing actions.
Implements all Twitch API endpoints for pushing actions.
"""
import asyncio
import logging
from typing import Optional, Dict, Any, List
import aiohttp
from datetime import datetime

from config import Config
from services.token_manager import TokenManager

logger = logging.getLogger(__name__)


class TwitchService:
    """Service for executing Twitch Helix API actions."""

    def __init__(self, token_manager: TokenManager):
        """Initialize Twitch service."""
        self.token_manager = token_manager
        self.client_id = Config.TWITCH_CLIENT_ID
        self.base_url = Config.TWITCH_API_BASE_URL
        self.timeout = Config.REQUEST_TIMEOUT

    async def _execute_request(
        self,
        session: aiohttp.ClientSession,
        method: str,
        url: str,
        headers: Dict,
        params: Optional[Dict],
        json_data: Optional[Dict],
    ) -> tuple[int, str]:
        """Execute a single HTTP request and return (status, body)."""
        async with session.request(
            method,
            url,
            headers=headers,
            params=params,
            json=json_data,
            timeout=aiohttp.ClientTimeout(total=self.timeout),
        ) as resp:
            return resp.status, await resp.text()

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        broadcaster_id: str,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Make authenticated request to Twitch API.

        On a 401 response the token is force-refreshed and the request
        is retried once.  All other 4xx/5xx errors raise immediately.

        Args:
            method: HTTP method (GET, POST, PATCH, DELETE)
            endpoint: API endpoint path
            broadcaster_id: Broadcaster ID for token lookup
            params: Query parameters
            json_data: JSON request body

        Returns:
            API response as dictionary
        """
        # Get valid access token
        access_token = await self.token_manager.get_token(broadcaster_id)
        if not access_token:
            raise ValueError(f"No valid token for broadcaster {broadcaster_id}")

        headers = {
            "Client-ID": self.client_id,
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        url = f"{self.base_url}{endpoint}"

        try:
            async with aiohttp.ClientSession() as session:
                status, response_text = await self._execute_request(
                    session, method, url, headers, params, json_data
                )

                if status == 401:
                    # Token was rejected — force a refresh and retry once.
                    logger.warning(
                        f"Twitch API 401 for broadcaster {broadcaster_id} on "
                        f"{method} {endpoint} — refreshing token and retrying"
                    )
                    new_token = await self.token_manager.force_refresh(broadcaster_id)
                    if not new_token:
                        raise Exception(
                            f"Token refresh after 401 failed for broadcaster {broadcaster_id}"
                        )
                    headers["Authorization"] = f"Bearer {new_token}"
                    status, response_text = await self._execute_request(
                        session, method, url, headers, params, json_data
                    )

                if status >= 400:
                    logger.error(
                        f"Twitch API error: {method} {endpoint} - "
                        f"Status {status}: {response_text}"
                    )
                    raise Exception(f"Twitch API error: {status} - {response_text}")

                if response_text:
                    import json as _json
                    return _json.loads(response_text)
                return {"success": True}

        except asyncio.TimeoutError:
            logger.error(f"Twitch API timeout: {method} {endpoint}")
            raise Exception("Twitch API request timeout")
        except Exception as e:
            logger.error(f"Twitch API request failed: {method} {endpoint} - {e}")
            raise

    async def send_chat_message(self, broadcaster_id: str, message: str) -> Dict[str, Any]:
        """
        Send chat message to broadcaster's channel.

        Args:
            broadcaster_id: Broadcaster ID
            message: Message text

        Returns:
            API response
        """
        endpoint = "/chat/messages"
        json_data = {
            "broadcaster_id": broadcaster_id,
            "sender_id": broadcaster_id,
            "message": message
        }

        result = await self._make_request("POST", endpoint, broadcaster_id, json_data=json_data)
        logger.info(f"Chat message sent to broadcaster {broadcaster_id}")
        return result

    async def send_whisper(
        self,
        from_user_id: str,
        to_user_id: str,
        message: str
    ) -> Dict[str, Any]:
        """
        Send whisper to user.

        Args:
            from_user_id: Sender user ID (must have token)
            to_user_id: Recipient user ID
            message: Whisper text

        Returns:
            API response
        """
        endpoint = "/whispers"
        params = {
            "from_user_id": from_user_id,
            "to_user_id": to_user_id
        }
        json_data = {"message": message}

        result = await self._make_request("POST", endpoint, from_user_id, params=params, json_data=json_data)
        logger.info(f"Whisper sent from {from_user_id} to {to_user_id}")
        return result

    async def send_announcement(
        self,
        broadcaster_id: str,
        message: str,
        color: str = "primary"
    ) -> Dict[str, Any]:
        """
        Send announcement to chat.

        Args:
            broadcaster_id: Broadcaster ID
            message: Announcement text
            color: Announcement color (blue, green, orange, purple, primary)

        Returns:
            API response
        """
        endpoint = "/chat/announcements"
        params = {
            "broadcaster_id": broadcaster_id,
            "moderator_id": broadcaster_id
        }
        json_data = {
            "message": message,
            "color": color
        }

        result = await self._make_request("POST", endpoint, broadcaster_id, params=params, json_data=json_data)
        logger.info(f"Announcement sent to broadcaster {broadcaster_id}")
        return result

    async def create_clip(self, broadcaster_id: str) -> Dict[str, Any]:
        """
        Create clip of current broadcast.

        Args:
            broadcaster_id: Broadcaster ID

        Returns:
            Clip creation response with clip ID and edit URL
        """
        endpoint = "/clips"
        params = {"broadcaster_id": broadcaster_id}

        result = await self._make_request("POST", endpoint, broadcaster_id, params=params)
        logger.info(f"Clip created for broadcaster {broadcaster_id}")
        return result

    async def create_poll(
        self,
        broadcaster_id: str,
        title: str,
        choices: List[str],
        duration: int
    ) -> Dict[str, Any]:
        """
        Create poll in channel.

        Args:
            broadcaster_id: Broadcaster ID
            title: Poll title
            choices: List of poll choices (2-5 items)
            duration: Poll duration in seconds (15-1800)

        Returns:
            Poll creation response
        """
        if len(choices) < 2 or len(choices) > 5:
            raise ValueError("Poll must have 2-5 choices")

        endpoint = "/polls"
        json_data = {
            "broadcaster_id": broadcaster_id,
            "title": title,
            "choices": [{"title": choice} for choice in choices],
            "duration": duration
        }

        result = await self._make_request("POST", endpoint, broadcaster_id, json_data=json_data)
        logger.info(f"Poll created for broadcaster {broadcaster_id}")
        return result

    async def end_poll(
        self,
        broadcaster_id: str,
        poll_id: str,
        status: str
    ) -> Dict[str, Any]:
        """
        End active poll.

        Args:
            broadcaster_id: Broadcaster ID
            poll_id: Poll ID
            status: Poll status (TERMINATED or ARCHIVED)

        Returns:
            API response
        """
        endpoint = "/polls"
        json_data = {
            "broadcaster_id": broadcaster_id,
            "id": poll_id,
            "status": status.upper()
        }

        result = await self._make_request("PATCH", endpoint, broadcaster_id, json_data=json_data)
        logger.info(f"Poll {poll_id} ended for broadcaster {broadcaster_id}")
        return result

    async def create_prediction(
        self,
        broadcaster_id: str,
        title: str,
        outcomes: List[str],
        duration: int
    ) -> Dict[str, Any]:
        """
        Create prediction in channel.

        Args:
            broadcaster_id: Broadcaster ID
            title: Prediction title
            outcomes: List of outcomes (exactly 2)
            duration: Prediction window in seconds (1-1800)

        Returns:
            Prediction creation response
        """
        if len(outcomes) != 2:
            raise ValueError("Prediction must have exactly 2 outcomes")

        endpoint = "/predictions"
        json_data = {
            "broadcaster_id": broadcaster_id,
            "title": title,
            "outcomes": [{"title": outcome} for outcome in outcomes],
            "prediction_window": duration
        }

        result = await self._make_request("POST", endpoint, broadcaster_id, json_data=json_data)
        logger.info(f"Prediction created for broadcaster {broadcaster_id}")
        return result

    async def resolve_prediction(
        self,
        broadcaster_id: str,
        prediction_id: str,
        winning_outcome_id: str
    ) -> Dict[str, Any]:
        """
        Resolve prediction with winning outcome.

        Args:
            broadcaster_id: Broadcaster ID
            prediction_id: Prediction ID
            winning_outcome_id: Winning outcome ID

        Returns:
            API response
        """
        endpoint = "/predictions"
        json_data = {
            "broadcaster_id": broadcaster_id,
            "id": prediction_id,
            "status": "RESOLVED",
            "winning_outcome_id": winning_outcome_id
        }

        result = await self._make_request("PATCH", endpoint, broadcaster_id, json_data=json_data)
        logger.info(f"Prediction {prediction_id} resolved for broadcaster {broadcaster_id}")
        return result

    async def ban_user(
        self,
        broadcaster_id: str,
        user_id: str,
        reason: str,
        duration: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Ban or timeout user.

        Args:
            broadcaster_id: Broadcaster ID
            user_id: User ID to ban
            reason: Ban reason
            duration: Timeout duration in seconds (None for permanent ban)

        Returns:
            API response
        """
        endpoint = "/moderation/bans"
        params = {
            "broadcaster_id": broadcaster_id,
            "moderator_id": broadcaster_id
        }
        json_data = {
            "data": {
                "user_id": user_id,
                "reason": reason
            }
        }

        if duration:
            json_data["data"]["duration"] = duration

        result = await self._make_request("POST", endpoint, broadcaster_id, params=params, json_data=json_data)
        action = "timed out" if duration else "banned"
        logger.info(f"User {user_id} {action} in broadcaster {broadcaster_id}")
        return result

    async def unban_user(self, broadcaster_id: str, user_id: str) -> Dict[str, Any]:
        """
        Unban user.

        Args:
            broadcaster_id: Broadcaster ID
            user_id: User ID to unban

        Returns:
            API response
        """
        endpoint = "/moderation/bans"
        params = {
            "broadcaster_id": broadcaster_id,
            "moderator_id": broadcaster_id,
            "user_id": user_id
        }

        result = await self._make_request("DELETE", endpoint, broadcaster_id, params=params)
        logger.info(f"User {user_id} unbanned in broadcaster {broadcaster_id}")
        return result

    async def delete_chat_message(
        self,
        broadcaster_id: str,
        message_id: str
    ) -> Dict[str, Any]:
        """
        Delete chat message.

        Args:
            broadcaster_id: Broadcaster ID
            message_id: Message ID to delete

        Returns:
            API response
        """
        endpoint = "/moderation/chat"
        params = {
            "broadcaster_id": broadcaster_id,
            "moderator_id": broadcaster_id,
            "message_id": message_id
        }

        result = await self._make_request("DELETE", endpoint, broadcaster_id, params=params)
        logger.info(f"Message {message_id} deleted in broadcaster {broadcaster_id}")
        return result

    async def update_stream_title(self, broadcaster_id: str, title: str) -> Dict[str, Any]:
        """
        Update stream title.

        Args:
            broadcaster_id: Broadcaster ID
            title: New stream title

        Returns:
            API response
        """
        endpoint = "/channels"
        params = {"broadcaster_id": broadcaster_id}
        json_data = {"title": title}

        result = await self._make_request("PATCH", endpoint, broadcaster_id, params=params, json_data=json_data)
        logger.info(f"Stream title updated for broadcaster {broadcaster_id}")
        return result

    async def update_stream_game(self, broadcaster_id: str, game_id: str) -> Dict[str, Any]:
        """
        Update stream game/category.

        Args:
            broadcaster_id: Broadcaster ID
            game_id: Twitch game ID

        Returns:
            API response
        """
        endpoint = "/channels"
        params = {"broadcaster_id": broadcaster_id}
        json_data = {"game_id": game_id}

        result = await self._make_request("PATCH", endpoint, broadcaster_id, params=params, json_data=json_data)
        logger.info(f"Stream game updated for broadcaster {broadcaster_id}")
        return result

    async def create_stream_marker(
        self,
        broadcaster_id: str,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create stream marker.

        Args:
            broadcaster_id: Broadcaster ID
            description: Marker description

        Returns:
            API response
        """
        endpoint = "/streams/markers"
        json_data = {"user_id": broadcaster_id}
        if description:
            json_data["description"] = description

        result = await self._make_request("POST", endpoint, broadcaster_id, json_data=json_data)
        logger.info(f"Stream marker created for broadcaster {broadcaster_id}")
        return result

    async def raid(self, from_broadcaster_id: str, to_broadcaster_id: str) -> Dict[str, Any]:
        """
        Start raid to another channel.

        Args:
            from_broadcaster_id: Source broadcaster ID
            to_broadcaster_id: Target broadcaster ID

        Returns:
            API response
        """
        endpoint = "/raids"
        params = {
            "from_broadcaster_id": from_broadcaster_id,
            "to_broadcaster_id": to_broadcaster_id
        }

        result = await self._make_request("POST", endpoint, from_broadcaster_id, params=params)
        logger.info(f"Raid started from {from_broadcaster_id} to {to_broadcaster_id}")
        return result

    async def manage_vip(
        self,
        broadcaster_id: str,
        user_id: str,
        action: str
    ) -> Dict[str, Any]:
        """
        Add or remove VIP.

        Args:
            broadcaster_id: Broadcaster ID
            user_id: User ID
            action: 'add' or 'remove'

        Returns:
            API response
        """
        endpoint = "/channels/vips"
        params = {
            "broadcaster_id": broadcaster_id,
            "user_id": user_id
        }

        method = "POST" if action == "add" else "DELETE"
        result = await self._make_request(method, endpoint, broadcaster_id, params=params)
        logger.info(f"VIP {action} for user {user_id} in broadcaster {broadcaster_id}")
        return result

    async def manage_moderator(
        self,
        broadcaster_id: str,
        user_id: str,
        action: str
    ) -> Dict[str, Any]:
        """
        Add or remove moderator.

        Args:
            broadcaster_id: Broadcaster ID
            user_id: User ID
            action: 'add' or 'remove'

        Returns:
            API response
        """
        endpoint = "/moderation/moderators"
        params = {
            "broadcaster_id": broadcaster_id,
            "user_id": user_id
        }

        method = "POST" if action == "add" else "DELETE"
        result = await self._make_request(method, endpoint, broadcaster_id, params=params)
        logger.info(f"Moderator {action} for user {user_id} in broadcaster {broadcaster_id}")
        return result
