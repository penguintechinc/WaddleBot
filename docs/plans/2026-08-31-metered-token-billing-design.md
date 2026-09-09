# Metered-Consumable Token Billing — Design Spec

**Date:** 2026-08-31
**Status:** Design (DESIGN DOC ONLY — no implementation). Feeds program plan **P6** (`docs/plans/2026-08-31-v3-sccebm-program-plan.md:357`), owed spec row at `:377`.
**Scope:** ONE metered-billing mechanism serving TWO+ consumables — **transcoding/encoding tokens** (svc-streaming, program-plan §4.3) and **premium-AI tokens** (§6). Extensible to future consumables. A **third** billing axis beyond the license per-node / per-seat axes (`.PLAN:352-356`).

## Sources this grounds against

| Source | What it gives | Cite |
|---|---|---|
| Marketplace payment machinery (Node, → Python P2) | stripe/paypal checkout, refunds, webhooks; billing tables keyed by `community_id`; **cents** money | `admin/marketplace_module/backend/src/services/{stripeService,paypalService,paymentService,premiumService}.js`, `config/postgres/migrations/017_add_marketplace.sql` |
| License-server metering | per-node/per-seat via generic `entitlement_usage`; checkin/validate API; **no** token/credit primitive | `license-server:api/app/models.py:243-296`, `license-server:api/app/routes/api.py:382-540` |
| Entitlement two-gate client (product side) | `feature_enabled(flag, *, tenant, community, default)`; license validate/tier | `libs/flask_core/flask_core/feature_flags.py:37`, `entitlement.py:249`, `core/video_proxy_module/services/license_service.py:65` |
| PAT/CAT "token" (naming collision) | existing `token` = auth tokens, NOT billing | `admin/hub_module/backend/src/controllers/tokenController.js:1-5` |

> **Naming collision (must resolve in impl):** "token" already means PAT/CAT auth tokens (`tokenController.js`). This axis is a **billing consumable** — name the domain **`consumable`** / **`credit`** in code (`token_products`, `community_token_balances`, `token_transactions` tables are fine; API paths use `/tokens` under marketplace to match user-facing "buy tokens" language, distinct from auth `/token`).

---

## 1. Model — the third (per-consumable) axis

Three **independent** metering axes, enforced separately:

| Axis | Meters | Home today | Overage posture |
|---|---|---|---|
| per-**node** | compute instances enrolled | license-server `entitlement_usage["nodes"]` | **burst freely, never block** (`critical-rules` — blocking infra = outage) |
| per-**seat** | customer identities | license-server `entitlement_usage["users"]` + marketplace per-seat premium | **block new seat creation** (deliberate action) |
| per-**consumable-token** (NEW) | prepaid units spent per paid action (transcode, premium-AI inference) | **product marketplace ledger** (this spec) | **block at admission** (deliberate paid action; §4) |

Principles:
- **Global admin (platform owner) sets per-token PRICES** per consumable type/unit. Prices are platform-global, not per-community.
- A **community holds a BALANCE per consumable**; a usage event **decrements** it atomically.
- **Orthogonal to license tier** — even a Free-tier community buys/consumes tokens (this IS the monetization). A consumable's *availability* is still behind its Feature flag + tier gate (`feature_enabled`), but *purchase/spend* is tier-independent.
- **Consumable types are extensible** (`transcoding`, `premium_ai`, later e.g. `bulk_email`, `sms`) — a row in `token_products`, no schema change.
- **One mechanism, both consumables** — svc-streaming and the AI premium path call the same `consume()`.

---

## 2. Ledger schema

Three tables. **PostgreSQL**, defined as SQLAlchemy models + **Alembic** migration (head `alembic/versions/0004`) in the **hub-api marketplace module** (P2 Node→Python port). Money = integer **cents** (matches `marketplace_payments.amount_cents`, `017:122`). `community_id` = INTEGER FK `communities(id)` — consistent with every existing `marketplace_*` table (`017:87,116`); community is a tenancy/OU entity, **not PII**. The only PII-adjacent column is `actor_user_uuid` → **UUID reference to the single identity table only** (`backend-database` PII tokenization) — never user PII in the ledger.

### 2.1 `token_products` — global pricing catalog (one row per consumable)

