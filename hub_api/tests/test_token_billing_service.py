"""`services/token_billing_service.py` -- the metered-token-billing ledger.

Fail-first verification performed for the two SECURITY-relevant guards
below (documented here since the guard itself lives in a single line of
`debit_tokens()`, not something a reader can eyeball-verify from the test
alone -- `hub_api/PORTING.md`'s Test pattern section):

1. `TestDebitBlocksInsufficientBalance.test_insufficient_balance_blocked`:
   run against a deliberately-broken version of `_guarded_debit_sync`'s
   WHERE clause (`balance >= amount` removed, i.e. an unconditional
   decrement) -- went RED (the debit succeeded and drove the balance
   negative, violating both the `balance >= 0` CHECK constraint and this
   test's own assertion). Reverting to the real guarded UPDATE turned it
   GREEN.
2. `TestConcurrentDebitsDoNotOversell.test_concurrent_debits_never_oversell`:
   this test caught a REAL bug during development, not a synthetic one --
   the first implementation used `async with async_dal.transaction_async():
   await async_dal.update_async(...); ...; await async_dal.insert_async(...)`
   (multiple separate executor submissions with `await` points between
   them). Under this test's own concurrent load it went RED: `len(succeeded)
   == 10` (correct) but the community's FINAL balance was still `10`
   (unchanged) instead of `0` -- `transaction_async()`'s rollback (from a
   sibling, concurrently-interleaved BLOCKED debit) was undoing OTHER,
   already-"successful" coroutines' uncommitted writes, because pydal's
   `self.dal` is one shared, connection-scoped ambient transaction, not a
   transaction scoped to each individual coroutine's own writes. Rewriting
   `debit_tokens()` to submit ONE combined synchronous function
   (`_guarded_debit_sync` -- guarded UPDATE + balance re-read + ledger
   INSERT + COMMIT, no `await` anywhere inside it) as a single executor
   job turned this test GREEN. See `token_billing_service.py`'s own
   top-of-file docstring for the full writeup.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from services import token_billing_service as svc
from services.errors import ApiError
from services.token_billing_service import (
    REASON_INSUFFICIENT_BALANCE,
    REASON_LEDGER_UNAVAILABLE,
    REASON_NO_BALANCE,
    REASON_UNKNOWN_PRODUCT,
    credit_tokens,
    debit_tokens,
    list_balances,
    list_products,
    list_transactions,
)
from tests.conftest import seed_community, seed_token_balance, seed_token_product


def _dal(token_billing_db: Any) -> tuple[Any, Any]:
    return token_billing_db, token_billing_db.dal


class TestListProducts:
    """`list_products()` -- catalog reads."""

    async def test_active_only_by_default(self, token_billing_db: Any) -> None:
        async_dal, dal = _dal(token_billing_db)
        seed_token_product(token_billing_db, key="active_one", active=True)
        seed_token_product(token_billing_db, key="inactive_one", active=False)

        products = await list_products(async_dal, dal)

        keys = {p.key for p in products}
        assert keys == {"active_one"}

    async def test_include_inactive(self, token_billing_db: Any) -> None:
        async_dal, dal = _dal(token_billing_db)
        seed_token_product(token_billing_db, key="active_one", active=True)
        seed_token_product(token_billing_db, key="inactive_one", active=False)

        products = await list_products(async_dal, dal, include_inactive=True)

        keys = {p.key for p in products}
        assert keys == {"active_one", "inactive_one"}


class TestCreditTokens:
    """`credit_tokens()` -- grant path (admin action / purchase grant)."""

    async def test_creates_balance_row_on_first_credit(self, token_billing_db: Any) -> None:
        async_dal, dal = _dal(token_billing_db)
        product_id = seed_token_product(token_billing_db, key="ai_call", tokens_granted=10)
        community_id = seed_community(token_billing_db)

        result = await credit_tokens(
            async_dal,
            dal,
            community_id=community_id,
            product_key="ai_call",
            amount=25,
            reason="purchase:pack_a",
            ref="order-1",
        )

        assert result.ok is True
        assert result.balance_after == 25
        assert result.transaction_id is not None

        row = (
            dal(
                (dal.community_token_balances.community_id == community_id)
                & (dal.community_token_balances.product_id == product_id)
            )
            .select()
            .first()
        )
        assert row.balance == 25

        txn = dal(dal.token_transactions.id == result.transaction_id).select().first()
        assert txn.delta == 25
        assert txn.balance_after == 25
        assert txn.reason == "purchase:pack_a"
        assert txn.ref == "order-1"

    async def test_increments_existing_balance(self, token_billing_db: Any) -> None:
        async_dal, dal = _dal(token_billing_db)
        product_id = seed_token_product(token_billing_db, key="ai_call")
        community_id = seed_community(token_billing_db)
        seed_token_balance(
            token_billing_db, community_id=community_id, product_id=product_id, balance=10
        )

        result = await credit_tokens(
            async_dal,
            dal,
            community_id=community_id,
            product_key="ai_call",
            amount=5,
            reason="admin_grant",
        )

        assert result.ok is True
        assert result.balance_after == 15

    async def test_concurrent_first_credit_race_retries_as_update(
        self, token_billing_db: Any
    ) -> None:
        """`_guarded_credit_sync`'s cross-connection race retry path (see its own docstring).

        No balance row exists yet -- a genuine first-ever credit. The
        patched `insert` simulates a concurrent (different-connection)
        winner: by the time OUR insert attempt runs, the row already
        exists (inserted by the patch itself, standing in for the sibling
        connection), so OUR insert is the one that would violate the
        migration 076 `UNIQUE (community_id, product_id)` constraint.
        Proves the retry-as-UPDATE path recovers the credit rather than
        losing it. Manual save/restore (not `monkeypatch.setattr`) --
        pydal's `Table.__setattr__` guards against a SECOND assignment to
        an existing method name (raises `SyntaxError: Object exists and
        cannot be redefined`), which `monkeypatch`'s own automatic
        teardown restore trips over.
        """
        async_dal, dal = _dal(token_billing_db)
        product_id = seed_token_product(token_billing_db, key="ai_call")
        community_id = seed_community(token_billing_db)

        real_insert = dal.community_token_balances.insert
        call_count = 0

        def _insert_then_raise(**fields: Any) -> Any:
            nonlocal call_count
            call_count += 1
            real_insert(community_id=community_id, product_id=product_id, balance=3)
            dal.commit()
            raise RuntimeError("simulated UNIQUE constraint violation")

        object.__setattr__(dal.community_token_balances, "insert", _insert_then_raise)
        try:
            result = await credit_tokens(
                async_dal,
                dal,
                community_id=community_id,
                product_key="ai_call",
                amount=5,
                reason="race_test",
            )
        finally:
            object.__setattr__(dal.community_token_balances, "insert", real_insert)

        assert call_count == 1
        assert result.ok is True
        assert result.balance_after == 8

    async def test_non_positive_amount_rejected(self, token_billing_db: Any) -> None:
        async_dal, dal = _dal(token_billing_db)
        seed_token_product(token_billing_db, key="ai_call")
        community_id = seed_community(token_billing_db)

        with pytest.raises(ApiError) as exc_info:
            await credit_tokens(
                async_dal,
                dal,
                community_id=community_id,
                product_key="ai_call",
                amount=0,
                reason="x",
            )
        assert exc_info.value.status_code == 400

    async def test_unknown_product_rejected(self, token_billing_db: Any) -> None:
        async_dal, dal = _dal(token_billing_db)
        community_id = seed_community(token_billing_db)

        with pytest.raises(ApiError) as exc_info:
            await credit_tokens(
                async_dal,
                dal,
                community_id=community_id,
                product_key="does_not_exist",
                amount=5,
                reason="x",
            )
        assert exc_info.value.status_code == 404


class TestDebitTokensSuccess:
    """`debit_tokens()` -- the internal metering API's happy path."""

    async def test_decrements_balance_and_writes_ledger_row(self, token_billing_db: Any) -> None:
        async_dal, dal = _dal(token_billing_db)
        product_id = seed_token_product(token_billing_db, key="ai_call")
        community_id = seed_community(token_billing_db)
        seed_token_balance(
            token_billing_db, community_id=community_id, product_id=product_id, balance=10
        )

        result = await debit_tokens(
            async_dal,
            dal,
            community_id=community_id,
            product_key="ai_call",
            amount=3,
            reason="ai_route:gpt-4o",
            ref="req-42",
        )

        assert result.ok is True
        assert result.balance_after == 7
        assert result.transaction_id is not None

        row = (
            dal(
                (dal.community_token_balances.community_id == community_id)
                & (dal.community_token_balances.product_id == product_id)
            )
            .select()
            .first()
        )
        assert row.balance == 7

        txn = dal(dal.token_transactions.id == result.transaction_id).select().first()
        assert txn.delta == -3
        assert txn.balance_after == 7
        assert txn.reason == "ai_route:gpt-4o"
        assert txn.ref == "req-42"

    async def test_exact_balance_drains_to_zero(self, token_billing_db: Any) -> None:
        """Spending exactly the balance succeeds and leaves 0, not blocked (`>=`, not `>`)."""
        async_dal, dal = _dal(token_billing_db)
        product_id = seed_token_product(token_billing_db, key="ai_call")
        community_id = seed_community(token_billing_db)
        seed_token_balance(
            token_billing_db, community_id=community_id, product_id=product_id, balance=5
        )

        result = await debit_tokens(
            async_dal, dal, community_id=community_id, product_key="ai_call", amount=5, reason="x"
        )

        assert result.ok is True
        assert result.balance_after == 0

    async def test_non_positive_amount_rejected(self, token_billing_db: Any) -> None:
        async_dal, dal = _dal(token_billing_db)
        seed_token_product(token_billing_db, key="ai_call")
        community_id = seed_community(token_billing_db)

        with pytest.raises(ApiError) as exc_info:
            await debit_tokens(
                async_dal,
                dal,
                community_id=community_id,
                product_key="ai_call",
                amount=-1,
                reason="x",
            )
        assert exc_info.value.status_code == 400


