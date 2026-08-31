"""
Configuration for svc-streaming.

SCAFFOLD ONLY -- no external MarchProxy/LiveKit client wiring, no hub-api
control-plane client, no token-billing client yet (see the TODOs in app.py).
Env var names mirror what the Helm Deployment sets
(k8s/helm/waddlebot/templates/svc-streaming.yaml): MODULE_NAME/MODULE_PORT/
PIPELINE_STAGE come from there in cluster; everything else here has a
repo-standard local default so the app boots stand-alone for tests and
local dev.
"""
import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Runtime configuration for the svc-streaming control plane."""

    MODULE_NAME = os.getenv('MODULE_NAME', 'svc-streaming')
    MODULE_VERSION = '0.1.0'
    MODULE_PORT = int(os.getenv('MODULE_PORT', '8208'))
    PIPELINE_STAGE = os.getenv('PIPELINE_STAGE', 'streaming')
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

    # TODO(svc-streaming): hub-api control-plane client -- per-community
    # FORWARD target CRUD writes to the primary, routing reads (live status,
    # capability flags) from the read replica (design spec §3, same
    # stage-runner routing-read pattern as svc-presentation,
    # app-bundle-sdk-design.md §6.3; backend.md Database Tier Architecture).
    HUB_API_URL = os.getenv('HUB_API_URL', 'http://hub-api:8204')

    # TODO(svc-streaming): fronting external MarchProxy -- the RTMP relay
    # that does the real RTMP ingest + x265/AV1/x264 transcode + fan-out
    # (design spec §1, §6; env var names match
    # core/video_proxy_module/config.py:39-40 exactly -- svc-streaming is
    # the Rust/Quart-scaffold reimplementation of that control plane, not a
    # new integration). See app.py's _front_marchproxy_* stubs.
    MARCHPROXY_GRPC_HOST = os.getenv('MARCHPROXY_GRPC_HOST', 'localhost')
    MARCHPROXY_GRPC_PORT = int(os.getenv('MARCHPROXY_GRPC_PORT', '50050'))

    # TODO(svc-streaming): fronting external LiveKit -- the SFU that does
    # the real WebRTC media (design spec §1, §6; today's Go control plane,
    # core/module_rtc/go.mod:8-11, `livekit/protocol` + `server-sdk-go`).
    # See app.py's _front_livekit_* stub.
    LIVEKIT_HOST = os.getenv('LIVEKIT_HOST', '')
    LIVEKIT_API_KEY = os.getenv('LIVEKIT_API_KEY', '')

    # TODO(svc-streaming): transcoding-token metering -- ENCODE/TRANSCODE
    # (capability #6) calls hub-api marketplace's consume() at job
    # admission (design spec §5; PIPELINE_MAPPING.md:119,207:
    # `consume(community_id, consumable_type, amount, idempotency_key,
    # source_ref, actor)`, e.g. `consume('transcoding', units, job_id)`).
    # svc-streaming holds NO ledger DB grant -- internal call only.
    # See app.py's _consume_transcoding_tokens stub.
    TOKEN_CONSUME_URL = os.getenv(
        'TOKEN_CONSUME_URL', 'http://hub-api:8204/internal/tokens/consume'
    )
