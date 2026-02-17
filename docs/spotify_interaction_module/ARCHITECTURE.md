# Spotify Interaction Module — Architecture

> Internal design, component breakdown, OAuth token lifecycle, and data flows
> for the Spotify Interaction Module.

---

## Overview

The `spotify_interaction_module` is a single-process Quart (async Python) application
served by Hypercorn with 4 worker processes. It owns the Spotify OAuth token lifecycle
for all WaddleBot communities and provides a REST API consumed by other modules.

```
  External Browser / Admin
          |
          | HTTP (OAuth flow)
          v
  Hypercorn ASGI Server (port 8026, 4 workers)
          |
          v
  Quart Application (app.py)
    |
    +-- Health Blueprint (flask_core.create_health_blueprint)
    |       /health, /healthz, /metrics
    |
    +-- API Blueprint (api_bp, prefix=/api/v1)
            |
            +-- GET /status              (app.py: status())
            |
            +-- OAuth endpoints
                    |
                    v
            SpotifyOAuthService (services/oauth_service.py)
                    |
                    +-- get_authorization_url()
                    +-- exchange_code_for_token()
                    +-- refresh_token()
                    +-- get_valid_token()
                    +-- is_authenticated()
                    +-- revoke_token()
                    +-- _store_token()
                    |
                    v
            PostgreSQL (music_oauth_tokens table)
            Spotify Web API (accounts.spotify.com, api.spotify.com)
```

---

## Application Startup

Application startup follows the Quart `@app.before_serving` lifecycle hook in `app.py`:

```python
@app.before_serving
async def startup():
    global dal
    logger.system("Starting spotify_interaction_module", action="startup")
    dal = init_database(Config.DATABASE_URL)
    app.config['dal'] = dal
    logger.system("spotify_interaction_module started", result="SUCCESS")
```

Startup sequence:
1. Quart application is imported and blueprints registered
2. `create_health_blueprint(Config.MODULE_NAME, Config.MODULE_VERSION)` registers
   `/health`, `/healthz`, `/metrics` endpoints
3. `api_bp` Blueprint is registered with prefix `/api/v1`
4. Hypercorn starts with `bind = f"0.0.0.0:{Config.MODULE_PORT}"` (default 8026)
5. `@app.before_serving` fires: `init_database(Config.DATABASE_URL)` initializes
   the PyDAL database access layer (`dal`)
6. `dal` is stored in `app.config['dal']` for endpoint access
7. The optional `Config.start_credential_listener(redis_client)` thread is started
   if `REDIS_URL` is configured

---

## Component: Config (config.py)

`Config` is a class-level configuration container (not instantiated) that provides:

### Static Configuration

| Attribute | Default | Source |
|---|---|---|
| MODULE_NAME | `spotify_interaction_module` | Hardcoded |
| MODULE_VERSION | `2.0.0` | Hardcoded |
| MODULE_PORT | `8026` | `os.getenv('MODULE_PORT', '8026')` |
| DATABASE_URL | `postgresql://waddlebot:password@localhost:5432/waddlebot` | `os.getenv` |
| CORE_API_URL | `http://router-service:8000` | `os.getenv` |
| ROUTER_API_URL | `http://router-service:8000/api/v1/router` | `os.getenv` |
| LOG_LEVEL | `INFO` | `os.getenv` |
| SECRET_KEY | `change-me-in-production` | `os.getenv` |
| REDIS_URL | `""` | `os.getenv` (empty = Redis disabled) |

### Credential Management

`Config` implements a thread-safe credential management pattern:

```python
_credentials_loaded: bool = False
_credential_lock: threading.Lock = threading.Lock()
```

**`load_credentials_from_db(db_connection)`** — Queries `platform_integrations`
for an active Spotify bot credential row. The SQL is:
```sql
SELECT client_id, client_secret, access_token
FROM platform_integrations
WHERE platform = 'spotify'
  AND integration_type = 'bot'
  AND is_active = TRUE
LIMIT 1
```
Returns `True` on success, `False` on failure. On failure, logs a warning and
the caller falls back to `SPOTIFY_CLIENT_ID` / `SPOTIFY_CLIENT_SECRET` env vars.

