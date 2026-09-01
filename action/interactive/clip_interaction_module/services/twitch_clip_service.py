"""HTTP client wrapping the action-twitch module's clip creation endpoint."""
import logging

import httpx

logger = logging.getLogger(__name__)


class TwitchClipService:
    """Proxies clip creation requests to the action-twitch module."""

    def __init__(self, config):
        self.config = config
        self.base_url = config.TWITCH_MODULE_URL

    async def create_clip(
        self,
        community_id: int,
        user_id: str,
        platform: str
    ) -> dict:
        """Create a Twitch clip via the action-twitch module.

        Args:
            community_id: The community ID.
            user_id: The user requesting the clip.
            platform: The platform identifier.

        Returns:
            Response dict with clip data, or error dict on failure.
        """
        url = f"{self.base_url}/api/v1/clips/create"
        payload = {
            "community_id": community_id,
            "user_id": user_id,
            "platform": platform,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                return response.json()

        except httpx.TimeoutException:
            logger.error(
                "Timeout creating clip for community %s", community_id
            )
            return {"error": "Clip creation timed out", "success": False}

        except httpx.HTTPError as exc:
            logger.error("HTTP error creating clip: %s", exc)
            return {
                "error": f"Clip creation failed: {exc}",
                "success": False,
            }
