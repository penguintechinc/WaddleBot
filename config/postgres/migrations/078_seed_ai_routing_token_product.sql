-- Migration 078: Seed the "ai_routing_call" token_products catalog row
-- (migration 076's community_token_balances/token_transactions ledger) so
-- premium-AI metering has an active product to debit against out of the
-- box. hub_api/services/token_ledger.py delegates its debit_tokens()/
-- credit_tokens()/get_balance() calls to hub_api/services/
-- token_billing_service.py against this exact product key --
-- token_billing_service.py's own debit_tokens() docstring already names
-- "ai_routing_call" as the example premium-AI product key this seed
-- fulfills.
--
-- price_cents/tokens_granted are catalog/purchase-UI display fields only
-- -- token_billing_service.py's credit_tokens()/debit_tokens() always take
-- an explicit `amount`, never a multiple of tokens_granted -- placeholder
-- values here pending a real commercial packaging decision; balances are
-- topped up via the admin credit endpoint (hub_api/blueprints/v1/
-- token_billing.py) independent of these two fields.

INSERT INTO token_products (key, name, unit, price_cents, tokens_granted, active)
VALUES ('ai_routing_call', 'AI Routing Call (Premium)', 'token', 0, 1, TRUE)
ON CONFLICT (key) DO NOTHING;
