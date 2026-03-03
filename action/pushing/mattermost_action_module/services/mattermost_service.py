import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

import httpx
from mattermostdriver import Client
from pydal import DAL

logger = logging.getLogger(__name__)


class MattermostService:
    """Service for interacting with Mattermost API."""

    def __init__(self, mattermost_url: str, bot_token: str, db: DAL):
        """Initialize Mattermost service.

        Args:
            mattermost_url: Base URL of Mattermost instance
            bot_token: Bot token for authentication
            db: PyDAL database instance
        """
        self.mattermost_url = mattermost_url.rstrip('/')
        self.bot_token = bot_token
        self.db = db

        # Initialize Mattermost client
        self.client = Client({
            'url': mattermost_url,
            'token': bot_token,
        })

        # HTTP client for direct API calls if needed
        self.http_client = httpx.AsyncClient(
            base_url=self.mattermost_url,
            headers={'Authorization': f'Bearer {bot_token}'},
            timeout=30.0,
        )

    async def send_message(
        self,
        channel_id: str,
        message: str,
        attachments: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Send a message to a Mattermost channel.

        Args:
            channel_id: Mattermost channel ID
            message: Message text
            attachments: Optional message attachments
            metadata: Optional metadata

        Returns:
            Response dict with success flag and message_id
        """
        try:
            post_data = {
                'channel_id': channel_id,
                'message': message,
            }

            if attachments:
                post_data['props'] = {
                    'attachments': attachments,
                }

            # Send post via client
            response = self.client.posts.create_post(post_data)

            return {
                'success': True,
                'message_id': response.get('id'),
                'channel_id': channel_id,
                'timestamp': datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.exception(f"Error sending message to channel {channel_id}")
            return {
                'success': False,
                'error': str(e),
                'channel_id': channel_id,
            }

    async def send_ephemeral(
        self,
        channel_id: str,
        user_id: str,
        message: str,
        attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Send an ephemeral (temporary) message to a user in a channel.

        Args:
            channel_id: Mattermost channel ID
            user_id: User ID to send ephemeral message to
            message: Message text
            attachments: Optional message attachments

        Returns:
            Response dict with success flag
        """
        try:
            post_data = {
                'user_id': user_id,
                'post': {
                    'channel_id': channel_id,
                    'message': message,
                }
            }

            if attachments:
                post_data['post']['props'] = {
                    'attachments': attachments,
                }

            # Send ephemeral post
            response = self.client.posts.create_post(post_data)

            return {
                'success': True,
                'user_id': user_id,
                'channel_id': channel_id,
                'timestamp': datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.exception(f"Error sending ephemeral message to user {user_id}")
            return {
                'success': False,
                'error': str(e),
                'user_id': user_id,
                'channel_id': channel_id,
            }

    async def add_reaction(
        self,
        message_id: str,
        emoji_name: str,
    ) -> Dict[str, Any]:
        """Add a reaction/emoji to a message.

        Args:
            message_id: Message ID to add reaction to
            emoji_name: Emoji name (e.g., 'thumbsup', 'heart')

        Returns:
            Response dict with success flag
        """
        try:
            # Mattermost uses emoji_name format: emoji_name for built-ins, :custom: for custom emojis
            if not emoji_name.startswith(':'):
                emoji_name = f':{emoji_name}:'

            # Add reaction via API
            user_id = self.client.users.get_user(user_id='me').get('id')
            response = self.client.reactions.create_reaction({
                'user_id': user_id,
                'post_id': message_id,
                'emoji_name': emoji_name.strip(':'),
            })

            return {
                'success': True,
                'message_id': message_id,
                'emoji_name': emoji_name,
                'timestamp': datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.exception(f"Error adding reaction to message {message_id}")
            return {
                'success': False,
                'error': str(e),
                'message_id': message_id,
            }

    async def remove_reaction(
        self,
        message_id: str,
        emoji_name: str,
    ) -> Dict[str, Any]:
        """Remove a reaction/emoji from a message.

        Args:
            message_id: Message ID to remove reaction from
            emoji_name: Emoji name to remove

        Returns:
            Response dict with success flag
        """
        try:
            if not emoji_name.startswith(':'):
                emoji_name = f':{emoji_name}:'

            user_id = self.client.users.get_user(user_id='me').get('id')
            self.client.reactions.delete_reaction({
                'user_id': user_id,
                'post_id': message_id,
                'emoji_name': emoji_name.strip(':'),
            })

            return {
                'success': True,
                'message_id': message_id,
                'emoji_name': emoji_name,
                'timestamp': datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.exception(f"Error removing reaction from message {message_id}")
            return {
                'success': False,
                'error': str(e),
                'message_id': message_id,
            }

    async def create_channel(
        self,
        channel_name: str,
        display_name: str,
        is_private: bool = False,
        purpose: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new Mattermost channel.

        Args:
            channel_name: Channel name (must be lowercase, alphanumeric)
            display_name: Display name for the channel
            is_private: Whether the channel is private
            purpose: Channel purpose/description

        Returns:
            Response dict with success flag and channel_id
        """
        try:
            # Get team ID (using default team)
            teams = self.client.teams.get_teams()
            if not teams:
                return {
                    'success': False,
                    'error': 'No teams found',
                }

            team_id = teams[0].get('id')

            channel_data = {
                'team_id': team_id,
                'name': channel_name.lower(),
                'display_name': display_name,
                'type': 'P' if is_private else 'O',  # P=private, O=open
            }

            if purpose:
                channel_data['purpose'] = purpose

            response = self.client.channels.create_channel(channel_data)

            return {
                'success': True,
                'channel_id': response.get('id'),
                'channel_name': response.get('name'),
                'display_name': response.get('display_name'),
                'is_private': response.get('type') == 'P',
                'timestamp': datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.exception(f"Error creating channel {channel_name}")
            return {
                'success': False,
                'error': str(e),
                'channel_name': channel_name,
            }

    async def get_action_history(
        self,
        limit: int = 100,
        offset: int = 0,
        action_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get action history from the database.

        Args:
            limit: Number of records to return
            offset: Number of records to skip
            action_type: Optional filter by action type

        Returns:
            Response dict with history records
        """
        try:
            query = self.db.action_history
            if action_type:
                query = query(self.db.action_history.action_type == action_type)

            records = query.select(
                orderby=~self.db.action_history.created_at,
                limitby=(offset, offset + limit),
            )

            history = [
                {
                    'id': r.id,
                    'action_type': r.action_type,
                    'channel_id': r.channel_id,
                    'message_id': r.message_id,
                    'user_id': r.user_id,
                    'status': r.status,
                    'error_message': r.error_message,
                    'created_at': r.created_at.isoformat() if r.created_at else None,
                }
                for r in records
            ]

            total = self.db(self.db.action_history).count()

            return {
                'success': True,
                'history': history,
                'total': total,
                'limit': limit,
                'offset': offset,
            }

        except Exception as e:
            logger.exception("Error retrieving action history")
            return {
                'success': False,
                'error': str(e),
            }

    async def close(self):
        """Close HTTP client and cleanup."""
        if self.http_client:
            await self.http_client.aclose()
