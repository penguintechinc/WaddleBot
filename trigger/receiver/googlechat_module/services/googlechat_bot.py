"""
Google Chat Bot Service - Event-driven Google Chat integration
Supports slash commands, card interactions, and space management
"""
import json
import asyncio
from typing import Dict, Any, Optional
import httpx
from google.oauth2 import service_account
from google.auth.transport.requests import Request

from flask_core import setup_aaa_logging
from libs.platform_receiver import PlatformReceiverBase
from .card_builder import CardBuilder


class GoogleChatBotService(PlatformReceiverBase):
    """
    Google Chat Bot service supporting:
    - Slash commands (via message text parsing)
    - Card v2 interactions (buttons, selects, form inputs)
    - Space management (ADDED_TO_SPACE, REMOVED_FROM_SPACE)
    - Message relay from hub
    """

    PLATFORM = "googlechat"

    def __init__(
        self,
        service_account_key: str,
        project_id: str,
        router_url: str,
        dal,
        log_level: str = 'INFO'
    ):
        super().__init__(router_url, log_level)
        self.logger = setup_aaa_logging('googlechat_bot', '1.0.0')
        self.service_account_key = service_account_key
        self.project_id = project_id
        self.dal = dal
        self._http_session: Optional[httpx.AsyncClient] = None
        self._credentials: Optional[service_account.Credentials] = None
        self._load_credentials()

    def _load_credentials(self):
        """Load Google service account credentials"""
        try:
            if isinstance(self.service_account_key, str):
                key_dict = json.loads(self.service_account_key)
            else:
                key_dict = self.service_account_key

            self._credentials = service_account.Credentials.from_service_account_info(
                key_dict,
                scopes=['https://www.googleapis.com/auth/chat.bot']
            )
            self.logger.debug("Google Chat credentials loaded successfully")
        except Exception as e:
            self.logger.error(f"Failed to load credentials: {e}")
            self._credentials = None

    async def start(self) -> None:
        """Initialize the Google Chat service (async startup handler)"""
        self.logger.info("Google Chat service starting")
        # Credentials are loaded in __init__, minimal async startup work needed
        pass

    async def stop(self) -> None:
        """Disconnect and cleanup"""
        self.logger.info("Google Chat service stopping")
        if self._http_session and not self._http_session.is_closed:
            await self._http_session.aclose()

    async def handle_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming Google Chat event"""
        try:
            event_type = event_data.get('type', '')

            if event_type == 'MESSAGE':
                return await self._handle_message(event_data)
            elif event_type == 'CARD_CLICKED':
                return await self._handle_card_click(event_data)
            elif event_type == 'ADDED_TO_SPACE':
                return await self._handle_added_to_space(event_data)
            elif event_type == 'REMOVED_FROM_SPACE':
                return await self._handle_removed_from_space(event_data)
            else:
                self.logger.warning(f"Unknown event type: {event_type}")
                return {"success": False, "error": "Unknown event type"}

        except Exception as e:
            self.logger.error(f"Error handling event: {e}")
            return {"success": False, "error": str(e)}

    async def _handle_message(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle message event from Google Chat"""
        try:
            message = event_data.get('message', {})
            space = event_data.get('space', {})
            user = event_data.get('user', {})

            message_id = message.get('name', '')
            text = message.get('text', '').strip()
            space_id = space.get('name', '')
            user_id = user.get('name', '')
            user_display = user.get('displayName', '')

            if not text or not space_id or not user_id:
                return {"success": False, "error": "Missing required fields"}

            # Check for slash command (Google Chat doesn't have native slash commands,
            # so we use text prefix like "/ command args" or "/command args")
            if text.startswith('/'):
                parts = text.lstrip('/').split(maxsplit=1)
                command = f"/{parts[0]}"
                args = parts[1] if len(parts) > 1 else ""

                event = self.build_slash_event(
                    user_id=user_id,
                    username=user_id,
                    command=command,
                    args=args,
                    channel_id=space_id,
                    server_id=space_id,
                    trigger_id=message_id,
                    metadata={
                        "message_id": message_id,
                        "display_name": user_display,
                        "thread_name": message.get('thread', {}).get('name'),
                    }
                )
            else:
                # Regular chat message
                event = self.build_chat_event(
                    user_id=user_id,
                    username=user_id,
                    display_name=user_display,
                    content=text,
                    channel_id=space_id,
                    server_id=space_id,
                    metadata={
                        "message_id": message_id,
                        "thread_name": message.get('thread', {}).get('name'),
                    }
                )

            response = await self.dispatch(event)
            return await self._execute_response(response, space_id, message_id)

        except Exception as e:
            self.logger.error(f"Error handling message: {e}")
            return {"success": False, "error": str(e)}

    async def _handle_card_click(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle card interaction (button, select, form submission)"""
        try:
            action = event_data.get('action', {})
            space = event_data.get('space', {})
            user = event_data.get('user', {})
            message = event_data.get('message', {})

            action_type = action.get('actionMethodName', '')
            params = action.get('parameters', [])
            space_id = space.get('name', '')
            user_id = user.get('name', '')
            user_display = user.get('displayName', '')
            message_id = message.get('name', '')

            if not space_id or not user_id:
                return {"success": False, "error": "Missing required fields"}

            # Parse parameters into a dict
            param_dict = {}
            for param in params:
                key = param.get('key', '')
                value = param.get('value', '')
                if key:
                    param_dict[key] = value

            # Determine interaction type based on action name
            interaction_type = 'button'
            if 'select' in action_type.lower():
                interaction_type = 'select'
            elif 'form' in action_type.lower():
                interaction_type = 'form_submit'

            event = self.build_chat_event(
                user_id=user_id,
                username=user_id,
                display_name=user_display,
                content="",
                channel_id=space_id,
                server_id=space_id,
                metadata={
                    "interaction_type": interaction_type,
                    "action_id": action_type,
                    "action_params": param_dict,
                    "message_id": message_id,
                }
            )
            # Set appropriate message type
            event['message_type'] = 'interaction'

            response = await self.dispatch(event)
            return await self._execute_response(response, space_id, message_id)

        except Exception as e:
            self.logger.error(f"Error handling card click: {e}")
            return {"success": False, "error": str(e)}

    async def _handle_added_to_space(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle bot added to space event"""
        try:
            space = event_data.get('space', {})
            space_id = space.get('name', '')
            space_type = space.get('type', '')

            self.logger.info(f"Bot added to space: {space_id} (type: {space_type})")

            # Send welcome card
            welcome_card = CardBuilder.build_welcome_card()
            await self.send_to_space(space_id, welcome_card)

            return {"success": True}

        except Exception as e:
            self.logger.error(f"Error handling ADDED_TO_SPACE: {e}")
            return {"success": False, "error": str(e)}

    async def _handle_removed_from_space(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle bot removed from space event"""
        try:
            space = event_data.get('space', {})
            space_id = space.get('name', '')

            self.logger.info(f"Bot removed from space: {space_id}")
            return {"success": True}

        except Exception as e:
            self.logger.error(f"Error handling REMOVED_FROM_SPACE: {e}")
            return {"success": False, "error": str(e)}

    async def _execute_response(
        self,
        response: Dict[str, Any],
        space_id: str,
        message_id: str
    ) -> Dict[str, Any]:
        """Execute router response by sending message/card to space"""
        try:
            if not response.get('success', False):
                # Send error message
                card = CardBuilder.build_error_card(response.get('error', 'Command failed'))
                await self.send_to_space(space_id, card)
                return {"success": False}

            action = response.get('action', {})
            action_type = action.get('type', 'message')

            if action_type == 'message':
                content = action.get('content', '')
                # If it's a simple text response, build a basic card
                if content:
                    card = CardBuilder.build_message_card(content)
                    await self.send_to_space(space_id, card)
                return {"success": True}

            elif action_type == 'card':
                card_config = action.get('card', {})
                card = CardBuilder.build_relay_card(card_config)
                await self.send_to_space(space_id, card)
                return {"success": True}

            return {"success": True}

        except Exception as e:
            self.logger.error(f"Error executing response: {e}")
            return {"success": False, "error": str(e)}

    async def send_to_space(
        self,
        space_id: str,
        content: Any,
        author: Optional[Dict[str, Any]] = None,
        message_type: str = 'message'
    ) -> bool:
        """Send a message or card to a Google Chat space"""
        try:
            if not self._credentials:
                self.logger.error("Credentials not available")
                return False

            # Refresh credentials if needed
            if self._credentials.expired:
                self._credentials.refresh(Request())

            # Build the message payload
            if isinstance(content, dict) and 'cards' in content:
                # It's already a card payload
                payload = content
            elif isinstance(content, dict):
                # It's a card dict, wrap it in cards array
                payload = {"cards": [content]}
            else:
                # It's text content
                if author:
                    display_name = author.get('username', 'Unknown')
                    platform = author.get('platform', 'hub')
                    text = f"**{display_name}** (via {platform}):\n{content}"
                else:
                    text = content
                payload = {
                    "text": text
                }

            # Send via Google Chat API
            client = self._get_http_session()
            headers = {
                "Authorization": f"Bearer {self._credentials.token}",
                "Content-Type": "application/json"
            }

            # Google Chat API endpoint
            url = f"https://chat.googleapis.com/v1/{space_id}/messages"

            response = await client.post(
                url,
                json=payload,
                headers=headers,
                timeout=10.0
            )

            if response.status_code in (200, 201):
                self.logger.debug(f"Message sent to {space_id}")
                return True
            else:
                self.logger.error(f"Failed to send message: {response.status_code} {response.text}")
                return False

        except Exception as e:
            self.logger.error(f"Error sending message to space: {e}")
            return False

    def _get_http_session(self) -> httpx.AsyncClient:
        """Get or create HTTP session"""
        if self._http_session is None or self._http_session.is_closed:
            self._http_session = httpx.AsyncClient()
        return self._http_session
