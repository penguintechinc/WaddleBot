"""gRPC transport TLS for this module's standalone servicer.

Security audit finding A02 (Cryptographic Failures): this module's gRPC
server was bound with ``add_insecure_port`` -- inter-service RPC traffic
(including the service JWT validated by ``grpc_auth_interceptor.py``, see
security.md Service-to-Service Auth) crossed the network in plaintext.

This module is a standalone, independently-deployed package (its own
Dockerfile/requirements, not linked against ``libs/flask_core``), so it
carries its own copy of the same TLS-loading logic as
``flask_core.grpc_tls`` rather than importing it -- see that module's
docstring for the full design rationale (fail-closed, SPIFFE-ready,
dev-only insecure escape hatch). Keep the two in sync if either changes.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import grpc

logger = logging.getLogger(__name__)

_INSECURE_DEV_ENV = "GRPC_TLS_INSECURE_DEV"
DEFAULT_MAX_MESSAGE_BYTES = 4 * 1024 * 1024  # 4 MiB


class GrpcTlsConfigError(RuntimeError):
    """TLS is required for this call but certificate material is missing/invalid."""


def _running_under_pytest() -> bool:
    """True in any pytest worker process, so a bare test run isn't treated as production."""
    return "pytest" in sys.modules


def _is_production() -> bool:
    """Fail-safe posture check: production unless an explicit dev/test env name is set."""
    release_mode = os.environ.get("RELEASE_MODE")
    if release_mode is not None:
        return release_mode.strip().lower() != "false"
    env = (
        os.environ.get("WADDLEBOT_ENV")
        or os.environ.get("ENVIRONMENT")
        or os.environ.get("NODE_ENV")
        or ""
    ).strip().lower()
    return env not in {"development", "dev", "local", "test", "testing"}


def _read_pem(env_var: str) -> bytes:
    """Read the PEM file named by ``env_var``, raising with the env var name on failure."""
    path = os.getenv(env_var, "")
    if not path:
        raise GrpcTlsConfigError(f"{env_var} is not set")
    file_path = Path(path)
    try:
        return file_path.read_bytes()
    except OSError as exc:
        raise GrpcTlsConfigError(f"{env_var}={path!r} could not be read: {exc}") from exc


def _insecure_dev_allowed() -> bool:
    """Whether the dev-only plaintext fallback may be used in this process."""
    opted_in = os.getenv(_INSECURE_DEV_ENV, "false").strip().lower() == "true"
    if not opted_in:
        return False
    if not _running_under_pytest() and _is_production():
        logger.error(
            "%s=true is set but this process is in production posture; "
            "refusing the plaintext fallback",
            _INSECURE_DEV_ENV,
        )
        return False
    return True


def server_credentials() -> grpc.ServerCredentials | None:
    """Build server-side TLS credentials from env-configured cert/key paths.

    Reads ``GRPC_TLS_CERT_PATH``/``GRPC_TLS_KEY_PATH``. If
    ``GRPC_TLS_CA_PATH`` is also set, mutual TLS is enabled. Returns
    ``None`` only under the dev-only insecure fallback; otherwise raises
    :class:`GrpcTlsConfigError`.
    """
    cert_path = os.getenv("GRPC_TLS_CERT_PATH", "")
    key_path = os.getenv("GRPC_TLS_KEY_PATH", "")
    if not cert_path or not key_path:
        if _insecure_dev_allowed():
            logger.warning(
                "GRPC_TLS_CERT_PATH/GRPC_TLS_KEY_PATH not set and %s=true -- "
                "binding gRPC server WITHOUT TLS. Dev only, never production.",
                _INSECURE_DEV_ENV,
            )
            return None
        raise GrpcTlsConfigError(
            "GRPC_TLS_CERT_PATH and GRPC_TLS_KEY_PATH are required to bind a gRPC "
            f"server over TLS (or set {_INSECURE_DEV_ENV}=true for local dev only)"
        )

    private_key = _read_pem("GRPC_TLS_KEY_PATH")
    certificate_chain = _read_pem("GRPC_TLS_CERT_PATH")

    ca_path = os.getenv("GRPC_TLS_CA_PATH", "")
    if ca_path:
        root_certificates = _read_pem("GRPC_TLS_CA_PATH")
        require_client_auth = (
            os.getenv("GRPC_TLS_REQUIRE_CLIENT_CERT", "true").strip().lower() == "true"
        )
        return grpc.ssl_server_credentials(
            [(private_key, certificate_chain)],
            root_certificates=root_certificates,
            require_client_auth=require_client_auth,
        )

    return grpc.ssl_server_credentials([(private_key, certificate_chain)])


def bind_secure_port(server: grpc.aio.Server, address: str) -> None:
    """Bind ``server`` to ``address``, over TLS unless the dev fallback applies.

    Drop-in replacement for ``server.add_insecure_port(address)``. Raises
    ``RuntimeError`` if the port could not be bound.
    """
    credentials = server_credentials()
    bound = (
        server.add_insecure_port(address)
        if credentials is None
        else server.add_secure_port(address, credentials)
    )
    if bound == 0:
        raise RuntimeError(f"Unable to bind gRPC server to {address}")


def default_server_options() -> list[tuple[str, object]]:
    """Server ``options`` enforcing an explicit max message size in both directions."""
    max_bytes = int(os.getenv("GRPC_MAX_MESSAGE_BYTES", str(DEFAULT_MAX_MESSAGE_BYTES)))
    return [
        ("grpc.max_receive_message_length", max_bytes),
        ("grpc.max_send_message_length", max_bytes),
    ]
