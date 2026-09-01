"""pydal table bindings for the M1 Core Identity/Auth group.

Schema is owned by `config/postgres/migrations/*.sql`, never by this
process (`backend-database.md`: "NO automatic Alembic migrations on
startup"; `app.py::_bind_reference_tables` already documents this for
`tenants`). `bind_auth_tables()` exists only so pydal has table/field
objects to build queries against -- every `define_table()` call below
passes `migrate=False` in production (see `bind_auth_tables()`'s own
docstring for the test-only exception).

Column provenance (so the next reader doesn't have to re-derive it):
`config/postgres/migrations/000_create_base_schema.sql` (hub_users,
hub_sessions, hub_temp_passwords, hub_user_identities, hub_oauth_states,
hub_user_profiles), `049_add_auth_settings.sql` (user_passkeys),
`058_tenants_and_claims.sql` (tenant_admins, tenants), `060_analytics_
consumer_role.sql` (hub_users.is_analytics_consumer). `communities`/
`community_members` are 000's own tables, bound here only for the
narrow slice `auth_service.add_user_to_global_community()` and
`get_current_user()`'s communities-list need.

Two known pre-existing gaps surfaced while porting the Node source
faithfully (not introduced by this port -- see `hub_api/PORTING.md`):
  1. `hub_users.email_verification_expires` is referenced by
     `authController.js` register()/verifyEmail()/resendVerification()
     but is defined only in `config/postgres/init.sql` (a separate,
     drifted bootstrap script), not in the numbered migrations that
     actually run in every real environment. Bound here to keep the
     Python port byte-faithful to Node; querying it will 500 exactly
     like Node does today if the column is truly absent. Needs a
     migration to reconcile -- out of scope for a "no schema changes"
     port PR.
  2. `hub_oauth_states` has no `metadata` column, but Node's
     `startOAuth()` INSERTs one (to stash `tenantSlug` for the login
     flow) -- also a pre-existing runtime error in Node today. This
     port omits the metadata insert and resolves login-flow OAuth
     against `DEFAULT_TENANT_SLUG` only (see `oauth_service.py`),
     which matches this app's actual default-tenant-only OAuth-login
     reality rather than porting a call that would 500.
  3. `platform_configs.enabled` (queried by `authController.js`'s
     `getTenantLoginInfo()`) is likewise undefined by any numbered
     migration -- bound here for the same byte-faithful-to-Node reason
     as gaps (1)/(2).
  4. `communities.license_key`/`license_expires_at`/`license_tier`
     (queried by `workflowController.js::validateLicense()`) are not
     defined by ANY numbered migration either (verified: `grep -rl
     license_key config/postgres/migrations/` -> no hits) -- same gap
     class as (1)-(3), added by the M-automation port group (see
     `hub_api/blueprints/v1/workflow.py`). `communities` can only be
     `define_table()`-d once per DAL instance (pydal), so these fields
     extend THIS SAME call rather than a second, competing definition
     -- the established pattern (see `app.py::_bind_reference_tables`'s
     own docstring re: `tenants`).
  5. `support_tickets`/`support_ticket_comments` (queried by
     `githubSyncService.js::syncTicketToGithub()`/
     `processInboundIssueComment()`) do not exist in ANY numbered
     migration at all -- apparently owned by a not-yet-ported Support
     module. Bound in `bind_github_sync_tables()` below anyway, byte-
     faithful to Node: a query against them will 500 exactly like
     Node's own code does against the real schema today. See
     `hub_api/blueprints/v1/github_sync.py`.

`community_roles` (`058_tenants_and_claims.sql`) and the
`community_members.community_role_id` FK the same migration adds are
bound here too (`community_members`' own `define_table()` call gets the
extra field; `community_roles` is new, in `bind_community_authz_tables()`
below) -- both needed by `services/community_authz.py`'s faithful port
of `middleware/auth.js::requireCommunityAdmin()`, shared by the
workflow and github_sync port groups (both Node route files gate every
endpoint with `requireCommunityAdmin`).
"""

from __future__ import annotations

from typing import Any

