"""Real HTTP client against `core/reputation_module`'s internal reputation-adjust endpoint.

Replaces a prior implementation that vendored `core/reputation_module`'s
`ReputationService` straight into this process via an `importlib`/
`sys.modules["config"]` swap and wrote reputation deltas through svc-
process's OWN DAL -- a service-boundary violation (backend.md Shared
Libraries / backend-database.md Per-Service Database Accounts: svc-process
has no business holding write access to `reputation_module`'s tables, and
`ReputationService` is that module's own internal implementation detail,
not a shared library). `core/reputation_module` already exposes a real,
already-shipped internal endpoint that does exactly what the gate needs:
`POST /api/v1/internal/events` (`core/reputation_module/app.py::
receive_events`) accepts one event dict `{community_id, user_id, platform,
platform_user_id, event_type, metadata}`, routes it through `EventProcessor
.process_batch()` -> `.process_event()` -> `ReputationService.adjust()` --
the identical call the old vendored bridge made directly -- and updates
both community AND (when the platform identity is hub-linked) global
reputation from that one call, same as before.

Auth: `X-Service-Key` shared-secret header, matching `internal_bp`'s own
`_verify_service_key()` check in `reputation_module/app.py` and the exact
calling convention `hub_api/services/analytics_proxy.py`/
`community_loyalty.py` already use for this shape of internal-only,
service-to-service call (`SERVICE_API_KEY` env var / Helm secret, shared
across modules) -- not the JWT-minting pattern `app.py::_jwt_provider`
uses for polling hub-api's user-JWT-gated distribution endpoint, since
`/internal/events` is gated on the shared service key, not a bearer JWT.

Transport: a fresh `httpx.AsyncClient` per call (`async with httpx.
AsyncClient(...) as client:`), matching `hub_api/services/community_loyalty
.py::_proxy`'s established pattern for this exact call shape (infrequent,
call-scoped, no long-lived client to manage through this process's own
lifecycle) rather than `token_ledger_client.py`'s injected-client style --
`run_moderation_gate` only calls this on an actual moderation-classifier
match (rare relative to per-message throughput), so per-call client
construction overhead is immaterial.

Graceful degradation (mandatory, see `docs/plans/2026-09-08-content-
moderation-design.md` and the `poll_failed` lesson referenced in the task):
`.adjust()` NEVER raises for an unreachable/erroring reputation service --
every failure mode (connection refused, timeout, non-2xx, malformed JSON)
is caught, logged, and returned as `ReputationAdjustResult(ok=False, ...)`.
`run_moderation_gate` only awaits this call and never branches on its
result, so a down reputation service degrades to "no reputation hit was
recorded, logged" while the flagged message still reaches `transform_fn`
exactly as before.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from config import Config

logger = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 5.0
_EVENTS_PATH = "/api/v1/internal/events"


class ReputationAdjuster(Protocol):
    """Structural type for the `.adjust()`-shaped dependency the moderation gate calls."""

    async def adjust(
        self,
        community_id: int,
        user_id: int | None,
        event_type: str,
        platform: str,
        platform_user_id: str,
        metadata: dict[str, Any] | None = None,
        reason: str | None = None,
        amount_multiplier: float = 1.0,
    ) -> Any:
        """Apply one reputation adjustment via `reputation_module`'s internal API."""
        ...


@dataclass(slots=True, frozen=True)
class ReputationAdjustResult:
    """Outcome of one `POST /api/v1/internal/events` call against `reputation_module`."""

    ok: bool
    error: str | None


class ReputationGateClient:
    """Thin HTTP client for `reputation_module`'s `POST /api/v1/internal/events` endpoint.

    `amount_multiplier` is accepted for `ReputationAdjuster` protocol
    compatibility but is NOT sent over the wire -- the real endpoint has no
    such field; it derives its own multiplier server-side from `metadata`
    for a fixed set of scaled event types (donation/cheer/gift_subscription,
    see `EventProcessor.SCALED_EVENTS`), and defaults to `1.0` for every
    other event type, including the gate's own fixed `event_type="warn"` --
    so the caller-supplied `1.0` and the server's own computed `1.0` are
    always identical for this gate's current usage.
    """

    def __init__(self, *, base_url: str | None = None, service_api_key: str | None = None) -> None:
        """Build a client for `base_url`/`service_api_key`, defaulting from `Config`."""
        self._base_url = (base_url or Config.REPUTATION_API_URL).rstrip("/")
        self._service_api_key = (
            service_api_key if service_api_key is not None else Config.SERVICE_API_KEY
        )

    async def adjust(
        self,
        community_id: int,
        user_id: int | None,
        event_type: str,
        platform: str,
        platform_user_id: str,
        metadata: dict[str, Any] | None = None,
        reason: str | None = None,
        amount_multiplier: float = 1.0,
    ) -> ReputationAdjustResult:
        """POST one event to `reputation_module`; never raises -- degrades to `ok=False`.

        `reason` is nested into `metadata["reason"]` -- `EventProcessor.
        process_event()`'s own contract reads the human-readable reason from
        `metadata.get('reason')` (falling back to `f"{platform} {event_type}"`
        itself if absent), there is no separate top-level `reason` field on
        the wire.
        """
        event_metadata = dict(metadata or {})
        if reason and "reason" not in event_metadata:
            event_metadata["reason"] = reason

        payload = {
            "community_id": community_id,
            "user_id": user_id,
            "platform": platform,
            "platform_user_id": platform_user_id,
            "event_type": event_type,
            "metadata": event_metadata,
        }

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    f"{self._base_url}{_EVENTS_PATH}",
                    json=payload,
                    headers={"X-Service-Key": self._service_api_key},
                )
        except httpx.HTTPError as exc:
            logger.warning(
                "reputation_gate_client.unreachable community_id=%s error=%s",
                community_id,
                exc,
            )
            return ReputationAdjustResult(ok=False, error=str(exc))

        if response.status_code >= 400:
            logger.warning(
                "reputation_gate_client.rejected community_id=%s status=%s",
                community_id,
                response.status_code,
            )
            return ReputationAdjustResult(ok=False, error=f"HTTP {response.status_code}")

        try:
            body = response.json()
        except ValueError as exc:
            logger.warning(
                "reputation_gate_client.invalid_response community_id=%s error=%s",
                community_id,
                exc,
            )
            return ReputationAdjustResult(ok=False, error=str(exc))

        data = body.get("data") if isinstance(body, dict) else None
        if not isinstance(data, dict) or int(data.get("failed", 0)) > 0:
            logger.warning(
                "reputation_gate_client.event_failed community_id=%s body=%s",
                community_id,
                body,
            )
            return ReputationAdjustResult(ok=False, error="reputation_module reported a failure")

        return ReputationAdjustResult(ok=True, error=None)


_lock = threading.Lock()
_client: ReputationGateClient | None = None


def get_reputation_service() -> ReputationAdjuster:
    """Lazily construct (once, process-wide) and return the real HTTP-backed reputation client."""
    global _client
    with _lock:
        if _client is None:
            _client = ReputationGateClient()
        return _client


def reset_for_tests() -> None:
    """Clear the cached singleton -- test isolation only, never called by production code."""
    global _client
    _client = None
