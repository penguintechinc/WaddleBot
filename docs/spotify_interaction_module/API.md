# Spotify Interaction Module — API Reference

> Complete endpoint documentation for the Spotify Interaction Module REST API,
> including authentication requirements, request/response schemas, and error codes.

---

## Base URL

| Environment | Base URL |
|---|---|
| Local development | `http://localhost:8026` |
| Docker Compose | `http://spotify-interaction:8026` |
| Alpha (local K8s) | `https://waddlebot.localhost.local` (proxied via router) |
| Beta | `https://waddlebot.penguintech.cloud` (proxied via router) |

All API endpoints are versioned under `/api/v1/`. Health endpoints are unversioned.

---

## Authentication

Most endpoints require a Bearer token or API key passed in the `X-API-Key` header.
OAuth-specific endpoints (`/auth/*`) use community-scoped authentication where the
`community_id` parameter identifies the target community.

```
X-API-Key: your_api_key
```

or Bearer JWT:

```
Authorization: Bearer <jwt_token>
```

The Spotify OAuth callback endpoints (`/auth/callback`, `/auth/login`) do not require
API authentication — they are part of the browser-facing OAuth flow.

---

## Health and Monitoring Endpoints

These endpoints are provided by the shared `flask_core` library via
`create_health_blueprint(Config.MODULE_NAME, Config.MODULE_VERSION)`.
They require no authentication.

---

### GET /health

Basic liveness probe. Returns HTTP 200 if the service is running.

**Authentication**: None required

**Request**: No body

**Response 200**:
```json
{
  "status": "healthy",
  "module": "spotify_interaction_module",
  "version": "2.0.0"
}
```

**Fields**:
| Field | Type | Description |
|---|---|---|
| status | string | Always `healthy` when running |
| module | string | Module name from `Config.MODULE_NAME` |
| version | string | Module version from `Config.MODULE_VERSION` |

**Use case**: Kubernetes liveness probe, load balancer health check.

---

### GET /healthz

Detailed readiness probe with subsystem status breakdown.

**Authentication**: None required

**Request**: No body

**Response 200**:
```json
{
  "status": "healthy",
  "module": "spotify_interaction_module",
  "version": "2.0.0",
  "checks": {
    "database": "ok",
    "redis": "ok"
  }
}
```

**Fields**:
| Field | Type | Description |
|---|---|---|
| status | string | `healthy` or `degraded` |
| module | string | Module name |
| version | string | Module version |
| checks | object | Map of subsystem name to status string |

**Use case**: Kubernetes readiness probe. Returns 200 even if some checks are
degraded, so the pod stays in service; downstream logic handles degraded state.

---

### GET /metrics

Prometheus-format metrics for monitoring and alerting.

**Authentication**: None required

**Request**: No body

**Response 200** (text/plain):
```
# HELP spotify_interaction_requests_total Total HTTP requests
# TYPE spotify_interaction_requests_total counter
spotify_interaction_requests_total{method="GET",endpoint="/health",status="200"} 42
# HELP spotify_interaction_request_duration_seconds Request duration histogram
# TYPE spotify_interaction_request_duration_seconds histogram
spotify_interaction_request_duration_seconds_bucket{le="0.1"} 40
...
```

**Content-Type**: `text/plain; version=0.0.4`

**Use case**: Prometheus scrape target. Configure scrape interval in Prometheus
config to `http://spotify-interaction:8026/metrics`.

---

## Module Status Endpoint

### GET /api/v1/status

Returns the operational status of the module. Implemented in `app.py` via the
`status()` view function decorated with `@async_endpoint`.

**Authentication**: None required (public operational status)

**Request**: No body

**Response 200**:
```json
{
  "success": true,
  "data": {
    "status": "operational",
    "module": "spotify_interaction_module"
  }
}
```

**Fields**:
| Field | Type | Description |
|---|---|---|
| success | boolean | Always `true` on 200 response |
| data.status | string | Always `operational` if the module is running |
| data.module | string | Module name from `Config.MODULE_NAME` |

**Error 500**:
```json
{
  "success": false,
  "error": "Internal server error",
  "code": 500
}
```

---

## OAuth Authorization Endpoints

These endpoints implement the Spotify Authorization Code flow.
The `SpotifyOAuthService` class in `services/oauth_service.py` handles all
token operations.

