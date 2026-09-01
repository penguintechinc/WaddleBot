"""Community-membership authorization tests -- the IDOR guard for every community-scoped route.

Uses the real `app_and_client` fixture's `async_dal`/`dal` (file-backed
sqlite, real pydal queries) rather than mocking the DB layer -- this
module IS the DB-backed authz check, so testing it against a fake DB
would test nothing real.
"""

from __future__ import annotations

from typing import Any

import pytest
from flask_core.tenancy import TenantContext

from services import community_access
from services.errors import ApiError
from tests.conftest import (
    OTHER_TENANT_SLUG,
    TENANT_SLUG,
    make_super_admin_token,
    make_user_token,
    seed_community,
    seed_membership,
    seed_tenant,
)


class _FakeRequest:
    """Minimal stand-in for `quart.Request` -- only `.headers.get(...)` is ever read."""

    def __init__(self, *, bearer_token: str | None = None) -> None:
        self.headers: dict[str, str] = {}
        if bearer_token is not None:
            self.headers["Authorization"] = f"Bearer {bearer_token}"


@pytest.mark.asyncio
async def test_require_admin_allows_active_owner(app_and_client: Any, dal_pair: Any) -> None:
    async_dal, dal = dal_pair
    tenant_id = seed_tenant(dal, slug=TENANT_SLUG)
    community_id = seed_community(dal, tenant_id=tenant_id)
    seed_membership(dal, community_id=community_id, user_id=1, role="community-owner")
    ctx = TenantContext(tenant_id=tenant_id, tenant_slug=TENANT_SLUG)
    request = _FakeRequest(bearer_token=make_user_token(user_id=1))

    await community_access.require_admin(
        async_dal, dal, request, ctx, community_id=community_id, user_id=1
    )  # must not raise


@pytest.mark.asyncio
async def test_require_admin_rejects_non_admin_member(app_and_client: Any, dal_pair: Any) -> None:
    async_dal, dal = dal_pair
    tenant_id = seed_tenant(dal, slug=TENANT_SLUG)
    community_id = seed_community(dal, tenant_id=tenant_id)
    seed_membership(dal, community_id=community_id, user_id=2, role="member")
    ctx = TenantContext(tenant_id=tenant_id, tenant_slug=TENANT_SLUG)
    request = _FakeRequest(bearer_token=make_user_token(user_id=2))

    with pytest.raises(ApiError) as exc_info:
        await community_access.require_admin(
            async_dal, dal, request, ctx, community_id=community_id, user_id=2
        )
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_require_admin_rejects_non_member_entirely(
    app_and_client: Any, dal_pair: Any
) -> None:
    async_dal, dal = dal_pair
    tenant_id = seed_tenant(dal, slug=TENANT_SLUG)
    community_id = seed_community(dal, tenant_id=tenant_id)
    ctx = TenantContext(tenant_id=tenant_id, tenant_slug=TENANT_SLUG)
    request = _FakeRequest(bearer_token=make_user_token(user_id=999))

    with pytest.raises(ApiError) as exc_info:
        await community_access.require_admin(
            async_dal, dal, request, ctx, community_id=community_id, user_id=999
        )
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_require_admin_rejects_cross_tenant_community_id(
    app_and_client: Any, dal_pair: Any
) -> None:
    """The core IDOR case: a valid tenant-A token targeting a real tenant-B community."""
    async_dal, dal = dal_pair
    tenant_a = seed_tenant(dal, slug=TENANT_SLUG)
    tenant_b = seed_tenant(dal, slug=OTHER_TENANT_SLUG)
    community_in_b = seed_community(dal, tenant_id=tenant_b)
    seed_membership(dal, community_id=community_in_b, user_id=1, role="community-owner")
    ctx_for_tenant_a = TenantContext(tenant_id=tenant_a, tenant_slug=TENANT_SLUG)
    request = _FakeRequest(bearer_token=make_user_token(user_id=1, tenant=TENANT_SLUG))

    with pytest.raises(ApiError) as exc_info:
        await community_access.require_admin(
            async_dal, dal, request, ctx_for_tenant_a, community_id=community_in_b, user_id=1
        )
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_require_admin_super_admin_bypasses_membership_check(
    app_and_client: Any, dal_pair: Any
) -> None:
    async_dal, dal = dal_pair
    tenant_id = seed_tenant(dal, slug=TENANT_SLUG)
    community_id = seed_community(dal, tenant_id=tenant_id)
    ctx = TenantContext(tenant_id=tenant_id, tenant_slug=TENANT_SLUG)
    request = _FakeRequest(bearer_token=make_super_admin_token(user_id=1))

    await community_access.require_admin(
        async_dal, dal, request, ctx, community_id=community_id, user_id=1
    )  # must not raise -- no membership row seeded at all


@pytest.mark.asyncio
async def test_require_member_allows_any_active_role(app_and_client: Any, dal_pair: Any) -> None:
    async_dal, dal = dal_pair
    tenant_id = seed_tenant(dal, slug=TENANT_SLUG)
    community_id = seed_community(dal, tenant_id=tenant_id)
    seed_membership(dal, community_id=community_id, user_id=3, role="member")
    ctx = TenantContext(tenant_id=tenant_id, tenant_slug=TENANT_SLUG)
    request = _FakeRequest(bearer_token=make_user_token(user_id=3))

    await community_access.require_member(
        async_dal, dal, request, ctx, community_id=community_id, user_id=3
    )  # must not raise


@pytest.mark.asyncio
async def test_require_member_rejects_non_member(app_and_client: Any, dal_pair: Any) -> None:
    async_dal, dal = dal_pair
    tenant_id = seed_tenant(dal, slug=TENANT_SLUG)
    community_id = seed_community(dal, tenant_id=tenant_id)
    ctx = TenantContext(tenant_id=tenant_id, tenant_slug=TENANT_SLUG)
    request = _FakeRequest(bearer_token=make_user_token(user_id=404))

    with pytest.raises(ApiError) as exc_info:
        await community_access.require_member(
            async_dal, dal, request, ctx, community_id=community_id, user_id=404
        )
    assert exc_info.value.status_code == 403


def test_decode_caller_user_id_from_valid_token() -> None:
    request = _FakeRequest(bearer_token=make_user_token(user_id=42))
    assert community_access.decode_caller_user_id(request) == 42


def test_decode_caller_user_id_raises_401_without_header() -> None:
    request = _FakeRequest(bearer_token=None)
    with pytest.raises(ApiError) as exc_info:
        community_access.decode_caller_user_id(request)
    assert exc_info.value.status_code == 401


def test_decode_caller_user_id_raises_401_for_malformed_token() -> None:
    request = _FakeRequest()
    request.headers["Authorization"] = "Bearer not-a-real-jwt"
    with pytest.raises(ApiError) as exc_info:
        community_access.decode_caller_user_id(request)
    assert exc_info.value.status_code == 401
