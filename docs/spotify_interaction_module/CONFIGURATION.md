# Spotify Interaction Module — Configuration Reference

> All environment variables, configuration classes, and example `.env` files
> for the Spotify Interaction Module.

---

## Configuration Source

All configuration is managed in `action/interactive/spotify_interaction_module/config.py`
by the `Config` class. Values are read at module startup via `os.getenv()` with
`python-dotenv` loading `.env` files automatically (via `load_dotenv()` at import).

The `Config` class uses class-level attributes — it is never instantiated.

---

## Required Variables

These variables must be set for the OAuth flow to function. The module will start
without them but OAuth operations will fail.

### SPOTIFY_CLIENT_ID

| Item | Value |
|---|---|
| Type | string |
| Required | Yes (for OAuth) |
| Default | None |
| Source | Spotify Developer Dashboard |

The Spotify application client ID. Obtained from https://developer.spotify.com/dashboard
after creating an application. Used in the Authorization URL query string and in the
Basic auth header for token requests.

```bash
SPOTIFY_CLIENT_ID=1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d
```

---

### SPOTIFY_CLIENT_SECRET

| Item | Value |
|---|---|
| Type | string |
| Required | Yes (for OAuth) |
| Default | None |
| Source | Spotify Developer Dashboard |

The Spotify application client secret. Used alongside `SPOTIFY_CLIENT_ID` to build
the Basic auth header: `base64(client_id:client_secret)`. Never expose in logs,
responses, or version control.

```bash
SPOTIFY_CLIENT_SECRET=abc123def456ghi789jkl012mno345pq
```

---

### SPOTIFY_REDIRECT_URI

| Item | Value |
|---|---|
| Type | string (URL) |
| Required | Yes (for OAuth) |
| Default | None |
| Source | Must match Spotify Developer Dashboard registration |

The OAuth callback URI. Spotify redirects the browser to this URL with the
authorization code. Must be registered exactly in the Spotify Developer Dashboard.

Examples by environment:

```bash
# Local development
SPOTIFY_REDIRECT_URI=http://localhost:8026/spotify/auth/callback

# Alpha (local Kubernetes)
SPOTIFY_REDIRECT_URI=https://waddlebot.localhost.local/spotify/auth/callback

# Beta
SPOTIFY_REDIRECT_URI=https://waddlebot.penguintech.cloud/spotify/auth/callback

# Production
SPOTIFY_REDIRECT_URI=https://waddlebot.io/spotify/auth/callback
```

---

### DATABASE_URL

| Item | Value |
|---|---|
| Type | string (PostgreSQL DSN) |
| Required | Yes |
| Default | `postgresql://waddlebot:password@localhost:5432/waddlebot` |
| Config attribute | `Config.DATABASE_URL` |

PostgreSQL connection string used by `init_database()` to initialize the PyDAL
database access layer. The `music_oauth_tokens` and `platform_integrations`
tables must exist in this database.

```bash
DATABASE_URL=postgresql://waddlebot:securepassword@postgres:5432/waddlebot
```

---

## Service Connectivity Variables

### CORE_API_URL

| Item | Value |
|---|---|
| Type | string (URL) |
| Required | Recommended |
| Default | `http://router-service:8000` |
| Config attribute | `Config.CORE_API_URL` |

Base URL for the WaddleBot router/core API service. Used for inter-service
communication and routing callbacks.

```bash
CORE_API_URL=http://router-service:8000
```

---

### ROUTER_API_URL

| Item | Value |
|---|---|
| Type | string (URL) |
| Required | Recommended |
| Default | `http://router-service:8000/api/v1/router` |
| Config attribute | `Config.ROUTER_API_URL` |

Full URL path to the router API endpoint. Typically
`{CORE_API_URL}/api/v1/router`.

```bash
ROUTER_API_URL=http://router-service:8000/api/v1/router
```

---

## Module Settings

### MODULE_PORT

| Item | Value |
|---|---|
| Type | integer |
| Required | No |
| Default | `8026` |
| Config attribute | `Config.MODULE_PORT` |

