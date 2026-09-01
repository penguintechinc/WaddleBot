"""SSRF guard tests -- the trust boundary for `source_url`/`forward_url`.

Uses literal IPs (never a real DNS lookup) so these tests are
deterministic and offline -- `is_private`/`is_loopback`/etc. are stdlib
`ipaddress` properties, no network I/O involved for the literal-IP path.
"""

from __future__ import annotations

import socket

import pytest

from services import url_guard
from services.errors import ApiError
from services.url_guard import validate_outbound_url


@pytest.mark.asyncio
async def test_accepts_public_literal_ip() -> None:
    result = await validate_outbound_url("rtmp://8.8.8.8/live/key", allowed_schemes=("rtmp",))
    assert result == "rtmp://8.8.8.8/live/key"


@pytest.mark.asyncio
async def test_rejects_loopback_literal_ip() -> None:
    with pytest.raises(ApiError) as exc_info:
        await validate_outbound_url("rtmp://127.0.0.1/live/key", allowed_schemes=("rtmp",))
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_rejects_private_rfc1918_ip() -> None:
    with pytest.raises(ApiError):
        await validate_outbound_url("rtmp://10.0.0.5/live/key", allowed_schemes=("rtmp",))


@pytest.mark.asyncio
async def test_rejects_link_local_metadata_ip() -> None:
    """169.254.169.254 -- the classic cloud-metadata SSRF target."""
    with pytest.raises(ApiError):
        await validate_outbound_url("rtmp://169.254.169.254/latest", allowed_schemes=("rtmp",))


@pytest.mark.asyncio
async def test_rejects_blocked_literal_hostname() -> None:
    with pytest.raises(ApiError):
        await validate_outbound_url("rtmp://localhost/live/key", allowed_schemes=("rtmp",))


@pytest.mark.asyncio
async def test_rejects_disallowed_scheme() -> None:
    with pytest.raises(ApiError):
        await validate_outbound_url(
            "http://example.com/live/key", allowed_schemes=("rtmp", "rtmps")
        )


@pytest.mark.asyncio
async def test_rejects_url_with_no_host() -> None:
    with pytest.raises(ApiError):
        await validate_outbound_url("rtmp:///live/key", allowed_schemes=("rtmp",))


@pytest.mark.asyncio
async def test_rejects_unresolvable_hostname() -> None:
    with pytest.raises(ApiError):
        await validate_outbound_url(
            "rtmp://this-host-does-not-exist.invalid/live/key", allowed_schemes=("rtmp",)
        )


@pytest.mark.asyncio
async def test_accepts_rtmps_scheme() -> None:
    result = await validate_outbound_url(
        "rtmps://8.8.8.8/live/key", allowed_schemes=("rtmp", "rtmps")
    )
    assert result == "rtmps://8.8.8.8/live/key"


# ---------------------------------------------------------------------------
# Hostname resolution path -- `socket.getaddrinfo` mocked for determinism,
# never a real DNS lookup for these specific assertions.
# ---------------------------------------------------------------------------


def _fake_addrinfo(ip: str) -> list[tuple[object, ...]]:
    """One `getaddrinfo()`-shaped result tuple carrying `ip` at index 4[0]."""
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 0))]


def test_resolve_and_check_sync_passes_for_hostname_resolving_public(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(socket, "getaddrinfo", lambda host, port: _fake_addrinfo("93.184.216.34"))
    url_guard._resolve_and_check_sync("public.example.com")  # must not raise


def test_resolve_and_check_sync_rejects_hostname_resolving_private(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(socket, "getaddrinfo", lambda host, port: _fake_addrinfo("10.1.2.3"))
    with pytest.raises(ApiError) as exc_info:
        url_guard._resolve_and_check_sync("sneaky-internal.example.com")
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_validate_outbound_url_accepts_hostname_resolving_to_public_ip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(socket, "getaddrinfo", lambda host, port: _fake_addrinfo("93.184.216.34"))
    result = await validate_outbound_url(
        "rtmp://public.example.com/live/key", allowed_schemes=("rtmp",)
    )
    assert result == "rtmp://public.example.com/live/key"


@pytest.mark.asyncio
async def test_validate_outbound_url_rejects_hostname_dns_rebinding_to_private_ip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DNS-rebind case: a hostname (not a literal IP) that resolves into a private range."""
    monkeypatch.setattr(socket, "getaddrinfo", lambda host, port: _fake_addrinfo("172.16.5.5"))
    with pytest.raises(ApiError):
        await validate_outbound_url(
            "rtmp://looks-public-but-isnt.example.com/live/key", allowed_schemes=("rtmp",)
        )