class TestDebitBlocksInsufficientBalance:
    """BLOCK-WITH-FALLBACK: an under-funded debit is denied, never silently allowed.

    See this module's own top-of-file docstring for the fail-first
    verification performed against a deliberately-unguarded UPDATE.
    """

    async def test_insufficient_balance_blocked(self, token_billing_db: Any) -> None:
        async_dal, dal = _dal(token_billing_db)
        product_id = seed_token_product(token_billing_db, key="ai_call")
        community_id = seed_community(token_billing_db)
        seed_token_balance(
            token_billing_db, community_id=community_id, product_id=product_id, balance=2
        )

        result = await debit_tokens(
            async_dal, dal, community_id=community_id, product_key="ai_call", amount=3, reason="x"
        )

        assert result.ok is False
        assert result.blocked_reason == REASON_INSUFFICIENT_BALANCE
        assert result.balance_after is None
        assert result.transaction_id is None

        # Balance MUST be unchanged -- a blocked debit is a no-op, not a
        # partial/negative write.
        row = (
            dal(
                (dal.community_token_balances.community_id == community_id)
                & (dal.community_token_balances.product_id == product_id)
            )
            .select()
            .first()
        )
        assert row.balance == 2
        assert dal(dal.token_transactions.community_id == community_id).count() == 0

    async def test_no_balance_row_blocked_distinctly(self, token_billing_db: Any) -> None:
        """A community that never purchased this product gets `REASON_NO_BALANCE`, not a crash."""
        async_dal, dal = _dal(token_billing_db)
        seed_token_product(token_billing_db, key="ai_call")
        community_id = seed_community(token_billing_db)

        result = await debit_tokens(
            async_dal, dal, community_id=community_id, product_key="ai_call", amount=1, reason="x"
        )

        assert result.ok is False
        assert result.blocked_reason == REASON_NO_BALANCE

    async def test_unknown_product_blocked(self, token_billing_db: Any) -> None:
        async_dal, dal = _dal(token_billing_db)
        community_id = seed_community(token_billing_db)

        result = await debit_tokens(
            async_dal,
            dal,
            community_id=community_id,
            product_key="does_not_exist",
            amount=1,
            reason="x",
        )

        assert result.ok is False
        assert result.blocked_reason == REASON_UNKNOWN_PRODUCT

    async def test_inactive_product_blocked(self, token_billing_db: Any) -> None:
        async_dal, dal = _dal(token_billing_db)
        seed_token_product(token_billing_db, key="retired", active=False)
        community_id = seed_community(token_billing_db)

        result = await debit_tokens(
            async_dal, dal, community_id=community_id, product_key="retired", amount=1, reason="x"
        )

        assert result.ok is False
        assert result.blocked_reason == REASON_UNKNOWN_PRODUCT


