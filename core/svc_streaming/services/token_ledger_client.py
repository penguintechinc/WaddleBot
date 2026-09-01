"""Real HTTP client against hub-api's already-shipped token ledger.

TRANSCODE admission (design spec §5: "checks entitlement before starting a
job") debits `Config.transcode_token_cost` tokens of `Config.
transcode_product_key` via hub-api's real, already-implemented `POST
/api/v1/marketplace/communities/<id>/tokens/debit` endpoint
(`hub_api/blueprints/v1/token_billing.py`, backed by `hub_api/services/
token_billing_service.py`'s atomic WHERE-guarded-UPDATE ledger) -- this
service holds NO ledger DB grant of its own (single-writer, per that
module's own docstring), so an HTTP call is the only way tokens are ever
decremented, matching the original scaffold's `TOKEN_CONSUME_URL` intent.

Auth model: this call PASSES THROUGH the caller's own bearer JWT (the
same token that authenticated the `POST .../start` request to svc-
streaming) rather than minting a separate service-to-service credential.
hub-api's `tokens/debit` route already authorizes via `services.
community_authz.authorize_community(..., admin=False)` -- "an active
community member spending their own community's tokens on a premium
feature", exactly the shape of a member starting their own community's
TRANSCODE-enabled forward. A dedicated internal service-identity credential
(SPIFFE mTLS / machine JWT, `security.md` Service-to-Service Auth) for a
background/unattended metering path is real follow-up work once such a
path exists (e.g. per-minute re-metering of an already-running job); it is
not needed for this synchronous, caller-initiated admission check.

BLOCK-WITH-FALLBACK: `debit_transcoding_tokens()` never raises for a
business-as-usual "can't afford it" outcome -- returns a `TokenDebitResult`
the caller (`services/streaming_service.py::start_forwarding`) branches on
to fall back to passthrough (no transcode) rather than blocking stream
start entirely, per this PR's task description.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 5.0

#: Stable, caller-facing vocabulary for why a debit didn't happen --
#: mirrors `hub_api/services/token_billing_service.py`'s own `REASON_*`
#: constants so a 402 from hub-api and a local network failure collapse
#: into the same shape for `start_forwarding()`'s fallback branch.
REASON_INSUFFICIENT_BALANCE = "insufficient_balance"
REASON_LEDGER_UNAVAILABLE = "ledger_unavailable"


@dataclass(slots=True, frozen=True)
class TokenDebitResult:
    """Outcome of one transcode-admission debit attempt against hub-api's ledger."""

    ok: bool
    balance_after: int | None
    blocked_reason: str | None


async def debit_transcoding_tokens(
    hub_api_url: str,
    *,
    bearer_token: str,
    community_id: int,
    amount: int,
    product_key: str,
    ref: str,
) -> TokenDebitResult:
    """POST a real debit to hub-api's token ledger; never raises for a blocked/unreachable outcome.

    `ref` should uniquely identify the admission attempt (e.g.
    `f"stream:{config_id}:{session_started_at}"`) -- hub-api's ledger
    itself isn't idempotency-keyed on `ref` today (that's `credit_tokens`/
    `debit_tokens`'s `ref` audit field, not an idempotency key), so a
    genuine retry after a network timeout can double-debit; callers should
    treat a `start_forwarding` retry as a new admission attempt, matching
    this module's own real behavior rather than a hidden guarantee it
    doesn't provide.
    """
    url = f"{hub_api_url}/api/v1/marketplace/communities/{community_id}/tokens/debit"
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            response = await client.post(
                url,
                headers={"Authorization": f"Bearer {bearer_token}"},
                json={
                    "product_key": product_key,
                    "amount": amount,
                    "reason": "svc_streaming_transcode_admission",
                    "ref": ref,
                },
            )
    except httpx.HTTPError as exc:
        logger.error("token_ledger_client.unreachable community_id=%s error=%s", community_id, exc)
        return TokenDebitResult(
            ok=False, balance_after=None, blocked_reason=REASON_LEDGER_UNAVAILABLE
        )

    if response.status_code == 200:
        body = response.json()
        return TokenDebitResult(
            ok=True, balance_after=int(body["balance_after"]), blocked_reason=None
        )

    if response.status_code == 402:
        return TokenDebitResult(
            ok=False, balance_after=None, blocked_reason=REASON_INSUFFICIENT_BALANCE
        )

    logger.error(
        "token_ledger_client.unexpected_status community_id=%s status=%s",
        community_id,
        response.status_code,
    )
    return TokenDebitResult(ok=False, balance_after=None, blocked_reason=REASON_LEDGER_UNAVAILABLE)
