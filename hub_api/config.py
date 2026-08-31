"""hub-api service configuration.

Env-driven configuration for the hub-api control-plane service (Task 0.5
skeleton -- docs/plans/2026-08-31-hubapi-node-to-quart-migration.md M0).
Every value is read from the environment (or an env var backed by a
secrets manager in real deployments); nothing here is a hardcoded
credential (security.md Secrets & Credentials). A frozen, slotted
dataclass rather than a mutable class-with-class-attrs (the pattern
several sibling `services/*/config.py` still use) -- see
`penguin-python-dev`'s Stack Decisions: `@dataclass(slots=True)` for
every data structure, `frozen=True` for a value object built once at
startup and never mutated.

Two field names deliberately mirror `flask_core` verbatim rather than
inventing a hub-api-local name: `secret_key` reads `SECRET_KEY` (not
`JWT_SECRET_KEY`) because `flask_core.tenancy.tenant_middleware` and
`flask_core.authz.require_scope` both call `os.getenv("SECRET_KEY", ...)`
directly at request time -- a differently-named env var here would leave
those decorators silently falling back to the
`"change-me-in-production"` default. Likewise `posthog_api_key`/
`posthog_host` mirror `flask_core.entitlement`'s own `POSTHOG_API_KEY`/
`POSTHOG_HOST` lookups. Config.from_env() exists so hub-api's own code
(logging, health blueprint naming, OpenAPI info) has one place to read
these from, while flask_core's decorators keep reading the environment
directly -- documented here rather than re-plumbed through app.config to
avoid a second, driftable source of truth.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import quote_plus

#: DB_TYPE values this config understands (backend-database.md Database
#: Support Matrix minus MariaDB Galera, which is not yet in hub-api's plan).
_DB_URI_SCHEMES: dict[str, str] = {
    "postgresql": "postgres",  # pydal wants postgres://, not postgresql://
    "mysql": "mysql",
    "sqlite": "sqlite",
}


def _bool_env(name: str, default: bool) -> bool:
    """Parse a boolean env var; anything not in the truthy set is False."""
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _build_db_url(
    *,
    db_type: str,
    host: str,
    port: str,
    name: str,
    user: str,
    password: str,
) -> str:
    """Build a pydal-compatible DB URI from DB_TYPE + components.

    backend-database.md's canonical env vars (DB_TYPE, DB_HOST, DB_PORT,
    DB_NAME, DB_USER, DB_PASS) in, one connection string out. sqlite
    ignores host/port/user/password -- `name` becomes the file path
    (or `:memory:`/`memory` for ephemeral/test use, matching
    libs/flask_core's own test fixtures, e.g. tests/test_tenancy.py).
    """
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
class HubAPIConfig:
    """Validated, immutable hub-api configuration -- built once via `from_env()`."""

    module_name: str
    module_version: str
    module_port: int
    grpc_port: int

    database_url: str
    database_read_replica_url: str | None
    db_pool_size: int
    db_max_retries: int
    db_retry_delay: int

    # Mirrors flask_core's own SECRET_KEY / HS256 lookup -- see module docstring.
    secret_key: str
    jwt_algorithm: str
    default_tenant_slug: str

    # flask_core.entitlement reads POSTHOG_API_KEY/POSTHOG_HOST directly;
    # kept here too so hub-api's own startup logging can report what's wired.
    posthog_api_key: str | None
    posthog_host: str
    license_server_url: str

    log_level: str

    @classmethod
    def from_env(cls) -> HubAPIConfig:
        """Build config from the process environment. Raises on an invalid DB_TYPE."""
        db_type = os.getenv("DB_TYPE", "postgresql")
        database_url = os.getenv("DATABASE_URL") or _build_db_url(
            db_type=db_type,
            host=os.getenv("DB_HOST", "infra-postgres"),
            port=os.getenv("DB_PORT", "5432"),
            name=os.getenv("DB_NAME", "waddlebot"),
            user=os.getenv("DB_USER", "hub-api-rw"),
            password=os.getenv("DB_PASS", ""),
        )

        read_replica_url = os.getenv("DATABASE_READ_REPLICA_URL")
        if not read_replica_url and os.getenv("DB_READ_REPLICA_HOST"):
            read_replica_url = _build_db_url(
                db_type=db_type,
                host=os.environ["DB_READ_REPLICA_HOST"],
                port=os.getenv("DB_READ_REPLICA_PORT", os.getenv("DB_PORT", "5432")),
                name=os.getenv("DB_NAME", "waddlebot"),
                user=os.getenv("DB_READ_REPLICA_USER", os.getenv("DB_USER", "hub-api-ro")),
                password=os.getenv("DB_READ_REPLICA_PASS", os.getenv("DB_PASS", "")),
            )

        return cls(
            module_name=os.getenv("MODULE_NAME", "hub-api"),
            module_version=os.getenv("MODULE_VERSION", "0.1.0"),
            module_port=int(os.getenv("MODULE_PORT", "8204")),
            grpc_port=int(os.getenv("GRPC_PORT", "50204")),
            database_url=database_url,
            database_read_replica_url=read_replica_url,
            db_pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
            db_max_retries=int(os.getenv("DB_MAX_RETRIES", "5")),
            db_retry_delay=int(os.getenv("DB_RETRY_DELAY", "5")),
            secret_key=os.getenv("SECRET_KEY", "change-me-in-production"),
            jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
            default_tenant_slug=os.getenv("DEFAULT_TENANT_SLUG", "global"),
            posthog_api_key=os.getenv("POSTHOG_API_KEY") or os.getenv("POSTHOG_KEY"),
            posthog_host=os.getenv("POSTHOG_HOST", "https://license.penguintech.io"),
            license_server_url=os.getenv("LICENSE_SERVER_URL", "https://license.penguintech.io"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )
