"""
Calendar Interaction Module - Pydantic Validation Models

Provides comprehensive input validation for all Calendar API endpoints using Pydantic.
Prevents 500 errors from unsafe int() conversions and provides detailed validation errors.

Usage:
    from validation_models import EventCreateRequest, EventSearchParams
    from flask_core.validation import validate_json, validate_query

    @calendar_bp.route('/<int:community_id>/events', methods=['POST'])
    @validate_json(EventCreateRequest)
    async def create_event(validated_data: EventCreateRequest):
        event = await calendar_service.create_event(validated_data.dict(), user_context)
        return success_response(event, status_code=201)
"""

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from typing import Optional, List
from datetime import datetime
import re


# ============================================================================
# Event Management Validation Models
# ============================================================================

class EventCreateRequest(BaseModel):
    """
    Validation model for creating new events.

    Prevents 500 errors from invalid data types and ensures data integrity.
    """
    community_id: int = Field(..., gt=0, description="Community ID (must be positive)")
    title: str = Field(
        ...,
        min_length=3,
        max_length=255,
        description="Event title (3-255 characters)"
    )
    description: Optional[str] = Field(
        None,
        max_length=5000,
        description="Event description (max 5000 characters)"
    )
    event_date: datetime = Field(
        ...,
        description="Event date and time (ISO 8601 format)"
    )
    end_date: Optional[datetime] = Field(
        None,
        description="Event end date and time (ISO 8601 format)"
    )
    timezone: Optional[str] = Field(
        default="UTC",
        max_length=50,
        description="Event timezone (e.g., America/New_York)"
    )
    location: Optional[str] = Field(
        None,
        max_length=500,
        description="Event location or virtual meeting link"
    )
    platform: str = Field(
        ...,
        pattern=r'^(twitch|discord|slack)$',
        description="Platform where event was created (twitch, discord, slack)"
    )
    entity_id: Optional[str] = Field(
        None,
        max_length=255,
        description="Platform channel/server ID"
    )
    channel_id: Optional[str] = Field(
        None,
        max_length=255,
        description="Platform channel ID for event"
    )
    created_by_username: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Username of event creator"
    )
    created_by_platform_user_id: Optional[str] = Field(
        None,
        max_length=255,
        description="Platform user ID of creator"
    )
    requires_approval: Optional[bool] = Field(
        default=False,
        description="Whether event requires admin approval"
    )
    rsvp_enabled: Optional[bool] = Field(
        default=True,
        description="Enable RSVP functionality"
    )
    rsvp_deadline: Optional[datetime] = Field(
        None,
        description="RSVP deadline (ISO 8601 format)"
    )
    max_attendees: Optional[int] = Field(
        None,
        ge=1,
        description="Maximum number of attendees (must be positive)"
    )
    waitlist_enabled: Optional[bool] = Field(
        default=False,
        description="Enable waitlist when max attendees reached"
    )
    recurring_rule: Optional[str] = Field(
        None,
        max_length=200,
        description="Recurring rule pattern (RRULE format)"
    )
    is_recurring: Optional[bool] = Field(
        default=False,
        description="Whether event is recurring"
    )
    recurring_pattern: Optional[str] = Field(
        None,
        max_length=50,
        description="Recurring pattern (daily, weekly, monthly)"
    )
    recurring_days: Optional[List[int]] = Field(
        None,
        description="Days of week for recurring events (0=Sunday, 6=Saturday)"
    )
    recurring_end_date: Optional[datetime] = Field(
        None,
        description="End date for recurring events"
    )
    category_id: Optional[int] = Field(
        None,
        gt=0,
        description="Event category ID"
    )
    tags: Optional[List[str]] = Field(
        default_factory=list,
        description="Event tags for categorization"
    )
    cover_image_url: Optional[str] = Field(
        None,
        max_length=1000,
        description="URL to event cover image"
    )

    @field_validator('title', 'created_by_username')
    @classmethod
    def validate_non_empty_string(cls, v, info):
        """Ensure strings are not just whitespace."""
        if v and not v.strip():
            raise ValueError(f'{info.field_name} cannot be empty or whitespace only')
        return v.strip() if v else v

    @field_validator('recurring_days')
    @classmethod
    def validate_recurring_days(cls, v):
        """Ensure recurring days are valid (0-6)."""
        if v:
            for day in v:
                if not isinstance(day, int) or day < 0 or day > 6:
                    raise ValueError('recurring_days must contain integers 0-6 (0=Sunday, 6=Saturday)')
        return v

    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v):
        """Validate tag format and length."""
        if v:
            if len(v) > 20:
                raise ValueError('Maximum 20 tags allowed')
            for tag in v:
                if not isinstance(tag, str) or len(tag) > 50:
                    raise ValueError('Each tag must be a string with max 50 characters')
        return v

    @field_validator('cover_image_url')
    @classmethod
    def validate_image_url(cls, v):
        """Validate image URL format."""
        if v:
            url_pattern = r'^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$'
            if not re.match(url_pattern, v):
                raise ValueError('cover_image_url must be a valid URL starting with http:// or https://')
        return v

    @model_validator(mode='after')
    def validate_dates(self):
        """Ensure end_date, rsvp_deadline, and recurring_end_date are valid."""
        if self.end_date and self.event_date:
            if self.end_date <= self.event_date:
                raise ValueError('end_date must be after event_date')
        if self.rsvp_deadline and self.event_date:
            if self.rsvp_deadline >= self.event_date:
                raise ValueError('rsvp_deadline must be before event_date')
        if self.recurring_end_date and self.event_date:
            if self.recurring_end_date <= self.event_date:
                raise ValueError('recurring_end_date must be after event_date')
        return self

    model_config = ConfigDict(extra='forbid')


