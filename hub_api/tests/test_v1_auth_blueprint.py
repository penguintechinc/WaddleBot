"""`blueprints/v1/auth.py` -- the M1 auth group, replacing the old login-only stub.

Standalone Quart app registering only `auth_bp` (mirrors
`test_platform_blueprint.py`'s own pattern) against the `auth_db`
fixture (`tests/conftest.py`) -- real JWTs via `flask_core.auth.
create_jwt_token`, real pydal queries against an in-memory schema, no
mocking of the auth chain itself.

Fail-first proof (executed, not narrated): temporarily removed
`get_current_user_id(request)`'s bearer-token check in `services/
current_user.py` (made it always return `1` regardless of the header) --
`test_set_password_without_token_is_401` went red (200 instead of 401,
an auth bypass); reverted, green again. Separately, temporarily swapped
`RequiresVerificationError` handling in `login()` to fall through to the
generic `except ApiError` branch -- `test_login_unverified_email_is_403_
requires_verification` went red (401 generic "Invalid credentials"
instead of 403 with `requiresVerification: true`, which `AuthContext.jsx`
depends on to route the user to the verification-resend flow); reverted,
green again.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import pytest
from quart import Quart
from quart_schema import QuartSchema

from blueprints.v1.auth import auth_bp
from config import HubAPIConfig
from tests.conftest import TENANT_SLUG, make_user_token


def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=4)).decode()


def _test_config() -> HubAPIConfig:
    return HubAPIConfig(
        module_name="hub-api-test",
        module_version="0.0.0-test",
        module_port=8204,
        grpc_port=50204,
        database_url="sqlite:memory",
        database_read_replica_url=None,
        db_pool_size=1,
        db_max_retries=1,
        db_retry_delay=1,
        secret_key="change-me-in-production",
        jwt_algorithm="HS256",
        default_tenant_slug="global",
        posthog_api_key=None,
        posthog_host="https://license.penguintech.io",
        license_server_url="https://license.penguintech.io",
        identity_callback_base_url="http://localhost:8204",
        frontend_origin="http://localhost:5173",
        log_level="INFO",
    )


@pytest.fixture
def app(auth_db: Any) -> Quart:
    quart_app = Quart(__name__)
    QuartSchema(quart_app)
    quart_app.register_blueprint(auth_bp)
    quart_app.config["dal"] = auth_db.dal
    quart_app.config["async_dal"] = auth_db
    quart_app.config["HUB_API_CONFIG"] = _test_config()
    return quart_app


@pytest.fixture
def client(app: Quart) -> Any:
    return app.test_client()


def _seed_settings(auth_db: Any, **settings: str) -> None:
    for key, value in settings.items():
        auth_db.dal.hub_settings.insert(setting_key=key, setting_value=value)
    auth_db.dal.commit()


def _seed_user(
    auth_db: Any,
    *,
    email: str = "alice@example.com",
    username: str = "alice",
    password: str = "hunter22",
    is_active: bool = True,
    email_verified: bool = True,
    is_super_admin: bool = False,
    is_analytics_consumer: bool = False,
) -> int:
    user_id: int = auth_db.dal.hub_users.insert(
        email=email,
        username=username,
        password_hash=_hash(password),
        is_active=is_active,
        email_verified=email_verified,
        is_super_admin=is_super_admin,
        is_analytics_consumer=is_analytics_consumer,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    auth_db.dal.commit()
    return user_id


class TestRegister:
    async def test_register_disabled_by_default_is_403(self, client: Any) -> None:
        """No hub_settings rows -- signup_enabled defaults to "not true" -- forbidden."""
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": "new@example.com", "password": "hunter22"},
        )
        assert response.status_code == 403

    async def test_register_success_returns_token_and_user(self, client: Any, auth_db: Any) -> None:
        _seed_settings(auth_db, signup_enabled="true", email_configured="true")
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": "new@example.com", "password": "hunter22", "username": "newuser"},
        )
        assert response.status_code == 200
        body = await response.get_json()
        assert body["success"] is True
        assert body["token"]
        assert body["user"]["email"] == "new@example.com"
        assert body["user"]["isSuperAdmin"] is False

    async def test_register_duplicate_email_is_409(self, client: Any, auth_db: Any) -> None:
        _seed_settings(auth_db, signup_enabled="true", email_configured="true")
        _seed_user(auth_db, email="taken@example.com")
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": "taken@example.com", "password": "hunter22"},
        )
        assert response.status_code == 409

    async def test_register_missing_fields_is_400(self, client: Any) -> None:
        """quart-schema @validate_request rejects a body missing required fields."""
        response = await client.post("/api/v1/auth/register", json={"email": "a@b.com"})
        assert response.status_code == 400


class TestLogin:
    async def test_login_success_returns_token(self, client: Any, auth_db: Any) -> None:
        _seed_user(auth_db, email="bob@example.com", password="correcthorse")
        response = await client.post(
            "/api/v1/auth/login", json={"email": "bob@example.com", "password": "correcthorse"}
        )
        assert response.status_code == 200
        body = await response.get_json()
        assert body["token"]
        assert body["user"]["email"] == "bob@example.com"

    async def test_login_wrong_password_is_401(self, client: Any, auth_db: Any) -> None:
        _seed_user(auth_db, email="bob@example.com", password="correcthorse")
        response = await client.post(
            "/api/v1/auth/login", json={"email": "bob@example.com", "password": "wrong"}
        )
        assert response.status_code == 401

    async def test_login_unknown_email_is_401(self, client: Any) -> None:
        """Never reveals whether the account exists -- same 401 as a wrong password."""
        response = await client.post(
            "/api/v1/auth/login", json={"email": "nobody@example.com", "password": "x"}
        )
        assert response.status_code == 401

    async def test_login_inactive_account_is_401(self, client: Any, auth_db: Any) -> None:
        _seed_user(auth_db, email="gone@example.com", password="hunter22", is_active=False)
        response = await client.post(
            "/api/v1/auth/login", json={"email": "gone@example.com", "password": "hunter22"}
        )
        assert response.status_code == 401

    async def test_login_unverified_email_is_403_requires_verification(
        self, client: Any, auth_db: Any
    ) -> None:
        _seed_user(auth_db, email="new@example.com", password="hunter22", email_verified=False)
        response = await client.post(
            "/api/v1/auth/login", json={"email": "new@example.com", "password": "hunter22"}
        )
        assert response.status_code == 403
        body = await response.get_json()
        assert body["requiresVerification"] is True

    async def test_login_analytics_consumer_grants_analytics_read_scope(
        self, client: Any, auth_db: Any
    ) -> None:
        """Analytics module port (M9) -- see `services/auth_service.py::create_session_token`.

        Without this scope grant, no `is_analytics_consumer` user could
        ever satisfy `blueprints/v1/analytics.py`'s platform-overview
        `require_scope("analytics:read")` gate.
        """
        from flask_core.auth import verify_jwt_token

        _seed_user(
            auth_db,
            email="carol@example.com",
            password="hunter22",
            is_analytics_consumer=True,
        )
        response = await client.post(
            "/api/v1/auth/login", json={"email": "carol@example.com", "password": "hunter22"}
        )
        assert response.status_code == 200
        body = await response.get_json()
        payload = verify_jwt_token(body["token"], "change-me-in-production")
        assert payload is not None
        assert "analytics:read" in payload["scope"].split()

    async def test_login_non_consumer_has_no_analytics_read_scope(
        self, client: Any, auth_db: Any
    ) -> None:
        from flask_core.auth import verify_jwt_token

        _seed_user(auth_db, email="dave@example.com", password="hunter22")
        response = await client.post(
            "/api/v1/auth/login", json={"email": "dave@example.com", "password": "hunter22"}
        )
        assert response.status_code == 200
        body = await response.get_json()
        payload = verify_jwt_token(body["token"], "change-me-in-production")
        assert payload is not None
        assert "analytics:read" not in payload["scope"].split()


class TestMe:
    async def test_me_without_token_returns_null_user(self, client: Any) -> None:
        """Matches Node's optionalAuth -- absent token is "logged out", not an error."""
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 200
        body = await response.get_json()
        assert body == {"success": True, "user": None}

    async def test_me_with_valid_token_returns_user(self, client: Any, auth_db: Any) -> None:
        user_id = _seed_user(auth_db, email="carol@example.com")
        token = make_user_token(user_id=user_id, tenant=TENANT_SLUG)
        response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        body = await response.get_json()
        assert body["user"]["email"] == "carol@example.com"
        assert body["user"]["hasPassword"] is True


