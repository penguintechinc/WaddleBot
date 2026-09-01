"""Minimal, real metered-consumable token ledger -- premium-AI's billing hook.

The full multi-consumable ledger (transcoding + premium-AI, purchase/refill,
stripe/paypal fulfillment) is a separate, parallel PR (`docs/plans/2026-08-31-
metered-token-billing-design.md`, `feature/v3-token-billing`). This module
defines the interface the premium-AI router needs *today* --
`debit_tokens()`/`get_balance()` against `ai_token_balances`/
`ai_token_transactions` (`services/schema.py::bind_ai_routing_tables()`,
migration 077) -- so premium-AI routing is never blocked on that PR landing.
Table names are deliberately distinct from the eventual `community_token_
balances`/`token_transactions` names that spec reserves, so the two never
collide at migration time; the real ledger PR is expected to reconcile/union
this module with its own, wider one.

Real, not a stub: `debit_tokens()` performs a genuine atomic conditional
decrement (`UPDATE ... WHERE balance_tokens >= amount`, the same
"database arbitrates the race, not application logic" pattern this repo
already uses for single-use claims -- `hub_api/PORTING.md` Gotcha #8,
`068_add_welcomed_users.sql`) plus an append-only `ai_token_transactions`
audit row, idempotent on `idempotency_key` (a replayed key short-circuits
to the previously recorded outcome instead of double-decrementing).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from services.errors import bad_request
from services.schema import bind_ai_routing_tables

#: The only consumable this module meters today -- premium-local-metered
#: AI inference (`services/ai_routing/router.py`). Kept as a module
#: constant (not hardcoded per call site) so the eventual multi-consumable
#: ledger PR has one place to see every `consumable_type` string this repo
#: already emits.
PREMIUM_AI_CONSUMABLE = "ai_premium_tokens"


@dataclass(slots=True, frozen=True)
class DebitResult:
    """Outcome of one `debit_tokens()` call -- always returned, never raises for "insufficient"."""

    success: bool
    balance_after: int
    reason: str | None = None


async def get_balance(
    async_dal: Any, dal: Any, *, community_id: int, consumable_type: str = PREMIUM_AI_CONSUMABLE
) -> int:
    """Return the community's spendable balance for `consumable_type` (0 if never seeded)."""
    bind_ai_routing_tables(dal)
    rows = await async_dal.select_async(
        dal(
            (dal.ai_token_balances.community_id == community_id)
            & (dal.ai_token_balances.consumable_type == consumable_type)
        )
    )
    if not rows:
        return 0
    balance: int = rows.first().balance_tokens
    return balance


async def _existing_transaction(async_dal: Any, dal: Any, *, idempotency_key: str) -> Any | None:
    rows = await async_dal.select_async(
        dal(dal.ai_token_transactions.idempotency_key == idempotency_key)
    )
    return rows.first() if rows else None


async def _ensure_balance_row(
    async_dal: Any, dal: Any, *, community_id: int, consumable_type: str
) -> None:
    """Insert a zero-balance row if one doesn't exist yet -- the atomic UPDATE below needs a row."""
    rows = await async_dal.select_async(
        dal(
            (dal.ai_token_balances.community_id == community_id)
            & (dal.ai_token_balances.consumable_type == consumable_type)
        )
    )
    if rows:
        return
    await async_dal.insert_async(
        dal.ai_token_balances,
        community_id=community_id,
        consumable_type=consumable_type,
        balance_tokens=0,
        lifetime_consumed=0,
        updated_at=datetime.now(UTC),
    )


