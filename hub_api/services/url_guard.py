"""Shared SSRF guard -- promoted from `bot_rcon.py`'s original `is_private_host`.

Two call sites need the identical check: `bot_rcon.py` (validates a
user-supplied RCON `host` at server-create/update time) and
`bot_ai_knowledge.py` (validates user-supplied knowledge-source URLs at
both write time and crawl/fetch time -- the crawler fetches
`sitemap.xml`, every `<loc>` URL found inside it, and the GitHub
Contents API, all server-side, on a user-controlled origin for the
`mkdocs`/`docusaurus`/`generic_url` source types). One guard, reused,
per security.md's "no reimplemented equivalents" and this repo's own
"promote, don't duplicate" precedent (`app_bundle_tables.py`, `bot_tables.py`).

Security posture (fail closed throughout):
- Scheme allowlist: `http`/`https` only -- rejects `file://`, `gopher://`,
  `ftp://`, etc. outright (SSRF via alternate scheme handlers).
- Hostname resolution: every literal IP AND every hostname is resolved
  via `socket.getaddrinfo()` (not a regex over the string) -- a hostname
  that currently resolves to a public IP but is switched to resolve to
  an internal one after the check (DNS rebind) is still caught at fetch
  time because the guard runs immediately before every request AND
  before following every redirect, not just once at write time.
- Disallowed ranges: loopback (127/8, ::1), link-local (169.254/16
  including the cloud-metadata address, fe80::/10), RFC 1918 private
  (10/8, 172.16/12, 192.168/16), IPv6 ULA (fc00::/7), `0.0.0.0/8`, and
  multicast. Python's `ipaddress.*.is_private` already covers loopback/
  link-local/RFC1918/`0.0.0.0/8`/ULA in one property (verified against
  every range this module's docstring lists); `is_multicast` is checked
  separately since `is_private` does not imply it. IPv4-mapped IPv6
  addresses (`::ffff:127.0.0.1`, a classic SSRF-filter bypass) are
  correctly classified `is_private=True` by the stdlib and therefore
  caught here too.
- A hostname that fails to resolve at all is treated as disallowed
  (fail closed) -- an unverifiable target is never fetched.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urljoin, urlparse

import httpx

#: Only these two schemes are ever fetched or stored -- SSRF via
#: `file://`/`gopher://`/`ftp://`/etc. is rejected before any network call.
ALLOWED_SCHEMES = frozenset({"http", "https"})

#: 3xx redirect hops re-validated before following; caps a redirect loop
#: and bounds how many DNS resolutions one request can trigger.
_MAX_REDIRECTS = 5

_REDIRECT_STATUS_CODES = frozenset({301, 302, 303, 307, 308})


class SSRFError(ValueError):
    """A URL/host failed the SSRF guard -- reject at write time or fetch time."""


def _is_disallowed_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Loopback/link-local/RFC1918/`0.0.0.0/8`/ULA (`is_private`) or multicast."""
    return ip.is_private or ip.is_multicast


def is_private_host(host: str) -> bool:
    """True if `host` (a literal IP or a hostname) resolves to a disallowed address.

    Resolution-aware (via `socket.getaddrinfo`), not a regex over the
    string -- a hostname is checked by its *resolved* address(es), so a
    hostname pointing at an internal IP is caught even though the
    hostname itself doesn't look private. Rejects (returns `True`) if
    resolution fails entirely -- fail closed.
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
        # `sockaddr[0]` is the address for both AF_INET (2-tuple) and
        # AF_INET6 (4-tuple, may carry a `%scope_id` suffix) -- always a
        # `str` at runtime; mypy's stub widens it to `str | int` because
        # the same tuple shape is reused for AF_UNIX paths.
        raw_addr = str(addr_info[4][0])
        try:
            resolved_ip = ipaddress.ip_address(raw_addr.split("%", 1)[0])
        except ValueError:
            return True  # unparseable address -- fail closed
        if _is_disallowed_ip(resolved_ip):
            return True
    return False


def validate_url(url: str) -> None:
    """Raise `SSRFError` unless `url` is `http(s)` and its host resolves to a public address.

    Call at write time (before persisting a user-supplied URL) and at
    fetch time (before every request and before following every
    redirect) -- see module docstring.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise SSRFError(f"URL scheme must be http or https, got {parsed.scheme!r}")
    if not parsed.hostname:
        raise SSRFError(f"URL has no host: {url!r}")
    if is_private_host(parsed.hostname):
        raise SSRFError(f"URL host {parsed.hostname!r} resolves to a disallowed address")


async def guarded_get(
    client: httpx.AsyncClient, url: str, *, headers: dict[str, str] | None = None
) -> httpx.Response:
    """`GET url`, re-validating the SSRF guard before every hop.

    Applied before the initial request AND before following every
    redirect (defense against a public URL that 3xx-redirects to an
    internal target). `client` must be constructed with
    `follow_redirects=False` -- this function owns the redirect loop so
    each hop's `Location` can be re-validated before it's fetched.

    Raises `SSRFError` on the initial URL, on any redirect target, or
    after `_MAX_REDIRECTS` hops.
    """
    current_url = url
    for _ in range(_MAX_REDIRECTS + 1):
        validate_url(current_url)
        response = await client.get(current_url, headers=headers)
        if response.status_code not in _REDIRECT_STATUS_CODES:
            return response
        location = response.headers.get("location")
        if not location:
            return response
        current_url = urljoin(current_url, location)
    raise SSRFError(f"too many redirects (> {_MAX_REDIRECTS}) starting from {url!r}")
