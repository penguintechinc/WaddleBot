"""
Tenant Isolation Tests
=======================

Centerpiece: `TestCrossTenantIsolation` proves a token scoped to tenant A
never reaches tenant B's rows, via `tenant_scoped`. Also covers the
mandatory `tenant` JWT claim and its bounded migration-window fallback --
see security.md Tenant Isolation and Task 0.4 of
docs/plans/2026-08-26-v3-scbm-apps.md.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
import pytest
from pydal import DAL, Field

from flask_core.auth import (
    DEFAULT_TENANT_SLUG,
    TENANT_CLAIM_MIGRATION_CUTOFF,
    create_jwt_token,
    setup_default_roles,
    verify_jwt_token,
)
from flask_core.tenancy import TenantContext, TenantIsolationError, tenant_scoped

SECRET = "test-secret-key-not-for-production-use-only"


@pytest.fixture
def db():
    """In-memory pydal DB modelling the tenants -> communities -> posts chain."""
    dal = DAL("sqlite:memory")
    dal.define_table("tenants", Field("slug", unique=True), Field("is_active", "boolean", default=True))
    dal.define_table("communities", Field("tenant_id", "reference tenants"), Field("name"))
    dal.define_table("posts", Field("community_id", "reference communities"), Field("title"))
    dal.define_table("orphan_widgets", Field("label"))  # neither tenant_id nor community_id
    dal.define_table(
        "auth_role",
        Field("name", "string", unique=True, notnull=True),
        Field("level", "string"),
        Field("description", "text"),
        Field("permissions", "json"),
    )
    yield dal
    dal.close()


@pytest.fixture
def two_tenants(db):
    """Seed two tenants, one community each, one post each -- the isolation fixture."""
    tenant_a = db.tenants.insert(slug="tenant-a")
    tenant_b = db.tenants.insert(slug="tenant-b")
    community_a = db.communities.insert(tenant_id=tenant_a, name="A Community")
    community_b = db.communities.insert(tenant_id=tenant_b, name="B Community")
    db.posts.insert(community_id=community_a, title="a-post")
    db.posts.insert(community_id=community_b, title="b-post")
    db.commit()
    return {"tenant_a": tenant_a, "tenant_b": tenant_b}


class TestCrossTenantIsolation:
    """The centerpiece: a token for tenant A must not reach tenant B's data."""

    def test_unscoped_query_leaks_cross_tenant_data(self, db, two_tenants):
        """Documents the pre-Task-0.4 vulnerability directly: a query with no
        tenant filter at all -- exactly what 246 files did -- returns every
        tenant's rows. This is what tenant_scoped exists to prevent; see the
        two tests below for the fix, and the fail-first proof in the PR
        report (tenant_scoped temporarily neutered, this same assertion
        pattern observed failing)."""
        rows = db(db.posts.id > 0).select()
        titles = {r.title for r in rows}
        assert titles == {"a-post", "b-post"}

    def test_tenant_scoped_excludes_other_tenant_direct_fk(self, db, two_tenants):
        """communities has a direct tenant_id column."""
        ctx_a = TenantContext(tenant_id=two_tenants["tenant_a"], tenant_slug="tenant-a")
        rows = db(tenant_scoped(db.communities.id > 0, ctx_a)).select()
        names = {r.name for r in rows}
        assert names == {"A Community"}
        assert "B Community" not in names

    def test_tenant_scoped_excludes_other_tenant_via_community_fk(self, db, two_tenants):
        """posts has no tenant_id -- scoping goes through community_id -> communities.tenant_id."""
        ctx_a = TenantContext(tenant_id=two_tenants["tenant_a"], tenant_slug="tenant-a")
        rows = db(tenant_scoped(db.posts.id > 0, ctx_a)).select()
        titles = {r.title for r in rows}
        assert titles == {"a-post"}
        assert "b-post" not in titles

    def test_tenant_scoped_symmetric_for_tenant_b(self, db, two_tenants):
        """Same helper, other tenant -- proves this isn't a one-sided fixture accident."""
        ctx_b = TenantContext(tenant_id=two_tenants["tenant_b"], tenant_slug="tenant-b")
        rows = db(tenant_scoped(db.posts.id > 0, ctx_b)).select()
        titles = {r.title for r in rows}
        assert titles == {"b-post"}
        assert "a-post" not in titles

    def test_default_tenant_runs_identical_code_n_equals_1(self, db):
        """No `if tenant == "default": skip_filter()` shortcut -- the default
        tenant is filtered by the exact same tenant_scoped() call path, just
        with a roster of one."""
        default_tenant = db.tenants.insert(slug=DEFAULT_TENANT_SLUG)
        community = db.communities.insert(tenant_id=default_tenant, name="Only Community")
        db.posts.insert(community_id=community, title="only-post")
        db.commit()

        ctx = TenantContext(tenant_id=default_tenant, tenant_slug=DEFAULT_TENANT_SLUG, is_default=True)
        rows = db(tenant_scoped(db.posts.id > 0, ctx)).select()
        assert {r.title for r in rows} == {"only-post"}

    def test_tenant_scoped_rejects_table_with_no_tenant_path(self, db, two_tenants):
        """A table with neither tenant_id nor community_id fails loudly, not silently."""
        db.orphan_widgets.insert(label="mystery")
        db.commit()
        ctx_a = TenantContext(tenant_id=two_tenants["tenant_a"], tenant_slug="tenant-a")
        with pytest.raises(TenantIsolationError):
            tenant_scoped(db.orphan_widgets.id > 0, ctx_a)


