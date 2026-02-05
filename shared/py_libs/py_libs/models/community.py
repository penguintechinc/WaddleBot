"""
Community-related models.

Provides models for community identification and context that are
used across all Waddles modules for multi-tenant operations.
"""

from __future__ import annotations

from typing import Optional

from pydantic import Field, field_validator

from .base import WaddleRequestModel
from .platform import Platform


class CommunityIdRequired(WaddleRequestModel):
    """
    Base model requiring a valid community_id.

    All community-scoped operations should inherit from this model
    to ensure community_id is always validated.

    Usage:
        class EventRequest(CommunityIdRequired):
            title: str = Field(..., min_length=3)
            description: Optional[str] = None
    """

    community_id: int = Field(
        ...,
        gt=0,
        description="Community ID (must be positive integer)"
    )


class CommunityIdOptional(WaddleRequestModel):
    """
    Base model with optional community_id.

    Used for queries that may operate across communities or
    within a specific community.
    """

    community_id: Optional[int] = Field(
        None,
        gt=0,
        description="Optional community ID filter"
    )


class CommunityContext(WaddleRequestModel):
    """
    Full community context for requests.

    Includes community identification along with platform-specific
    details for complete request context.
    """

    community_id: int = Field(
        ...,
        gt=0,
        description="Community ID"
    )
    platform: Platform = Field(
        ...,
        description="Source platform"
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

    @field_validator("entity_id", "channel_id", mode="before")
    @classmethod
    def strip_and_empty_to_none(cls, v: Optional[str]) -> Optional[str]:
        """Strip whitespace and convert empty strings to None."""
        if v is not None:
            v = v.strip()
            return v if v else None
        return v


class UserContext(WaddleRequestModel):
    """
    User context for authenticated requests.

    Combines community and user identification for
    authorization decisions.
    """

    community_id: int = Field(
        ...,
        gt=0,
        description="Community ID"
    )
    user_id: Optional[int] = Field(
        None,
        gt=0,
        description="Internal user ID (if authenticated)"
    )
    username: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Username"
    )
    platform: Platform = Field(
        ...,
        description="Source platform"
    )
    platform_user_id: Optional[str] = Field(
        None,
        max_length=255,
        description="Platform-specific user ID"
    )
    roles: list[str] = Field(
        default_factory=list,
        description="User roles in the community"
    )

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate username is not empty after stripping."""
        v = v.strip()
        if not v:
            raise ValueError("username cannot be empty")
        return v

    def has_role(self, role: str) -> bool:
        """Check if user has a specific role."""
        return role in self.roles

    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return "admin" in self.roles or "owner" in self.roles

    def is_moderator(self) -> bool:
        """Check if user has moderator role."""
        return self.is_admin() or "moderator" in self.roles


class CommunityMemberRequest(CommunityIdRequired):
    """
    Request model for community member operations.

    Used when operating on a specific member within a community.
    """

    username: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Member username"
    )
    platform_user_id: Optional[str] = Field(
        None,
        max_length=255,
        description="Platform user ID"
    )

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate username is not empty after stripping."""
        v = v.strip()
        if not v:
            raise ValueError("username cannot be empty")
        return v


class CommunitySearchParams(WaddleRequestModel):
    """
    Search parameters for community-scoped queries.

    Extends basic pagination with community-specific filtering.
    """

    community_id: int = Field(
        ...,
        gt=0,
        description="Community ID"
    )
    search: Optional[str] = Field(
        None,
        max_length=255,
        description="Search query text"
    )
    platform: Optional[Platform] = Field(
        None,
        description="Filter by platform"
    )
    limit: int = Field(
        default=50,
        ge=1,
        le=100,
        description="Number of items to return"
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Number of items to skip"
    )

    @field_validator("search", mode="before")
    @classmethod
    def strip_search(cls, v: Optional[str]) -> Optional[str]:
        """Strip search query and convert empty to None."""
        if v is not None:
            v = v.strip()
            return v if v else None
        return v


__all__ = [
    "CommunityIdRequired",
    "CommunityIdOptional",
    "CommunityContext",
    "UserContext",
    "CommunityMemberRequest",
    "CommunitySearchParams",
]
