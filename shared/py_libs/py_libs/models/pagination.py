"""
Pagination models for API endpoints.

Provides standardized pagination parameters and response wrappers
for consistent pagination across all Waddles modules.
"""

from __future__ import annotations

from typing import Any, Generic, List, Optional, TypeVar

from pydantic import Field, field_validator, model_validator

from .base import WaddleRequestModel, WaddleResponseModel


# Type variable for paginated items
T = TypeVar("T")


class PaginationParams(WaddleRequestModel):
    """
    Standard pagination parameters.

    Provides sensible defaults for limit and offset with validation
    to prevent excessive queries.

    Usage in endpoints:
        @api_bp.route('/items', methods=['GET'])
        @validate_query(PaginationParams)
        async def list_items(query_params: PaginationParams):
            items = await service.get_items(
                limit=query_params.limit,
                offset=query_params.offset
            )
            return success_response(items)
    """

    limit: int = Field(
        default=50,
        ge=1,
        le=100,
        description="Number of items to return (1-100)"
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Number of items to skip"
    )

    @property
    def page(self) -> int:
        """Calculate current page number (1-indexed)."""
        if self.limit == 0:
            return 1
        return (self.offset // self.limit) + 1


class ExtendedPaginationParams(PaginationParams):
    """
    Extended pagination with sorting options.

    Includes common sorting and ordering parameters.
    """

    sort_by: Optional[str] = Field(
        None,
        max_length=50,
        description="Field name to sort by"
    )
    sort_order: str = Field(
        default="desc",
        pattern=r"^(asc|desc)$",
        description="Sort order (asc or desc)"
    )

    @field_validator("sort_by", mode="before")
    @classmethod
    def validate_sort_by(cls, v: Optional[str]) -> Optional[str]:
        """Validate and normalize sort_by field."""
        if v is not None:
            v = v.strip().lower()
            return v if v else None
        return v


class CursorPaginationParams(WaddleRequestModel):
    """
    Cursor-based pagination parameters.

    More efficient for large datasets as it doesn't require
    counting total items.
    """

    cursor: Optional[str] = Field(
        None,
        max_length=255,
        description="Cursor for pagination (opaque token)"
    )
    limit: int = Field(
        default=50,
        ge=1,
        le=100,
        description="Number of items to return (1-100)"
    )


class PaginatedResponse(WaddleResponseModel, Generic[T]):
    """
    Standard paginated response wrapper.

    Provides consistent structure for paginated API responses.

    Usage:
        items = await service.get_items(limit=50, offset=0)
        total = await service.count_items()

        return PaginatedResponse(
            items=items,
            total=total,
            limit=50,
            offset=0
        ).model_dump()
    """

    items: List[Any] = Field(
        ...,
        description="List of items in current page"
    )
    total: int = Field(
        ...,
        ge=0,
        description="Total number of items"
    )
    limit: int = Field(
        ...,
        ge=1,
        description="Number of items requested"
    )
    offset: int = Field(
        ...,
        ge=0,
        description="Number of items skipped"
    )

    @property
    def page(self) -> int:
        """Calculate current page number (1-indexed)."""
        if self.limit == 0:
            return 1
        return (self.offset // self.limit) + 1

    @property
    def pages(self) -> int:
        """Calculate total number of pages."""
        if self.limit == 0:
            return 1
        return (self.total + self.limit - 1) // self.limit

    @property
    def has_next(self) -> bool:
        """Check if there are more items after current page."""
        return self.offset + self.limit < self.total

    @property
    def has_prev(self) -> bool:
        """Check if there are items before current page."""
        return self.offset > 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary with computed properties."""
        return {
            "items": self.items,
            "total": self.total,
            "limit": self.limit,
            "offset": self.offset,
            "page": self.page,
            "pages": self.pages,
            "has_next": self.has_next,
            "has_prev": self.has_prev,
        }


class CursorPaginatedResponse(WaddleResponseModel, Generic[T]):
    """
    Cursor-based paginated response.

    Returns a cursor for fetching the next page instead of
    total count.
    """

    items: List[Any] = Field(
        ...,
        description="List of items in current page"
    )
    next_cursor: Optional[str] = Field(
        None,
        description="Cursor for next page (null if no more items)"
    )
    has_more: bool = Field(
        ...,
        description="Whether there are more items"
    )


def paginate_list(
    items: List[T],
    limit: int,
    offset: int,
) -> tuple[List[T], int]:
    """
    Paginate an in-memory list.

    Args:
        items: Full list of items
        limit: Number of items to return
        offset: Number of items to skip

    Returns:
        Tuple of (paginated items, total count)
    """
    total = len(items)
    start = min(offset, total)
    end = min(offset + limit, total)
    return items[start:end], total


__all__ = [
    "PaginationParams",
    "ExtendedPaginationParams",
    "CursorPaginationParams",
    "PaginatedResponse",
    "CursorPaginatedResponse",
    "paginate_list",
]
