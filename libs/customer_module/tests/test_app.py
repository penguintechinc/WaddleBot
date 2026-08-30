"""
Customer Module MVP skeleton tests
======================================

Exercises the worked gate example wired end-to-end in
:mod:`customer_module.app` -- ``POST /customer/accounts`` guarded on
``waddles.customer.accounts``. Unlike Bot's shoutout gate (a separate
service with a heavy dependency chain, tested only at the contract level
in ``test_customer_features.py``-equivalent fashion), Customer's stub has
no such dependencies, so the actual Quart handler is exercised here via
``app.test_client()`` with ``feature_enabled`` mocked -- a regression in
the flag name or the no-op status code is caught directly, not just at the
contract layer.
"""

from __future__ import annotations

from typing import Any

import pytest
from customer_module.app import app


class _FakeFeatureEnabled:
    """Records the flag/tenant/community it was called with and returns a fixed verdict."""

    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled
        self.calls: list[dict[str, Any]] = []

    async def __call__(
        self,
        flag_key: str,
        *,
        tenant: str,
        community: int | None = None,
        default: bool = False,
    ) -> bool:
        self.calls.append({"flag_key": flag_key, "tenant": tenant, "community": community})
        return self.enabled


@pytest.fixture
def client():
    return app.test_client()


class TestCreateAccountGate:
    async def test_flag_off_no_ops_with_404(
        self, client: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake = _FakeFeatureEnabled(enabled=False)
        monkeypatch.setattr("customer_module.app.feature_enabled", fake)

        response = await client.post("/customer/accounts", json={"name": "Acme"})

        assert response.status_code == 404
        body = await response.get_json()
        assert body["success"] is False
        assert fake.calls == [
            {"flag_key": "waddles.customer.accounts", "tenant": "global", "community": None}
        ]

    async def test_flag_on_succeeds(self, client: Any, monkeypatch: pytest.MonkeyPatch) -> None:
        fake = _FakeFeatureEnabled(enabled=True)
        monkeypatch.setattr("customer_module.app.feature_enabled", fake)

        response = await client.post(
            "/customer/accounts", json={"name": "Acme", "community_id": 42}
        )

        assert response.status_code == 200
        body = await response.get_json()
        assert body["success"] is True
        assert body["data"] == {"id": "stub-account", "name": "Acme"}
        assert fake.calls == [
            {"flag_key": "waddles.customer.accounts", "tenant": "global", "community": 42}
        ]
