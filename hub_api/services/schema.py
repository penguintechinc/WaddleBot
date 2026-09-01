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
        # Added by the M7 Streaming group (`bind_streaming_tables()` below) --
        # `flask_core.tenancy.tenant_scoped()`'s community_id-owning-table
        # fallback path reads `dal.communities.tenant_id` directly, but no
        # group before M7 queried a community_id-owning table through that
        # helper, so it was never bound. Real column since migration
        # 058_tenants_and_claims.sql (`ALTER TABLE communities ADD COLUMN
        # ... tenant_id`); extended here rather than redefining the table,
        # same pattern `app.py::_bind_reference_tables()`'s own docstring
        # documents for `tenants`.
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
        Field("role", "string", length=50, default="member"),
        Field("is_active", "boolean", default=True),
        Field("joined_at", "datetime"),
        # Added by the M7 Streaming group -- real columns since migration
        # 058_tenants_and_claims.sql, used by `services.community_authz`'s
        # faithful port of `middleware/auth.js`'s `requireMember`/
        # `requireCommunityAdmin` (LEFT JOIN `community_roles`, parse
        # `claims_cache`/`base_claims` for the caller's community-scoped
        # OIDC scopes). Extended here rather than redefining the table.
        Field("community_role_id", "integer"),
        Field("claims_cache", "json"),
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

    `community_roles` is a real table (migration
    058_tenants_and_claims.sql) bound here for the first time -- no group
    before M7 needed the community-scoped-role join `services.
    community_authz` performs (`middleware/auth.js`'s `requireMember`/
    `requireCommunityAdmin`, byte-faithfully ported: LEFT JOIN
    `community_members.community_role_id -> community_roles.id`, parse
    `claims_cache`/`base_claims` for the caller's scopes). `coordination`/
    `community_servers` are likewise real, pre-existing tables
    (`004_add_missing_tables.sql` / `000_create_base_schema.sql`) queried
    read-only by `stream_service.py`.

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
    if "community_roles" in dal.tables:
        return

    dal.define_table(
        "community_roles",
        Field("community_id", "integer", notnull=True),
        Field("name", "string", length=50, notnull=True),
        Field("display_name", "string", length=100),
        Field("priority", "integer", default=0),
        Field("base_claims", "json"),
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
        "community_servers",
        Field("community_id", "integer", notnull=True),
        Field("platform", "string", length=50, notnull=True),
        Field("platform_server_id", "string", length=255, notnull=True),
        Field("status", "string", length=50, default="pending"),
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
