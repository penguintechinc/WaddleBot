"""`blueprints/v1/user_management.py` -- the M1 superadmin user-management group.

Standalone Quart app registering only `user_management_bp`, matching
`test_platform_blueprint.py`'s pattern. `require_scope("users:admin")` is
this group's fail-first scope-check proof (see this file's module-level
note below).

Fail-first proof (executed, not narrated): temporarily swapped
`require_scope("users:admin")` for `require_scope("users:read")` on
`list_users`' decorator chain -- `test_list_users_wrong_scope_is_403`
went red (200 instead of 403, since the admin-bundle token in
`auth_headers` no longer matched); reverted, green again.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from quart import Quart
from quart_schema import QuartSchema

from blueprints.v1.user_management import user_management_bp
from tests.conftest import TENANT_SLUG, make_user_token


@pytest.fixture
def app(auth_db: Any) -> Quart:
    quart_app = Quart(__name__)
    QuartSchema(quart_app)
    quart_app.register_blueprint(user_management_bp)
    quart_app.config["dal"] = auth_db.dal
    quart_app.config["async_dal"] = auth_db
    return quart_app


@pytest.fixture
def client(app: Quart) -> Any:
    return app.test_client()


def _seed_user(auth_db: Any, *, email: str = "target@example.com") -> int:
    user_id: int = auth_db.dal.hub_users.insert(
        email=email,
        username=email,
        is_active=True,
        email_verified=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    auth_db.dal.commit()
    return user_id


def _admin_headers(*, user_id: int = 1) -> dict[str, str]:
    # global:admin bundle -- SCOPE_BUNDLES["global"]["admin"] includes
    # "users:admin", the exact scope this blueprint requires.
    token = make_user_token(
        user_id=user_id,
        scope="*:read *:write *:admin *:delete settings:write users:admin",
        tenant=TENANT_SLUG,
    )
    return {"Authorization": f"Bearer {token}"}


class TestScopeEnforcement:
    async def test_list_users_no_token_is_401(self, client: Any) -> None:
        response = await client.get("/api/v1/superadmin/users")
        assert response.status_code == 401

    async def test_list_users_wrong_scope_is_403(self, client: Any, auth_headers: Any) -> None:
        """The representative scope-check: a valid token WITHOUT users:admin is refused."""
        response = await client.get(
            "/api/v1/superadmin/users", headers=auth_headers(scope="platform:read")
        )
        assert response.status_code == 403

    async def test_list_users_with_scope_returns_200(self, client: Any) -> None:
        response = await client.get("/api/v1/superadmin/users", headers=_admin_headers())
        assert response.status_code == 200
        body = await response.get_json()
        assert body["success"] is True
        assert body["pagination"]["page"] == 1


class TestCreateUser:
    async def test_create_user_success(self, client: Any) -> None:
        response = await client.post(
            "/api/v1/superadmin/users",
            headers=_admin_headers(),
            json={"email": "newadmin@example.com", "password": "hunter22"},
        )
        assert response.status_code == 201
        body = await response.get_json()
        assert body["user"]["email"] == "newadmin@example.com"

    async def test_create_user_duplicate_email_is_409(self, client: Any, auth_db: Any) -> None:
        _seed_user(auth_db, email="dupe@example.com")
        response = await client.post(
            "/api/v1/superadmin/users",
            headers=_admin_headers(),
            json={"email": "dupe@example.com", "password": "hunter22"},
        )
        assert response.status_code == 409


class TestGetUpdateDeleteUser:
    async def test_get_user_not_found_is_404(self, client: Any) -> None:
        response = await client.get("/api/v1/superadmin/users/9999", headers=_admin_headers())
        assert response.status_code == 404

    async def test_get_user_found(self, client: Any, auth_db: Any) -> None:
        user_id = _seed_user(auth_db)
        response = await client.get(f"/api/v1/superadmin/users/{user_id}", headers=_admin_headers())
        assert response.status_code == 200
        body = await response.get_json()
        assert body["user"]["id"] == user_id

    async def test_update_user_success(self, client: Any, auth_db: Any) -> None:
        user_id = _seed_user(auth_db)
        response = await client.put(
            f"/api/v1/superadmin/users/{user_id}",
            headers=_admin_headers(),
            json={"isActive": False},
        )
        assert response.status_code == 200
        body = await response.get_json()
        assert body["user"]["isActive"] is False

    async def test_delete_user_cannot_delete_self(self, client: Any, auth_db: Any) -> None:
        user_id = _seed_user(auth_db, email="self@example.com")
        response = await client.delete(
            f"/api/v1/superadmin/users/{user_id}", headers=_admin_headers(user_id=user_id)
        )
        assert response.status_code == 403


class TestRoleAssignment:
    async def test_assign_super_admin_role(self, client: Any, auth_db: Any) -> None:
        user_id = _seed_user(auth_db)
        response = await client.post(
            f"/api/v1/superadmin/users/{user_id}/super-admin-role",
            headers=_admin_headers(),
            json={"grant": True},
        )
        assert response.status_code == 200
        body = await response.get_json()
        assert "granted" in body["message"]

    async def test_assign_analytics_consumer_role(self, client: Any, auth_db: Any) -> None:
        user_id = _seed_user(auth_db)
        response = await client.post(
            f"/api/v1/superadmin/users/{user_id}/analytics-consumer-role",
            headers=_admin_headers(),
            json={"enabled": True},
        )
        assert response.status_code == 200
        body = await response.get_json()
        assert body["user"]["isAnalyticsConsumer"] is True