class EventSearchParams(BaseModel):
    """
    Validation model for event search/list query parameters.

    CRITICAL FIX: Replaces unsafe int() conversions that caused 500 errors
    on lines 116-117 of app.py when non-numeric values were passed.
    """
    community_id: Optional[int] = Field(None, gt=0, description="Community ID filter")
    platform: Optional[str] = Field(
        None,
        pattern=r'^(twitch|discord|slack)$',
        description="Platform filter (twitch, discord, slack)"
    )
    status: Optional[str] = Field(
        None,
        pattern=r'^(pending|approved|rejected|cancelled)$',
        description="Event status filter"
    )
    date_from: Optional[datetime] = Field(
        None,
        description="Start date filter (ISO 8601)"
    )
    date_to: Optional[datetime] = Field(
        None,
        description="End date filter (ISO 8601)"
    )
    category_id: Optional[int] = Field(
        None,
        gt=0,
        description="Category ID filter"
    )
    entity_id: Optional[str] = Field(
        None,
        max_length=255,
        description="Entity ID filter"
    )
    tags: Optional[List[str]] = Field(
        default_factory=list,
        description="Tags filter (matches any)"
    )
    limit: int = Field(
        default=50,
        ge=1,
        le=100,
        description="Number of results (1-100)"
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Offset for pagination"
    )
    include_attendees: Optional[bool] = Field(
        default=False,
        description="Include attendee information"
    )

    @model_validator(mode='after')
    def validate_date_range(self):
        """Ensure date_to is after date_from if both provided."""
        if self.date_to and self.date_from:
            if self.date_to <= self.date_from:
                raise ValueError('date_to must be after date_from')
        return self

    model_config = ConfigDict(extra='forbid')


class EventUpdateRequest(BaseModel):
    """
    Validation model for updating existing events.

    All fields are optional to allow partial updates.
    """
    title: Optional[str] = Field(
        None,
        min_length=3,
        max_length=255,
        description="Event title (3-255 characters)"
    )
    description: Optional[str] = Field(
        None,
        max_length=5000,
        description="Event description (max 5000 characters)"
    )
    event_date: Optional[datetime] = Field(
        None,
        description="Event date and time (ISO 8601 format)"
    )
    end_date: Optional[datetime] = Field(
        None,
        description="Event end date and time (ISO 8601 format)"
    )
    timezone: Optional[str] = Field(
        None,
        max_length=50,
        description="Event timezone"
    )
    location: Optional[str] = Field(
        None,
        max_length=500,
        description="Event location or virtual meeting link"
    )
    status: Optional[str] = Field(
        None,
        pattern=r'^(pending|approved|rejected|cancelled)$',
        description="Event status"
    )
    rsvp_enabled: Optional[bool] = Field(
        None,
        description="Enable RSVP functionality"
    )
    rsvp_deadline: Optional[datetime] = Field(
        None,
        description="RSVP deadline (ISO 8601 format)"
    )
    max_attendees: Optional[int] = Field(
        None,
        ge=1,
        description="Maximum number of attendees"
    )
    waitlist_enabled: Optional[bool] = Field(
        None,
        description="Enable waitlist when max attendees reached"
    )
    category_id: Optional[int] = Field(
        None,
        gt=0,
        description="Event category ID"
    )
    tags: Optional[List[str]] = Field(
        None,
        description="Event tags for categorization"
    )
    cover_image_url: Optional[str] = Field(
        None,
        max_length=1000,
        description="URL to event cover image"
    )

    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        """Ensure title is not just whitespace."""
        if v and not v.strip():
            raise ValueError('title cannot be empty or whitespace only')
        return v.strip() if v else v

    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v):
        """Validate tag format and length."""
        if v:
            if len(v) > 20:
                raise ValueError('Maximum 20 tags allowed')
            for tag in v:
                if not isinstance(tag, str) or len(tag) > 50:
                    raise ValueError('Each tag must be a string with max 50 characters')
        return v

    @field_validator('cover_image_url')
    @classmethod
    def validate_image_url(cls, v):
        """Validate image URL format."""
        if v:
            url_pattern = r'^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$'
            if not re.match(url_pattern, v):
                raise ValueError('cover_image_url must be a valid URL starting with http:// or https://')
        return v

    @model_validator(mode='after')
    def validate_end_date(self):
        """Ensure end_date is after event_date."""
        if self.end_date and self.event_date:
            if self.end_date <= self.event_date:
                raise ValueError('end_date must be after event_date')
        return self

    model_config = ConfigDict(extra='forbid')


