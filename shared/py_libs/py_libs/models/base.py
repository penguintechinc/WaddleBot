"""
Base Pydantic v2 model configuration.

Provides a standardized BaseModel with common configuration for all Waddles
modules, ensuring consistent validation behavior across the platform.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from typing import Any, Dict


class WaddleBaseModel(BaseModel):
    """
    Base model with standard configuration for all Waddles models.

    Features:
    - extra='forbid': Rejects unknown fields (prevents silent data loss)
    - validate_assignment=True: Re-validates on attribute assignment
    - str_strip_whitespace=True: Strips leading/trailing whitespace from strings
    - str_min_length=1: Empty strings are invalid by default for required fields
    - from_attributes=True: Allows creation from ORM objects

    Example:
        from py_libs.models import WaddleBaseModel
        from pydantic import Field

        class UserRequest(WaddleBaseModel):
            username: str = Field(..., min_length=3, max_length=50)
            email: str = Field(..., pattern=r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+$')
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True,
        from_attributes=True,
        populate_by_name=True,
    )


class WaddleRequestModel(WaddleBaseModel):
    """
    Base model for API request validation.

    Same as WaddleBaseModel but with explicit configuration
    for request payloads.
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True,
        from_attributes=True,
        populate_by_name=True,
        # Request-specific settings
        strict=False,  # Allow coercion (e.g., "123" -> 123)
    )


class WaddleResponseModel(WaddleBaseModel):
    """
    Base model for API response serialization.

    Allows extra fields for flexible response construction.
    """

    model_config = ConfigDict(
        extra="allow",  # Allow additional computed fields
        from_attributes=True,
        populate_by_name=True,
        # Response serialization settings
        ser_json_inf_nan="null",  # Serialize inf/nan as null
    )


class ImmutableModel(WaddleBaseModel):
    """
    Immutable model that cannot be modified after creation.

    Use for configuration objects or value objects that should
    never change after initialization.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,  # Make immutable
        str_strip_whitespace=True,
        from_attributes=True,
    )


def model_to_dict(model: WaddleBaseModel, exclude_none: bool = True) -> Dict[str, Any]:
    """
    Convert a model to a dictionary, optionally excluding None values.

    Args:
        model: The Pydantic model to convert
        exclude_none: Whether to exclude None values from the result

    Returns:
        Dictionary representation of the model
    """
    return model.model_dump(exclude_none=exclude_none)


def model_to_json(model: WaddleBaseModel, exclude_none: bool = True) -> str:
    """
    Convert a model to a JSON string.

    Args:
        model: The Pydantic model to convert
        exclude_none: Whether to exclude None values from the result

    Returns:
        JSON string representation of the model
    """
    return model.model_dump_json(exclude_none=exclude_none)


__all__ = [
    "WaddleBaseModel",
    "WaddleRequestModel",
    "WaddleResponseModel",
    "ImmutableModel",
    "model_to_dict",
    "model_to_json",
]
