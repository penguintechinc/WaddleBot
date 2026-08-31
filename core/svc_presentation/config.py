"""
Configuration for svc-presentation.

SCAFFOLD ONLY -- no hub-api client or read-replica DAL wiring yet (see the
TODOs in app.py). Env var names mirror what the Helm Deployment sets
(k8s/helm/waddlebot/templates/svc-presentation.yaml): MODULE_NAME/
MODULE_PORT/PIPELINE_STAGE come from there in cluster; everything else here
has a repo-standard local default so the app boots stand-alone for tests
and local dev.
"""
import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Runtime configuration for the svc-presentation stage-runner."""

    MODULE_NAME = os.getenv('MODULE_NAME', 'svc-presentation')
    MODULE_VERSION = '0.1.0'
    MODULE_PORT = int(os.getenv('MODULE_PORT', '8207'))
    PIPELINE_STAGE = os.getenv('PIPELINE_STAGE', 'presentation')
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

    # TODO(svc-presentation): hub-api poll target for the installed
    # presentation-component set. docs/plans/2026-08-31-app-bundle-sdk-design.md
    # §6.2 -- GET {HUB_API_URL}/api/v1/apps/installed?stage=presentation,
    # polled every HUB_API_POLL_INTERVAL_SECONDS. See app.py's
    # _poll_installed_presentation_components stub.
    HUB_API_URL = os.getenv('HUB_API_URL', 'http://hub-api:8204')
    HUB_API_POLL_INTERVAL_SECONDS = int(
        os.getenv('HUB_API_POLL_INTERVAL_SECONDS', '30')
    )

    # TODO(svc-presentation): read-only DSN for per-community
    # activation/routing reads against the READ REPLICA, never the primary
    # hub-api holds. docs/plans/2026-08-31-app-bundle-sdk-design.md §6.3;
    # backend.md Database Tier Architecture (per-service scoped DB account).
    # See app.py's _read_community_activations stub.
    READ_REPLICA_DATABASE_URL = os.getenv('READ_REPLICA_DATABASE_URL', '')