class EventApprovalRequest(BaseModel):
    """
    Validation model for event approval/rejection actions.
    """
    status: str = Field(
        ...,
        pattern=r'^(approved|rejected)$',
        description="Approval status (approved or rejected)"
    )
    notes: Optional[str] = Field(
        None,
        max_length=1000,
        description="Admin notes for approval/rejection"
    )
    reason: Optional[str] = Field(
        None,
        max_length=1000,
        description="Reason for rejection (deprecated, use notes)"
    )

    model_config = ConfigDict(extra='forbid')


# ============================================================================
# RSVP Validation Models
# ============================================================================

class RSVPRequest(BaseModel):
    """
    Validation model for RSVP actions.
    """
    status: str = Field(
        ...,
        pattern=r'^(yes|no|maybe)$',
        description="RSVP status (yes, no, maybe)"
    )
    guest_count: Optional[int] = Field(
        default=0,
        ge=0,
        le=10,
        description="Number of additional guests (0-10)"
    )
    note: Optional[str] = Field(
        None,
        max_length=500,
        description="User note for RSVP"
    )

    model_config = ConfigDict(extra='forbid')


class AttendeeSearchParams(BaseModel):
    """
    Validation model for attendee list query parameters.
    """
    status: Optional[str] = Field(
        None,
        pattern=r'^(yes|no|maybe)$',
        description="Filter by RSVP status"
    )

    model_config = ConfigDict(extra='forbid')


# ============================================================================
# Search and Discovery Validation Models
# ============================================================================

class EventFullTextSearchParams(BaseModel):
    """
    Validation model for full-text event search.
    """
    q: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Search query (1-200 characters)"
    )
    category_id: Optional[int] = Field(
        None,
        gt=0,
        description="Category ID filter"
    )
    date_from: Optional[datetime] = Field(
        None,
        description="Start date filter"
    )
    date_to: Optional[datetime] = Field(
        None,
        description="End date filter"
    )
    limit: int = Field(
        default=50,
        ge=1,
        le=100,
        description="Number of results"
    )

    @field_validator('q')
    @classmethod
    def validate_query(cls, v):
        """Ensure query is not just whitespace."""
        if not v.strip():
            raise ValueError('search query cannot be empty or whitespace only')
        return v.strip()

    @model_validator(mode='after')
    def validate_date_range(self):
        """Ensure date_to is after date_from."""
        if self.date_to and self.date_from:
            if self.date_to <= self.date_from:
                raise ValueError('date_to must be after date_from')
        return self

    model_config = ConfigDict(extra='forbid')


class UpcomingEventsParams(BaseModel):
    """
    Validation model for upcoming events query.
    """
    limit: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Number of events to return"
    )
    entity_id: Optional[str] = Field(
        None,
        max_length=255,
        description="Filter by entity ID"
    )

    model_config = ConfigDict(extra='forbid')


# ============================================================================
# Configuration Validation Models
# ============================================================================

class PermissionsConfigRequest(BaseModel):
    """
    Validation model for calendar permissions configuration.
    """
    allow_member_create: Optional[bool] = Field(
        None,
        description="Allow members to create events"
    )
    require_approval: Optional[bool] = Field(
        None,
        description="Require admin approval for events"
    )
    allow_member_edit_own: Optional[bool] = Field(
        None,
        description="Allow members to edit their own events"
    )
    allow_member_delete_own: Optional[bool] = Field(
        None,
        description="Allow members to delete their own events"
    )
    allow_rsvp: Optional[bool] = Field(
        None,
        description="Enable RSVP functionality"
    )
    max_events_per_member: Optional[int] = Field(
        None,
        ge=0,
        le=100,
        description="Maximum events per member (0=unlimited)"
    )

    model_config = ConfigDict(extra='forbid')


class CategoryCreateRequest(BaseModel):
    """
    Validation model for creating event categories.
    """
    name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Category name (2-100 characters)"
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="Category description"
    )
    color: Optional[str] = Field(
        None,
        pattern=r'^#[0-9A-Fa-f]{6}$',
        description="Category color (hex format: #RRGGBB)"
    )
    icon: Optional[str] = Field(
        None,
        max_length=50,
        description="Category icon identifier"
    )
    display_order: Optional[int] = Field(
        default=100,
        ge=0,
        description="Display order for sorting"
    )

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        """Ensure name is not just whitespace."""
        if not v.strip():
            raise ValueError('category name cannot be empty or whitespace only')
        return v.strip()

    model_config = ConfigDict(extra='forbid')


