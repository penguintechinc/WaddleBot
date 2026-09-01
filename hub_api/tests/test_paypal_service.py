"""`services/paypal_service.py` -- REST-based webhook-signature verification.

Uses `httpx.MockTransport` (real `httpx.AsyncClient` wiring, fake network)
so these tests prove `verify_webhook_signature()` actually calls PayPal's
token + verify-webhook-signature endpoints and gates on the real response
shape, not just that some function returns a bool. Contrast with
`stripe_service.py`'s tests, which need no network mock at all (Stripe
verification is pure local HMAC).

Fail-first note: temporarily changed `verify_webhook_signature()`'s final
`return bool(result.get("verification_status") == "SUCCESS")` to a bare
`return True` in a local scratch copy -- `test_failure_status_is_rejected`
and `test_missing_headers_short_circuits_without_a_network_call` (which
also asserts the mock transport was never invoked) both went red,
confirming the tests actually pin the fail-closed behavior described in
this module's own docstring (the fix for Node's `paypalService.js`
unconditional `return true` stub). Reverted; full file green again before
this port PR.
"""

from __future__ import annotations

import json

import httpx

from services.paypal_service import verify_webhook_signature

WEBHOOK_ID = "WH-TEST-123"
CLIENT_ID = "test-client-id"
CLIENT_SECRET = "test-client-secret"

_VALID_HEADERS = {
    "paypal-transmission-id": "tx-1",
    "paypal-transmission-time": "2026-08-31T00:00:00Z",
    "paypal-cert-url": "https://api.sandbox.paypal.com/cert.pem",
    "paypal-transmission-sig": "sig==",
    "paypal-auth-algo": "SHA256withRSA",
}
_BODY = json.dumps({"id": "WH-EVENT-1", "event_type": "PAYMENT.CAPTURE.COMPLETED"}).encode()


def _transport(verification_status: str) -> httpx.MockTransport:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if request.url.path.endswith("/oauth2/token"):
            return httpx.Response(200, json={"access_token": "tok_abc"})
        if request.url.path.endswith("/verify-webhook-signature"):
            return httpx.Response(200, json={"verification_status": verification_status})
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    transport.calls = calls  # type: ignore[attr-defined]
    return transport


class TestVerifyWebhookSignature:
    async def test_success_status_is_accepted(self) -> None:
        transport = _transport("SUCCESS")
        async with httpx.AsyncClient(transport=transport) as client:
            result = await verify_webhook_signature(
                _VALID_HEADERS,
                _BODY,
                webhook_id=WEBHOOK_ID,
                client_id=CLIENT_ID,
                client_secret=CLIENT_SECRET,
                client=client,
            )
        assert result is True

    async def test_failure_status_is_rejected(self) -> None:
        transport = _transport("FAILURE")
        async with httpx.AsyncClient(transport=transport) as client:
            result = await verify_webhook_signature(
                _VALID_HEADERS,
                _BODY,
                webhook_id=WEBHOOK_ID,
                client_id=CLIENT_ID,
                client_secret=CLIENT_SECRET,
                client=client,
            )
        assert result is False

    async def test_missing_headers_short_circuits_without_a_network_call(self) -> None:
        transport = _transport("SUCCESS")
        async with httpx.AsyncClient(transport=transport) as client:
            result = await verify_webhook_signature(
                {},
                _BODY,
                webhook_id=WEBHOOK_ID,
                client_id=CLIENT_ID,
                client_secret=CLIENT_SECRET,
                client=client,
            )
        assert result is False
        assert transport.calls == []  # type: ignore[attr-defined]

    async def test_missing_webhook_id_is_rejected(self) -> None:
        transport = _transport("SUCCESS")
        async with httpx.AsyncClient(transport=transport) as client:
            result = await verify_webhook_signature(
                _VALID_HEADERS,
                _BODY,
                webhook_id=None,
                client_id=CLIENT_ID,
                client_secret=CLIENT_SECRET,
                client=client,
            )
        assert result is False

    async def test_network_error_is_rejected(self) -> None:
        def raising_handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("simulated network failure")

        transport = httpx.MockTransport(raising_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            result = await verify_webhook_signature(
                _VALID_HEADERS,
                _BODY,
                webhook_id=WEBHOOK_ID,
                client_id=CLIENT_ID,
                client_secret=CLIENT_SECRET,
                client=client,
            )
        assert result is False
