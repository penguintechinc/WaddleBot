"""`services/marketplace_webhook_service.py` -- direct dispatch/persistence coverage.

Complements `test_v1_marketplace_webhooks_security.py` (blueprint-level
signature + idempotency) with branch coverage on event types the security
test file doesn't already exercise (module-subscription activation/
cancellation, PayPal capture/activation/cancellation, unhandled event
types).
"""

from __future__ import annotations

from typing import Any

import pytest

from services import marketplace_webhook_service as svc


@pytest.fixture
def seeded(marketplace_billing_db: Any) -> tuple[Any, int, int]:
    return marketplace_billing_db


class TestRecordPayment:
    def test_first_insert_is_created(self, seeded: Any) -> None:
        dal, _t, community_id = seeded
        row_id, created = svc.record_payment(
            dal,
            provider="stripe",
            external_payment_id="pi_a",
            community_id=community_id,
            module_id=None,
            subscription_id=None,
            amount_cents=1000,
            currency="USD",
            status="succeeded",
        )
        assert created is True
        assert row_id > 0

    def test_replay_is_not_created(self, seeded: Any) -> None:
        dal, _t, community_id = seeded
        first_id, _ = svc.record_payment(
            dal,
            provider="stripe",
            external_payment_id="pi_b",
            community_id=community_id,
            module_id=None,
            subscription_id=None,
            amount_cents=1000,
            currency="USD",
            status="succeeded",
        )
        second_id, created = svc.record_payment(
            dal,
            provider="stripe",
            external_payment_id="pi_b",
            community_id=community_id,
            module_id=None,
            subscription_id=None,
            amount_cents=1000,
            currency="USD",
            status="succeeded",
        )
        assert created is False
        assert second_id == first_id

    def test_missing_external_id_always_inserts(self, seeded: Any) -> None:
        dal, _t, community_id = seeded
        _id1, created1 = svc.record_payment(
            dal,
            provider="paypal",
            external_payment_id=None,
            community_id=community_id,
            module_id=None,
            subscription_id=None,
            amount_cents=100,
            currency="USD",
            status="succeeded",
        )
        _id2, created2 = svc.record_payment(
            dal,
            provider="paypal",
            external_payment_id=None,
            community_id=community_id,
            module_id=None,
            subscription_id=None,
            amount_cents=100,
            currency="USD",
            status="succeeded",
        )
        assert created1 is True
        assert (
            created2 is True
        )  # no dedupe key -> both persisted (matches provider having no event id)


class TestModuleSubscriptionActivation:
    def test_activate_then_replay_is_noop(self, seeded: Any) -> None:
        dal, _t, community_id = seeded
        module_id = int(dal.hub_modules.insert(name="m1", is_published=True))
        dal.commit()
        first = svc.activate_module_subscription(
            dal,
            community_id=community_id,
            module_id=module_id,
            provider="stripe",
            provider_subscription_id="sub_1",
        )
        second = svc.activate_module_subscription(
            dal,
            community_id=community_id,
            module_id=module_id,
            provider="stripe",
            provider_subscription_id="sub_1",
        )
        assert first is True
        assert second is False
        rows = dal(
            (dal.marketplace_subscriptions.community_id == community_id)
            & (dal.marketplace_subscriptions.module_id == module_id)
        ).select()
        assert len(rows) == 1

    def test_cancel_module_subscription(self, seeded: Any) -> None:
        dal, _t, community_id = seeded
        module_id = int(dal.hub_modules.insert(name="m2", is_published=True))
        dal.commit()
        svc.activate_module_subscription(
            dal,
            community_id=community_id,
            module_id=module_id,
            provider="stripe",
            provider_subscription_id="sub_2",
        )
        changed = svc.cancel_module_subscription(
            dal, provider="stripe", provider_subscription_id="sub_2"
        )
        assert changed is True
        again = svc.cancel_module_subscription(
            dal, provider="stripe", provider_subscription_id="sub_2"
        )
        assert again is False  # already canceled -- replay is a no-op

    def test_cancel_unknown_subscription_is_false(self, seeded: Any) -> None:
        dal, _t, _c = seeded
        assert (
            svc.cancel_module_subscription(dal, provider="stripe", provider_subscription_id="nope")
            is False
        )


