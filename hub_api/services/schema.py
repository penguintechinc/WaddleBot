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
  4. `communities.about_extended`/`social_links`/`website_url`/
     `discord_invite_url`/`visibility` -- see the `communities`
     `define_table()` call's own inline comment for detail. Added by
     the M2 Core Tenancy-Misc group.
  5. `communities.license_key`/`license_expires_at`/`license_tier`
     (queried by `workflowController.js::validateLicense()`) are not
     defined by ANY numbered migration either (verified: `grep -rl
     license_key config/postgres/migrations/` -> no hits) -- same gap
     class as (1)-(3), added by the M-automation port group (see
     `hub_api/blueprints/v1/workflow.py`). `communities` can only be
     `define_table()`-d once per DAL instance (pydal), so these fields
     extend THIS SAME call rather than a second, competing definition
     -- the established pattern (see `app.py::_bind_reference_tables`'s
     own docstring re: `tenants`).
  6. `support_tickets`/`support_ticket_comments` (queried by
     `githubSyncService.js::syncTicketToGithub()`/
     `processInboundIssueComment()`) do not exist in ANY numbered
     migration at all -- apparently owned by a not-yet-ported Support
     module. Bound in `bind_github_sync_tables()` below anyway, byte-
     faithful to Node: a query against them will 500 exactly like
     Node's own code does against the real schema today. See
     `hub_api/blueprints/v1/github_sync.py`.

M2 (Core Tenancy-Misc: `communityProfileController.js` +
`joinRequestController.js`) extends this function's existing
`communities`/`community_members` calls with the additional columns
those two controllers need, and adds `community_roles`/
`community_join_requests` -- per this file's own precedent (`app.py`'s
`tenants` table) of extending the ONE existing `define_table()` call
rather than redefining a table a second time elsewhere. `bind_auth_tables()`
is still the sole call site (`app.py::_bind_reference_tables()`), so no
`app.py` edit is needed for a group that only needs more columns on an
already-bound table.

