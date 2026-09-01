"""`services/ai_routing/config_service.py` -- real pydal queries against `ai_routing_db`.

BYOK key validation (`clients.validate_byok_key`) is monkeypatched here --
that real-HTTP-call logic has its own dedicated coverage in
`tests/test_ai_routing_clients.py`; this file only needs to trust the
result. Encryption itself is NOT mocked -- `set_byok_key`/
`get_active_byok_key_plaintext` round-trip through the real
`byok_crypto.encrypt_key`/`decrypt_key` AES-256-GCM primitive.

Fail-first proof (executed, not narrated): temporarily made `set_byok_key()`
skip the `await validate_byok_key(...)` call entirely -- `test_set_byok_key_rejects_invalid_key`
went red (a rejected key would have been silently encrypted and stored);
reverted, confirmed green again.
"""

from __future__ import annotations

from typing import Any

import pytest

from services.ai_routing import config_service
from services.ai_routing.errors import ApiError


@pytest.fixture(autouse=True)
def _byok_encryption_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """A real, fixed 32-byte hex key -- `AI_BYOK_ENCRYPTION_KEY` (`byok_crypto.py`'s env var)."""
    monkeypatch.setenv("AI_BYOK_ENCRYPTION_KEY", "11" * 32)


@pytest.fixture(autouse=True)
def _stub_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    """By default, every BYOK key "validates" -- individual tests override to force a rejection."""

    async def _ok(provider: str, api_key: str, **kwargs: Any) -> None:
        return None

    monkeypatch.setattr(config_service, "validate_byok_key", _ok)


@pytest.fixture
def config_db(ai_routing_db: Any) -> Any:
    dal = ai_routing_db.dal
    tenant = dal(dal.tenants.slug == "acme-corp").select().first()
    community_id = dal.communities.insert(name="acme", tenant_id=tenant.id, is_active=True)
    dal.commit()
    return ai_routing_db, community_id


class TestAIConfig:
    async def test_get_config_defaults_when_unset(self, config_db: Any) -> None:
        async_dal, community_id = config_db
        cfg = await config_service.get_ai_config(
            async_dal, async_dal.dal, community_id=community_id
        )
        assert cfg.preferred_tier == "free"
        assert cfg.byok_provider is None
        assert cfg.on_insufficient_balance == "fallback_free"

    async def test_set_then_get_round_trips(self, config_db: Any) -> None:
        async_dal, community_id = config_db
        await config_service.set_ai_config(
            async_dal,
            async_dal.dal,
            community_id=community_id,
            preferred_tier="premium",
            byok_provider=None,
            on_insufficient_balance="block",
            updated_by_user_id=1,
        )
        cfg = await config_service.get_ai_config(
            async_dal, async_dal.dal, community_id=community_id
        )
        assert cfg.preferred_tier == "premium"
        assert cfg.on_insufficient_balance == "block"

    async def test_set_config_is_upsert(self, config_db: Any) -> None:
        async_dal, community_id = config_db
        await config_service.set_ai_config(
            async_dal,
            async_dal.dal,
            community_id=community_id,
            preferred_tier="premium",
            byok_provider=None,
            on_insufficient_balance="block",
            updated_by_user_id=1,
        )
        await config_service.set_ai_config(
            async_dal,
            async_dal.dal,
            community_id=community_id,
            preferred_tier="byok",
            byok_provider="openai",
            on_insufficient_balance="fallback_free",
            updated_by_user_id=1,
        )
        cfg = await config_service.get_ai_config(
            async_dal, async_dal.dal, community_id=community_id
        )
        assert cfg.preferred_tier == "byok"
        assert cfg.byok_provider == "openai"

    async def test_invalid_tier_raises_bad_request(self, config_db: Any) -> None:
        async_dal, community_id = config_db
        with pytest.raises(ApiError) as exc_info:
            await config_service.set_ai_config(
                async_dal,
                async_dal.dal,
                community_id=community_id,
                preferred_tier="not-a-real-tier",
                byok_provider=None,
                on_insufficient_balance="block",
                updated_by_user_id=1,
            )
        assert exc_info.value.status_code == 400


