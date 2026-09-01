"""`blueprints/v1/profile.py` -- the M1 self-service profile group.

Standalone Quart app registering only `profile_bp`. `update_my_profile`
routes through `jsonify_dto()` (see `services/dto_response.py`) -- this
suite is what proved that route needed the workaround in the first place.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from quart import Quart
from quart_schema import QuartSchema

from blueprints.v1.profile import profile_bp
from tests.conftest import TENANT_SLUG, make_user_token


@pytest.fixture
def app(auth_db: Any) -> Quart:
    quart_app = Quart(__name__)
    QuartSchema(quart_app)
    quart_app.register_blueprint(profile_bp)
    quart_app.config["dal"] = auth_db.dal
    quart_app.config["async_dal"] = auth_db
    return quart_app


@pytest.fixture
def client(app: Quart) -> Any:
    return app.test_client()


def _seed_user(auth_db: Any, *, email: str = "alice@example.com") -> int:
    user_id: int = auth_db.dal.hub_users.insert(
        email=email,
        username="alice",
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    auth_db.dal.commit()
    return user_id


def _headers(user_id: int) -> dict[str, str]:
    return {"Authorization": f"Bearer {make_user_token(user_id=user_id, tenant=TENANT_SLUG)}"}


class TestGetProfile:
    async def test_get_profile_without_token_is_401(self, client: Any) -> None:
        response = await client.get("/api/v1/user/profile")
        assert response.status_code == 401

    async def test_get_profile_success(self, client: Any, auth_db: Any) -> None:
        user_id = _seed_user(auth_db)
        response = await client.get("/api/v1/user/profile", headers=_headers(user_id))
        assert response.status_code == 200
        body = await response.get_json()
        assert body["profile"]["userId"] == user_id


class TestUpdateProfile:
    async def test_update_profile_success(self, client: Any, auth_db: Any) -> None:
        user_id = _seed_user(auth_db)
        response = await client.put(
            "/api/v1/user/profile",
            headers=_headers(user_id),
            json={"displayName": "Alice W", "bio": "hello world"},
        )
        assert response.status_code == 200
        body = await response.get_json()
        assert body["profile"]["displayName"] == "Alice W"
        assert body["profile"]["bio"] == "hello world"

    async def test_update_profile_invalid_visibility_is_400(
        self, client: Any, auth_db: Any
    ) -> None:
        user_id = _seed_user(auth_db)
        response = await client.put(
            "/api/v1/user/profile",
            headers=_headers(user_id),
            json={"visibility": "not-a-real-value"},
        )
        assert response.status_code == 400

    async def test_update_profile_without_token_is_401(self, client: Any) -> None:
        response = await client.put("/api/v1/user/profile", json={"bio": "x"})
        assert response.status_code == 401


class TestLinkedPlatforms:
    async def test_get_linked_platforms_empty(self, client: Any, auth_db: Any) -> None:
        user_id = _seed_user(auth_db)
        response = await client.get("/api/v1/user/linked-platforms", headers=_headers(user_id))
        assert response.status_code == 200
        body = await response.get_json()
        assert body["linkedPlatforms"] == []