# ============================================================================
# Context Management Validation Models
# ============================================================================

class ContextSwitchRequest(BaseModel):
    """
    Validation model for switching community context.
    """
    user_id: Optional[str] = Field(
        default="anonymous",
        max_length=255,
        description="User ID"
    )
    community_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Community name to switch to"
    )

    @field_validator('community_name')
    @classmethod
    def validate_community_name(cls, v):
        """Ensure community name is not just whitespace."""
        if not v.strip():
            raise ValueError('community_name cannot be empty or whitespace only')
        return v.strip()

    model_config = ConfigDict(extra='forbid')


# ============================================================================
# Ticketing Validation Models
# ============================================================================

class TicketTypeCreateRequest(BaseModel):
    """
    Validation model for creating ticket types.
    """
    name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Ticket type name (2-100 characters)"
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="Ticket type description"
    )
    max_quantity: Optional[int] = Field(
        None,
        gt=0,
        le=100000,
        description="Maximum tickets available (null=unlimited)"
    )
    price_cents: int = Field(
        default=0,
        ge=0,
        le=10000000,
        description="Price in cents (0=free, max $100,000)"
    )
    currency: str = Field(
        default='USD',
        pattern=r'^[A-Z]{3}$',
        description="Currency code (ISO 4217)"
    )
    sales_start: Optional[datetime] = Field(
        None,
        description="When ticket sales start"
    )
    sales_end: Optional[datetime] = Field(
        None,
        description="When ticket sales end"
    )
    display_order: int = Field(
        default=0,
        ge=0,
        le=1000,
        description="Display order (lower=first)"
    )

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        """Ensure name is not just whitespace."""
        if not v.strip():
            raise ValueError('name cannot be empty or whitespace only')
        return v.strip()

    @model_validator(mode='after')
    def validate_sales_end(self):
        """Ensure sales_end is after sales_start."""
        if self.sales_end and self.sales_start:
            if self.sales_end <= self.sales_start:
                raise ValueError('sales_end must be after sales_start')
        return self

    model_config = ConfigDict(extra='forbid')


class TicketTypeUpdateRequest(BaseModel):
    """
    Validation model for updating ticket types.
    """
    name: Optional[str] = Field(
        None,
        min_length=2,
        max_length=100,
        description="Ticket type name"
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="Ticket type description"
    )
    max_quantity: Optional[int] = Field(
        None,
        gt=0,
        le=100000,
        description="Maximum tickets available"
    )
    price_cents: Optional[int] = Field(
        None,
        ge=0,
        le=10000000,
        description="Price in cents"
    )
    currency: Optional[str] = Field(
        None,
        pattern=r'^[A-Z]{3}$',
        description="Currency code"
    )
    sales_start: Optional[datetime] = Field(
        None,
        description="When ticket sales start"
    )
    sales_end: Optional[datetime] = Field(
        None,
        description="When ticket sales end"
    )
    display_order: Optional[int] = Field(
        None,
        ge=0,
        le=1000,
        description="Display order"
    )
    is_visible: Optional[bool] = Field(
        None,
        description="Whether ticket type is visible to users"
    )
    is_active: Optional[bool] = Field(
        None,
        description="Whether ticket type is active"
    )

    model_config = ConfigDict(extra='forbid')


class TicketCreateRequest(BaseModel):
    """
    Validation model for creating tickets (admin manual creation).
    """
    ticket_type_id: Optional[int] = Field(
        None,
        gt=0,
        description="Ticket type ID"
    )
    holder_name: Optional[str] = Field(
        None,
        max_length=255,
        description="Ticket holder name"
    )
    holder_email: Optional[str] = Field(
        None,
        max_length=255,
        description="Ticket holder email"
    )
    platform: str = Field(
        ...,
        pattern=r'^(twitch|discord|slack|hub)$',
        description="Platform (twitch, discord, slack, hub)"
    )
    platform_user_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Platform user ID"
    )
    username: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Username"
    )
    guest_count: int = Field(
        default=0,
        ge=0,
        le=10,
        description="Number of additional guests"
    )

    @field_validator('holder_email')
    @classmethod
    def validate_email(cls, v):
        """Validate email format if provided."""
        if v:
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, v):
                raise ValueError('Invalid email format')
        return v

    model_config = ConfigDict(extra='forbid')


