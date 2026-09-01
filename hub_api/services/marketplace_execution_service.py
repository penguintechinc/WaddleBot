"""Vendor module execution -- port of `vendorExecutionService.js`.

This is the third-party App invocation path: a router/trigger module asks
hub-api to run a marketplace command, hub-api resolves the vendor
module's config and calls out to vendor-controlled infrastructure
(`webhook_url` for `webhook_push`, `api_base_url` for `rest_pull`).
Preserved from Node: HMAC-SHA256 request signing (`webhook_secret`) and a
timeout bound. Fixed from Node (security.md Service-to-Service Auth /
SSRF):

- **SSRF**: `module.webhook_url`/`module.api_base_url` are vendor-
  controlled at module-creation time (`marketplace_vendor_service.
  create_vendor_module` already SSRF-guards them at write time) but a
  hostname's resolved address can change between write time and request
  time (DNS rebinding) -- `url_guard.validate_url` re-validates
  immediately before every outbound call, same defense-in-depth pattern
  as `url_guard.guarded_get`.
- **No redirect-following**: Node's `fetch()` follows redirects (up to
  20) by default without re-validating the target -- a classic SSRF
  bypass (public URL 302s to an internal one). This port uses
  `httpx.AsyncClient(follow_redirects=False)`; a 3xx response from a
  vendor endpoint is treated as a failure, never silently followed.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any

import httpx

from services.errors import ApiError, not_found
from services.url_guard import SSRFError, validate_url

_DEFAULT_TIMEOUT_MS = 5000


@dataclass(slots=True, frozen=True)
class ModuleConfig:
    """Resolved, approved marketplace module config -- what `execute_command` needs."""

    id: int
    name: str
    webhook_url: str
    webhook_secret: str | None
    webhook_timeout_ms: int
    communication_model: str
    auth_type: str
    auth_config: dict[str, Any]
    api_base_url: str | None


def get_module_config(dal: Any, module_id: int) -> ModuleConfig | None:
    """Resolve an approved, non-deleted module's execution config, or `None`."""
    row = (
        dal(
            (dal.marketplace_modules.id == module_id)
            & (dal.marketplace_modules.status == "approved")
            & (dal.marketplace_modules.deleted_at == None)  # noqa: E711
        )
        .select()
        .first()
    )
    if row is None:
        return None
    return ModuleConfig(
        id=row.id,
        name=row.name,
        webhook_url=row.webhook_url,
        webhook_secret=row.webhook_secret,
        webhook_timeout_ms=row.webhook_timeout_ms or _DEFAULT_TIMEOUT_MS,
        communication_model=row.communication_model or "webhook_push",
        auth_type=row.auth_type or "hmac",
        auth_config=row.auth_config or {},
        api_base_url=row.api_base_url,
    )


def _hmac_signature(secret: str, payload: dict[str, Any]) -> str:
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    digest = hmac.new(secret.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"sha256={digest}"


async def _post_no_redirect(
    url: str, *, headers: dict[str, str], payload: dict[str, Any], timeout_ms: int
) -> httpx.Response:
    """SSRF-guarded POST -- re-validates `url` before the call, never follows redirects."""
    try:
        validate_url(url)
    except SSRFError as exc:
        raise ApiError(f"Rejected module URL: {exc}", 502, "SSRF_REJECTED") from exc
    async with httpx.AsyncClient(follow_redirects=False, timeout=timeout_ms / 1000) as client:
        response = await client.post(url, headers=headers, json=payload)
    if 300 <= response.status_code < 400:
        raise ApiError("Vendor module returned a redirect (not followed)", 502, "BAD_GATEWAY")
    return response


async def execute_command(dal: Any, module_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    """Proxy a router-issued command to the vendor module. Raises `ApiError` on failure."""
    module = get_module_config(dal, module_id)
    if module is None:
        raise not_found("Module not found or not available")

    start = time.monotonic()
    if module.communication_model == "rest_pull":
        data = await _execute_rest_pull(module, payload)
    else:
        data = await _execute_webhook_push(module, payload)
    duration_ms = int((time.monotonic() - start) * 1000)

    dal(dal.marketplace_modules.id == module_id).update(
        total_requests=dal.marketplace_modules.total_requests + 1
    )
    dal.commit()
    _ = duration_ms  # parity with Node's debug-log timing; structured logging done by the caller
    return data


async def _execute_webhook_push(module: ModuleConfig, payload: dict[str, Any]) -> dict[str, Any]:
    if not module.webhook_secret:
        raise ApiError("Module has no webhook secret configured", 502, "BAD_GATEWAY")
    signature = _hmac_signature(module.webhook_secret, payload)
    headers = {
        "Content-Type": "application/json",
        "X-WaddleBot-Signature": signature,
        "X-WaddleBot-Module-Id": str(module.id),
    }
    response = await _post_no_redirect(
        module.webhook_url, headers=headers, payload=payload, timeout_ms=module.webhook_timeout_ms
    )
    if response.status_code >= 400:
        raise ApiError(f"Vendor module returned {response.status_code}", 502, "BAD_GATEWAY")
    result: dict[str, Any] = response.json()
    return result


async def _execute_rest_pull(module: ModuleConfig, payload: dict[str, Any]) -> dict[str, Any]:
    if not module.api_base_url:
        raise ApiError("Module has no api_base_url configured", 502, "BAD_GATEWAY")

    if module.auth_type == "api_key":
        auth_headers = {"Authorization": f"Bearer {module.auth_config.get('api_key', '')}"}
    elif module.auth_type == "oauth2_client_credentials":
        auth_headers = {"Authorization": f"Bearer {module.auth_config.get('access_token', '')}"}
    elif module.webhook_secret:
        auth_headers = {"X-WaddleBot-Signature": _hmac_signature(module.webhook_secret, payload)}
    else:
        raise ApiError("Module has no auth configured for rest_pull", 502, "BAD_GATEWAY")

    response = await _post_no_redirect(
        module.api_base_url.rstrip("/") + "/execute",
        headers={"Content-Type": "application/json", **auth_headers},
        payload=payload,
        timeout_ms=module.webhook_timeout_ms,
    )
    if response.status_code >= 400:
        raise ApiError(f"Vendor module returned {response.status_code}", 502, "BAD_GATEWAY")
    result: dict[str, Any] = response.json()
    return result


def increment_request_count(dal: Any, module_id: int) -> None:
    """Best-effort request counter -- mirrors Node's fire-and-forget `incrementRequestCount`."""
    dal(dal.marketplace_modules.id == module_id).update(
        total_requests=dal.marketplace_modules.total_requests + 1
    )
    dal.commit()
