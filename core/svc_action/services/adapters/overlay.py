"""`overlay` action-target adapter -- SSRF-guarded HTTP push to svc-presentation.

POSTs to `{presentation_base_url}/overlay/{community}/{surface}/push` (the
per-community browser-source overlay's push endpoint -- svc-presentation
itself is a separate, still-scaffold container, core/svc_presentation/
app.py; this adapter is the outbound client side, real and independent of
whether that endpoint's receiving handler is implemented yet). `community`
defaults to the envelope's own `community` when the target config leaves
it unset -- an overlay push nearly always targets the same community the
triggering event came from.
"""

from __future__ import annotations

import json

import httpx

from services.action_target import ActionTarget
from services.adapters.base import AdapterResult, NonRetryableDispatchError, RetryableDispatchError
from services.envelope import ActionEnvelope
from services.url_guard import SSRFError, guarded_request


class OverlayTargetError(NonRetryableDispatchError):
    """No community resolvable for an overlay push (neither target nor envelope has one)."""


async def dispatch(
    target: ActionTarget,
    envelope: ActionEnvelope,
    *,
    presentation_base_url: str,
    timeout_seconds: float,
    client: httpx.AsyncClient | None = None,
) -> AdapterResult:
    """POST the envelope payload to svc-presentation's per-community overlay push endpoint."""
    community = target.community or envelope.community
    if not community:
        raise OverlayTargetError(
            "overlay target has no community (neither action_target.community "
            "nor the envelope's own community is set)"
        )

    url = f"{presentation_base_url.rstrip('/')}/overlay/{community}/{target.surface}/push"
    body = json.dumps(dict(envelope.payload)).encode("utf-8")

    owns_client = client is None
    http_client = client or httpx.AsyncClient(
        follow_redirects=False, timeout=timeout_seconds
    )
    try:
        response = await guarded_request(
            http_client,
            "POST",
            url,
            headers={"Content-Type": "application/json"},
            content=body,
        )
    except SSRFError as exc:
        raise NonRetryableDispatchError(f"overlay URL rejected by SSRF guard: {exc}") from exc
    except (httpx.TimeoutException, httpx.NetworkError, httpx.TransportError) as exc:
        raise RetryableDispatchError(f"overlay push failed: {exc}") from exc
    finally:
        if owns_client:
            await http_client.aclose()

    if response.status_code in (401, 403):
        raise NonRetryableDispatchError(
            f"overlay push rejected auth: HTTP {response.status_code}",
            http_status=response.status_code,
        )
    if 400 <= response.status_code < 500:
        raise NonRetryableDispatchError(
            f"overlay push returned client error: HTTP {response.status_code}",
            http_status=response.status_code,
        )
    if response.status_code >= 500:
        raise RetryableDispatchError(
            f"overlay push returned server error: HTTP {response.status_code}",
            http_status=response.status_code,
        )

    return AdapterResult(
        target_type="overlay",
        detail=f"pushed to community={community} surface={target.surface}, "
        f"HTTP {response.status_code}",
        http_status=response.status_code,
    )