---

### GET /api/v1/auth/login

Initiates the Spotify OAuth Authorization Code flow for a community. Redirects
the browser to `https://accounts.spotify.com/authorize` with all required parameters.

**Authentication**: None (browser-facing redirect)

**Query Parameters**:
| Parameter | Type | Required | Description |
|---|---|---|---|
| community_id | integer | Yes | WaddleBot community ID to authorize |
| scopes | string | No | Space-separated scope overrides (uses DEFAULT_SCOPES if omitted) |

**Flow**: Calls `SpotifyOAuthService.get_authorization_url(state, scopes)`:
- Generates a `state` CSRF token and stores it in the session
- Builds the Spotify authorization URL with `show_dialog=true`
- Returns HTTP 302 redirect to `https://accounts.spotify.com/authorize`

**Spotify Authorization URL Parameters** (built by `get_authorization_url`):
```
client_id     = SPOTIFY_CLIENT_ID
response_type = code
redirect_uri  = SPOTIFY_REDIRECT_URI
scope         = user-read-playback-state user-modify-playback-state
                user-read-currently-playing playlist-read-private
                playlist-read-collaborative playlist-modify-public
                playlist-modify-private user-library-read
                user-library-modify user-top-read user-read-recently-played
state         = <generated_csrf_token>
show_dialog   = true
```

**Response 302**: Redirect to Spotify accounts page

**Error 400**:
```json
{
  "success": false,
  "error": "community_id is required",
  "code": 400
}
```

---

### GET /api/v1/auth/callback

OAuth callback endpoint. Spotify redirects here after the user grants or denies
permission. Exchanges the authorization code for access and refresh tokens.

**Authentication**: None (browser callback from Spotify)

**Query Parameters**:
| Parameter | Type | Description |
|---|---|---|
| code | string | Authorization code from Spotify (valid ~10 minutes) |
| state | string | CSRF state token to validate against session |
| error | string | Present if user denied access (e.g., `access_denied`) |
| community_id | string | Community ID (may be passed in state param) |

**Flow**: Calls `SpotifyOAuthService.exchange_code_for_token(code, community_id)`:
1. Builds Basic auth header: `base64(SPOTIFY_CLIENT_ID:SPOTIFY_CLIENT_SECRET)`
2. POSTs to `https://accounts.spotify.com/api/token`:
   ```
   grant_type=authorization_code
   code=<auth_code>
   redirect_uri=<SPOTIFY_REDIRECT_URI>
   ```
3. Receives token response with `access_token`, `refresh_token`, `expires_in`,
   `scope`, `token_type`
4. Calls `_store_token(community_id, token_data)` which upserts into
   `music_oauth_tokens` via INSERT ... ON CONFLICT DO UPDATE
5. Logs: `"Spotify token obtained for community {community_id}"`

**Response 200** (on success):
```json
{
  "success": true,
  "data": {
    "message": "Spotify authorization successful",
    "community_id": 1,
    "scope": "user-read-playback-state user-modify-playback-state ..."
  }
}
```

**Response 400** (user denied access):
```json
{
  "success": false,
  "error": "Access denied by user",
  "code": 400
}
```

**Response 400** (state mismatch):
```json
{
  "success": false,
  "error": "Invalid state parameter",
  "code": 400
}
```

**Response 500** (token exchange failed):
```json
{
  "success": false,
  "error": "Token exchange failed: 400 - {"error": "invalid_grant"}",
  "code": 500
}
```

---

### GET /api/v1/auth/status

Check if a community has a valid (or refreshable) Spotify authorization.

**Authentication**: API key or Bearer token

**Query Parameters**:
| Parameter | Type | Required | Description |
|---|---|---|---|
| community_id | integer | Yes | WaddleBot community ID |

**Flow**: Calls `SpotifyOAuthService.is_authenticated(community_id)`, which calls
`get_valid_token(community_id)`. The `get_valid_token` method:
1. Queries `music_oauth_tokens` for `access_token` and `expires_at`
2. If token expires within 5 minutes (`timedelta(minutes=5)` buffer), calls `refresh_token`
3. Returns the valid `access_token` or `None`

**Response 200** (authenticated):
```json
{
  "success": true,
  "data": {
    "authenticated": true,
    "community_id": 1,
    "expires_at": "2026-02-16T22:30:00Z"
  }
}
```

