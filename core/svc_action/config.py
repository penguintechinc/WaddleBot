"""svc-action service configuration.

Env-driven configuration for the ACTION stage-runner (Helm skeleton:
k8s/helm/waddlebot/templates/svc-action.yaml, values.yaml
`pipeline.svcAction.port: 8202`). Mirrors hub_api/config.py's pattern
(frozen slotted dataclass, `from_env()`, DB_TYPE/DB_HOST/DB_PORT/DB_NAME/
DB_USER/DB_PASS -> pydal URI) -- see that module's docstring for the
rationale. svc-action holds a READ-ONLY DB account (`DB_USER` defaults to
`svc-action-ro`) -- it only ever reads `app_activations`/
`app_tenant_availability` to resolve a bundle's declared action target
(services/config_lookup.py); it never writes app-bundle tables.

Queue connection: Valkey (backend.md "Use Valkey, not bitnami/redis").
`VALKEY_URL` is the primary env var per this task's spec; the Helm chart's
existing secret currently only sets `REDIS_URL` (same connection, older
name shared by every other module) -- `VALKEY_URL` is read first so this
service is forward-compatible with the eventual rename, falling back to
`REDIS_URL` so it works against the chart as it exists today without a
Helm change.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import quote_plus

#: DB_TYPE values understood -- backend-database.md Database Support Matrix
#: minus MariaDB Galera (not needed for this service's narrow read-only use).
_DB_URI_SCHEMES: dict[str, str] = {
    "postgresql": "postgres",  # pydal wants postgres://, not postgresql://
    "mysql": "mysql",
    "sqlite": "sqlite",
}


def _bool_env(name: str, default: bool) -> bool:
    """Parse a boolean env var; anything not in the truthy set is False."""
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _build_db_url(
    *, db_type: str, host: str, port: str, name: str, user: str, password: str
) -> str:
    """Build a pydal-compatible DB URI from DB_TYPE + components."""
    scheme = _DB_URI_SCHEMES.get(db_type)
    if scheme is None:
        raise ValueError(
            f"unsupported DB_TYPE {db_type!r} -- expected one of {sorted(_DB_URI_SCHEMES)}"
        )
    if scheme == "sqlite":
        return f"sqlite:{name}"
    if password:
        return f"{scheme}://{user}:{quote_plus(password)}@{host}:{port}/{name}"
    return f"{scheme}://{user}@{host}:{port}/{name}"


@dataclass(slots=True, frozen=True)
class ActionConfig:
    """Validated, immutable svc-action configuration -- built once via `from_env()`."""

    module_name: str
    module_version: str
    module_port: int
    pipeline_stage: str
    log_level: str

    # Valkey (process -> action queue; libs/flask_core/flask_core/
    # stream_pipeline.py bundle_stream_key(..., stage="action") key scheme).
    valkey_url: str
    queue_scan_pattern: str
    queue_scan_interval_seconds: float
    queue_block_timeout_seconds: int

    # Read-only DB account -- action-target config lookup + dispatch-log writes.
    database_url: str
    db_pool_size: int

    # Outbound HTTP dispatch (webhook/rest_api/overlay adapters).
    http_timeout_seconds: float
    max_retries: int
    retry_initial_delay: float
    retry_max_delay: float

    # overlay adapter target -- svc-presentation's push endpoint.
    presentation_base_url: str

    # email adapter (aiosmtplib).
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    smtp_use_tls: bool
    smtp_from_addr: str

    @classmethod
    def from_env(cls) -> ActionConfig:
        """Build config from the process environment. Raises on an invalid DB_TYPE."""
        db_type = os.getenv("DB_TYPE", "postgresql")
        database_url = os.getenv("DATABASE_URL") or _build_db_url(
            db_type=db_type,
            host=os.getenv("DB_HOST", "infra-postgres"),
            port=os.getenv("DB_PORT", "5432"),
            name=os.getenv("DB_NAME", "waddlebot"),
            user=os.getenv("DB_USER", "svc-action-ro"),
            password=os.getenv("DB_PASS", ""),
        )

        valkey_url = os.getenv("VALKEY_URL") or os.getenv("REDIS_URL") or "redis://localhost:6379/0"

        return cls(
            module_name=os.getenv("MODULE_NAME", "svc-action"),
            module_version=os.getenv("MODULE_VERSION", "0.1.0"),
            module_port=int(os.getenv("MODULE_PORT", "8202")),
            pipeline_stage=os.getenv("PIPELINE_STAGE", "action"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            valkey_url=valkey_url,
            queue_scan_pattern=os.getenv(
                "ACTION_QUEUE_SCAN_PATTERN", "waddles:t:*:c:*:app:*:action"
            ),
            queue_scan_interval_seconds=float(os.getenv("ACTION_QUEUE_SCAN_INTERVAL_SECONDS", "5")),
            queue_block_timeout_seconds=int(os.getenv("ACTION_QUEUE_BLOCK_TIMEOUT_SECONDS", "5")),
            database_url=database_url,
            db_pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
            http_timeout_seconds=float(os.getenv("ACTION_HTTP_TIMEOUT_SECONDS", "10")),
            max_retries=int(os.getenv("ACTION_MAX_RETRIES", "3")),
            retry_initial_delay=float(os.getenv("ACTION_RETRY_INITIAL_DELAY", "1.0")),
            retry_max_delay=float(os.getenv("ACTION_RETRY_MAX_DELAY", "30.0")),
            presentation_base_url=os.getenv("PRESENTATION_URL", "http://svc-presentation:8207"),
            smtp_host=os.getenv("SMTP_HOST", "localhost"),
            smtp_port=int(os.getenv("SMTP_PORT", "587")),
            smtp_user=os.getenv("SMTP_USER", ""),
            smtp_password=os.getenv("SMTP_PASS", ""),
            smtp_use_tls=_bool_env("SMTP_USE_TLS", True),
            smtp_from_addr=os.getenv("SMTP_FROM_ADDR", "noreply@waddlebot.com"),
        )
