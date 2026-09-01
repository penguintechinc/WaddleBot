"""Real metered-consumable token ledger adapter -- premium-AI's billing hook.

Thin delegation layer, not an independent ledger: every call here forwards
to `services/token_billing_service.py` (#234's authoritative, atomic
`community_token_balances`/`token_transactions` ledger, migration 076) --
this module owns no balance/transaction arithmetic of its own. It exists so
`services/ai_routing/router.py` keeps calling a stable, `consumable_type`-
shaped API (`debit_tokens()`/`get_balance()`/`credit_tokens()`, signatures
unchanged from this module's original, parallel-ledger version) while
translating `consumable_type` to the real ledger's `product_key` vocabulary
underneath (`_PRODUCT_KEY_BY_CONSUMABLE`).

This module used to be a real-but-deliberately-parallel `ai_token_balances`/
`ai_token_transactions` ledger (migration 077), kept separate from #234's
wider design until it landed -- see git history for that version, and its
own docstring's promise: "the real ledger PR is expected to reconcile/union
this module with its own, wider one." Now that #234 is merged, this module
IS that reconciliation: premium-AI metering debits the SAME
`community_token_balances` rows the marketplace token-billing HTTP API
(`blueprints/v1/token_billing.py`) reads/credits, so a community's balance
is single-sourced regardless of which feature spent it. `PREMIUM_AI_
CONSUMABLE` maps to the real ledger's `"ai_routing_call"` `token_products`
catalog key (named in `token_billing_service.debit_tokens()`'s own
docstring, seeded by migration 078).

Idempotency: `debit_tokens()`/`credit_tokens()`'s `idempotency_key` is
stored as the real ledger's `ref` column and checked with a plain
`select_async()` immediately before delegating -- the exact same
check-then-act shape (and the same accepted race window: a genuinely
simultaneous replay of the SAME key, vanishingly rare for a caller-side
network-timeout retry, vs. two independently-issued keys) this module's
original `ai_token_balances`-backed version already used for its own
idempotency check. What changed for the better is the property that
actually matters under real concurrency -- never overselling a community's
balance -- which `token_billing_service`'s single guarded-UPDATE executor
job now enforces atomically, independent of (and not weakened by) this
check.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from services import token_billing_service
from services.errors import bad_request

#: The only consumable this module meters today -- premium-local-metered
#: AI inference (`services/ai_routing/router.py`). Kept as a module
#: constant (not hardcoded per call site) so every call site agrees on one
#: string.
PREMIUM_AI_CONSUMABLE = "ai_premium_tokens"

#: `consumable_type` -> real `token_products.key` (migration 076 catalog,
#: seeded by migration 078). Any `consumable_type` with no explicit
#: mapping here passes through unchanged as its own `product_key`
#: (forward-compatible with a future non-AI consumable sharing this same
#: adapter shape, e.g. a hypothetical `"transcoding"`) -- but note the
#: real ledger requires an active `token_products` row to exist for
#: WHATEVER key is used, unlike this module's old auto-vivifying fallback.
_PRODUCT_KEY_BY_CONSUMABLE: dict[str, str] = {
    PREMIUM_AI_CONSUMABLE: "ai_routing_call",
}


def _product_key(consumable_type: str) -> str:
    return _PRODUCT_KEY_BY_CONSUMABLE.get(consumable_type, consumable_type)


def _reason(consumable_type: str, *, source_ref: str | None, actor_user_id: int | None) -> str:
    """Fold `source_ref`/`actor_user_id` into the real ledger's one free-text `reason` column.

    `token_transactions` has no dedicated columns for either -- no info
    dropped, just relocated into `reason`.
    """
    parts = [f"consumable={consumable_type}"]
    if source_ref is not None:
        parts.append(f"source={source_ref}")
    if actor_user_id is not None:
        parts.append(f"actor={actor_user_id}")
    return " ".join(parts)


@dataclass(slots=True, frozen=True)
class DebitResult:
    """Outcome of one `debit_tokens()` call -- always returned, never raises for "insufficient"."""

    success: bool
    balance_after: int
    reason: str | None = None


async def get_balance(
    async_dal: Any, dal: Any, *, community_id: int, consumable_type: str = PREMIUM_AI_CONSUMABLE
) -> int:
    """Real, spendable balance for `consumable_type` -- 0 if the community never credited it."""
    return await token_billing_service.get_balance(
        async_dal, dal, community_id=community_id, product_key=_product_key(consumable_type)
    )


async def _replayed_transaction(
    async_dal: Any, dal: Any, *, community_id: int, ref: str
) -> Any | None:
    """The real ledger's own committed row for a previously-used `ref` (idempotency key), if any.

    Only a SUCCESSFUL credit/debit ever inserts a `token_transactions`
    row (`token_billing_service._guarded_debit_sync`/`_guarded_credit_
    sync`, both migration-076 executor jobs) -- so, same as this module's
    original contract, a previously-BLOCKED attempt's key is free to be
    retried against a since-changed balance rather than being treated as
    a replay.
    """
    rows = await async_dal.select_async(
        dal(
            (dal.token_transactions.community_id == community_id)
            & (dal.token_transactions.ref == ref)
        )
    )
    return rows.first() if rows else None


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
    """Atomically decrement `community_id`'s real `consumable_type` balance by `amount`.

    Delegates to `token_billing_service.debit_tokens()` -- the atomic,
    WHERE-guarded UPDATE against `community_token_balances` (migration
    076) is what actually arbitrates the oversell race; this function
    never duplicates that logic, only translates this module's
    `consumable_type`/`idempotency_key`/`source_ref`/`actor_user_id` shape
    to the real ledger's `product_key`/`ref`/`reason` shape and back.

    Never raises on "can't afford it" (nor on an unknown product, nor on a
    ledger failure -- `token_billing_service`'s own BLOCK-WITH-FALLBACK
    policy already fails closed for all three) -- always returns a
    `DebitResult` so the AI router applies its own block-vs-fallback
    policy, exactly as this module's original contract promised.
    """
    if amount <= 0:
        raise bad_request("debit amount must be positive")

    replayed = await _replayed_transaction(
        async_dal, dal, community_id=community_id, ref=idempotency_key
    )
    if replayed is not None:
        return DebitResult(
            success=True, balance_after=int(replayed.balance_after), reason="replayed"
        )

    result = await token_billing_service.debit_tokens(
        async_dal,
        dal,
        community_id=community_id,
        product_key=_product_key(consumable_type),
        amount=amount,
        reason=_reason(consumable_type, source_ref=source_ref, actor_user_id=actor_user_id),
        ref=idempotency_key,
    )
    if result.ok:
        balance_after = result.balance_after if result.balance_after is not None else 0
        return DebitResult(success=True, balance_after=balance_after)

    current = await get_balance(
        async_dal, dal, community_id=community_id, consumable_type=consumable_type
    )
    return DebitResult(success=False, balance_after=current, reason=result.blocked_reason)


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
    """Credit (grant/purchase/refund) `amount` real tokens -- the debit path's mirror image.

    Delegates to `token_billing_service.credit_tokens()`; used today by
    superadmin manual grants and by tests seeding a balance for the
    block-with-fallback path. Idempotent the same way `debit_tokens()`
    is. Raises :class:`ApiError` (404) if `consumable_type` has no
    matching active `token_products` catalog row (migration 078 seeds
    `"ai_routing_call"`) -- unlike this module's old auto-vivifying
    fallback, the real ledger's catalog is managed explicitly
    (`blueprints/v1/token_billing.py`), so crediting an undefined product
    is a caller error, not a silent no-op.
    """
    if amount <= 0:
        raise bad_request("credit amount must be positive")

    replayed = await _replayed_transaction(
        async_dal, dal, community_id=community_id, ref=idempotency_key
    )
    if replayed is not None:
        return DebitResult(
            success=True, balance_after=int(replayed.balance_after), reason="replayed"
        )

    result = await token_billing_service.credit_tokens(
        async_dal,
        dal,
        community_id=community_id,
        product_key=_product_key(consumable_type),
        amount=amount,
        reason=_reason(consumable_type, source_ref=source_ref, actor_user_id=actor_user_id),
        ref=idempotency_key,
    )
    balance_after = result.balance_after if result.balance_after is not None else 0
    return DebitResult(success=True, balance_after=balance_after)
