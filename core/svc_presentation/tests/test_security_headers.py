"""security.md A05 hardening -- `install_security_headers(app, csp=OVERLAY_CSP)`.

svc-presentation serves real rendered HTML with inline `<script>`/`<style>`
(no nonce infrastructure -- `services/render.py`) plus third-party embeds
(YouTube iframe API, Spotify track embeds), so it gets `OVERLAY_CSP` rather
than `flask_core.security_headers.DEFAULT_CSP` (deny-everything, correct
for the JSON-only services). CSP is enforced by the *browser*, not this
server -- these tests prove two different things: the baseline headers are
present on every response (`test_health_carries_the_security_header_baseline`),
and the CSP this service actually sends is the relaxed one that permits
what its own overlay pages need, not the default that would silently break
them in a real browser (`test_overlay_csp_permits_what_the_rendered_pages_need`).
"""

from __future__ import annotations

import pytest
from flask_core.security_headers import DEFAULT_CSP
from quart.typing import TestClientProtocol


@pytest.mark.asyncio
async def test_health_carries_the_security_header_baseline(client: TestClientProtocol) -> None:
    """Every response -- including the plain JSON `/health` -- gets the baseline four."""
    response = await client.get("/health")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert "Content-Security-Policy" in response.headers


@pytest.mark.asyncio
async def test_overlay_csp_permits_what_the_rendered_pages_need(
    client: TestClientProtocol,
) -> None:
    """The CSP sent is the relaxed `OVERLAY_CSP`, not the deny-everything `DEFAULT_CSP`.

    `DEFAULT_CSP` (`default-src 'none'`) would silently break every overlay
    surface in a real browser -- their inline `<script>`/`<style>` blocks
    and the YouTube/Spotify embeds would all be blocked client-side while
    the server still happily returns 200. This is the regression proof
    that the *correct* CSP -- not just *a* CSP -- is what's actually sent.
    """
    response = await client.get("/overlay/testcommunity/full_screen")
    assert response.status_code == 200
    csp = response.headers["Content-Security-Policy"]
    assert csp != DEFAULT_CSP
    assert "'unsafe-inline'" in csp  # the page's own inline <script>/<style>
    assert "frame-ancestors 'none'" in csp  # still denies framing by other sites


@pytest.mark.asyncio
@pytest.mark.parametrize("surface", ["full_screen", "media", "crawler"])
async def test_every_core_surface_still_renders_200_under_the_relaxed_csp(
    client: TestClientProtocol, surface: str
) -> None:
    """Each overlay surface still renders cleanly with `install_security_headers` wired in."""
    response = await client.get(f"/overlay/testcommunity/{surface}")
    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("text/html")
