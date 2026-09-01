"""Shared adapter contract: result shape + the retryable/non-retryable exception split.

Every adapter (`webhook`/`rest_api`/`message_queue`/`overlay`/`email`)
raises one of the two exceptions below instead of returning a bool, so
`runner.py` can hand `RetryableDispatchError` (and only that) to
`flask_core.circuit_breaker.retry_with_backoff` -- a `NonRetryableDispatchError`
(4xx auth, bad config) propagates immediately, no retry, matching this
task's "no retry on 4xx auth (401/403)" requirement.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


class RetryableDispatchError(Exception):
    """5xx response or network/timeout error -- worth retrying with backoff."""

    def __init__(self, message: str, *, http_status: Optional[int] = None) -> None:
        super().__init__(message)
        self.http_status = http_status


class NonRetryableDispatchError(Exception):
    """4xx auth failure (401/403) or a config error -- retrying cannot succeed."""

    def __init__(self, message: str, *, http_status: Optional[int] = None) -> None:
        super().__init__(message)
        self.http_status = http_status


@dataclass(slots=True, frozen=True)
class AdapterResult:
    """Successful-dispatch outcome, recorded to the dispatch log (dispatch_log.py)."""

    target_type: str
    detail: str
    http_status: Optional[int] = None