class TicketVerifyRequest(BaseModel):
    """
    Validation model for ticket verification/check-in via QR code.
    """
    ticket_code: str = Field(
        ...,
        min_length=64,
        max_length=64,
        pattern=r'^[a-fA-F0-9]{64}$',
        description="64-character hex ticket code"
    )
    perform_checkin: bool = Field(
        default=True,
        description="Whether to perform check-in or just verify"
    )
    location: Optional[str] = Field(
        None,
        max_length=255,
        description="Check-in location"
    )

    model_config = ConfigDict(extra='forbid')


class TicketCheckInRequest(BaseModel):
    """
    Validation model for manual ticket check-in.
    Supports check-in by ticket_code, ticket_id, or holder search.
    """
    ticket_code: Optional[str] = Field(
        None,
        min_length=64,
        max_length=64,
        pattern=r'^[a-fA-F0-9]{64}$',
        description="64-character hex ticket code"
    )
    ticket_id: Optional[int] = Field(
        None,
        gt=0,
        description="Ticket ID"
    )
    holder_name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=255,
        description="Search by holder name"
    )
    location: Optional[str] = Field(
        None,
        max_length=255,
        description="Check-in location"
    )
    notes: Optional[str] = Field(
        None,
        max_length=500,
        description="Check-in notes"
    )

    @model_validator(mode='after')
    def validate_has_identifier(self):
        """Ensure at least one identifier is provided."""
        if not self.ticket_id and not self.ticket_code and not self.holder_name:
            raise ValueError(
                'At least one of ticket_code, ticket_id, or holder_name must be provided'
            )
        return self

    model_config = ConfigDict(extra='forbid')


class TicketUndoCheckInRequest(BaseModel):
    """
    Validation model for undoing a ticket check-in.
    """
    ticket_id: int = Field(
        ...,
        gt=0,
        description="Ticket ID"
    )
    reason: Optional[str] = Field(
        None,
        max_length=500,
        description="Reason for undoing check-in"
    )

    model_config = ConfigDict(extra='forbid')


class TicketTransferRequest(BaseModel):
    """
    Validation model for admin-only ticket transfer.
    """
    new_holder_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="New holder name"
    )
    new_holder_email: Optional[str] = Field(
        None,
        max_length=255,
        description="New holder email"
    )
    new_holder_platform: str = Field(
        ...,
        pattern=r'^(twitch|discord|slack|hub)$',
        description="New holder platform"
    )
    new_holder_platform_user_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="New holder platform user ID"
    )
    new_holder_username: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="New holder username"
    )
    new_holder_user_id: Optional[int] = Field(
        None,
        gt=0,
        description="New holder hub user ID"
    )
    notes: Optional[str] = Field(
        None,
        max_length=500,
        description="Transfer notes"
    )

    @field_validator('new_holder_email')
    @classmethod
    def validate_email(cls, v):
        """Validate email format if provided."""
        if v:
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, v):
                raise ValueError('Invalid email format')
        return v

    model_config = ConfigDict(extra='forbid')


class TicketCancelRequest(BaseModel):
    """
    Validation model for ticket cancellation.
    """
    reason: Optional[str] = Field(
        None,
        max_length=500,
        description="Cancellation reason"
    )

    model_config = ConfigDict(extra='forbid')


class TicketSearchParams(BaseModel):
    """
    Validation model for ticket list query parameters.
    """
    status: Optional[str] = Field(
        None,
        pattern=r'^(valid|checked_in|cancelled|expired|refunded|transferred)$',
        description="Filter by ticket status"
    )
    is_checked_in: Optional[bool] = Field(
        None,
        description="Filter by check-in status"
    )
    ticket_type_id: Optional[int] = Field(
        None,
        gt=0,
        description="Filter by ticket type"
    )
    search: Optional[str] = Field(
        None,
        max_length=100,
        description="Search by holder name/email/username"
    )
    limit: int = Field(
        default=50,
        ge=1,
        le=100,
        description="Number of results (1-100)"
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Pagination offset"
    )

    model_config = ConfigDict(extra='forbid')


class CheckInLogParams(BaseModel):
    """
    Validation model for check-in log query parameters.
    """
    success_only: bool = Field(
        default=False,
        description="Filter to successful check-ins only"
    )
    from_date: Optional[datetime] = Field(
        None,
        description="Filter logs from this date"
    )
    to_date: Optional[datetime] = Field(
        None,
        description="Filter logs until this date"
    )
    limit: int = Field(
        default=50,
        ge=1,
        le=100,
        description="Number of results (1-100)"
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Pagination offset"
    )

    @model_validator(mode='after')
    def validate_date_range(self):
        """Ensure to_date is after from_date."""
        if self.to_date and self.from_date:
            if self.to_date <= self.from_date:
                raise ValueError('to_date must be after from_date')
        return self

    model_config = ConfigDict(extra='forbid')


