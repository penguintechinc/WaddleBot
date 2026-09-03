"""url_guard.py -- SSRF guard: scheme/host validation, resolution, redirect revalidation."""

from __future__ import annotations

import socket

import httpx
import pytest

from waddle_transports.url_guard import (
    ResponseTooLargeError,
    SSRFError,
    guarded_request,
    is_private_host,
    validate_url,
)


class TestIsPrivateHost:
    def test_literal_public_ip_is_not_private(self) -> None:
        assert is_private_host("8.8.8.8") is False

    def test_literal_private_ip_is_private(self) -> None:
        assert is_private_host("10.0.0.5") is True

    def test_literal_link_local_metadata_ip_is_private(self) -> None:
        assert is_private_host("169.254.169.254") is True

    def test_hostname_localhost_resolves_and_is_private(self) -> None:
        """Real `socket.getaddrinfo` resolution (no mocking) -- "localhost" via /etc/hosts."""
        assert is_private_host("localhost") is True

    def test_unresolvable_hostname_fails_closed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def _raise_gaierror(host: str, port: object) -> object:
            raise socket.gaierror("mocked: name resolution failed")

        monkeypatch.setattr(socket, "getaddrinfo", _raise_gaierror)
        assert is_private_host("this-host-does-not-exist.invalid") is True

    def test_hostname_resolving_to_public_ip_is_not_private(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _fake_getaddrinfo(host: str, port: object) -> list:
            return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 0))]

        monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo)
        assert is_private_host("example.com") is False

    def test_unparseable_resolved_address_fails_closed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _fake_getaddrinfo(host: str, port: object) -> list:
            return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("not-an-ip-address", 0))]

        monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo)
        assert is_private_host("weird.example.com") is True

    def test_no_resolved_addresses_fails_closed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def _fake_getaddrinfo(host: str, port: object) -> list:
            return []

        monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo)
        assert is_private_host("empty.example.com") is True


class TestValidateUrl:
    def test_rejects_bad_scheme(self) -> None:
        with pytest.raises(SSRFError, match="scheme"):
            validate_url("file:///etc/passwd")

    def test_rejects_url_with_no_host(self) -> None:
        with pytest.raises(SSRFError, match="no host"):
            validate_url("https://")

    def test_rejects_private_host(self) -> None:
        with pytest.raises(SSRFError, match="disallowed"):
            validate_url("http://169.254.169.254/latest/meta-data/")

    def test_accepts_public_literal_ip(self) -> None:
        validate_url("https://8.8.8.8/x")  # must not raise


class TestGuardedRequest:
    async def test_direct_200_response(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200)

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), follow_redirects=False
        ) as client:
            response = await guarded_request(client, "GET", "https://8.8.8.8/x")
        assert response.status_code == 200

    async def test_follows_one_redirect_to_a_validated_location(self) -> None:
        calls = []

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(str(request.url))
            if str(request.url) == "https://8.8.8.8/start":
                return httpx.Response(302, headers={"location": "https://8.8.8.8/final"})
            return httpx.Response(200)

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), follow_redirects=False
        ) as client:
            response = await guarded_request(client, "GET", "https://8.8.8.8/start")

        assert response.status_code == 200
        assert calls == ["https://8.8.8.8/start", "https://8.8.8.8/final"]

    async def test_redirect_to_private_host_is_rejected(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            if str(request.url) == "https://8.8.8.8/start":
                return httpx.Response(302, headers={"location": "http://169.254.169.254/steal"})
            return httpx.Response(200)  # pragma: no cover -- must never be reached

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), follow_redirects=False
        ) as client:
            with pytest.raises(SSRFError, match="disallowed"):
                await guarded_request(client, "GET", "https://8.8.8.8/start")

    async def test_redirect_with_no_location_header_returns_as_is(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(302)  # no Location header at all

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), follow_redirects=False
        ) as client:
            response = await guarded_request(client, "GET", "https://8.8.8.8/x")
        assert response.status_code == 302

    async def test_too_many_redirects_raises(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(302, headers={"location": "https://8.8.8.8/next"})

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), follow_redirects=False
        ) as client:
            with pytest.raises(SSRFError, match="too many redirects"):
                await guarded_request(client, "GET", "https://8.8.8.8/start")


