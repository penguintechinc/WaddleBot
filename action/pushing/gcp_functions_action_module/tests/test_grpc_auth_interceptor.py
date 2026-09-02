"""Tests for the gRPC auth interceptor protecting GCPFunctionsActionServicer.

Regression coverage for the CRITICAL finding (C7): every RPC on this
servicer used to be callable by anyone who could reach the port. These
tests prove an unauthenticated/unauthorized call is rejected with
UNAUTHENTICATED/PERMISSION_DENIED, and that a properly authorized call
still succeeds end-to-end through a real ``grpc.aio.server``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock

import grpc
import jwt
import pytest

from config import Config
from grpc_proto import gcp_functions_action_pb2, gcp_functions_action_pb2_grpc
from services.gcp_functions_service import GCPFunctionsService
from services.grpc_auth_interceptor import (
    AuthInterceptor,
    authorize_service,
    verify_service_token,
)
from services.grpc_handler import GCPFunctionsActionServicer


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


class TestAuthInterceptorUnit:
    """Unit tests exercising ``intercept_service`` directly with mocks."""

    @pytest.mark.asyncio
    async def test_missing_token_short_circuits_to_unauthenticated(self) -> None:
        interceptor = AuthInterceptor()
        handler_call_details = MagicMock()
        handler_call_details.invocation_metadata = ()
        handler_call_details.method = "/gcp.functions.v1/InvokeFunction"
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
        handler_call_details.method = "/gcp.functions.v1/InvokeFunction"
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
        handler_call_details.method = "/gcp.functions.v1/InvokeFunction"
        sentinel_handler = MagicMock()
        continuation = AsyncMock(return_value=sentinel_handler)

        handler = await interceptor.intercept_service(continuation, handler_call_details)

        continuation.assert_awaited_once_with(handler_call_details)
        assert handler is sentinel_handler


@pytest.fixture
async def running_server() -> AsyncIterator[tuple[grpc.aio.Server, int]]:
    """Start a real gRPC server for InvokeFunction with the auth interceptor live."""
    gcp_service = MagicMock(spec=GCPFunctionsService)
    gcp_service.invoke_function = AsyncMock(
        return_value={
            "success": True,
            "status_code": 200,
            "response": "ok",
            "error": "",
            "execution_time_ms": 5,
        }
    )
    servicer = GCPFunctionsActionServicer(gcp_service)

    server = grpc.aio.server(interceptors=[AuthInterceptor()])
    gcp_functions_action_pb2_grpc.add_GCPFunctionsActionServiceServicer_to_server(
        servicer, server
    )
    port = server.add_insecure_port("127.0.0.1:0")
    await server.start()
    try:
        yield server, port
    finally:
        await server.stop(grace=None)


@pytest.mark.asyncio
class TestInvokeFunctionEndToEnd:
    """Fail-first, red->green: reject unauthenticated, allow authorized."""

    async def test_unauthenticated_call_is_rejected(
        self, running_server: tuple[grpc.aio.Server, int]
    ) -> None:
        _, port = running_server
        async with grpc.aio.insecure_channel(f"127.0.0.1:{port}") as channel:
            stub = gcp_functions_action_pb2_grpc.GCPFunctionsActionServiceStub(channel)
            request = gcp_functions_action_pb2.InvokeFunctionRequest(
                project="proj", region="us-central1", function_name="fn"
            )
            with pytest.raises(grpc.aio.AioRpcError) as exc_info:
                await stub.InvokeFunction(request)

            assert exc_info.value.code() == grpc.StatusCode.UNAUTHENTICATED

    async def test_authorized_call_succeeds(
        self, running_server: tuple[grpc.aio.Server, int]
    ) -> None:
        _, port = running_server
        token = _make_token()
        async with grpc.aio.insecure_channel(f"127.0.0.1:{port}") as channel:
            stub = gcp_functions_action_pb2_grpc.GCPFunctionsActionServiceStub(channel)
            request = gcp_functions_action_pb2.InvokeFunctionRequest(
                project="proj", region="us-central1", function_name="fn"
            )
            metadata = (("authorization", f"Bearer {token}"),)

            response = await stub.InvokeFunction(request, metadata=metadata)

            assert response.success is True
            assert response.status_code == 200
