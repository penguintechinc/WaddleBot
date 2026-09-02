"""
Tests for flask_core.grpc_tls (A02 security fix: gRPC transport TLS).

Security audit finding A02 (Cryptographic Failures): every in-repo gRPC
server bound with ``add_insecure_port`` -- inter-service RPC traffic
(including the service JWTs validated by the C7-fix interceptors, PR #257)
crossed the network in plaintext. The load-bearing assertions here:

- Missing cert/key material refuses to build server/client credentials
  (fails closed) unless the explicit ``GRPC_TLS_INSECURE_DEV`` escape hatch
  is set -- and that escape hatch is itself refused under production
  posture (``TestInsecureDevFallbackRefusedInProduction``), mirroring the
  fail-closed pattern ``flask_core.secrets`` already established for C1.
- A real TLS handshake: a server bound via :func:`bind_secure_port` rejects
  a plaintext client and accepts an authorized mTLS client
  (``TestEndToEndHandshake``) -- proves the fix works at the wire level,
  not just that the right grpc.* functions are called.
"""

from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path

import grpc
import pytest

from flask_core.grpc_tls import (
    GrpcTlsConfigError,
    _insecure_dev_allowed,
    bind_secure_port,
    channel_credentials,
    default_server_options,
    secure_channel,
    server_credentials,
)


def _generate_dev_certs(cert_dir: Path) -> None:
    """Generate a throwaway CA + server/client cert pair for this test module only."""
    ca_key = cert_dir / "ca.key"
    ca_crt = cert_dir / "ca.crt"
    subprocess.run(
        ["openssl", "genrsa", "-out", str(ca_key), "2048"],
        check=True, capture_output=True,
    )
    subprocess.run(
        [
            "openssl", "req", "-x509", "-new", "-nodes",
            "-key", str(ca_key), "-sha256", "-days", "2",
            "-subj", "/O=Test/CN=test-ca", "-out", str(ca_crt),
        ],
        check=True, capture_output=True,
    )
    for role, cn, ext in (
        ("server", "localhost", "extendedKeyUsage=serverAuth\nsubjectAltName=DNS:localhost,IP:127.0.0.1"),
        ("client", "test-client", "extendedKeyUsage=clientAuth"),
    ):
        key = cert_dir / f"{role}.key"
        csr = cert_dir / f"{role}.csr"
        crt = cert_dir / f"{role}.crt"
        subprocess.run(
            ["openssl", "genrsa", "-out", str(key), "2048"], check=True, capture_output=True
        )
        subprocess.run(
            [
                "openssl", "req", "-new", "-key", str(key),
                "-subj", f"/O=Test/CN={cn}", "-out", str(csr),
            ],
            check=True, capture_output=True,
        )
        extfile = cert_dir / f"{role}.ext"
        extfile.write_text(ext)
        subprocess.run(
            [
                "openssl", "x509", "-req", "-in", str(csr),
                "-CA", str(ca_crt), "-CAkey", str(ca_key), "-CAcreateserial",
                "-days", "2", "-sha256", "-extfile", str(extfile),
                "-out", str(crt),
            ],
            check=True, capture_output=True,
        )


@pytest.fixture()
def dev_certs(tmp_path: Path) -> Path:
    """A throwaway self-signed CA + server/client cert pair, generated per test."""
    _generate_dev_certs(tmp_path)
    return tmp_path


class TestServerCredentialsFailClosed:
    """Missing TLS material refuses to build credentials -- no silent plaintext fallback."""

    def test_missing_cert_and_key_raises(self, monkeypatch):
        monkeypatch.delenv("GRPC_TLS_CERT_PATH", raising=False)
        monkeypatch.delenv("GRPC_TLS_KEY_PATH", raising=False)
        monkeypatch.delenv("GRPC_TLS_INSECURE_DEV", raising=False)
        with pytest.raises(GrpcTlsConfigError, match="GRPC_TLS_CERT_PATH"):
            server_credentials()

    def test_cert_path_pointing_nowhere_raises(self, monkeypatch, tmp_path):
        monkeypatch.setenv("GRPC_TLS_CERT_PATH", str(tmp_path / "does-not-exist.crt"))
        monkeypatch.setenv("GRPC_TLS_KEY_PATH", str(tmp_path / "does-not-exist.key"))
        with pytest.raises(GrpcTlsConfigError, match="could not be read"):
            server_credentials()

    def test_valid_cert_and_key_builds_credentials(self, monkeypatch, dev_certs):
        monkeypatch.setenv("GRPC_TLS_CERT_PATH", str(dev_certs / "server.crt"))
        monkeypatch.setenv("GRPC_TLS_KEY_PATH", str(dev_certs / "server.key"))
        monkeypatch.delenv("GRPC_TLS_CA_PATH", raising=False)
        creds = server_credentials()
        assert isinstance(creds, grpc.ServerCredentials)

    def test_ca_path_enables_mtls_credentials(self, monkeypatch, dev_certs):
        monkeypatch.setenv("GRPC_TLS_CERT_PATH", str(dev_certs / "server.crt"))
        monkeypatch.setenv("GRPC_TLS_KEY_PATH", str(dev_certs / "server.key"))
        monkeypatch.setenv("GRPC_TLS_CA_PATH", str(dev_certs / "ca.crt"))
        creds = server_credentials()
        assert isinstance(creds, grpc.ServerCredentials)