class TestSetPassword:
    async def test_set_password_without_token_is_401(self, client: Any) -> None:
        """The representative auth-bypass check: no bearer token, no access."""
        response = await client.post(
            "/api/v1/auth/password", json={"newPassword": "newpassword123"}
        )
        assert response.status_code == 401

    async def test_set_password_wrong_current_password_is_401(
        self, client: Any, auth_db: Any
    ) -> None:
        user_id = _seed_user(auth_db, password="original1")
        token = make_user_token(user_id=user_id, tenant=TENANT_SLUG)
        response = await client.post(
            "/api/v1/auth/password",
            headers={"Authorization": f"Bearer {token}"},
            json={"currentPassword": "wrongpass", "newPassword": "newpassword123"},
        )
        assert response.status_code == 401

    async def test_set_password_success(self, client: Any, auth_db: Any) -> None:
        user_id = _seed_user(auth_db, password="original1")
        token = make_user_token(user_id=user_id, tenant=TENANT_SLUG)
        response = await client.post(
            "/api/v1/auth/password",
            headers={"Authorization": f"Bearer {token}"},
            json={"currentPassword": "original1", "newPassword": "newpassword123"},
        )
        assert response.status_code == 200


class TestLogout:
    async def test_logout_always_returns_success(self, client: Any) -> None:
        """No token present -- matches Node's logout(), a no-op success, never an error."""
        response = await client.post("/api/v1/auth/logout")
        assert response.status_code == 200
        body = await response.get_json()
        assert body == {"success": True}


