"""Tenant-isolation regression tests for shoutout_interaction_module's app.py.

regression: tenant-isolation audit 2026-08-30 -- ``create_shoutout`` (POST
/api/v1/shoutout) called ``get_tenant_context`` but never applied
``tenant_middleware``, so the context was always ``None`` and every
request silently ran as ``DEFAULT_TENANT_SLUG`` with no auth at all.

``feature_enabled`` is mocked to return ``False`` so these tests exercise
only the auth/tenant wiring (the ``waddles.bot.shoutout`` gate check and
the 401 short-circuit before it) without needing the live Twitch/video/
identity services or a database -- those are out of scope here (see
``libs/flask_core/tests/test_bot_features.py::TestShoutoutGate`` for the
contract-level coverage of the gate's flag name).

Fail-first proof: with ``@tenant_middleware`` temporarily removed from
``create_shoutout``, ``test_no_jwt_is_rejected_not_run_as_default_tenant``
and ``test_invalid_jwt_returns_401`` both failed (404 with the flag check
running unauthenticated) before the fix, and pass after it.
"""

from __future__ import annotations

from typing import Any

import pytest
from app import app
from flask_core.auth import create_jwt_token
from flask_core.tenancy import TenantContext

# tenant_middleware falls back to this exact default when SECRET_KEY isn't
# set in the environment (flask_core/tenancy.py).
_SECRET_KEY = "change-me-in-production"


class _FakeFeatureEnabled:
    """Records the flag/tenant it was called with and returns a fixed verdict."""

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
        self.calls.append({"flag_key": flag_key, "tenant": tenant})
        return self.enabled


def _bearer_token(tenant: str) -> str:
    return create_jwt_token(
        user_id="u1",
        username="alice",
        email="alice@example.com",
        roles=["viewer"],
        secret_key=_SECRET_KEY,
        tenant=tenant,
    )


@pytest.fixture
def client():
    return app.test_client()


@pytest.fixture
def fake_tenant_resolution(monkeypatch: pytest.MonkeyPatch):
    """Stub `resolve_tenant_context` so `tenant_middleware` doesn't need a
    real DB-backed `tenants` table -- isolates the wiring bug on this
    handler from `resolve_tenant_context`'s own DB lookup, which is
    unit-tested in `libs/flask_core/tests/test_tenancy.py`.
    """

    async def _resolve(payload: dict[str, Any], dal: Any) -> TenantContext:
        return TenantContext(tenant_id=1, tenant_slug=payload["tenant"])

    monkeypatch.setattr("flask_core.tenancy.resolve_tenant_context", _resolve)


class TestCreateShoutoutTenantIsolation:
    """regression: tenant-isolation audit 2026-08-30."""

    async def test_no_jwt_is_rejected_not_run_as_default_tenant(
        self, client: Any, monkeypatch: pytest.MonkeyPatch, fake_tenant_resolution: None
    ) -> None:
        fake = _FakeFeatureEnabled(enabled=False)
        monkeypatch.setattr("app.feature_enabled", fake)

        response = await client.post(
            "/api/v1/shoutout",
            json={"username": "someuser", "community_id": 1},
        )

        assert response.status_code == 401
        assert fake.calls == []

    async def test_invalid_jwt_returns_401(
        self, client: Any, monkeypatch: pytest.MonkeyPatch, fake_tenant_resolution: None
    ) -> None:
        fake = _FakeFeatureEnabled(enabled=False)
        monkeypatch.setattr("app.feature_enabled", fake)

        response = await client.post(
            "/api/v1/shoutout",
            json={"username": "someuser", "community_id": 1},
            headers={"Authorization": "Bearer not-a-real-token"},
        )

        assert response.status_code == 401
        assert fake.calls == []

    async def test_tenant_comes_from_jwt_not_default(
        self, client: Any, monkeypatch: pytest.MonkeyPatch, fake_tenant_resolution: None
    ) -> None:
        fake = _FakeFeatureEnabled(enabled=False)
        monkeypatch.setattr("app.feature_enabled", fake)
        token = _bearer_token(tenant="acme-corp")

        response = await client.post(
            "/api/v1/shoutout",
            json={"username": "someuser", "community_id": 1},
            headers={"Authorization": f"Bearer {token}"},
        )

        # The gate itself is mocked OFF -- 404 -- but the point of this test
        # is what tenant it was evaluated against.
        assert response.status_code == 404
        assert fake.calls == [{"flag_key": "waddles.bot.shoutout", "tenant": "acme-corp"}]