class TestConcurrentDebitsDoNotOversell:
    """Atomicity: N concurrent debits against a fixed balance never oversell.

    See this module's own top-of-file docstring for the fail-first
    verification performed against a TOCTOU ("select then update")
    rewrite.
    """

    async def test_concurrent_debits_never_oversell(self, token_billing_db: Any) -> None:
        async_dal, dal = _dal(token_billing_db)
        product_id = seed_token_product(token_billing_db, key="ai_call")
        community_id = seed_community(token_billing_db)
        starting_balance = 10
        seed_token_balance(
            token_billing_db,
            community_id=community_id,
            product_id=product_id,
            balance=starting_balance,
        )

        # 25 concurrent 1-token debits against a balance of 10 -- at most
        # 10 can legitimately succeed.
        results = await asyncio.gather(
            *[
                debit_tokens(
                    async_dal,
                    dal,
                    community_id=community_id,
                    product_key="ai_call",
                    amount=1,
                    reason="concurrent_test",
                    ref=f"req-{i}",
                )
                for i in range(25)
            ]
        )

        succeeded = [r for r in results if r.ok]
        blocked = [r for r in results if not r.ok]
        assert len(succeeded) == starting_balance
        assert len(blocked) == 25 - starting_balance
        assert all(r.blocked_reason == REASON_INSUFFICIENT_BALANCE for r in blocked)

        final_row = (
            dal(
                (dal.community_token_balances.community_id == community_id)
                & (dal.community_token_balances.product_id == product_id)
            )
            .select()
            .first()
        )
        # The critical assertion: balance never goes negative, and lands
        # at exactly 0 -- not oversold, not undersold.
        assert final_row.balance == 0

        ledger_count = dal(dal.token_transactions.community_id == community_id).count()
        assert ledger_count == starting_balance


