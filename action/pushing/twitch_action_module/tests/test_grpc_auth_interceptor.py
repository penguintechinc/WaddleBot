"""Tests for the gRPC auth guard protecting TwitchActionServicer.

Regression coverage for the CRITICAL finding (C7): this servicer's RPC
methods used to perform zero token verification. This servicer's server
transport is not fully wired to generated protobuf stubs yet, so
``require_auth`` is invoked directly at the top of every RPC method
instead of via a server-level interceptor -- these tests prove it rejects
unauthenticated/unauthorized callers and passes through valid ones.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import grpc
import jwt
import pytest

from config import Config
from services.grpc_auth_interceptor import (
    authorize_service,
    require_auth,
    verify_service_token,
)


def _make_token(**overrides: object) -> str:
    payload: dict[str, object] = {
        "service": "router_module",
        "iat": 0,
        "exp": 9999999999,
    }
    payload.update(overrides)
    return jwt.encode(payload, Config.MODULE_SECRET_KEY, algorithm=Config.JWT_ALGORITHM)


class TestVerifyServiceToken:
    """Unit tests for the shared token-validation helper."""

    def test_missing_metadata_is_rejected(self) -> None:
        valid, claims, error = verify_service_token({})
        assert valid is False
        assert claims is None
        assert "Missing bearer token" in error

    def test_invalid_signature_is_rejected(self) -> None:
        forged = jwt.encode(
            {"service": "router_module", "exp": 9999999999},
            "not-the-real-secret",
            algorithm=Config.JWT_ALGORITHM,
        )
        valid, claims, error = verify_service_token(
            {"authorization": f"Bearer {forged}"}
        )
        assert valid is False
        assert claims is None

    def test_expired_token_is_rejected(self) -> None:
        expired = _make_token(exp=1)
        valid, claims, error = verify_service_token(
            {"authorization": f"Bearer {expired}"}
        )
        assert valid is False
        assert error == "Token expired"

    def test_valid_token_is_accepted(self) -> None:
        token = _make_token()
        valid, claims, error = verify_service_token(
            {"authorization": f"Bearer {token}"}
        )
        assert valid is True
        assert claims is not None
        assert claims["service"] == "router_module"


class TestAuthorizeService:
    """Unit tests for the service-claim allowlist check."""

    def test_missing_service_claim_is_denied(self) -> None:
        authorized, error = authorize_service({})
        assert authorized is False

    def test_disallowed_service_is_denied(self) -> None:
        authorized, error = authorize_service({"service": "some_random_caller"})
        assert authorized is False

    def test_allowed_service_is_authorized(self) -> None:
        authorized, error = authorize_service({"service": "router_module"})
        assert authorized is True


class TestRequireAuth:
    """Unit tests for the per-RPC-method auth guard."""

    @pytest.mark.asyncio
    async def test_missing_token_aborts_unauthenticated(self) -> None:
        context = AsyncMock()
        context.invocation_metadata = MagicMock(return_value=())
        context.abort = AsyncMock(side_effect=grpc.aio.AbortError())

        with pytest.raises(grpc.aio.AbortError):
            await require_auth(context)

        context.abort.assert_awaited_once()
        assert context.abort.await_args.args[0] == grpc.StatusCode.UNAUTHENTICATED

    @pytest.mark.asyncio
    async def test_disallowed_service_aborts_permission_denied(self) -> None:
        token = _make_token(service="untrusted_service")
        context = AsyncMock()
        context.invocation_metadata = MagicMock(
            return_value=(("authorization", f"Bearer {token}"),)
        )
        context.abort = AsyncMock(side_effect=grpc.aio.AbortError())

        with pytest.raises(grpc.aio.AbortError):
            await require_auth(context)

        context.abort.assert_awaited_once()
        assert context.abort.await_args.args[0] == grpc.StatusCode.PERMISSION_DENIED

    @pytest.mark.asyncio
    async def test_valid_authorized_token_returns_claims(self) -> None:
        token = _make_token()
        context = AsyncMock()
        context.invocation_metadata = MagicMock(
            return_value=(("authorization", f"Bearer {token}"),)
        )

        claims = await require_auth(context)

        context.abort.assert_not_called()
        assert claims["service"] == "router_module"