class TestByokKeys:
    async def test_set_key_is_encrypted_at_rest(self, config_db: Any) -> None:
        async_dal, community_id = config_db
        await config_service.set_byok_key(
            async_dal,
            async_dal.dal,
            community_id=community_id,
            provider="openai",
            plaintext_key="sk-super-secret-value-123",
            created_by_user_id=1,
        )
        # `hub_api/PORTING.md` Gotcha #2 -- `insert_async` never commits; a
        # bare synchronous `dal(...)` read is a DIFFERENT connection and
        # sees nothing. Assert via `select_async` (same connection as the
        # write) instead.
        rows = await async_dal.select_async(
            async_dal.dal(async_dal.dal.ai_byok_keys.community_id == community_id)
        )
        row = rows.first()
        assert "sk-super-secret-value-123" not in row.encrypted_key
        assert row.key_last4 == "-123"

    async def test_get_active_key_plaintext_decrypts_correctly(self, config_db: Any) -> None:
        async_dal, community_id = config_db
        await config_service.set_byok_key(
            async_dal,
            async_dal.dal,
            community_id=community_id,
            provider="anthropic",
            plaintext_key="sk-ant-original-value",
            created_by_user_id=1,
        )
        plaintext = await config_service.get_active_byok_key_plaintext(
            async_dal, async_dal.dal, community_id=community_id, provider="anthropic"
        )
        assert plaintext == "sk-ant-original-value"

    async def test_get_active_key_plaintext_none_when_unconfigured(self, config_db: Any) -> None:
        async_dal, community_id = config_db
        plaintext = await config_service.get_active_byok_key_plaintext(
            async_dal, async_dal.dal, community_id=community_id, provider="openai"
        )
        assert plaintext is None

    async def test_rotate_replaces_the_key(self, config_db: Any) -> None:
        async_dal, community_id = config_db
        await config_service.set_byok_key(
            async_dal,
            async_dal.dal,
            community_id=community_id,
            provider="openai",
            plaintext_key="sk-original",
            created_by_user_id=1,
        )
        await config_service.set_byok_key(
            async_dal,
            async_dal.dal,
            community_id=community_id,
            provider="openai",
            plaintext_key="sk-rotated",
            created_by_user_id=1,
        )
        plaintext = await config_service.get_active_byok_key_plaintext(
            async_dal, async_dal.dal, community_id=community_id, provider="openai"
        )
        assert plaintext == "sk-rotated"
        keys = await config_service.list_byok_keys(
            async_dal, async_dal.dal, community_id=community_id
        )
        assert len(keys) == 1  # upsert, not a second row
        assert keys[0].rotated_at is not None

    async def test_delete_deactivates_not_hard_deletes(self, config_db: Any) -> None:
        async_dal, community_id = config_db
        await config_service.set_byok_key(
            async_dal,
            async_dal.dal,
            community_id=community_id,
            provider="openai",
            plaintext_key="sk-original",
            created_by_user_id=1,
        )
        await config_service.delete_byok_key(
            async_dal, async_dal.dal, community_id=community_id, provider="openai"
        )
        plaintext = await config_service.get_active_byok_key_plaintext(
            async_dal, async_dal.dal, community_id=community_id, provider="openai"
        )
        assert plaintext is None  # inactive, so no longer "active"
        keys = await config_service.list_byok_keys(
            async_dal, async_dal.dal, community_id=community_id
        )
        assert len(keys) == 1  # still on file, just inactive
        assert keys[0].is_active is False

    async def test_delete_unconfigured_provider_is_404(self, config_db: Any) -> None:
        async_dal, community_id = config_db
        with pytest.raises(ApiError) as exc_info:
            await config_service.delete_byok_key(
                async_dal, async_dal.dal, community_id=community_id, provider="anthropic"
            )
        assert exc_info.value.status_code == 404

    async def test_set_byok_key_rejects_invalid_key(
        self, config_db: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def _reject(provider: str, api_key: str, **kwargs: Any) -> None:
            raise ApiError("nope", 400, "AI_BYOK_KEY_INVALID")

        monkeypatch.setattr(config_service, "validate_byok_key", _reject)
        async_dal, community_id = config_db
        with pytest.raises(ApiError) as exc_info:
            await config_service.set_byok_key(
                async_dal,
                async_dal.dal,
                community_id=community_id,
                provider="openai",
                plaintext_key="sk-bad",
                created_by_user_id=1,
            )
        assert exc_info.value.code == "AI_BYOK_KEY_INVALID"
        # Never written to the DB -- rejected before any insert.
        rows = async_dal.dal(async_dal.dal.ai_byok_keys.community_id == community_id).select()
        assert not rows
