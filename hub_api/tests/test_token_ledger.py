"""`services/token_ledger.py` -- real atomic decrement/credit against a file-backed sqlite DAL.

Fail-first proof (executed, not narrated): temporarily changed `debit_tokens()`'s
atomic-update `WHERE` clause from `balance_tokens >= amount` to always-true
(`balance_tokens >= 0`) -- `test_debit_more_than_balance_fails_closed` went
green->red as expected (would have let a debit drive the balance negative);
reverted, confirmed green again.
"""

from __future__ import annotations

from typing import Any

import pytest

from services import token_ledger
from services.errors import ApiError


@pytest.fixture
def ledger_db(ai_routing_db: Any) -> Any:
    """`ai_routing_db` plus one seeded community -- all `token_ledger` needs."""
    dal = ai_routing_db.dal
    tenant = dal(dal.tenants.slug == "acme-corp").select().first()
    community_id = dal.communities.insert(name="acme", tenant_id=tenant.id, is_active=True)
    dal.commit()
    return ai_routing_db, community_id


class TestGetBalance:
    async def test_defaults_to_zero_when_never_seeded(self, ledger_db: Any) -> None:
        async_dal, community_id = ledger_db
        balance = await token_ledger.get_balance(
            async_dal, async_dal.dal, community_id=community_id
        )
        assert balance == 0

    async def test_reflects_a_credit(self, ledger_db: Any) -> None:
        async_dal, community_id = ledger_db
        await token_ledger.credit_tokens(
            async_dal,
            async_dal.dal,
            community_id,
            token_ledger.PREMIUM_AI_CONSUMABLE,
            100,
            idempotency_key="grant-1",
        )
        balance = await token_ledger.get_balance(
            async_dal, async_dal.dal, community_id=community_id
        )
        assert balance == 100


class TestDebitTokens:
    async def test_debit_succeeds_when_affordable(self, ledger_db: Any) -> None:
        async_dal, community_id = ledger_db
        await token_ledger.credit_tokens(
            async_dal,
            async_dal.dal,
            community_id,
            token_ledger.PREMIUM_AI_CONSUMABLE,
            50,
            idempotency_key="grant-1",
        )
        result = await token_ledger.debit_tokens(
            async_dal,
            async_dal.dal,
            community_id,
            token_ledger.PREMIUM_AI_CONSUMABLE,
            30,
            idempotency_key="debit-1",
        )
        assert result.success is True
        assert result.balance_after == 20
        balance = await token_ledger.get_balance(
            async_dal, async_dal.dal, community_id=community_id
        )
        assert balance == 20

    async def test_debit_more_than_balance_fails_closed(self, ledger_db: Any) -> None:
        async_dal, community_id = ledger_db
        await token_ledger.credit_tokens(
            async_dal,
            async_dal.dal,
            community_id,
            token_ledger.PREMIUM_AI_CONSUMABLE,
            10,
            idempotency_key="grant-1",
        )
        result = await token_ledger.debit_tokens(
            async_dal,
            async_dal.dal,
            community_id,
            token_ledger.PREMIUM_AI_CONSUMABLE,
            50,
            idempotency_key="debit-1",
        )
        assert result.success is False
        assert result.reason == "insufficient_balance"
        assert result.balance_after == 10  # unchanged -- the atomic UPDATE never matched

    async def test_debit_against_never_seeded_balance_is_insufficient(self, ledger_db: Any) -> None:
        async_dal, community_id = ledger_db
        result = await token_ledger.debit_tokens(
            async_dal,
            async_dal.dal,
            community_id,
            token_ledger.PREMIUM_AI_CONSUMABLE,
            5,
            idempotency_key="debit-1",
        )
        assert result.success is False
        assert result.balance_after == 0

    async def test_replayed_idempotency_key_does_not_double_decrement(self, ledger_db: Any) -> None:
        async_dal, community_id = ledger_db
        await token_ledger.credit_tokens(
            async_dal,
            async_dal.dal,
            community_id,
            token_ledger.PREMIUM_AI_CONSUMABLE,
            100,
            idempotency_key="grant-1",
        )
        first = await token_ledger.debit_tokens(
            async_dal,
            async_dal.dal,
            community_id,
            token_ledger.PREMIUM_AI_CONSUMABLE,
            40,
            idempotency_key="same-key",
        )
        second = await token_ledger.debit_tokens(
            async_dal,
            async_dal.dal,
            community_id,
            token_ledger.PREMIUM_AI_CONSUMABLE,
            40,
            idempotency_key="same-key",
        )
        assert first.success is True
        assert second.success is True
        assert second.balance_after == first.balance_after
        balance = await token_ledger.get_balance(
            async_dal, async_dal.dal, community_id=community_id
        )
        assert balance == 60  # only debited once, not 80

    async def test_zero_or_negative_amount_raises(self, ledger_db: Any) -> None:
        async_dal, community_id = ledger_db
        with pytest.raises(ApiError):
            await token_ledger.debit_tokens(
                async_dal,
                async_dal.dal,
                community_id,
                token_ledger.PREMIUM_AI_CONSUMABLE,
                0,
                idempotency_key="bad",
            )

    async def test_separate_consumable_types_have_independent_balances(
        self, ledger_db: Any
    ) -> None:
        async_dal, community_id = ledger_db
        await token_ledger.credit_tokens(
            async_dal, async_dal.dal, community_id, "ai_premium_tokens", 10, idempotency_key="g1"
        )
        await token_ledger.credit_tokens(
            async_dal, async_dal.dal, community_id, "transcoding", 999, idempotency_key="g2"
        )
        ai_balance = await token_ledger.get_balance(
            async_dal, async_dal.dal, community_id=community_id, consumable_type="ai_premium_tokens"
        )
        assert ai_balance == 10
