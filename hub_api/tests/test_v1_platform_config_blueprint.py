"""`blueprints/v1/platform_config.py` -- M3 superadmin platform-config group.

Ported from `platformConfigController.js`'s superadmin.js-mounted subset.
Same standalone-app / real-JWT / real-pydal pattern as
`test_v1_user_management_blueprint.py`, which this group shares its
`require_scope("users:admin")` gate with.

Fail-first proof (executed, not narrated): temporarily swapped
`require_scope("users:admin")` for `require_scope("platform:read")` on
`get_platform_configs`' decorator chain (matches the "wrong scope"
token `auth_headers(scope="platform:read")` already carries) --
`test_get_platform_configs_wrong_scope_is_403` went red (200 instead of
403); reverted, green again.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx
import pytest
from quart import Quart
from quart_schema import QuartSchema

from blueprints.v1.platform_config import platform_config_bp
from config import HubAPIConfig
from tests.conftest import TENANT_SLUG, make_user_token


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
        default_tenant_slug=TENANT_SLUG,
        posthog_api_key=None,
        posthog_host="https://license.penguintech.io",
        license_server_url="https://license.penguintech.io",
        identity_callback_base_url="http://localhost:8204",
        frontend_origin="http://localhost:5173",
        log_level="INFO",
    )


@pytest.fixture
def app(platform_db: Any) -> Quart:
    quart_app = Quart(__name__)
    QuartSchema(quart_app)
    quart_app.register_blueprint(platform_config_bp)
    quart_app.config["dal"] = platform_db.dal
    quart_app.config["async_dal"] = platform_db
    quart_app.config["HUB_API_CONFIG"] = _test_config()
    return quart_app


@pytest.fixture
def client(app: Quart) -> Any:
    return app.test_client()


def _admin_headers(*, user_id: int = 1) -> dict[str, str]:
    token = make_user_token(
        user_id=user_id,
        scope="*:read *:write *:admin *:delete settings:write users:admin",
        tenant=TENANT_SLUG,
    )
    return {"Authorization": f"Bearer {token}"}


def _seed_bot_credential(
    platform_db: Any, *, platform: str = "twitch", access_token: str | None = "tok_abc"
) -> int:
    row_id: int = platform_db.dal.platform_integrations.insert(
        platform=platform,
        integration_type="bot",
        access_token=access_token,
        client_id="client-123",
        token_type="Bearer",
        is_active=True,
        is_encrypted=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    platform_db.dal.commit()
    return row_id


class TestScopeEnforcement:
    async def test_get_platform_configs_no_token_is_401(self, client: Any) -> None:
        response = await client.get("/api/v1/superadmin/platform-config")
        assert response.status_code == 401

    async def test_get_platform_configs_wrong_scope_is_403(
        self, client: Any, auth_headers: Any
    ) -> None:
        response = await client.get(
            "/api/v1/superadmin/platform-config", headers=auth_headers(scope="platform:read")
        )
        assert response.status_code == 403

    async def test_get_platform_configs_with_scope_returns_200(self, client: Any) -> None:
        response = await client.get(
            "/api/v1/superadmin/platform-config", headers=_admin_headers()
        )
        assert response.status_code == 200


class TestGetPlatformConfigs:
    async def test_masks_tokens(self, client: Any, platform_db: Any) -> None:
        _seed_bot_credential(platform_db)
        response = await client.get(
            "/api/v1/superadmin/platform-config", headers=_admin_headers()
        )
        assert response.status_code == 200
        body = await response.get_json()
        assert body["count"] == 1
        cred = body["data"][0]
        assert cred["accessToken"] == "***"
        assert cred["clientId"] == "client-123"  # never masked

    async def test_filters_by_platform(self, client: Any, platform_db: Any) -> None:
        _seed_bot_credential(platform_db, platform="twitch")
        _seed_bot_credential(platform_db, platform="discord")
        response = await client.get(
            "/api/v1/superadmin/platform-config",
            headers=_admin_headers(),
            query_string={"platform": "discord"},
        )
        body = await response.get_json()
        assert body["count"] == 1
        assert body["data"][0]["platform"] == "discord"

    async def test_filters_by_integration_type(self, client: Any, platform_db: Any) -> None:
        _seed_bot_credential(platform_db, platform="twitch")
        response = await client.get(
            "/api/v1/superadmin/platform-config",
            headers=_admin_headers(),
            query_string={"integrationType": "user_oauth"},
        )
        body = await response.get_json()
        assert body["count"] == 0


class TestUpdatePlatformConfig:
    async def test_always_404s(self, client: Any, platform_db: Any) -> None:
        """See services/platform_config_service.py's docstring: a pre-existing Node bug."""
        _seed_bot_credential(platform_db, platform="twitch")
        response = await client.put(
            "/api/v1/superadmin/platform-config/twitch",
            headers=_admin_headers(),
            json={"clientId": "new-id"},
        )
        assert response.status_code == 404


