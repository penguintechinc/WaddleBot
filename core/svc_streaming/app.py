"""
svc-streaming -- Quart application entrypoint.

SCAFFOLD ONLY. Streaming module's control plane (RTC + broadcast media,
docs/plans/2026-08-31-svc-streaming-design.md §1). Per that spec's
load-bearing correction: this repo has NO first-party media engine --
svc-streaming is a CONTROL PLANE fronting two EXTERNAL media engines
(MarchProxy for RTMP ingest/AV1 transcode/fan-out,
core/video_proxy_module/config.py:39-40; LiveKit for the WebRTC SFU,
core/module_rtc/go.mod:8-11). Build vs keep-external is an OPEN decision
(spec §8.1) -- this scaffold builds neither, only the control-plane HTTP
surface that will eventually orchestrate one or the other.

Every capability below (INGEST/DISPLAY/FORWARD/premium_limits/RECORD/
TRANSCODE/RTC) is its own PostHog feature flag under `waddles.streaming.*`
(spec §2) -- flag checks are NOT wired in this scaffold (TODO); routes are
unconditionally stubbed.

The word "restream" is never used anywhere in this file or its docs --
"forward" / "stream-forwarding" / "forward to targets" only (spec
Terminology, mandatory).
"""
from __future__ import annotations

import re

from flask_core import create_health_blueprint, setup_aaa_logging
from quart import Blueprint, Quart, jsonify, request

from config import Config

app = Quart(__name__)

# /health, /healthz, /metrics -- flask_core standard blueprint, same as
# every other pipeline-stage container. k8s liveness/readiness probes
# (k8s/helm/waddlebot/templates/svc-streaming.yaml) point at /health.
health_bp = create_health_blueprint(Config.MODULE_NAME, Config.MODULE_VERSION)
app.register_blueprint(health_bp)

logger = setup_aaa_logging(Config.MODULE_NAME, Config.MODULE_VERSION)

streams_bp = Blueprint('streams', __name__, url_prefix='/streams')

# Loose slug validation for path params -- security.md Input Validation
# (server-side validation on client input) applies even to a stub response.
_SLUG_RE = re.compile(r'^[a-zA-Z0-9_-]{1,64}$')


def _not_implemented(detail: str) -> tuple[dict, int]:
    """Build the standard scaffold 501 body -- every stub route returns this shape."""
    return {"status": "not_implemented", "detail": detail}, 501


async def _front_marchproxy_ingest(community_id: str, source: str) -> None:
    """
    TODO(svc-streaming): front external MarchProxy for INGEST (capability
    #1) -- open an RTMP/HLS intake session against MarchProxy's gRPC
    control API (`Config.MARCHPROXY_GRPC_HOST`/`MARCHPROXY_GRPC_PORT`,
    matching `core/video_proxy_module/config.py:39-40`; today's
    `proto/video_proxy.proto` `VideoProxyService`). Gated on the
    `waddles.streaming.ingest` PostHog flag (spec §2) -- not checked here.

    See: docs/plans/2026-08-31-svc-streaming-design.md §3, §6
    """
    raise NotImplementedError(
        "svc-streaming: MarchProxy ingest front-end not implemented (scaffold)"
    )


async def _front_marchproxy_transcode(community_id: str, stream_id: str, profile: str) -> None:
    """
    TODO(svc-streaming): front external MarchProxy for ENCODE/TRANSCODE
    (capability #6) -- request a transcode profile from MarchProxy,
    gated on `waddles.streaming.transcode` (Professional + metered
    tokens, spec §2) AND a successful `_consume_transcoding_tokens` call
    at job admission (spec §5) BEFORE starting the job. Never kill an
    in-flight job on balance exhaustion -- block only new job starts
    (spec §5 enforcement posture).

    See: docs/plans/2026-08-31-svc-streaming-design.md §5, §6
    """
    raise NotImplementedError(
        "svc-streaming: MarchProxy transcode front-end not implemented (scaffold)"
    )


async def _front_livekit_rtc(community_id: str, room: str) -> None:
    """
    TODO(svc-streaming): front external LiveKit for RTC (capability #7,
    the folded-in `svc-rtc`/`module_rtc`) -- room create/join-JWT/
    moderation control reimplemented against LiveKit's control API
    (today's Go control plane: `core/module_rtc/internal/services/
    room_service.go:53-178`, `call_features.go:32-106`). Gated on
    `waddles.streaming.rtc` (spec §2).

    See: docs/plans/2026-08-31-svc-streaming-design.md §6
    """
    raise NotImplementedError(
        "svc-streaming: LiveKit RTC front-end not implemented (scaffold)"
    )