class TestLedgerUnavailableDegradesGracefully:
    """A DB failure mid-write degrades to a blocked result -- never a hard crash."""

    async def test_debit_returns_blocked_not_raised_on_db_error(
        self, token_billing_db: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async_dal, dal = _dal(token_billing_db)
        product_id = seed_token_product(token_billing_db, key="ai_call")
        community_id = seed_community(token_billing_db)
        seed_token_balance(
            token_billing_db, community_id=community_id, product_id=product_id, balance=10
        )

        def _boom(*args: Any, **kwargs: Any) -> Any:
            raise RuntimeError("simulated connection loss")

        # `_guarded_debit_sync` is the actual unit `debit_tokens()` submits
        # to the executor -- patching it (not `async_dal.update_async`,
        # which the new single-executor-job design no longer calls)
        # simulates a failure inside that atomic write.
        monkeypatch.setattr(svc, "_guarded_debit_sync", _boom)

        result = await debit_tokens(
            async_dal, dal, community_id=community_id, product_key="ai_call", amount=1, reason="x"
        )

        assert result.ok is False
        assert result.blocked_reason == REASON_LEDGER_UNAVAILABLE

    async def test_credit_returns_blocked_not_raised_on_db_error(
        self, token_billing_db: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async_dal, dal = _dal(token_billing_db)
        seed_token_product(token_billing_db, key="ai_call")
        community_id = seed_community(token_billing_db)

        def _boom(*args: Any, **kwargs: Any) -> Any:
            raise RuntimeError("simulated connection loss")

        monkeypatch.setattr(svc, "_guarded_credit_sync", _boom)

        result = await credit_tokens(
            async_dal, dal, community_id=community_id, product_key="ai_call", amount=5, reason="x"
        )

        assert result.ok is False
        assert result.blocked_reason == REASON_LEDGER_UNAVAILABLE


class TestListBalances:
    """`list_balances()` -- every active product, 0 for never-credited ones."""

    async def test_uncredited_product_shows_zero(self, token_billing_db: Any) -> None:
        async_dal, dal = _dal(token_billing_db)
        seed_token_product(token_billing_db, key="ai_call", name="AI Call")
        community_id = seed_community(token_billing_db)

        balances = await list_balances(async_dal, dal, community_id=community_id)

        assert len(balances) == 1
        assert balances[0].product_key == "ai_call"
        assert balances[0].balance == 0
        assert balances[0].updated_at is None

    async def test_credited_product_shows_real_balance(self, token_billing_db: Any) -> None:
        async_dal, dal = _dal(token_billing_db)
        product_id = seed_token_product(token_billing_db, key="ai_call")
        community_id = seed_community(token_billing_db)
        seed_token_balance(
            token_billing_db, community_id=community_id, product_id=product_id, balance=42
        )

        balances = await list_balances(async_dal, dal, community_id=community_id)

        assert balances[0].balance == 42

    async def test_inactive_product_excluded(self, token_billing_db: Any) -> None:
        async_dal, dal = _dal(token_billing_db)
        seed_token_product(token_billing_db, key="retired", active=False)
        community_id = seed_community(token_billing_db)

        balances = await list_balances(async_dal, dal, community_id=community_id)

        assert balances == []

    async def test_balance_scoped_to_its_own_community(self, token_billing_db: Any) -> None:
        """Two communities' balances for the same product never bleed into each other."""
        async_dal, dal = _dal(token_billing_db)
        product_id = seed_token_product(token_billing_db, key="ai_call")
        community_a = seed_community(token_billing_db, name="community-a")
        community_b = seed_community(token_billing_db, name="community-b")
        seed_token_balance(
            token_billing_db, community_id=community_a, product_id=product_id, balance=100
        )

        balances_a = await list_balances(async_dal, dal, community_id=community_a)
        balances_b = await list_balances(async_dal, dal, community_id=community_b)

        assert balances_a[0].balance == 100
        assert balances_b[0].balance == 0


class TestListTransactions:
    """`list_transactions()` -- pagination + filter coverage."""

    async def test_pagination(self, token_billing_db: Any) -> None:
        async_dal, dal = _dal(token_billing_db)
        product_id = seed_token_product(token_billing_db, key="ai_call")
        community_id = seed_community(token_billing_db)
        seed_token_balance(
            token_billing_db, community_id=community_id, product_id=product_id, balance=100
        )
        for i in range(5):
            await debit_tokens(
                async_dal,
                dal,
                community_id=community_id,
                product_key="ai_call",
                amount=1,
                reason=f"r{i}",
            )

        page1, total1 = await list_transactions(
            async_dal, dal, community_id=community_id, limit=2, offset=0
        )
        page2, total2 = await list_transactions(
            async_dal, dal, community_id=community_id, limit=2, offset=2
        )

        assert total1 == 5
        assert total2 == 5
        assert len(page1) == 2
        assert len(page2) == 2
        assert {t.id for t in page1}.isdisjoint({t.id for t in page2})

    async def test_filter_by_product_key(self, token_billing_db: Any) -> None:
        async_dal, dal = _dal(token_billing_db)
        product_a = seed_token_product(token_billing_db, key="product_a")
        product_b = seed_token_product(token_billing_db, key="product_b")
        community_id = seed_community(token_billing_db)
        seed_token_balance(
            token_billing_db, community_id=community_id, product_id=product_a, balance=10
        )
        seed_token_balance(
            token_billing_db, community_id=community_id, product_id=product_b, balance=10
        )
        await debit_tokens(
            async_dal, dal, community_id=community_id, product_key="product_a", amount=1, reason="a"
        )
        await debit_tokens(
            async_dal, dal, community_id=community_id, product_key="product_b", amount=1, reason="b"
        )

        rows, total = await list_transactions(
            async_dal, dal, community_id=community_id, product_key="product_a"
        )

        assert total == 1
        assert rows[0].product_key == "product_a"

    async def test_filter_by_date_range(self, token_billing_db: Any) -> None:
        async_dal, dal = _dal(token_billing_db)
        product_id = seed_token_product(token_billing_db, key="ai_call")
        community_id = seed_community(token_billing_db)
        seed_token_balance(
            token_billing_db, community_id=community_id, product_id=product_id, balance=10
        )
        await debit_tokens(
            async_dal, dal, community_id=community_id, product_key="ai_call", amount=1, reason="x"
        )
        now = datetime.now(UTC)

        in_range, in_range_total = await list_transactions(
            async_dal,
            dal,
            community_id=community_id,
            start=now - timedelta(hours=1),
            end=now + timedelta(hours=1),
        )
        before_range, before_total = await list_transactions(
            async_dal, dal, community_id=community_id, end=now - timedelta(hours=1)
        )

        assert in_range_total == 1
        assert before_total == 0
        assert before_range == []

    async def test_empty_result_for_unknown_product_filter(self, token_billing_db: Any) -> None:
        async_dal, dal = _dal(token_billing_db)
        product_id = seed_token_product(token_billing_db, key="ai_call")
        community_id = seed_community(token_billing_db)
        seed_token_balance(
            token_billing_db, community_id=community_id, product_id=product_id, balance=10
        )
        await debit_tokens(
            async_dal, dal, community_id=community_id, product_key="ai_call", amount=1, reason="x"
        )

        rows, total = await list_transactions(
            async_dal, dal, community_id=community_id, product_key="does_not_exist"
        )

        assert rows == []
        assert total == 0

    async def test_ordered_most_recent_first(self, token_billing_db: Any) -> None:
        async_dal, dal = _dal(token_billing_db)
        product_id = seed_token_product(token_billing_db, key="ai_call")
        community_id = seed_community(token_billing_db)
        seed_token_balance(
            token_billing_db, community_id=community_id, product_id=product_id, balance=10
        )
        first = await debit_tokens(
            async_dal,
            dal,
            community_id=community_id,
            product_key="ai_call",
            amount=1,
            reason="first",
        )
        second = await debit_tokens(
            async_dal,
            dal,
            community_id=community_id,
            product_key="ai_call",
            amount=1,
            reason="second",
        )

        rows, _ = await list_transactions(async_dal, dal, community_id=community_id)

        assert rows[0].id == second.transaction_id
        assert rows[1].id == first.transaction_id
