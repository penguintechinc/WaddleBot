"""Idempotent webhook-event persistence -- the fix for Node's stub webhook handlers.

**The gap this closes**: `stripeService.js::handleCheckoutCompleted` and
every other `handle*` method in `stripeService.js`/`paypalService.js`
`console.log`s the event and returns a plain object -- literally
`// TODO: Store in database, send confirmation email, fulfill order`.
Nothing is ever written to `marketplace_subscriptions`/`marketplace_payments`/
`community_premium_subscriptions`. A Stripe/PayPal payment could succeed
and the app would never know -- no subscription activation, no payment
record, no seat unlock. This module is the missing persistence layer,
called only after `blueprints/v1/marketplace_webhooks.py` has verified the
provider signature (`services/stripe_service.py::verify_webhook_signature`/
`services/paypal_service.py::verify_webhook_signature`) -- never before.

**Idempotency** (task security mandate: "a replayed webhook must not
double-credit"): both providers redeliver events on transient failures/
timeouts, so every write here is dedupe-safe against a second delivery of
the SAME event:

- `record_payment()` -- SELECT-before-INSERT on `(payment_provider,
  external_payment_id)`. No new migration adds a DB-level UNIQUE
  constraint in this PR (`hub_api/PORTING.md` Gotcha #4's "no schema
  changes" convention) -- enforced at the application layer instead. A
  narrow race (two concurrent deliveries of the same event interleaving
  between the SELECT and the INSERT) is a known, documented limitation of
  an application-layer dedupe versus a DB constraint; providers do not
  deliver true concurrent duplicates of the same event in practice
  (sequential retries), and the follow-up migration to add a real UNIQUE
  index is out of scope for a "no schema changes" controller port.
- `activate_premium_subscription()`/`activate_module_subscription()` --
  natural upsert keyed on `community_premium_subscriptions`'s own
  `UNIQUE(community_id)` / `marketplace_subscriptions`'s own
  `UNIQUE(community_id, module_id)` constraints (both already exist in
  migrations 059/017) -- re-delivering the same "subscription activated"
  event twice converges to the same row state, not a second row.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True, frozen=True)
class WebhookResult:
    """What a webhook handler did -- returned to the blueprint for the response body."""

    processed: bool
    event_type: str
    detail: str = ""


def record_payment(
    dal: Any,
    *,
    provider: str,
    external_payment_id: str | None,
    community_id: int | None,
    module_id: int | None,
    subscription_id: int | None,
    amount_cents: int,
    currency: str,
    status: str,
    platform_fee_cents: int = 0,
    developer_amount_cents: int = 0,
    metadata: dict[str, Any] | None = None,
) -> tuple[int, bool]:
    """Idempotent insert into `marketplace_payments`. Returns `(row_id, created)`.

    `created=False` means a row for this `(provider, external_payment_id)`
    already existed -- a replayed webhook delivery, not a new payment. The
    existing row is returned unchanged (no double-credit).
    """
    if external_payment_id:
        existing = (
            dal(
                (dal.marketplace_payments.payment_provider == provider)
                & (dal.marketplace_payments.external_payment_id == external_payment_id)
            )
            .select()
            .first()
        )
        if existing is not None:
            return int(existing.id), False

    new_id = dal.marketplace_payments.insert(
        subscription_id=subscription_id,
        community_id=community_id,
        module_id=module_id,
        payment_provider=provider,
        external_payment_id=external_payment_id,
        amount_cents=amount_cents,
        currency=currency,
        status=status,
        platform_fee_cents=platform_fee_cents,
        developer_amount_cents=developer_amount_cents,
        created_at=dt.datetime.utcnow(),
        metadata=metadata or {},
    )
    dal.commit()
    return int(new_id), True


def _sub_field(provider: str) -> str:
    return "stripe_subscription_id" if provider == "stripe" else "paypal_subscription_id"


def activate_premium_subscription(
    dal: Any,
    *,
    community_id: int,
    provider: str,
    provider_subscription_id: str,
    current_period_end: dt.datetime | None = None,
) -> bool:
    """Idempotent activate/upsert of `community_premium_subscriptions`; `True` iff state changed."""
    field_name = _sub_field(provider)
    row = dal(dal.community_premium_subscriptions.community_id == community_id).select().first()
    if (
        row is not None
        and getattr(row, field_name) == provider_subscription_id
        and row.status == "active"
    ):
        return False  # replay -- already active with this exact provider subscription id

    now = dt.datetime.utcnow()
    if row is None:
        insert_kwargs: dict[str, Any] = {
            "community_id": community_id,
            "status": "active",
            field_name: provider_subscription_id,
            "current_seat_count": 0,
            "base_price_cents": 500,
            "overage_price_cents": 10,
            "base_seat_limit": 50,
            "created_at": now,
            "updated_at": now,
        }
        if current_period_end is not None:
            insert_kwargs["current_period_end"] = current_period_end
        dal.community_premium_subscriptions.insert(**insert_kwargs)
    else:
        update_kwargs: dict[str, Any] = {
            "status": "active",
            field_name: provider_subscription_id,
            "updated_at": now,
        }
        if current_period_end is not None:
            update_kwargs["current_period_end"] = current_period_end
        dal(dal.community_premium_subscriptions.id == row.id).update(**update_kwargs)
    dal.commit()
    return True


def cancel_premium_subscription(dal: Any, *, provider: str, provider_subscription_id: str) -> bool:
    """Idempotent cancel of `community_premium_subscriptions` by provider subscription id."""
    field_name = _sub_field(provider)
    row = (
        dal(dal.community_premium_subscriptions[field_name] == provider_subscription_id)
        .select()
        .first()
    )
    if row is None or row.status == "canceled":
        return False
    dal(dal.community_premium_subscriptions.id == row.id).update(
        status="canceled", cancel_at_period_end=True, updated_at=dt.datetime.utcnow()
    )
    dal.commit()
    return True


def activate_module_subscription(
    dal: Any,
    *,
    community_id: int,
    module_id: int,
    provider: str,
    provider_subscription_id: str,
    tenant_id: int | None = None,
) -> bool:
    """Idempotent activate/upsert of `marketplace_subscriptions` (per-module install billing)."""
    field_name = _sub_field(provider)
    row = (
        dal(
            (dal.marketplace_subscriptions.community_id == community_id)
            & (dal.marketplace_subscriptions.module_id == module_id)
        )
        .select()
        .first()
    )
    if (
        row is not None
        and getattr(row, field_name) == provider_subscription_id
        and row.status == "active"
    ):
        return False

    now = dt.datetime.utcnow()
    if row is None:
        dal.marketplace_subscriptions.insert(
            community_id=community_id,
            module_id=module_id,
            tenant_id=tenant_id,
            status="active",
            is_enabled=True,
            **{field_name: provider_subscription_id},
            subscribed_at=now,
        )
    else:
        dal(dal.marketplace_subscriptions.id == row.id).update(
            status="active", **{field_name: provider_subscription_id}
        )
    dal.commit()
    return True


def cancel_module_subscription(dal: Any, *, provider: str, provider_subscription_id: str) -> bool:
    """Idempotent cancel of `marketplace_subscriptions` by provider subscription id."""
    field_name = _sub_field(provider)
    row = (
        dal(dal.marketplace_subscriptions[field_name] == provider_subscription_id).select().first()
    )
    if row is None or row.status == "canceled":
        return False
    dal(dal.marketplace_subscriptions.id == row.id).update(
        status="canceled", canceled_at=dt.datetime.utcnow()
    )
    dal.commit()
    return True


# ---------------------------------------------------------------------------
# Provider event dispatch
# ---------------------------------------------------------------------------


def process_stripe_event(dal: Any, event: dict[str, Any]) -> WebhookResult:
    """Dispatch a VERIFIED Stripe event (`services.stripe_service.parse_webhook_event`'s output)."""
    event_type = event.get("type", "")
    data_object = event.get("data", {}).get("object", {})
    event_id = event.get("id")

    if event_type == "checkout.session.completed":
        metadata = data_object.get("metadata") or {}
        community_id = metadata.get("communityId")
        payment_intent = data_object.get("payment_intent")
        external_id = payment_intent if isinstance(payment_intent, str) else event_id

        if metadata.get("type") == "community_premium" and community_id:
            activate_premium_subscription(
                dal,
                community_id=int(community_id),
                provider="stripe",
                provider_subscription_id=str(data_object.get("subscription") or external_id),
            )
        elif community_id and metadata.get("moduleId"):
            activate_module_subscription(
                dal,
                community_id=int(community_id),
                module_id=int(metadata["moduleId"]),
                provider="stripe",
                provider_subscription_id=str(data_object.get("subscription") or external_id),
            )

        amount_total = data_object.get("amount_total")
        if amount_total is not None:
            record_payment(
                dal,
                provider="stripe",
                external_payment_id=external_id,
                community_id=int(community_id) if community_id else None,
                module_id=int(metadata["moduleId"]) if metadata.get("moduleId") else None,
                subscription_id=None,
                amount_cents=int(amount_total),
                currency=str(data_object.get("currency", "usd")).upper(),
                status="succeeded",
                metadata=metadata,
            )
        return WebhookResult(True, event_type)

    if event_type == "invoice.payment_succeeded":
        subscription_id = data_object.get("subscription")
        amount_paid = data_object.get("amount_paid", 0)
        record_payment(
            dal,
            provider="stripe",
            external_payment_id=data_object.get("id"),
            community_id=None,
            module_id=None,
            subscription_id=None,
            amount_cents=int(amount_paid),
            currency=str(data_object.get("currency", "usd")).upper(),
            status="succeeded",
            metadata={"stripeSubscriptionId": subscription_id} if subscription_id else {},
        )
        return WebhookResult(True, event_type)

    if event_type in ("customer.subscription.deleted", "customer.subscription.updated"):
        subscription_id = data_object.get("id")
        status = data_object.get("status")
        if event_type == "customer.subscription.deleted" or status in ("canceled", "unpaid"):
            changed_premium = cancel_premium_subscription(
                dal, provider="stripe", provider_subscription_id=subscription_id
            )
            changed_module = cancel_module_subscription(
                dal, provider="stripe", provider_subscription_id=subscription_id
            )
            return WebhookResult(changed_premium or changed_module, event_type)
        return WebhookResult(False, event_type, "no-op status transition")

    return WebhookResult(False, event_type, "unhandled event type")


def process_paypal_event(dal: Any, event: dict[str, Any]) -> WebhookResult:
    """Dispatch a VERIFIED PayPal event (`paypal_service.verify_webhook_signature` already ran)."""
    event_type = event.get("event_type", "")
    resource = event.get("resource", {})
    event_id = event.get("id")

    if event_type == "PAYMENT.CAPTURE.COMPLETED":
        amount = resource.get("amount", {})
        custom_id = resource.get("custom_id")
        record_payment(
            dal,
            provider="paypal",
            external_payment_id=resource.get("id") or event_id,
            community_id=int(custom_id) if custom_id and str(custom_id).isdigit() else None,
            module_id=None,
            subscription_id=None,
            amount_cents=round(float(amount.get("value", 0)) * 100),
            currency=str(amount.get("currency_code", "USD")),
            status="succeeded",
            metadata={"paypalCaptureId": resource.get("id")},
        )
        return WebhookResult(True, event_type)

    if event_type == "BILLING.SUBSCRIPTION.ACTIVATED":
        custom_id = resource.get("custom_id")
        if custom_id and str(custom_id).isdigit():
            activate_premium_subscription(
                dal,
                community_id=int(custom_id),
                provider="paypal",
                provider_subscription_id=resource.get("id"),
            )
        return WebhookResult(bool(custom_id), event_type)

    if event_type in ("BILLING.SUBSCRIPTION.CANCELLED", "BILLING.SUBSCRIPTION.EXPIRED"):
        subscription_id = resource.get("id")
        changed_premium = cancel_premium_subscription(
            dal, provider="paypal", provider_subscription_id=subscription_id
        )
        changed_module = cancel_module_subscription(
            dal, provider="paypal", provider_subscription_id=subscription_id
        )
        return WebhookResult(changed_premium or changed_module, event_type)

    return WebhookResult(False, event_type, "unhandled event type")
