"""Security response headers -- security.md A05 (Security Misconfiguration) hardening.

Repo-wide finding this closes: 0 of ~1027 scanned Python responses set any
of CSP / HSTS / X-Content-Type-Options / X-Frame-Options / Referrer-Policy
-- every service builds its own `Quart(__name__)` directly (no shared app
factory exists across `hub_api`/`core/*`), so there was no single choke
point setting these. `install_security_headers()` is that choke point now:
one `app.after_request` hook, registered once per service in its own
`create_app()`/module-level setup -- the same "global hook, not a per-route
decorator" shape `hub_api/services/rate_limiting.py::install_rate_limiting`
already established for the equivalent 449-endpoints-can't-each-opt-in
problem.

Two CSPs are exported because this monorepo has two genuinely different
kinds of service:

- `DEFAULT_CSP`: deny-everything, correct for the JSON-only API services
  that are most of `hub_api`/`core/*` -- they never serve HTML, so there is
  nothing a same-origin allowance would help with.
- `OVERLAY_CSP`: the small set of services that render real HTML with
  inline `<script>`/`<style>` (no nonce infrastructure exists yet -- see
  `core/svc_presentation/services/render.py`) plus third-party
  OBS-embeddable players (YouTube iframe API, Spotify track embeds, Twitch
  clip embeds, placeholder images) -- `core/svc_presentation` and
  `core/browser_source_core_module`. `frame-ancestors 'none'` still
  applies in both CSPs: it blocks *other* sites from framing these overlay
  pages; it has no effect on OBS's browser source (a direct Chromium
  navigation to the URL, never an iframe embed) or on the third-party
  `<iframe>`s these pages themselves embed (governed by `frame-src`, not
  `frame-ancestors`).

`hsts` defaults to `workload_identity.is_production()` so dev/test
environments -- and any request received without TLS having actually
terminated somewhere in front of this process -- never advertise HSTS.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .workload_identity import is_production

if TYPE_CHECKING:
    from quart import Quart, Response

#: Deny-everything default -- correct for the JSON-only API services that
#: are most of this monorepo (hub_api, every `core/*_module` except the
#: two overlay-rendering services below). No inline/external script or
#: style is ever needed by a service that returns only `application/json`.
DEFAULT_CSP = "default-src 'none'; frame-ancestors 'none'; base-uri 'self'"

#: Relaxed CSP for services that render real HTML overlay/browser-source
#: pages -- see module docstring for the full rationale. `script-src`/
#: `frame-src https:` is broad (any HTTPS origin) rather than an explicit
#: youtube.com/open.spotify.com/clips.twitch.tv allowlist because these
#: overlay pages are configured per-community (custom image URLs, future
#: embed providers) with no fixed provider set -- still meaningfully
#: stricter than no CSP at all (blocks `http:`, inline `object`/`embed`,
#: and framing of the page itself).
OVERLAY_CSP = (
    "default-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "
    "script-src 'self' 'unsafe-inline' https:; "
    "img-src 'self' https: data:; "
    "frame-src https:; "
    "connect-src 'self'; "
    "frame-ancestors 'none'; "
    "object-src 'none'; "
    "base-uri 'self'"
)

_HSTS_VALUE = "max-age=31536000; includeSubDomains"


@dataclass(slots=True, frozen=True)
class SecurityHeadersConfig:
    """The resolved header set one service installed -- returned for tests/introspection."""

    csp: str
    hsts_enabled: bool
    extra_headers: Mapping[str, str] = field(default_factory=dict)


def install_security_headers(
    app: Quart,
    *,
    csp: str | None = None,
    hsts: bool | None = None,
    extra_headers: Mapping[str, str] | None = None,
) -> SecurityHeadersConfig:
    """Wire the global security-headers `after_request` hook onto `app`.

    Sets `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
    `Referrer-Policy: no-referrer`, and `Content-Security-Policy` (`csp`,
    default `DEFAULT_CSP`) on every response, plus `Strict-Transport-
    Security` when `hsts` (default `is_production()`) is true. Uses
    `headers.setdefault()`, never direct assignment, so a route that
    deliberately sets its own value for one of these headers (e.g. a
    future nonce-scoped CSP for a single surface) is never silently
    clobbered by this app-wide default.

    Call once per service, in `create_app()` (or at module scope for
    services with no factory) -- registering it twice would just call
    `setdefault()` twice, harmlessly, but there is never a reason to.
    """
    resolved_csp = csp if csp is not None else DEFAULT_CSP
    resolved_hsts = is_production() if hsts is None else hsts
    resolved_extra: Mapping[str, str] = dict(extra_headers) if extra_headers else {}

    @app.after_request
    async def _install_security_headers(response: Response) -> Response:
        """Set the app-wide security header baseline, never overriding a route's own value."""
        headers = response.headers
        headers.setdefault("X-Content-Type-Options", "nosniff")
        headers.setdefault("X-Frame-Options", "DENY")
        headers.setdefault("Referrer-Policy", "no-referrer")
        headers.setdefault("Content-Security-Policy", resolved_csp)
        if resolved_hsts:
            headers.setdefault("Strict-Transport-Security", _HSTS_VALUE)
        for name, value in resolved_extra.items():
            headers.setdefault(name, value)
        return response

    return SecurityHeadersConfig(
        csp=resolved_csp, hsts_enabled=resolved_hsts, extra_headers=resolved_extra
    )
