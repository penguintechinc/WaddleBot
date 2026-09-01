"""`services/paypal_service.py` -- outbound order/refund coverage + honest subscription stubs.

Complements `test_paypal_service.py` (webhook-signature verification).
"""

from __future__ import annotations

import httpx
import pytest

from services import paypal_service
from services.errors import ApiError

CLIENT_ID = "cid"
CLIENT_SECRET = "csecret"


def _transport(order_body: dict | None = None, status_code: int = 200) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/oauth2/token"):
            return httpx.Response(200, json={"access_token": "tok"})
        return httpx.Response(
            status_code, json=order_body or {"id": "ORDER-1", "status": "CREATED"}
        )

    return httpx.MockTransport(handler)


class TestOrders:
    async def test_create_order(self) -> None:
        transport = _transport(
            {"id": "ORDER-1", "links": [{"rel": "approve", "href": "https://approve"}]}
        )
        async with httpx.AsyncClient(transport=transport) as client:
            result = await paypal_service.create_order(
                client_id=CLIENT_ID,
                client_secret=CLIENT_SECRET,
                mode="sandbox",
                items=[{"name": "Widget", "price": 10.0, "quantity": 1}],
                total_amount=10.0,
                return_url="https://x/success",
                cancel_url="https://x/cancel",
                metadata={"userId": "5"},
                client=client,
            )
        assert result["id"] == "ORDER-1"

    async def test_capture_order(self) -> None:
        transport = _transport({"id": "ORDER-1", "status": "COMPLETED"})
        async with httpx.AsyncClient(transport=transport) as client:
            result = await paypal_service.capture_order(
                "ORDER-1",
                client_id=CLIENT_ID,
                client_secret=CLIENT_SECRET,
                mode="sandbox",
                client=client,
            )
        assert result["status"] == "COMPLETED"

    async def test_get_order(self) -> None:
        transport = _transport({"id": "ORDER-1"})
        async with httpx.AsyncClient(transport=transport) as client:
            result = await paypal_service.get_order(
                "ORDER-1",
                client_id=CLIENT_ID,
                client_secret=CLIENT_SECRET,
                mode="sandbox",
                client=client,
            )
        assert result["id"] == "ORDER-1"

    async def test_error_response_raises_api_error(self) -> None:
        transport = _transport({"message": "bad request"}, status_code=400)
        async with httpx.AsyncClient(transport=transport) as client:
            with pytest.raises(ApiError) as excinfo:
                await paypal_service.get_order(
                    "ORDER-1",
                    client_id=CLIENT_ID,
                    client_secret=CLIENT_SECRET,
                    mode="sandbox",
                    client=client,
                )
            assert excinfo.value.status_code == 400


class TestRefunds:
    async def test_create_refund(self) -> None:
        transport = _transport({"id": "REFUND-1", "status": "COMPLETED"})
        async with httpx.AsyncClient(transport=transport) as client:
            result = await paypal_service.create_refund(
                "CAPTURE-1",
                client_id=CLIENT_ID,
                client_secret=CLIENT_SECRET,
                mode="sandbox",
                amount=5.0,
                client=client,
            )
        assert result["status"] == "COMPLETED"

    async def test_get_refund(self) -> None:
        transport = _transport({"id": "REFUND-1"})
        async with httpx.AsyncClient(transport=transport) as client:
            result = await paypal_service.get_refund(
                "REFUND-1",
                client_id=CLIENT_ID,
                client_secret=CLIENT_SECRET,
                mode="sandbox",
                client=client,
            )
        assert result["id"] == "REFUND-1"


class TestApiBase:
    def test_live_mode(self) -> None:
        assert paypal_service.api_base("live") == paypal_service.PAYPAL_LIVE_BASE

    def test_sandbox_default(self) -> None:
        assert paypal_service.api_base("sandbox") == paypal_service.PAYPAL_SANDBOX_BASE
        assert paypal_service.api_base("anything-else") == paypal_service.PAYPAL_SANDBOX_BASE


class TestSubscriptionStubs:
    """Matches Node's own `paypalService.js` unimplemented subscription methods -- honest 501s."""

    async def test_create_subscription_raises_501(self) -> None:
        with pytest.raises(ApiError) as excinfo:
            await paypal_service.create_subscription()
        assert excinfo.value.status_code == 501

    async def test_cancel_subscription_raises_501(self) -> None:
        with pytest.raises(ApiError) as excinfo:
            await paypal_service.cancel_subscription()
        assert excinfo.value.status_code == 501

    async def test_get_subscription_raises_501(self) -> None:
        with pytest.raises(ApiError) as excinfo:
            await paypal_service.get_subscription()
        assert excinfo.value.status_code == 501
