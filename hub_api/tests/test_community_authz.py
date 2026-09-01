"""`services/community_authz.py` -- direct + integration coverage.

`tests/test_v1_workflow_blueprint.py`/`test_v1_github_sync_blueprint.py`
exercise the "not an admin -> 403" and "is a community member with the
right scope -> 200" paths through the real HTTP blueprints already --
`TestJwtRolesDirect`/`TestRequireCommunityAdminBypasses` below close the
remaining branches for the M-automation group's `require_community_admin()`:
the three bypasses (`super-admin`, `tenant-admin`, `platform-admin`), the
"member but wrong scope" 403, and `_jwt_roles()`'s own defensive branches
(unreachable through the normal HTTP flow, since `tenant_middleware`/
`get_current_user_id` already validate the bearer token before
`_jwt_roles()` ever runs -- covered here as a direct unit test of the
function instead).

`TestParseClaimsScopes`/`TestDecodeCaller`/`TestAuthorizeCommunityMissingTenantContext`
below cover the M7 Streaming group's own `_scoped` variant instead --
`_decode_caller`/`authorize_community`'s early-return branches (missing
bearer token, invalid token, missing `sub` claim, unresolved tenant
context) are similarly unreachable through the normal route path once
`tenant_middleware` has already run (it 401s on exactly those same
conditions first) -- same "defensive, second independent decode" shape
`services.current_user`'s own docstring describes. Tested directly here
against a minimal request-like stand-in, mirroring how
`tests/test_event_calendar_proxy.py` unit-tests `event_calendar_proxy.py`
below the blueprint layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import Mock

import jwt as pyjwt
import pytest
from flask_core.auth import create_jwt_token
from quart import Quart
from quart_schema import QuartSchema

import blueprints.v1.workflow as workflow_module
from blueprints.v1.workflow import workflow_bp
from services.community_authz import (
    _decode_caller,
    _jwt_roles,
    _parse_claims_scopes,
    authorize_community,
)
from services.errors import ApiError
from services.workflow_service import ProxyResult
from tests.conftest import SECRET_KEY, TENANT_SLUG

COMMUNITY_ID = 1


@dataclass(slots=True)
class _FakeRequest:
    """Minimal stand-in for `quart.Request` -- only the attributes these functions touch."""

    headers: dict[str, str] = field(default_factory=dict)
    tenant_context: Any = None


class TestParseClaimsScopes:
    def test_none_is_empty(self) -> None:
        assert _parse_claims_scopes(None) == frozenset()

    def test_valid_json_string_list(self) -> None:
        assert _parse_claims_scopes('["a:read", "b:write"]') == {"a:read", "b:write"}

    def test_invalid_json_string_is_empty(self) -> None:
        assert _parse_claims_scopes("not json") == frozenset()

    def test_list(self) -> None:
        assert _parse_claims_scopes(["a:read"]) == {"a:read"}

    def test_dict_with_scopes(self) -> None:
        assert _parse_claims_scopes({"scopes": ["a:read"]}) == {"a:read"}

    def test_dict_without_scopes_key_is_empty(self) -> None:
        assert _parse_claims_scopes({"other": True}) == frozenset()

    def test_unrecognized_type_is_empty(self) -> None:
        assert _parse_claims_scopes(42) == frozenset()


class TestDecodeCaller:
    def test_missing_authorization_header_is_401(self) -> None:
        with pytest.raises(ApiError) as exc_info:
            _decode_caller(_FakeRequest(headers={}))
        assert exc_info.value.status_code == 401

    def test_non_bearer_header_is_401(self) -> None:
        with pytest.raises(ApiError) as exc_info:
            _decode_caller(_FakeRequest(headers={"Authorization": "Basic xyz"}))
        assert exc_info.value.status_code == 401

    def test_invalid_token_is_401(self) -> None:
        with pytest.raises(ApiError) as exc_info:
            _decode_caller(_FakeRequest(headers={"Authorization": "Bearer not-a-real-jwt"}))
        assert exc_info.value.status_code == 401

    def test_token_missing_subject_claim_is_401(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import services.community_authz as module

        monkeypatch.setattr(module, "verify_jwt_token", lambda token, key: {"roles": []})
        with pytest.raises(ApiError) as exc_info:
            _decode_caller(_FakeRequest(headers={"Authorization": "Bearer x"}))
        assert exc_info.value.status_code == 401

    def test_success_returns_user_id_and_roles(self) -> None:
        token = create_jwt_token(
            user_id="7",
            username="alice",
            email="alice@example.com",
            roles=["super_admin"],
            secret_key=SECRET_KEY,
            tenant="acme-corp",
        )
        user_id, roles = _decode_caller(_FakeRequest(headers={"Authorization": f"Bearer {token}"}))
        assert user_id == 7
        assert roles == ["super_admin"]


class TestAuthorizeCommunityMissingTenantContext:
    async def test_no_tenant_context_is_403(self) -> None:
        with pytest.raises(ApiError) as exc_info:
            await authorize_community(
                _FakeRequest(headers={}, tenant_context=None),
                async_dal=None,
                dal=None,
                community_id=1,
                admin=True,
            )
        assert exc_info.value.status_code == 403


class _StubWorkflowCore:
    """Just enough of `WorkflowCoreProxyClient` for `list_workflows` to succeed without real I/O."""

    async def request(
        self, method: str, path: str, *, json_body: object = None, params: object = None
    ) -> ProxyResult:
        return ProxyResult(ok=True, status_code=200, body={"workflows": [], "pagination": {}})


@pytest.fixture(autouse=True)
def _stub_workflow_core(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(workflow_module, "_client", _StubWorkflowCore())


class TestJwtRolesDirect:
    """Direct unit tests -- these branches are unreachable through the normal HTTP flow."""

    def test_no_authorization_header_is_empty(self) -> None:
        request = Mock()
        request.headers = {}
        assert _jwt_roles(request) == frozenset()

    def test_non_bearer_header_is_empty(self) -> None:
        request = Mock()
        request.headers = {"Authorization": "Basic dXNlcjpwYXNz"}
        assert _jwt_roles(request) == frozenset()

    def test_invalid_token_is_empty(self) -> None:
        request = Mock()
        request.headers = {"Authorization": "Bearer not-a-real-jwt"}
        assert _jwt_roles(request) == frozenset()

    def test_non_list_roles_claim_is_empty(self) -> None:
        """`create_jwt_token()` only accepts `List[str]` -- hand-craft the payload instead."""
        token = pyjwt.encode(
            {
                "sub": "1",
                "tenant": TENANT_SLUG,
                "roles": "platform-admin",  # a bare string, not a list
                "exp": datetime.now(UTC) + timedelta(hours=1),
            },
            SECRET_KEY,
            algorithm="HS256",
        )
        request = Mock()
        request.headers = {"Authorization": f"Bearer {token}"}
        assert _jwt_roles(request) == frozenset()

    def test_platform_admin_role_is_present(self) -> None:
        token = create_jwt_token(
            user_id="1",
            username="u",
            email="u@example.com",
            roles=["platform-admin"],
            secret_key=SECRET_KEY,
            tenant=TENANT_SLUG,
        )
        request = Mock()
        request.headers = {"Authorization": f"Bearer {token}"}
        assert "platform-admin" in _jwt_roles(request)


class TestRequireCommunityAdminBypasses:
    """Integration coverage via `workflow.py`'s `list_workflows` -- the thinnest gated route."""

    def _app(self, automation_db: Any) -> Quart:
        quart_app = Quart(__name__)
        QuartSchema(quart_app)
        quart_app.register_blueprint(workflow_bp)
        quart_app.config["dal"] = automation_db.dal
        quart_app.config["async_dal"] = automation_db
        return quart_app

    def _token(self, *, user_id: str, roles: list[str] | None = None) -> str:
        return create_jwt_token(
            user_id=user_id,
            username="u",
            email="u@example.com",
            roles=roles or [],
            secret_key=SECRET_KEY,
            tenant=TENANT_SLUG,
        )

    async def test_super_admin_bypasses_community_membership(self, automation_db: Any) -> None:
        dal = automation_db.dal
        user_id = dal.hub_users.insert(username="root", is_super_admin=True)
        dal.commit()
        app = self._app(automation_db)
        client = app.test_client()
        response = await client.get(
            f"/api/v1/admin/{COMMUNITY_ID}/workflows",
            headers={"Authorization": f"Bearer {self._token(user_id=str(user_id))}"},
        )
        assert response.status_code == 200

    async def test_tenant_admin_bypasses_community_membership(self, automation_db: Any) -> None:
        dal = automation_db.dal
        user_id = dal.hub_users.insert(username="tadmin", is_super_admin=False)
        tenant_row = dal(dal.tenants.slug == TENANT_SLUG).select().first()
        dal.tenant_admins.insert(tenant_id=tenant_row.id, user_id=user_id, role="tenant-admin")
        dal.commit()
        app = self._app(automation_db)
        client = app.test_client()
        response = await client.get(
            f"/api/v1/admin/{COMMUNITY_ID}/workflows",
            headers={"Authorization": f"Bearer {self._token(user_id=str(user_id))}"},
        )
        assert response.status_code == 200

    async def test_platform_admin_role_bypasses_community_membership(
        self, automation_db: Any
    ) -> None:
        app = self._app(automation_db)
        client = app.test_client()
        response = await client.get(
            f"/api/v1/admin/{COMMUNITY_ID}/workflows",
            headers={
                "Authorization": f"Bearer {self._token(user_id='999', roles=['platform-admin'])}"
            },
        )
        assert response.status_code == 200

    async def test_member_with_wrong_scope_is_403(self, automation_db: Any) -> None:
        dal = automation_db.dal
        user_id = dal.hub_users.insert(username="member", is_super_admin=False)
        role_id = dal.community_roles.insert(
            community_id=COMMUNITY_ID, name="viewer", base_claims={"scopes": ["community:read"]}
        )
        dal.community_members.insert(
            community_id=COMMUNITY_ID,
            user_id=str(user_id),
            role="viewer",
            is_active=True,
            community_role_id=role_id,
        )
        dal.commit()
        app = self._app(automation_db)
        client = app.test_client()
        response = await client.get(
            f"/api/v1/admin/{COMMUNITY_ID}/workflows",
            headers={"Authorization": f"Bearer {self._token(user_id=str(user_id))}"},
        )
        assert response.status_code == 403

    async def test_member_with_no_role_assigned_is_403(self, automation_db: Any) -> None:
        """Legacy member row with `community_role_id=None` -- LEFT JOIN finds nothing."""
        dal = automation_db.dal
        user_id = dal.hub_users.insert(username="legacy-member", is_super_admin=False)
        dal.community_members.insert(
            community_id=COMMUNITY_ID, user_id=str(user_id), role="member", is_active=True
        )
        dal.commit()
        app = self._app(automation_db)
        client = app.test_client()
        response = await client.get(
            f"/api/v1/admin/{COMMUNITY_ID}/workflows",
            headers={"Authorization": f"Bearer {self._token(user_id=str(user_id))}"},
        )
        assert response.status_code == 403
