"""`services/community_authz.py` -- direct unit tests for branches the blueprint layer can't reach.

`_decode_caller`/`authorize_community`'s early-return branches (missing
bearer token, invalid token, missing `sub` claim, unresolved tenant
context) are unreachable through the normal route path once
`tenant_middleware` has already run (it 401s on exactly those same
conditions first) -- same "defensive, second independent decode" shape
`services.current_user`'s own docstring describes. Tested directly here
against a minimal request-like stand-in, mirroring how
`tests/test_event_calendar_proxy.py` unit-tests `event_calendar_proxy.py`
below the blueprint layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest
from flask_core.auth import create_jwt_token

from services.community_authz import _decode_caller, _parse_claims_scopes, authorize_community
from services.errors import ApiError

SECRET_KEY = "change-me-in-production"


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
