"""Core overlay surfaces (`full_screen`/`media`/`crawler`) + the generic live/push routes.

Route shapes:
    GET  /overlay/<community>/full_screen        -- render the full_screen surface
    GET  /overlay/<community>/media               -- render the media surface
    GET  /overlay/<community>/crawler              -- render the crawler surface
    GET  /overlay/<community>/<surface>/live        -- SSE live-update channel (any known surface)
    POST /overlay/<community>/<surface>/push        -- action-stage adapters push content here

`music` is its own surface (`blueprints/music.py`) but shares this
module's `/live` and `/push` routes -- both are surface-generic.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from typing import Any

from quart import Blueprint, Response, current_app, jsonify, request

from services.presentation_config_service import get_theme_config, is_surface_enabled
from services.presentation_hub import PresentationHub
from services.render import RENDERERS
from services.surfaces import KNOWN_SURFACES, is_valid_community

logger = logging.getLogger(__name__)

overlay_bp = Blueprint("overlay", __name__, url_prefix="/overlay")

#: SSE heartbeat comment, sent while a connection is otherwise idle, so
#: intermediary proxies/OBS's embedded Chromium don't time the connection
#: out on a long silence -- a real keep-alive, not decorative.
_HEARTBEAT_INTERVAL_SECONDS = 15


def _dal() -> tuple[Any, Any]:
    """Return `(async_dal, dal)` from app config -- set at startup, see `app.py`."""
    return current_app.config["async_dal"], current_app.config["dal"]


def _hub() -> PresentationHub:
    """Return this process's `PresentationHub` -- set at startup, see `app.py`."""
    return current_app.config["PRESENTATION_HUB"]  # type: ignore[no-any-return]


@overlay_bp.route("/<community>/<surface>")
async def render_core_surface(community: str, surface: str) -> Any:
    """Render one of the three core overlay surfaces as a self-contained HTML page."""
    if not is_valid_community(community):
        return "invalid community", 400
    renderer = RENDERERS.get(surface)
    if renderer is None:
        return "unknown surface", 404

    async_dal, dal = _dal()
    if not await is_surface_enabled(async_dal, dal, community=community, surface=surface):
        return "surface disabled for this community", 404
    theme = await get_theme_config(async_dal, dal, community=community)

    body = renderer(
        community,
        surface,
        primary_color=theme.primary_color,
        secondary_color=theme.secondary_color,
        font_family=theme.font_family,
    )
    return body, 200, {"Content-Type": "text/html; charset=utf-8"}


@overlay_bp.route("/<community>/<surface>/live")
async def live(community: str, surface: str) -> Any:
    """SSE channel: streams every `push`ed payload for `community`/`surface` to this client."""
    if not is_valid_community(community):
        return "invalid community", 400
    if surface not in KNOWN_SURFACES:
        return "unknown surface", 404

    hub = _hub()
    queue = hub.register(community, surface)

    async def event_stream() -> AsyncGenerator[bytes, None]:
        try:
            yield _sse_event({"type": "connected", "community": community, "surface": surface})
            while True:
                try:
                    payload = await asyncio.wait_for(
                        queue.get(), timeout=_HEARTBEAT_INTERVAL_SECONDS
                    )
                    yield _sse_event(payload)
                except TimeoutError:
                    yield b": heartbeat\n\n"
        finally:
            hub.unregister(community, surface, queue)

    return Response(
        event_stream(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _sse_event(payload: dict[str, Any]) -> bytes:
    """Encode one Python dict as a single `data: ...\\n\\n` SSE frame."""
    return f"data: {json.dumps(payload)}\n\n".encode()


@overlay_bp.route("/<community>/<surface>/push", methods=["POST"])
async def push(community: str, surface: str) -> Any:
    """Push a content update out to every connected browser-source client.

    Bearer-token gated when `PRESENTATION_PUSH_TOKEN` is configured
    (`config.py`) -- open by default in environments that haven't
    provisioned one yet, matching this scaffold's pre-existing documented
    posture for not-yet-wired inter-service auth (`core/svc_streaming/
    config.py`'s `LIVEKIT_API_KEY`/etc). Real SPIFFE/OIDC machine-JWT
    service-to-service auth (security.md) is follow-up work once a real
    action-stage overlay adapter caller exists.
    """
    if not is_valid_community(community):
        return jsonify({"error": "invalid community"}), 400
    if surface not in KNOWN_SURFACES:
        return jsonify({"error": "unknown surface"}), 404

    push_token = current_app.config["APP_CONFIG"].push_token
    if push_token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header != f"Bearer {push_token}":
            return jsonify({"error": "unauthorized"}), 401

    payload = await request.get_json(force=True, silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "request body must be a JSON object"}), 400

    hub = _hub()
    await hub.publish(community, surface, payload)
    return jsonify({"status": "published", "community": community, "surface": surface}), 200


BLUEPRINTS: list[Blueprint] = [overlay_bp]