| Column | Type | Notes |
|---|---|---|
| `id` | serial PK | |
| `consumable_type` | varchar UNIQUE | `'transcoding'`, `'premium_ai'`, … (extensible) |
| `display_name`, `description` | varchar/text | |
| `unit` | varchar | what one token buys — e.g. `'transcode-minute'`, `'1k-ai-tokens'` |
| `unit_price_cents` | int | **price per token — set by global admin** |
| `currency` | varchar(10) DEFAULT `'USD'` | matches `017:123` |
| `min_purchase_tokens`, `purchase_increment` | int | purchase constraints |
| `free_allotment_tokens` | int DEFAULT 0 | recurring free grant (e.g. free premium-AI trial) |
| `free_allotment_period` | varchar DEFAULT `'monthly'` | reset cadence; **non-rolling** |
| `enforcement_policy` | varchar | `'block'` \| `'block_admission_allow_inflight'` \| `'allow_overage'` (§4) |
| `expiry_days` | int NULL | promo/free-grant expiry only; NULL = paid balance never expires (§4.3) |
| `is_active` | bool | |
| `created_at`, `updated_at` | timestamptz | |

### 2.2 `community_token_balances` — per-community, per-consumable gauge

| Column | Type | Notes |
|---|---|---|
| `id` | serial PK | |
| `community_id` | int FK `communities(id)` | |
| `consumable_type` | varchar FK `token_products` | |
| `balance_tokens` | bigint DEFAULT 0 | spendable balance; decremented under row-lock |
| `free_allotment_remaining` | bigint | resets per `free_allotment_period` |
| `free_allotment_reset_at` | timestamptz | |
| `lifetime_purchased`, `lifetime_consumed` | bigint | audit rollups |
| `auto_refill_enabled` | bool | §5.3 |
| `auto_refill_threshold_tokens`, `auto_refill_amount_tokens` | bigint | |
| `payment_method_ref` | varchar NULL | provider payment-method / customer id for off-session refill (**new — Node never persisted this, §5.3**) |
| `last_activity_at` | timestamptz | reporting/staleness (§4.3) |
| — | | **UNIQUE(`community_id`,`consumable_type`)** |

`balance_tokens` is a **materialized gauge** for O(1) locked decrement; it is fully **reconcilable** from `token_transactions` (`SUM(amount_tokens)`), which is the source of truth.

### 2.3 `token_transactions` — append-only ledger (source of truth; idempotent; auditable)

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `community_id` | int FK | |
| `consumable_type` | varchar | |
| `txn_type` | varchar CHECK | `'purchase'`\|`'consume'`\|`'refund'`\|`'adjust'`\|`'free_grant'`\|`'expire'` |
| `amount_tokens` | bigint | **signed**: + purchase/refund/grant, − consume/expire |
| `balance_after` | bigint | running snapshot (audit) |
| `idempotency_key` | varchar **UNIQUE** | dedup — purchase = provider event id; consume = caller source-event id (§8-5) |
| `unit_price_cents` | int NULL | **price snapshot** at purchase (prices change over time) |
| `amount_cents` | int NULL | money moved (purchase/refund); NULL for consume/grant |
| `payment_id` | int FK `marketplace_payments(id)` | links purchase → payment record (`017:113`) |
| `discount_code_id` | int NULL | reuse vendor discount (§3, open §8-10) |
| `actor_user_uuid` | UUID NULL | **PII-tokenized** initiator ref |
| `source_service` | varchar | `'svc-streaming'`\|`'ai'`\|`'hub-api'` |
| `source_ref` | varchar NULL | transcode-job / AI-request id (reconciliation, not PII) |
| `metadata` | jsonb | |
| `created_at` | timestamptz | immutable |

**Per-service DB accounts** (`backend.md` Database Tier): **only the hub-api marketplace account holds read-write** on these three tables. svc-streaming / AI hold **no ledger grant** — they call `consume()` (§6). Ledger writes are single-owner, keeping decrement atomic and centrally enforced.

---

## 3. Pricing config (global admin)

