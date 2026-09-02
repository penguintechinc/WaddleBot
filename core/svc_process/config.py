"""Configuration for svc-process. Mirrors `core/svc_ingest/config.py` -- see its docstring."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from flask_core.secrets import require_secret_key

load_dotenv()


def _optional_int(value: str | None) -> int | None:
    return int(value) if value not in (None, "") else None


class Config:
    """Runtime configuration for the svc-process stage-runner."""

    MODULE_NAME = os.getenv("MODULE_NAME", "svc-process")
    MODULE_VERSION = "0.1.0"
    MODULE_PORT = int(os.getenv("MODULE_PORT", "8211"))
    PIPELINE_STAGE = "process"
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    HUB_API_URL = os.getenv("HUB_API_URL", "http://hub-api:8204")
    DISTRIBUTION_URL = os.getenv("DISTRIBUTION_URL", f"{HUB_API_URL}/api/v1/distribution/bundles")
    POLL_INTERVAL_S = float(os.getenv("POLL_INTERVAL_S", "5.0"))
    BASE_BACKOFF_S = float(os.getenv("BASE_BACKOFF_S", "1.0"))
    MAX_BACKOFF_S = float(os.getenv("MAX_BACKOFF_S", "60.0"))

    RUNNER_TENANT_SLUG = os.getenv("RUNNER_TENANT_SLUG", "global")
    RUNNER_COMMUNITY_ID = _optional_int(os.getenv("RUNNER_COMMUNITY_ID"))

    SECRET_KEY = require_secret_key()
    JWT_SCOPE = "distribution:read"

    VALKEY_URL = os.getenv("VALKEY_URL", "redis://localhost:6379/0")
