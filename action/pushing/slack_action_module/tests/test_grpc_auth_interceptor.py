"""Tests for the gRPC auth interceptor protecting SlackActionServicer.

Regression coverage for the CRITICAL finding (C7): this servicer's RPCs
used to be callable by anyone who could reach the port, with zero token
verification. These tests prove an unauthenticated/unauthorized call is
rejected with UNAUTHENTICATED/PERMISSION_DENIED before it reaches the
servicer, and that a properly authorized caller is still let through.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import grpc
import jwt
import pytest

from config import Config
from services.grpc_auth_interceptor import (
    AuthInterceptor,
    authorize_service,
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

    def test_non_bearer_scheme_is_rejected(self) -> None:
        valid, claims, error = verify_service_token({"authorization": "Basic abc"})
        assert valid is False
        assert claims is None

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
        assert "Invalid token" in error

    def test_expired_token_is_rejected(self) -> None:
        expired = _make_token(exp=1)
        valid, claims, error = verify_service_token(
            {"authorization": f"Bearer {expired}"}
        )
        assert valid is False
        assert claims is None
        assert error == "Token expired"

    def test_valid_token_is_accepted(self) -> None:
        token = _make_token()
        valid, claims, error = verify_service_token(
            {"authorization": f"Bearer {token}"}
        )
        assert valid is True
        assert claims is not None
        assert claims["service"] == "router_module"
        assert error == ""


class TestAuthorizeService:
    """Unit tests for the service-claim allowlist check."""

    def test_missing_service_claim_is_denied(self) -> None:
        authorized, error = authorize_service({})
        assert authorized is False
        assert "missing a service claim" in error

    def test_disallowed_service_is_denied(self) -> None:
        authorized, error = authorize_service({"service": "some_random_caller"})
        assert authorized is False
        assert "not authorized" in error

    def test_allowed_service_is_authorized(self) -> None:
        authorized, error = authorize_service({"service": "router_module"})
        assert authorized is True
        assert error == ""


class TestAuthInterceptor:
    """Unit tests exercising ``intercept_service`` directly with mocks.

    A real ``grpc.aio.server`` round-trip is exercised in the
    gcp_functions_action_module suite (the one module with generated
    protobuf stubs checked at test time); these mock-based tests give the
    same fail-first coverage without requiring a proto build step here.
    """

    @pytest.mark.asyncio
    async def test_missing_token_short_circuits_to_unauthenticated(self) -> None:
        interceptor = AuthInterceptor()
        handler_call_details = MagicMock()
        handler_call_details.invocation_metadata = ()
        handler_call_details.method = "/slack.action.v1/SendMessage"
        continuation = AsyncMock()

        handler = await interceptor.intercept_service(continuation, handler_call_details)

        continuation.assert_not_called()
        context = AsyncMock()
        await handler.unary_unary(MagicMock(), context)
        context.abort.assert_awaited_once()
        assert context.abort.await_args.args[0] == grpc.StatusCode.UNAUTHENTICATED

    @pytest.mark.asyncio
    async def test_disallowed_service_short_circuits_to_permission_denied(self) -> None:
        token = _make_token(service="untrusted_service")
        interceptor = AuthInterceptor()
        handler_call_details = MagicMock()
        handler_call_details.invocation_metadata = (
            ("authorization", f"Bearer {token}"),
        )
        handler_call_details.method = "/slack.action.v1/SendMessage"
        continuation = AsyncMock()

        handler = await interceptor.intercept_service(continuation, handler_call_details)

        continuation.assert_not_called()
        context = AsyncMock()
        await handler.unary_unary(MagicMock(), context)
        context.abort.assert_awaited_once()
        assert context.abort.await_args.args[0] == grpc.StatusCode.PERMISSION_DENIED

    @pytest.mark.asyncio
    async def test_valid_authorized_token_invokes_continuation(self) -> None:
        token = _make_token()
        interceptor = AuthInterceptor()
        handler_call_details = MagicMock()
        handler_call_details.invocation_metadata = (
            ("authorization", f"Bearer {token}"),
        )
        handler_call_details.method = "/slack.action.v1/SendMessage"
        sentinel_handler = MagicMock()
        continuation = AsyncMock(return_value=sentinel_handler)

        handler = await interceptor.intercept_service(continuation, handler_call_details)

        continuation.assert_awaited_once_with(handler_call_details)
        assert handler is sentinel_handler
