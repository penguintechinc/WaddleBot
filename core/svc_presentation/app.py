"""
svc-presentation -- Quart application entrypoint.

SCAFFOLD ONLY. The 8th container / 4th stage-runner
(docs/plans/2026-08-31-music-station-design.md §8): renders, per community,
(a) core overlays (full_screen/media/crawler), (b) the Music Station, and
(c) each activated bundle's own `presentation` component (HTML/JS overlay).
Follows the same poll+reconcile distribution model as the other three
stage-runners (docs/plans/2026-08-31-app-bundle-sdk-design.md §6) and
supersedes/absorbs core/browser_source_core_module's per-community
browser-source role -- that module coexists until cutover, not touched here.

Real rendering, hub-api polling, and read-replica routing reads are NOT
implemented -- see the three TODO-marked stub functions below.
"""
from __future__ import annotations

import html
import re

from flask_core import create_health_blueprint, setup_aaa_logging
from quart import Blueprint, Quart

from config import Config

app = Quart(__name__)

# /health, /healthz, /metrics -- flask_core standard blueprint, same as
# every other pipeline-stage container. k8s liveness/readiness probes
# (k8s/helm/waddlebot/templates/svc-presentation.yaml) point at /health.
health_bp = create_health_blueprint(Config.MODULE_NAME, Config.MODULE_VERSION)
app.register_blueprint(health_bp)

logger = setup_aaa_logging(Config.MODULE_NAME, Config.MODULE_VERSION)

overlay_bp = Blueprint('overlay', __name__, url_prefix='/overlay')

# Loose slug validation for path params that get reflected into the
# placeholder HTML below -- security.md Input Validation (server-side
# validation on client input) applies even to a stub response.
_SLUG_RE = re.compile(r'^[a-zA-Z0-9_-]{1,64}$')


async def _poll_installed_presentation_components() -> None:
    """
    TODO(svc-presentation): poll hub-api for the installed bundle set
    scoped to the `presentation` stage and reconcile local overlay/asset
    code against it -- same poll+reconcile model as svc-ingest/process/
    action (app-bundle-sdk-design.md §6.2).

    Target: ``GET {Config.HUB_API_URL}/api/v1/apps/installed?stage=presentation``
    on an interval of ``Config.HUB_API_POLL_INTERVAL_SECONDS``.
    ``KNOWN_SURFACES`` (libs/flask_core/flask_core/app_manifest.py, today
    ``{ingest, process, action}``) needs a `presentation` entry first --
    that's follow-up work on the bundle SDK spec, not this scaffold.

    See: docs/plans/2026-08-31-app-bundle-sdk-design.md §6.2
         docs/plans/2026-08-31-music-station-design.md §8.1
    """
    raise NotImplementedError(
        "svc-presentation: hub-api poll+reconcile not implemented (scaffold)"
    )


async def _read_community_activations(community_id: str) -> None:
    """
    TODO(svc-presentation): read per-community activation/routing -- which
    core overlays are enabled, Music Station policy, which activated
    bundles declare a `presentation` component -- from the READ REPLICA,
    never the primary hub-api holds. Read-only DB account per backend.md's
    Database Tier Architecture.

    See: docs/plans/2026-08-31-app-bundle-sdk-design.md §6.3
    """
    raise NotImplementedError(
        "svc-presentation: read-replica routing read not implemented (scaffold)"
    )


async def _render_surface(community_id: str, surface: str) -> str:
    """
    TODO(svc-presentation): render the requested surface for real -- a core
    overlay (full_screen/media/crawler), the Music Station player, or an
    activated bundle's own presentation component (HTML/JS asset + a live
    queue-state channel, music-station-design.md §8.4) -- using the results
    of `_poll_installed_presentation_components` and
    `_read_community_activations` above. Also needs the per-community
    overlay-token auth model (docs/browser_source_core_module/API.md
    "Overlay Key Authentication", extended per app-bundle-sdk-design.md
    §8.3) -- not wired in this scaffold; this route is currently open.

    Returns a placeholder page so the route is exercisable end-to-end
    before the real renderer exists.
    """
    safe_community = html.escape(community_id)
    safe_surface = html.escape(surface)
    return (
        "<!DOCTYPE html><html><head><title>svc-presentation stub</title></head>"
        "<body><h1>svc-presentation placeholder</h1>"
        f"<p>community={safe_community} surface={safe_surface}</p>"
        "<p>Real rendering not implemented yet -- see _render_surface() TODO "
        "in core/svc_presentation/app.py.</p>"
        "</body></html>"
    )


@overlay_bp.route('/<community>/<surface>')
async def overlay(community: str, surface: str):
    """
    STUB per-community browser-source route. OBS points a browser source at
    this URL per community + surface (e.g. `full_screen`, `media`,
    `crawler`, `music_station`, or a bundle's own surface name). Returns a
    placeholder page -- see `_render_surface` for the real-rendering TODO.
    """
    if not (_SLUG_RE.match(community) and _SLUG_RE.match(surface)):
        return "invalid community or surface", 400
    body = await _render_surface(community, surface)
    return body, 200, {"Content-Type": "text/html; charset=utf-8"}


app.register_blueprint(overlay_bp)


if __name__ == "__main__":  # pragma: no cover - process entrypoint, not exercised by unit tests
    import asyncio

    import hypercorn.asyncio
    from hypercorn.config import Config as HyperConfig

    hyper_config = HyperConfig()
    hyper_config.bind = [f"0.0.0.0:{Config.MODULE_PORT}"]
    asyncio.run(hypercorn.asyncio.serve(app, hyper_config))
