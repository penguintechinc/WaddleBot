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
        Field("is_global", "boolean", default=False),
        Field("is_active", "boolean", default=True),
        Field("member_count", "integer", default=0),
        Field("config", "json"),
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
