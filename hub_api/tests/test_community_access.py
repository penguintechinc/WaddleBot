"""`services/community_access.py` -- direct unit tests for `_is_super_admin`.

`test_v1_overlay_blueprint.py`/`test_v1_calls_blueprint.py` exercise
`require_community_admin`/`require_community_member` end-to-end through
the full `tenant_middleware` -> `require_scope` -> handler chain, which
means `_is_super_admin`'s "no bearer token" / "invalid token" branches
are structurally unreachable there -- `tenant_middleware` already 401s
before `community_access` ever runs in that case. This file calls
`_is_super_admin` directly with a minimal stand-in for `quart.Request`
(only `.headers.get(...)` is used) to close that gap.
"""

from __future__ import annotations

from services.community_access import _is_super_admin


class _FakeHeaders:
    def __init__(self, value: str | None) -> None:
        self._value = value

    def get(self, _name: str) -> str | None:
        return self._value


class _FakeRequest:
    def __init__(self, auth_header: str | None) -> None:
        self.headers = _FakeHeaders(auth_header)


class TestIsSuperAdmin:
    def test_no_authorization_header_is_false(self) -> None:
        assert _is_super_admin(_FakeRequest(None)) is False  # type: ignore[arg-type]

    def test_non_bearer_authorization_header_is_false(self) -> None:
        assert _is_super_admin(_FakeRequest("Basic dXNlcjpwYXNz")) is False  # type: ignore[arg-type]

    def test_invalid_token_is_false(self) -> None:
        assert _is_super_admin(_FakeRequest("Bearer not-a-real-jwt")) is False  # type: ignore[arg-type]
