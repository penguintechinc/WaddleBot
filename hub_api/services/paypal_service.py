"""PayPal REST client -- port of `paypalService.js` via `httpx` (no PayPal SDK dependency).

**Fixes a real vulnerability Node shipped, not just a faithful port**:
`paypalService.js::verifyWebhookSignature` (see `hub_api/PORTING.md`'s
sibling note in `stripe_service.py`) builds the verification request body
correctly but then **never sends it** -- it logs the payload and
unconditionally `return true`s, with the comment "PayPal SDK doesn't have
built-in webhook verification... For now, we'll return true". That is an
unauthenticated payment webhook: any caller who can reach the endpoint can
forge `PAYMENT.CAPTURE.COMPLETED`/`BILLING.SUBSCRIPTION.ACTIVATED` events
and the Node handler would have persisted them as real money movement, had
the persistence side been implemented (it also is not -- see
`marketplace_webhook_service.py`). `verify_webhook_signature()` below calls
the real, PayPal-documented REST endpoint (`POST /v1/notifications/verify-
webhook-signature`, https://developer.paypal.com/api/rest/webhooks/rest/#
link-verifywebhooksignature) and fails closed on every error path
(missing headers, missing webhook id, network failure, non-`SUCCESS`
verification status) -- never a bare `return true`.
"""

from __future__ import annotations

from typing import Any

import httpx

from services.errors import ApiError

PAYPAL_SANDBOX_BASE = "https://api-m.sandbox.paypal.com"
PAYPAL_LIVE_BASE = "https://api-m.paypal.com"

_REQUIRED_WEBHOOK_HEADERS = (
    "paypal-transmission-id",
    "paypal-transmission-time",
    "paypal-cert-url",
    "paypal-transmission-sig",
    "paypal-auth-algo",
)


def api_base(mode: str) -> str:
    """Return PayPal's REST API base URL for `mode` ("live" or anything else -> sandbox)."""
    return PAYPAL_LIVE_BASE if mode == "live" else PAYPAL_SANDBOX_BASE


async def get_access_token(
    *,
    client_id: str,
    client_secret: str,
    mode: str = "sandbox",
    client: httpx.AsyncClient | None = None,
) -> str:
    """OAuth2 client_credentials grant -- PayPal's token endpoint, no caching (see module docs)."""
    owns_client = client is None
    http_client = client or httpx.AsyncClient(timeout=15.0)
    try:
        response = await http_client.post(
            f"{api_base(mode)}/v1/oauth2/token",
            data={"grant_type": "client_credentials"},
            auth=(client_id, client_secret),
        )
    finally:
        if owns_client:
            await http_client.aclose()

    if response.status_code >= 400:
        raise ApiError("Failed to obtain PayPal access token", 502, "PAYPAL_AUTH_ERROR")
    token: str = response.json()["access_token"]
    return token


async def verify_webhook_signature(
    headers: dict[str, str],
    raw_body: bytes,
    *,
    webhook_id: str | None,
    client_id: str,
    client_secret: str,
    mode: str = "sandbox",
    client: httpx.AsyncClient | None = None,
) -> bool:
    """Verify a PayPal webhook via PayPal's own `verify-webhook-signature` REST endpoint.

    Fails closed on any missing precondition or non-`SUCCESS` result --
    never returns `True` without a real, positive verification response
    from PayPal. Headers are matched case-insensitively (PayPal sends
    `PAYPAL-TRANSMISSION-ID` etc; ASGI/Quart normalizes header names, but
    this function accepts a plain dict so it stays testable without a full
    request object).
    """
    lower_headers = {k.lower(): v for k, v in headers.items()}
    if not webhook_id or not client_id or not client_secret:
        return False
    if any(lower_headers.get(name) is None for name in _REQUIRED_WEBHOOK_HEADERS):
        return False

    try:
        import json as _json

        event_body = _json.loads(raw_body)
    except (ValueError, UnicodeDecodeError):
        return False

    verify_payload = {
        "auth_algo": lower_headers["paypal-auth-algo"],
        "cert_url": lower_headers["paypal-cert-url"],
        "transmission_id": lower_headers["paypal-transmission-id"],
        "transmission_sig": lower_headers["paypal-transmission-sig"],
        "transmission_time": lower_headers["paypal-transmission-time"],
        "webhook_id": webhook_id,
        "webhook_event": event_body,
    }

    try:
        token = await get_access_token(
            client_id=client_id, client_secret=client_secret, mode=mode, client=client
        )
        owns_client = client is None
        http_client = client or httpx.AsyncClient(timeout=15.0)
        try:
            response = await http_client.post(
                f"{api_base(mode)}/v1/notifications/verify-webhook-signature",
                json=verify_payload,
                headers={"Authorization": f"Bearer {token}"},
            )
        finally:
            if owns_client:
                await http_client.aclose()
    except (httpx.HTTPError, ApiError, KeyError, ValueError):
        return False

    if response.status_code >= 400:
        return False
    result: dict[str, Any] = response.json()
    return bool(result.get("verification_status") == "SUCCESS")


