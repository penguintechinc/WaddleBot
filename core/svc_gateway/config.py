"""Configuration for svc-gateway.

Env var names follow the repo-standard `MODULE_NAME`/`MODULE_PORT` pattern
(`core/svc_ingest/config.py`), plus this container's own receiver/fan-out
wiring. `SECRET_KEY` is unused today (svc-gateway mints no service JWT of
its own -- it never calls hub-api's distribution endpoint, see
`fanout.py`'s module docstring for why) but kept for parity with every
other pipeline-stage container's config shape in case a future receiver
needs it (e.g. an OIDC-authenticated webhook alongside the gateway socket).
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Runtime configuration for svc-gateway."""

    MODULE_NAME = os.getenv("MODULE_NAME", "svc-gateway")
    MODULE_VERSION = "0.1.0"
    MODULE_PORT = int(os.getenv("MODULE_PORT", "8209"))
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    VALKEY_URL = os.getenv("VALKEY_URL", "redis://localhost:6379/0")

    # This process's own tenant scope for fan-out (`fanout.py`) -- mirrors
    # svc-ingest's `RUNNER_TENANT_SLUG`. A real multi-tenant guild->tenant
    # mapping is out of scope for this PR (no such lookup exists anywhere
    # in this codebase yet, see the PR description); every fanned-out
    # event resolves against this single fixed tenant.
    RUNNER_TENANT_SLUG = os.getenv("RUNNER_TENANT_SLUG", "global")

    # Discord gateway receiver. Empty string (never committed, never
    # logged) disables the receiver entirely -- `app.py`'s startup skips
    # it gracefully, matching `trigger/receiver/discord_module/app.py`'s
    # own "DISCORD_BOT_TOKEN not configured" skip behavior.
    DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")

    # ReceiverSupervisor backoff bounds (mirrors flask_core.stage_runner's
    # BundlePoller defaults -- same shape, different subject: restarting a
    # died receiver task instead of retrying a poll).
    BASE_BACKOFF_S = float(os.getenv("BASE_BACKOFF_S", "1.0"))
    MAX_BACKOFF_S = float(os.getenv("MAX_BACKOFF_S", "60.0"))
