"""Tests for flask_core.security_headers -- security.md A05 hardening.

Red->green baseline this closes: before `install_security_headers()`
existed, a bare Quart response carried none of CSP/HSTS/X-Content-Type-
Options/X-Frame-Options/Referrer-Policy -- `test_bare_app_has_no_security_headers`
below is that regression proof, run against an app that never calls
`install_security_headers()`.
"""

from __future__ import annotations

import pytest
from flask_core.security_headers import (
    DEFAULT_CSP,
    OVERLAY_CSP,
    SecurityHeadersConfig,
    install_security_headers,
)
from quart import Quart


def _make_app() -> Quart:
    app = Quart(__name__)

    @app.route("/ping")
    async def ping() -> str:
        return "pong"

    return app


@pytest.mark.asyncio
async def test_bare_app_has_no_security_headers() -> None:
    """Regression proof: a Quart app with no hook installed sends none of these headers."""
    app = _make_app()
    async with app.test_app() as running:
        response = await running.test_client().get("/ping")
    for header in (
        "Content-Security-Policy",
        "Strict-Transport-Security",
        "X-Content-Type-Options",
        "X-Frame-Options",
        "Referrer-Policy",
    ):
        assert header not in response.headers


@pytest.mark.asyncio
async def test_install_security_headers_sets_the_baseline_four() -> None:
    """The always-on baseline: nosniff, deny-framing, no-referrer, default-deny CSP."""
    app = _make_app()
    install_security_headers(app)
    async with app.test_app() as running:
        response = await running.test_client().get("/ping")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["Content-Security-Policy"] == DEFAULT_CSP


@pytest.mark.asyncio
async def test_hsts_absent_when_not_production() -> None:
    """Dev/test posture (`hsts=False`) never advertises HSTS -- see `is_production()`."""
    app = _make_app()
    install_security_headers(app, hsts=False)
    async with app.test_app() as running:
        response = await running.test_client().get("/ping")
    assert "Strict-Transport-Security" not in response.headers


@pytest.mark.asyncio
async def test_hsts_present_when_production() -> None:
    """Prod posture (`hsts=True`) advertises HSTS with a real max-age."""
    app = _make_app()
    install_security_headers(app, hsts=True)
    async with app.test_app() as running:
        response = await running.test_client().get("/ping")
    assert response.headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"


@pytest.mark.asyncio
async def test_hsts_defaults_to_is_production(monkeypatch: pytest.MonkeyPatch) -> None:
    """`hsts=None` (the default) resolves from `workload_identity.is_production()`."""
    monkeypatch.setenv("RELEASE_MODE", "false")
    app = _make_app()
    install_security_headers(app)
    async with app.test_app() as running:
        response = await running.test_client().get("/ping")
    assert "Strict-Transport-Security" not in response.headers


@pytest.mark.asyncio
async def test_overlay_csp_permits_inline_and_https_embeds() -> None:
    """`OVERLAY_CSP` is the documented relaxation for svc_presentation-style HTML pages."""
    app = _make_app()
    install_security_headers(app, csp=OVERLAY_CSP)
    async with app.test_app() as running:
        response = await running.test_client().get("/ping")
    csp = response.headers["Content-Security-Policy"]
    assert "'unsafe-inline'" in csp
    assert "frame-ancestors 'none'" in csp  # still denies being framed by other sites
    assert "object-src 'none'" in csp


@pytest.mark.asyncio
async def test_route_supplied_header_is_never_clobbered() -> None:
    """A route that sets its own value for one of these headers wins -- `setdefault`, not overwrite."""
    app = Quart(__name__)

    @app.route("/custom")
    async def custom() -> tuple[str, int, dict[str, str]]:
        return "ok", 200, {"X-Frame-Options": "SAMEORIGIN"}

    install_security_headers(app)
    async with app.test_app() as running:
        response = await running.test_client().get("/custom")
    assert response.headers["X-Frame-Options"] == "SAMEORIGIN"


def test_install_security_headers_returns_the_resolved_config() -> None:
    """Return value is introspectable -- callers/tests don't have to re-derive it."""
    app = _make_app()
    config = install_security_headers(app, csp=OVERLAY_CSP, hsts=True, extra_headers={"X-Foo": "bar"})
    assert config == SecurityHeadersConfig(
        csp=OVERLAY_CSP, hsts_enabled=True, extra_headers={"X-Foo": "bar"}
    )


@pytest.mark.asyncio
async def test_extra_headers_are_applied() -> None:
    """Per-service `extra_headers` (e.g. Permissions-Policy) are set the same way."""
    app = _make_app()
    install_security_headers(app, extra_headers={"Permissions-Policy": "geolocation=()"})
    async with app.test_app() as running:
        response = await running.test_client().get("/ping")
    assert response.headers["Permissions-Policy"] == "geolocation=()"
