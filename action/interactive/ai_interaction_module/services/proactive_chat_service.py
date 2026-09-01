"""
Proactive Chat Service
=======================
Determines whether the AI should respond to a chat message
and generates the response. Called by the proactive-chat endpoint.
"""
import random
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ProactiveChatService:
    """Handles AI proactive chat response logic."""

    # System prompt for community chat context (different from research prompt)
    CHAT_SYSTEM_PROMPT = (
        "You are a friendly community assistant in a live chat. "
        "Keep responses brief (1-2 sentences), conversational, and relevant to what was said. "
        "Do not ask multiple questions. Do not be preachy. Match the casual tone of the chat."
    )

    def __init__(self, ai_service, chatter_config_service, chatter_rate_limiter, logger_instance=None):
        self.ai_service = ai_service
        self.config_service = chatter_config_service
        self.rate_limiter = chatter_rate_limiter
        self.logger = logger_instance or logger

    async def should_respond(
        self,
        community_id: int,
        user_id: str,
        message: str,
        config: dict
    ) -> bool:
        """
        Determine if the AI should respond to this message.
        Checks: message length, probability roll, community rate limit, user rate limit.
        """
        # Check message length
        if len(message) < config.get('min_message_length', 10):
            return False

        # Probability roll
        if random.random() >= config.get('response_probability', 0.30):
            return False

        # Community rate limit
        community_result = await self.rate_limiter.check_and_increment_community(
            community_id=community_id,
            window_seconds=config.get('window_seconds', 600),
            max_count=config.get('max_responses_per_window', 10),
        )
        if not community_result.allowed:
            self.logger.audit(
                action="ai_chatter_rate_limited",
                community=str(community_id),
                user=user_id,
                result="COMMUNITY_LIMIT",
            )
            return False

        # User rate limit
        user_result = await self.rate_limiter.check_and_increment_user(
            community_id=community_id,
            user_id=user_id,
            window_seconds=config.get('window_seconds', 600),
            max_count=config.get('max_per_user_per_window', 2),
        )
        if not user_result.allowed:
            self.logger.audit(
                action="ai_chatter_rate_limited",
                community=str(community_id),
                user=user_id,
                result="USER_LIMIT",
            )
            return False

        return True

    async def generate_response(
        self,
        message: str,
        community_id: int,
        user_id: str,
        session_id: str,
    ) -> Optional[str]:
        """
        Generate an AI response for a chat message.
        Uses a conversational prompt rather than research-focused prompt.
        """
        try:
            response = await self.ai_service.generate_response(
                message_content=message,
                message_type='chatMessage',
                user_id=user_id,
                platform='proactive',
                context={
                    'trigger_type': 'proactive_chat',
                    'community_id': community_id,
                    'session_id': session_id,
                    'system_prompt_override': self.CHAT_SYSTEM_PROMPT,
                }
            )
            return response
        except Exception as e:
            self.logger.error(
                f"Proactive chat response generation failed: {e}",
                community_id=community_id,
                user_id=user_id,
            )
            return None
