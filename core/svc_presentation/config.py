"""Configuration for svc-presentation.

Env-driven, frozen/slotted dataclass -- same shape as `hub_api/config.py`'s
`HubAPIConfig` (`_build_db_url` copied verbatim: same `DB_TYPE`/`DB_HOST`/
`DB_PORT`/`DB_NAME`/`DB_USER`/`DB_PASS` env vars, backend-database.md
Database Support Matrix). svc-presentation gets its own `DB_USER`/`DB_PASS`
pair in deployment (backend-database.md Per-Service Database Accounts) even
though the Helm chart's `envFrom` currently injects the same shared
`DATABASE_URL`/`DB_*` configmap/secret every pipeline-stage container reads
today (`k8s/helm/waddlebot/templates/configmap.yaml`,`secrets.yaml`) --
provisioning a dedicated scoped account is deployment/infra follow-up, not
a code change here.

Valkey: the Helm chart's shared secret exports `REDIS_URL` (Valkey is the
deployed engine, `values.yaml`'s `infrastructure.redis.image:
valkey/valkey:8-bookworm`, keyed under the historical `redis` name) --
`VALKEY_URL` is the name this service's own env contract uses so the
config/code reads correctly regardless of which name a given deployment
sets, preferring `VALKEY_URL` and falling back to the already-provisioned
`REDIS_URL` so this boots against the real cluster secret with zero Helm
changes.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import quote_plus

#: Mirrors hub_api/config.py's own scheme map (backend-database.md Database
#: Support Matrix minus MariaDB Galera).
_DB_URI_SCHEMES: dict[str, str] = {
    "postgresql": "postgres",
    "mysql": "mysql",
    "sqlite": "sqlite",
}


def _build_db_url(
    *,
    db_type: str,
    host: str,
    port: str,
    name: str,
    user: str,
    password: str,
) -> str:
    """Build a pydal-compatible DB URI from DB_TYPE + components (hub_api/config.py twin)."""
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
class Config:
    """Validated, immutable svc-presentation configuration -- built once via `from_env()`."""

    module_name: str
    module_version: str
    module_port: int
    pipeline_stage: str
    log_level: str

    database_url: str
    database_read_replica_url: str | None
    db_pool_size: int

    valkey_url: str | None

    hub_api_url: str
    hub_api_poll_interval_seconds: int

    #: Bearer token gate on the push endpoint (`POST /overlay/<c>/<s>/push`)
    #: -- action-stage overlay adapters authenticate with it. Empty string
    #: means "not yet provisioned" (dev-friendly open default, same posture
    #: `core/svc_streaming/config.py` documents for its own unwired
    #: LIVEKIT_API_KEY) -- real SPIFFE/OIDC machine-JWT service-to-service
    #: auth (security.md) is follow-up work once an actual caller exists.
    push_token: str

    #: Namespace/key convention the JSON music-queue read matches exactly --
    #: `core/unified_music_module/services/unified_queue.py`'s
    #: `UnifiedQueue._make_key` (`f"{namespace}:{community_id}:queue"`,
    #: `unified_queue.py:180-182`). hub-api has no `GET .../music/queue`
    #: endpoint today (confirmed: `hub_api/blueprints/v1/music.py` only
    #: exposes settings/providers/radio-stations); reading this Redis/
    #: Valkey key directly is the only real, already-implemented source of
    #: per-community queue state (music-station-design.md §4 table: "
    #: presentation container's queue-state read" = `UnifiedQueue.
    #: get_queue(community_id)`).
    music_queue_namespace: str

    @classmethod
    def from_env(cls) -> Config:
        """Build config from the process environment. Raises on an invalid DB_TYPE."""
        db_type = os.getenv("DB_TYPE", "postgresql")
        database_url = os.getenv("DATABASE_URL") or _build_db_url(
            db_type=db_type,
            host=os.getenv("DB_HOST", "infra-postgres"),
            port=os.getenv("DB_PORT", "5432"),
            name=os.getenv("DB_NAME", "waddlebot"),
            user=os.getenv("DB_USER", "svc-presentation-rw"),
            password=os.getenv("DB_PASS", ""),
        )
        read_replica_url = os.getenv("DATABASE_READ_REPLICA_URL") or None

        return cls(
            module_name=os.getenv("MODULE_NAME", "svc-presentation"),
            module_version=os.getenv("MODULE_VERSION", "0.2.0"),
            module_port=int(os.getenv("MODULE_PORT", "8207")),
            pipeline_stage=os.getenv("PIPELINE_STAGE", "presentation"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            database_url=database_url,
            database_read_replica_url=read_replica_url,
            db_pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
            valkey_url=os.getenv("VALKEY_URL") or os.getenv("REDIS_URL") or None,
            hub_api_url=os.getenv("HUB_API_URL", "http://hub-api:8204"),
            hub_api_poll_interval_seconds=int(os.getenv("HUB_API_POLL_INTERVAL_SECONDS", "30")),
            push_token=os.getenv("PRESENTATION_PUSH_TOKEN", ""),
            music_queue_namespace=os.getenv("MUSIC_QUEUE_NAMESPACE", "music_queue"),
        )