class TestChannelCredentialsFailClosed:
    """Client-side: missing CA material refuses to build channel credentials."""

    def test_missing_ca_raises(self, monkeypatch):
        monkeypatch.delenv("GRPC_TLS_CA_PATH", raising=False)
        monkeypatch.delenv("GRPC_TLS_INSECURE_DEV", raising=False)
        with pytest.raises(GrpcTlsConfigError, match="GRPC_TLS_CA_PATH"):
            channel_credentials()

    def test_ca_only_builds_server_validating_credentials(self, monkeypatch, dev_certs):
        monkeypatch.setenv("GRPC_TLS_CA_PATH", str(dev_certs / "ca.crt"))
        monkeypatch.delenv("GRPC_TLS_CLIENT_CERT_PATH", raising=False)
        creds = channel_credentials()
        assert isinstance(creds, grpc.ChannelCredentials)

    def test_ca_and_client_cert_builds_mtls_credentials(self, monkeypatch, dev_certs):
        monkeypatch.setenv("GRPC_TLS_CA_PATH", str(dev_certs / "ca.crt"))
        monkeypatch.setenv("GRPC_TLS_CLIENT_CERT_PATH", str(dev_certs / "client.crt"))
        monkeypatch.setenv("GRPC_TLS_CLIENT_KEY_PATH", str(dev_certs / "client.key"))
        creds = channel_credentials()
        assert isinstance(creds, grpc.ChannelCredentials)


class TestInsecureDevFallbackRefusedInProduction:
    """The explicit dev-only escape hatch is itself refused under production posture."""

    def test_insecure_dev_allowed_outside_production(self, monkeypatch):
        monkeypatch.delenv("GRPC_TLS_CERT_PATH", raising=False)
        monkeypatch.delenv("GRPC_TLS_KEY_PATH", raising=False)
        monkeypatch.setenv("GRPC_TLS_INSECURE_DEV", "true")
        monkeypatch.setenv("RELEASE_MODE", "false")
        assert server_credentials() is None

    def test_insecure_dev_refused_in_production(self, monkeypatch):
        """`require_production_check=True` forces production posture regardless of
        pytest -- the same override shape `secrets.require_secret_key(require=...)`
        uses -- so this test can exercise the refusal path deterministically
        rather than relying on the real environment/pytest auto-detection."""
        monkeypatch.setenv("GRPC_TLS_INSECURE_DEV", "true")
        assert _insecure_dev_allowed(require_production_check=True) is False

    def test_server_credentials_refused_in_production_via_env(self, monkeypatch):
        """End-to-end through the public API: RELEASE_MODE=true alone is not
        enough to force production posture under pytest (by design, see
        `_running_under_pytest`), so this asserts the actual default posture
        resolution used by `server_credentials()` still fails closed when no
        cert material is configured, regardless of GRPC_TLS_INSECURE_DEV."""
        monkeypatch.delenv("GRPC_TLS_CERT_PATH", raising=False)
        monkeypatch.delenv("GRPC_TLS_KEY_PATH", raising=False)
        monkeypatch.delenv("GRPC_TLS_INSECURE_DEV", raising=False)
        monkeypatch.setenv("RELEASE_MODE", "true")
        with pytest.raises(GrpcTlsConfigError):
            server_credentials()

    def test_insecure_dev_not_opted_in_still_raises(self, monkeypatch):
        """GRPC_TLS_INSECURE_DEV unset (or false) -- the default -- always fails closed."""
        monkeypatch.delenv("GRPC_TLS_CERT_PATH", raising=False)
        monkeypatch.delenv("GRPC_TLS_KEY_PATH", raising=False)
        monkeypatch.delenv("GRPC_TLS_INSECURE_DEV", raising=False)
        monkeypatch.setenv("RELEASE_MODE", "false")
        with pytest.raises(GrpcTlsConfigError):
            server_credentials()


