"""Service-layer error taxonomy -- byte-identical copy of hub_api/services/errors.py.

svc-action is a standalone container (own pip install, no cross-container
Python import), so this small error-taxonomy module is duplicated rather
than imported -- it exists solely so `services/url_guard.py` (copied
verbatim from hub_api per this task's "do NOT reimplement SSRF guard")
compiles unchanged; `ApiError`/`bad_request` are not SSRF logic, just the
exception shape `validate_outbound_url` raises on rejection.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ApiError(Exception):
    """Raised by the service layer; caught by the caller and converted/logged."""

    message: str
    status_code: int = 400
    code: str = "BAD_REQUEST"


def bad_request(message: str = "Bad request") -> ApiError:
    """400 -- malformed/missing input."""
    return ApiError(message, 400, "BAD_REQUEST")
