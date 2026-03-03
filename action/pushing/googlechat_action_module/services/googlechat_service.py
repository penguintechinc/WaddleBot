"""
Google Chat Service - Google Chat API integration using google-api-python-client
Handles all Google Chat API operations for pushing actions
"""
import json
import logging
from typing import Optional, Any
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from pydal import DAL, Field


logger = logging.getLogger(__name__)


class GoogleChatService:
    """Google Chat API service using google-api-python-client"""

    def __init__(self, service_account_key_json: str, db: DAL):
        """
        Initialize Google Chat service

        Args:
            service_account_key_json: Service account JSON key as string
            db: PyDAL database instance
        """
        self.db = db
        self.client = None

        # Initialize Google Chat API client
        if service_account_key_json:
            try:
                self._initialize_client(service_account_key_json)
            except Exception as e:
                logger.error(f"Failed to initialize Google Chat client: {e}")

        self._define_tables()

    def _initialize_client(self, service_account_key_json: str):
        """
        Initialize Google Chat API client from service account key

        Args:
            service_account_key_json: Service account JSON key as string
        """
        try:
            # Parse service account key
            service_account_info = json.loads(service_account_key_json)

            # Create credentials
            credentials = service_account.Credentials.from_service_account_info(
                service_account_info,
                scopes=['https://www.googleapis.com/auth/chat.bot']
            )

            # Build the Chat service
            self.client = build('chat', 'v1', credentials=credentials)
            logger.info("Google Chat API client initialized successfully")

        except json.JSONDecodeError as e:
            logger.error(f"Invalid service account key JSON: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Google Chat client: {e}")
            raise

    def _define_tables(self):
        """Define database tables for tracking Google Chat actions"""
        self.db.define_table(
            'googlechat_actions',
            Field('community_id', 'string', length=64, required=True),
            Field('action_type', 'string', length=64, required=True),
            Field('space_id', 'string', length=256),
            Field('message_id', 'string', length=256),
            Field('thread_id', 'string', length=256),
            Field('request_data', 'json'),
            Field('response_data', 'json'),
            Field('success', 'boolean', default=True),
            Field('error_message', 'text'),
            Field('created_at', 'datetime', default='now')
        )

    async def send_message(
        self,
        community_id: str,
        space_id: str,
        text: Optional[str] = None,
        cards: Optional[list[dict]] = None,
        thread_id: Optional[str] = None
    ) -> dict:
        """
        Send message to Google Chat space

        Args:
            community_id: Community identifier
            space_id: Google Chat space ID
            text: Message text
            cards: Optional list of Card objects
            thread_id: Optional thread ID for replies

        Returns:
            Dict with success status, message_id, and error if any
        """
        if not self.client:
            error_msg = "Google Chat client not initialized"
            logger.error(error_msg)
            return {
                'success': False,
                'message_id': None,
                'error': error_msg
            }

        try:
            # Build message body
            message_body = {}

            if text:
                message_body['text'] = text

            if cards:
                message_body['cardsV2'] = [{'cardId': f'card-{i}', 'card': card} for i, card in enumerate(cards)]

            if thread_id:
                message_body['thread'] = {'name': thread_id}

            # Build request path
            parent = f"spaces/{space_id}"
            request_body = {'message': message_body}

            # Send message
            response = self.client.spaces().messages().create(
                parent=parent,
                body=request_body
            ).execute()

            message_id = response.get('name', '')

            # Log action to database
            self.db.googlechat_actions.insert(
                community_id=community_id,
                action_type='send_message',
                space_id=space_id,
                message_id=message_id,
                thread_id=thread_id,
                request_data={'text': text, 'cards': cards},
                response_data=response,
                success=True
            )
            self.db.commit()

            logger.info(f"Sent message to space {space_id} in community {community_id}")
            return {
                'success': True,
                'message_id': message_id,
                'error': None
            }

        except HttpError as e:
            error_msg = str(e)
            logger.error(f"Failed to send message: {error_msg}")
            self.db.googlechat_actions.insert(
                community_id=community_id,
                action_type='send_message',
                space_id=space_id,
                request_data={'text': text, 'cards': cards},
                success=False,
                error_message=error_msg
            )
            self.db.commit()

            return {
                'success': False,
                'message_id': None,
                'error': error_msg
            }

    async def update_message(
        self,
        community_id: str,
        message_id: str,
        text: Optional[str] = None,
        cards: Optional[list[dict]] = None
    ) -> dict:
        """
        Update existing message

        Args:
            community_id: Community identifier
            message_id: Google Chat message ID (resource name)
            text: New message text
            cards: Optional new Card objects

        Returns:
            Dict with success status and error if any
        """
        if not self.client:
            error_msg = "Google Chat client not initialized"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }

        try:
            # Build message body
            message_body = {}

            if text:
                message_body['text'] = text

            if cards:
                message_body['cardsV2'] = [{'cardId': f'card-{i}', 'card': card} for i, card in enumerate(cards)]

            request_body = {'message': message_body}

            # Update message
            response = self.client.spaces().messages().patch(
                name=message_id,
                updateMask='text,cardsV2',
                body=request_body
            ).execute()

            self.db.googlechat_actions.insert(
                community_id=community_id,
                action_type='update_message',
                message_id=message_id,
                request_data={'text': text, 'cards': cards},
                response_data=response,
                success=True
            )
            self.db.commit()

            logger.info(f"Updated message {message_id}")
            return {'success': True, 'error': None}

        except HttpError as e:
            error_msg = str(e)
            logger.error(f"Failed to update message: {error_msg}")
            self.db.googlechat_actions.insert(
                community_id=community_id,
                action_type='update_message',
                message_id=message_id,
                request_data={'text': text, 'cards': cards},
                success=False,
                error_message=error_msg
            )
            self.db.commit()

            return {'success': False, 'error': error_msg}

    async def delete_message(
        self,
        community_id: str,
        message_id: str
    ) -> dict:
        """
        Delete message

        Args:
            community_id: Community identifier
            message_id: Google Chat message ID (resource name)

        Returns:
            Dict with success status and error if any
        """
        if not self.client:
            error_msg = "Google Chat client not initialized"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }

        try:
            # Delete message
            response = self.client.spaces().messages().delete(
                name=message_id
            ).execute()

            self.db.googlechat_actions.insert(
                community_id=community_id,
                action_type='delete_message',
                message_id=message_id,
                response_data=response if response else {},
                success=True
            )
            self.db.commit()

            logger.info(f"Deleted message {message_id}")
            return {'success': True, 'error': None}

        except HttpError as e:
            error_msg = str(e)
            logger.error(f"Failed to delete message: {error_msg}")
            self.db.googlechat_actions.insert(
                community_id=community_id,
                action_type='delete_message',
                message_id=message_id,
                success=False,
                error_message=error_msg
            )
            self.db.commit()

            return {'success': False, 'error': error_msg}

    async def create_space(
        self,
        community_id: str,
        display_name: str,
        space_type: str = "SPACE",
        description: Optional[str] = None
    ) -> dict:
        """
        Create new Google Chat space

        Args:
            community_id: Community identifier
            display_name: Space display name
            space_type: Type of space (SPACE, GROUP_CHAT, or DIRECT_MESSAGE)
            description: Optional space description

        Returns:
            Dict with success status, space_id, and error if any
        """
        if not self.client:
            error_msg = "Google Chat client not initialized"
            logger.error(error_msg)
            return {
                'success': False,
                'space_id': None,
                'error': error_msg
            }

        try:
            # Build space body
            space_body = {
                'displayName': display_name,
                'spaceType': space_type
            }

            if description:
                space_body['description'] = description

            request_body = {'space': space_body}

            # Create space
            response = self.client.spaces().create(
                body=request_body
            ).execute()

            space_id = response.get('name', '')

            self.db.googlechat_actions.insert(
                community_id=community_id,
                action_type='create_space',
                space_id=space_id,
                request_data={'display_name': display_name, 'space_type': space_type, 'description': description},
                response_data=response,
                success=True
            )
            self.db.commit()

            logger.info(f"Created space {display_name} with ID {space_id}")
            return {'success': True, 'space_id': space_id, 'error': None}

        except HttpError as e:
            error_msg = str(e)
            logger.error(f"Failed to create space: {error_msg}")
            self.db.googlechat_actions.insert(
                community_id=community_id,
                action_type='create_space',
                request_data={'display_name': display_name, 'space_type': space_type},
                success=False,
                error_message=error_msg
            )
            self.db.commit()

            return {'success': False, 'space_id': None, 'error': error_msg}

    async def get_action_history(
        self,
        community_id: str,
        limit: int = 100
    ) -> list[dict]:
        """
        Get action history for community

        Args:
            community_id: Community identifier
            limit: Maximum number of records to return

        Returns:
            List of action records
        """
        rows = self.db(
            self.db.googlechat_actions.community_id == community_id
        ).select(
            orderby=~self.db.googlechat_actions.created_at,
            limitby=(0, limit)
        )

        return [row.as_dict() for row in rows]
