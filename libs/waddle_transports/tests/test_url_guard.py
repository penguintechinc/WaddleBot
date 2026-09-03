"""url_guard.py -- SSRF guard: scheme/host validation, resolution, redirect revalidation."""

from __future__ import annotations

import socket

import httpx
import pytest

from waddle_transports.url_guard import SSRFError, guarded_request, is_private_host, validate_url


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