class TestRefresh:
    async def test_refresh_without_token_is_400(self, client: Any) -> None:
        response = await client.post("/api/v1/auth/refresh")
        assert response.status_code == 400

    async def test_refresh_valid_session_returns_new_token(self, client: Any, auth_db: Any) -> None:
        user_id = _seed_user(auth_db)
        token = make_user_token(user_id=user_id, tenant=TENANT_SLUG)
        auth_db.dal.hub_sessions.insert(
            session_token=token,
            user_id=user_id,
            is_active=True,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            created_at=datetime.now(UTC),
        )
        auth_db.dal.commit()
        response = await client.post(
            "/api/v1/auth/refresh", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        body = await response.get_json()
        assert body["token"] and body["token"] != token


class TestTenantLoginInfo:
    async def test_unknown_tenant_is_404(self, client: Any) -> None:
        response = await client.get("/api/v1/auth/tenant/no-such-tenant")
        assert response.status_code == 404

    async def test_known_tenant_returns_info(self, client: Any) -> None:
        response = await client.get(f"/api/v1/auth/tenant/{TENANT_SLUG}")
        assert response.status_code == 200
        body = await response.get_json()
        assert body["tenant"]["slug"] == TENANT_SLUG


class TestLegacyLinkOAuth:
    async def test_legacy_link_oauth_is_501(self, client: Any) -> None:
        """Dead code under the unified session model -- see blueprints/v1/auth.py docstring."""
        response = await client.post("/api/v1/auth/link-oauth")
        assert response.status_code == 501
