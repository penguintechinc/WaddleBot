"""`services/url_guard.py` -- direct unit tests, DNS resolution mocked for hermeticity.

`socket.getaddrinfo` is monkeypatched throughout rather than relying on
real DNS -- a sandboxed/egress-filtered CI runner (security.md: "deny-by-
default outbound") may have no route to resolve an arbitrary hostname,
and a real lookup makes the suite non-deterministic regardless. Literal-
IP inputs (used elsewhere, e.g. `tests/test_v1_music_blueprint.py`) don't
need this since `validate_outbound_url` short-circuits before ever
calling the resolver for those.
"""

from __future__ import annotations

import socket

import pytest

from services.errors import ApiError
from services.url_guard import validate_outbound_url


def _fake_getaddrinfo(ip: str) -> object:
    def _inner(host: str, port: object) -> list[tuple]:
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 0))]

    return _inner


class TestSchemeAndHostValidation:
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


class TestLiteralIP:
    async def test_private_literal_ip_is_400(self) -> None:
        with pytest.raises(ApiError):
            await validate_outbound_url("http://10.0.0.5/x", allowed_schemes=("http", "https"))

    async def test_public_literal_ip_passes(self) -> None:
        result = await validate_outbound_url("http://8.8.8.8/x", allowed_schemes=("http", "https"))
        assert result == "http://8.8.8.8/x"


class TestDnsResolvedHostname:
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
