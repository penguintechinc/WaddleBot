"""SSRF guard tests -- `services/url_guard.py` (copy of hub_api/tests/test_url_guard.py).

Same coverage as hub_api's own suite (this module is a verbatim copy of
hub_api's SSRF logic, see url_guard.py's module docstring) plus
`TestGuardedRequestRedirects`, covering the POST-capable `guarded_request`
helper svc-action's adapters actually call.

Fail-first proof (executed, not narrated): temporarily replaced
`is_private_host` with a stub returning `False` unconditionally, ran this
file -- every `TestIsPrivateHost*`/`TestValidateUrl`/`TestGuardedRequestRedirects`
private-target case went from raising `SSRFError` to silently passing
(red). Reverted; full suite green again. See PR description for the
before/after `pytest -k` output.
"""

from __future__ import annotations

import socket
from typing import Any

import httpx
import pytest

from services.errors import ApiError
from services.url_guard import (
    SSRFError,
    guarded_get,
    guarded_request,
    is_private_host,
    validate_outbound_url,
    validate_url,
)


class TestIsPrivateHostLiteralIPs:
    """Literal IPs never touch DNS -- fast, deterministic, no mocking needed."""

    @pytest.mark.parametrize(
        "host",
        [
            "127.0.0.1",  # loopback
            "169.254.169.254",  # cloud metadata (AWS/GCP/Azure IMDS)
            "10.1.2.3",  # RFC 1918
            "172.16.5.5",  # RFC 1918
            "192.168.1.1",  # RFC 1918
            "0.0.0.0",  # noqa: S104 - unspecified/"this network", a guard *input*, not a bind address
            "0.5.5.5",  # 0.0.0.0/8
            "224.0.0.1",  # multicast
            "::1",  # IPv6 loopback
            "fe80::1",  # IPv6 link-local
            "fc00::1",  # IPv6 ULA
            "::ffff:127.0.0.1",  # IPv4-mapped IPv6 loopback (classic filter bypass)
            "::ffff:169.254.169.254",  # IPv4-mapped IPv6 metadata address
        ],
    )
    def test_rejects_disallowed_literal_ip(self, host: str) -> None:
        assert is_private_host(host) is True

    @pytest.mark.parametrize("host", ["8.8.8.8", "1.1.1.1", "2001:4860:4860::8888"])
    def test_allows_public_literal_ip(self, host: str) -> None:
        assert is_private_host(host) is False


class TestIsPrivateHostResolvedHostnames:
    """Hostname resolution mocked via `socket.getaddrinfo` -- no real DNS."""

    @staticmethod
    def _fake_getaddrinfo(ip: str) -> Any:
        def _fake(host: str, port: Any, *args: Any, **kwargs: Any) -> list[Any]:
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 0))]

        return _fake

    def test_hostname_resolving_to_private_ip_is_rejected(self, monkeypatch: Any) -> None:
        """DNS-rebind scenario: a hostname that resolves to an internal address."""
        monkeypatch.setattr(socket, "getaddrinfo", self._fake_getaddrinfo("169.254.169.254"))
        assert is_private_host("attacker-controlled.example") is True

    def test_hostname_resolving_to_public_ip_is_allowed(self, monkeypatch: Any) -> None:
        monkeypatch.setattr(socket, "getaddrinfo", self._fake_getaddrinfo("93.184.216.34"))
        assert is_private_host("docs.example.com") is False

    def test_unresolvable_hostname_is_rejected(self, monkeypatch: Any) -> None:
        """Fail closed: a hostname that doesn't resolve at all is never allowed through."""

        def _raise(*args: Any, **kwargs: Any) -> Any:
            raise socket.gaierror("Name or service not known")

        monkeypatch.setattr(socket, "getaddrinfo", _raise)
        assert is_private_host("nonexistent.invalid") is True


class TestValidateUrl:
    def test_rejects_file_scheme(self) -> None:
        with pytest.raises(SSRFError):
            validate_url("file:///etc/passwd")

    def test_rejects_gopher_scheme(self) -> None:
        with pytest.raises(SSRFError):
            validate_url("gopher://127.0.0.1/x")

    def test_rejects_loopback_target(self) -> None:
        with pytest.raises(SSRFError):
            validate_url("http://127.0.0.1/admin")

    def test_rejects_cloud_metadata_target(self) -> None:
        with pytest.raises(SSRFError):
            validate_url("http://169.254.169.254/latest/meta-data/")

    def test_rejects_private_10_range_target(self) -> None:
        with pytest.raises(SSRFError):
            validate_url("http://10.0.5.5/internal")

    def test_rejects_private_192_168_range_target(self) -> None:
        with pytest.raises(SSRFError):
            validate_url("http://192.168.1.1/router")

    def test_allows_normal_public_url(self) -> None:
        """A genuinely public target (literal IP -- no real DNS needed) passes."""
        validate_url("https://8.8.8.8/docs")  # must not raise

    def test_rejects_url_with_no_host(self) -> None:
        with pytest.raises(SSRFError):
            validate_url("http:///no-host")