from pydal import Field


def bind_auth_tables(dal: Any, *, migrate: bool = False) -> None:
    """Define every table the M1 auth/identity/passkey/profile/user-management group queries.

    Idempotent per-DAL-instance -- a second call on the same `dal` is a
    no-op (guards against double-binding if `app.py` startup and a test
    fixture both call this against the same instance).

    `migrate=False` (the default) matches production: schema owned by
    `config/postgres/migrations/*.sql`, this process never runs DDL. Tests
    against a throwaway sqlite file (`tests/conftest.py::auth_db`) pass
    `migrate=True` so pydal actually creates the tables -- there is no
    separate migration step for a test-only database.
    """
    if "hub_users" in dal.tables:
        return

    dal.define_table(
        "hub_users",
        Field("display_name", "string", length=255),
        Field("username", "string", length=255),
        Field("email", "string", length=255),
        Field("password_hash", "string", length=255),
        Field("avatar_url", "text"),
        Field("is_super_admin", "boolean", default=False),
        Field("is_vendor", "boolean", default=False),
        Field("is_analytics_consumer", "boolean", default=False),
        Field("email_verified", "boolean", default=False),
        Field("email_verification_token", "string", length=255),
        Field("email_verification_expires", "datetime"),  # see module docstring gap (1)
        Field("password_reset_token", "string", length=255),
        Field("password_reset_expires", "datetime"),
        Field("last_login", "datetime"),
        Field("created_at", "datetime"),
        Field("updated_at", "datetime"),
        Field("is_active", "boolean", default=True),
        migrate=migrate,
    )

    dal.define_table(
        "hub_sessions",
        Field("session_token", "text", notnull=True),
        Field("user_id", "integer"),
        Field("platform", "string", length=50),
        Field("platform_user_id", "string", length=255),
        Field("platform_username", "string", length=255),
        Field("avatar_url", "text"),
        Field("is_active", "boolean", default=True),
        Field("expires_at", "datetime"),
        Field("revoked_at", "datetime"),
        Field("created_at", "datetime"),
        migrate=migrate,
    )

    dal.define_table(
        "hub_user_identities",
        Field("hub_user_id", "integer", notnull=True),
        Field("platform", "string", length=50, notnull=True),
        Field("platform_user_id", "string", length=255, notnull=True),
        Field("platform_username", "string", length=255),
        Field("avatar_url", "text"),
        Field("is_primary", "boolean", default=False),
        Field("linked_at", "datetime"),
        Field("last_used", "datetime"),
        migrate=migrate,
    )

    dal.define_table(
        "hub_oauth_states",
        Field("state", "string", length=255, notnull=True, unique=True),
        Field("mode", "string", length=50, default="login"),
        Field("platform", "string", length=50, notnull=True),
        Field("user_id", "integer"),
        Field("redirect_uri", "text"),
        Field("expires_at", "datetime", notnull=True),
        Field("created_at", "datetime"),
        migrate=migrate,
    )

    dal.define_table(
        "hub_temp_passwords",
        Field("user_identifier", "string", length=255, notnull=True),
        Field("password_hash", "string", length=255, notnull=True),
        Field("community_id", "integer"),
        Field("force_oauth_link", "boolean", default=False),
        Field("linked_oauth_platform", "string", length=50),
        Field("linked_oauth_user_id", "string", length=255),
        Field("is_used", "boolean", default=False),
        Field("used_at", "datetime"),
        Field("expires_at", "datetime", notnull=True),
        Field("created_at", "datetime"),
        migrate=migrate,
    )

    dal.define_table(
        "hub_user_profiles",
        Field("hub_user_id", "integer", notnull=True, unique=True),
        Field("display_name", "string", length=255),
        Field("bio", "text"),
        Field("location", "string", length=255),
        Field("location_city", "string", length=100),
        Field("location_state", "string", length=100),
        Field("location_country", "string", length=2),
        Field("website_url", "string", length=500),
        Field("custom_avatar_url", "text"),
        Field("banner_url", "text"),
        Field("visibility", "string", length=50, default="public"),
        Field("show_activity", "boolean", default=True),
        Field("show_communities", "boolean", default=True),
        Field("updated_at", "datetime"),
        migrate=migrate,
    )

    dal.define_table(
        "user_passkeys",
        Field("user_id", "integer", notnull=True),
        Field("credential_id", "text", notnull=True, unique=True),
        Field("public_key", "text", notnull=True),
        Field("sign_count", "integer", default=0),
        Field("device_name", "string", length=100),
        Field("created_at", "datetime"),
        Field("last_used_at", "datetime"),
        migrate=migrate,
    )

    dal.define_table(
        "tenant_admins",
        Field("tenant_id", "integer", notnull=True),
        Field("user_id", "integer", notnull=True),
        Field("role", "string", length=50, default="tenant-admin"),
        Field("created_at", "datetime"),
        migrate=migrate,
    )

    dal.define_table(
        "communities",
        Field("name", "string", length=255),
        Field("display_name", "string", length=255),
        Field("is_global", "boolean", default=False),
        Field("is_active", "boolean", default=True),
        Field("member_count", "integer", default=0),
        Field("config", "json"),
        # license_key/license_expires_at/license_tier: added by the
        # M-automation port group -- see module docstring gap (4).
        Field("license_key", "string", length=255),
        Field("license_expires_at", "datetime"),
        Field("license_tier", "string", length=50),
        migrate=migrate,
    )

    dal.define_table(
        "community_members",
        Field("community_id", "integer"),
        # VARCHAR in Postgres (legacy platform-identity membership model),
        # not a FK to hub_users.id -- bound as string and callers pass
        # str(user_id), matching how Node's pg driver serializes it.
        Field("user_id", "string", length=255),
        Field("role", "string", length=50, default="member"),
        Field("is_active", "boolean", default=True),
        Field("joined_at", "datetime"),
        # community_role_id: `058_tenants_and_claims.sql` FK to
        # community_roles(id) -- added by the M-automation port group for
        # `services/community_authz.py`'s requireCommunityAdmin port (see
        # module docstring). Nullable: pre-058 rows / legacy VARCHAR-role
        # members never got backfilled a role_id in every environment.
        Field("community_role_id", "integer"),
        migrate=migrate,
    )

    dal.define_table(
        "platform_configs",
        Field("tenant_id", "integer"),
        Field("platform", "string", length=50),
        Field("config_key", "string", length=100),
        Field("config_value", "text"),
        Field("is_encrypted", "boolean", default=False),
        # `enabled` is queried by authController.js's getTenantLoginInfo()
        # (`WHERE tenant_id = ... AND enabled = true`) but -- like gaps (1)
        # and (2) above -- is not defined by any numbered migration. Bound
        # here to stay byte-faithful to Node; a query against it will 500
        # exactly like Node's would against the real, gapped schema.
        Field("enabled", "boolean", default=False),
        migrate=migrate,
    )

    # hub_settings is schema-owned by the Platform-admin group (M3's
    # platformConfigController.js), not this group -- bound here anyway
    # because auth_service.register()/resend_verification() read it
    # (signup_enabled/email_configured/captcha_* flags). Table BINDING for
    # query purposes tracks "who queries it", not "who owns the schema" --
    # the M3 group extends this same definition if/when it needs to write
    # to it, rather than redefining the table a second time.
    dal.define_table(
        "hub_settings",
        Field("setting_key", "string", length=100, notnull=True),
        Field("setting_value", "text"),
        migrate=migrate,
    )


