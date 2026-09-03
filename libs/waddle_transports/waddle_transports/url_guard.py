"""Shared SSRF guard -- verbatim logic from `core/svc_action/services/url_guard.py`.

Ported into this shared library (not cross-imported from svc-action, which
has no installable package boundary of its own) so every transport that
makes an outbound HTTP(/2) call -- across every consuming service -- gets
the identical SSRF posture. Do not hand-edit the SSRF checks themselves
independently per-copy if this module is ever duplicated again; port
fixes here instead (this repo's established convention, see the original
module's own docstring for the rationale it inherited from `hub_api`'s
copy).

Security posture (fail closed throughout):
- Scheme allowlist: `http`/`https` only.
- Hostname resolution: every literal IP AND every hostname is resolved via
  `socket.getaddrinfo()` (not a regex over the string) -- re-checked
  before the initial request AND before following every redirect (DNS
  rebind defense).
- Disallowed ranges: loopback, link-local (including the cloud-metadata
  address), RFC 1918 private, IPv6 ULA, `0.0.0.0/8`, multicast.
- A hostname that fails to resolve at all is treated as disallowed (fail
  closed).
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urljoin, urlparse

import httpx

#: Only these two schemes are ever fetched -- SSRF via `file://`/
#: `gopher://`/`ftp://`/etc. is rejected before any network call.
ALLOWED_SCHEMES = frozenset({"http", "https"})

#: 3xx redirect hops re-validated before following; caps a redirect loop
#: and bounds how many DNS resolutions one request can trigger.
_MAX_REDIRECTS = 5

_REDIRECT_STATUS_CODES = frozenset({301, 302, 303, 307, 308})


class SSRFError(ValueError):
    """A URL/host failed the SSRF guard -- reject at fetch time."""


def _is_disallowed_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Loopback/link-local/RFC1918/`0.0.0.0/8`/ULA (`is_private`) or multicast."""
    return ip.is_private or ip.is_multicast


def is_private_host(host: str) -> bool:
    """True if `host` (a literal IP or a hostname) resolves to a disallowed address.

    Resolution-aware (via `socket.getaddrinfo`), not a regex over the
    string. Rejects (returns `True`) if resolution fails entirely -- fail
    closed.
    """
    try:
        return _is_disallowed_ip(ipaddress.ip_address(host))
    except ValueError:
        pass  # not a literal IP -- resolve it below

    try:
        addr_infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return True  # cannot resolve -- fail closed

    for addr_info in addr_infos:
        raw_addr = str(addr_info[4][0])
        try:
            resolved_ip = ipaddress.ip_address(raw_addr.split("%", 1)[0])
        except ValueError:
            return True  # unparseable address -- fail closed
        if _is_disallowed_ip(resolved_ip):
            return True
    return False


def validate_url(url: str) -> None:
    """Raise `SSRFError` unless `url` is `http(s)` and its host resolves to a public address."""
    parsed = urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise SSRFError(f"URL scheme must be http or https, got {parsed.scheme!r}")
    if not parsed.hostname:
        raise SSRFError(f"URL has no host: {url!r}")
    if is_private_host(parsed.hostname):
        raise SSRFError(f"URL host {parsed.hostname!r} resolves to a disallowed address")


async def guarded_request(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    content: bytes | None = None,
    json: dict[str, object] | list[object] | None = None,
) -> httpx.Response:
    """`method url`, re-validating the SSRF guard before every hop.

    `client` must be constructed with `follow_redirects=False` -- this
    function owns the redirect loop so each hop's `Location` can be
    re-validated before it's fetched.
    """
    current_url = url
    for _ in range(_MAX_REDIRECTS + 1):
        validate_url(current_url)
        response = await client.request(
            method, current_url, headers=headers, content=content, json=json
        )
        if response.status_code not in _REDIRECT_STATUS_CODES:
            return response
        location = response.headers.get("location")
        if not location:
            return response
        current_url = urljoin(current_url, location)
    raise SSRFError(f"too many redirects (> {_MAX_REDIRECTS}) starting from {url!r}")