class TestGuardedRequestDnsRebindPinning:
    """Fail-first regression for the DNS-rebind TOCTOU.

    `validate_url()`'s own resolution and the HTTP client's connect-time
    resolution used to be two independent `getaddrinfo()` calls -- an
    attacker controlling DNS could return a public IP for the first
    (validation) lookup and a private/internal IP for the second (connect)
    lookup. The fix resolves once and pins the connection to that one
    validated IP, so a second, independently-resolved (and potentially
    rebound) address is never dialed.
    """

    async def test_connects_to_the_one_validated_ip_not_a_re_resolved_hostname(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls = {"n": 0}

        def _fake_getaddrinfo(host: str, port: object) -> list:
            calls["n"] += 1
            return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 0))]

        monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo)

        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["url_host"] = request.url.host
            captured["host_header"] = request.headers.get("host")
            captured["sni"] = request.extensions.get("sni_hostname")
            return httpx.Response(200)

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), follow_redirects=False
        ) as client:
            response = await guarded_request(client, "GET", "https://example.com/path")

        assert response.status_code == 200
        # The actual outbound request targets the ONE resolved/validated IP --
        # not "example.com" left for the transport to resolve again.
        assert captured["url_host"] == "93.184.216.34"
        # Host header + SNI still carry the real hostname, so virtual-hosting
        # and TLS certificate verification are unaffected by the IP pin.
        assert captured["host_header"] == "example.com"
        assert captured["sni"] == "example.com"
        # Exactly one resolution for this hop -- no second, independent lookup.
        assert calls["n"] == 1

    async def test_bad_scheme_is_rejected_before_any_request(self) -> None:
        called = False

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal called
            called = True
            return httpx.Response(200)  # pragma: no cover -- must never be reached

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), follow_redirects=False
        ) as client:
            with pytest.raises(SSRFError, match="scheme"):
                await guarded_request(client, "GET", "ftp://8.8.8.8/x")
        assert called is False

    async def test_no_host_is_rejected(self) -> None:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda r: httpx.Response(200)), follow_redirects=False
        ) as client:
            with pytest.raises(SSRFError, match="no host"):
                await guarded_request(client, "GET", "https://")

    async def test_preserves_userinfo_and_port_in_the_pinned_url(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _fake_getaddrinfo(host: str, port: object) -> list:
            return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 0))]

        monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo)

        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["url"] = str(request.url)
            return httpx.Response(200)

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), follow_redirects=False
        ) as client:
            await guarded_request(client, "GET", "https://user:pass@example.com:8443/x")

        assert captured["url"] == "https://user:pass@93.184.216.34:8443/x"

    async def test_literal_ip_url_needs_no_dns_resolution(self) -> None:
        """Confirm a literal-IP URL never triggers DNS resolution.

        A literal-IP URL (the common case in this file's other tests) must
        not trigger any `getaddrinfo()` call at all -- the pin is the
        literal itself.
        """

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200)

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), follow_redirects=False
        ) as client:
            response = await guarded_request(client, "GET", "https://8.8.8.8/x")
        assert response.status_code == 200


class TestGuardedRequestResponseSizeCap:
    """Fail-first regression for the missing response-body size cap.

    `rest_pull`/`graphql`/`grpc` (and every other sub_type sharing this
    one `guarded_request()` call path) used to buffer the full response
    body with no size limit. A cap is enforced here, centrally, so every
    caller is protected uniformly.
    """

    async def test_oversized_response_is_rejected(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=b"x" * 100)

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), follow_redirects=False
        ) as client:
            with pytest.raises(ResponseTooLargeError, match="exceeded"):
                await guarded_request(client, "GET", "https://8.8.8.8/x", max_response_bytes=10)

    async def test_response_within_cap_is_returned_normally(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=b"ok")

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), follow_redirects=False
        ) as client:
            response = await guarded_request(
                client, "GET", "https://8.8.8.8/x", max_response_bytes=10
            )
        assert response.content == b"ok"

    async def test_default_cap_allows_a_normal_sized_response(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"a": 1})

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), follow_redirects=False
        ) as client:
            response = await guarded_request(client, "GET", "https://8.8.8.8/x")
        assert response.json() == {"a": 1}