def bind_community_authz_tables(dal: Any, *, migrate: bool = False) -> None:
    """Define `community_roles` (`058_tenants_and_claims.sql`) for `services/community_authz.py`.

    `app.py` is frozen for this port (`hub_api/PORTING.md`'s per-group
    isolation note during the parallel M-phase port wave -- editing it
    would conflict with every other group's own worktree/PR) -- unlike
    `bind_auth_tables()`, which app.py's own `_bind_reference_tables()`
    calls unconditionally at startup, this is called LAZILY (idempotent,
    cheap: a `dal.define_table()` with no real DDL when `migrate=False`)
    from `community_authz.require_community_admin()` on first use rather
    than at app startup. Safe: `dal` is a single long-lived pydal
    instance for the app's lifetime, and every caller goes through this
    same idempotency guard before ever touching `dal.community_roles`.
    """
    if "community_roles" in dal.tables:
        return

    dal.define_table(
        "community_roles",
        Field("community_id", "integer", notnull=True),
        Field("name", "string", length=50, notnull=True),
        Field("display_name", "string", length=100),
        Field("description", "text"),
        Field("is_system", "boolean", default=False),
        Field("priority", "integer", default=0),
        # base_claims: JSONB `{"scopes": [...]}"` -- see requireCommunityAdmin's
        # `claims.scopes` read in middleware/auth.js.
        Field("base_claims", "json"),
        Field("created_at", "datetime"),
        Field("updated_at", "datetime"),
        migrate=migrate,
    )


