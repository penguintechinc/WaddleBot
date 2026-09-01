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

``TestCreateAccountTenantIsolation`` covers the tenant-isolation audit
(2026-08-30): ``tenant_middleware`` was missing from this handler, so
``get_tenant_context(request)`` always returned ``None`` and every request
silently ran as ``DEFAULT_TENANT_SLUG`` with no auth at all. Fail-first
proof: with ``@tenant_middleware`` temporarily removed from
``create_account``, ``test_no_jwt_is_rejected_not_run_as_default_tenant``
and ``test_invalid_jwt_returns_401`` both failed (200, flag check ran
unauthenticated) before the fix, and pass after it.

``TestCreateAccountScopeEnforcement`` covers the HTTP-layer scope check
added on top of that fix: ``@require_scope("customer.account:write")`` now
sits between ``tenant_middleware`` and ``async_endpoint`` on this handler,
per ``customer_module/features.py``'s ``customer.account`` Feature
contract (``requires_scopes == {"customer.account:write"}``). Fail-first
proof: with ``@require_scope(...)`` temporarily removed from
``create_account``, ``test_missing_scope_is_403`` and
``test_wrong_scope_is_403`` both failed (200, flag check ran with no scope
check at all) before the fix, and pass after it. ``_bearer_token``'s
default ``scope`` is the exact required scope, so every pre-existing test
above that doesn't override it keeps exercising the real, now-enforced
path.
"""

from __future__ import annotations

from typing import Any

import pytest
from customer_module.app import app
from flask_core.auth import create_jwt_token
from flask_core.tenancy import TenantContext

# tenant_middleware falls back to this exact default when SECRET_KEY isn't
# set in the environment (flask_core/tenancy.py) -- matches what the test
# process runs with unless a repo-wide .env overrides it.
_SECRET_KEY = "change-me-in-production"


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


def _bearer_token(tenant: str, scope: str = "customer.account:write") -> str:
    """A valid JWT scoped to `tenant`, signed with tenant_middleware's default
    secret. `scope` defaults to `create_account`'s required scope so every
    pre-existing caller of this helper keeps exercising the real,
    now-enforced `@require_scope` path without having to be touched."""
    return create_jwt_token(
        user_id="u1",
        username="alice",
        email="alice@example.com",
        roles=["viewer"],
        secret_key=_SECRET_KEY,
        tenant=tenant,
        scope=scope,
    )


@pytest.fixture
def client():
    return app.test_client()


@pytest.fixture
def fake_tenant_resolution(monkeypatch: pytest.MonkeyPatch):
    """Stub `resolve_tenant_context` so `tenant_middleware` doesn't need a
    real DB-backed `tenants` table. This isolates what this suite is
    actually proving -- that `tenant_middleware` is applied to
    `create_account` at all -- from `resolve_tenant_context`'s own DB
    lookup behavior, which is unit-tested directly in
    `libs/flask_core/tests/test_tenancy.py`.
    """

    async def _resolve(payload: dict[str, Any], dal: Any) -> TenantContext:
        return TenantContext(tenant_id=1, tenant_slug=payload["tenant"])

    monkeypatch.setattr("flask_core.tenancy.resolve_tenant_context", _resolve)


class TestCreateAccountGate:
    async def test_flag_off_no_ops_with_404(
        self, client: Any, monkeypatch: pytest.MonkeyPatch, fake_tenant_resolution: None
    ) -> None:
        fake = _FakeFeatureEnabled(enabled=False)
        monkeypatch.setattr("customer_module.app.feature_enabled", fake)
        token = _bearer_token(tenant="global")

        response = await client.post(
            "/customer/accounts",
            json={"name": "Acme"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404
        body = await response.get_json()
        assert body["success"] is False
        assert fake.calls == [
            {"flag_key": "waddles.customer.accounts", "tenant": "global", "community": None}
        ]

    async def test_flag_on_succeeds(
        self, client: Any, monkeypatch: pytest.MonkeyPatch, fake_tenant_resolution: None
    ) -> None:
        fake = _FakeFeatureEnabled(enabled=True)
        monkeypatch.setattr("customer_module.app.feature_enabled", fake)
        token = _bearer_token(tenant="global")

        response = await client.post(
            "/customer/accounts",
            json={"name": "Acme", "community_id": 42},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        body = await response.get_json()
        assert body["success"] is True
        assert body["data"] == {"id": "stub-account", "name": "Acme"}
        assert fake.calls == [
            {"flag_key": "waddles.customer.accounts", "tenant": "global", "community": 42}
        ]


class TestCreateAccountTenantIsolation:
    """regression: tenant-isolation audit 2026-08-30.

    `tenant_middleware` was missing from `create_account`, so
    `get_tenant_context(request)` always returned `None` and every request
    -- authenticated or not -- silently ran as `DEFAULT_TENANT_SLUG`.
    """

    async def test_no_jwt_is_rejected_not_run_as_default_tenant(
        self, client: Any, monkeypatch: pytest.MonkeyPatch, fake_tenant_resolution: None
    ) -> None:
        fake = _FakeFeatureEnabled(enabled=True)
        monkeypatch.setattr("customer_module.app.feature_enabled", fake)

        response = await client.post("/customer/accounts", json={"name": "Acme"})

        assert response.status_code == 401
        # The flag check must never run unauthenticated -- proves this
        # isn't a silent DEFAULT_TENANT_SLUG fallback.
        assert fake.calls == []

    async def test_invalid_jwt_returns_401(
        self, client: Any, monkeypatch: pytest.MonkeyPatch, fake_tenant_resolution: None
    ) -> None:
        fake = _FakeFeatureEnabled(enabled=True)
        monkeypatch.setattr("customer_module.app.feature_enabled", fake)

        response = await client.post(
            "/customer/accounts",
            json={"name": "Acme"},
            headers={"Authorization": "Bearer not-a-real-token"},
        )

        assert response.status_code == 401
        assert fake.calls == []

    async def test_tenant_comes_from_jwt_not_default(
        self, client: Any, monkeypatch: pytest.MonkeyPatch, fake_tenant_resolution: None
    ) -> None:
        fake = _FakeFeatureEnabled(enabled=True)
        monkeypatch.setattr("customer_module.app.feature_enabled", fake)
        token = _bearer_token(tenant="acme-corp")

        response = await client.post(
            "/customer/accounts",
            json={"name": "Acme", "community_id": 42},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert fake.calls == [
            {"flag_key": "waddles.customer.accounts", "tenant": "acme-corp", "community": 42}
        ]


class TestCreateAccountScopeEnforcement:
    """`@require_scope("customer.account:write")` -- the HTTP-layer scope
    check closing the tenant -> scope -> feature chain (security.md)."""

    async def test_missing_scope_is_403(
        self, client: Any, monkeypatch: pytest.MonkeyPatch, fake_tenant_resolution: None
    ) -> None:
        fake = _FakeFeatureEnabled(enabled=True)
        monkeypatch.setattr("customer_module.app.feature_enabled", fake)
        token = _bearer_token(tenant="global", scope="")

        response = await client.post(
            "/customer/accounts",
            json={"name": "Acme"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403
        assert fake.calls == []

    async def test_wrong_scope_is_403(
        self, client: Any, monkeypatch: pytest.MonkeyPatch, fake_tenant_resolution: None
    ) -> None:
        fake = _FakeFeatureEnabled(enabled=True)
        monkeypatch.setattr("customer_module.app.feature_enabled", fake)
        token = _bearer_token(tenant="global", scope="social.quote:write")

        response = await client.post(
            "/customer/accounts",
            json={"name": "Acme"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403
        assert fake.calls == []

    async def test_valid_scope_proceeds(
        self, client: Any, monkeypatch: pytest.MonkeyPatch, fake_tenant_resolution: None
    ) -> None:
        fake = _FakeFeatureEnabled(enabled=True)
        monkeypatch.setattr("customer_module.app.feature_enabled", fake)
        token = _bearer_token(tenant="global", scope="customer.account:write")

        response = await client.post(
            "/customer/accounts",
            json={"name": "Acme", "community_id": 42},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert fake.calls == [
            {"flag_key": "waddles.customer.accounts", "tenant": "global", "community": 42}
        ]
