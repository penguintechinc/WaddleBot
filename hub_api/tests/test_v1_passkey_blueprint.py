"""`blueprints/v1/passkey.py` -- the M1 self-service passkey (WebAuthn) group.

Only the credential-management routes (register options, list, delete) --
full registration-finish/login-finish flows need a real WebAuthn
authenticator ceremony (browser-side crypto), out of scope for a server-
only test; `services/passkey_service.py`'s option-generation and
challenge-store logic is exercised directly instead.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from quart import Quart
from quart_schema import QuartSchema

from blueprints.v1.passkey import passkey_bp
from tests.conftest import TENANT_SLUG, make_user_token


@pytest.fixture
def app(auth_db: Any) -> Quart:
    quart_app = Quart(__name__)
    QuartSchema(quart_app)
    quart_app.register_blueprint(passkey_bp)
    quart_app.config["dal"] = auth_db.dal
    quart_app.config["async_dal"] = auth_db
    return quart_app


@pytest.fixture
def client(app: Quart) -> Any:
    return app.test_client()


def _seed_user(auth_db: Any) -> int:
    user_id: int = auth_db.dal.hub_users.insert(
        email="alice@example.com", username="alice", is_active=True, created_at=datetime.now(UTC)
    )
    auth_db.dal.commit()
    return user_id


def _headers(user_id: int) -> dict[str, str]:
    return {"Authorization": f"Bearer {make_user_token(user_id=user_id, tenant=TENANT_SLUG)}"}


class TestRegistrationStart:
    async def test_start_registration_without_token_is_401(self, client: Any) -> None:
        response = await client.post("/api/v1/user/passkey/register/start")
        assert response.status_code == 401

    async def test_start_registration_returns_webauthn_options(
        self, client: Any, auth_db: Any
    ) -> None:
        user_id = _seed_user(auth_db)
        response = await client.post(
            "/api/v1/user/passkey/register/start", headers=_headers(user_id)
        )
        assert response.status_code == 200
        body = await response.get_json()
        assert body["success"] is True
        assert "challenge" in body["options"]
        assert body["options"]["rp"]["name"]


class TestListCredentials:
    async def test_list_credentials_empty(self, client: Any, auth_db: Any) -> None:
        user_id = _seed_user(auth_db)
        response = await client.get("/api/v1/user/passkey/credentials", headers=_headers(user_id))
        assert response.status_code == 200
        body = await response.get_json()
        assert body["credentials"] == []

    async def test_list_credentials_without_token_is_401(self, client: Any) -> None:
        response = await client.get("/api/v1/user/passkey/credentials")
        assert response.status_code == 401


class TestRemoveCredential:
    async def test_remove_nonexistent_credential_still_returns_success(
        self, client: Any, auth_db: Any
    ) -> None:
        """DELETE is idempotent -- removing an already-absent credential is still a 200."""
        user_id = _seed_user(auth_db)
        response = await client.delete(
            "/api/v1/user/passkey/credentials/9999", headers=_headers(user_id)
        )
        assert response.status_code == 200

    async def test_remove_credential_without_token_is_401(self, client: Any) -> None:
        response = await client.delete("/api/v1/user/passkey/credentials/1")
        assert response.status_code == 401