- **Global admin sets `unit_price_cents` per consumable** via `token_products` (superadmin scope) — `POST/PUT /api/v2/platform/token-products` (§7). Platform-global, not per-community.
- **Currency:** integer cents, default `'USD'` (matches existing convention). Multi-currency / tax = open (§8-3).
- **Discounts:** reuse `vendor_discount_codes` (`config/postgres/migrations/064_vendor_discount_codes.sql:5` — `percentage`\|`fixed_amount`\|`free`), applied to the cents charged at purchase, recorded in `discount_code_redemptions` (`064:39`). Note: today's discount codes are **seller-scoped**; a **platform-level** token discount may need a new scope (open §8-10). (Also flag the pre-existing `discountCodeService.js` table-name drift bug — it queries `marketplace_discount_codes`, migration creates `vendor_discount_codes` — fix during the Python port, not this axis.)
- **Free allotments:** `free_allotment_tokens` grants N free tokens/period, reset non-rolling into `community_token_balances.free_allotment_remaining`. **Premium-AI "free" ≠ free tokens:** the **free local model** (`llama3.1:1b`) is **unmetered — bypasses the ledger entirely**; only the **premium-local** and metered paths decrement `premium_ai` (program-plan §6). A free monthly premium-AI allotment is an optional goodwill grant on top (open §8-6).

---

## 4. Consumption + enforcement

### 4.1 Atomic decrement (authoritative, in hub-api marketplace)

```
consume(community_id, consumable_type, amount, idempotency_key, source_ref, actor):
  BEGIN
   row = SELECT * FROM community_token_balances
         WHERE community_id, consumable_type FOR UPDATE          -- row lock
   if EXISTS token_transactions WHERE idempotency_key            -- replay-safe
        -> COMMIT; return prior decision                         -- idempotent
   spend_free = min(amount, row.free_allotment_remaining)
   spend_bal  = amount - spend_free
   if spend_bal > row.balance_tokens and policy == block*:
        -> ROLLBACK; return INSUFFICIENT(need, purchase_url)     -- 402
   INSERT token_transactions(consume, -amount, balance_after, idempotency_key, source_ref, actor)
   UPDATE community_token_balances
        SET balance -= spend_bal, free_allotment_remaining -= spend_free,
            lifetime_consumed += amount, last_activity_at = now()
  COMMIT
  (async) report aggregate to license-server checkin (§6)
```

Contrast license-server's `entitlement_usage`: an **overwrite gauge** (`SET current_usage = value`, `license-server:api/app/routes/api.py:462`), **not** a decrementing ledger — genuine spend/top-up semantics do **not** exist there (confirmed absent) and are built fresh here.

### 4.2 Enforcement policy — **block, per consumable** (recommendation)

Unlike the license per-**node** rule (*never block, true-up later* — blocking infra causes outages), a consumable is a **discrete, community-initiated paid action** with a **self-serve purchase path** — closer to the per-**seat** *block-new-creation* rule. Recommend **block**, tuned per consumable:

| Consumable | Recommend | Rationale |
|---|---|---|
| **premium_ai** | **BLOCK** on insufficient balance | Deliberate paid action. **Never a hard failure** — the model router **falls back to the free local model** (program-plan §6), so "blocked" = graceful downgrade, not error. Clear purchase/upgrade path returned. |
| **transcoding** | **BLOCK at job admission; allow bounded in-flight completion** | Don't *start* a transcode you can't pay for. Never interrupt a running transcode mid-stream (corrupts output) — let an admitted job finish into a small bounded overage (`block_admission_allow_inflight`), then block the next. Bound size = open §8-2. |

`allow_overage` (negative balance, commercial true-up) is available per `token_products.enforcement_policy` but **not recommended** for either launch consumable.

### 4.3 Staleness / expiry

- **Prepaid paid balances DO NOT expire by default** — prepaid credit is an accounting liability and consumer-protection concern (contrast license 30-day *node reclamation*, which is only a reporting heuristic anyway — `license-server:portal.py:517`). `last_activity_at` is tracked for **reporting only**.
- **Optional expiry** via `token_products.expiry_days` applies **only to promo / free-grant tokens** (`free_grant` txns), realized as an `expire` txn. Free allotments simply reset non-rolling each period.
- Jurisdiction-dependent (some regions prohibit expiring prepaid) → open §8-7.

---

## 5. Purchase / refill flow (reuse marketplace payments)

### 5.1 Buy tokens

```
POST /api/v2/marketplace/tokens/purchase {consumable_type, quantity_tokens, provider, discount_code?}
  amount_cents = quantity_tokens * token_products.unit_price_cents  (− discount)
  -> stripeService/paypalService.createCheckoutSession  (Python port of admin/marketplace_module)
  -> return checkout_url                                            (no ledger credit yet)
```

### 5.2 Fulfillment (webhook — the critical fix)

