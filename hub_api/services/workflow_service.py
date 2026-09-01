"""Business logic ported from `workflowController.js` -- proxy client + owned license check.

`workflowController.js` is almost entirely a reverse-proxy to the
standalone `workflow-core` service (`proxyRequest()`, port 8070) --
mirrors `services/event_calendar_proxy.py`'s `EventCalendarProxyClient`
(same `async with httpx.AsyncClient(...)` per-call pattern, same
`ProxyResult(ok, status_code, body)` shape). Two pieces of REAL,
hub-api-owned logic ride along with the proxying, both ported here:

1. `validate_license()` -- `workflowController.js::validateLicense()`,
   a direct `communities` table read (license_key/license_expires_at/
   license_tier), gating `create_workflow`/`publish_workflow`/
   `execute_workflow` only (matches Node's own call sites exactly --
   `update`/`delete`/`test`/`validate`/list/get/executions/webhooks
   never call it in Node either). See `services/schema.py`'s module
   docstring gap (4): these three columns aren't in any real migration,
   byte-faithful-to-Node gap, not introduced by this port.

2. `get_workflow_or_403()` -- SECURITY FIX, not a faithful-port item.
   `getWorkflow()` is the ONLY Node handler that checks
   `result.communityId !== communityId -> 403` before returning a
   workflow proxied from `workflow-core`; `updateWorkflow`/
   `deleteWorkflow`/`publishWorkflow`/`executeWorkflow`/`testWorkflow`/
   every execution and webhook endpoint addressing a specific
   `workflowId` proxy straight through with NO equivalent check --
   an authenticated admin of community A, given a `workflowId`
   belonging to community B (workflow ids are unguessable but not
   secret -- visible in any URL/log/webhook payload), could mutate/
   execute/webhook a workflow they were never granted access to,
   trusting `workflow-core` alone to enforce scoping it has no
   token-derived signal to enforce (hub-api forwards `communityId` as
   a plain request field, same trust level as any other body param).
   `blueprints/v1/workflow.py` routes every `<workflow_id>`-addressing
   mutation through this same ownership check `getWorkflow` already
   proved out, closing the gap uniformly instead of leaving it fixed
   in exactly one of fifteen endpoints.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx

from services.errors import ApiError, forbidden, not_found

_DEFAULT_BASE_URL = "http://workflow-core:8070"
_DEFAULT_TIMEOUT_SECONDS = 10.0
#: Matches workflowController.js::validateLicense()'s workflowTiers list exactly.
_WORKFLOW_LICENSE_TIERS = frozenset({"pro", "enterprise", "premium"})


@dataclass(slots=True, frozen=True)
class ProxyResult:
    """Outcome of one proxied call to `workflow-core`.

    Mirrors `services.event_calendar_proxy.ProxyResult`.
    """

    ok: bool
    status_code: int
    body: Any


@dataclass(slots=True, frozen=True)
class LicenseCheckResult:
    """Result of `validate_license()` -- `{valid, reason}`, matches Node's return shape."""

    valid: bool
    reason: str | None = None


class WorkflowCoreProxyClient:
    """Forwards one request to `workflow-core`, relaying its JSON body.

    Port of Node's `proxyRequest()`.
    """

    def __init__(
        self, *, base_url: str | None = None, timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS
    ) -> None:
        """Build the client; `base_url` defaults to `WORKFLOW_CORE_URL` env var, same as Node."""
        self._base_url = base_url or os.getenv("WORKFLOW_CORE_URL", _DEFAULT_BASE_URL)
        self._timeout_seconds = timeout_seconds

    async def request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> ProxyResult:
        """Forward `method /api/v1{path}` to `workflow-core`."""
        url = f"{self._base_url}/api/v1{path}"
        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.request(method, url, json=json_body, params=params)
        except httpx.HTTPError as exc:
            # Node's proxyRequest() catch-all: no `err.response` -> statusCode 500,
            # code SERVICE_UNAVAILABLE.
            raise ApiError(
                f"Failed to connect to workflow service: {exc}", 500, "SERVICE_UNAVAILABLE"
            ) from exc

        try:
            data: Any = response.json()
        except ValueError:
            data = None
        return ProxyResult(ok=response.is_success, status_code=response.status_code, body=data)