class TicketingConfigRequest(BaseModel):
    """
    Validation model for enabling/configuring ticketing on an event.
    """
    ticketing_enabled: Optional[bool] = Field(
        None,
        description="Enable/disable ticketing"
    )
    require_ticket: Optional[bool] = Field(
        None,
        description="Whether ticket is required to attend"
    )
    is_paid_event: Optional[bool] = Field(
        None,
        description="Whether tickets are paid (requires premium)"
    )
    ticket_sales_start: Optional[datetime] = Field(
        None,
        description="When ticket sales start"
    )
    ticket_sales_end: Optional[datetime] = Field(
        None,
        description="When ticket sales end"
    )
    event_type: Optional[str] = Field(
        None,
        pattern=r'^(virtual|in_person|hybrid)$',
        description="Event type"
    )
    check_in_mode: Optional[str] = Field(
        None,
        pattern=r'^(admin_only|self_checkin|auto_checkin)$',
        description="Check-in mode"
    )
    refund_policy: Optional[dict] = Field(
        None,
        description="Event-level refund policy override"
    )

    @model_validator(mode='after')
    def validate_sales_dates(self):
        """Ensure sales_end is after sales_start."""
        if self.ticket_sales_end and self.ticket_sales_start:
            if self.ticket_sales_end <= self.ticket_sales_start:
                raise ValueError('ticket_sales_end must be after ticket_sales_start')
        return self

    model_config = ConfigDict(extra='forbid')


# ============================================================================
# Event Admin Validation Models
# ============================================================================

class EventAdminAssignRequest(BaseModel):
    """
    Validation model for assigning an event admin.
    """
    platform: str = Field(
        ...,
        pattern=r'^(twitch|discord|slack|hub)$',
        description="Platform"
    )
    platform_user_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Platform user ID"
    )
    username: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Username"
    )
    hub_user_id: Optional[int] = Field(
        None,
        gt=0,
        description="Hub user ID if linked"
    )
    # Granular permissions
    can_edit_event: bool = Field(
        default=True,
        description="Can edit event details"
    )
    can_check_in: bool = Field(
        default=True,
        description="Can check in attendees"
    )
    can_view_tickets: bool = Field(
        default=True,
        description="Can view ticket list"
    )
    can_manage_ticket_types: bool = Field(
        default=False,
        description="Can manage ticket types"
    )
    can_cancel_tickets: bool = Field(
        default=False,
        description="Can cancel tickets"
    )
    can_transfer_tickets: bool = Field(
        default=False,
        description="Can transfer tickets"
    )
    can_export_attendance: bool = Field(
        default=True,
        description="Can export attendance reports"
    )
    can_assign_event_admins: bool = Field(
        default=False,
        description="Can assign other event admins"
    )
    assignment_notes: Optional[str] = Field(
        None,
        max_length=500,
        description="Notes about this assignment"
    )

    model_config = ConfigDict(extra='forbid')


class EventAdminUpdateRequest(BaseModel):
    """
    Validation model for updating event admin permissions.
    """
    can_edit_event: Optional[bool] = Field(None, description="Can edit event details")
    can_check_in: Optional[bool] = Field(None, description="Can check in attendees")
    can_view_tickets: Optional[bool] = Field(None, description="Can view ticket list")
    can_manage_ticket_types: Optional[bool] = Field(None, description="Can manage ticket types")
    can_cancel_tickets: Optional[bool] = Field(None, description="Can cancel tickets")
    can_transfer_tickets: Optional[bool] = Field(None, description="Can transfer tickets")
    can_export_attendance: Optional[bool] = Field(None, description="Can export attendance")
    can_assign_event_admins: Optional[bool] = Field(None, description="Can assign event admins")
    assignment_notes: Optional[str] = Field(None, max_length=500, description="Notes")

    model_config = ConfigDict(extra='forbid')


class EventAdminRevokeRequest(BaseModel):
    """
    Validation model for revoking an event admin.
    """
    reason: Optional[str] = Field(
        None,
        max_length=500,
        description="Reason for revoking access"
    )

    model_config = ConfigDict(extra='forbid')


# ============================================================================
# Calendar OAuth & Availability Validation Models (Phase 4A + 4B)
# ============================================================================

