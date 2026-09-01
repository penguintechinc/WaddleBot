-- Migration 074: ACTION stage-runner dispatch audit log.
-- Per docs/plans/2026-08-31-app-bundle-sdk-design.md's stage-runner model (Sec6):
-- svc-action (core/svc_action) dequeues process->action queue items and dispatches
-- them to a bundle's declared `action_target` (webhook/rest_api/message_queue/
-- overlay/email, core/svc_action/services/adapters/). This table is the audit
-- trail for every dispatch attempt -- security.md's "log masked, never raw PII"
-- and this task's "never log secrets/tokens/full bodies" apply: `detail` is a
-- short human-readable status string only, never the request/response body or
-- resolved secret.
--
-- Encryption at rest: engine-level (PostgreSQL volume/TDE per security.md
-- Encryption -- Storage baseline). No column-level action needed here.
--
-- svc-action's DB account (DB_USER=svc-action-ro, core/svc_action/config.py)
-- is READ-ONLY today -- provisioning an INSERT/UPDATE grant for this table via
-- the `provision_module_db_account` stored procedure (034_module_db_accounts.sql)
-- is explicit follow-up work, matching every other stage-runner scaffold's
-- (svc_streaming, svc_presentation) current state of "DB access not yet wired
-- into the account-provisioning system." Documented here rather than silently
-- assumed -- this migration only creates the table.

CREATE TABLE IF NOT EXISTS action_dispatch_log (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       INTEGER NOT NULL REFERENCES tenants(id),
    community_id    INTEGER REFERENCES communities(id) ON DELETE CASCADE,  -- NULL = tenant-wide
    app_id          TEXT NOT NULL,                      -- waddles.<module>.<feature>.<app>
    target_type     TEXT NOT NULL,                       -- webhook | rest_api | message_queue | overlay | email
    status          TEXT NOT NULL,                       -- success | retryable_failure | non_retryable_failure
    attempt         INTEGER NOT NULL DEFAULT 1,
    http_status     INTEGER,                              -- NULL for non-HTTP adapters (message_queue)
    detail          TEXT NOT NULL DEFAULT '',              -- short status string only -- never body/secret
    envelope_ts     TIMESTAMPTZ,                            -- the envelope's own `ts` field
    dispatched_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_action_dispatch_log_tenant_app
    ON action_dispatch_log (tenant_id, app_id, dispatched_at DESC);

CREATE INDEX IF NOT EXISTS idx_action_dispatch_log_status
    ON action_dispatch_log (status, dispatched_at DESC);
