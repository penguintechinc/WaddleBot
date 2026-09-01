"""Tenant-isolation regression tests for welcome_interaction_module's app.py.

regression: tenant-isolation audit 2026-08-30 -- ``welcome_check`` (POST
/api/v1/welcome/check) had no auth decorator at all and read ``tenant``
straight off the request body, feeding it into the
``waddles.social.welcome_ai`` gate (``services/welcome_service.py``). Any
caller could spoof ``tenant`` in the body to probe/consume another
tenant's entitlement.

The fix applies ``tenant_middleware`` and takes the tenant from the
JWT-derived ``TenantContext`` only; ``tenant`` was removed from
``WelcomeCheckRequest`` entirely (``validation_models.py``), and that
model's ``extra = 'forbid'`` means a request body that still includes
``tenant`` is now rejected outright (400) rather than silently accepted --
a stronger guarantee than merely ignoring it, and proven directly by
``test_spoofed_tenant_field_in_body_is_rejected``.

Fail-first proof: with ``@tenant_middleware`` temporarily removed from
``welcome_check``, ``test_no_jwt_is_rejected_not_run_as_default_tenant``
and ``test_invalid_jwt_returns_401`` both failed (200, service called
unauthenticated) before the fix, and pass after it.

``TestWelcomeCheckScopeEnforcement`` covers the HTTP-layer scope check
added on top of that fix: ``@require_scope("social.welcome:write")`` now
sits between ``tenant_middleware`` and ``validate_json`` on this handler,
per ``social_module/features.py``'s ``social.welcome`` Feature contract
(``requires_scopes == {"social.welcome:write"}``, shared with
``social.welcome_ai``). ``_bearer_token``'s default ``scope`` is the exact
required scope, so every pre-existing test above that doesn't override it
keeps exercising the real, now-enforced path.
"""

from __future__ import annotations

from typing import Any

import pytest
from app import app
from flask_core.auth import create_jwt_token
from flask_core.tenancy import TenantContext
from services.welcome_service import WelcomeResult

# tenant_middleware falls back to this exact default when SECRET_KEY isn't
# set in the environment (flask_core/tenancy.py).
_SECRET_KEY = "change-me-in-production"

_VALID_BODY = {
    "community_id": 123,
    "platform": "twitch",
    "platform_user_id": "456",
    "platform_username": "jdoe",
}


class _FakeWelcomeService:
    """Records the kwargs `check_and_welcome` was called with."""

    def __init__(self, result: WelcomeResult) -> None:
        self.result = result
        self.calls: list[dict[str, Any]] = []

    async def check_and_welcome(self, **kwargs: Any) -> WelcomeResult:
        self.calls.append(kwargs)
        return self.result


def _bearer_token(tenant: str, scope: str = "social.welcome:write") -> str:
    """`scope` defaults to `welcome_check`'s required scope so every
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
    real DB-backed `tenants` table -- isolates the wiring bug on this
    handler from `resolve_tenant_context`'s own DB lookup, which is
    unit-tested in `libs/flask_core/tests/test_tenancy.py`.
    """

    async def _resolve(payload: dict[str, Any], dal: Any) -> TenantContext:
        return TenantContext(tenant_id=1, tenant_slug=payload["tenant"])

    monkeypatch.setattr("flask_core.tenancy.resolve_tenant_context", _resolve)


@pytest.fixture
def fake_welcome_service(monkeypatch: pytest.MonkeyPatch) -> _FakeWelcomeService:
    """Patch the module-level `welcome_service` global (normally set in
    `startup()`, never called under `test_client()`) so the handler has
    something to call once auth/tenant/validation succeed."""
    fake = _FakeWelcomeService(result=WelcomeResult(welcomed=False))
    monkeypatch.setattr("app.welcome_service", fake)
    return fake


class TestWelcomeCheckTenantIsolation:
    """regression: tenant-isolation audit 2026-08-30."""

    @pytest.mark.asyncio
    async def test_no_jwt_is_rejected_not_run_as_default_tenant(
        self,
        client: Any,
        fake_tenant_resolution: None,
        fake_welcome_service: _FakeWelcomeService,
    ) -> None:
        response = await client.post("/api/v1/welcome/check", json=_VALID_BODY)

        assert response.status_code == 401
        assert fake_welcome_service.calls == []

    @pytest.mark.asyncio
    async def test_invalid_jwt_returns_401(
        self,
        client: Any,
        fake_tenant_resolution: None,
        fake_welcome_service: _FakeWelcomeService,
    ) -> None:
        response = await client.post(
            "/api/v1/welcome/check",
            json=_VALID_BODY,
            headers={"Authorization": "Bearer not-a-real-token"},
        )

        assert response.status_code == 401
        assert fake_welcome_service.calls == []

    @pytest.mark.asyncio
    async def test_tenant_comes_from_jwt_not_default(
        self,
        client: Any,
        fake_tenant_resolution: None,
        fake_welcome_service: _FakeWelcomeService,
    ) -> None:
        token = _bearer_token(tenant="acme-corp")

        response = await client.post(
            "/api/v1/welcome/check",
            json=_VALID_BODY,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert len(fake_welcome_service.calls) == 1
        assert fake_welcome_service.calls[0]["tenant"] == "acme-corp"

    @pytest.mark.asyncio
    async def test_spoofed_tenant_field_in_body_is_rejected(
        self,
        client: Any,
        fake_tenant_resolution: None,
        fake_welcome_service: _FakeWelcomeService,
    ) -> None:
        """A caller trying to smuggle a `tenant` field into the body (the
        exact vector the audit flagged) is rejected outright -- `tenant`
        is no longer a field on `WelcomeCheckRequest`, and its
        `extra = 'forbid'` config rejects unknown fields with 400. The
        gate is never reached with an attacker-supplied tenant, spoofed
        or otherwise: this request never reaches `welcome_service` at
        all.
        """
        token = _bearer_token(tenant="acme-corp")
        spoofed_body = {**_VALID_BODY, "tenant": "victim-tenant"}

        response = await client.post(
            "/api/v1/welcome/check",
            json=spoofed_body,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 400
        assert fake_welcome_service.calls == []


class TestWelcomeCheckScopeEnforcement:
    """`@require_scope("social.welcome:write")` -- the HTTP-layer scope
    check closing the tenant -> scope -> feature chain (security.md)."""

    @pytest.mark.asyncio
    async def test_missing_scope_is_403(
        self,
        client: Any,
        fake_tenant_resolution: None,
        fake_welcome_service: _FakeWelcomeService,
    ) -> None:
        token = _bearer_token(tenant="acme-corp", scope="")

        response = await client.post(
            "/api/v1/welcome/check",
            json=_VALID_BODY,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403
        assert fake_welcome_service.calls == []

    @pytest.mark.asyncio
    async def test_wrong_scope_is_403(
        self,
        client: Any,
        fake_tenant_resolution: None,
        fake_welcome_service: _FakeWelcomeService,
    ) -> None:
        token = _bearer_token(tenant="acme-corp", scope="bot.command:write")

        response = await client.post(
            "/api/v1/welcome/check",
            json=_VALID_BODY,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403
        assert fake_welcome_service.calls == []

    @pytest.mark.asyncio
    async def test_valid_scope_proceeds(
        self,
        client: Any,
        fake_tenant_resolution: None,
        fake_welcome_service: _FakeWelcomeService,
    ) -> None:
        token = _bearer_token(tenant="acme-corp", scope="social.welcome:write")

        response = await client.post(
            "/api/v1/welcome/check",
            json=_VALID_BODY,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert len(fake_welcome_service.calls) == 1
