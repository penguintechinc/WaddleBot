"""AI Client for Personalized Welcomes.

ai_interaction_module runs as its own container with its own Dockerfile
build context (only its own directory + libs/flask_core get COPY'd in --
see its Dockerfile), so this module cannot import
`ai_interaction_module.services.ai_service.AIService` directly. Instead
`AIInteractionClient` reproduces the exact
`generate_response(message_content, message_type, user_id, platform,
context) -> Optional[str]` signature from that module's `AIProvider`
Protocol and satisfies it over HTTP, against the OpenAI-compatible
`/api/v1/ai/chat/completions` endpoint it already exposes.

Any failure (network error, timeout, non-200, malformed body) returns
None rather than raising -- `welcome_service.build_welcome` treats None as
"fall back to the template", per the requirement that an AI hiccup must
never leave a user un-welcomed.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Protocol

import aiohttp

logger = logging.getLogger(__name__)


class AIResponder(Protocol):
    """The interface welcome_service depends on -- swappable for tests."""

    async def generate_response(
        self,
        message_content: str,
        message_type: str,
        user_id: str,
        platform: str,
        context: dict[str, Any],
    ) -> str | None:
        """Generate an AI response, or None if generation failed."""
        ...


@dataclass(slots=True)
class AIInteractionClient:
    """HTTP adapter satisfying `AIResponder` against ai_interaction_module."""

    base_url: str
    api_key: str = ''
    timeout_seconds: float = 5.0

    async def generate_response(
        self,
        message_content: str,
        message_type: str,
        user_id: str,
        platform: str,
        context: dict[str, Any],
    ) -> str | None:
        """Adapt the call into an OpenAI-compatible chat/completions request.

        Args:
            message_content: Prompt describing the greeting to generate.
            message_type: Kept for interface parity with AIProvider; unused
                by the chat/completions endpoint.
            user_id: Platform user ID of the person being welcomed.
            platform: Source platform (twitch, discord, slack, ...).
            context: Additional context merged into the prompt metadata.

        Returns:
            Generated greeting text, or None on any failure.

        """
        headers = {'X-API-Key': self.api_key} if self.api_key else {}
        payload = {
            'messages': [{'role': 'user', 'content': message_content}],
            'metadata': {
                'message_type': message_type,
                'user_id': user_id,
                'platform': platform,
                'context': context,
            },
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/v1/ai/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout_seconds),
                ) as response:
                    if response.status != 200:
                        logger.warning(
                            "AI welcome generation failed: status=%s",
                            response.status,
                        )
                        return None

                    body = await response.json()
                    data = body.get('data', body)
                    choices = data.get('choices') or []
                    if not choices:
                        return None

                    text = choices[0].get('message', {}).get('content')
                    return text or None

        except aiohttp.ClientError as exc:
            logger.warning(f"AI welcome generation connection error: {exc}")
            return None
        except Exception as exc:  # noqa: BLE001 - never crash the welcome path
            logger.warning(f"AI welcome generation error: {exc}")
            return None
