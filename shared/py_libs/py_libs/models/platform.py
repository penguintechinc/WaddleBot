"""
Platform enumeration and validation models.

Provides a centralized, consistent definition of supported platforms
across all Waddles modules.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import Field, field_validator

from .base import WaddleRequestModel


class Platform(str, Enum):
    """
    Supported chat platforms.

    Using str Enum allows direct JSON serialization and comparison
    with string values.
    """

    TWITCH = "twitch"
    DISCORD = "discord"
    SLACK = "slack"
    KICK = "kick"
    YOUTUBE = "youtube"

    @classmethod
    def from_string(cls, value: str) -> "Platform":
        """
        Convert string to Platform enum.

        Args:
            value: String platform name (case-insensitive)

        Returns:
            Platform enum value

        Raises:
            ValueError: If platform is not supported
        """
        normalized = value.lower().strip()
        try:
            return cls(normalized)
        except ValueError:
            valid = ", ".join(p.value for p in cls)
            raise ValueError(f"Invalid platform '{value}'. Valid platforms: {valid}")

    @classmethod
    def values(cls) -> list[str]:
        """Return list of valid platform string values."""
        return [p.value for p in cls]


# Commonly used subset (excludes newer/experimental platforms)
class CorePlatform(str, Enum):
    """Core platforms with full support."""

    TWITCH = "twitch"
    DISCORD = "discord"
    SLACK = "slack"

    @classmethod
    def values(cls) -> list[str]:
        """Return list of valid platform string values."""
        return [p.value for p in cls]


class PlatformContext(WaddleRequestModel):
    """
    Context model for platform-specific requests.

    Used to identify the source platform of a request along with
    platform-specific identifiers.
    """

    platform: Platform = Field(
        ...,
        description="Source platform for the request"
    )
    platform_user_id: Optional[str] = Field(
        None,
        max_length=255,
        description="Platform-specific user ID"
    )
    entity_id: Optional[str] = Field(
        None,
        max_length=255,
        description="Platform entity ID (server/channel)"
    )
    channel_id: Optional[str] = Field(
        None,
        max_length=255,
        description="Platform channel ID"
    )

    @field_validator("platform_user_id", "entity_id", "channel_id", mode="before")
    @classmethod
    def strip_whitespace(cls, v: Optional[str]) -> Optional[str]:
        """Strip whitespace from optional string fields."""
        if v is not None:
            v = v.strip()
            return v if v else None
        return v


class PlatformRequired(WaddleRequestModel):
    """
    Base model requiring a valid platform.

    Inherit from this model for endpoints that require platform specification.
    """

    platform: Platform = Field(
        ...,
        description="Platform name"
    )


class PlatformOptional(WaddleRequestModel):
    """
    Base model with optional platform.

    Useful for queries that may or may not filter by platform.
    """

    platform: Optional[Platform] = Field(
        None,
        description="Optional platform filter"
    )


# Regex pattern for validation (for use in Field definitions)
PLATFORM_PATTERN = r"^(twitch|discord|slack|kick|youtube)$"
CORE_PLATFORM_PATTERN = r"^(twitch|discord|slack)$"


def is_valid_platform(value: str) -> bool:
    """
    Check if a string is a valid platform.

    Args:
        value: String to check

    Returns:
        True if valid platform, False otherwise
    """
    try:
        Platform(value.lower().strip())
        return True
    except ValueError:
        return False


__all__ = [
    "Platform",
    "CorePlatform",
    "PlatformContext",
    "PlatformRequired",
    "PlatformOptional",
    "PLATFORM_PATTERN",
    "CORE_PLATFORM_PATTERN",
    "is_valid_platform",
]