class AvailabilitySettingsUpdateRequest(BaseModel):
    """
    Validation model for updating user calendar/availability settings.
    """
    visibility_public: Optional[str] = Field(
        None,
        pattern=r'^(hidden|free_busy|details)$',
        description="Public visibility level"
    )
    visibility_registered: Optional[str] = Field(
        None,
        pattern=r'^(hidden|free_busy|details)$',
        description="Registered user visibility level"
    )
    visibility_community: Optional[str] = Field(
        None,
        pattern=r'^(hidden|free_busy|details)$',
        description="Community member visibility level"
    )
    slot_durations: Optional[List[int]] = Field(
        None,
        description="Available slot durations in minutes"
    )
    default_slot_duration: Optional[int] = Field(
        None,
        ge=5,
        le=480,
        description="Default slot duration in minutes (5-480)"
    )
    min_notice_hours: Optional[int] = Field(
        None,
        ge=0,
        le=168,
        description="Minimum notice hours before booking (0-168)"
    )
    max_future_days: Optional[int] = Field(
        None,
        ge=1,
        le=365,
        description="Maximum days in future for booking (1-365)"
    )
    buffer_minutes: Optional[int] = Field(
        None,
        ge=0,
        le=120,
        description="Buffer between appointments in minutes (0-120)"
    )
    timezone: Optional[str] = Field(
        None,
        max_length=50,
        description="User timezone (e.g., America/New_York)"
    )
    booking_enabled: Optional[bool] = Field(
        None,
        description="Enable public booking page"
    )
    booking_slug: Optional[str] = Field(
        None,
        min_length=3,
        max_length=100,
        pattern=r'^[a-z0-9-]+$',
        description="Booking page slug (lowercase, numbers, hyphens)"
    )
    booking_page_title: Optional[str] = Field(
        None,
        max_length=255,
        description="Booking page title"
    )
    booking_page_description: Optional[str] = Field(
        None,
        max_length=2000,
        description="Booking page description"
    )

    model_config = ConfigDict(extra='forbid')


class WeeklyAvailabilityUpdateRequest(BaseModel):
    """
    Validation model for updating weekly availability.
    Example: {"monday": [{"start":"09:00","end":"17:00"}], ...}
    """
    monday: Optional[List[dict]] = Field(default_factory=list)
    tuesday: Optional[List[dict]] = Field(default_factory=list)
    wednesday: Optional[List[dict]] = Field(default_factory=list)
    thursday: Optional[List[dict]] = Field(default_factory=list)
    friday: Optional[List[dict]] = Field(default_factory=list)
    saturday: Optional[List[dict]] = Field(default_factory=list)
    sunday: Optional[List[dict]] = Field(default_factory=list)

    model_config = ConfigDict(extra='forbid')


class AvailableSlotsParams(BaseModel):
    """
    Validation model for available slots query parameters.
    """
    date: str = Field(
        ...,
        pattern=r'^\d{4}-\d{2}-\d{2}$',
        description="Date in YYYY-MM-DD format"
    )
    duration: int = Field(
        default=30,
        ge=5,
        le=480,
        description="Slot duration in minutes (5-480, default 30)"
    )

    model_config = ConfigDict(extra='forbid')


# ============================================================================
# Booking Page Validation Models (Phase 4C + 4D)
# ============================================================================

class BookingPageCreateRequest(BaseModel):
    """
    Validation model for creating a booking page.
    """
    slug: str = Field(
        ...,
        min_length=3,
        max_length=100,
        pattern=r'^[a-z0-9-]+$',
        description="URL slug (lowercase, numbers, hyphens)"
    )
    title: str = Field(
        ...,
        min_length=3,
        max_length=255,
        description="Booking page title"
    )
    description: Optional[str] = Field(
        None,
        max_length=2000,
        description="Booking page description"
    )
    slot_duration: int = Field(
        default=30,
        ge=5,
        le=480,
        description="Slot duration in minutes (5-480)"
    )
    access_scope: str = Field(
        default='public',
        pattern=r'^(public|registered|community)$',
        description="Access scope"
    )
    form_fields: Optional[List[dict]] = Field(
        default_factory=list,
        max_length=8,
        description="Custom form fields (max 8)"
    )

    model_config = ConfigDict(extra='forbid')


class BookingPageUpdateRequest(BaseModel):
    """
    Validation model for updating a booking page.
    """
    title: Optional[str] = Field(
        None,
        min_length=3,
        max_length=255,
        description="Booking page title"
    )
    description: Optional[str] = Field(
        None,
        max_length=2000,
        description="Booking page description"
    )
    slot_duration: Optional[int] = Field(
        None,
        ge=5,
        le=480,
        description="Slot duration in minutes (5-480)"
    )
    access_scope: Optional[str] = Field(
        None,
        pattern=r'^(public|registered|community)$',
        description="Access scope"
    )
    form_fields: Optional[List[dict]] = Field(
        None,
        max_length=8,
        description="Custom form fields (max 8)"
    )
    is_active: Optional[bool] = Field(
        None,
        description="Active status"
    )

    model_config = ConfigDict(extra='forbid')


class BookingCreateRequest(BaseModel):
    """
    Validation model for creating a booking.
    """
    guest_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Guest name"
    )
    guest_email: Optional[str] = Field(
        None,
        max_length=255,
        description="Guest email"
    )
    slot_start: datetime = Field(
        ...,
        description="Booking start time (ISO 8601)"
    )
    slot_end: datetime = Field(
        ...,
        description="Booking end time (ISO 8601)"
    )
    form_responses: Optional[dict] = Field(
        default_factory=dict,
        description="Custom form responses"
    )

    @field_validator('guest_email')
    @classmethod
    def validate_email(cls, v):
        """Validate email format if provided."""
        if v:
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, v):
                raise ValueError('Invalid email format')
        return v

    @model_validator(mode='after')
    def validate_time_order(self):
        """Ensure slot_end is after slot_start."""
        if self.slot_end <= self.slot_start:
            raise ValueError('slot_end must be after slot_start')
        return self

    model_config = ConfigDict(extra='forbid')


