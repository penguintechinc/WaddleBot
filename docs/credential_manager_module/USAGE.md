# Credential Manager Module — Usage Guide

This guide covers how to run the Credential Manager Module, verify it is operating correctly, interact with its REST API, and integrate the Redis pub/sub notification system into dependent modules.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Getting Started — Local Development](#getting-started--local-development)
3. [Running with Docker](#running-with-docker)
4. [Running with Docker Compose](#running-with-docker-compose)
5. [Health Check](#health-check)
6. [Credential Status](#credential-status)
7. [Force Refresh](#force-refresh)
8. [Understanding the Refresh Workflow](#understanding-the-refresh-workflow)
9. [Redis Pub/Sub Notifications](#redis-pubsub-notifications)
10. [Subscribing from Another Module](#subscribing-from-another-module)
11. [Rotation Workflow](#rotation-workflow)
12. [Graceful Shutdown](#graceful-shutdown)

---

## Prerequisites

Before starting the Credential Manager Module, ensure the following are available:

- **PostgreSQL** database accessible at the URL specified by `DATABASE_URL`
- **Redis** instance accessible at the URL specified by `REDIS_URL`
- The `platform_integrations` table exists and is populated with OAuth tokens for at least one platform integration
- Python 3.11+ (if running directly) or Docker (if running containerized)

The module reads credentials from and writes refreshed tokens to the `platform_integrations` table. It does not bootstrap that table — the Admin Hub or community onboarding flow must have already stored the initial OAuth tokens there.

---

## Getting Started — Local Development

### Install dependencies

```bash
cd core/credential_manager_module
pip install -r requirements.txt
```

### Set required environment variables

Never hardcode credential values. Always use environment variables:

```bash
export DATABASE_URL="postgresql://mod_credential_manager:<password>@localhost:5432/waddlebot"
export REDIS_URL="redis://localhost:6379/0"
export PLATFORM_ENCRYPTION_KEY="<your-32-byte-base64-encoded-key>"
export MODULE_PORT="8095"
export LOG_LEVEL="DEBUG"
```

Replace `<password>` with the actual database user password from your local secrets store. Replace `<your-32-byte-base64-encoded-key>` with the value of `PLATFORM_ENCRYPTION_KEY` from your environment.

### Run with Hypercorn (async WSGI)

```bash
hypercorn core.credential_manager_module.app:app --bind 0.0.0.0:8095
```

Or run directly:

```bash
python -m core.credential_manager_module.app
```

The module will log startup messages and begin polling:

```
2026-02-16 00:00:00,000 [credential_manager_module.app] INFO: Credential Manager started (poll=60s, buffer=300s)
2026-02-16 00:00:00,001 [credential_manager_module.services.refresh_service] INFO: Refresh service started
```

---

## Running with Docker

Pull or build the image:

```bash
docker build -t waddlebot/credential-manager:local \
  -f core/credential_manager_module/Dockerfile .
```

Run the container, injecting credentials via environment variables — never bake secrets into the image:

```bash
docker run --rm \
  --name credential-manager \
  -e DATABASE_URL="postgresql://mod_credential_manager:<password>@host.docker.internal:5432/waddlebot" \
  -e REDIS_URL="redis://host.docker.internal:6379/0" \
  -e PLATFORM_ENCRYPTION_KEY="<base64-key>" \
  -e TOKEN_REFRESH_BUFFER="300" \
  -e POLL_INTERVAL="60" \
  -e MAX_REFRESH_RETRIES="3" \
  -e RETRY_BACKOFF_BASE="5" \
  -e LOG_LEVEL="INFO" \
  -p 8095:8095 \
  waddlebot/credential-manager:local
```

Verify the container started successfully:

```bash
docker logs credential-manager
```

Expected log output on healthy start:

```
INFO: Refresh service started
INFO: Credential Manager started (poll=60s, buffer=300s)
```

---

## Running with Docker Compose

In the Waddlebot `docker-compose.yml`, the Credential Manager service should be defined as follows (do not hardcode values — use a `.env` file or secrets manager):

```yaml
credential-manager:
  image: waddlebot/credential-manager:${IMAGE_TAG}
  restart: unless-stopped
  ports:
    - "8095:8095"
  environment:
    DATABASE_URL: ${CREDENTIAL_MANAGER_DATABASE_URL}
    REDIS_URL: ${REDIS_URL}
    PLATFORM_ENCRYPTION_KEY: ${PLATFORM_ENCRYPTION_KEY}
    TOKEN_REFRESH_BUFFER: ${TOKEN_REFRESH_BUFFER:-300}
    POLL_INTERVAL: ${POLL_INTERVAL:-60}
    MAX_REFRESH_RETRIES: ${MAX_REFRESH_RETRIES:-3}
    RETRY_BACKOFF_BASE: ${RETRY_BACKOFF_BASE:-5}
    LOG_LEVEL: ${LOG_LEVEL:-INFO}
  depends_on:
    - postgres
    - redis
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8095/health"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 15s
```

Start the service:

```bash
docker-compose up core-credential-manager
```

---

## Health Check

The health endpoint reports the running state of the refresh service, when the last cycle ran, and lifetime counters.

```bash
curl -s http://localhost:8095/health | python3 -m json.tool
```

**Response — healthy (HTTP 200)**:

```json
{
  "status": "healthy",
  "module": "credential_manager",
  "version": "1.0.0",
  "running": true,
  "last_cycle": "2026-02-16T00:01:00.000000+00:00",
  "total_refreshed": 14,
  "total_errors": 0
}
```

**Response — degraded (HTTP 503)**:

```json
{
  "status": "degraded",
  "module": "credential_manager",
  "version": "1.0.0",
  "running": false,
  "last_cycle": null,
  "total_refreshed": 0,
  "total_errors": 2
}
```

A `degraded` response means the background `RefreshService` is not running. This typically indicates a database or Redis connectivity failure at startup. Check container logs immediately.

---

## Credential Status

The credential status endpoint returns a per-platform summary of token state: total integrations tracked, how many are expiring within 5 minutes, and how many have already expired.

```bash
curl -s http://localhost:8095/api/v1/credentials/status | python3 -m json.tool
```

**Response (HTTP 200)**:

```json
{
  "success": true,
  "stats": [
    {
      "platform": "discord",
      "integration_type": "bot",
      "total": 3,
      "expiring_soon": 0,
      "expired": 0
    },
    {
      "platform": "twitch",
      "integration_type": "bot",
      "total": 5,
      "expiring_soon": 1,
      "expired": 0
    },
    {
      "platform": "youtube",
      "integration_type": "bot",
      "total": 2,
      "expiring_soon": 0,
      "expired": 0
    }
  ]
}
```

The `expiring_soon` count reflects integrations where `expires_at < NOW() + 5 minutes`. The `expired` count reflects integrations where `expires_at < NOW()`. Both counts signal tokens that the refresh service should have picked up or will pick up on the next cycle.

---

## Force Refresh

To immediately trigger a full refresh cycle without waiting for the next poll interval:

```bash
curl -s -X POST http://localhost:8095/api/v1/credentials/refresh-now | python3 -m json.tool
```

**Response (HTTP 200)**:

```json
{
  "success": true,
  "message": "Refreshed 3 credentials"
}
```

This is useful after:
- Adding a new platform integration that has a short-lived initial token
- Manually expiring tokens during testing
- Recovering from a known outage where tokens were not refreshed for an extended period

---

## Understanding the Refresh Workflow

The module follows this cycle every `POLL_INTERVAL` seconds:

1. **Query**: Fetch all rows from `platform_integrations` where `is_active = TRUE`, `refresh_token IS NOT NULL`, `expires_at IS NOT NULL`, and `expires_at < NOW() + TOKEN_REFRESH_BUFFER seconds`. Results are ordered by soonest-expiring first, limited to 50 per cycle.

2. **Refresh**: For each row, look up the appropriate OAuth handler for the platform. Call the handler's `refresh_token()` method with the stored `refresh_token`, `client_id`, and `client_secret`.

3. **Retry**: If the refresh call fails, retry up to `MAX_REFRESH_RETRIES` times with exponential backoff starting at `RETRY_BACKOFF_BASE` seconds (`5s`, `10s`, `20s` by default).

4. **Update**: On success, write the new `access_token`, `refresh_token` (if returned), `expires_at`, `token_type`, and `scopes` back to the database row.

5. **Notify**: Publish a timestamp message to the Redis channel `credentials:<platform>:<integration_type>[:<community_id>]:refreshed`.

6. **Sleep**: Wait `POLL_INTERVAL` seconds before repeating.

---

## Redis Pub/Sub Notifications

When the Credential Manager successfully refreshes a token, it publishes to a Redis channel following this naming convention:

```
credentials:<platform>:<integration_type>:<community_id>:refreshed
```

If no `community_id` is set for the integration, the channel omits that segment:

```
credentials:<platform>:<integration_type>:refreshed
```

Examples:

```
credentials:twitch:bot:42:refreshed
credentials:discord:bot:refreshed
credentials:youtube:bot:99:refreshed
```

The message payload is an ISO 8601 UTC timestamp string indicating when the refresh occurred.

---

## Subscribing from Another Module

Any module that caches platform credentials in memory should subscribe to the relevant Redis channel and reload credentials when notified. The `Config.start_credential_listener()` method in `config.py` provides a ready-made implementation:

```python
import redis
from core.credential_manager_module.config import Config

redis_client = redis.Redis.from_url(Config.REDIS_URL)
listener_thread = Config.start_credential_listener(redis_client)
```

The listener runs in a daemon thread. When a refresh notification arrives on `credentials:credential_manager:bot:refreshed`, it resets `Config._credentials_loaded` to `False`, triggering the next credential access to reload from the database.

For other modules, implement similar logic targeting the channel for your platform:

```python
import threading
import redis

def start_credential_listener(redis_url: str, channel: str, on_refresh) -> threading.Thread:
    def _listen():
        client = redis.Redis.from_url(redis_url)
        pubsub = client.pubsub()
        pubsub.subscribe(channel)
        for message in pubsub.listen():
            if message["type"] == "message":
                on_refresh()

    thread = threading.Thread(target=_listen, daemon=True, name="credential-listener")
    thread.start()
    return thread
```

---

## Rotation Workflow

The intended end-to-end credential rotation workflow is:

1. **Initial grant**: User authorizes the integration via the Admin Hub OAuth flow. The hub stores `access_token`, `refresh_token`, `client_id`, `client_secret`, and `expires_at` in `platform_integrations`.

2. **Proactive refresh**: The Credential Manager polls and, when `expires_at` approaches, calls the platform token endpoint and updates the row.

3. **Notification**: Dependent action modules receive the Redis pub/sub event and reload credentials from the database on next use.

4. **Expiry recovery**: If a token expires before the Credential Manager refreshes it (e.g., during a restart), the action module will encounter a 401 response. It should fall back to the database for the latest token. The Credential Manager will refresh on the next poll.

5. **Client secret rotation**: When OAuth application credentials (`client_id`, `client_secret`) are rotated at the platform level, update them in `platform_integrations` directly. The Credential Manager will use the new values on the next refresh cycle.

---

## Graceful Shutdown

The module handles `SIGTERM` and `SIGINT` signals via Quart's `after_serving` hook. On shutdown:

1. The background refresh task is cancelled.
2. The HTTP client (`httpx.AsyncClient`) is closed.
3. The Redis async connection is closed.
4. The PostgreSQL connection pool is closed.

Allow up to 30 seconds for graceful shutdown when stopping via `docker stop` or Kubernetes pod termination.