def error_from_proxy(result: ProxyResult, *, not_found_message: str) -> ApiError:
    """Map a failed `ProxyResult` to an `ApiError`.

    Port of each controller's `err.statusCode` switch. Node:
    `err.statusCode === 404 -> errors.notFound(...)`, else
    `errors.internal(err.message)` (any other status -- Node's own
    controllers collapse every non-404 workflow-core failure to a
    generic 500, faithfully preserved here rather than relaying
    workflow-core's real status code, which Node never does either).
    """
    if result.status_code == 404:
        return not_found(not_found_message)
    message = None
    if isinstance(result.body, dict):
        message = result.body.get("message") or result.body.get("error")
    return ApiError(str(message) if message else "Workflow service error", 500, "INTERNAL_ERROR")


def _is_expired(expires_at: datetime | None) -> bool:
    """`communities.license_expires_at < now`, tz-aware-or-naive-storage safe.

    BUG FIX (caught by this port's own test suite, not a Node behavior to
    preserve): pydal's sqlite adapter round-trips a tz-aware `datetime`
    back as NAIVE, silently dropping `tzinfo` while keeping the UTC wall-
    clock VALUE unchanged (confirmed empirically -- inserting
    `datetime.now(UTC)` and reading it back gives a naive datetime equal
    to the UTC wall-clock reading, not the local one). Comparing that
    against `datetime.now()` (naive LOCAL time) silently miscomputes
    "expired" by the server's UTC offset -- correct only by accident on a
    UTC-configured host. Postgres (`TIMESTAMPTZ`, the real column type
    here) returns a genuinely tz-AWARE datetime via psycopg2, so the
    naive branch is sqlite/test-only today, but must stay correct
    independent of host timezone regardless.
    """
    if expires_at is None:
        return False
    now = (
        datetime.now(UTC)
        if expires_at.tzinfo is not None
        else datetime.now(UTC).replace(tzinfo=None)
    )
    return expires_at < now


async def validate_license(async_dal: Any, dal: Any, *, community_id: int) -> LicenseCheckResult:
    """Port of `workflowController.js::validateLicense()`.

    Direct `communities` read -- no proxy call to `workflow-core`.
    """
    rows = await async_dal.select_async(dal(dal.communities.id == community_id))
    if not rows:
        return LicenseCheckResult(False, "Community not found")
    row = rows.first()

    if not row.license_key:
        return LicenseCheckResult(False, "No license configured")
    if _is_expired(row.license_expires_at):
        return LicenseCheckResult(False, "License expired")

    tier = (row.license_tier or "").lower()
    if tier not in _WORKFLOW_LICENSE_TIERS:
        return LicenseCheckResult(False, "Workflows not included in current license tier")

    return LicenseCheckResult(True)


async def get_workflow_or_403(
    client: WorkflowCoreProxyClient, *, community_id: int, workflow_id: str
) -> dict[str, Any]:
    """Fetch a workflow and enforce community ownership -- see module docstring item (2).

    Every route addressing a specific `workflow_id` (not just `getWorkflow`)
    calls this before proceeding, closing the IDOR Node's own controllers
    left open on every mutating/execution/webhook endpoint.
    """
    result = await client.request(
        "GET", f"/workflows/{workflow_id}", params={"communityId": community_id}
    )
    if not result.ok:
        raise error_from_proxy(result, not_found_message="Workflow not found")
    body = result.body if isinstance(result.body, dict) else {}
    if body.get("communityId") != community_id:
        raise forbidden("Access denied")
    return body