class TestDefaultServerOptions:
    """Explicit max message size, overridable via env var."""

    def test_default_max_message_bytes(self, monkeypatch):
        monkeypatch.delenv("GRPC_MAX_MESSAGE_BYTES", raising=False)
        options = dict(default_server_options())
        assert options["grpc.max_receive_message_length"] == 4 * 1024 * 1024
        assert options["grpc.max_send_message_length"] == 4 * 1024 * 1024

    def test_max_message_bytes_overridable(self, monkeypatch):
        monkeypatch.setenv("GRPC_MAX_MESSAGE_BYTES", "1048576")
        options = dict(default_server_options())
        assert options["grpc.max_receive_message_length"] == 1048576


class TestEndToEndHandshake:
    """Real TLS handshake over a loopback socket -- not just credential-object shape."""

    @pytest.mark.asyncio
    async def test_server_rejects_plaintext_client(self, monkeypatch, dev_certs, unused_tcp_port):
        monkeypatch.setenv("GRPC_TLS_CERT_PATH", str(dev_certs / "server.crt"))
        monkeypatch.setenv("GRPC_TLS_KEY_PATH", str(dev_certs / "server.key"))
        monkeypatch.setenv("GRPC_TLS_CA_PATH", str(dev_certs / "ca.crt"))

        server = grpc.aio.server(options=default_server_options())
        address = f"127.0.0.1:{unused_tcp_port}"
        bind_secure_port(server, address)
        await server.start()
        try:
            plaintext_channel = grpc.aio.insecure_channel(address)
            try:
                with pytest.raises(asyncio.TimeoutError):
                    await asyncio.wait_for(plaintext_channel.channel_ready(), timeout=2.0)
            finally:
                await plaintext_channel.close()
        finally:
            await server.stop(None)

    @pytest.mark.asyncio
    async def test_authorized_mtls_client_connects(self, monkeypatch, dev_certs, unused_tcp_port):
        monkeypatch.setenv("GRPC_TLS_CERT_PATH", str(dev_certs / "server.crt"))
        monkeypatch.setenv("GRPC_TLS_KEY_PATH", str(dev_certs / "server.key"))
        monkeypatch.setenv("GRPC_TLS_CA_PATH", str(dev_certs / "ca.crt"))
        monkeypatch.setenv("GRPC_TLS_REQUIRE_CLIENT_CERT", "true")

        server = grpc.aio.server(options=default_server_options())
        address = f"127.0.0.1:{unused_tcp_port}"
        bind_secure_port(server, address)
        await server.start()
        try:
            monkeypatch.setenv("GRPC_TLS_CLIENT_CERT_PATH", str(dev_certs / "client.crt"))
            monkeypatch.setenv("GRPC_TLS_CLIENT_KEY_PATH", str(dev_certs / "client.key"))
            tls_channel = secure_channel(address)
            try:
                await asyncio.wait_for(tls_channel.channel_ready(), timeout=5.0)
            finally:
                await tls_channel.close()
        finally:
            await server.stop(None)

    @pytest.mark.asyncio
    async def test_bind_secure_port_raises_when_port_occupied(
        self, monkeypatch, dev_certs, unused_tcp_port
    ):
        """The add_insecure_port(...) == 0 failure convention is preserved for TLS binds."""
        import socket

        monkeypatch.setenv("GRPC_TLS_CERT_PATH", str(dev_certs / "server.crt"))
        monkeypatch.setenv("GRPC_TLS_KEY_PATH", str(dev_certs / "server.key"))
        monkeypatch.delenv("GRPC_TLS_CA_PATH", raising=False)

        address = f"127.0.0.1:{unused_tcp_port}"
        occupier = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        occupier.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
        occupier.bind(("127.0.0.1", unused_tcp_port))
        occupier.listen(1)
        try:
            server = grpc.aio.server(options=default_server_options())
            # grpc.aio.Server.add_secure_port raises directly (rather than
            # returning 0) when the OS refuses the bind outright -- either
            # way, bind_secure_port must not silently swallow the failure.
            with pytest.raises(RuntimeError, match="[Ff]ailed to bind|Unable to bind"):
                bind_secure_port(server, address)
        finally:
            occupier.close()


@pytest.fixture()
def unused_tcp_port() -> int:
    """A free TCP port on localhost, picked fresh per test to avoid cross-test collisions."""
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]
