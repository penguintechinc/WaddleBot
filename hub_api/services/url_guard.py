"""SSRF-safe validation for user-supplied outbound URLs.

Two write paths in the M7 Streaming port accept a URL that this service
(or a downstream service it forwards to) will eventually open an outbound
connection to: `music_service.add_radio_station()`'s `url` field (an
Icecast/Shoutcast stream URL) and `streaming_proxy_service.add_destination()`'s
`rtmpUrl` (an RTMP forward-target, relayed to `video_proxy_module`, which
opens the real outbound RTMP connection). Node's own validation
(`musicController.js`: `new URL(url)`; `streamingController.js`:
`rtmpUrl.startsWith('rtmp://'||'rtmps://')`) checks *format* only, not
*destination* -- a caller can supply `http://169.254.169.254/latest/
meta-data/` or `rtmp://10.0.0.5:6379/internal-service` and either request
happily forwards it. This module is the fix (security.md Input Validation
+ the M7 port's explicit SSRF-adjacent instruction): scheme allowlist AND
a resolved-IP check against RFC 1918/loopback/link-local/multicast/
reserved ranges, run via `asyncio.to_thread` (DNS resolution is blocking
I/O -- never call it directly from an async route handler, penguin-
python-dev's Performance Patterns).
"""

from __future__ import annotations

import asyncio
import ipaddress
import socket
from urllib.parse import urlparse

from services.errors import bad_request

#: Never treated as safe outbound targets regardless of scheme, even if a
#: DNS/literal-IP check would otherwise pass -- catches SSRF-classic
#: metadata endpoints and loopback hostnames that don't always resolve to
#: an IP a naive `ipaddress` check would flag (some resolvers special-case
#: these).
_BLOCKED_HOSTNAMES: frozenset[str] = frozenset({"localhost", "metadata.google.internal"})


def _is_blocked_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """True if `ip` is private/loopback/link-local/multicast/reserved/unspecified."""
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def _resolve_and_check_sync(hostname: str) -> None:
    """Blocking DNS resolution + IP-range check -- run only via `asyncio.to_thread`."""
    try:
        infos = socket.getaddrinfo(hostname, None)
    except OSError as exc:
        raise bad_request(f"Could not resolve host: {hostname}") from exc
    for info in infos:
        raw_ip = info[4][0]
        try:
            ip = ipaddress.ip_address(raw_ip)
        except ValueError:
            continue
        if _is_blocked_ip(ip):
            raise bad_request(f"URL resolves to a disallowed network address: {hostname}")


async def validate_outbound_url(url: str, *, allowed_schemes: tuple[str, ...]) -> str:
    """Validate `url` is safe to use as an outbound network target.

    Raises `services.errors.ApiError` (400) on any of: unparseable URL,
    disallowed scheme, blocked literal hostname, or a hostname/literal IP
    that resolves into a private/loopback/link-local/multicast/reserved
    range. Returns `url` unchanged (a pass-through validator, not a
    normalizer -- callers store/forward exactly what the user supplied,
    matching Node's own byte-faithful behavior once it passes).
    """
    parsed = urlparse(url)
    if parsed.scheme.lower() not in allowed_schemes or not parsed.hostname:
        raise bad_request(
            f"Invalid URL -- expected one of {', '.join(allowed_schemes)}:// with a host"
        )

    hostname = parsed.hostname.lower()
    if hostname in _BLOCKED_HOSTNAMES:
        raise bad_request(f"URL host is not allowed: {hostname}")

    try:
        literal_ip = ipaddress.ip_address(hostname)
    except ValueError:
        literal_ip = None

    if literal_ip is not None:
        if _is_blocked_ip(literal_ip):
            raise bad_request(f"URL resolves to a disallowed network address: {hostname}")
        return url

    await asyncio.to_thread(_resolve_and_check_sync, hostname)
    return url