class AvailableSlotsQueryParams(BaseModel):
    """
    Validation model for available slots query parameters.
    """
    date: str = Field(
        ...,
        pattern=r'^\d{4}-\d{2}-\d{2}$',
        description="Date in YYYY-MM-DD format"
    )

    model_config = ConfigDict(extra='forbid')


class BookingListParams(BaseModel):
    """
    Validation model for booking list query parameters.
    """
    status: Optional[str] = Field(
        None,
        pattern=r'^(pending|confirmed|cancelled_by_host|cancelled_by_guest|completed|no_show)$',
        description="Filter by status"
    )
    start: Optional[str] = Field(
        None,
        pattern=r'^\d{4}-\d{2}-\d{2}$',
        description="Start date filter (YYYY-MM-DD)"
    )
    end: Optional[str] = Field(
        None,
        pattern=r'^\d{4}-\d{2}-\d{2}$',
        description="End date filter (YYYY-MM-DD)"
    )

    model_config = ConfigDict(extra='forbid')


class GroupBookingPageCreateRequest(BaseModel):
    """
    Validation model for creating a group booking page.
    """
    slug: str = Field(
        ...,
        min_length=3,
        max_length=100,
        pattern=r'^[a-z0-9-]+$',
        description="URL slug (lowercase, numbers, hyphens)"
    )
    title: str = Field(
        ...,
        min_length=3,
        max_length=255,
        description="Booking page title"
    )
    description: Optional[str] = Field(
        None,
        max_length=2000,
        description="Booking page description"
    )
    slot_duration: int = Field(
        default=30,
        ge=5,
        le=480,
        description="Slot duration in minutes (5-480)"
    )
    access_scope: str = Field(
        default='public',
        pattern=r'^(public|registered|community)$',
        description="Access scope"
    )
    form_fields: Optional[List[dict]] = Field(
        default_factory=list,
        max_length=8,
        description="Custom form fields (max 8)"
    )

    model_config = ConfigDict(extra='forbid')


class GroupMemberAddRequest(BaseModel):
    """
    Validation model for adding a member to a group booking page.
    """
    user_id: int = Field(
        ...,
        gt=0,
        description="Hub user ID to add"
    )
    is_required: bool = Field(
        default=True,
        description="Whether member is required for availability"
    )

    model_config = ConfigDict(extra='forbid')


class BestSlotsParams(BaseModel):
    """
    Validation model for best slots query parameters.
    """
    start: str = Field(
        ...,
        pattern=r'^\d{4}-\d{2}-\d{2}$',
        description="Start date (YYYY-MM-DD)"
    )
    end: str = Field(
        ...,
        pattern=r'^\d{4}-\d{2}-\d{2}$',
        description="End date (YYYY-MM-DD)"
    )
    limit: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of slots to return (1-20)"
    )

    model_config = ConfigDict(extra='forbid')


__all__ = [
    # Event management
    'EventCreateRequest',
    'EventSearchParams',
    'EventUpdateRequest',
    'EventApprovalRequest',
    # RSVP
    'RSVPRequest',
    'AttendeeSearchParams',
    # Search and discovery
    'EventFullTextSearchParams',
    'UpcomingEventsParams',
    # Configuration
    'PermissionsConfigRequest',
    'CategoryCreateRequest',
    # Context management
    'ContextSwitchRequest',
    # Ticketing
    'TicketTypeCreateRequest',
    'TicketTypeUpdateRequest',
    'TicketCreateRequest',
    'TicketVerifyRequest',
    'TicketCheckInRequest',
    'TicketUndoCheckInRequest',
    'TicketTransferRequest',
    'TicketCancelRequest',
    'TicketSearchParams',
    'CheckInLogParams',
    'TicketingConfigRequest',
    # Event admin
    'EventAdminAssignRequest',
    'EventAdminUpdateRequest',
    'EventAdminRevokeRequest',
    # Calendar OAuth & Availability
    'AvailabilitySettingsUpdateRequest',
    'WeeklyAvailabilityUpdateRequest',
    'AvailableSlotsParams',
    # Booking pages
    'BookingPageCreateRequest',
    'BookingPageUpdateRequest',
    'BookingCreateRequest',
    'AvailableSlotsQueryParams',
    'BookingListParams',
    'GroupBookingPageCreateRequest',
    'GroupMemberAddRequest',
    'BestSlotsParams',
]