class TestGuardedGetRedirects:
    """`guarded_get` re-validates every redirect hop against a mocked transport."""

    async def test_direct_public_response_returned(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, text="ok")

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), follow_redirects=False
        ) as client:
            response = await guarded_get(client, "https://8.8.8.8/docs")
        assert response.status_code == 200

    async def test_redirect_to_internal_target_is_blocked(self) -> None:
        """The exact attack the review flagged: a public URL 302s to an internal host."""

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                302, headers={"Location": "http://169.254.169.254/latest/meta-data/"}
            )

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), follow_redirects=False
        ) as client:
            with pytest.raises(SSRFError):
                await guarded_get(client, "https://8.8.8.8/start")


class TestGuardedRequestRedirects:
    """`guarded_request` (POST-capable) -- svc-action's adapters call this, not `guarded_get`."""

    async def test_initial_private_target_is_blocked_before_any_request(self) -> None:
        """The fail-first-verify case: a webhook/rest_api target pointed at a private host."""
        called = False

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal called
            called = True
            return httpx.Response(200)

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), follow_redirects=False
        ) as client:
            with pytest.raises(SSRFError):
                await guarded_request(
                    client, "POST", "http://169.254.169.254/latest/meta-data/", content=b"{}"
                )
        assert called is False  # guard rejects before the request is ever sent

    async def test_direct_public_post_is_sent(self) -> None:
        received: list[bytes] = []

        def handler(request: httpx.Request) -> httpx.Response:
            received.append(request.content)
            return httpx.Response(200, text="ok")

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), follow_redirects=False
        ) as client:
            response = await guarded_request(
                client, "POST", "https://8.8.8.8/hook", content=b'{"x":1}'
            )
        assert response.status_code == 200
        assert received == [b'{"x":1}']

    async def test_redirect_to_internal_target_is_blocked(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(302, headers={"Location": "http://127.0.0.1/pwn"})

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), follow_redirects=False
        ) as client:
            with pytest.raises(SSRFError):
                await guarded_request(client, "POST", "https://8.8.8.8/start", content=b"{}")

    async def test_excessive_redirect_chain_is_blocked(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            n = int(request.url.path.rsplit("/", 1)[-1] or 0)
            return httpx.Response(302, headers={"Location": f"https://8.8.8.8/hop/{n + 1}"})

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), follow_redirects=False
        ) as client:
            with pytest.raises(SSRFError):
                await guarded_request(client, "POST", "https://8.8.8.8/hop/0", content=b"{}")


def _fake_getaddrinfo(ip: str) -> object:
    def _inner(host: str, port: object) -> list[tuple]:
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 0))]

    return _inner


class TestValidateOutboundUrlSchemeAndHostValidation:
    async def test_disallowed_scheme_is_400(self) -> None:
        with pytest.raises(ApiError) as exc_info:
            await validate_outbound_url("ftp://example.com/x", allowed_schemes=("http", "https"))
        assert exc_info.value.status_code == 400

    async def test_missing_host_is_400(self) -> None:
        with pytest.raises(ApiError):
            await validate_outbound_url("https:///no-host", allowed_schemes=("http", "https"))

    async def test_blocked_literal_hostname_is_400(self) -> None:
        with pytest.raises(ApiError) as exc_info:
            await validate_outbound_url("http://localhost/admin", allowed_schemes=("http", "https"))
        assert "not allowed" in exc_info.value.message


class TestValidateOutboundUrlLiteralIP:
    async def test_private_literal_ip_is_400(self) -> None:
        with pytest.raises(ApiError):
            await validate_outbound_url("http://10.0.0.5/x", allowed_schemes=("http", "https"))

    async def test_public_literal_ip_passes(self) -> None:
        result = await validate_outbound_url("http://8.8.8.8/x", allowed_schemes=("http", "https"))
        assert result == "http://8.8.8.8/x"


class TestValidateOutboundUrlDnsResolvedHostname:
    async def test_hostname_resolving_to_public_ip_passes(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo("93.184.216.34"))
        result = await validate_outbound_url("https://public.example/x", allowed_schemes=("https",))
        assert result == "https://public.example/x"

    async def test_hostname_resolving_to_private_ip_is_400(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo("169.254.169.254"))
        with pytest.raises(ApiError) as exc_info:
            await validate_outbound_url(
                "https://metadata-lookalike.internal/x", allowed_schemes=("https",)
            )
        assert exc_info.value.status_code == 400

    async def test_unresolvable_hostname_is_400(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def _raise(host: str, port: object) -> list[tuple]:
            raise OSError("name or service not known")

        monkeypatch.setattr(socket, "getaddrinfo", _raise)
        with pytest.raises(ApiError) as exc_info:
            await validate_outbound_url(
                "https://no-such-host.invalid/x", allowed_schemes=("https",)
            )
        assert exc_info.value.status_code == 400
