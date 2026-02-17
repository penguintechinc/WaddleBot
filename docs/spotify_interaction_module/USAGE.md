# Spotify Interaction Module — Usage Guide

> Getting started with the Spotify Interaction Module: Docker setup, OAuth
> configuration, health verification, and common workflow examples.

---

## Prerequisites

Before running the module, you need:

1. A **Spotify Developer Application** registered at https://developer.spotify.com/dashboard
2. The application **Client ID** and **Client Secret**
3. A **Redirect URI** registered in your Spotify app settings
4. A running **PostgreSQL** instance with the WaddleBot schema applied
5. Docker (for containerized runs) or Python 3.12+ (for local development)

---

## Step 1: Create the Spotify Developer Application

1. Go to https://developer.spotify.com/dashboard and log in with a Spotify account.
2. Click **Create App** and fill in:
   - **App name**: WaddleBot
   - **App description**: WaddleBot Spotify integration for community music
   - **Redirect URI**: see the table below
3. Accept the Developer Terms of Service and click **Save**.
4. Copy your **Client ID** and **Client Secret** from the app dashboard page.

### Redirect URI by Environment

| Environment      | Redirect URI                                               |
|------------------|------------------------------------------------------------|
| Local dev        | http://localhost:8026/spotify/auth/callback                |
| Alpha (local K8s)| https://waddlebot.localhost.local/spotify/auth/callback    |
| Beta             | https://waddlebot.penguintech.cloud/spotify/auth/callback  |
| Production       | https://waddlebot.io/spotify/auth/callback                 |

You can register multiple redirect URIs in the Spotify Dashboard under
**Edit Settings -> Redirect URIs**. The value in `SPOTIFY_REDIRECT_URI` must
match one of the registered values exactly.

---

## Step 2: Environment Configuration

Create a `.env` file in the module directory or export the variables to your shell.
Minimum required configuration for the OAuth flow to work:

```bash
# Spotify OAuth credentials (from developer.spotify.com/dashboard)
SPOTIFY_CLIENT_ID=your_client_id_here
SPOTIFY_CLIENT_SECRET=your_client_secret_here
SPOTIFY_REDIRECT_URI=http://localhost:8026/spotify/auth/callback
SPOTIFY_SCOPES=user-read-playback-state user-modify-playback-state user-read-currently-playing streaming

# Database
DATABASE_URL=postgresql://waddlebot:password@localhost:5432/waddlebot

# Service connectivity
CORE_API_URL=http://router-service:8000
ROUTER_API_URL=http://router-service:8000/api/v1/router

# Optional: Redis for credential live-reload
REDIS_URL=redis://localhost:6379/0

# Module settings
MODULE_PORT=8026
SECRET_KEY=change-me-in-production
LOG_LEVEL=INFO
```

See [CONFIGURATION.md](CONFIGURATION.md) for the complete variable reference including
all optional variables such as MAX_SEARCH_RESULTS, CACHE_TTL, and REQUEST_TIMEOUT.

---

## Step 3: Running with Docker

### Build the Image

The Dockerfile uses multi-directory COPY, so build from the repository root:

```bash
docker build \
  -f action/interactive/spotify_interaction_module/Dockerfile \
  -t waddlebot/spotify-interaction:latest \
  .
```

### Run the Container

```bash
docker run -d \
  --name spotify-interaction \
  -p 8026:8026 \
  -e SPOTIFY_CLIENT_ID=your_client_id \
  -e SPOTIFY_CLIENT_SECRET=your_client_secret \
  -e SPOTIFY_REDIRECT_URI=http://localhost:8026/spotify/auth/callback \
  -e DATABASE_URL=postgresql://waddlebot:password@host.docker.internal:5432/waddlebot \
  -e SECRET_KEY=change-me-in-production \
  waddlebot/spotify-interaction:latest
```

The container runs as the non-root `waddlebot` user and listens on port 8026
with 4 Hypercorn workers (set in the Dockerfile CMD).

### Docker Compose Service Block

```yaml
spotify-interaction:
  image: waddlebot/spotify-interaction:latest
  ports:
    - "8026:8026"
  environment:
    - SPOTIFY_CLIENT_ID=${SPOTIFY_CLIENT_ID}
    - SPOTIFY_CLIENT_SECRET=${SPOTIFY_CLIENT_SECRET}
    - SPOTIFY_REDIRECT_URI=${SPOTIFY_REDIRECT_URI}
    - DATABASE_URL=${DATABASE_URL}
    - CORE_API_URL=http://router-service:8000
    - ROUTER_API_URL=http://router-service:8000/api/v1/router
    - SECRET_KEY=${SECRET_KEY}
    - REDIS_URL=${REDIS_URL}
  depends_on:
    - postgres
    - router-service
  restart: unless-stopped
```

---

## Step 4: Local Development (without Docker)

Ensure you have Python 3.12 and install the shared `flask_core` library first.

```bash
# Install the shared library (from repo root)
pip install -e libs/flask_core

# Install module dependencies
pip install -r action/interactive/spotify_interaction_module/requirements.txt

# Set environment variables
export SPOTIFY_CLIENT_ID=your_client_id
export SPOTIFY_CLIENT_SECRET=your_client_secret
export SPOTIFY_REDIRECT_URI=http://localhost:8026/spotify/auth/callback
export DATABASE_URL=postgresql://waddlebot:password@localhost:5432/waddlebot
export SECRET_KEY=dev-secret-key
export MODULE_PORT=8026

# Run with hot reload from the module directory
cd action/interactive/spotify_interaction_module
python -m hypercorn app:app --bind 0.0.0.0:8026 --reload
```

---

## Step 5: Health Check

