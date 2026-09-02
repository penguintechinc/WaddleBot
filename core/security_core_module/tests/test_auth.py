"""Security-Core Authentication/Authorization Tests.

security_core_module (`app.py`) previously exposed every `api_bp` route
(`/api/v1/security/<community_id>/...`) and `internal_bp` route
(`/api/v1/internal/...`) with ZERO authentication -- any caller reaching
the service's network address could read/write ANY community's warnings,
blocked words, and moderation log (BOLA, OWASP A01), and inject fabricated
moderation events on the internal service-to-service routes. This is the
fix's regression suite.

Fail-first proof: with `install_community_scoped_auth(api_bp)` (app.py's
module-level call) commented out, `test_get_status_requires_token`,
`test_get_config_requires_token`, `test_non_member_get_config_is_403`, and
`test_member_forbidden_from_write_route` all went green->red as expected
(200 instead of 401/403). Separately, with `_require_internal_service_key`
temporarily replaced with a bare `return None`,
`test_internal_check_requires_service_key` went red the same way. Both
reverted after confirming; see PR report for the exact before/after run.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

from tests.conftest import (
    OTHER_TENANT_SLUG,
    TENANT_SLUG,
    make_token,
    seed_community,
    seed_membership,
    seed_tenant,
)


class TestApiBpTenantAndCommunityAuth:
    async def test_get_status_requires_token(self, client: Any) -> None:
        """`/status` has no community_id -- still requires a valid bearer token."""
        response = await client.get("/api/v1/security/status")
        assert response.status_code == 401

    async def test_get_status_with_valid_token_passes(
        self, client: Any, dal_pair: tuple[Any, Any]
    ) -> None:
        _, dal = dal_pair
        seed_tenant(dal)
        token = make_token()
        response = await client.get(
            "/api/v1/security/status", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200

    async def test_get_config_requires_token(self, client: Any, dal_pair: tuple[Any, Any]) -> None:
        _, dal = dal_pair
        tenant_id = seed_tenant(dal)
        community_id = seed_community(dal, tenant_id=tenant_id)
        response = await client.get(f"/api/v1/security/{community_id}/config")
        assert response.status_code == 401

    async def test_non_member_get_config_is_403(
        self, client: Any, dal_pair: tuple[Any, Any]
    ) -> None:
        """BOLA case: a valid tenant JWT, but the caller isn't a member of THIS community."""
        _, dal = dal_pair
        tenant_id = seed_tenant(dal)
        community_id = seed_community(dal, tenant_id=tenant_id)
        token = make_token(sub="999")
        response = await client.get(
            f"/api/v1/security/{community_id}/config",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

    async def test_cross_tenant_community_id_is_403(
        self, client: Any, dal_pair: tuple[Any, Any]
    ) -> None:
        """Same-numbered community, different tenant -- must not leak via a real caller's JWT."""
        _, dal = dal_pair
        tenant_id = seed_tenant(dal, slug=TENANT_SLUG)
        other_tenant_id = seed_tenant(dal, slug=OTHER_TENANT_SLUG)
        seed_community(dal, tenant_id=tenant_id)
        other_community_id = seed_community(dal, tenant_id=other_tenant_id)
        token = make_token(sub="1", tenant=TENANT_SLUG)
        response = await client.get(
            f"/api/v1/security/{other_community_id}/config",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

    async def test_member_forbidden_from_write_route(
        self, client: Any, dal_pair: tuple[Any, Any]
    ) -> None:
        """A plain member (not admin) can GET config, but cannot PUT it."""
        _, dal = dal_pair
        tenant_id = seed_tenant(dal)
        community_id = seed_community(dal, tenant_id=tenant_id)
        seed_membership(dal, community_id=community_id, user_id=1, role="member")
        token = make_token(sub="1")
        response = await client.put(
            f"/api/v1/security/{community_id}/config",
            headers={"Authorization": f"Bearer {token}"},
            json={"use_builtin_profanity": True},
        )
        assert response.status_code == 403

    async def test_member_passes_read_route(
        self, client: Any, dal_pair: tuple[Any, Any], app_and_client: tuple[Any, Any]
    ) -> None:
        """A member reaches the real handler -- proven by a 200 from a stubbed service call."""
        app_module, _ = app_and_client
        _, dal = dal_pair
        tenant_id = seed_tenant(dal)
        community_id = seed_community(dal, tenant_id=tenant_id)
        seed_membership(dal, community_id=community_id, user_id=1, role="member")
        app_module.security_service.get_config = AsyncMock(
            return_value={"community_id": community_id}
        )

        token = make_token(sub="1")
        response = await client.get(
            f"/api/v1/security/{community_id}/config",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

    async def test_admin_passes_write_route(
        self, client: Any, dal_pair: tuple[Any, Any], app_and_client: tuple[Any, Any]
    ) -> None:
        """A community-admin reaches the real handler for a mutating route."""
        app_module, _ = app_and_client
        _, dal = dal_pair
        tenant_id = seed_tenant(dal)
        community_id = seed_community(dal, tenant_id=tenant_id)
        seed_membership(dal, community_id=community_id, user_id=2, role="community-admin")
        app_module.security_service.update_config = AsyncMock(
            return_value={"community_id": community_id}
        )

        token = make_token(sub="2")
        response = await client.put(
            f"/api/v1/security/{community_id}/config",
            headers={"Authorization": f"Bearer {token}"},
            json={"use_builtin_profanity": True},
        )
        assert response.status_code == 200


class TestInternalBpServiceKeyAuth:
    async def test_internal_check_requires_service_key(self, client: Any) -> None:
        response = await client.post(
            "/api/v1/internal/check",
            json={
                "community_id": 1,
                "platform": "twitch",
                "platform_user_id": "u1",
                "message": "hello",
            },
        )
        assert response.status_code == 401

    async def test_internal_check_rejects_wrong_service_key(self, client: Any) -> None:
        response = await client.post(
            "/api/v1/internal/check",
            headers={"X-Service-Key": "not-the-real-key"},
            json={
                "community_id": 1,
                "platform": "twitch",
                "platform_user_id": "u1",
                "message": "hello",
            },
        )
        assert response.status_code == 401

    async def test_internal_check_accepts_correct_service_key(
        self, client: Any, app_and_client: tuple[Any, Any]
    ) -> None:
        app_module, _ = app_and_client
        app_module.spam_detector.check_spam = AsyncMock(return_value=False)
        app_module.content_filter.check_message = AsyncMock(return_value=(False, None))

        response = await client.post(
            "/api/v1/internal/check",
            headers={"X-Service-Key": "test-service-key"},
            json={
                "community_id": 1,
                "platform": "twitch",
                "platform_user_id": "u1",
                "message": "hello",
            },
        )
        assert response.status_code == 200

    async def test_internal_warn_requires_service_key(self, client: Any) -> None:
        response = await client.post(
            "/api/v1/internal/warn",
            json={
                "community_id": 1,
                "platform": "twitch",
                "platform_user_id": "u1",
                "warning_type": "spam",
                "warning_reason": "spamming",
            },
        )
        assert response.status_code == 401

    async def test_internal_sync_action_requires_service_key(self, client: Any) -> None:
        response = await client.post(
            "/api/v1/internal/sync-action",
            json={
                "community_id": 1,
                "platform": "twitch",
                "platform_user_id": "u1",
                "action_type": "timeout",
            },
        )
        assert response.status_code == 401