The TCP port the Hypercorn ASGI server binds to. The Dockerfile CMD hardcodes
`--bind 0.0.0.0:8026`; override via environment variable to remap the port.

```bash
MODULE_PORT=8026
```

---

### SECRET_KEY

| Item | Value |
|---|---|
| Type | string |
| Required | Yes (for session security) |
| Default | `change-me-in-production` |
| Config attribute | `Config.SECRET_KEY` |

Used by Quart's session signing. The default value is insecure and must be
replaced in all non-development deployments. Generate with:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

```bash
SECRET_KEY=64-character-random-hex-string-here
```

---

### LOG_LEVEL

| Item | Value |
|---|---|
| Type | string |
| Required | No |
| Default | `INFO` |
| Config attribute | `Config.LOG_LEVEL` |

Logging verbosity level. Valid values: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`.
Use `DEBUG` during development to see detailed OAuth request/response logs.

```bash
LOG_LEVEL=INFO
```

---

## Redis Configuration

### REDIS_URL

| Item | Value |
|---|---|
| Type | string (Redis DSN) |
| Required | No |
| Default | `""` (empty — Redis disabled) |
| Config attribute | `Config.REDIS_URL` |

Connection string for Redis. When set, `Config.start_credential_listener()` starts
a daemon thread subscribing to `credentials:spotify:bot:refreshed`. Receiving any
message on that channel resets `_credentials_loaded = False`, triggering a credential
re-read from `platform_integrations` on the next request.

When `REDIS_URL` is empty, the credential listener is not started and `start_credential_listener`
returns `None`.

```bash
REDIS_URL=redis://redis:6379/0
```

---

## Optional Extended Variables

These variables appear in the environment variable reference for the Spotify module
and are read by downstream service layers:

### SPOTIFY_SCOPES

| Item | Value |
|---|---|
| Type | string (space-separated) |
| Required | No |
| Default | Uses `SpotifyOAuthService.DEFAULT_SCOPES` if not overridden |

Override the default OAuth scope set. The `DEFAULT_SCOPES` in `oauth_service.py`
contains 11 scopes. Provide a custom space-separated list to override.

```bash
SPOTIFY_SCOPES=user-read-playback-state user-modify-playback-state user-read-currently-playing streaming
```

### BROWSER_SOURCE_API_URL

| Item | Value |
|---|---|
| Type | string (URL) |
| Required | No |
| Default | `http://browser-source:8027/browser/source` |

URL of the browser source module for now-playing overlay integration.

```bash
BROWSER_SOURCE_API_URL=http://browser-source:8027/browser/source
```

### MAX_SEARCH_RESULTS

| Item | Value |
|---|---|
| Type | integer |
| Required | No |
| Default | `10` |

Maximum number of results to return from Spotify search queries.

```bash
MAX_SEARCH_RESULTS=10
```

### CACHE_TTL

| Item | Value |
|---|---|
| Type | integer (seconds) |
| Required | No |
| Default | `300` |

Time-to-live in seconds for cached Spotify search results.

```bash
CACHE_TTL=300
```

### REQUEST_TIMEOUT

| Item | Value |
|---|---|
| Type | integer (seconds) |
| Required | No |
| Default | `30` |

HTTP request timeout in seconds for calls to the Spotify Web API.

```bash
REQUEST_TIMEOUT=30
```

### TOKEN_REFRESH_BUFFER

| Item | Value |
|---|---|
| Type | integer (seconds) |
| Required | No |
| Default | `300` (5 minutes) |

Seconds before token expiry at which automatic refresh is triggered.
This corresponds to the `timedelta(minutes=5)` buffer in
`SpotifyOAuthService.get_valid_token`. Increasing this reduces the risk of
mid-request token expiry for long-running API calls.

```bash
TOKEN_REFRESH_BUFFER=300
```

### ENABLE_PLAYLISTS

| Item | Value |
|---|---|
| Type | boolean string |
| Required | No |
| Default | `true` |

Feature flag to enable playlist management endpoints.