async def debit_tokens(
    async_dal: Any,
    dal: Any,
    community_id: int,
    consumable_type: str,
    amount: int,
    *,
    idempotency_key: str,
    source_ref: str | None = None,
    actor_user_id: int | None = None,
) -> DebitResult:
    """Atomically decrement `community_id`'s `consumable_type` balance by `amount`.

    Never raises on "can't afford it" -- returns `DebitResult(success=False,
    reason="insufficient_balance", ...)` so the caller (the AI router) can
    apply its own block-vs-fallback policy (spec §2). Raises `ApiError`
    (400) only for a genuinely malformed call (`amount <= 0`), never for a
    business-as-usual insufficient-balance outcome.

    Idempotent: a replayed `idempotency_key` (same caller retry, e.g. after
    a network timeout) returns the ORIGINAL outcome without decrementing
    twice -- no `token_transactions` row is written for a declined attempt,
    so a retry after the community's balance later increases is free to
    re-evaluate against the new balance (that's a new attempt, not a
    replay of a committed one).
    """
    if amount <= 0:
        raise bad_request("debit amount must be positive")

    bind_ai_routing_tables(dal)

    existing = await _existing_transaction(async_dal, dal, idempotency_key=idempotency_key)
    if existing is not None:
        return DebitResult(success=True, balance_after=existing.balance_after, reason="replayed")

    await _ensure_balance_row(
        async_dal, dal, community_id=community_id, consumable_type=consumable_type
    )

    affordable_query = (
        (dal.ai_token_balances.community_id == community_id)
        & (dal.ai_token_balances.consumable_type == consumable_type)
        & (dal.ai_token_balances.balance_tokens >= amount)
    )
    updated_count = await async_dal.update_async(
        affordable_query,
        balance_tokens=dal.ai_token_balances.balance_tokens - amount,
        lifetime_consumed=dal.ai_token_balances.lifetime_consumed + amount,
        updated_at=datetime.now(UTC),
    )

    current = await get_balance(
        async_dal, dal, community_id=community_id, consumable_type=consumable_type
    )
    if not updated_count:
        return DebitResult(success=False, balance_after=current, reason="insufficient_balance")

    await async_dal.insert_async(
        dal.ai_token_transactions,
        community_id=community_id,
        consumable_type=consumable_type,
        amount_tokens=-amount,
        balance_after=current,
        idempotency_key=idempotency_key,
        source_ref=source_ref,
        actor_user_id=actor_user_id,
        metadata=None,
        created_at=datetime.now(UTC),
    )
    return DebitResult(success=True, balance_after=current)


async def credit_tokens(
    async_dal: Any,
    dal: Any,
    community_id: int,
    consumable_type: str,
    amount: int,
    *,
    idempotency_key: str,
    source_ref: str | None = None,
    actor_user_id: int | None = None,
) -> DebitResult:
    """Credit (grant/purchase/refund) `amount` tokens -- the debit path's mirror image.

    Real, minimal purchase/grant hook (not wired to a payment provider
    here -- that's the token-billing PR's `POST /marketplace/tokens/
    purchase` + webhook fulfillment); used today by superadmin manual
    grants and by tests seeding a balance for the block-with-fallback
    path. Idempotent the same way `debit_tokens()` is.
    """
    if amount <= 0:
        raise bad_request("credit amount must be positive")

    bind_ai_routing_tables(dal)

    existing = await _existing_transaction(async_dal, dal, idempotency_key=idempotency_key)
    if existing is not None:
        return DebitResult(success=True, balance_after=existing.balance_after, reason="replayed")

    await _ensure_balance_row(
        async_dal, dal, community_id=community_id, consumable_type=consumable_type
    )

    await async_dal.update_async(
        (dal.ai_token_balances.community_id == community_id)
        & (dal.ai_token_balances.consumable_type == consumable_type),
        balance_tokens=dal.ai_token_balances.balance_tokens + amount,
        updated_at=datetime.now(UTC),
    )
    current = await get_balance(
        async_dal, dal, community_id=community_id, consumable_type=consumable_type
    )
    await async_dal.insert_async(
        dal.ai_token_transactions,
        community_id=community_id,
        consumable_type=consumable_type,
        amount_tokens=amount,
        balance_after=current,
        idempotency_key=idempotency_key,
        source_ref=source_ref,
        actor_user_id=actor_user_id,
        metadata=None,
        created_at=datetime.now(UTC),
    )
    return DebitResult(success=True, balance_after=current)