`community_roles` (`058_tenants_and_claims.sql`, already bound by the M2
group above) and the `community_members.community_role_id` FK the same
migration adds are also relied on by `services/community_authz.py`'s
faithful port of `middleware/auth.js::requireCommunityAdmin()`, shared by
the workflow and github_sync port groups (both Node route files gate
every endpoint with `requireCommunityAdmin`); `bind_community_authz_tables()`
below is this group's own idempotent-binding entry point mirroring that
module's own lazy-bind call pattern.
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
        "hub_oauth_exchange_codes",
        # `config/postgres/migrations/075_oauth_exchange_codes.sql` -- backs the
        # exchange-code handoff fix for the JWT-in-URL leak in
        # `blueprints/v1/auth.py::oauth_callback` (see that route's docstring
        # and `hub_api/PORTING.md` Gotcha #8). Single-use is enforced by an
        # atomic `UPDATE ... WHERE used = FALSE AND expires_at > NOW()` claim
        # in `oauth_service.redeem_oauth_exchange_code` -- the database, not
        # application logic, arbitrates a concurrent-redemption race (same
        # pattern as `community_welcomed_users`, migration 068).
        Field("code", "string", length=255, notnull=True, unique=True),
        Field("token", "text", notnull=True),
        Field("platform", "string", length=50),
        Field("used", "boolean", default=False),
        Field("used_at", "datetime"),
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
        # Added by the Analytics-module port (M9): this table can only be
        # `define_table()`-d once per DAL instance, and `create_app()`
        # binds this M1 definition (via `_bind_reference_tables`) before
        # any request runs -- `services/community_common.py::
        # ensure_community_tables()`'s own idempotent guard then silently
        # skips its (separately-defined) `tenant_id` column, so
        # `community_in_tenant()` would `AttributeError` in production
        # against a real app (pre-existing gap, only masked because every
        # Community-module blueprint's own tests build an isolated app +
        # dal that never loads `bind_auth_tables` at all). Extending here
        # -- not redefining -- per this module's own docstring guidance for
        # `tenants` columns, generalized to `communities`: the real
        # Postgres column already exists (058_tenants_and_claims.sql),
        # this just maps pydal onto it.
        Field("tenant_id", "integer"),
        Field("is_global", "boolean", default=False),
        Field("is_active", "boolean", default=True),
        Field("member_count", "integer", default=0),
        Field("config", "json"),
        # license_key/license_expires_at/license_tier: added by the
        # M-automation port group -- see module docstring gap (5).
        Field("license_key", "string", length=255),
        Field("license_expires_at", "datetime"),
        Field("license_tier", "string", length=50),
        # Columns below added by the M3 Platform-admin group (adminController.js
        # /superadminController.js), the M2 Core Tenancy-Misc group
        # (communityProfileController.js / joinRequestController.js port),
        # and the M3 Platform-admin/Public group (platformController.js/
        # publicController.js -- see `hub_api/PORTING.md`) -- `communities`
        # is bound once, here, by M1; every column any later group needs
        # joins this same Field list rather than a second define_table()
        # call (pydal allows exactly one per table name per DAL instance).
        # `tenant_id`, `description`, `platform`, `owner_id`, `join_mode`,
        # `is_public`, `deleted_at` match 000_create_base_schema.sql +
        # 058_tenants_and_claims.sql's `ALTER TABLE communities ADD COLUMN
        # tenant_id` verbatim. `tenant_id` is NOT NULL in Postgres -- every
        # public/platform-admin query that lists communities MUST filter on
        # this (security.md Tenant Isolation); see services/public_service.
        # py's module docstring for the pre-auth resolution mechanism. Also
        # relied on by the M7 Streaming (music/stream/streaming) group AND
        # the M7 Streaming (overlay/calls) group: `flask_core.tenancy.
        # tenant_scoped()`'s community_id-owning-table fallback path reads
        # `dal.communities.tenant_id` directly -- no group before M7 queried
        # a community_id-owning table through that helper, so this was the
        # first caller to actually need the column bound (not just present
        # in Postgres). `services/community_access.py` (overlay/calls) is
        # the second `tenant_scoped()` caller with the identical need.
        # `about_extended`, `social_links`, `website_url`,
        # `discord_invite_url`, `visibility` are a pre-existing schema gap:
        # `communityProfileController.js`'s own raw SQL reads/writes these
        # exact column names on `communities`, but no numbered migration
        # ever adds them (`social_links` migration 037 adds a same-named
        # column to `community_members`, a DIFFERENT table -- not this
        # one). Bound here anyway to stay byte-faithful to Node: a query
        # touching these columns 500s against real Postgres exactly like
        # Node's own controller does today. Needs a migration to
        # reconcile -- out of scope for a "no schema changes" port PR.
        # `logo_url`/`banner_url`/`primary_platform` are genuine columns
        # platformController.js/publicController.js read, same
        # 000_create_base_schema.sql origin as the rest of this list.
        Field("tenant_id", "integer"),
        Field("description", "text"),
        Field("about_extended", "text"),  # gap -- see docstring above
        Field("social_links", "json"),  # gap -- see docstring above
        Field("website_url", "string", length=500),  # gap -- see docstring above
        Field("discord_invite_url", "string", length=500),  # gap -- see docstring above
        Field("visibility", "string", length=30, default="public"),  # gap -- see docstring above
        Field("logo_url", "text"),
        Field("banner_url", "text"),
        Field("primary_platform", "string", length=50),
        Field("platform", "string", length=50, default="discord"),
        Field("platform_server_id", "string", length=255),
        # VARCHAR in Postgres, not a hub_users.id FK -- see community_members.user_id below.
        Field("owner_id", "string", length=255),
        Field("owner_name", "string", length=255),
        Field("community_type", "string", length=50, default="creator"),
        Field("join_mode", "string", length=50, default="open"),
        Field("is_public", "boolean", default=True),
        Field("is_premium", "boolean", default=False),
        Field("seat_limit", "integer"),
        Field("created_by", "string", length=255),
        Field("created_at", "datetime"),
        Field("updated_at", "datetime"),
        Field("deleted_at", "datetime"),
        Field("deleted_by", "string", length=255),
        migrate=migrate,
    )

    dal.define_table(
        "community_members",
        Field("community_id", "integer"),
        # VARCHAR in Postgres (legacy platform-identity membership model),
        # not a FK to hub_users.id -- bound as string and callers pass
        # str(user_id), matching how Node's pg driver serializes it.
        Field("user_id", "string", length=255),
        # platform/platform_user_id/display_name/reputation added by the M3
        # group (platformController.js's getUsers/getUser/getStats) -- all
        # real columns in 000_create_base_schema.sql.
        Field("platform", "string", length=50),
        Field("platform_user_id", "string", length=255),
        Field("display_name", "string", length=255),
        Field("reputation", "integer", default=600),
        Field("role", "string", length=50, default="member"),
        Field("is_active", "boolean", default=True),
        Field("joined_at", "datetime"),
        # Gap (4): platformController.js's getUsers()/getUser()/getStats()
        # all reference `community_members.last_activity`/`created_at`, but
        # no numbered migration (nor init.sql) ever adds either -- only an
        # unrelated `analytics_suspected_bots.last_activity_at` exists. Same
        # class of pre-existing gap as (1)/(2)/(3): bound here to stay
        # byte-faithful to Node; a real query against either 500s exactly
        # like Node's does today. Needs a migration to reconcile -- out of
        # scope here.
        Field("last_activity", "datetime"),
        Field("created_at", "datetime"),
        # Columns below added by the M3 Platform-admin group -- same
        # single-define_table() rationale as `communities` above.
        # `claims_cache` matches 000_create_base_schema.sql /
        # 058_tenants_and_claims.sql exactly (`reputation` is already bound
        # above by the M3 Platform-admin/Public group -- same column, not
        # duplicated). `community_role_id` is the same FK to
        # community_roles.id (`058_tenants_and_claims.sql`'s "1f. Update
        # community_members" ALTER) the M2 Core Tenancy-Misc group's, the
        # M-automation group's, and the M7 Streaming group's own
        # `services/community_authz.py` (`_scoped` variant) all rely on
        # for their per-community admin checks -- bound once here, not
        # duplicated. `claims_cache` is the same faithful-port source the
        # M7 group's `resolve_community_membership_scoped()` parses for
        # the caller's community-scoped OIDC scopes.
        # `removed_at`/`removed_by`/`removal_reason` are a pre-existing
        # schema gap (adminController.js's removeMember() references them,
        # but no migration defines them -- same class of gap as
        # hub_users.email_verification_expires above; bound here to stay
        # byte-faithful to Node, which 500s against real Postgres today for
        # the exact same reason).
        Field("community_role_id", "integer"),
        Field("claims_cache", "json"),
        Field("removed_at", "datetime"),
        Field("removed_by", "integer"),
        Field("removal_reason", "text"),
        Field("updated_at", "datetime"),
        migrate=migrate,
    )

    dal.define_table(
        "community_roles",
        # Schema: `058_tenants_and_claims.sql`'s "1e. Community roles
        # table". Added by the M2 group -- `services/community_authz.py`
        # resolves a caller's granted scopes for one community via this
        # table (`base_claims.scopes`), the same DB-backed check Node's
        # `middleware/auth.js::requireCommunityAdmin`/`requireMember` do.
        Field("community_id", "integer", notnull=True),
        Field("name", "string", length=50, notnull=True),
        Field("display_name", "string", length=100),
        Field("priority", "integer", default=0),
        Field("base_claims", "json"),
        migrate=migrate,
    )

    dal.define_table(
        "community_join_requests",
        # Schema: `049_add_auth_settings.sql`. Added by the M2 group
        # (joinRequestController.js port). Unlike `community_members.
        # user_id` (legacy VARCHAR), `user_id` here is a real INTEGER FK
        # to `hub_users.id` -- matches Node's own INSERT/SELECT, which
        # pass `req.user.userId` (an int) directly, never `str(...)`.
        Field("community_id", "integer", notnull=True),
        Field("user_id", "integer", notnull=True),
        Field("status", "string", length=20, default="pending"),
        Field("message", "text"),
        Field("reviewed_by", "integer"),
        Field("reviewed_at", "datetime"),
        Field("created_at", "datetime"),
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


def bind_support_token_tables(dal: Any, *, migrate: bool = False) -> None:
    """Define every table the Support-ticket + PAT/CAT-token port group queries.

    Idempotent per-DAL-instance, same contract as `bind_auth_tables()` above.
    Not wired into `app.py::_bind_reference_tables()` -- `app.py`/`routers/*.py`/
    `blueprints/__init__.py` are frozen for the parallel port wave (see
    `services/community_common.py::ensure_community_tables()`'s own docstring
    for why). Callers (`services/support_service.py`, `services/
    access_token_service.py`) call this idempotently at the top of every
    service function instead, matching that same established pattern.

    Does NOT bind `communities`/`hub_users` -- those are owned by
    `bind_auth_tables()`/`ensure_community_tables()`; callers needing tenant
    isolation (`community_in_tenant()`) must ensure one of those has already
    run against the same `dal` (matches `services/community_*.py`'s own
    established convention of calling `ensure_community_tables(dal)` first).

    Column provenance: `support_ticket_categories`/`support_tickets`/
    `support_ticket_comments` are created at Node runtime startup
    (`admin/hub_module/backend/src/index.js`'s `initializeDatabase()`), not
    by any numbered SQL migration -- ported here verbatim from that CREATE
    TABLE block. `user_access_tokens`/`community_access_tokens` come from
    `config/postgres/migrations/048_add_pat_cat_tables.sql`.

    One more pre-existing gap, same category as `hub_api/PORTING.md`'s
    Gotcha #4: `048_add_pat_cat_tables.sql` never creates a `permission_scopes`
    table with `scope_key`/`display_name` columns -- the only migration that
    creates `permission_scopes` at all (`011_add_scoped_tokens.sql`) defines
    `scope_name` (not `scope_key`) and has no `display_name` column, yet
    `tokenController.js`'s `createCAT()`/`listScopes()` query exactly
    `scope_key`/`display_name` from it. This is a pre-existing runtime gap in
    Node's own code today (its query would already fail against the real,
    migrated schema), not introduced by this port. Bound here byte-faithful
    to Node's query, not silently renamed to the migration's real column --
    needs a migration to reconcile (`ALTER TABLE permission_scopes RENAME
    COLUMN scope_name TO scope_key`, `ADD COLUMN display_name`), out of scope
    for a "no schema changes" port PR.
    """
    if "support_ticket_categories" not in dal.tables:
        dal.define_table(
            "support_ticket_categories",
            Field("community_id", "integer", notnull=True),
            Field("name", "string", length=255, notnull=True),
            Field("description", "text"),
            Field("sort_order", "integer", default=0),
            Field("is_active", "boolean", default=True),
            Field("form_fields", "json"),
            Field("created_at", "datetime"),
            migrate=migrate,
        )

    if "support_tickets" not in dal.tables:
        dal.define_table(
            "support_tickets",
            Field("community_id", "integer", notnull=True),
            Field("category_id", "integer"),
            Field("ticket_number", "string", length=20, notnull=True),
            Field("subject", "string", length=500, notnull=True),
            Field("description", "text"),
            Field("status", "string", length=20, default="open"),
            Field("priority", "string", length=20, default="medium"),
            Field("reporter_user_id", "integer"),
            Field("reporter_name", "string", length=255),
            Field("reporter_email", "string", length=255),
            Field("assignee_user_id", "integer"),
            Field("custom_fields", "json"),
            Field("resolved_at", "datetime"),
            Field("created_at", "datetime"),
            Field("updated_at", "datetime"),
            migrate=migrate,
        )

    if "support_ticket_comments" not in dal.tables:
        dal.define_table(
            "support_ticket_comments",
            Field("ticket_id", "integer", notnull=True),
            Field("author_user_id", "integer"),
            Field("author_name", "string", length=255),
            Field("content", "text", notnull=True),
            Field("is_internal", "boolean", default=False),
            Field("created_at", "datetime"),
            migrate=migrate,
        )

    if "user_access_tokens" not in dal.tables:
        dal.define_table(
            "user_access_tokens",
            Field("user_id", "integer", notnull=True, unique=True),
            Field("name", "string", length=100, notnull=True),
            # SHA-256 hex of the plaintext token; plaintext is never stored.
            Field("token_hash", "string", length=64, notnull=True, unique=True),
            # NULL = inherit the user's full permissions; pydal has no native
            # Postgres TEXT[] type -- "list:string" round-trips a Python list
            # portably across Postgres/MySQL/sqlite (pydal's own abstraction).
            Field("scope_ceiling", "list:string"),
            Field("created_at", "datetime"),
            Field("last_used_at", "datetime"),
            Field("expires_at", "datetime"),
            Field("is_revoked", "boolean", notnull=True, default=False),
            migrate=migrate,
        )

    if "community_access_tokens" not in dal.tables:
        dal.define_table(
            "community_access_tokens",
            Field("community_id", "integer", notnull=True),
            Field("created_by_user_id", "integer"),
            Field("name", "string", length=100, notnull=True),
            Field("token_hash", "string", length=64, notnull=True, unique=True),
            Field("scopes", "list:string", notnull=True),
            Field("created_at", "datetime"),
            Field("last_used_at", "datetime"),
            Field("expires_at", "datetime"),
            Field("is_revoked", "boolean", notnull=True, default=False),
            migrate=migrate,
        )

    if "permission_scopes" not in dal.tables:
        dal.define_table(
            "permission_scopes",
            # See this function's own docstring -- `scope_key`/`display_name`
            # match Node's query, not `011_add_scoped_tokens.sql`'s real
            # `scope_name` column (pre-existing schema-drift gap).
            Field("scope_key", "string", length=100, notnull=True, unique=True),
            Field("display_name", "string", length=255),
            Field("description", "text"),
            Field("category", "string", length=50),
            migrate=migrate,
        )


def bind_overlay_tables(dal: Any, *, migrate: bool = False) -> None:
    """Define the M7 Streaming (overlay/calls) group's own tables.

    Named `bind_overlay_tables` (not `bind_streaming_tables`) even though
    this group is also nominally M7 Streaming -- the M7 music/stream/
    streaming controller group (a separate, parallel port task) already
    landed its own `bind_streaming_tables()` above for a disjoint table
    set (`community_music_settings`, `coordination`, `community_servers`,
    etc.); this group's own tables (`community_overlay_tokens`,
    `overlay_access_log`) are unrelated, so this function keeps its own
    name rather than colliding on identical text with incompatible bodies
    (the same class of same-name-different-function collision
    `services/community_authz.py`'s own `_scoped` suffix already
    documents for the M-automation/M7-music groups).

    Column provenance: `config/postgres/migrations/000_create_base_schema.sql`
    ("community_overlay_tokens", "overlay_access_log").

    Deliberately NOT wired into `app.py::_bind_reference_tables()` the way
    `bind_auth_tables()` is -- this port's task scope explicitly forbids
    editing `app.py`/`routers/*.py`/`blueprints/__init__.py` (the
    collision-avoidance boundary for the parallel M1..M9 port wave, see
    `hub_api/PORTING.md`'s own "single new module" extension point).
    `services/overlay_service.py` calls this idempotently (matching the
    `if "<table>" in dal.tables: return` guard below) at the top of every
    entry point instead of relying on app startup -- safe under Quart's
    single-threaded-per-request-coroutine model since `define_table()`
    itself awaits nothing, so no two coroutines can interleave mid-call.
    A future group that gets an `app.py` edit in scope should fold this
    into `_bind_reference_tables()` the normal way and delete this note.
    """
    if "community_overlay_tokens" in dal.tables:
        return

    dal.define_table(
        "community_overlay_tokens",
        Field("community_id", "integer", notnull=True, unique=True),
        Field("overlay_key", "string", length=64, notnull=True, unique=True),
        Field("previous_key", "string", length=64),
        Field("is_active", "boolean", default=True),
        Field("theme_config", "json"),
        Field("enabled_sources", "json"),
        Field("last_accessed", "datetime"),
        Field("access_count", "integer", default=0),
        Field("created_at", "datetime"),
        Field("updated_at", "datetime"),
        Field("rotated_at", "datetime"),
        migrate=migrate,
    )

    dal.define_table(
        "overlay_access_log",
        Field("community_id", "integer", notnull=True),
        Field("overlay_key", "string", length=64),
        Field("ip_address", "string", length=45),
        Field("user_agent", "text"),
        Field("accessed_at", "datetime"),
        migrate=migrate,
    )


def bind_streaming_tables(dal: Any, *, migrate: bool = False) -> None:
    """Define every table the M7 Streaming group (music/stream/streaming) queries.

    Idempotent per-DAL-instance, `migrate=False` in production -- same
    contract as `bind_auth_tables()` above (see its own docstring and
    `hub_api/PORTING.md`'s Gotcha #2). Unlike M1, this function is never
    called from `app.py::_bind_reference_tables()` -- the M7 port's own
    scope explicitly forbids editing `app.py`/`routers/*.py`/
    `blueprints/__init__.py` (auto-discovery is the only wiring point for
    blueprints; table binding has no equivalent auto-discovery hook yet).
    Each M7 service module calls this itself, guarded by pydal's own
    `if "<table>" in dal.tables: return`-per-`define_table()` idempotency
    (`DAL.define_table()` no-ops on a name that's already bound against
    this `dal` instance) -- safe to call on every request; the real cost
    is paid exactly once per process.

    `community_roles` (migration 058_tenants_and_claims.sql) is relied on
    by `services.community_authz`'s community-scoped-role join
    (`middleware/auth.js`'s `requireMember`/`requireCommunityAdmin`,
    byte-faithfully ported: LEFT JOIN `community_members.community_role_id
    -> community_roles.id`, parse `claims_cache`/`base_claims` for the
    caller's scopes) but is NOT bound here -- `bind_auth_tables()` above
    (extended by the M2 Core Tenancy-Misc group) already binds it
    unconditionally at app startup, before this function's own lazy first
    call could ever run. `coordination` (also bound by `bind_platform_tables()`,
    identical field list either way) and `community_servers` (also bound
    by `bind_admin_tables()`, whose field list is a strict superset of the
    4 fields this group's own `stream_service.py` reads) are each
    individually guarded below rather than redefined, so whichever group's
    binding runs first in this shared, long-lived `dal` instance wins
    without error -- this function deliberately mirrors `bind_admin_tables()`'s
    fuller `community_servers` field list (not just this group's own
    narrower 4) so a streaming route hit before any admin route never
    leaves `community_servers` bound too narrowly for `bind_admin_tables()`
    to use later.

    This function's own top-level idempotency guard therefore checks
    `community_music_settings` (a table genuinely unique to this group),
    not `coordination`/`community_roles`/any other table another group
    also binds -- checking a shared table would short-circuit this
    function's own tables as a false-positive "already done" the moment
    that other group's binding landed first (caught the hard way during
    the M7-onto-release merge: this function originally guarded on
    `community_roles`, which `bind_auth_tables()` already binds
    unconditionally at app startup, so the guard skipped every table below
    -- including this function's own -- unconditionally, for every real
    request; `coordination`/`community_music_settings`/etc. never bound at
    all). `coordination`/`community_servers` are likewise real, pre-existing
    tables (`004_add_missing_tables.sql` / `000_create_base_schema.sql`)
    queried read-only by `stream_service.py`.

    Schema gap (`hub_api/PORTING.md` Gotcha #4's pattern, a larger
    instance of it): `musicController.js` queries five tables --
    `community_music_settings`, `community_music_providers`,
    `community_radio_stations`, `oauth_state_tokens`, `oauth_tokens` --
    that exist in NEITHER the numbered migrations NOR
    `config/postgres/init.sql`. `config/postgres/migrations/
    005_add_music_tables.sql` / `012_add_music_providers.sql` define a
    DIFFERENT, non-overlapping music schema (`music_settings`,
    `music_provider_config`, `music_radio_state`, `music_queue`, ...) that
    appears to supersede whatever `musicController.js` was originally
    written against -- and `admin/hub_module/backend/src/routes/music.js`
    (the only place these 8 controller functions are wired to routes) is
    itself never mounted in `routes/index.js`, so this entire code path is
    unreachable dead code in the Node app today, hit by nothing in
    production. Per Gotcha #4's rule ("document it, don't silently invent
    a column, don't silently drop the whole feature either") and the M7
    port's explicit instruction to port the EXISTING controller endpoints
    faithfully: these 5 tables are bound here with the exact columns
    Node's SQL references, `migrate=False` in production (byte-faithful --
    a real deployment 500s on first use exactly like Node's dead code
    would if it were ever wired up), `migrate=True` in tests (so the
    ported logic itself has real characterization coverage against
    sqlite). A follow-up ticket should either (a) write the missing
    migration for this schema, or (b) confirm with product that
    `music.py`'s settings/providers/radio-stations surface should be
    rebuilt against the real `music_provider_config`/`music_radio_state`
    schema instead -- out of scope for a byte-faithful controller port.
    """
    if "community_music_settings" in dal.tables:
        return

    # `coordination` is ALSO bound by `bind_platform_tables()` above (same
    # exact field list -- both groups ported it from the same real
    # `004_add_missing_tables.sql` table independently) and
    # `community_servers` by `bind_admin_tables()` below (a strict
    # superset of the 4 fields this group's own `stream_service.py` reads
    # -- `platform_server_name`/`link_type`/`is_primary`/`config`/
    # `added_by`/`approved_by`/`verified_at`/`created_at` on top of this
    # group's `community_id`/`platform`/`platform_server_id`/`status`).
    # Both guarded on existence here (not redefined) so whichever group's
    # binding runs first in this process wins -- for `coordination` that's
    # inconsequential (identical fields either way); for `community_servers`
    # this function intentionally uses `bind_admin_tables()`'s fuller field
    # list even though this group only reads the narrower 4, so a caller
    # that hits a streaming route before any admin route never ends up
    # with an admin-incompatible narrower table bound first (the exact
    # failure mode this docstring's `coordination`/`community_roles`
    # history above already describes for a same-name guard chosen wrong).
    if "coordination" not in dal.tables:
        dal.define_table(
            "coordination",
            Field("entity_id", "string", length=255, notnull=True),
            Field("platform", "string", length=50, notnull=True),
            Field("server_id", "string", length=255),
            Field("channel_id", "string", length=255),
            Field("channel_name", "string", length=255),
            Field("is_live", "boolean", default=False),
            Field("viewer_count", "integer", default=0),
            Field("live_since", "datetime"),
            Field("stream_title", "text"),
            Field("game_name", "string", length=255),
            Field("thumbnail_url", "text"),
            Field("last_updated", "datetime"),
            migrate=migrate,
        )

    if "community_servers" not in dal.tables:
        dal.define_table(
            "community_servers",
            Field("community_id", "integer", notnull=True),
            Field("platform", "string", length=50, notnull=True),
            Field("platform_server_id", "string", length=255, notnull=True),
            Field("platform_server_name", "string", length=255),
            Field("link_type", "string", length=50, default="standard"),
            Field("status", "string", length=50, default="pending"),
            Field("is_primary", "boolean", default=False),
            Field("config", "json"),
            Field("added_by", "integer"),
            Field("approved_by", "integer"),
            Field("verified_at", "datetime"),
            Field("created_at", "datetime"),
            migrate=migrate,
        )

    # --- Schema-gap tables (see module docstring above) ---------------

    dal.define_table(
        "community_music_settings",
        Field("community_id", "integer", notnull=True, unique=True),
        Field("default_provider", "string", length=50),
        Field("autoplay_enabled", "boolean", default=False),
        Field("volume_limit", "integer", default=100),
        Field("allowed_genres", "json"),
        Field("blocked_artists", "json"),
        Field("require_dj_approval", "boolean", default=False),
        Field("is_active", "boolean", default=True),
        Field("created_at", "datetime"),
        Field("updated_at", "datetime"),
        migrate=migrate,
    )

    dal.define_table(
        "community_music_providers",
        Field("community_id", "integer", notnull=True),
        Field("provider_name", "string", length=50, notnull=True),
        Field("is_connected", "boolean", default=False),
        Field("is_active", "boolean", default=False),
        Field("oauth_expires_at", "datetime"),
        Field("last_sync", "datetime"),
        Field("config", "text"),
        Field("created_at", "datetime"),
        Field("updated_at", "datetime"),
        migrate=migrate,
    )

    dal.define_table(
        "community_radio_stations",
        Field("community_id", "integer", notnull=True),
        Field("name", "string", length=255, notnull=True),
        Field("url", "string", length=2048, notnull=True),
        Field("description", "text"),
        Field("genre", "string", length=100),
        Field("is_active", "boolean", default=True),
        Field("created_by", "integer"),
        Field("created_at", "datetime"),
        Field("updated_at", "datetime"),
        migrate=migrate,
    )

    dal.define_table(
        "oauth_state_tokens",
        Field("community_id", "integer", notnull=True),
        Field("provider", "string", length=50, notnull=True),
        Field("state_token", "string", length=255, notnull=True, unique=True),
        Field("redirect_uri", "text"),
        Field("expires_at", "datetime", notnull=True),
        Field("created_at", "datetime"),
        migrate=migrate,
    )

    dal.define_table(
        "oauth_tokens",
        Field("community_id", "integer", notnull=True),
        Field("provider", "string", length=50, notnull=True),
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


def bind_privacy_tables(dal: Any, *, migrate: bool = False) -> None:
    """Define every table the Privacy/Compliance group (GDPR DSAR + cookie consent) queries.

    Idempotent per-DAL-instance, same guard pattern as `bind_auth_tables()`.
    `migrate=False` (default) matches production -- schema owned by
    `config/postgres/migrations/*.sql`; tests pass `migrate=True`.

    Deliberately NOT called from `app.py::_bind_reference_tables()` --
    this port PR (`blueprints/v1/data_privacy.py` +
    `blueprints/v1/cookie_consent.py`) is scoped to never touch
    `app.py`/`routers/*.py`/`blueprints/__init__.py` (shared files a
    parallel M-phase port wave would collide on). Instead,
    `blueprints/v1/data_privacy.py` and `blueprints/v1/cookie_consent.py`
    each call this from their own `before_request` hook -- a correctness-
    equivalent substitute given the idempotent guard below: the first
    request against either blueprint binds every table in this function,
    every request after that is a no-op check. A future PR that touches
    `app.py` for an unrelated reason should fold this call into
    `_bind_reference_tables()` alongside `bind_auth_tables()` and delete
    the two `before_request` hooks.

    Column provenance: `config/postgres/migrations/000_create_base_schema.sql`
    (cookie_policy_versions, cookie_consent, cookie_audit_log, hub_chat_messages),
    `044_add_activity_tables.sql` (activity_watch_sessions, activity_message_events),
    `062_data_deletion_requests.sql` (data_deletion_requests). Note
    `006_add_cookie_consent.sql` defines an OLDER, incompatible shape for
    the three cookie_* tables (different columns, e.g. `session_id`/
    `consent_timestamp` instead of `consent_id`/`consented_at`) -- it never
    runs in practice because `000_create_base_schema.sql`'s `CREATE TABLE
    IF NOT EXISTS` always applies first (numeric ordering), so the columns
    bound here match `000`'s definition, the one that actually wins in
    every real environment. `hub_users`/`hub_user_profiles`/
    `hub_user_identities`/`hub_sessions`/`user_passkeys` (also read by the
    DSAR export) are already bound by `bind_auth_tables()`, called first
    by every blueprint's `_ensure_tables()` hook.
    """
    if "cookie_consent" in dal.tables:
        return

    dal.define_table(
        "cookie_policy_versions",
        Field("version", "string", length=50, notnull=True, unique=True),
        Field("content", "text", notnull=True),
        Field("changes_summary", "text"),
        Field("is_active", "boolean", default=False),
        Field("effective_date", "datetime"),
        Field("created_by", "integer"),
        Field("created_at", "datetime"),
        migrate=migrate,
    )

    dal.define_table(
        "cookie_consent",
        Field("user_id", "integer"),
        Field("consent_id", "string", length=255, notnull=True, unique=True),
        Field("preferences", "json"),
        Field("consent_version", "string", length=50, notnull=True),
        Field("consent_method", "string", length=50, default="banner"),
        Field("ip_address", "string", length=45),
        Field("user_agent", "text"),
        Field("consented_at", "datetime"),
        Field("updated_at", "datetime"),
        Field("expires_at", "datetime"),
        migrate=migrate,
    )

    dal.define_table(
        "cookie_audit_log",
        Field("consent_id", "string", length=255),
        Field("user_id", "integer"),
        Field("action", "string", length=50, notnull=True),
        Field("category", "string", length=50),
        Field("previous_value", "boolean"),
        Field("new_value", "boolean"),
        Field("consent_version", "string", length=50),
        Field("ip_address", "string", length=45),
        Field("user_agent", "text"),
        Field("created_at", "datetime"),
        migrate=migrate,
    )

    dal.define_table(
        "data_deletion_requests",
        Field("hub_user_id", "integer", notnull=True),
        Field("requested_at", "datetime", notnull=True),
        Field("completed_at", "datetime"),
        Field("status", "string", length=20, default="pending"),
        Field("deletion_scope", "json"),
        Field("error_detail", "text"),
        migrate=migrate,
    )

    # Read by the DSAR export (`data_privacy_service.py::collect_user_data`)
    # only -- schema-owned by the Engagement/Leaderboard group
    # (activityController.js), not this group. Bound here the same way
    # `bind_auth_tables()` binds `hub_settings` for a different group's
    # own reads: table BINDING tracks "who queries it", not "who owns the
    # schema".
    dal.define_table(
        "activity_message_events",
        Field("community_id", "integer", notnull=True),
        Field("hub_user_id", "integer"),
        Field("platform", "string", length=50, notnull=True),
        Field("platform_user_id", "string", length=255, notnull=True),
        Field("platform_username", "string", length=255),
        Field("channel_id", "string", length=255),
        Field("created_at", "datetime"),
        migrate=migrate,
    )

    dal.define_table(
        "activity_watch_sessions",
        Field("community_id", "integer", notnull=True),
        Field("hub_user_id", "integer"),
        Field("platform", "string", length=50, notnull=True),
        Field("platform_user_id", "string", length=255, notnull=True),
        Field("platform_username", "string", length=255),
        Field("channel_id", "string", length=255, notnull=True),
        Field("session_start", "datetime"),
        Field("session_end", "datetime"),
        Field("duration_seconds", "integer", default=0),
        Field("is_active", "boolean", default=True),
        Field("created_at", "datetime"),
        Field("updated_at", "datetime"),
        migrate=migrate,
    )

    # Read by the DSAR export only -- schema-owned by the Tenancy/
    # Community group (communityInteractionController.js et al), same
    # cross-group binding rationale as activity_* above.
    dal.define_table(
        "hub_chat_messages",
        Field("community_id", "integer", notnull=True),
        Field("channel_name", "string", length=255),
        Field("sender_hub_user_id", "integer"),
        Field("sender_platform", "string", length=50),
        Field("sender_username", "string", length=255),
        Field("sender_avatar_url", "text"),
        Field("message_content", "text", notnull=True),
        Field("message_type", "string", length=50, default="text"),
        Field("created_at", "datetime"),
        migrate=migrate,
    )


def bind_platform_tables(dal: Any, *, migrate: bool = False) -> None:
    """Define every table the M3 Platform-admin/Public group queries.

    Calls `bind_auth_tables()` first (dependency: `communities`,
    `community_members`, `hub_settings`, `tenants` all live there, extended
    in place -- see that function's own field-list comments), then defines
    this group's own new tables. Idempotent per-DAL-instance, same guard
    pattern as `bind_auth_tables()`.

    Gap (5): `platformController.js`'s `getUsers()`/`getUser()`/
    `updateUserRole()`/`deactivateUser()` all query a `platform_admins`
    table that does not exist in ANY migration OR `init.sql` -- a step
    beyond gaps (1)-(4) above (those were missing *columns* on real
    tables; this is a missing *table*). Combined with `requirePlatformAdmin`
    checking `req.user.roles.includes('platform-admin')`, a claim
    `createSession()` (authController.js) never actually populates (only
    'admin'/'super_admin'/'vendor' are ever pushed), this makes
    `platformController.js`'s entire route group unreachable AND
    non-functional in Node today: every caller gets 403 (no JWT ever
    carries the role) and, even if that were bypassed, half the queries
    would 500 (table absent). This port's authz fix (see
    `blueprints/v1/platform.py`'s module docstring) grants access via the
    existing `*:admin` global-admin wildcard scope instead of the
    never-populated role string -- restoring the group to reachable AND
    functional, matching the evident product intent (Node's own
    `createSession()` pushes 'admin' for `is_super_admin`, strongly
    suggesting a global admin was always meant to satisfy this check).
    `platform_admins` is bound here (byte-faithful field guesses from the
    controller's own SELECT/INSERT usage) so the group is fully testable;
    real Postgres needs a migration to add the table before this is
    functional in a live environment -- tracked as a follow-up, not
    silently invented schema.

    Gap (6): `getModuleRegistry()` queries a `collector_modules` table,
    likewise absent from every migration and `init.sql`. Same treatment:
    bound here from the controller's own column usage, real-environment
    functionality blocked on a follow-up migration.
    """
    if "platform_admins" in dal.tables:
        return

    bind_auth_tables(dal, migrate=migrate)

    dal.define_table(
        "platform_admins",
        Field("user_id", "integer", notnull=True),
        Field("role", "string", length=50),
        Field("is_active", "boolean", default=True),
        Field("deactivated_at", "datetime"),
        Field("created_at", "datetime"),
        Field("updated_at", "datetime"),
        migrate=migrate,
    )

    dal.define_table(
        "collector_modules",
        Field("module_name", "string", length=255, notnull=True),
        Field("module_version", "string", length=50),
        Field("platform", "string", length=50),
        Field("endpoint_url", "text"),
        Field("status", "string", length=50),
        Field("last_heartbeat", "datetime"),
        Field("created_at", "datetime"),
        migrate=migrate,
    )

    dal.define_table(
        "audit_log",
        Field("user_id", "integer"),
        Field("action", "string", length=100, notnull=True),
        Field("target_type", "string", length=50),
        Field("target_id", "string", length=255),
        Field("details", "json"),
        Field("ip_address", "string", length=45),
        Field("user_agent", "text"),
        Field("created_at", "datetime"),
        migrate=migrate,
    )

    # Also bound by `bind_streaming_tables()` above (identical field list --
    # both groups ported it from the same real `004_add_missing_tables.sql`
    # table independently); guarded on existence here (not redefined) so
    # whichever group's binding runs first in this shared, long-lived `dal`
    # instance wins without a duplicate-define error.
    if "coordination" not in dal.tables:
        dal.define_table(
            "coordination",
            Field("entity_id", "string", length=255, notnull=True),
            Field("platform", "string", length=50, notnull=True),
            Field("server_id", "string", length=255),
            Field("channel_id", "string", length=255),
            Field("channel_name", "string", length=255),
            Field("is_live", "boolean", default=False),
            Field("viewer_count", "integer", default=0),
            Field("live_since", "datetime"),
            Field("stream_title", "text"),
            Field("game_name", "string", length=255),
            Field("thumbnail_url", "text"),
            Field("last_updated", "datetime"),
            migrate=migrate,
        )

    dal.define_table(
        "hub_modules",
        Field("name", "string", length=255, notnull=True),
        Field("display_name", "string", length=255),
        Field("description", "text"),
        Field("version", "string", length=50),
        Field("author", "string", length=255),
        Field("category", "string", length=100),
        Field("icon_url", "text"),
        Field("is_published", "boolean", default=False),
        Field("is_core", "boolean", default=False),
        Field("config_schema", "json"),
        Field("created_at", "datetime"),
        Field("updated_at", "datetime"),
        migrate=migrate,
    )

    dal.define_table(
        "hub_module_reviews",
        Field("module_id", "integer"),
        Field("community_id", "integer"),
        Field("user_id", "integer"),
        Field("rating", "integer"),
        Field("review_text", "text"),
        Field("admin_notes", "text"),
        Field("created_at", "datetime"),
        migrate=migrate,
    )

    dal.define_table(
        "hub_module_installations",
        Field("community_id", "integer", notnull=True),
        Field("module_id", "integer"),
        Field("installed_by", "integer"),
        Field("config", "json"),
        Field("is_enabled", "boolean", default=True),
        Field("installed_at", "datetime"),
        Field("updated_at", "datetime"),
        migrate=migrate,
    )

    dal.define_table(
        "platform_integrations",
        Field("platform", "string", length=50, notnull=True),
        Field("integration_type", "string", length=20, notnull=True),
        Field("community_id", "integer"),
        Field("user_id", "integer"),
        Field("access_token", "text"),
        Field("refresh_token", "text"),
        Field("client_id", "string", length=255),
        Field("client_secret", "text"),
        Field("token_type", "string", length=50, default="Bearer"),
        Field("expires_at", "datetime"),
        Field("scopes", "list:string"),
        Field("config_data", "json"),
        Field("is_active", "boolean", default=True),
        Field("is_encrypted", "boolean", default=True),
        Field("created_at", "datetime"),
        Field("updated_at", "datetime"),
        Field("created_by_user_id", "integer"),
        Field("updated_by_user_id", "integer"),
        migrate=migrate,
    )


def bind_admin_tables(dal: Any, *, migrate: bool = False) -> None:
    """Define every table the M3 Platform-admin group (admin/superadmin) queries.

    `app.py::_bind_reference_tables` is frozen (`routers/_discovery.py`'s
    auto-discovery contract: port agents never edit `app.py`/
    `routers/*.py`/`blueprints/__init__.py`), so -- matching the precedent
    the Community-module port (M6) already established in
    `services/community_common.py::ensure_community_tables` -- this group's
    tables are bound lazily, guarded per-table, from the top of every
    `admin_service`/`superadmin_service` function rather than at app
    startup. Idempotent: a second call on the same `dal` is a cheap no-op
    (`dal.tables` membership check).

    `migrate=False` (production default) matches every other group in this
    file: schema owned by `config/postgres/migrations/*.sql`, this process
    never runs DDL. Tests pass `migrate=True` against a throwaway sqlite
    file the same way `tests/conftest.py::auth_db` does.
    """
    if "hub_modules" not in dal.tables:
        dal.define_table(
            "hub_modules",
            Field("name", "string", length=255, notnull=True, unique=True),
            Field("display_name", "string", length=255),
            Field("description", "text"),
            Field("version", "string", length=50),
            Field("author", "string", length=255),
            Field("category", "string", length=100),
            Field("icon_url", "text"),
            Field("is_published", "boolean", default=False),
            Field("is_core", "boolean", default=False),
            Field("config_schema", "json"),
            Field("created_at", "datetime"),
            Field("updated_at", "datetime"),
            migrate=migrate,
        )

    if "hub_module_installations" not in dal.tables:
        dal.define_table(
            "hub_module_installations",
            Field("community_id", "integer", notnull=True),
            Field("module_id", "integer"),
            Field("installed_by", "integer"),
            Field("config", "json"),
            Field("is_enabled", "boolean", default=True),
            Field("installed_at", "datetime"),
            Field("updated_at", "datetime"),
            # `module_name` is a pre-existing schema gap: adminController.js's
            # getCommands() LEFT JOINs `hmi.module_name = c.module_name`, but
            # no migration defines this column on hub_module_installations
            # (only module_id, an integer FK to hub_modules.id) -- same class
            # of gap as hub_users.email_verification_expires (see this
            # module's top-of-file docstring gap list). Bound here to stay
            # byte-faithful; a real query against it 500s against Postgres
            # today exactly like Node's does.
            Field("module_name", "string", length=255),
            migrate=migrate,
        )

    if "hub_module_reviews" not in dal.tables:
        dal.define_table(
            "hub_module_reviews",
            Field("module_id", "integer"),
            Field("community_id", "integer"),
            Field("user_id", "integer"),
            Field("rating", "integer"),
            Field("review_text", "text"),
            Field("admin_notes", "text"),
            Field("created_at", "datetime"),
            migrate=migrate,
        )

    if "hub_admins" not in dal.tables:
        dal.define_table(
            "hub_admins",
            Field("username", "string", length=255, notnull=True, unique=True),
            Field("password_hash", "string", length=255, notnull=True),
            Field("email", "string", length=255),
            Field("is_active", "boolean", default=True),
            Field("is_super_admin", "boolean", default=False),
            Field("last_login", "datetime"),
            Field("created_at", "datetime"),
            Field("updated_at", "datetime"),
            migrate=migrate,
        )

    # `modules`/`module_installations` (community-level module toggles,
    # 046_add_remaining_admin_tables.sql + 004_add_missing_tables.sql) are a
    # SEPARATE table family from `hub_modules`/`hub_module_installations`
    # (marketplace registry, 000_create_base_schema.sql) above -- not a
    # typo. adminController.js's getModules()/updateModuleConfig() query
    # this family; superadminController.js's marketplace registry queries
    # the `hub_*` family. Both are real, distinct tables in Node's actual
    # schema (confirmed against the migrations directly).
    if "modules" not in dal.tables:
        dal.define_table(
            "modules",
            Field("name", "string", length=100, notnull=True, unique=True),
            Field("display_name", "string", length=255),
            Field("description", "text"),
            Field("category", "string", length=50),
            Field("version", "string", length=20, default="1.0.0"),
            Field("is_active", "boolean", default=True),
            Field("created_at", "datetime"),
            Field("updated_at", "datetime"),
            migrate=migrate,
        )

    if "module_installations" not in dal.tables:
        dal.define_table(
            "module_installations",
            Field("community_id", "integer"),
            # VARCHAR(100) in Postgres -- getModules() joins
            # `modules m ON m.id::text = mi.module_id`, i.e. module_id is
            # the *text* representation of modules.id, not an integer FK.
            Field("module_id", "string", length=100, notnull=True),
            Field("is_enabled", "boolean", default=True),
            Field("config", "json"),
            Field("installed_at", "datetime"),
            Field("installed_by", "integer"),
            migrate=migrate,
        )

    if "community_servers" not in dal.tables:
        dal.define_table(
            "community_servers",
            Field("community_id", "integer", notnull=True),
            Field("platform", "string", length=50, notnull=True),
            Field("platform_server_id", "string", length=255, notnull=True),
            Field("platform_server_name", "string", length=255),
            Field("link_type", "string", length=50, default="standard"),
            Field("status", "string", length=50, default="pending"),
            Field("is_primary", "boolean", default=False),
            Field("config", "json"),
            Field("added_by", "integer"),
            Field("approved_by", "integer"),
            Field("verified_at", "datetime"),
            Field("created_at", "datetime"),
            migrate=migrate,
        )

    if "commands" not in dal.tables:
        dal.define_table(
            "commands",
            Field("command", "string", length=100, notnull=True),
            Field("module_name", "string", length=255, notnull=True),
            Field("description", "text"),
            Field("usage", "text"),
            Field("category", "string", length=100, default="general"),
            Field("permission_level", "string", length=50, default="everyone"),
            Field("cooldown_seconds", "integer", default=0),
            Field("community_id", "integer"),
            Field("is_enabled", "boolean", default=True),
            Field("is_active", "boolean", default=True),
            Field("created_at", "datetime"),
            Field("updated_at", "datetime"),
            # `platforms` is a pre-existing schema gap: adminController.js's
            # getCommands() selects `c.platforms`, but 002_add_commands_table.sql
            # never defines it -- same class of gap as
            # hub_module_installations.module_name above. Bound here to stay
            # byte-faithful.
            Field("platforms", "json"),
            migrate=migrate,
        )

    if "community_roles" not in dal.tables:
        dal.define_table(
            "community_roles",
            Field("community_id", "integer", notnull=True),
            Field("name", "string", length=50, notnull=True),
            Field("display_name", "string", length=100),
            Field("description", "text"),
            Field("is_system", "boolean", default=False),
            Field("priority", "integer", default=0),
            Field("base_claims", "json"),
            Field("created_at", "datetime"),
            Field("updated_at", "datetime"),
            migrate=migrate,
        )


def bind_superadmin_tenant_fields(dal: Any, *, migrate: bool = False) -> None:
    """Redefine `tenants` with the extra columns superadmin tenant CRUD needs.

    `app.py::_bind_reference_tables` (frozen) only binds the subset M1's
    auth chain needs (slug/display_name/logo_url/is_global/is_active/
    config). `superadminController.js`'s tenant management
    (listTenants/createTenant/updateTenant/deleteTenant) additionally
    needs `description`/`allowed_module_ids`/`seat_limit`/`created_at`/
    `updated_at` -- the full column set from
    `058_tenants_and_claims.sql`'s `CREATE TABLE tenants`. pydal forbids a
    second `define_table("tenants", ...)` call unless `redefine=True`,
    which replaces the table's field metadata in place (no DDL --
    `migrate=False` in production, so this never touches the real schema,
    only pydal's own Python-side Table object). Guarded by a field-presence
    check so this only runs once per DAL instance rather than on every
    request.
    """
    if "seat_limit" in dal.tenants.fields:
        return

    dal.define_table(
        "tenants",
        Field("slug", "string", length=100),
        Field("display_name", "string", length=255),
        Field("description", "text"),
        Field("logo_url", "text"),
        Field("is_global", "boolean", default=False),
        Field("is_active", "boolean", default=True),
        Field("config", "json"),
        Field("allowed_module_ids", "list:integer"),
        Field("seat_limit", "integer"),
        Field("created_at", "datetime"),
        Field("updated_at", "datetime"),
        migrate=migrate,
        redefine=True,
    )


def bind_tenant_tables(dal: Any, *, migrate: bool = False) -> None:
    """Extend `tenants`/`communities` + bind new tables for the M2 Core Tenant group.

    This group's task explicitly scopes `app.py`/`routers/*.py`/
    `blueprints/__init__.py` as never-edit (avoids a shared-file collision
    point across the parallel M1..M9 port wave -- the same rationale
    `app.py::_bind_reference_tables`'s own docstring gives for keeping
    that function's diff small). That means this group can't follow
    `hub_api/PORTING.md`'s literal "extend the ONE define_table("tenants",
    ...) call already in app.py" instruction the way M1 did -- `tenants`
    and `communities` are both already bound (by app.py's
    `_bind_reference_tables` and this module's own `bind_auth_tables`,
    respectively) by the time any request reaches a tenant-blueprint
    route.

    Instead, this function is called lazily (see `blueprints/v1/tenant.py`
    ::_dal()`) and uses pydal's `redefine=True` to ADD fields to those two
    already-bound `Table` objects, always paired with `migrate=migrate`
    (production is always `False`) so this is a pure in-memory Field-list
    update -- no DDL, same "schema owned by
    config/postgres/migrations/*.sql, never by this process" invariant
    `_bind_reference_tables` documents for `tenants` itself. Verified
    empirically: `redefine=True` REPLACES a table's field list wholesale
    (not merge-by-name), so both redefine calls below repeat every field
    the table's original definition already had -- dropping one here would
    silently break `flask_core.tenancy.resolve_tenant_context`'s
    `row.is_active` access (`tenants`) or `auth_service.
    add_user_to_global_community()`'s `dal.communities.name`/`.display_name`
    access (`communities`) for every request served after this function's
    first call. Safe under Quart's single-threaded event loop: `define_table`
    has no `await` inside it, so no concurrent request can observe a
    half-rebuilt `Table` object mid-call. Idempotent (`"tenant_settings" in
    dal.tables` guard) -- cheap to call on every request via `_dal()`.

    New columns, all real (not invented) per `config/postgres/migrations/
    058_tenants_and_claims.sql` (`tenants.description`/`allowed_module_ids`/
    `seat_limit`/`created_at`, `communities.tenant_id`) and `000_create_base_
    schema.sql`/`008_add_community_types.sql` (`communities.is_public`/
    `community_type`/`created_at`) -- `tenantController.js`'s `getTenant`/
    `updateTenant`/`getTenantModules`/`getTenantCommunities` all read them.

    `tenant_settings` (`058_tenants_and_claims.sql`) and `hub_modules`
    (`000_create_base_schema.sql`) are new tables, owned outright by this
    group -- bound the normal (non-redefine) way.
    """
    if "tenant_settings" in dal.tables:
        return

    dal.define_table(
        "tenants",
        Field("slug", "string", length=100),
        Field("display_name", "string", length=255),
        Field("logo_url", "text"),
        Field("is_global", "boolean", default=False),
        Field("is_active", "boolean", default=True),
        Field("config", "json"),
        Field("description", "text"),
        Field("allowed_module_ids", "list:integer"),
        Field("seat_limit", "integer"),
        Field("created_at", "datetime"),
        migrate=migrate,
        redefine=True,
    )

    dal.define_table(
        "communities",
        Field("name", "string", length=255),
        Field("display_name", "string", length=255),
        Field("is_global", "boolean", default=False),
        Field("is_active", "boolean", default=True),
        Field("member_count", "integer", default=0),
        Field("config", "json"),
        Field("tenant_id", "integer"),
        Field("is_public", "boolean", default=True),
        Field("community_type", "string", length=50, default="creator"),
        Field("created_at", "datetime"),
        migrate=migrate,
        redefine=True,
    )

    dal.define_table(
        "tenant_settings",
        Field("tenant_id", "integer", notnull=True),
        Field("key", "string", length=100, notnull=True),
        Field("value", "text"),
        Field("created_at", "datetime"),
        Field("updated_at", "datetime"),
        migrate=migrate,
    )

    dal.define_table(
        "hub_modules",
        Field("name", "string", length=255),
        Field("display_name", "string", length=255),
        Field("description", "text"),
        Field("category", "string", length=100),
        Field("is_core", "boolean", default=False),
        Field("is_published", "boolean", default=False),
        Field("version", "string", length=50),
        Field("created_at", "datetime"),
        migrate=migrate,
    )


def bind_marketplace_catalog_tables(dal: Any, *, migrate: bool = False) -> None:
    """Define every table the marketplace-catalog group's port queries.

    `app.py`/`routers/*.py`/`blueprints/__init__.py` are frozen (the
    parallel port wave's auto-discovery contract -- see
    `routers/_discovery.py`'s own docstring), so unlike `bind_auth_tables`
    this is never called from `app.py::_bind_reference_tables`. Instead it
    is idempotent (`dal.tables` membership guard, same idiom as
    `services/community_common.py::ensure_community_tables`) and called at
    the top of every `services/marketplace_catalog_service.py` function,
    matching the pattern the Community-module port (M6) already
    established once `app.py` stopped being editable.

    `marketplace_catalog` is a read-only Postgres VIEW
    (`config/postgres/migrations/059_marketplace_consolidation.sql`,
    unions `hub_modules` + approved `marketplace_modules`), not a table --
    pydal has no notion of "view" so it is bound as an ordinary table this
    process only ever `select()`s (`migrate=True` in tests creates a real
    throwaway TABLE with the same columns instead of a view; the test
    fixture seeds rows directly rather than replicating the view's
    Postgres-side UNION/aggregation, matching this repo's established
    "one field definition, tests seed it directly" convention -- see
    `tests/conftest.py::auth_db`). No single-column primary key exists on
    the view, so `primarykey=["source", "source_id"]` (the view's own
    natural composite key) is used instead, the same `primarykey=`
    pattern `flask_core.app_bundle_tables.init_app_bundle_tables` uses for
    `app_catalog`.

    `hub_modules.is_featured` -- see this module's own docstring gap (4)
    -- and `marketplace_modules` itself are NOT queried directly by
    either ported controller (`catalogController.js` only ever queries
    the `marketplace_catalog` view; `moduleController.js` only ever
    queries `hub_modules`/`hub_module_reviews`/`hub_module_installations`)
    -- `marketplace_modules` is therefore intentionally not bound here;
    a future group porting vendor self-service
    (`vendorController.js`) binds it then.
    """
    if "marketplace_catalog" in dal.tables:
        return

    dal.define_table(
        "marketplace_catalog",
        Field("source", "string", length=20, notnull=True),
        Field("source_id", "integer", notnull=True),
        Field("name", "string", length=255),
        Field("display_name", "string", length=255),
        Field("description", "text"),
        Field("category", "string", length=100),
        Field("icon_url", "text"),
        Field("is_core", "boolean", default=False),
        Field("pricing_type", "string", length=50, default="free"),
        Field("price_cents", "integer", default=0),
        Field("pricing_model", "string", length=50, default="flat"),
        Field("version", "string", length=50),
        Field("author", "string", length=255),
        Field("webhook_url", "text"),
        Field("communication_model", "string", length=50),
        Field("integration_type", "string", length=50),
        Field("avg_rating", "double", default=0),
        Field("review_count", "integer", default=0),
        Field("install_count", "integer", default=0),
        Field("created_at", "datetime"),
        Field("updated_at", "datetime"),
        # NULL for 'core' rows (always globally visible); the owning
        # tenant for 'marketplace' rows (backfilled to the global tenant
        # by 059's own migration when unset). Filtered by
        # `visible_tenant_ids()` -- see marketplace_catalog_service.py's
        # module docstring for the cross-tenant-leak fix this closes.
        Field("tenant_id", "integer"),
        primarykey=["source", "source_id"],
        migrate=migrate,
    )

    dal.define_table(
        "hub_modules",
        Field("name", "string", length=255, notnull=True, unique=True),
        Field("display_name", "string", length=255),
        Field("description", "text"),
        Field("version", "string", length=50),
        Field("author", "string", length=255),
        Field("category", "string", length=100),
        Field("icon_url", "text"),
        Field("is_published", "boolean", default=False),
        Field("is_core", "boolean", default=False),
        # See module docstring gap (4) -- no numbered migration defines
        # this column on hub_modules; bound anyway to stay byte-faithful
        # to moduleService.js's create/update/format queries.
        Field("is_featured", "boolean", default=False),
        Field("config_schema", "json", default={}),
        Field("created_at", "datetime"),
        Field("updated_at", "datetime"),
        migrate=migrate,
    )

    dal.define_table(
        "hub_module_reviews",
        Field("module_id", "integer", notnull=True),
        Field("community_id", "integer"),
        Field("user_id", "integer"),
        Field("rating", "integer"),
        Field("review_text", "text"),
        Field("admin_notes", "text"),
        Field("created_at", "datetime"),
        migrate=migrate,
    )

    dal.define_table(
        "hub_module_installations",
        Field("community_id", "integer", notnull=True),
        Field("module_id", "integer"),
        Field("installed_by", "integer"),
        Field("config", "json", default={}),
        Field("is_enabled", "boolean", default=True),
        Field("installed_at", "datetime"),
        Field("updated_at", "datetime"),
        migrate=migrate,
    )

    # Minimal projection -- schema-owned by
    # `059_marketplace_consolidation.sql`'s extension of
    # `017_add_marketplace.sql`'s original table; only the columns the
    # catalog's install-status enrichment needs.
    dal.define_table(
        "marketplace_subscriptions",
        Field("community_id", "integer", notnull=True),
        Field("module_id", "integer", notnull=True),
        Field("is_enabled", "boolean", default=True),
        Field("tenant_id", "integer"),
        migrate=migrate,
    )
