# Credential Manager Module — Architecture

This document describes the internal design of the Credential Manager Module: its components, data flows, encryption approach, credential type model, access control design, and key rotation strategy.

---

## Table of Contents

1. [Design Goals](#design-goals)
2. [Component Overview](#component-overview)
3. [Component Details](#component-details)
   - [Quart HTTP Application (app.py)](#quart-http-application-apppy)
   - [Config (config.py)](#config-configpy)
   - [RefreshService (services/refresh_service.py)](#refreshservice-servicesrefresh_servicepy)
   - [OAuthHandlers (services/oauth_handlers.py)](#oauthhandlers-servicesoauth_handlerspy)
4. [Credential Type Model](#credential-type-model)
5. [Data Flow — Token Refresh Cycle](#data-flow--token-refresh-cycle)
6. [Encryption at Rest](#encryption-at-rest)
7. [Access Control Model](#access-control-model)
8. [Redis Pub/Sub Design](#redis-pubsub-design)
9. [Key Rotation Design](#key-rotation-design)
10. [Database Schema Integration](#database-schema-integration)
11. [Connection Pooling](#connection-pooling)
12. [Retry and Backoff Strategy](#retry-and-backoff-strategy)
13. [Platform-Specific Handler Design](#platform-specific-handler-design)
14. [Error Propagation Model](#error-propagation-model)
15. [Operational Counters](#operational-counters)

---

## Design Goals

The Credential Manager Module was designed with the following priorities:

1. **Reliability**: Tokens must be refreshed before expiry without requiring manual intervention.
2. **Isolation**: Credential refresh logic is centralized in one module; no action module implements its own refresh.
3. **Observability**: Running state, cycle timestamps, and lifetime counters are exposed via the health endpoint.
4. **Security**: Credential values are never returned through the API. The module reads from and writes to the database only; external callers receive only metadata.
5. **Extensibility**: Adding a new platform requires only a new `BaseOAuthHandler` subclass and one entry in the `get_handler()` factory.
6. **Async performance**: The entire refresh pipeline is async (`asyncio`, `asyncpg`, `aioredis`, `httpx`), allowing concurrent handling of HTTP requests while the background poll loop runs.

---

## Component Overview

```
core/credential_manager_module/
├── app.py                         # Quart application, HTTP endpoints, lifecycle hooks
├── config.py                      # Config class, env var loading, validation,
│                                  # credential listener, DB loader
├── services/
│   ├── __init__.py
│   ├── refresh_service.py         # RefreshService — background poll loop, DB queries,
│                                  # token update, Redis publish
│   └── oauth_handlers.py          # BaseOAuthHandler, platform-specific handlers,
│                                  # get_handler() factory
├── requirements.txt               # Python dependencies
├── Dockerfile                     # Container image definition
└── test_credential_manager.py     # Integration and unit tests
```

---

## Component Details

### Quart HTTP Application (app.py)

The entry point. Uses [Quart](https://quart.palletsprojects.com/), an async-native web framework compatible with Flask's API.

**Responsibilities**:
- Validate configuration on startup via `Config.validate()`. Exit with code 1 if required variables are missing.
- Instantiate `RefreshService` with all required parameters sourced from `Config`.
- Start the `RefreshService` background task.
- Expose three HTTP endpoints: `/health`, `/api/v1/credentials/status`, `/api/v1/credentials/refresh-now`.
- Stop the `RefreshService` gracefully on shutdown.

**Lifecycle hooks**:

| Hook | When | Action |
|---|---|---|
| `@app.before_serving` (`startup`) | Before the first request is served | Instantiate and start `RefreshService` |
| `@app.after_serving` (`shutdown`) | After the last request completes during shutdown | Call `RefreshService.stop()` |

**Module-level globals**:

| Name | Type | Description |
|---|---|---|
| `app` | `Quart` | The WSGI/ASGI application instance |
| `refresh_service` | `RefreshService \| None` | The singleton service instance, set during startup |
| `_shutdown_event` | `asyncio.Event` | Reserved for future graceful shutdown signaling |

---

### Config (config.py)

A class of class-level attributes loaded from environment variables at import time. There is no `__init__`; all values are set when the module is first imported.

**Key attributes**:

| Attribute | Env Var | Type | Default | Purpose |
|---|---|---|---|---|
| `MODULE_NAME` | — | str | `"credential_manager"` | Identity string for health response |
| `MODULE_VERSION` | — | str | `"1.0.0"` | Version string for health response |
| `MODULE_PORT` | `MODULE_PORT` | int | `8095` | HTTP listen port |
| `DATABASE_URL` | `DATABASE_URL` | str | See config.py | PostgreSQL connection string |
| `REDIS_URL` | `REDIS_URL` | str | `redis://localhost:6379/0` | Redis connection string |
| `REDIS_KEY_PREFIX` | `REDIS_KEY_PREFIX` | str | `"credentials:"` | Prefix for Redis pub/sub channel names |
| `TOKEN_REFRESH_BUFFER` | `TOKEN_REFRESH_BUFFER` | int | `300` | Seconds before token expiry to trigger refresh |
| `POLL_INTERVAL` | `POLL_INTERVAL` | int | `60` | Seconds between poll cycles |
| `MAX_REFRESH_RETRIES` | `MAX_REFRESH_RETRIES` | int | `3` | Max retry attempts per token refresh |
| `RETRY_BACKOFF_BASE` | `RETRY_BACKOFF_BASE` | int | `5` | Base seconds for exponential backoff |
| `ENCRYPTION_KEY` | `PLATFORM_ENCRYPTION_KEY` | str | `""` | At-rest encryption key (see Encryption section) |
| `LOG_LEVEL` | `LOG_LEVEL` | str | `"INFO"` | Python logging level |

**URL normalization**: `DATABASE_URL` is stored internally with the `postgresql://` prefix normalized to `postgres://` for compatibility with PyDAL. The `RefreshService` converts it back to `postgresql://` for asyncpg.

**Thread-safe credential state**:
- `_credentials_loaded: bool` — tracks whether in-memory credentials have been loaded from the DB.
- `_credential_lock: threading.Lock` — protects `_credentials_loaded` from concurrent modification.

**`validate()` method**: Returns a list of error strings. Currently validates that `DATABASE_URL` and `REDIS_URL` are non-empty. Called at startup; any errors cause the process to exit.

**`load_credentials_from_db(db_connection)`**: Attempts to query the `platform_integrations` table for `credential_manager` bot credentials. Falls back to environment variable values if the query fails. Returns `True` if DB credentials were loaded.

**`start_credential_listener(redis_client)`**: Starts a daemon background thread that subscribes to `credentials:credential_manager:bot:refreshed`. On receiving a message, sets `_credentials_loaded = False` to invalidate the in-memory credential cache. Returns the thread, or `None` if Redis is not configured.

---

### RefreshService (services/refresh_service.py)

The core service. Runs as an asyncio background task. Holds connection pools for PostgreSQL (via `asyncpg`) and Redis (via `redis.asyncio`), and an HTTP client (via `httpx`).

**Slot-based memory layout**: Uses `__slots__` for all instance attributes, reducing per-instance memory overhead and preventing accidental attribute creation.

**Lifecycle**:

| Method | Description |
|---|---|
| `start()` | Create asyncpg pool, aioredis client, httpx client; launch `_poll_loop` as asyncio task |
| `stop()` | Cancel the poll task; close HTTP client, Redis connection, DB pool in order |
| `_poll_loop()` | Infinite loop: call `run_refresh_cycle()`, sleep `POLL_INTERVAL` seconds, repeat |
| `run_refresh_cycle()` | Query expiring tokens, refresh each, return count |
| `_refresh_token(integration)` | Refresh a single token with retry logic |
| `_call_refresh_endpoint(...)` | Delegate to platform-specific OAuth handler |
| `_update_tokens(...)` | Write new tokens to PostgreSQL |
| `_publish_refresh_event(...)` | Publish timestamp to Redis pub/sub channel |

**Observability state**:

| Attribute | Description |
|---|---|
| `_running` | Whether the service is active |
| `_last_cycle` | `datetime` of the last completed cycle |
| `_total_refreshed` | Lifetime count of successfully refreshed tokens |
| `_total_errors` | Lifetime count of errors (cycle-level and token-level) |

---

### OAuthHandlers (services/oauth_handlers.py)

Provides one handler class per supported platform, all implementing `BaseOAuthHandler`.

**`BaseOAuthHandler` (ABC)**:
- Defines `refresh_token(refresh_token, client_id, client_secret, config_data)` as an abstract method.
- Provides `_post_form(url, data, headers)` — an async helper that uses a fresh `httpx.AsyncClient` per call with a 10-second timeout.
- `TIMEOUT = 10` seconds class constant.

**Handler classes**:

| Class | Platform | Token URL | Auth Method |
|---|---|---|---|
| `TwitchOAuthHandler` | Twitch | `https://id.twitch.tv/oauth2/token` | Form body (`client_id`, `client_secret`) |
| `DiscordOAuthHandler` | Discord | `https://discord.com/api/v10/oauth2/token` | Form body (`client_id`, `client_secret`) |
| `SlackOAuthHandler` | Slack | `https://slack.com/api/oauth.v2.access` | Form body (`client_id`, `client_secret`) |
| `YouTubeOAuthHandler` | YouTube/Google | `https://oauth2.googleapis.com/token` | Form body (`client_id`, `client_secret`) |
| `SpotifyOAuthHandler` | Spotify | `https://accounts.spotify.com/api/token` | HTTP Basic Auth (`Authorization: Basic base64(client_id:client_secret)`) |
| `KickOAuthHandler` | Kick | `https://id.kick.com/oauth/token` | Form body (`client_id`, `client_secret`) |

**Platform-specific notes**:
- **Slack**: Validates the `ok` field in the response. Any response where `ok` is falsy raises `OAuthRefreshError`.
- **YouTube/Google**: Google does not return a new `refresh_token` on refresh. The existing refresh token is preserved unchanged.
- **Spotify**: Uses HTTP Basic Authentication with Base64-encoded `client_id:client_secret` rather than embedding them in the form body.

**`get_handler(platform)` factory**: Instantiates and returns the appropriate handler for the given platform name string. Platform names are case-sensitive lowercase. Raises `ValueError` for unsupported platforms.

**`OAuthRefreshError`**: Custom exception class raised by handlers on any refresh failure (network, HTTP, platform-specific error). Caught by `_call_refresh_endpoint()` in `RefreshService`.

---

## Credential Type Model

The module categorizes credentials stored in `platform_integrations` by two dimensions:

1. **Platform**: The external service (`twitch`, `discord`, `slack`, `youtube`, `spotify`, `kick`).
2. **Integration type**: The nature of the integration (e.g., `bot` for a bot token, `user` for a user-delegated OAuth token).

Both dimensions are stored as plain strings in the database. The Credential Manager does not enforce a fixed set of integration types — it processes any active row that has a `refresh_token`, an `expires_at`, and whose platform is registered in the `get_handler()` factory.

---

## Data Flow — Token Refresh Cycle

```
RefreshService._poll_loop()
        │
        ▼  (every POLL_INTERVAL seconds)
RefreshService.run_refresh_cycle()
        │
        ▼
asyncpg: SELECT from platform_integrations
         WHERE is_active = TRUE
           AND refresh_token IS NOT NULL
           AND expires_at IS NOT NULL
           AND expires_at < NOW() + TOKEN_REFRESH_BUFFER
         ORDER BY expires_at ASC
         LIMIT 50
        │
        ▼  (for each row)
RefreshService._refresh_token(integration: dict)
        │
        ▼
RefreshService._call_refresh_endpoint(platform, endpoint, integration)
        │
        ▼
get_handler(platform) → handler: BaseOAuthHandler
        │
        ▼
handler.refresh_token(refresh_token, client_id, client_secret, config_data)
        │
        ├── On success: return new_tokens dict
        │
        └── On failure: raise OAuthRefreshError
                │
                └── Caught by _call_refresh_endpoint → return None
                        │
                        └── _refresh_token retries with backoff
        │
        ▼  (on new_tokens received)
RefreshService._update_tokens(integration_id, platform, new_tokens)
        │
        ▼
asyncpg: UPDATE platform_integrations SET
         access_token, refresh_token, token_type, expires_at, scopes, updated_at
         WHERE id = integration_id
        │
        ▼
RefreshService._publish_refresh_event(integration, new_tokens)
        │
        ▼
Redis PUBLISH credentials:<platform>:<type>[:<community_id>]:refreshed <timestamp>
```

---

## Encryption at Rest

The `PLATFORM_ENCRYPTION_KEY` environment variable (mapped to `Config.ENCRYPTION_KEY`) is intended for at-rest encryption of sensitive fields in the database (access tokens, refresh tokens, client secrets). The `cryptography` library (`cryptography>=41.0.0`) is listed as a dependency.

**Important**: The application-level encryption integration point is provided by the `PLATFORM_ENCRYPTION_KEY` configuration value. The actual encryption/decryption layer is applied at the database write/read boundary. Never store the raw key value in source code, Docker images, or version control.

**Key format**: The key must be a 32-byte value encoded in URL-safe Base64. This is compatible with Fernet symmetric encryption from the `cryptography` library.

**Key storage**:
- In development: use a `.env` file with `PLATFORM_ENCRYPTION_KEY=<base64-value>`, listed in `.gitignore`.
- In Kubernetes: use a `Secret` resource, mounted as an environment variable.
- In Docker Compose: use a `.env` file at the project root, never committed to git.

---

## Access Control Model

The Credential Manager is an internal service. It has no external authentication layer on its HTTP endpoints. Access control is enforced at the network/infrastructure level:

- **Kubernetes**: The service is not exposed via the ingress. It is accessible only within the cluster namespace via ClusterIP service.
- **Docker Compose**: Port 8095 should not be published to the host in production deployments. Other services reach it via the internal Docker network.
- **No role-based access**: All three endpoints (`/health`, `/status`, `/refresh-now`) are available to any caller that can reach the service on port 8095.

For production deployments, consider adding a network policy that restricts inbound connections to the service to only authorized pods (Admin Hub, monitoring systems).

---

## Redis Pub/Sub Design

The Credential Manager uses Redis pub/sub for event-driven credential cache invalidation. It does not use Redis as a credential store — all authoritative credential data lives in PostgreSQL.

**Channel naming convention**:

```
{REDIS_KEY_PREFIX}{platform}:{integration_type}[:{community_id}]:refreshed
```

With default `REDIS_KEY_PREFIX = "credentials:"`:

```
credentials:twitch:bot:42:refreshed
credentials:discord:bot:refreshed
```

**Publisher**: `RefreshService._publish_refresh_event()` after each successful token update.

**Subscriber (built-in)**: `Config.start_credential_listener()` subscribes to `credentials:credential_manager:bot:refreshed` and invalidates `_credentials_loaded`.

**Subscriber (action modules)**: Each action module that caches credentials should subscribe to its own platform channel and reload from the database on receipt.

**Message payload**: ISO 8601 UTC timestamp string — only used for logging/auditing purposes by subscribers.

---

## Key Rotation Design

### OAuth Token Rotation (automated)

The module handles OAuth access token rotation automatically. When a token approaches expiry, the refresh cycle obtains a new access token (and optionally a new refresh token from the platform) and writes it back to the database.

### OAuth Client Credential Rotation (manual)

When `client_id` or `client_secret` values are rotated at the platform (e.g., the Twitch developer application secret is regenerated):

1. Update the `client_id` and `client_secret` columns in `platform_integrations` for the affected rows.
2. The Credential Manager will automatically use the new values on the next refresh cycle.
3. No restart is required.

### Encryption Key Rotation (manual, coordinated)

Rotating `PLATFORM_ENCRYPTION_KEY` requires a coordinated decryption-then-re-encryption pass:

1. Decrypt all stored credentials using the old key.
2. Re-encrypt all stored credentials using the new key.
3. Update the `PLATFORM_ENCRYPTION_KEY` environment variable across all services simultaneously.
4. Restart all services that use this key.

This is a maintenance window operation. Automate it via a migration script that reads the old key and writes with the new key in a single transaction.

---

## Database Schema Integration

The Credential Manager queries the `platform_integrations` table. The module does not create or migrate this table — it is owned by the Admin Hub or the central schema migration system.

**Required columns**:

```sql
CREATE TABLE platform_integrations (
    id              SERIAL PRIMARY KEY,
    platform        VARCHAR(50)   NOT NULL,
    integration_type VARCHAR(50)  NOT NULL,
    community_id    INTEGER,
    user_id         INTEGER,
    access_token    TEXT,
    refresh_token   TEXT,
    client_id       TEXT,
    client_secret   TEXT,
    token_type      VARCHAR(50)   DEFAULT 'Bearer',
    expires_at      TIMESTAMPTZ,
    scopes          TEXT[],
    config_data     JSONB,
    is_active       BOOLEAN       NOT NULL DEFAULT TRUE,
    updated_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);
```

**Query performance**: The refresh query filters on `is_active`, `refresh_token`, `expires_at`, and orders by `expires_at`. Ensure these columns are indexed:

```sql
CREATE INDEX IF NOT EXISTS idx_platform_integrations_refresh
    ON platform_integrations (expires_at ASC)
    WHERE is_active = TRUE AND refresh_token IS NOT NULL AND expires_at IS NOT NULL;
```

---

## Connection Pooling

**PostgreSQL**: `asyncpg.create_pool()` with `min_size=2`, `max_size=5`. Connections are acquired per query and released immediately after. This keeps pool pressure low during normal operation where one cycle runs every 60 seconds.

**Redis**: `aioredis.from_url()` with `decode_responses=True`. Uses a single persistent connection for pub/sub publishing.

**HTTP**: `httpx.AsyncClient` is shared across all refresh calls in a cycle (instantiated once in `start()`, closed in `stop()`). Individual OAuth handlers open their own short-lived `httpx.AsyncClient` per call (with a 10-second timeout) for isolation.

---

## Retry and Backoff Strategy

Each token refresh attempt uses exponential backoff:

```
wait = RETRY_BACKOFF_BASE * (2 ** attempt)
```

With defaults (`RETRY_BACKOFF_BASE=5`, `MAX_REFRESH_RETRIES=3`):

| Attempt | Wait before retry |
|---|---|
| 1 (first retry after failure) | 5 seconds |
| 2 (second retry) | 10 seconds |
| 3 (third retry — last) | No wait (no more retries) |

Total maximum wait for one token: ~15 seconds before giving up. After all retries are exhausted, the error is logged and `_total_errors` is incremented.

---

## Platform-Specific Handler Design

Each platform handler is a stateless object — it holds no instance state beyond the class constant `TOKEN_URL` and `TIMEOUT`. The `get_handler()` factory creates a new instance on each call.

The `_post_form()` base class method creates a new `httpx.AsyncClient` per request (inside an async context manager), ensuring no shared connection state between calls.

This design means handlers are thread-safe and can be called concurrently from multiple asyncio tasks without risk of connection sharing.

---

## Error Propagation Model

```
handler.refresh_token() raises OAuthRefreshError
        │
        ▼
_call_refresh_endpoint() catches OAuthRefreshError
        │
        └── logs warning, returns None
                │
                ▼
_refresh_token() sees None result
        │
        └── retries up to MAX_REFRESH_RETRIES
                │
                └── after all retries: logs error, increments _total_errors, returns False
                        │
                        ▼
run_refresh_cycle() counts only True returns
        │
        ▼
_poll_loop() logs exception if cycle itself raises
```

Platform-reported errors (e.g., Slack `ok: false`) are translated to `OAuthRefreshError` inside the handler before propagating, ensuring consistent error handling at all levels.

---

## Operational Counters

The `RefreshService` maintains two lifetime counters since process start:

| Counter | Incremented when |
|---|---|
| `_total_refreshed` | A token is successfully refreshed in any cycle (including manual force-refresh) |
| `_total_errors` | A token exhausts all retry attempts, or a poll cycle itself raises an unhandled exception |

These counters are not persisted to the database. They reset to zero on each restart. They are exposed via the `/health` endpoint for real-time monitoring.