**`start_credential_listener(redis_client)`** — Starts a daemon thread that
subscribes to the Redis pub/sub channel `credentials:spotify:bot:refreshed`.
When a message arrives (any content), it acquires `_credential_lock` and sets
`_credentials_loaded = False`, triggering re-read from DB on the next credential
access. The thread name is `credential-listener`. Returns `None` if `REDIS_URL`
is empty.

---

## Component: SpotifyOAuthService (services/oauth_service.py)

The `SpotifyOAuthService` class is the core OAuth implementation. It is instantiated
with resolved credentials at service startup and holds a reference to `dal`.

### Constructor

```python
SpotifyOAuthService(dal, client_id, client_secret, redirect_uri)
```

| Parameter | Type | Source |
|---|---|---|
| dal | database connection | `app.config['dal']` |
| client_id | str | `SPOTIFY_CLIENT_ID` env or `platform_integrations` |
| client_secret | str | `SPOTIFY_CLIENT_SECRET` env or `platform_integrations` |
| redirect_uri | str | `SPOTIFY_REDIRECT_URI` env var |

### OAuth Endpoints (Class Constants)

```python
OAUTH_AUTHORIZE_URL = "https://accounts.spotify.com/authorize"
OAUTH_TOKEN_URL     = "https://accounts.spotify.com/api/token"
```

---

## OAuth Token Lifecycle

### Phase 1: Authorization (exchange_code_for_token)

```
  Browser                 Module                      Spotify API
     |                      |                              |
     |  GET /auth/login      |                              |
     |--------------------->|                              |
     |  302 -> accounts.    |                              |
     |  spotify.com/auth    |                              |
     |<---------------------|                              |
     |                      |                              |
     |--- Spotify login + consent ---------------------------->|
     |                      |                              |
     |<-- ?code=X&state=Y --|                              |
     |  GET /auth/callback  |                              |
     |--------------------->|                              |
     |                      |  POST /api/token             |
     |                      |  Authorization: Basic B64    |
     |                      |  grant_type=authorization_code|
     |                      |  code=X                      |
     |                      |  redirect_uri=...            |
     |                      |----------------------------->|
     |                      |  {access_token, refresh_token|
     |                      |   expires_in, scope}         |
     |                      |<-----------------------------|
     |                      |  _store_token() -> DB upsert |
     |  200 OK              |                              |
     |<---------------------|                              |
```

**Authorization header encoding** (`exchange_code_for_token`):
```python
auth_str = f"{self.client_id}:{self.client_secret}"
auth_b64 = base64.b64encode(auth_str.encode()).decode()
headers = {"Authorization": f"Basic {auth_b64}"}
```

**Token storage** (`_store_token`):
```sql
INSERT INTO music_oauth_tokens
  (community_id, platform, access_token, refresh_token,
   token_type, expires_at, scope, created_at, updated_at)
VALUES (%s, 'spotify', %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (community_id, platform)
DO UPDATE SET
    access_token  = EXCLUDED.access_token,
    refresh_token = COALESCE(EXCLUDED.refresh_token,
                             music_oauth_tokens.refresh_token),
    token_type    = EXCLUDED.token_type,
    expires_at    = EXCLUDED.expires_at,
    scope         = EXCLUDED.scope,
    updated_at    = EXCLUDED.updated_at
```

The `COALESCE` on `refresh_token` is critical: Spotify does not always return a
new refresh token on refresh. If the new response omits it, the existing value
is preserved. This is also handled in Python before calling `_store_token`:
```python
if "refresh_token" not in token_data:
    token_data["refresh_token"] = refresh_token  # preserve existing
```

---

### Phase 2: Valid Token Retrieval (get_valid_token)

Called by other services that need a current access token:

