"""security.md A05 hardening -- `install_security_headers` on browser_source_core_module.

This module's two HTML overlay routes (`serve_overlay`/`serve_caption_overlay`
in `app.py`) each already return an explicit `X-Frame-Options: ALLOWALL`
("Required for OBS browser source" -- intentionally embeddable from any
origin). `install_security_headers()` uses `headers.setdefault()` so that
value is never clobbered (`test_route_supplied_header_is_never_clobbered` in
`libs/flask_core/tests/test_security_headers.py` proves the general
mechanism); this file's own regression is narrower and more important here:
CSP `frame-ancestors`, when present, overrides `X-Frame-Options` in every
browser that supports it -- so `app.py` strips `frame-ancestors 'none'` out
of the shared `OVERLAY_CSP` before installing it
(`_OVERLAY_CSP_FRAMEABLE`), and `test_valid_overlay_response_omits_frame_ancestors`
below is the proof that stripping actually happened, not just that
`X-Frame-Options` survived.

Uses the same import-order workaround as `tests/test_auth.py`
(`import flask_core` before `from app import app`, `DATABASE_URL`/
`SERVICE_API_KEY` set before that import) and stubs `app.overlay_service`
directly rather than running `@app.before_serving` -- this module's real
`OverlayService` speaks Postgres-flavored raw SQL (`$1` placeholders,
`NOW()`), which a `sqlite://` test DB can't execute; no automated test in
this module exercises the real overlay-key DB path today (see
`tests/test_auth.py`'s own module docstring -- only the captions
service-key gate is covered), so stubbing is the same boundary this
module's test suite has always drawn, not a new gap this PR introduces.
"""

from __future__ import annotations

import os
import sys

import flask_core  # noqa: F401 - see module docstring; must import before `app`

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("DATABASE_URL", "sqlite://test.db")
os.environ.setdefault("SERVICE_API_KEY", "test-service-key")

from flask_core.security_headers import OVERLAY_CSP  # noqa: E402

import app as app_module  # noqa: E402


class _StubOverlayService:
    """Duck-typed `OverlayService` stand-in -- no DB, just proves the header contract.

    Mirrors the real `OverlayService.validate_overlay_key`'s length check
    (64-char hex keys only) so an obviously-malformed key still 404s here,
    same as production -- everything past that format check is stubbed
    since it would otherwise require a real Postgres-flavored DB.
    """

    async def validate_overlay_key(self, overlay_key: str) -> dict | None:
        if not overlay_key or len(overlay_key) != 64:
            return None
        return {"community_id": 1, "theme_config": {}, "enabled_sources": []}

    async def log_access(self, **kwargs: object) -> None:
        return None

    async def get_overlay_html(
        self, community_id: int, theme_config: dict, enabled_sources: list
    ) -> str:
        return "<html><body>stub overlay</body></html>"


class TestInvalidKeyStillCarriesHeaders:
    """`after_request` fires on every response, including the 404 error path."""

    async def test_invalid_key_404_still_gets_the_baseline_headers(self) -> None:
        app_module.overlay_service = _StubOverlayService()
        client = app_module.app.test_client()
        response = await client.get("/overlay/not-a-valid-key")
        assert response.status_code == 404
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert "Content-Security-Policy" in response.headers


class TestValidOverlayResponsePreservesAllowall:
    """The real regression: ALLOWALL survives, and CSP no longer contradicts it."""

    async def test_valid_overlay_response_keeps_x_frame_options_allowall(self) -> None:
        app_module.overlay_service = _StubOverlayService()
        client = app_module.app.test_client()
        response = await client.get("/overlay/" + "a" * 64)
        assert response.status_code == 200
        # Route's own explicit value -- setdefault() must not clobber it.
        assert response.headers["X-Frame-Options"] == "ALLOWALL"

    async def test_valid_overlay_response_omits_frame_ancestors(self) -> None:
        """CSP `frame-ancestors` (if present) overrides X-Frame-Options -- must be absent here."""
        app_module.overlay_service = _StubOverlayService()
        client = app_module.app.test_client()
        response = await client.get("/overlay/" + "a" * 64)
        csp = response.headers["Content-Security-Policy"]
        assert "frame-ancestors" not in csp
        # Everything else from OVERLAY_CSP (inline script/style allowance
        # for the template's own <script>/<style>) is still present.
        assert "'unsafe-inline'" in csp
        # Confirms this app installed the stripped variant, not the raw one.
        assert csp != OVERLAY_CSP
