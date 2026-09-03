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


class ResponseTooLargeError(Exception):
    """A response body exceeded `guarded_request`'s configured byte cap -- download aborted."""


#: Applied when a caller doesn't pass its own `max_response_bytes` -- large enough
#: for any legitimate webhook/REST/GraphQL/gRPC payload this library expects, small
#: enough that a malicious/misbehaving target can't force unbounded memory growth.
DEFAULT_MAX_RESPONSE_BYTES = 10 * 1024 * 1024  # 10 MiB


def _is_disallowed_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Loopback/link-local/RFC1918/`0.0.0.0/8`/ULA (`is_private`) or multicast."""
    return ip.is_private or ip.is_multicast


def _resolve_and_validate_ip(hostname: str) -> str:
    """Resolve `hostname` exactly once and return one validated IP to pin the connection to.

    Doing resolution and validation together (rather than a separate
    `getaddrinfo()` here for the check and a second, independent one at
    HTTP-connect time) closes the DNS-rebind TOCTOU window: the IP
    returned here is the exact address the connection is pinned to by
    `guarded_request()`, never a second lookup that could return a
    different (rebound) address between validation and connection.

    Fail-closed throughout, same posture as the former `is_private_host`
    body this replaces: an unresolvable hostname, an unparseable address,
    or ANY disallowed candidate among multiple `A`/`AAAA` records rejects
    the whole hostname (never silently picks around a bad one).
    """
    try:
        literal_ip = ipaddress.ip_address(hostname)
    except ValueError:
        pass  # not a literal IP -- resolve it below
    else:
        if _is_disallowed_ip(literal_ip):
            raise SSRFError(f"URL host {hostname!r} resolves to a disallowed address")
        return str(literal_ip)

    try:
        addr_infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise SSRFError(f"URL host {hostname!r} could not be resolved") from exc

    resolved_ips: list[str] = []
    for addr_info in addr_infos:
        raw_addr = str(addr_info[4][0])
        try:
            resolved_ip = ipaddress.ip_address(raw_addr.split("%", 1)[0])
        except ValueError as exc:
            raise SSRFError(
                f"URL host {hostname!r} resolved to an unparseable address"
            ) from exc
        if _is_disallowed_ip(resolved_ip):
            raise SSRFError(f"URL host {hostname!r} resolves to a disallowed address")
        resolved_ips.append(str(resolved_ip))

    if not resolved_ips:
        raise SSRFError(f"URL host {hostname!r} resolves to a disallowed address")
    return resolved_ips[0]


def is_private_host(host: str) -> bool:
    """True if `host` (a literal IP or a hostname) resolves to a disallowed address.

    Resolution-aware (via `socket.getaddrinfo`, through
    `_resolve_and_validate_ip`), not a regex over the string. Rejects
    (returns `True`) if resolution fails entirely -- fail closed.
    """
    try:
        _resolve_and_validate_ip(host)
    except SSRFError:
        return True
    return False


def _pin_host_to_ip(url: str) -> tuple[str, str]:
    """Validate `url` and return `(url with its host replaced by the one validated IP, hostname)`.

    The literal IP is what `guarded_request()` actually connects to; the
    original hostname is preserved (returned separately) for the `Host`
    header and TLS SNI, so virtual-hosting and certificate verification
    are unaffected by connecting to an IP instead of the name.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise SSRFError(f"URL scheme must be http or https, got {parsed.scheme!r}")
    hostname = parsed.hostname
    if not hostname:
        raise SSRFError(f"URL has no host: {url!r}")

    pinned_ip = _resolve_and_validate_ip(hostname)

    userinfo = ""
    if parsed.username:
        userinfo = parsed.username
        if parsed.password:
            userinfo += f":{parsed.password}"
        userinfo += "@"
    host_literal = f"[{pinned_ip}]" if ":" in pinned_ip else pinned_ip
    netloc = f"{userinfo}{host_literal}"
    if parsed.port is not None:
        netloc = f"{netloc}:{parsed.port}"

    return parsed._replace(netloc=netloc).geturl(), hostname


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
    max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
) -> httpx.Response:
    """`method url`, re-validating the SSRF guard before every hop.

    `client` must be constructed with `follow_redirects=False` -- this
    function owns the redirect loop so each hop's `Location` can be
    re-validated before it's fetched.

    Each hop resolves and validates the host exactly once (`_pin_host_to_
    ip`) and connects to that literal pinned IP -- the original hostname
    is preserved via an explicit `Host` header and the `sni_hostname`
    extension (SNI + TLS certificate verification), so this closes the
    DNS-rebind TOCTOU window between validation and the actual connection
    without weakening virtual-hosting or cert checks.

    The response body is streamed and capped at `max_response_bytes` --
    exceeding it aborts the download immediately (`ResponseTooLargeError`)
    rather than buffering an unbounded body into memory.
    """
    current_url = url
    for _ in range(_MAX_REDIRECTS + 1):
        pinned_url, original_host = _pin_host_to_ip(current_url)
        request_headers = {**(headers or {}), "Host": original_host}
        async with client.stream(
            method,
            pinned_url,
            headers=request_headers,
            content=content,
            json=json,
            extensions={"sni_hostname": original_host},
        ) as response:
            body = bytearray()
            async for chunk in response.aiter_bytes():
                body.extend(chunk)
                if len(body) > max_response_bytes:
                    raise ResponseTooLargeError(
                        f"response from {pinned_url!r} exceeded {max_response_bytes} byte cap"
                    )
            # Mirrors httpx's own `Response.aread()` (`self._content = b"".join(...)`)
            # -- makes `.content`/`.json()`/`.text` usable by the caller after this
            # function returns, populated from the capped read above rather than a
            # second, unbounded read.
            response._content = bytes(body)  # noqa: SLF001
        if response.status_code not in _REDIRECT_STATUS_CODES:
            return response
        location = response.headers.get("location")
        if not location:
            return response
        current_url = urljoin(current_url, location)
    raise SSRFError(f"too many redirects (> {_MAX_REDIRECTS}) starting from {url!r}")
