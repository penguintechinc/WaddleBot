"""`rest_api` action-target adapter -- SSRF-guarded, configurable method/headers/body.

Unlike `webhook`, `rest_api` targets are not HMAC-signed by convention (a
generic third-party REST endpoint, not necessarily one expecting Waddle's
signature scheme) -- callers needing auth put it in `headers` (e.g. a
static `Authorization` header resolved from config, never hardcoded).
"""

from __future__ import annotations

import httpx

from services.action_target import ActionTarget
from services.adapters.base import AdapterResult, NonRetryableDispatchError, RetryableDispatchError
from services.envelope import ActionEnvelope
from services.templating import build_body
from services.url_guard import SSRFError, guarded_request


async def dispatch(
    target: ActionTarget,
    envelope: ActionEnvelope,
    *,
    timeout_seconds: float,
    client: httpx.AsyncClient | None = None,
) -> AdapterResult:
    """`target.method target.url`, SSRF-guarded, redirect-revalidated.

    Same retry classification as `webhook.dispatch`: 401/403/other-4xx ->
    non-retryable, 5xx/network -> retryable.
    """
    body = build_body(target, envelope) if target.method in ("POST", "PUT", "PATCH") else None
    headers = {**target.headers}
    if body is not None:
        headers.setdefault("Content-Type", "application/json")

    owns_client = client is None
    http_client = client or httpx.AsyncClient(follow_redirects=False, timeout=timeout_seconds)
    try:
        response = await guarded_request(
            http_client, target.method, target.url, headers=headers, content=body
        )
    except SSRFError as exc:
        raise NonRetryableDispatchError(f"rest_api URL rejected by SSRF guard: {exc}") from exc
    except (httpx.TimeoutException, httpx.NetworkError, httpx.TransportError) as exc:
        raise RetryableDispatchError(f"rest_api request failed: {exc}") from exc
    finally:
        if owns_client:
            await http_client.aclose()

    if response.status_code in (401, 403):
        raise NonRetryableDispatchError(
            f"rest_api target rejected auth: HTTP {response.status_code}",
            http_status=response.status_code,
        )
    if 400 <= response.status_code < 500:
        raise NonRetryableDispatchError(
            f"rest_api target returned client error: HTTP {response.status_code}",
            http_status=response.status_code,
        )
    if response.status_code >= 500:
        raise RetryableDispatchError(
            f"rest_api target returned server error: HTTP {response.status_code}",
            http_status=response.status_code,
        )

    return AdapterResult(
        target_type="rest_api",
        detail=f"delivered, HTTP {response.status_code}",
        http_status=response.status_code,
    )
