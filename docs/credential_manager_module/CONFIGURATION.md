# Credential Manager Module — Configuration Reference

This document covers every environment variable accepted by the Credential Manager Module, their defaults, valid ranges, and security hardening guidance. It also includes an example `.env` file with placeholder values suitable for local development.

---

## Table of Contents

1. [Configuration Loading](#configuration-loading)
2. [Required Variables](#required-variables)
3. [Optional Variables — Service Tuning](#optional-variables--service-tuning)
4. [Optional Variables — Security](#optional-variables--security)
5. [Optional Variables — Observability](#optional-variables--observability)
6. [Internal Constants](#internal-constants)
7. [Validation Rules](#validation-rules)
8. [Example .env File (Development)](#example-env-file-development)
9. [Example .env File (Production — Placeholder Values Only)](#example-env-file-production--placeholder-values-only)
10. [Kubernetes Secret Configuration](#kubernetes-secret-configuration)
11. [Docker Compose Environment Injection](#docker-compose-environment-injection)
12. [Security Hardening Notes](#security-hardening-notes)
13. [Environment Variable Cross-Reference](#environment-variable-cross-reference)

---

## Configuration Loading

All configuration is loaded from environment variables by `config.py` at import time. The `Config` class uses class-level attributes with `os.getenv()` calls. There is no configuration file format — environment variables are the sole configuration mechanism.

The configuration is validated at startup via `Config.validate()`. If required variables are missing, the application logs the errors and exits with code 1.

---

## Required Variables

These variables must be set. The module will not start without them.

---

### `DATABASE_URL`

**Type**: String — PostgreSQL connection URL
**Required**: Yes
**Default (fallback for local dev)**: `postgresql://mod_credential_manager:mod_credential_manager_dev_changeme@localhost:5432/waddlebot`

The PostgreSQL connection string for the Waddlebot shared database. The module reads from and writes to the `platform_integrations` table in this database.

**Format**:

```
postgresql://<username>:<password>@<host>:<port>/<database>
```

**Examples** (use only as format reference — never hardcode actual credentials):

```
postgresql://mod_credential_manager:<db-password>@postgres-service:5432/waddlebot
postgresql://mod_credential_manager:<db-password>@127.0.0.1:5432/waddlebot
```

**Notes**:
- The module normalizes `postgresql://` to `postgres://` internally for PyDAL compatibility when loading via `Config`, then converts back to `postgresql://` for asyncpg.
- The database user must have `SELECT` and `UPDATE` permissions on `platform_integrations`.
- The database user does not need `INSERT`, `DELETE`, or `CREATE` permissions.
- Never use the superuser account for this connection. Create a dedicated limited-privilege user.

---

### `REDIS_URL`

**Type**: String — Redis connection URL
**Required**: Yes
**Default (fallback for local dev)**: `redis://localhost:6379/0`

The Redis connection string used for pub/sub credential refresh notifications.

**Format**:

```
redis://[:<password>@]<host>:<port>/<db>
rediss://[:<password>@]<host>:<port>/<db>   (TLS)
```

**Examples** (format reference only):

```
redis://:redis-password@redis-service:6379/0
rediss://:redis-password@redis.internal:6380/0
redis://localhost:6379/0
```

**Notes**:
- If Redis requires authentication, include the password in the URL.
- For TLS-encrypted Redis connections, use the `rediss://` scheme.
- Database number (the `/0` suffix) can be any valid Redis database index (0–15). Use a consistent database number across all Waddlebot services.

---

## Optional Variables — Service Tuning

These variables control the timing and retry behavior of the background token refresh loop.

---

### `MODULE_PORT`

**Type**: Integer
**Required**: No
**Default**: `8095`
**Valid range**: `1024–65535`

The TCP port on which the Quart HTTP server listens for incoming connections.

```
MODULE_PORT=8095
```

Do not change this value without also updating the corresponding Kubernetes Service manifest and Docker Compose port mapping.

---

### `TOKEN_REFRESH_BUFFER`

**Type**: Integer (seconds)
**Required**: No
**Default**: `300` (5 minutes)
**Valid range**: `60–3600`

How many seconds before a token's `expires_at` timestamp the refresh cycle considers it eligible for refresh. A token with `expires_at = NOW() + 4 minutes` will be picked up when `TOKEN_REFRESH_BUFFER >= 240`.

Setting this value too low (e.g., 30 seconds) risks tokens expiring between the poll cycle and the actual platform API call. Setting it too high (e.g., 1800 seconds) causes unnecessary early refreshes, increasing platform API call volume.

```
TOKEN_REFRESH_BUFFER=300
```

---

### `POLL_INTERVAL`

**Type**: Integer (seconds)
**Required**: No
**Default**: `60` (1 minute)
**Valid range**: `10–3600`

How many seconds the refresh service sleeps between poll cycles. Reducing this value increases responsiveness but also increases database query frequency. The default of 60 seconds is appropriate for production workloads with up to several hundred platform integrations.

```
POLL_INTERVAL=60
```

---

### `MAX_REFRESH_RETRIES`

**Type**: Integer
**Required**: No
**Default**: `3`
**Valid range**: `1–10`

Maximum number of refresh attempts for a single token before the module gives up and logs an error. The first attempt is not counted as a retry — so with `MAX_REFRESH_RETRIES=3`, the module makes up to 3 total attempts (1 initial + 2 retries).

```
MAX_REFRESH_RETRIES=3
```

---

### `RETRY_BACKOFF_BASE`

**Type**: Integer (seconds)
**Required**: No
**Default**: `5`
**Valid range**: `1–60`

Base delay in seconds for exponential backoff between retry attempts. The formula is:

```
wait_seconds = RETRY_BACKOFF_BASE * (2 ** attempt_index)
```

With defaults:
- After attempt 0 failure: wait 5 seconds
- After attempt 1 failure: wait 10 seconds
- After attempt 2 (last): no more retries

```
RETRY_BACKOFF_BASE=5
```

---

### `REDIS_KEY_PREFIX`

**Type**: String
**Required**: No
**Default**: `credentials:`

The prefix applied to all Redis pub/sub channel names. The channel format is:

```
{REDIS_KEY_PREFIX}{platform}:{integration_type}[:{community_id}]:refreshed
```

Change this only if you are running multiple isolated Waddlebot deployments sharing the same Redis instance and need to prevent cross-deployment event delivery.

```
REDIS_KEY_PREFIX=credentials:
```

---

## Optional Variables — Security

---

### `PLATFORM_ENCRYPTION_KEY`

**Type**: String — Base64-encoded 32-byte key
**Required**: Recommended for production
**Default**: `""` (empty — encryption not enforced)
**Env var name**: `PLATFORM_ENCRYPTION_KEY`
**Config attribute**: `Config.ENCRYPTION_KEY`

The encryption key used to encrypt sensitive credential fields at rest in the database. This key is used by the application-level encryption layer (implemented with the `cryptography` library, Fernet symmetric encryption) to protect access tokens, refresh tokens, and client secrets stored in `platform_integrations`.

**Key generation** (run once, store the output in your secrets manager):

```bash
python3 -c "
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
"
```

This produces a URL-safe Base64-encoded 32-byte key, such as:

```
<base64-encoded-fernet-key-placeholder>
```

**IMPORTANT**: Never log, print, commit, or document the actual key value. Store it only in:
- A secrets manager (HashiCorp Vault, AWS Secrets Manager, GCP Secret Manager)
- A Kubernetes Secret
- A `.env` file that is in `.gitignore` and never committed

```
PLATFORM_ENCRYPTION_KEY=<your-generated-key>
```

---

## Optional Variables — Observability

---

### `LOG_LEVEL`

**Type**: String — Python logging level name
**Required**: No
**Default**: `INFO`
**Valid values**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

Controls the verbosity of log output. In production, use `INFO` or `WARNING`. Use `DEBUG` only in development or when actively troubleshooting — debug logs include database query details and Redis channel names.

```
LOG_LEVEL=INFO
```

At `DEBUG` level, the module logs:
- Every published Redis channel name after each token refresh
- Database pool connection events
- Individual token refresh outcomes

---

## Internal Constants

These values are hardcoded in the source and cannot be changed via environment variables:

| Constant | Value | Location | Description |
|---|---|---|---|
| `MODULE_NAME` | `"credential_manager"` | `config.py` | Module identifier for health responses |
| `MODULE_VERSION` | `"1.0.0"` | `config.py` | Module semantic version |
| `BaseOAuthHandler.TIMEOUT` | `10` (seconds) | `oauth_handlers.py` | HTTP timeout for OAuth token endpoint calls |
| `asyncpg pool min_size` | `2` | `refresh_service.py` | Minimum DB pool connections |
| `asyncpg pool max_size` | `5` | `refresh_service.py` | Maximum DB pool connections |
| `httpx.AsyncClient timeout` | `30.0` (seconds) | `refresh_service.py` | Shared HTTP client timeout |
| Refresh batch limit | `50` | `refresh_service.py` | Max tokens refreshed per cycle |

---

## Validation Rules

On startup, `Config.validate()` checks:

1. `DATABASE_URL` must be non-empty.
2. `REDIS_URL` must be non-empty.

If either check fails, the process logs the error and exits with code 1. The container will restart according to the restart policy.

No runtime validation is currently performed on numeric values (`MODULE_PORT`, `TOKEN_REFRESH_BUFFER`, `POLL_INTERVAL`, etc.). If an environment variable contains a non-integer value for an integer-typed setting, the `int()` cast in `config.py` will raise a `ValueError` at import time, crashing the process.

---

## Example .env File (Development)

This file is for local development only. All values are placeholders — substitute with actual values from your local secrets store. Never commit this file to version control.

```dotenv
# core/credential_manager_module — LOCAL DEVELOPMENT ONLY
# DO NOT COMMIT — add .env to .gitignore

# === Required ===
DATABASE_URL=postgresql://mod_credential_manager:changeme-local@localhost:5432/waddlebot
REDIS_URL=redis://localhost:6379/0

# === Security ===
# Generate with: python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
PLATFORM_ENCRYPTION_KEY=<generate-with-command-above-do-not-use-this-placeholder>

# === Service Port ===
MODULE_PORT=8095

# === Token Refresh Tuning ===
TOKEN_REFRESH_BUFFER=300
POLL_INTERVAL=60
MAX_REFRESH_RETRIES=3
RETRY_BACKOFF_BASE=5

# === Redis ===
REDIS_KEY_PREFIX=credentials:

# === Observability ===
LOG_LEVEL=DEBUG
```

---

## Example .env File (Production — Placeholder Values Only)

In production, environment variables should be injected by your secrets manager or CI/CD pipeline — not from a `.env` file. This template shows the variable names and expected formats; actual values must come from your secure credential store.

```dotenv
# PRODUCTION TEMPLATE — Actual values from secrets manager only
# This file documents variable names and formats only.
# Replace all <placeholder> values with values from your secrets manager.

DATABASE_URL=postgresql://mod_credential_manager:<db-password>@postgres-primary:5432/waddlebot
REDIS_URL=rediss://:<redis-password>@redis-primary:6380/0
PLATFORM_ENCRYPTION_KEY=<fernet-key-from-vault>
MODULE_PORT=8095
TOKEN_REFRESH_BUFFER=300
POLL_INTERVAL=60
MAX_REFRESH_RETRIES=3
RETRY_BACKOFF_BASE=5
REDIS_KEY_PREFIX=credentials:
LOG_LEVEL=INFO
```

---

## Kubernetes Secret Configuration

Store sensitive values in a Kubernetes `Secret` and inject them as environment variables into the pod:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: credential-manager-secrets
  namespace: waddlebot
type: Opaque
stringData:
  DATABASE_URL: "postgresql://mod_credential_manager:<password>@postgres:5432/waddlebot"
  REDIS_URL: "rediss://:<password>@redis:6380/0"
  PLATFORM_ENCRYPTION_KEY: "<fernet-key>"
```

Reference the secret in the Deployment:

```yaml
spec:
  containers:
    - name: credential-manager
      image: waddlebot/credential-manager:latest
      envFrom:
        - secretRef:
            name: credential-manager-secrets
      env:
        - name: MODULE_PORT
          value: "8095"
        - name: TOKEN_REFRESH_BUFFER
          value: "300"
        - name: POLL_INTERVAL
          value: "60"
        - name: MAX_REFRESH_RETRIES
          value: "3"
        - name: RETRY_BACKOFF_BASE
          value: "5"
        - name: REDIS_KEY_PREFIX
          value: "credentials:"
        - name: LOG_LEVEL
          value: "INFO"
```

---

## Docker Compose Environment Injection

In `docker-compose.yml`, reference a project-level `.env` file for secret injection:

```yaml
credential-manager:
  image: waddlebot/credential-manager:${IMAGE_TAG:-latest}
  env_file:
    - .env.credential-manager
  environment:
    MODULE_PORT: "8095"
    TOKEN_REFRESH_BUFFER: "${TOKEN_REFRESH_BUFFER:-300}"
    POLL_INTERVAL: "${POLL_INTERVAL:-60}"
    MAX_REFRESH_RETRIES: "${MAX_REFRESH_RETRIES:-3}"
    RETRY_BACKOFF_BASE: "${RETRY_BACKOFF_BASE:-5}"
    REDIS_KEY_PREFIX: "${REDIS_KEY_PREFIX:-credentials:}"
    LOG_LEVEL: "${LOG_LEVEL:-INFO}"
```

Create `.env.credential-manager` locally (in `.gitignore`) with:

```dotenv
DATABASE_URL=postgresql://mod_credential_manager:<password>@postgres:5432/waddlebot
REDIS_URL=redis://redis:6379/0
PLATFORM_ENCRYPTION_KEY=<generated-key>
```

---

## Security Hardening Notes

### Never hardcode credential values

All secrets — `DATABASE_URL` password component, Redis password, `PLATFORM_ENCRYPTION_KEY` — must come from environment variables injected at runtime. The source code defaults for `DATABASE_URL` contain an obvious placeholder password (`mod_credential_manager_dev_changeme`) to make it clear when environment injection is missing.

### Restrict database user permissions

The `mod_credential_manager` database user should have only:
- `SELECT` on `platform_integrations`
- `UPDATE` on `platform_integrations` (for the specific columns the module writes: `access_token`, `refresh_token`, `token_type`, `expires_at`, `scopes`, `updated_at`)

It should not have `INSERT`, `DELETE`, `TRUNCATE`, `CREATE`, `DROP`, or any DDL permissions.

### Network isolation

The module's port (default `8095`) should not be exposed to the public internet. In Kubernetes, use a `ClusterIP` service type. In Docker Compose, remove the `ports` mapping in production or restrict it to the internal network.

### TLS for database and Redis

In production:
- Use `postgresql+ssl://` or configure `sslmode=require` in the `DATABASE_URL`.
- Use `rediss://` (Redis over TLS) in the `REDIS_URL`.

### Log level in production

Use `LOG_LEVEL=INFO` or `LOG_LEVEL=WARNING` in production. `DEBUG` logs include internal channel names and connection details that may assist an attacker in understanding the system layout.

### Encryption key rotation

Treat `PLATFORM_ENCRYPTION_KEY` as a long-lived secret. Rotate it on a schedule defined by your security policy (e.g., annually, or after any suspected compromise). See the Key Rotation section in ARCHITECTURE.md for the rotation procedure.

### Audit log access

The `updated_at` column on `platform_integrations` serves as an implicit audit trail for when tokens were last refreshed. For a more complete audit log, add a trigger or separate audit table that records who (which service) updated which row and when.

---

## Environment Variable Cross-Reference

| Env Var Name | Config Attribute | Type | Default | Required |
|---|---|---|---|---|
| `MODULE_PORT` | `Config.MODULE_PORT` | int | `8095` | No |
| `DATABASE_URL` | `Config.DATABASE_URL` | str | dev fallback | Yes |
| `REDIS_URL` | `Config.REDIS_URL` | str | `redis://localhost:6379/0` | Yes |
| `REDIS_KEY_PREFIX` | `Config.REDIS_KEY_PREFIX` | str | `credentials:` | No |
| `TOKEN_REFRESH_BUFFER` | `Config.TOKEN_REFRESH_BUFFER` | int | `300` | No |
| `POLL_INTERVAL` | `Config.POLL_INTERVAL` | int | `60` | No |
| `MAX_REFRESH_RETRIES` | `Config.MAX_REFRESH_RETRIES` | int | `3` | No |
| `RETRY_BACKOFF_BASE` | `Config.RETRY_BACKOFF_BASE` | int | `5` | No |
| `PLATFORM_ENCRYPTION_KEY` | `Config.ENCRYPTION_KEY` | str | `""` | Recommended |
| `LOG_LEVEL` | `Config.LOG_LEVEL` | str | `INFO` | No |
