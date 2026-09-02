"""RefreshService Encryption Wiring Tests.

Covers the two boundaries `refresh_service.py` was fixed at (SECURITY
HIGH): `_update_tokens()` must persist ciphertext, never the plaintext
OAuth response fields, and `_decrypt_integration()` must correctly
decrypt a freshly-fetched encrypted row while passing legacy plaintext
rows through unchanged.

Fail-first proof: see `test_token_crypto.py`'s own module docstring for
the exact before/after run against `_update_tokens`.
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock

import pytest

os.environ.setdefault(
    "CREDENTIAL_ENCRYPTION_KEY", "d4f9317783becee1a4415c1a1229b9258e7a90b768d72a9e2c7dc891af661df6"
)

from .refresh_service import RefreshService  # noqa: E402 - env var must be set first
from .token_crypto import decrypt_value, encrypt_value  # noqa: E402


@pytest.fixture
def service() -> RefreshService:
    return RefreshService(database_url="postgresql://u:p@localhost/db", redis_url="redis://localhost")


class TestUpdateTokensEncryptsOnWrite:
    async def test_update_tokens_persists_ciphertext_not_plaintext(
        self, service: RefreshService
    ) -> None:
        captured: dict = {}

        async def fake_execute(sql: str, *params: object) -> None:
            captured["sql"] = sql
            captured["params"] = params

        conn = MagicMock()
        conn.execute = AsyncMock(side_effect=fake_execute)
        acquire_ctx = MagicMock()
        acquire_ctx.__aenter__ = AsyncMock(return_value=conn)
        acquire_ctx.__aexit__ = AsyncMock(return_value=False)
        service._pool = MagicMock()
        service._pool.acquire = MagicMock(return_value=acquire_ctx)

        await service._update_tokens(
            integration_id=42,
            platform="twitch",
            new_tokens={
                "access_token": "plaintext-access-token",
                "refresh_token": "plaintext-refresh-token",
                "token_type": "Bearer",
            },
        )

        access_token_param, refresh_token_param = captured["params"][0], captured["params"][1]
        assert access_token_param != "plaintext-access-token"
        assert refresh_token_param != "plaintext-refresh-token"
        assert decrypt_value(access_token_param) == "plaintext-access-token"
        assert decrypt_value(refresh_token_param) == "plaintext-refresh-token"
        assert "is_encrypted = TRUE" in captured["sql"]

    async def test_update_tokens_sql_never_contains_plaintext_literal(
        self, service: RefreshService
    ) -> None:
        """Belt-and-suspenders: the captured SQL text itself never embeds the plaintext."""
        captured: dict = {}

        async def fake_execute(sql: str, *params: object) -> None:
            captured["sql"] = sql
            captured["params"] = params

        conn = MagicMock()
        conn.execute = AsyncMock(side_effect=fake_execute)
        acquire_ctx = MagicMock()
        acquire_ctx.__aenter__ = AsyncMock(return_value=conn)
        acquire_ctx.__aexit__ = AsyncMock(return_value=False)
        service._pool = MagicMock()
        service._pool.acquire = MagicMock(return_value=acquire_ctx)

        await service._update_tokens(
            integration_id=1,
            platform="discord",
            new_tokens={"access_token": "SENTINEL_TOKEN_VALUE", "refresh_token": "r"},
        )

        assert "SENTINEL_TOKEN_VALUE" not in captured["sql"]
        assert "SENTINEL_TOKEN_VALUE" not in captured["params"]


class TestDecryptIntegrationRow:
    def test_decrypts_encrypted_fields(self, service: RefreshService) -> None:
        row = {
            "access_token": encrypt_value("real-access-token"),
            "refresh_token": encrypt_value("real-refresh-token"),
            "client_secret": encrypt_value("real-client-secret"),
            "is_encrypted": True,
            "platform": "twitch",
        }
        result = service._decrypt_integration(dict(row))
        assert result["access_token"] == "real-access-token"
        assert result["refresh_token"] == "real-refresh-token"
        assert result["client_secret"] == "real-client-secret"

    def test_legacy_plaintext_row_unaffected(self, service: RefreshService) -> None:
        row = {
            "access_token": "legacy-plaintext-access",
            "refresh_token": "legacy-plaintext-refresh",
            "client_secret": "legacy-plaintext-secret",
            "is_encrypted": False,
            "platform": "discord",
        }
        result = service._decrypt_integration(dict(row))
        assert result["access_token"] == "legacy-plaintext-access"
        assert result["refresh_token"] == "legacy-plaintext-refresh"
        assert result["client_secret"] == "legacy-plaintext-secret"

    def test_is_encrypted_none_treated_as_legacy_plaintext(self, service: RefreshService) -> None:
        row = {
            "access_token": "raw-value",
            "refresh_token": "raw-refresh",
            "client_secret": None,
            "is_encrypted": None,
            "platform": "slack",
        }
        result = service._decrypt_integration(dict(row))
        assert result["access_token"] == "raw-value"