class TestTestPlatformConnection:
    async def test_no_credential_is_404(self, client: Any) -> None:
        response = await client.post(
            "/api/v1/superadmin/platform-config/twitch/test", headers=_admin_headers()
        )
        assert response.status_code == 404

    async def test_no_access_token_is_valid(self, client: Any, platform_db: Any) -> None:
        _seed_bot_credential(platform_db, platform="twitch", access_token=None)
        response = await client.post(
            "/api/v1/superadmin/platform-config/twitch/test", headers=_admin_headers()
        )
        assert response.status_code == 200
        body = await response.get_json()
        assert body["data"]["valid"] is True

    def _patch_httpx(self, monkeypatch: Any, handler: Any) -> None:
        """Replace `httpx.AsyncClient` with one wired to a `MockTransport` -- no real network."""
        real_async_client = httpx.AsyncClient

        def _factory(*args: Any, **kwargs: Any) -> httpx.AsyncClient:
            kwargs["transport"] = httpx.MockTransport(handler)
            return real_async_client(*args, **kwargs)

        monkeypatch.setattr(httpx, "AsyncClient", _factory)

    async def test_twitch_valid_token(
        self, client: Any, platform_db: Any, monkeypatch: Any
    ) -> None:
        _seed_bot_credential(platform_db, platform="twitch")
        self._patch_httpx(monkeypatch, lambda req: httpx.Response(200, json={}))
        response = await client.post(
            "/api/v1/superadmin/platform-config/twitch/test", headers=_admin_headers()
        )
        body = await response.get_json()
        assert body["data"]["valid"] is True

    async def test_discord_invalid_token(
        self, client: Any, platform_db: Any, monkeypatch: Any
    ) -> None:
        _seed_bot_credential(platform_db, platform="discord")
        self._patch_httpx(monkeypatch, lambda req: httpx.Response(401, json={}))
        response = await client.post(
            "/api/v1/superadmin/platform-config/discord/test", headers=_admin_headers()
        )
        body = await response.get_json()
        assert body["data"]["valid"] is False
        assert "HTTP 401" in body["data"]["error"]

    async def test_slack_ok_true(
        self, client: Any, platform_db: Any, monkeypatch: Any
    ) -> None:
        _seed_bot_credential(platform_db, platform="slack")
        self._patch_httpx(monkeypatch, lambda req: httpx.Response(200, json={"ok": True}))
        response = await client.post(
            "/api/v1/superadmin/platform-config/slack/test", headers=_admin_headers()
        )
        body = await response.get_json()
        assert body["data"]["valid"] is True

    async def test_slack_ok_false(
        self, client: Any, platform_db: Any, monkeypatch: Any
    ) -> None:
        _seed_bot_credential(platform_db, platform="slack")
        self._patch_httpx(monkeypatch, lambda req: httpx.Response(200, json={"ok": False}))
        response = await client.post(
            "/api/v1/superadmin/platform-config/slack/test", headers=_admin_headers()
        )
        body = await response.get_json()
        assert body["data"]["valid"] is False

    async def test_youtube_valid_token(
        self, client: Any, platform_db: Any, monkeypatch: Any
    ) -> None:
        _seed_bot_credential(platform_db, platform="youtube")
        self._patch_httpx(monkeypatch, lambda req: httpx.Response(200, json={}))
        response = await client.post(
            "/api/v1/superadmin/platform-config/youtube/test", headers=_admin_headers()
        )
        body = await response.get_json()
        assert body["data"]["valid"] is True

    async def test_unknown_platform_defaults_valid(
        self, client: Any, platform_db: Any, monkeypatch: Any
    ) -> None:
        _seed_bot_credential(platform_db, platform="storage")
        self._patch_httpx(monkeypatch, lambda req: httpx.Response(200, json={}))
        response = await client.post(
            "/api/v1/superadmin/platform-config/storage/test", headers=_admin_headers()
        )
        body = await response.get_json()
        assert body["data"]["valid"] is True

    async def test_network_error_fails_closed(
        self, client: Any, platform_db: Any, monkeypatch: Any
    ) -> None:
        _seed_bot_credential(platform_db, platform="twitch")

        def _raise(_req: Any) -> httpx.Response:
            raise httpx.ConnectError("boom")

        self._patch_httpx(monkeypatch, _raise)
        response = await client.post(
            "/api/v1/superadmin/platform-config/twitch/test", headers=_admin_headers()
        )
        body = await response.get_json()
        assert body["data"]["valid"] is False


