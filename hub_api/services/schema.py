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
        # py's module docstring for the pre-auth resolution mechanism.
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
        # community_members" ALTER) the M2 Core Tenancy-Misc group's
        # `services/community_authz.py` also relies on for its
        # per-community admin check -- bound once here, not duplicated.
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
