"""Service-layer error taxonomy -- mirrors `hub_api/services/errors.py`'s `ApiError` shape.

Every service function raises :class:`ApiError`; every blueprint route
catches it at the top level and converts it into the shared `{success,
error: {code, message}}` envelope, same convention every other Quart
service in this repo already uses.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ApiError(Exception):
    """Raised by the service layer; caught by the blueprint route and converted to JSON."""

    message: str
    status_code: int = 400
    code: str = "BAD_REQUEST"


def bad_request(message: str = "Bad request") -> ApiError:
    """400 -- malformed/missing input."""
    return ApiError(message, 400, "BAD_REQUEST")


def unauthorized(message: str = "Unauthorized") -> ApiError:
    """401 -- missing/invalid credentials."""
    return ApiError(message, 401, "UNAUTHORIZED")


def forbidden(message: str = "Forbidden") -> ApiError:
    """403 -- authenticated but not permitted."""
    return ApiError(message, 403, "FORBIDDEN")


def not_found(message: str = "Not found") -> ApiError:
    """404 -- resource does not exist."""
    return ApiError(message, 404, "NOT_FOUND")


def conflict(message: str = "Conflict") -> ApiError:
    """409 -- e.g. a stream config already exists for this community."""
    return ApiError(message, 409, "CONFLICT")


def payment_required(message: str = "This feature requires a higher plan") -> ApiError:
    """402 -- tier/feature-flag gate denied the request."""
    return ApiError(message, 402, "PAYMENT_REQUIRED")


def service_unavailable(message: str = "Upstream service unavailable") -> ApiError:
    """503 -- hub-api (token ledger, etc.) unreachable; never a raw 500."""
    return ApiError(message, 503, "SERVICE_UNAVAILABLE")