After starting the service, verify it is running correctly:

```bash
# Basic liveness check
curl http://localhost:8026/health
# Expected: {"status": "healthy", "module": "spotify_interaction_module", "version": "2.0.0"}

# Detailed health check with subsystem breakdown
curl http://localhost:8026/healthz

# Prometheus-format metrics
curl http://localhost:8026/metrics

# Module operational status endpoint
curl http://localhost:8026/api/v1/status
# Expected: {"success": true, "data": {"status": "operational", "module": "spotify_interaction_module"}}
```

---

## Step 6: OAuth Authorization Walkthrough

Once the service is running, authorize a community to use Spotify.

### 6.1 — Initiate OAuth

Direct the community admin to the authorization endpoint. Supply the `community_id`
value from the WaddleBot PostgreSQL database:

```
GET http://localhost:8026/api/v1/auth/login?community_id=1
```

The service calls `SpotifyOAuthService.get_authorization_url(state, scopes)` and
redirects the admin to `https://accounts.spotify.com/authorize` with:
- `client_id`: value of `SPOTIFY_CLIENT_ID`
- `response_type`: `code`
- `redirect_uri`: value of `SPOTIFY_REDIRECT_URI`
- `scope`: space-separated `DEFAULT_SCOPES` string (11 scopes)
- `state`: a generated CSRF token
- `show_dialog`: `true` (forces Spotify to show the consent screen)

### 6.2 — Admin Grants Permission

The admin logs into Spotify (if not already) and clicks **Agree** to grant scopes.
Spotify redirects to `SPOTIFY_REDIRECT_URI` with:
- `code`: the short-lived authorization code (valid for ~10 minutes)
- `state`: the CSRF state token to validate

### 6.3 — Callback Processing

The module receives `GET /auth/callback?code=X&state=Y` and:

1. Validates the `state` parameter against the stored CSRF token
2. Calls `SpotifyOAuthService.exchange_code_for_token(code, community_id)`
3. POSTs to `https://accounts.spotify.com/api/token` with:
   - `Authorization: Basic base64(client_id:client_secret)`
   - `grant_type: authorization_code`
   - `code`: the authorization code
   - `redirect_uri`: must match `SPOTIFY_REDIRECT_URI` exactly
4. Receives `access_token`, `refresh_token`, `expires_in`, `scope`, `token_type`
5. Calls `_store_token(community_id, token_data)` which upserts into `music_oauth_tokens`:
   - On first auth: INSERT
   - On re-auth: ON CONFLICT (community_id, platform) DO UPDATE

### 6.4 — Verify Authorization

```bash
psql $DATABASE_URL -c "
  SELECT community_id, platform, token_type, expires_at, scope
  FROM music_oauth_tokens
  WHERE platform = 'spotify';
"
```

---

## Common Workflow Examples

### Check Authentication Status

```bash
curl "http://localhost:8026/api/v1/auth/status?community_id=1"
```

Internally calls `SpotifyOAuthService.is_authenticated(community_id)`, which calls
`get_valid_token`. Returns `{"authenticated": true}` if a valid or refreshable token
exists, `{"authenticated": false}` if no token is found.

### Force Token Refresh

Tokens are refreshed automatically when within 5 minutes of expiry (the
`timedelta(minutes=5)` buffer in `SpotifyOAuthService.get_valid_token`). To trigger
a manual refresh for testing:

```bash
curl -X POST http://localhost:8026/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"community_id": 1}'
```

### Revoke Authorization

To disconnect a community from Spotify:

```bash
curl -X DELETE "http://localhost:8026/api/v1/auth/revoke?community_id=1"
```

This calls `SpotifyOAuthService.revoke_token(community_id)`, executing:
```sql
DELETE FROM music_oauth_tokens
WHERE community_id = 1 AND platform = 'spotify'
```

### Trigger Credential Reload (Redis)

If you have Redis configured and updated the Spotify client credentials via the
WaddleBot admin panel, publish a reload notification:

```bash
redis-cli PUBLISH credentials:spotify:bot:refreshed "reload"
```

`Config.start_credential_listener()` listens on this channel. On receiving any
message, it sets `_credentials_loaded = False` so the next request re-reads
credentials from the `platform_integrations` table.

---

## Running the API Test Suite

The module ships a comprehensive Bash test script for endpoint validation:

```bash
# Run against local instance (default URL: http://localhost:8026)
./action/interactive/spotify_interaction_module/test-api.sh

# Verbose output shows each HTTP request and response
./action/interactive/spotify_interaction_module/test-api.sh --verbose

# Custom base URL
./action/interactive/spotify_interaction_module/test-api.sh --url http://spotify:8026

# Supply an API key for authenticated endpoint tests
./action/interactive/spotify_interaction_module/test-api.sh --api-key your_api_key

# Skip tests that require authentication
./action/interactive/spotify_interaction_module/test-api.sh --skip-auth
```

Test coverage:

| Test | Endpoint | Expected Code |
|------|----------|---------------|
| Health check | GET /health | 200 (status=healthy) |
| Detailed health | GET /healthz | 200 (status=healthy, checks map) |
| Metrics | GET /metrics | 200 (Prometheus format) |
| Module status | GET /api/v1/status | 200 (status=operational) |
| Not found | GET /api/v1/nonexistent | 404 |
| Method not allowed | DELETE /api/v1/status | 405 |

Exit code 0 if all tests pass, 1 if any fail.

---

## Next Steps

- [API.md](API.md) — Complete endpoint reference
- [CONFIGURATION.md](CONFIGURATION.md) — All environment variables
- [ARCHITECTURE.md](ARCHITECTURE.md) — Internal design and data flow
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) — OAuth failures and common issues