The provider webhook credits tokens. **The existing Node webhook handlers are stubs** — `stripeService.handleCheckoutCompleted` ends at `// TODO: Store in database, fulfill order` (`admin/marketplace_module/backend/src/services/stripeService.js:287`); `orderService.js` is entirely commented-out example code; **nothing ever writes `marketplace_payments`** (dead table). The Python port **MUST** implement idempotent fulfillment:

```
POST /api/v2/webhooks/{stripe|paypal}   (verify signature: stripeService.js:184)
  event = verified
  idempotency_key = event.id                                       -- dedup replays
  BEGIN
    INSERT marketplace_payments(status='succeeded', amount_cents, external_payment_id, provider)
    INSERT token_transactions(purchase, +quantity, idempotency_key=event.id, payment_id, unit_price_cents)
    UPDATE community_token_balances(balance += quantity, lifetime_purchased += quantity)
  COMMIT
```

`token_transactions.idempotency_key` UNIQUE on `event.id` makes replayed webhooks safe (closes the current no-dedup gap — `stripeService.js:203-254` has no `event.id` guard).

### 5.3 Receipts & auto-refill

- **Receipts:** `GET /api/v2/marketplace/tokens/transactions` — ledger history; a receipt = `purchase` txn joined to its `marketplace_payments` row.
- **Auto-refill:** when a `consume` drops `balance < auto_refill_threshold` and `auto_refill_enabled`, charge the stored `payment_method_ref` **off-session** (Stripe customer/off-session, mirrors `marketplace_subscriptions` recurring machinery `017:93-104`) for `auto_refill_amount_tokens`, then credit via the §5.2 path. **Requires persisting a customer/payment-method ref** — the Node code creates Stripe customers (`paymentController.js:387`) but **never stores the id** (no `stripe_customer_id` column anywhere); `community_token_balances.payment_method_ref` is the new home.

---

## 6. Integration points + ledger-location recommendation

```
 svc-streaming (transcode) ─┐                         ┌─ PRIMARY DB (marketplace acct RW)
                            ├─ consume() ── hub-api ───┤   token_products / balances / transactions
 AI premium path (router) ─┘   (svc→svc JWT,  marketplace │
                                SPIFFE-ready)  module  │
                                                       └─(async) report aggregate ──▶ license-server
                                                          entitlement_usage["*_tokens_consumed"]
                                                          (3rd axis, reporting/true-up only)
```

| Point | Behavior |
|---|---|
| **svc-streaming** (program-plan §4.3) | Transcode/encode path calls `consume('transcoding', units, job_id)` at **job admission**; block-admission on insufficient. Holds **no ledger DB grant** — internal `POST /internal/tokens/consume`. |
| **AI premium** (program-plan §6) | Model router: free-local (unmetered) → premium-local `consume('premium_ai', ntokens, req_id)` → BYOK. Ties to `model_access_policy` + the separate **premium-AI-routing spec** (program-plan §377-378). BYOK metering = open §8-8. |
| **hub-api marketplace module** | **Owns** the ledger + all purchase/consume/balance/pricing endpoints (P2 port makes hub-api real, P6 wires billing). Single writer. |
| **license-server** | **Reporting axis only** (see recommendation). |

### Recommendation — ledger lives in the **product marketplace (hub-api)**, NOT license-server

| Criterion | Marketplace (hub-api) | license-server |
|---|---|---|
| Payment machinery (stripe/paypal, checkout, refund, webhook) | **present** (being ported P2) | **absent** |
| Decrement/top-up/refund ledger semantics | build new (small) | build new (its `entitlement_usage` is an **overwrite gauge**, wrong shape) |
| Per-community wallet keying | **native** — every `marketplace_*` table is `community_id`-keyed | no community/wallet concept |
| PII/UUID identity for actor | product identity table exists | **no PII/UUID pattern** (`license-server:models.py:131` customer = plain string) |
| Consumption hot path | **in-cluster, local** decrement | per-transcode sync cross-service call = latency + coupling |

**Decision (recommend): the balance/ledger + enforcement live in the marketplace module inside hub-api.** license-server keeps the **third axis as a reporting gauge** — the marketplace periodically reports aggregate consumed/purchased via the existing checkin path (`entitlement_name = 'transcoding_tokens_consumed'` / `'premium_ai_tokens_consumed'`, `license-server:api/app/routes/api.py:452-525`), so node/seat/consumable all surface in one place for analytics + commercial true-up — **without** putting the hot decrement or the payment integration there. **Flagged as open §8-1** (a valid alternative is a license-server "wallet" service for cross-product token portability; rejected for launch on the five criteria above).

