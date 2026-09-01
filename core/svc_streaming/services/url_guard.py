"""SSRF guard for caller-supplied network targets -- ported from `hub_api/services/url_guard.py`.

Two call sites need this: a stream's `source_url` (ffmpeg's own `-i`
input -- rtmp/rtmps/http/https) and a forward target's `forward_url`
(ffmpeg opens a real outbound RTMP connection to it, `services/
ffmpeg_engine.py`). Both are caller-supplied network destinations this
process will itself connect out to -- exactly the SSRF trust boundary
`hub_api/services/streaming_proxy_service.py`'s module docstring already
flags for the legacy `video_proxy_module` proxy's `rtmpUrl` field.

Security posture (fail closed, ported verbatim from the hub-api original):
scheme allowlist, blocked-hostname list (localhost, cloud metadata host),
literal-IP check, and `socket.getaddrinfo()` resolution for hostnames --
loopback/link-local/RFC1918/multicast/reserved/unspecified all rejected.
"""

from __future__ import annotations

import asyncio
import ipaddress
import socket
from urllib.parse import urlparse

from services.errors import bad_request

#: Never treated as safe outbound targets regardless of scheme -- catches
#: SSRF-classic metadata endpoints and loopback hostnames that don't
#: always resolve to an IP a naive `ipaddress` check would flag.
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
    """Validate `url` is safe for this process to open an outbound connection to.

    Raises `services.errors.ApiError` (400) on any of: unparseable URL,
    disallowed scheme, blocked literal hostname, or a hostname/literal IP
    that resolves into a private/loopback/link-local/multicast/reserved
    range. Returns `url` unchanged (pass-through validator).
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