```bash
ENABLE_PLAYLISTS=true
```

### ENABLE_QUEUE

| Item | Value |
|---|---|
| Type | boolean string |
| Required | No |
| Default | `true` |

Feature flag to enable song queue management.

```bash
ENABLE_QUEUE=true
```

### ENABLE_HISTORY

| Item | Value |
|---|---|
| Type | boolean string |
| Required | No |
| Default | `true` |

Feature flag to enable recently played history retrieval.

```bash
ENABLE_HISTORY=true
```

---

## Complete Example .env

```bash
# ============================================================
# Spotify Interaction Module — Environment Configuration
# ============================================================

# --- Spotify OAuth (REQUIRED for OAuth flow) ---
SPOTIFY_CLIENT_ID=1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d
SPOTIFY_CLIENT_SECRET=abc123def456ghi789jkl012mno345pq
SPOTIFY_REDIRECT_URI=http://localhost:8026/spotify/auth/callback
SPOTIFY_SCOPES=user-read-playback-state user-modify-playback-state user-read-currently-playing streaming

# --- Database (REQUIRED) ---
DATABASE_URL=postgresql://waddlebot:securepassword@localhost:5432/waddlebot

# --- Service Connectivity ---
CORE_API_URL=http://router-service:8000
ROUTER_API_URL=http://router-service:8000/api/v1/router
BROWSER_SOURCE_API_URL=http://browser-source:8027/browser/source

# --- Redis (optional, for credential live-reload) ---
REDIS_URL=redis://localhost:6379/0

# --- Module Settings ---
MODULE_PORT=8026
MODULE_NAME=spotify_interaction_module
SECRET_KEY=change-me-with-secrets-token-hex-32-output

# --- Logging ---
LOG_LEVEL=INFO

# --- Performance ---
MAX_SEARCH_RESULTS=10
CACHE_TTL=300
REQUEST_TIMEOUT=30
TOKEN_REFRESH_BUFFER=300

# --- Feature Flags ---
ENABLE_PLAYLISTS=true
ENABLE_QUEUE=true
ENABLE_HISTORY=true
```

---

## Kubernetes / ConfigMap Example

For Kubernetes deployments using Kustomize, environment variables are split between
a ConfigMap (non-sensitive) and a Secret (sensitive):

**ConfigMap** (non-sensitive):
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: spotify-interaction-config
data:
  SPOTIFY_REDIRECT_URI: "https://waddlebot.penguintech.cloud/spotify/auth/callback"
  CORE_API_URL: "http://router-service:8000"
  ROUTER_API_URL: "http://router-service:8000/api/v1/router"
  MODULE_PORT: "8026"
  LOG_LEVEL: "INFO"
  MAX_SEARCH_RESULTS: "10"
  CACHE_TTL: "300"
  ENABLE_PLAYLISTS: "true"
  ENABLE_QUEUE: "true"
  ENABLE_HISTORY: "true"
```

**Secret** (sensitive — use Sealed Secrets or external secret manager):
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: spotify-interaction-secrets
type: Opaque
stringData:
  SPOTIFY_CLIENT_ID: "your_client_id"
  SPOTIFY_CLIENT_SECRET: "your_client_secret"
  DATABASE_URL: "postgresql://waddlebot:securepassword@postgres:5432/waddlebot"
  SECRET_KEY: "your-64-char-random-secret"
  REDIS_URL: "redis://redis:6379/0"
```

---

## Credential Rotation Without Restart

If credentials are stored in the `platform_integrations` table (production mode),
they can be rotated without restarting the container:

1. Update `platform_integrations` with new `client_id` and `client_secret`
2. Publish a Redis notification:
   ```bash
   redis-cli PUBLISH credentials:spotify:bot:refreshed "rotated"
   ```
3. `Config.start_credential_listener()` receives the message, sets
   `_credentials_loaded = False` (protected by `_credential_lock`)
4. Next request triggers `Config.load_credentials_from_db()`, loading the new values

If Redis is not configured, restart the container to pick up new credentials.