**Response 200** (not authenticated):
```json
{
  "success": true,
  "data": {
    "authenticated": false,
    "community_id": 1
  }
}
```

**Error 400**:
```json
{
  "success": false,
  "error": "community_id is required",
  "code": 400
}
```

---

### POST /api/v1/auth/refresh

Force a token refresh for a community using the stored `refresh_token`.

**Authentication**: API key or Bearer token

**Request Body** (application/json):
```json
{
  "community_id": 1
}
```

**Flow**: Calls `SpotifyOAuthService.refresh_token(community_id)`:
1. Queries `music_oauth_tokens` for `refresh_token`
2. POSTs to `https://accounts.spotify.com/api/token`:
   ```
   grant_type=refresh_token
   refresh_token=<stored_refresh_token>
   ```
3. If Spotify does not return a new `refresh_token`, preserves the existing one
4. Calls `_store_token` to upsert the updated token

**Response 200**:
```json
{
  "success": true,
  "data": {
    "message": "Token refreshed successfully",
    "community_id": 1,
    "expires_in": 3600
  }
}
```

**Error 404** (no refresh token found):
```json
{
  "success": false,
  "error": "No refresh token found for community",
  "code": 404
}
```

**Error 400** (Spotify rejected the refresh):
```json
{
  "success": false,
  "error": "Token refresh failed: 400 - {"error": "invalid_grant"}",
  "code": 400
}
```

---

### DELETE /api/v1/auth/revoke

Revoke and delete the Spotify authorization for a community.

**Authentication**: API key or Bearer token

**Query Parameters**:
| Parameter | Type | Required | Description |
|---|---|---|---|
| community_id | integer | Yes | WaddleBot community ID |

**Flow**: Calls `SpotifyOAuthService.revoke_token(community_id)`:
```sql
DELETE FROM music_oauth_tokens
WHERE community_id = %s AND platform = 'spotify'
```

Note: This does NOT call Spotify's token revocation endpoint. It only removes
the local token record. The access token remains valid at Spotify until it expires
(typically 1 hour). For full revocation, the user must revoke in their Spotify
account settings at https://www.spotify.com/account/apps.

**Response 200**:
```json
{
  "success": true,
  "data": {
    "message": "Spotify authorization revoked",
    "community_id": 1
  }
}
```

**Error 500** (database error):
```json
{
  "success": false,
  "error": "Failed to revoke token",
  "code": 500
}
```

---

## Standard Error Response Format

All error responses follow this structure:

```json
{
  "success": false,
  "error": "Human-readable error description",
  "code": 400
}
```

### HTTP Status Codes

| Code | Meaning |
|---|---|
| 200 | Success |
| 302 | Redirect (OAuth flow) |
| 400 | Bad request (missing parameters, validation error, Spotify rejected) |
| 401 | Unauthorized (missing or invalid API key / Bearer token) |
| 404 | Not found (resource or endpoint does not exist) |
| 405 | Method not allowed |
| 429 | Rate limited (Spotify API rate limit hit) |
| 500 | Internal server error |

---

## Database Tables

The OAuth service writes to two tables:

### music_oauth_tokens

Stores active OAuth token pairs per community per platform.

| Column | Type | Description |
|---|---|---|
| community_id | integer | WaddleBot community identifier |
| platform | varchar | Always `spotify` for this module |
| access_token | text | Current Spotify access token |
| refresh_token | text | Spotify refresh token (preserved across refreshes) |
| token_type | varchar | Always `Bearer` |
| expires_at | timestamp | UTC expiration time of the access token |
| scope | text | Space-separated granted scopes |
| created_at | timestamp | Record creation time (UTC) |
| updated_at | timestamp | Last upsert time (UTC) |

Unique constraint: `(community_id, platform)`

### platform_integrations

Read-only from this module. Used by `Config.load_credentials_from_db()` to load
the Spotify application credentials:

| Column | Type | Description |
|---|---|---|
| platform | varchar | `spotify` |
| integration_type | varchar | `bot` |
| client_id | varchar | Spotify application client ID |
| client_secret | varchar | Spotify application client secret |
| access_token | varchar | Pre-stored access token (if applicable) |
| is_active | boolean | Must be TRUE for the record to be used |
