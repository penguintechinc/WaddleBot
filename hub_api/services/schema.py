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
        # description/logo_url/banner_url/primary_platform/platform/is_public/
        # community_type/join_mode/created_at/updated_at/tenant_id added by
        # the M3 Platform-admin/Public group (platformController.js/
        # publicController.js both read these) -- `communities` is bound
        # once, here, by M1; extending the field list is the established
        # cross-group-table pattern (see hub_settings below), never a second
        # define_table() call. All new columns are genuinely present in
        # `config/postgres/migrations/000_create_base_schema.sql` +
        # `058_tenants_and_claims.sql` (tenant_id) -- no gap here, unlike
        # gaps (1)/(2)/(3) above.
        Field("description", "text"),
        Field("logo_url", "text"),
        Field("banner_url", "text"),
        Field("primary_platform", "string", length=50),
        Field("platform", "string", length=50),
        Field("is_global", "boolean", default=False),
        Field("is_active", "boolean", default=True),
        Field("is_public", "boolean", default=True),
        Field("community_type", "string", length=50, default="creator"),
        Field("join_mode", "string", length=50, default="open"),
        Field("member_count", "integer", default=0),
        Field("config", "json"),
        Field("created_at", "datetime"),
        Field("updated_at", "datetime"),
        # NOT NULL in Postgres (058_tenants_and_claims.sql) -- every public/
        # platform-admin query that lists communities MUST filter on this
        # (security.md Tenant Isolation); see services/public_service.py's
        # module docstring for the pre-auth resolution mechanism.
        Field("tenant_id", "integer"),
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