async def _request(
    method: str,
    path: str,
    *,
    client_id: str,
    client_secret: str,
    mode: str = "sandbox",
    json_body: dict[str, Any] | None = None,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    token = await get_access_token(
        client_id=client_id, client_secret=client_secret, mode=mode, client=client
    )
    owns_client = client is None
    http_client = client or httpx.AsyncClient(timeout=15.0)
    try:
        response = await http_client.request(
            method,
            f"{api_base(mode)}{path}",
            json=json_body,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
    finally:
        if owns_client:
            await http_client.aclose()

    body: dict[str, Any] = response.json() if response.content else {}
    if response.status_code >= 400:
        message = body.get("message", "PayPal API error")
        raise ApiError(message, response.status_code, "PAYPAL_ERROR")
    return body


async def create_order(
    *,
    client_id: str,
    client_secret: str,
    mode: str,
    items: list[dict[str, Any]],
    total_amount: float,
    currency: str = "USD",
    return_url: str,
    cancel_url: str,
    metadata: dict[str, Any] | None = None,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    """Create a PayPal Order (v2 Orders API) -- one-time payment (real, not stubbed)."""
    metadata = metadata or {}
    payload = {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "amount": {
                    "currency_code": currency,
                    "value": f"{total_amount:.2f}",
                    "breakdown": {
                        "item_total": {"currency_code": currency, "value": f"{total_amount:.2f}"}
                    },
                },
                "items": [
                    {
                        "name": item["name"],
                        "description": item.get("description", ""),
                        "unit_amount": {
                            "currency_code": currency,
                            "value": f"{float(item['price']):.2f}",
                        },
                        "quantity": str(item.get("quantity", 1)),
                        "category": "DIGITAL_GOODS",
                    }
                    for item in items
                ],
                "custom_id": str(metadata.get("userId", "")) or None,
            }
        ],
        "application_context": {
            "brand_name": "WaddleBot Marketplace",
            "landing_page": "NO_PREFERENCE",
            "user_action": "PAY_NOW",
            "return_url": return_url,
            "cancel_url": cancel_url,
        },
    }
    return await _request(
        "POST",
        "/v2/checkout/orders",
        client_id=client_id,
        client_secret=client_secret,
        mode=mode,
        json_body=payload,
        client=client,
    )


async def capture_order(
    order_id: str,
    *,
    client_id: str,
    client_secret: str,
    mode: str,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    """Capture payment for an approved PayPal order."""
    return await _request(
        "POST",
        f"/v2/checkout/orders/{order_id}/capture",
        client_id=client_id,
        client_secret=client_secret,
        mode=mode,
        client=client,
    )


async def get_order(
    order_id: str,
    *,
    client_id: str,
    client_secret: str,
    mode: str,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    """Retrieve a PayPal order."""
    return await _request(
        "GET",
        f"/v2/checkout/orders/{order_id}",
        client_id=client_id,
        client_secret=client_secret,
        mode=mode,
        client=client,
    )


async def create_refund(
    capture_id: str,
    *,
    client_id: str,
    client_secret: str,
    mode: str,
    amount: float | None = None,
    currency: str = "USD",
    note: str = "",
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    """Refund a captured PayPal payment."""
    payload: dict[str, Any] = {"note_to_payer": note}
    if amount is not None:
        payload["amount"] = {"currency_code": currency, "value": f"{amount:.2f}"}
    return await _request(
        "POST",
        f"/v2/payments/captures/{capture_id}/refund",
        client_id=client_id,
        client_secret=client_secret,
        mode=mode,
        json_body=payload,
        client=client,
    )


async def get_refund(
    refund_id: str,
    *,
    client_id: str,
    client_secret: str,
    mode: str,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    """Retrieve a PayPal refund."""
    return await _request(
        "GET",
        f"/v2/payments/refunds/{refund_id}",
        client_id=client_id,
        client_secret=client_secret,
        mode=mode,
        client=client,
    )


# ---------------------------------------------------------------------------
# PayPal Subscriptions (Billing Plans API) -- honest 501s, matching Node
# ---------------------------------------------------------------------------
#
# `paypalService.js`'s own createSubscriptionPlan()/createSubscription()/
# cancelSubscription()/getSubscription() are themselves unimplemented in
# Node ("Note: ... requires REST API implementation... This is a
# placeholder", each one unconditionally `throw`s). Porting them as a clear
# 501 is not a regression versus Node's own shipped behavior -- unlike the
# webhook-verification stub above, this is genuinely out of scope for this
# billing-controller port (task instructions: stub only the outbound
# provider call, never the security checks -- these carry no security
# logic to begin with, only unimplemented business calls).


async def create_subscription(**_kwargs: Any) -> dict[str, Any]:
    """Not implemented -- matches Node's own `paypalService.js::createSubscription` stub."""
    raise ApiError(
        "PayPal subscription creation requires Billing Plans API integration "
        "(not implemented -- matches upstream Node stub)",
        501,
        "NOT_IMPLEMENTED",
    )


async def cancel_subscription(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
    """Not implemented -- matches Node's own `paypalService.js::cancelSubscription` stub."""
    raise ApiError(
        "PayPal subscription cancellation requires Billing Plans API integration "
        "(not implemented -- matches upstream Node stub)",
        501,
        "NOT_IMPLEMENTED",
    )


async def get_subscription(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
    """Not implemented -- matches Node's own `paypalService.js::getSubscription` stub."""
    raise ApiError(
        "PayPal get-subscription requires Billing Plans API integration "
        "(not implemented -- matches upstream Node stub)",
        501,
        "NOT_IMPLEMENTED",
    )