---

## 7. API

`/api/v2` (bundle API major, program-plan §7); tenant/community from **JWT claim, never path**; OpenAPI 3.x generated (`quart-schema`), two-document split (public login-only + full behind JWT, `backend.md`). All responses schema-validated DTOs (`security.md` Output Validation).

| Surface | Method / Path | Scope | Notes |
|---|---|---|---|
| Community | `GET /api/v2/marketplace/tokens/balances` | community JWT | all consumable balances |
| Community | `GET /api/v2/marketplace/tokens/balances/{consumable_type}` | community | single |
| Community | `POST /api/v2/marketplace/tokens/purchase` | community | start checkout (§5.1) |
| Community | `GET /api/v2/marketplace/tokens/transactions` | community | history/receipts; **filterable** (type, consumable, date range, pagination — `testing.md` filter coverage) |
| Community | `PUT /api/v2/marketplace/tokens/auto-refill/{consumable_type}` | community | configure (§5.3) |
| Internal | `POST /internal/tokens/consume` | **service JWT** (SPIFFE-ready) | authoritative decrement (§4.1) |
| Internal | `POST /internal/tokens/precheck` | service JWT | cheap cached balance check (short-TTL) |
| Webhook | `POST /api/v2/webhooks/{stripe\|paypal}` | signature-verified | idempotent fulfillment (§5.2) |
| Admin | `GET/POST/PUT /api/v2/platform/token-products` | **superadmin** | global pricing CRUD (§3) |
| Admin | `POST /api/v2/platform/tokens/adjust` | superadmin | manual grant/clawback → `adjust` txn (audited) |
| Admin | `GET /api/v2/platform/tokens/usage` | superadmin | platform-wide consumption reporting |

**Auth:** tenant middleware → `require_scope` → `feature_enabled` (program-plan gating chain). Consume path = short-lived signed service JWT regardless of transport (`security.md` Service-to-Service). The **billing capability itself** sits behind its consumable's PostHog flag (e.g. `waddles.streaming.transcode`, `waddles.<module>.premium_ai`), defaulted OFF.

---

## 8. Open decisions

| # | Decision | Recommendation / note |
|---|---|---|
| 1 | **Ledger location** — marketplace vs license-server | **Marketplace (hub-api)**; license-server = reporting axis only (§6). Alt: cross-product license-server wallet — rejected for launch. |
| 2 | **Enforcement per consumable** | premium_ai = **block** (→ free-local fallback); transcoding = **block-admission, allow bounded in-flight**. Confirm the in-flight overage bound. |
| 3 | **Currency / tax** | USD cents only today. Multi-currency + VAT/sales-tax (Stripe Tax?) on token purchases — undecided. |
| 4 | **Refund policy** | Refund **unconsumed** tokens only (debit balance to zero floor + provider refund); deny/prorate if already consumed; admin clawback via `adjust`. Confirm. |
| 5 | **Idempotency key strategy** | purchase = provider `event.id`; consume = caller `source_ref` (transcode-job / AI-request id). Confirm uniqueness scope (global UNIQUE vs per-community). |
| 6 | **Free-allotment modeling** | free premium-AI = **free local model (unmetered)**; optional monthly free premium-token grant on top? Confirm which is "free-tier AI free". |
| 7 | **Balance expiry / staleness** | Paid balances **do not expire**; optional expiry for promo/free grants only. Jurisdiction-dependent — confirm. |
| 8 | **BYOK metering** | Does BYOK consume platform tokens (service fee) or bypass the ledger (community pays provider directly)? Ties to premium-AI-routing spec. |
| 9 | **Consume DB ownership** | **hub-api marketplace account only** writes the ledger; stage-runners call `/internal/tokens/consume` (no direct grant). Confirm. |
| 10 | **Discount scope** | Reuse seller-scoped `vendor_discount_codes` vs new platform-level token discount. (Also: fix pre-existing `discountCodeService` table-name drift during port.) |
| 11 | **Payment fulfillment gap (dependency, not a fork)** | Node webhook handlers are stubs (`stripeService.js:287`) — the Python port **must** implement idempotent webhook→ledger credit + persist a customer/payment-method ref (for auto-refill). Prerequisite for this axis. |