async def _consume_transcoding_tokens(community_id: str, units: int, job_id: str) -> None:
    """
    TODO(svc-streaming): metered transcoding-token consumption -- call
    hub-api marketplace's `consume()` at transcode job admission via
    `Config.TOKEN_CONSUME_URL` (internal `POST /internal/tokens/consume`,
    signature `consume(community_id, consumable_type, amount,
    idempotency_key, source_ref, actor)`, e.g.
    `consume('transcoding', units, job_id)` --
    `k8s/helm/waddlebot/PIPELINE_MAPPING.md:119,207`). svc-streaming holds
    NO ledger DB grant (marketplace account is single-writer) -- this is
    the only way tokens are ever decremented.

    Cross-ref: docs/plans/2026-08-31-metered-token-billing-design.md
               docs/plans/2026-08-31-svc-streaming-design.md §5
    """
    raise NotImplementedError(
        "svc-streaming: transcoding-token consume() call not implemented (scaffold)"
    )


async def _aggregate_live_status(community_id: str) -> None:
    """
    TODO(svc-streaming): live-streams aggregation (DISPLAY, capability #2)
    -- merge (a) this community's own svc-streaming ingest/forward
    sessions with (b) the per-connected-channel live-status projection
    that Twitch EventSub (`trigger/receiver/twitch_module/
    eventsub_handler.py:215-236`, already emits `stream_online`/
    `stream_offline`) and YouTube WebSub/poll
    (`trigger/receiver/youtube_live_module/webhook_handler.py`,
    `youtube_client.py:141-178`) already detect -- detection exists
    today, only the projection + aggregation are new (spec §4, §4.1).
    Read from the read replica, never primary (backend.md Database Tier).
    Rendered by svc-presentation, NOT served as HTML from this route
    (spec §3) -- this endpoint returns the raw projection only.

    See: docs/plans/2026-08-31-svc-streaming-design.md §4, §4.1, §8.6
    """
    raise NotImplementedError(
        "svc-streaming: live-status aggregation not implemented (scaffold)"
    )


@streams_bp.route('', methods=['GET'])
async def list_streams():
    """
    STUB -- list this community's active/known streams. Real
    implementation reads per-community stream state from the read
    replica (spec §3) once `_aggregate_live_status`/hub-api client wiring
    lands.
    """
    body, status = _not_implemented(
        "list streams: hub-api read-replica client not wired (scaffold)"
    )
    return jsonify(body), status


@streams_bp.route('', methods=['POST'])
async def create_stream():
    """
    STUB -- create/ingest a new stream (capability #1, INGEST). Real
    implementation validates the request body, checks the
    `waddles.streaming.ingest` flag + tier entitlement, and calls
    `_front_marchproxy_ingest`.
    """
    await request.get_json(force=True, silent=True)
    try:
        await _front_marchproxy_ingest(community_id="", source="")
    except NotImplementedError as exc:
        body, status = _not_implemented(str(exc))
        return jsonify(body), status
    return jsonify({"status": "created"}), 201  # pragma: no cover - unreachable in scaffold


@streams_bp.route('/<stream_id>/forward', methods=['POST'])
async def add_forward_target(stream_id: str):
    """
    STUB -- add a FORWARD target for an existing stream (capability #3/#4,
    spec §3's `stream_destinations` model). Real implementation validates
    `stream_id`, checks `waddles.streaming.forward` +
    `waddles.streaming.premium_limits` tier limits, resolves the target
    stream key via a `penguin-sal` reference (never inline, spec §8.4),
    and writes to hub-api's primary.
    """
    if not _SLUG_RE.match(stream_id):
        return jsonify({"status": "invalid_stream_id"}), 400
    await request.get_json(force=True, silent=True)
    body, status = _not_implemented(
        "add forward target: hub-api destination CRUD not wired (scaffold)"
    )
    return jsonify(body), status


@streams_bp.route('/live', methods=['GET'])
async def live_status():
    """
    STUB -- live-status projection endpoint (DISPLAY aggregation, spec
    §4). Consumed by svc-presentation's community "live streams" section,
    not rendered as HTML here (spec §3).
    """
    try:
        await _aggregate_live_status(community_id="")
    except NotImplementedError as exc:
        body, status = _not_implemented(str(exc))
        return jsonify(body), status
    return jsonify({"streams": []}), 200  # pragma: no cover - unreachable in scaffold


app.register_blueprint(streams_bp)


if __name__ == "__main__":  # pragma: no cover - process entrypoint, not exercised by unit tests
    import asyncio

    import hypercorn.asyncio
    from hypercorn.config import Config as HyperConfig

    hyper_config = HyperConfig()
    hyper_config.bind = [f"0.0.0.0:{Config.MODULE_PORT}"]
    asyncio.run(hypercorn.asyncio.serve(app, hyper_config))