class TestTenantClaim:
    """create_jwt_token/verify_jwt_token: the tenant claim contract."""

    def test_create_jwt_token_requires_tenant(self):
        with pytest.raises(ValueError):
            create_jwt_token(
                user_id="u1",
                username="alice",
                email="alice@example.com",
                roles=["viewer"],
                secret_key=SECRET,
                tenant="",
            )

    def test_create_and_verify_round_trip_carries_tenant(self):
        token = create_jwt_token(
            user_id="u1",
            username="alice",
            email="alice@example.com",
            roles=["viewer"],
            secret_key=SECRET,
            tenant="tenant-a",
        )
        payload = verify_jwt_token(token, SECRET)
        assert payload is not None
        assert payload["tenant"] == "tenant-a"

    def test_verify_rejects_missing_tenant_claim_post_cutoff(self):
        """A token issued after the migration cutoff with no tenant claim is
        rejected outright -- the fallback is bounded, not permanent."""
        now = datetime.now(timezone.utc)
        assert now < TENANT_CLAIM_MIGRATION_CUTOFF, "test assumes 'now' precedes the cutoff constant"
        post_cutoff_iat = TENANT_CLAIM_MIGRATION_CUTOFF + timedelta(days=1)
        payload = {
            "sub": "u1",
            "username": "alice",
            "email": "alice@example.com",
            "roles": [],
            "iat": post_cutoff_iat,
            "exp": post_cutoff_iat + timedelta(hours=1),
            "type": "access",
        }
        token = jwt.encode(payload, SECRET, algorithm="HS256")
        # exp is compared against real wall-clock utcnow(); a post-cutoff iat
        # is necessarily in the future too, so the token is not yet expired --
        # rejection here is solely the missing-tenant-claim path.
        assert verify_jwt_token(token, SECRET) is None

    def test_verify_applies_default_tenant_fallback_pre_cutoff(self):
        """A legacy token (no tenant claim, issued before the cutoff) is
        defaulted to DEFAULT_TENANT_SLUG rather than rejected."""
        legacy_iat = datetime.now(timezone.utc)
        assert legacy_iat < TENANT_CLAIM_MIGRATION_CUTOFF
        payload = {
            "sub": "u1",
            "username": "alice",
            "email": "alice@example.com",
            "roles": [],
            "iat": legacy_iat,
            "exp": legacy_iat + timedelta(hours=1),
            "type": "access",
        }
        token = jwt.encode(payload, SECRET, algorithm="HS256")
        result = verify_jwt_token(token, SECRET)
        assert result is not None
        assert result["tenant"] == DEFAULT_TENANT_SLUG


class TestScopeBundles:
    """setup_default_roles: per-level scope bundles, no unbounded '*'."""

    def test_creates_roles_at_all_three_levels(self, db):
        setup_default_roles(db)
        names = {r.name for r in db(db.auth_role).select()}
        for level in ("global", "tenant", "community"):
            for bundle in ("admin", "maintainer", "viewer"):
                assert f"{level}:{bundle}" in names

    def test_no_bundle_grants_unbounded_wildcard(self, db):
        setup_default_roles(db)
        for row in db(db.auth_role).select():
            assert "*" not in row.permissions, f"{row.name} grants unbounded '*'"

    def test_narrower_level_does_not_exceed_broader_level_scope_count(self, db):
        setup_default_roles(db)
        global_admin = db(db.auth_role.name == "global:admin").select().first()
        community_admin = db(db.auth_role.name == "community:admin").select().first()
        # Global admin's scopes are platform-wide wildcards; community admin's
        # are resource-specific -- narrower levels restrict, they don't gain
        # a broader grant global:admin doesn't already imply.
        assert all(not scope.startswith("*:") for scope in community_admin.permissions)
        assert any(scope.startswith("*:") for scope in global_admin.permissions)

    def test_setup_default_roles_is_idempotent(self, db):
        setup_default_roles(db)
        setup_default_roles(db)
        names = [r.name for r in db(db.auth_role).select()]
        assert len(names) == len(set(names))