class TestPremiumCancelUnknown:
    def test_cancel_unknown_is_false(self, seeded: Any) -> None:
        dal, _t, _c = seeded
        assert (
            svc.cancel_premium_subscription(dal, provider="stripe", provider_subscription_id="none")
            is False
        )


class TestProcessStripeEvent:
    def test_unhandled_event_type(self, seeded: Any) -> None:
        dal, _t, _c = seeded
        result = svc.process_stripe_event(
            dal, {"id": "evt_x", "type": "some.unknown.event", "data": {"object": {}}}
        )
        assert result.processed is False
        assert result.event_type == "some.unknown.event"

    def test_no_op_subscription_update_status(self, seeded: Any) -> None:
        dal, _t, _c = seeded
        result = svc.process_stripe_event(
            dal,
            {
                "id": "evt_y",
                "type": "customer.subscription.updated",
                "data": {"object": {"id": "sub_x", "status": "active"}},
            },
        )
        assert result.processed is False


class TestProcessPaypalEvent:
    def test_capture_completed_persists_payment(self, seeded: Any) -> None:
        dal, _t, community_id = seeded
        event = {
            "id": "WH-1",
            "event_type": "PAYMENT.CAPTURE.COMPLETED",
            "resource": {
                "id": "CAPTURE-1",
                "amount": {"value": "5.00", "currency_code": "USD"},
                "custom_id": str(community_id),
            },
        }
        result = svc.process_paypal_event(dal, event)
        assert result.processed is True
        payment = dal(dal.marketplace_payments.external_payment_id == "CAPTURE-1").select().first()
        assert payment is not None
        assert payment.amount_cents == 500

    def test_subscription_activated_without_custom_id_is_not_processed(self, seeded: Any) -> None:
        dal, _t, _c = seeded
        event = {
            "id": "WH-2",
            "event_type": "BILLING.SUBSCRIPTION.ACTIVATED",
            "resource": {"id": "SUB-1"},
        }
        result = svc.process_paypal_event(dal, event)
        assert result.processed is False

    def test_subscription_activated_with_custom_id_activates_premium(self, seeded: Any) -> None:
        dal, _t, community_id = seeded
        event = {
            "id": "WH-3",
            "event_type": "BILLING.SUBSCRIPTION.ACTIVATED",
            "resource": {"id": "SUB-2", "custom_id": str(community_id)},
        }
        result = svc.process_paypal_event(dal, event)
        assert result.processed is True
        row = dal(dal.community_premium_subscriptions.community_id == community_id).select().first()
        assert row is not None
        assert row.status == "active"

    def test_subscription_cancelled(self, seeded: Any) -> None:
        dal, _t, community_id = seeded
        activate_event = {
            "id": "WH-4",
            "event_type": "BILLING.SUBSCRIPTION.ACTIVATED",
            "resource": {"id": "SUB-3", "custom_id": str(community_id)},
        }
        svc.process_paypal_event(dal, activate_event)
        cancel_event = {
            "id": "WH-5",
            "event_type": "BILLING.SUBSCRIPTION.CANCELLED",
            "resource": {"id": "SUB-3"},
        }
        result = svc.process_paypal_event(dal, cancel_event)
        assert result.processed is True
        row = dal(dal.community_premium_subscriptions.community_id == community_id).select().first()
        assert row.status == "canceled"

    def test_unhandled_paypal_event_type(self, seeded: Any) -> None:
        dal, _t, _c = seeded
        result = svc.process_paypal_event(
            dal, {"id": "WH-9", "event_type": "SOME.OTHER.EVENT", "resource": {}}
        )
        assert result.processed is False
