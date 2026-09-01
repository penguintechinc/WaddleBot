"""Configuration for svc-ingest.

Env var names follow the repo-standard `MODULE_NAME`/`MODULE_PORT` pattern
(`core/svc_streaming/config.py`), plus this stage-runner's own distribution-
poll and Valkey wiring. `SECRET_KEY` mirrors `flask_core.tenancy`/`authz`'s
own `os.getenv("SECRET_KEY", ...)` lookup -- the runner mints its own
short-lived service JWT (`app.py`'s `_jwt_provider`) with the same shared
secret hub-api's `tenant_middleware`/`require_scope` verify against
(security.md Service-to-Service Auth: short-lived signed machine JWT,
OIDC-machine-JWT fallback where SPIFFE/SPIRE isn't deployed in this
environment yet -- this service is SPIFFE-ready in the sense that nothing
here precludes swapping the JWT for an mTLS/X.509-SVID identity later, that
wiring itself is out of scope for this PR).
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


def _optional_int(value: str | None) -> int | None:
    return int(value) if value not in (None, "") else None


class Config:
    """Runtime configuration for the svc-ingest stage-runner."""

    MODULE_NAME = os.getenv("MODULE_NAME", "svc-ingest")
    MODULE_VERSION = "0.1.0"
    MODULE_PORT = int(os.getenv("MODULE_PORT", "8210"))
    PIPELINE_STAGE = "ingest"
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    # Distribution API (hub_api/blueprints/v1/distribution.py) poll wiring.
    HUB_API_URL = os.getenv("HUB_API_URL", "http://hub-api:8204")
    DISTRIBUTION_URL = os.getenv("DISTRIBUTION_URL", f"{HUB_API_URL}/api/v1/distribution/bundles")
    POLL_INTERVAL_S = float(os.getenv("POLL_INTERVAL_S", "5.0"))
    BASE_BACKOFF_S = float(os.getenv("BASE_BACKOFF_S", "1.0"))
    MAX_BACKOFF_S = float(os.getenv("MAX_BACKOFF_S", "60.0"))

    # This runner instance's own tenant/community scope -- security.md
    # Tenant Isolation: never widened at request time, fixed at deploy time
    # via this env var, matching the JWT `tenant` claim the runner mints
    # for itself.
    RUNNER_TENANT_SLUG = os.getenv("RUNNER_TENANT_SLUG", "global")
    RUNNER_COMMUNITY_ID = _optional_int(os.getenv("RUNNER_COMMUNITY_ID"))

    # Shared HS256 secret -- mirrors flask_core.tenancy/authz's own
    # os.getenv("SECRET_KEY", "change-me-in-production") fallback exactly,
    # so a token minted here verifies against hub-api's own decorators.
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
    JWT_SCOPE = "distribution:read"

    VALKEY_URL = os.getenv("VALKEY_URL", "redis://localhost:6379/0")
