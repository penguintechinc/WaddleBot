"""WaddleBot Welcome Interaction Module - Validation Models.

Pydantic model for the /welcome/check request body.
"""

from flask_core.sanitization import sanitize_input
from pydantic import BaseModel, Field


class WelcomeCheckRequest(BaseModel):
    """Validation model for POST /welcome/check."""

    community_id: int = Field(
        ...,
        gt=0,
        description="Community ID (must be positive integer)",
    )
    platform: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Source platform (twitch, discord, slack, ...)",
    )
    platform_user_id: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="User's platform-native ID",
    )
    platform_username: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Display name to greet if the user is welcomed",
    )
    tenant: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Tenant slug (mandatory JWT claim) for the AI flag check",
    )

    def sanitized_username(self) -> str:
        """Return `platform_username` with HTML/JS-unsafe content stripped."""
        return str(sanitize_input(self.platform_username))

    class Config:
        """Pydantic model config -- reject any field not declared above."""

        extra = 'forbid'
