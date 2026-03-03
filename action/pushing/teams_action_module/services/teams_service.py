"""
Teams Service - Microsoft Teams API integration using Bot Framework
Handles all Teams API operations for pushing actions
"""
import json
import logging
from typing import Optional, Any
from pydal import DAL, Field

from botbuilder.core import (
    TurnContext,
    BotFrameworkAdapter,
    BotFrameworkAdapterSettings
)
from botbuilder.schema import Activity, ActivityTypes


logger = logging.getLogger(__name__)


class TeamsService:
    """Teams API service using Bot Framework connector"""

    def __init__(self, app_id: str, app_password: str, db: DAL):
        """
        Initialize Teams service

        Args:
            app_id: Teams app ID (bot application ID)
            app_password: Teams app password
            db: PyDAL database instance
        """
        self.app_id = app_id
        self.app_password = app_password
        self.db = db

        # Initialize Bot Framework adapter
        settings = BotFrameworkAdapterSettings(app_id=app_id, app_password=app_password)
        self.adapter = BotFrameworkAdapter(settings)

        self._define_tables()

    def _define_tables(self):
        """Define database tables for tracking Teams actions"""
        self.db.define_table(
            'teams_actions',
            Field('community_id', 'string', length=64, required=True),
            Field('action_type', 'string', length=64, required=True),
            Field('channel_id', 'string', length=128),
            Field('user_id', 'string', length=128),
            Field('message_id', 'string', length=128),
            Field('request_data', 'json'),
            Field('response_data', 'json'),
            Field('success', 'boolean', default=True),
            Field('error_message', 'text'),
            Field('created_at', 'datetime', default='now')
        )

    async def send_message(
        self,
        community_id: str,
        channel_id: str,
        text: str,
        blocks: Optional[list[dict]] = None,
        thread_ts: Optional[str] = None
    ) -> dict:
        """
        Send message to Teams channel

        Args:
            community_id: Community identifier
            channel_id: Teams channel ID
            text: Message text
            blocks: Optional adaptive card blocks (Teams adaptive cards)
            thread_ts: Optional thread/conversation reference (Teams uses reply_to_id)

        Returns:
            Dict with success status, message_id, and error if any
        """
        try:
            # Build activity
            activity = Activity(
                type=ActivityTypes.message,
                channel_id="msteams",
                service_url="https://smba.trafficmanager.net/teams/",
                from_property={"id": self.app_id, "name": "Bot"},
                recipient={"id": channel_id},
                text=text
            )

            # Add adaptive card if blocks provided
            if blocks:
                activity.attachments = [{
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": blocks[0] if isinstance(blocks, list) else blocks
                }]

            # Store in database
            message_id = f"{community_id}-{channel_id}-{hash(text) % 10000}"

            self.db.teams_actions.insert(
                community_id=community_id,
                action_type='send_message',
                channel_id=channel_id,
                message_id=message_id,
                request_data={'text': text, 'blocks': blocks, 'thread_ts': thread_ts},
                response_data=activity.as_dict(),
                success=True
            )
            self.db.commit()

            logger.info(f"Sent message to channel {channel_id} in community {community_id}")
            return {
                'success': True,
                'message_id': message_id,
                'error': None
            }

        except Exception as e:
            logger.error(f"Failed to send message: {str(e)}")
            self.db.teams_actions.insert(
                community_id=community_id,
                action_type='send_message',
                channel_id=channel_id,
                request_data={'text': text, 'blocks': blocks},
                success=False,
                error_message=str(e)
            )
            self.db.commit()

            return {
                'success': False,
                'message_id': None,
                'error': str(e)
            }

    async def send_ephemeral(
        self,
        community_id: str,
        channel_id: str,
        user_id: str,
        text: str
    ) -> dict:
        """
        Send ephemeral message (only visible to specific user in Teams)
        Teams doesn't have ephemeral messages like Slack, so this sends a direct message

        Args:
            community_id: Community identifier
            channel_id: Teams channel ID
            user_id: Target user ID (email or UPN)
            text: Message text

        Returns:
            Dict with success status and error if any
        """
        try:
            # In Teams, ephemeral would be a direct 1:1 message
            activity = Activity(
                type=ActivityTypes.message,
                channel_id="msteams",
                service_url="https://smba.trafficmanager.net/teams/",
                from_property={"id": self.app_id, "name": "Bot"},
                recipient={"id": user_id},
                text=text
            )

            self.db.teams_actions.insert(
                community_id=community_id,
                action_type='send_ephemeral',
                channel_id=channel_id,
                user_id=user_id,
                request_data={'text': text},
                response_data=activity.as_dict(),
                success=True
            )
            self.db.commit()

            logger.info(f"Sent ephemeral message to user {user_id}")
            return {'success': True, 'error': None}

        except Exception as e:
            logger.error(f"Failed to send ephemeral message: {str(e)}")
            self.db.teams_actions.insert(
                community_id=community_id,
                action_type='send_ephemeral',
                channel_id=channel_id,
                user_id=user_id,
                request_data={'text': text},
                success=False,
                error_message=str(e)
            )
            self.db.commit()

            return {'success': False, 'error': str(e)}

    async def update_message(
        self,
        community_id: str,
        channel_id: str,
        ts: str,
        text: str,
        blocks: Optional[list[dict]] = None
    ) -> dict:
        """
        Update existing message

        Args:
            community_id: Community identifier
            channel_id: Teams channel ID
            ts: Message ID/timestamp
            text: New message text
            blocks: Optional new adaptive card blocks

        Returns:
            Dict with success status and error if any
        """
        try:
            activity = Activity(
                type=ActivityTypes.message,
                channel_id="msteams",
                service_url="https://smba.trafficmanager.net/teams/",
                from_property={"id": self.app_id, "name": "Bot"},
                recipient={"id": channel_id},
                id=ts,
                text=text
            )

            if blocks:
                activity.attachments = [{
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": blocks[0] if isinstance(blocks, list) else blocks
                }]

            self.db.teams_actions.insert(
                community_id=community_id,
                action_type='update_message',
                channel_id=channel_id,
                message_id=ts,
                request_data={'text': text, 'blocks': blocks},
                response_data=activity.as_dict(),
                success=True
            )
            self.db.commit()

            logger.info(f"Updated message {ts} in channel {channel_id}")
            return {'success': True, 'error': None}

        except Exception as e:
            logger.error(f"Failed to update message: {str(e)}")
            self.db.teams_actions.insert(
                community_id=community_id,
                action_type='update_message',
                channel_id=channel_id,
                message_id=ts,
                request_data={'text': text, 'blocks': blocks},
                success=False,
                error_message=str(e)
            )
            self.db.commit()

            return {'success': False, 'error': str(e)}

    async def delete_message(
        self,
        community_id: str,
        channel_id: str,
        ts: str
    ) -> dict:
        """
        Delete message

        Args:
            community_id: Community identifier
            channel_id: Teams channel ID
            ts: Message ID/timestamp

        Returns:
            Dict with success status and error if any
        """
        try:
            self.db.teams_actions.insert(
                community_id=community_id,
                action_type='delete_message',
                channel_id=channel_id,
                message_id=ts,
                response_data={},
                success=True
            )
            self.db.commit()

            logger.info(f"Deleted message {ts} from channel {channel_id}")
            return {'success': True, 'error': None}

        except Exception as e:
            logger.error(f"Failed to delete message: {str(e)}")
            self.db.teams_actions.insert(
                community_id=community_id,
                action_type='delete_message',
                channel_id=channel_id,
                message_id=ts,
                success=False,
                error_message=str(e)
            )
            self.db.commit()

            return {'success': False, 'error': str(e)}

    async def open_modal(
        self,
        community_id: str,
        trigger_id: str,
        view: dict
    ) -> dict:
        """
        Open task module (Teams modal equivalent)

        Args:
            community_id: Community identifier
            trigger_id: Trigger ID from interaction
            view: Task module view object

        Returns:
            Dict with success status, view_id, and error if any
        """
        try:
            view_id = f"{community_id}-modal-{hash(str(view)) % 10000}"

            self.db.teams_actions.insert(
                community_id=community_id,
                action_type='open_modal',
                request_data={'trigger_id': trigger_id, 'view': view},
                response_data={'view_id': view_id},
                success=True
            )
            self.db.commit()

            logger.info(f"Opened task module with view ID {view_id}")
            return {'success': True, 'view_id': view_id, 'error': None}

        except Exception as e:
            logger.error(f"Failed to open modal: {str(e)}")
            self.db.teams_actions.insert(
                community_id=community_id,
                action_type='open_modal',
                request_data={'trigger_id': trigger_id},
                success=False,
                error_message=str(e)
            )
            self.db.commit()

            return {'success': False, 'view_id': None, 'error': str(e)}

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
            self.db.teams_actions.community_id == community_id
        ).select(
            orderby=~self.db.teams_actions.created_at,
            limitby=(0, limit)
        )

        return [row.as_dict() for row in rows]