```
  Caller
    |
    | get_valid_token(community_id)
    v
  Query music_oauth_tokens for access_token, expires_at
    |
    +-- Token found?
    |     NO -> return None (not authenticated)
    |
    +-- expires_at <= utcnow() + timedelta(minutes=5)?
    |     YES -> refresh_token(community_id) -> return new access_token
    |     NO  -> return access_token as-is
```

The 5-minute buffer gives downstream operations enough time to complete before
the token actually expires mid-request.

---

### Phase 3: Token Refresh (refresh_token)

```
  Module                              Spotify API
    |                                     |
    |  SELECT refresh_token FROM          |
    |  music_oauth_tokens                 |
    |                                     |
    |  POST /api/token                    |
    |  Authorization: Basic B64           |
    |  grant_type=refresh_token           |
    |  refresh_token=<stored>             |
    |----------------------------------->|
    |  {access_token, expires_in, ...}   |
    |<-----------------------------------|
    |  _store_token() upsert              |
```

If Spotify returns a new `refresh_token` in the refresh response (uncommon but
possible), the new one is stored. Otherwise, the existing refresh token is
preserved via the `COALESCE` in the upsert SQL.

---

### Phase 4: Revocation (revoke_token)

```python
self.dal.executesql(
    "DELETE FROM music_oauth_tokens "
    "WHERE community_id = %s AND platform = 'spotify'",
    [community_id]
)
```

This removes the local token record. It does not call Spotify's revocation
endpoint. The access token remains valid on Spotify's side until it naturally
expires (typically 1 hour after issuance).

---

## HTTP Client: aiohttp

All calls to the Spotify API use `aiohttp.ClientSession` within async context managers:

```python
async with aiohttp.ClientSession() as session:
    async with session.post(self.OAUTH_TOKEN_URL, headers=headers, data=data) as response:
        if response.status != 200:
            error_text = await response.text()
            raise Exception(f"Token exchange failed: {response.status} - {error_text}")
        token_data = await response.json()
```

A new `ClientSession` is created per request (not reused across calls). This is
safe for the current request volume but could be optimized with a persistent
session stored in the DAL or app context for high-throughput deployments.

---

## Shared Library: flask_core

The module depends on the `flask_core` shared library from `libs/flask_core`,
installed as a Python package in the Docker build. The following imports are used:

```python
from flask_core import (
    async_endpoint,          # Decorator wrapping async view functions
    create_health_blueprint, # Creates /health, /healthz, /metrics blueprint
    init_database,           # Initializes PyDAL database connection
    setup_aaa_logging,       # Sets up structured AAA logging
    success_response         # Builds standard {success: true, data: ...} response
)
```

The `@async_endpoint` decorator handles:
- Exception catching and structured error response formatting
- Request/response logging
- Async Quart compatibility

---

## Concurrency Model

- **Server**: Hypercorn ASGI with 4 workers (set in Dockerfile CMD)
- **Async framework**: Quart (asyncio-based), all route handlers are `async`
- **HTTP client**: aiohttp (async, creates per-request sessions)
- **Database**: PyDAL via `executesql` (synchronous calls within async handlers;
  consider `asyncpg` or run_in_executor for high-throughput production use)
- **Credential listener**: `threading.Thread` daemon (separate from asyncio event loop)
- **Credential lock**: `threading.Lock` protecting `_credentials_loaded` state

---

## Security Considerations

1. **Client secret**: Never exposed in responses or logs. Encoded with `base64.b64encode`
   only in the HTTP Authorization header for Spotify API calls.
2. **State parameter**: CSRF protection for the OAuth flow. Must be validated in
   the callback before exchanging the code.
3. **Token storage**: Tokens stored in PostgreSQL, not in memory or cookies.
   Database credentials are provided via `DATABASE_URL` environment variable.
4. **Non-root container**: The Docker image runs as the `waddlebot` user.
5. **Credentials from DB**: Production deployments load `client_id`/`client_secret`
   from the `platform_integrations` table rather than environment variables,
   enabling credential rotation without container restarts.
