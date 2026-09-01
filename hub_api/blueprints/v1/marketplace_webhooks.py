"""v1 `marketplace.webhooks` group -- Stripe/PayPal payment-provider callbacks (migration plan M4).

Ports `routes/webhooks.js` (`POST /stripe`, `POST /paypal`). Provider
callbacks, not user requests -- **no `tenant_middleware`/`require_scope`**
(matches `hub_api/PORTING.md`'s pre-auth-route pattern: there is no JWT on
a webhook delivery), but that does NOT mean unauthenticated in the
security.md sense. The provider's cryptographic signature is the auth
mechanism here, verified BEFORE anything in the payload is trusted:

- Stripe: `services.stripe_service.parse_webhook_event()` (HMAC-SHA256
  over `Stripe-Signature`, stdlib `hmac`/`hashlib` -- see that module's
  docstring for the full algorithm).
- PayPal: `services.paypal_service.verify_webhook_signature()` (PayPal's
  own `POST /v1/notifications/verify-webhook-signature` REST endpoint).

**Both of Node's provider webhook handlers were stubs that never persist**
(`hub_api/PORTING.md`/task security brief) -- `stripeService.js::
handleWebhook` logs and returns an in-memory object with a `// TODO: Store
in database` comment; `paypalService.js::verifyWebhookSignature`
unconditionally `return true`s without ever calling PayPal's verification
endpoint (an unauthenticated payment webhook -- see `paypal_service.py`'s
module docstring). This blueprint fixes both: real signature verification
gates every request, and `services.marketplace_webhook_service` persists
the result idempotently (dedup key = provider + external event/payment
id) so a provider's automatic retry of the same event never double-credits
a subscription or payment record.
"""

from __future__ import annotations

from typing import Any, cast

from quart import Blueprint, current_app, request

from services import marketplace_webhook_service as webhook_svc
from services import paypal_service, stripe_service
from services.errors import ApiError

webhooks_bp = Blueprint(
    "v1_marketplace_webhooks", __name__, url_prefix="/api/v1/marketplace/webhooks"
)


@webhooks_bp.route("/stripe", methods=["POST"])
async def stripe_webhook() -> tuple[dict[str, Any], int]:
    """`POST /webhooks/stripe` -- HMAC-verified, then idempotently persisted."""
    cfg = current_app.config["HUB_API_CONFIG"]
    # `Request.get_data()`'s return type is `str | bytes` (as_text-dependent)
    # per Quart's own stubs -- default `as_text=False` always returns bytes
    # at runtime, `cast` narrows it for mypy --strict.
    raw_body = cast(bytes, await request.get_data(as_text=False))
    sig_header = request.headers.get("Stripe-Signature")

    if not cfg.stripe_webhook_secret:
        # Fail closed -- an unconfigured secret must never be treated as
        # "verification not required" (see config.py's field docstring).
        return {"received": False, "error": "Webhook not configured"}, 400

    try:
        event = stripe_service.parse_webhook_event(raw_body, sig_header, cfg.stripe_webhook_secret)
    except ApiError as exc:
        return {"received": False, "error": exc.message}, exc.status_code

    dal = current_app.config["dal"]
    result = webhook_svc.process_stripe_event(dal, event)
    return {
        "received": True,
        "success": True,
        "eventType": result.event_type,
        "processed": result.processed,
    }, 200


@webhooks_bp.route("/paypal", methods=["POST"])
async def paypal_webhook() -> tuple[dict[str, Any], int]:
    """`POST /webhooks/paypal` -- verified via PayPal's REST API, then idempotently persisted."""
    cfg = current_app.config["HUB_API_CONFIG"]
    raw_body = cast(bytes, await request.get_data(as_text=False))
    headers = dict(request.headers)

    if not cfg.paypal_webhook_id or not cfg.paypal_client_id or not cfg.paypal_client_secret:
        return {"received": False, "error": "Webhook not configured"}, 400

    verified = await paypal_service.verify_webhook_signature(
        headers,
        raw_body,
        webhook_id=cfg.paypal_webhook_id,
        client_id=cfg.paypal_client_id,
        client_secret=cfg.paypal_client_secret,
        mode=cfg.paypal_mode,
    )
    if not verified:
        return {"received": False, "error": "Invalid webhook signature"}, 400

    import json

    try:
        event = json.loads(raw_body)
    except (ValueError, UnicodeDecodeError):
        return {"received": False, "error": "Malformed webhook payload"}, 400

    dal = current_app.config["dal"]
    result = webhook_svc.process_paypal_event(dal, event)
    return {
        "received": True,
        "success": True,
        "eventType": result.event_type,
        "processed": result.processed,
    }, 200


BLUEPRINTS: list[Blueprint] = [webhooks_bp]
