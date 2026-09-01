"""`webhook` action-target adapter -- SSRF-guarded, HMAC-signed outbound POST.

Body: `body_template` rendered against `envelope.payload` if present
(simple `{{key}}` substitution, matching the App Bundle SDK's existing
template convention -- `flask_core.app_manifest`'s stage-spec docstring),
else the payload serialized as-is. Signed with HMAC-SHA256 over the exact
bytes sent, using the secret `secret_ref` resolves to (services/signing.py)
-- never the secret itself, and never logged.
"""

from __future__ import annotations

import httpx

from services.action_target import ActionTarget
from services.adapters.base import AdapterResult, NonRetryableDispatchError, RetryableDispatchError
from services.envelope import ActionEnvelope
from services.signing import resolve_secret, sign_body
from services.templating import build_body
from services.url_guard import SSRFError, guarded_request


async def dispatch(
    target: ActionTarget,
    envelope: ActionEnvelope,
    *,
    timeout_seconds: float,
    client: httpx.AsyncClient | None = None,
) -> AdapterResult:
    """POST `body` to `target.url`, HMAC-signed, SSRF-guarded, redirect-revalidated.

    Raises :class:`NonRetryableDispatchError` for 401/403 (or any other 4xx)
    and a bad `secret_ref`/SSRF-rejected URL; :class:`RetryableDispatchError`
    for 5xx and network/timeout errors.
    """
    body = build_body(target, envelope)
    try:
        secret = resolve_secret(target.secret_ref)
    except Exception as exc:  # SecretResolutionError -- config error, never retryable.
        raise NonRetryableDispatchError(f"webhook secret resolution failed: {exc}") from exc

    signature = sign_body(secret, body)
    headers = {
        **target.headers,
        "Content-Type": "application/json",
        "X-Waddle-Signature": signature,
    }

    owns_client = client is None
    http_client = client or httpx.AsyncClient(
        follow_redirects=False, timeout=timeout_seconds
    )
    try:
        response = await guarded_request(
            http_client, "POST", target.url, headers=headers, content=body
        )
    except SSRFError as exc:
        raise NonRetryableDispatchError(f"webhook URL rejected by SSRF guard: {exc}") from exc
    except (httpx.TimeoutException, httpx.NetworkError, httpx.TransportError) as exc:
        raise RetryableDispatchError(f"webhook request failed: {exc}") from exc
    finally:
        if owns_client:
            await http_client.aclose()

    if response.status_code in (401, 403):
        raise NonRetryableDispatchError(
            f"webhook target rejected auth: HTTP {response.status_code}",
            http_status=response.status_code,
        )
    if 400 <= response.status_code < 500:
        raise NonRetryableDispatchError(
            f"webhook target returned client error: HTTP {response.status_code}",
            http_status=response.status_code,
        )
    if response.status_code >= 500:
        raise RetryableDispatchError(
            f"webhook target returned server error: HTTP {response.status_code}",
            http_status=response.status_code,
        )

    return AdapterResult(
        target_type="webhook",
        detail=f"delivered, HTTP {response.status_code}",
        http_status=response.status_code,
    )