class TestTestPlatformConnectionDecryptsEncryptedCredentials:
    """SECURITY (HIGH): `test_platform_connection()` must decrypt before sending to the provider.

    `credential_manager_module`'s refresh service encrypts `access_token`
    at rest and sets `is_encrypted = TRUE`; this group proves the
    superadmin "test credential" feature sends the real, decrypted token
    to the platform's own API -- not ciphertext -- via the SAME
    `httpx.MockTransport` pattern `TestTestPlatformConnection` uses,
    asserting on the actual `Authorization` header the mock transport
    received.

    Fail-first proof: with `platform_config_service.test_platform_connection`'s
    `decrypt_if_needed(...)` call reverted to plain `row.access_token` (no
    decryption at all), `test_encrypted_token_is_decrypted_before_send`
    went red as expected (the mock transport observed the raw ciphertext
    in the `Authorization` header, not the real token). Reverted after
    confirming; see PR report for the exact before/after run.
    """

    # Fixed test-only AES key, not a real credential.
    _KEY = "d4f9317783becee1a4415c1a1229b9258e7a90b768d72a9e2c7dc891af661df6"  # gitleaks:allow

    def _encrypt_for_test(self, plaintext: str) -> str:
        """Same AES-256-GCM wire format as `token_crypto`/`platform_integrations_crypto`."""
        import base64
        import os as _os

        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        key = bytes.fromhex(self._KEY)
        iv = _os.urandom(12)
        ciphertext_and_tag = AESGCM(key).encrypt(iv, plaintext.encode("utf-8"), None)
        return base64.b64encode(iv + ciphertext_and_tag).decode("ascii")

    def _patch_httpx(self, monkeypatch: Any, handler: Any) -> None:
        real_async_client = httpx.AsyncClient

        def _factory(*args: Any, **kwargs: Any) -> httpx.AsyncClient:
            kwargs["transport"] = httpx.MockTransport(handler)
            return real_async_client(*args, **kwargs)

        monkeypatch.setattr(httpx, "AsyncClient", _factory)

    async def test_encrypted_token_is_decrypted_before_send(
        self, client: Any, platform_db: Any, monkeypatch: Any
    ) -> None:
        monkeypatch.setenv("CREDENTIAL_ENCRYPTION_KEY", self._KEY)
        real_token = "real-plaintext-twitch-oauth-token"
        encrypted_token = self._encrypt_for_test(real_token)
        _seed_bot_credential(platform_db, platform="twitch", access_token=encrypted_token)

        received_auth_header: dict[str, str] = {}

        def _handler(req: httpx.Request) -> httpx.Response:
            received_auth_header["value"] = req.headers.get("authorization", "")
            return httpx.Response(200, json={})

        self._patch_httpx(monkeypatch, _handler)
        response = await client.post(
            "/api/v1/superadmin/platform-config/twitch/test", headers=_admin_headers()
        )
        body = await response.get_json()
        assert body["data"]["valid"] is True
        assert real_token in received_auth_header["value"]

    async def test_legacy_plaintext_token_still_works(
        self, client: Any, platform_db: Any, monkeypatch: Any
    ) -> None:
        """A pre-fix row (`is_encrypted` not actually true ciphertext) still authenticates."""
        monkeypatch.setenv("CREDENTIAL_ENCRYPTION_KEY", self._KEY)
        _seed_bot_credential(platform_db, platform="twitch", access_token="tok_abc")

        received_auth_header: dict[str, str] = {}

        def _handler(req: httpx.Request) -> httpx.Response:
            received_auth_header["value"] = req.headers.get("authorization", "")
            return httpx.Response(200, json={})

        self._patch_httpx(monkeypatch, _handler)
        response = await client.post(
            "/api/v1/superadmin/platform-config/twitch/test", headers=_admin_headers()
        )
        body = await response.get_json()
        assert body["data"]["valid"] is True
        assert "tok_abc" in received_auth_header["value"]


class TestHubSettings:
    async def test_get_settings_empty(self, client: Any) -> None:
        response = await client.get("/api/v1/superadmin/settings", headers=_admin_headers())
        assert response.status_code == 200
        body = await response.get_json()
        assert body["data"] == {}

    async def test_update_settings_upserts(self, client: Any, platform_db: Any) -> None:
        response = await client.put(
            "/api/v1/superadmin/settings",
            headers=_admin_headers(),
            json={"signup_enabled": "true"},
        )
        assert response.status_code == 200
        body = await response.get_json()
        assert body["data"]["signup_enabled"] == "true"

        # Update again -- must UPDATE the existing row, not duplicate it.
        response2 = await client.put(
            "/api/v1/superadmin/settings",
            headers=_admin_headers(),
            json={"signup_enabled": "false"},
        )
        body2 = await response2.get_json()
        assert body2["data"]["signup_enabled"] == "false"
        rows = await platform_db.select_async(
            platform_db.dal(platform_db.dal.hub_settings.setting_key == "signup_enabled")
        )
        assert len(rows) == 1

    async def test_update_settings_non_dict_body_is_400(self, client: Any) -> None:
        response = await client.put(
            "/api/v1/superadmin/settings", headers=_admin_headers(), json=[1, 2, 3]
        )
        assert response.status_code == 400
