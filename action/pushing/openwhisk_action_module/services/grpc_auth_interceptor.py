"""gRPC server-side authentication interceptor.

Validates the short-lived, HS256-signed service JWT carried in the
``authorization`` gRPC metadata header on every unary RPC before it reaches
the servicer, and rejects unauthenticated or unauthorized calls outright.
This is the primary defense against destructive action RPCs (e.g.
InvokeFunction) being callable by anyone who can reach the port -- see
security.md Service-to-Service Auth.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

import grpc
import jwt

from config import Config

logger = logging.getLogger(__name__)


def verify_service_token(
    metadata: dict[str, str | bytes],
) -> tuple[bool, dict[str, Any] | None, str]:
    """Validate the bearer JWT carried in gRPC invocation metadata.

    Returns an ``(is_valid, claims, error_message)`` tuple. ``claims`` is
    populated only once signature and expiry checks pass; the caller is
    still responsible for authorizing the decoded ``service`` claim via
    :func:`authorize_service`.
    """
    raw_header = metadata.get("authorization", "")
    auth_header = (
        raw_header.decode("utf-8", errors="replace")
        if isinstance(raw_header, bytes)
        else raw_header
    )
    if not auth_header.lower().startswith("bearer "):
        return False, None, "Missing bearer token"

    token = auth_header[7:].strip()
    if not token:
        return False, None, "Missing bearer token"

    if not Config.MODULE_SECRET_KEY:
        logger.error("MODULE_SECRET_KEY is not configured; rejecting all RPCs")
        return False, None, "Server misconfigured"

    try:
        claims = jwt.decode(
            token, Config.MODULE_SECRET_KEY, algorithms=[Config.JWT_ALGORITHM]
        )
    except jwt.ExpiredSignatureError:
        return False, None, "Token expired"
    except jwt.InvalidTokenError as exc:
        return False, None, f"Invalid token: {exc}"

    return True, claims, ""


def authorize_service(claims: dict[str, Any]) -> tuple[bool, str]:
    """Check the token's ``service`` claim against the configured allowlist."""
    service = claims.get("service")
    if not service:
        return False, "Token is missing a service claim"
    if service not in Config.ALLOWED_SERVICES:
        return False, f"Service '{service}' is not authorized to call this module"
    return True, ""


class AuthInterceptor(grpc.aio.ServerInterceptor):
    """Rejects RPCs that lack a valid, authorized service-to-service JWT."""

    async def intercept_service(
        self,
        continuation: Callable[
            [grpc.HandlerCallDetails], Awaitable[grpc.RpcMethodHandler[Any, Any] | None]
        ],
        handler_call_details: grpc.HandlerCallDetails,
    ) -> grpc.RpcMethodHandler[Any, Any] | None:
        """Validate the caller's JWT before handing the call to its handler."""
        metadata: dict[str, str | bytes] = dict(
            handler_call_details.invocation_metadata or ()
        )

        valid, claims, error = verify_service_token(metadata)
        if not valid or claims is None:
            logger.warning(
                "Rejected unauthenticated RPC %s: %s",
                handler_call_details.method,
                error,
            )
            return _deny(grpc.StatusCode.UNAUTHENTICATED, error)

        authorized, auth_error = authorize_service(claims)
        if not authorized:
            logger.warning(
                "Rejected unauthorized RPC %s: %s",
                handler_call_details.method,
                auth_error,
            )
            return _deny(grpc.StatusCode.PERMISSION_DENIED, auth_error)

        return await continuation(handler_call_details)


async def require_auth(context: grpc.aio.ServicerContext[Any, Any]) -> dict[str, Any]:
    """Validate the caller's bearer JWT or abort the RPC.

    Call as the first line of every RPC method on a servicer whose server is
    not (yet) constructed with ``interceptors=[AuthInterceptor()]``, so
    authentication is enforced at the method level regardless of how the
    servicer ends up wired to a transport. Returns the decoded claims on
    success; aborts (raising) on failure.
    """
    metadata: dict[str, str | bytes] = dict(context.invocation_metadata() or ())

    valid, claims, error = verify_service_token(metadata)
    if not valid or claims is None:
        await context.abort(grpc.StatusCode.UNAUTHENTICATED, error)

    authorized, auth_error = authorize_service(claims)
    if not authorized:
        await context.abort(grpc.StatusCode.PERMISSION_DENIED, auth_error)

    return claims


def _deny(code: grpc.StatusCode, details: str) -> grpc.RpcMethodHandler[Any, Any]:
    """Build a unary-unary handler that immediately aborts with ``code``.

    Every RPC exposed by this service is unary-unary, so a single handler
    shape is sufficient to short-circuit denied calls before they reach the
    real servicer.
    """

    async def _reject(request: Any, context: grpc.aio.ServicerContext[Any, Any]) -> Any:
        await context.abort(code, details)

    return grpc.unary_unary_rpc_method_handler(_reject)
