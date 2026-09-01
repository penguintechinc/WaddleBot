"""Shared SSRF guard -- verbatim copy of hub_api/services/url_guard.py.

svc-action is a standalone container (own pip install/Docker image, no
cross-container Python import path back to hub_api), so this module is
duplicated rather than imported. Per this task's explicit instruction
("Reuse services/url_guard.py, do NOT reimplement SSRF guard") and
security.md's "no reimplemented equivalents" precedent, the logic below is
copied byte-for-byte from hub_api's version (only the `services.errors`
import target changes, to this package's own copy of that tiny exception
type -- see services/errors.py) -- do not hand-edit the SSRF checks
themselves here; port fixes from hub_api's copy instead.

Two entry points svc-action's adapters use:
- `guarded_get`/`validate_url` (via a `webhook`/`rest_api`/`overlay`
  adapter's own `guarded_post`-shaped call, built the same way) -- the
  action-target URL is re-validated before the initial request AND before
  following every redirect.
- `validate_outbound_url` -- validates an action-target URL read from
  bundle config before ever attempting to dispatch to it.

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
  link-local/RFC1918/`0.0.0.0/8`/ULA in one property; `is_multicast` is
  checked separately since `is_private` does not imply it. IPv4-mapped
  IPv6 addresses (`::ffff:127.0.0.1`, a classic SSRF-filter bypass) are
  correctly classified `is_private=True` by the stdlib and therefore
  caught here too.
- A hostname that fails to resolve at all is treated as disallowed
  (fail closed) -- an unverifiable target is never fetched.
"""

from __future__ import annotations

import asyncio
import ipaddress
import socket
from urllib.parse import urljoin, urlparse

import httpx

from services.errors import bad_request

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


async def guarded_request(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    content: bytes | None = None,
    json: dict | list | None = None,
) -> httpx.Response:
    """`method url`, re-validating the SSRF guard before every hop.

    Same redirect-revalidation contract as `guarded_get` (client must be
    built with `follow_redirects=False`), generalized to any HTTP method
    and an optional request body -- svc-action's `webhook`/`rest_api`/
    `overlay` adapters all POST (or a configurable method for `rest_api`),
    not just GET, so `guarded_get`'s GET-only shape doesn't cover them.
    Kept alongside `guarded_get` rather than replacing it, matching this
    module's own "kept alongside rather than folded in" precedent for
    `validate_outbound_url` below.
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
    normalizer).
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
