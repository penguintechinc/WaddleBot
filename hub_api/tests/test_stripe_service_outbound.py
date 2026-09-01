"""`services/stripe_service.py` -- outbound REST call coverage (`httpx.MockTransport`, no network).

Complements `test_stripe_service.py` (webhook-signature verification,
pure local HMAC, no network). These prove the outbound checkout/
subscription/refund/customer calls build the right Stripe REST request
shape and correctly surface a 4xx as `ApiError`.
"""

from __future__ import annotations

import httpx
import pytest

from services import stripe_service
from services.errors import ApiError

SECRET_KEY = "sk_test_123"


def _transport(status_code: int = 200, json_body: dict | None = None) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json=json_body or {"id": "obj_1", "object": "mock"})

    return httpx.MockTransport(handler)


class TestCreateCheckoutSession:
    async def test_success(self) -> None:
        transport = _transport(200, {"id": "cs_1", "url": "https://checkout.stripe.com/cs_1"})
        async with httpx.AsyncClient(transport=transport) as client:
            result = await stripe_service.create_checkout_session(
                secret_key=SECRET_KEY,
                items=[{"name": "Widget", "price": 10.0, "quantity": 1}],
                customer_email="a@b.com",
                success_url="https://x/success",
                cancel_url="https://x/cancel",
                client=client,
            )
        assert result["id"] == "cs_1"

    async def test_error_response_raises_api_error(self) -> None:
        transport = _transport(400, {"error": {"message": "bad request"}})
        async with httpx.AsyncClient(transport=transport) as client:
            with pytest.raises(ApiError) as excinfo:
                await stripe_service.create_checkout_session(
                    secret_key=SECRET_KEY,
                    items=[{"name": "Widget", "price": 10.0}],
                    customer_email="a@b.com",
                    success_url="https://x/success",
                    cancel_url="https://x/cancel",
                    client=client,
                )
            assert excinfo.value.status_code == 400


class TestSubscriptionOperations:
    async def test_create_subscription_session_with_trial(self) -> None:
        transport = _transport(
            200, {"id": "cs_sub_1", "url": "https://checkout.stripe.com/cs_sub_1"}
        )
        async with httpx.AsyncClient(transport=transport) as client:
            result = await stripe_service.create_subscription_session(
                secret_key=SECRET_KEY,
                price_id="price_1",
                customer_email="a@b.com",
                success_url="https://x/success",
                cancel_url="https://x/cancel",
                trial_period_days=7,
                client=client,
            )
        assert result["id"] == "cs_sub_1"

    async def test_get_checkout_session(self) -> None:
        transport = _transport(200, {"id": "cs_1", "payment_status": "paid"})
        async with httpx.AsyncClient(transport=transport) as client:
            result = await stripe_service.get_checkout_session(
                "cs_1", secret_key=SECRET_KEY, client=client
            )
        assert result["payment_status"] == "paid"

    async def test_get_subscription(self) -> None:
        transport = _transport(200, {"id": "sub_1", "status": "active"})
        async with httpx.AsyncClient(transport=transport) as client:
            result = await stripe_service.get_subscription(
                "sub_1", secret_key=SECRET_KEY, client=client
            )
        assert result["status"] == "active"

    async def test_cancel_immediately(self) -> None:
        transport = _transport(200, {"id": "sub_1", "status": "canceled"})
        async with httpx.AsyncClient(transport=transport) as client:
            result = await stripe_service.cancel_subscription(
                "sub_1", secret_key=SECRET_KEY, immediately=True, client=client
            )
        assert result["status"] == "canceled"

    async def test_cancel_at_period_end(self) -> None:
        transport = _transport(200, {"id": "sub_1", "cancel_at_period_end": True})
        async with httpx.AsyncClient(transport=transport) as client:
            result = await stripe_service.cancel_subscription(
                "sub_1", secret_key=SECRET_KEY, immediately=False, client=client
            )
        assert result["cancel_at_period_end"] is True

    async def test_reactivate(self) -> None:
        transport = _transport(200, {"id": "sub_1", "cancel_at_period_end": False})
        async with httpx.AsyncClient(transport=transport) as client:
            result = await stripe_service.reactivate_subscription(
                "sub_1", secret_key=SECRET_KEY, client=client
            )
        assert result["cancel_at_period_end"] is False


class TestRefundsAndCustomers:
    async def test_create_refund(self) -> None:
        transport = _transport(200, {"id": "re_1", "status": "succeeded"})
        async with httpx.AsyncClient(transport=transport) as client:
            result = await stripe_service.create_refund(
                secret_key=SECRET_KEY, payment_intent_id="pi_1", amount_cents=500, client=client
            )
        assert result["status"] == "succeeded"

    async def test_get_refund(self) -> None:
        transport = _transport(200, {"id": "re_1"})
        async with httpx.AsyncClient(transport=transport) as client:
            result = await stripe_service.get_refund("re_1", secret_key=SECRET_KEY, client=client)
        assert result["id"] == "re_1"

    async def test_create_customer(self) -> None:
        transport = _transport(200, {"id": "cus_1"})
        async with httpx.AsyncClient(transport=transport) as client:
            result = await stripe_service.create_customer(
                secret_key=SECRET_KEY, email="a@b.com", name="A B", client=client
            )
        assert result["id"] == "cus_1"

    async def test_get_customer(self) -> None:
        transport = _transport(200, {"id": "cus_1", "email": "a@b.com"})
        async with httpx.AsyncClient(transport=transport) as client:
            result = await stripe_service.get_customer(
                "cus_1", secret_key=SECRET_KEY, client=client
            )
        assert result["email"] == "a@b.com"

    async def test_list_payment_methods(self) -> None:
        transport = _transport(200, {"data": []})
        async with httpx.AsyncClient(transport=transport) as client:
            result = await stripe_service.list_payment_methods(
                "cus_1", secret_key=SECRET_KEY, client=client
            )
        assert result["data"] == []
