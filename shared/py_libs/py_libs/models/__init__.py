"""
Models module - Pydantic v2 base models for Waddles.

Provides reusable, validated data models for API requests and responses
with consistent configuration across all Waddles modules.

Core Features:
- WaddleBaseModel: Standard base with strict validation
- Reusable validators: String, numeric, date/time validators
- Common models: Pagination, Platform, Community, DateRange

Usage:
    from py_libs.models import (
        WaddleBaseModel,
        PaginationParams,
        CommunityIdRequired,
        Platform,
        DateTimeRange,
    )

    class EventRequest(CommunityIdRequired, DateTimeRange):
        title: str = Field(..., min_length=3, max_length=255)
        description: Optional[str] = None
        platform: Platform

Migration from pydantic.v1:
    # Before (pydantic v1 compatibility mode)
    from pydantic.v1 import BaseModel, Field, validator

    class OldModel(BaseModel):
        name: str

        @validator('name')
        def validate_name(cls, v):
            return v.strip()

        class Config:
            extra = 'forbid'

    # After (native pydantic v2)
    from py_libs.models import WaddleBaseModel
    from pydantic import Field, field_validator

    class NewModel(WaddleBaseModel):
        name: str

        @field_validator('name')
        @classmethod
        def validate_name(cls, v: str) -> str:
            return v.strip()
"""

# Base models
from .base import (
    ImmutableModel,
    WaddleBaseModel,
    WaddleRequestModel,
    WaddleResponseModel,
    model_to_dict,
    model_to_json,
)

# Reusable validators
from .validators import (
    # String validators
    validate_alphanumeric,
    validate_alphanumeric_with_extras,
    validate_email_format,
    validate_no_leading_trailing_whitespace,
    validate_not_empty_string,
    validate_slug,
    validate_url_format,
    validate_username_format,
    # Numeric validators
    validate_non_negative_int,
    validate_percentage,
    validate_positive_float,
    validate_positive_int,
    # Date/Time validators
    validate_date_not_in_future,
    validate_date_not_in_past,
    validate_timezone_string,
    # Cross-field validators
    validate_end_after_start,
    validate_optional_end_after_start,
)

# Platform models
from .platform import (
    CORE_PLATFORM_PATTERN,
    PLATFORM_PATTERN,
    CorePlatform,
    Platform,
    PlatformContext,
    PlatformOptional,
    PlatformRequired,
    is_valid_platform,
)

# Pagination models
from .pagination import (
    CursorPaginatedResponse,
    CursorPaginationParams,
    ExtendedPaginationParams,
    PaginatedResponse,
    PaginationParams,
    paginate_list,
)

# Community models
from .community import (
    CommunityContext,
    CommunityIdOptional,
    CommunityIdRequired,
    CommunityMemberRequest,
    CommunitySearchParams,
    UserContext,
)

# Date range models
from .date_range import (
    DateRange,
    DateRangeWithTimezone,
    DateTimeRange,
    DateTimeRangeStrict,
    FutureDateTimeRange,
    TimeSlot,
    get_duration_minutes,
    is_overlapping,
)

__all__ = [
    # Base models
    "WaddleBaseModel",
    "WaddleRequestModel",
    "WaddleResponseModel",
    "ImmutableModel",
    "model_to_dict",
    "model_to_json",
    # String validators
    "validate_not_empty_string",
    "validate_no_leading_trailing_whitespace",
    "validate_alphanumeric",
    "validate_alphanumeric_with_extras",
    "validate_slug",
    "validate_email_format",
    "validate_url_format",
    "validate_username_format",
    # Numeric validators
    "validate_positive_int",
    "validate_non_negative_int",
    "validate_positive_float",
    "validate_percentage",
    # Date/Time validators
    "validate_date_not_in_past",
    "validate_date_not_in_future",
    "validate_timezone_string",
    # Cross-field validators
    "validate_end_after_start",
    "validate_optional_end_after_start",
    # Platform
    "Platform",
    "CorePlatform",
    "PlatformContext",
    "PlatformRequired",
    "PlatformOptional",
    "PLATFORM_PATTERN",
    "CORE_PLATFORM_PATTERN",
    "is_valid_platform",
    # Pagination
    "PaginationParams",
    "ExtendedPaginationParams",
    "CursorPaginationParams",
    "PaginatedResponse",
    "CursorPaginatedResponse",
    "paginate_list",
    # Community
    "CommunityIdRequired",
    "CommunityIdOptional",
    "CommunityContext",
    "UserContext",
    "CommunityMemberRequest",
    "CommunitySearchParams",
    # Date range
    "DateRange",
    "DateTimeRange",
    "DateTimeRangeStrict",
    "TimeSlot",
    "FutureDateTimeRange",
    "DateRangeWithTimezone",
    "is_overlapping",
    "get_duration_minutes",
]