def bind_github_sync_tables(dal: Any, *, migrate: bool = False) -> None:
    """Define the tables `githubSyncService.js` owns/queries -- M-automation port group.

    `github_repo_connections`/`ticket_github_sync`/`github_sync_log` are
    real, migrated tables (`066_github_sync.sql`) -- fields bound below
    match that migration's columns exactly. `support_tickets`/
    `support_ticket_comments` are NOT (module docstring gap (5)) -- bound
    anyway to stay byte-faithful to Node; a query against them 500s
    exactly like Node's own code does against the real, gapped schema.

    Lazy/idempotent, same rationale as `bind_community_authz_tables()`
    above (app.py is frozen for this port).
    """
    if "github_repo_connections" in dal.tables:
        return

    dal.define_table(
        "github_repo_connections",
        Field("community_id", "integer"),
        Field("vendor_id", "integer"),
        Field("module_id", "integer"),
        Field("repo_owner", "string", length=255, notnull=True),
        Field("repo_name", "string", length=255, notnull=True),
        Field("sync_mode", "string", length=30, default="tickets_only"),
        Field("default_labels", "list:string"),
        Field("auto_close_on_github_close", "boolean", default=True),
        Field("auth_type", "string", length=20, notnull=True),
        Field("encrypted_token", "text", notnull=True),
        Field("webhook_secret", "string", length=255, notnull=True),
        Field("installation_id", "string", length=255),
        Field("is_active", "boolean", default=True),
        Field("created_at", "datetime"),
        Field("updated_at", "datetime"),
        migrate=migrate,
    )

    dal.define_table(
        "ticket_github_sync",
        Field("ticket_id", "integer", notnull=True),
        Field("github_repo_connection_id", "integer", notnull=True),
        Field("github_issue_number", "integer", notnull=True),
        Field("github_issue_node_id", "string", length=255),
        Field("sync_status", "string", length=30, default="synced"),
        Field("last_synced_at", "datetime"),
        Field("last_error", "text"),
        Field("retry_count", "integer", default=0),
        Field("created_at", "datetime"),
        migrate=migrate,
    )

    dal.define_table(
        "github_sync_log",
        Field("ticket_github_sync_id", "integer"),
        Field("direction", "string", length=10, notnull=True),
        Field("event_type", "string", length=50, notnull=True),
        Field("payload", "json"),
        Field("success", "boolean", notnull=True),
        Field("error_message", "text"),
        Field("created_at", "datetime"),
        migrate=migrate,
    )

    # --- gap (5): not in any numbered migration, bound byte-faithful to Node ---
    dal.define_table(
        "support_tickets",
        Field("subject", "string", length=255),
        Field("description", "text"),
        Field("status", "string", length=50),
        Field("priority", "string", length=50),
        Field("created_at", "datetime"),
        migrate=migrate,
    )

    dal.define_table(
        "support_ticket_comments",
        Field("ticket_id", "integer", notnull=True),
        Field("content", "text"),
        Field("author_name", "string", length=255),
        Field("is_internal", "boolean", default=False),
        Field("source", "string", length=50),
        Field("created_at", "datetime"),
        migrate=migrate,
    )
