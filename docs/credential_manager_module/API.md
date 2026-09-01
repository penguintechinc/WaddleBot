# Credential Manager Module — API Reference

**Base URL**: `http://<host>:8095`
**Protocol**: HTTP/1.1 (JSON responses)
**Authentication**: Internal service — no external authentication required. The module is intended to run inside the Waddlebot service mesh. Do not expose it directly to the public internet.

---

## Table of Contents

1. [General Conventions](#general-conventions)
2. [Endpoints](#endpoints)
   - [GET /health](#get-health)
   - [GET /api/v1/credentials/status](#get-apiv1credentialsstatus)
   - [POST /api/v1/credentials/refresh-now](#post-apiv1credentialsrefresh-now)
3. [Response Structures](#response-structures)
4. [Error Reference](#error-reference)
5. [Redis Event Schema](#redis-event-schema)
6. [Database Integration Schema](#database-integration-schema)

---

## General Conventions

### Content Type

All responses are `application/json`.

### Status Codes

| Code | Meaning |
|---|---|
| `200` | Request succeeded |
| `503` | Service unavailable — module not initialized or refresh service not running |

### Timestamps

All timestamps in responses are ISO 8601 format with UTC timezone:

```
2026-02-16T12:34:56.789012+00:00
```

### No credential values in responses

The API never returns actual credential values (tokens, secrets, keys). It returns only metadata: platform names, integration types, counts, timestamps, and status flags.

---

## Endpoints

---

### GET /health

Returns the operational health of the module and its background refresh service.

**Authentication**: None required.

**Request**:

```
GET /health HTTP/1.1
Host: localhost:8095
```

No request body or query parameters.

**Response — 200 OK (healthy)**:

```json
{
  "status": "healthy",
  "module": "credential_manager",
  "version": "1.0.0",
  "running": true,
  "last_cycle": "2026-02-16T12:00:00.000000+00:00",
  "total_refreshed": 42,
  "total_errors": 0
}
```

**Response — 503 Service Unavailable (degraded)**:

```json
{
  "status": "degraded",
  "module": "credential_manager",
  "version": "1.0.0",
  "running": false,
  "last_cycle": null,
  "total_refreshed": 0,
  "total_errors": 1
}
```

**Response Fields**:

| Field | Type | Description |
|---|---|---|
| `status` | string | `"healthy"` or `"degraded"` |
| `module` | string | Module identifier (`"credential_manager"`) |
| `version` | string | Module version (`"1.0.0"`) |
| `running` | boolean | Whether the background refresh service is active |
| `last_cycle` | string or null | ISO 8601 UTC timestamp of the most recently completed poll cycle, or `null` if no cycle has completed |
| `total_refreshed` | integer | Lifetime count of successfully refreshed tokens since the service started |
| `total_errors` | integer | Lifetime count of failed refresh cycles or individual token refresh errors |

**When to expect 503**: The module returns 503 when the `RefreshService` is not running. This can occur if the service failed to start (e.g., database connection refused) or if the background task crashed unexpectedly.

**Use in Kubernetes**: Configure liveness and readiness probes to call this endpoint. A non-200 response should trigger a pod restart.

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8095
  initialDelaySeconds: 15
  periodSeconds: 30
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /health
    port: 8095
  initialDelaySeconds: 10
  periodSeconds: 10
```

---

### GET /api/v1/credentials/status

Returns per-platform credential statistics: total integrations tracked, how many tokens are expiring within 5 minutes, and how many have already expired. Results are aggregated by platform and integration type.

**Authentication**: None required (internal service).

**Request**:

```
GET /api/v1/credentials/status HTTP/1.1
Host: localhost:8095
```

No request body or query parameters.

**Response — 200 OK**:

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
      "platform": "kick",
      "integration_type": "bot",
      "total": 1,
      "expiring_soon": 0,
      "expired": 0
    },
    {
      "platform": "slack",
      "integration_type": "bot",
      "total": 2,
      "expiring_soon": 1,
      "expired": 0
    },
    {
      "platform": "spotify",
      "integration_type": "bot",
      "total": 4,
      "expiring_soon": 0,
      "expired": 0
    },
    {
      "platform": "twitch",
      "integration_type": "bot",
      "total": 7,
      "expiring_soon": 0,
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

**Response — 503 Service Unavailable (not initialized)**:

```json
{
  "error": "Service not initialized"
}
```

**Response Fields — top level**:

| Field | Type | Description |
|---|---|---|
| `success` | boolean | `true` on success |
| `stats` | array | List of per-platform credential summaries |

**Response Fields — each stats entry**:

| Field | Type | Description |
|---|---|---|
| `platform` | string | Platform identifier (e.g., `"twitch"`, `"discord"`, `"slack"`, `"youtube"`, `"spotify"`, `"kick"`) |
| `integration_type` | string | Integration type as stored in `platform_integrations.integration_type` (e.g., `"bot"`) |
| `total` | integer | Total number of active integrations for this platform/type pair |
| `expiring_soon` | integer | Count of integrations with `expires_at < NOW() + 5 minutes` — tokens the refresh service should pick up on the next cycle |
| `expired` | integer | Count of integrations with `expires_at < NOW()` — tokens that have already expired and may be causing API call failures |

**Interpretation**:

- `expiring_soon > 0`: Normal if the refresh service is running; it will handle these on the next poll.
- `expired > 0`: Indicates tokens that the refresh service did not successfully refresh before expiry. This requires investigation — check `total_errors` on the health endpoint and review logs.
- Empty `stats` array: Either no `platform_integrations` rows are marked `is_active = TRUE`, or the database query returned no results. This is not an error state — it means no integrations are configured.

---

### POST /api/v1/credentials/refresh-now

Immediately triggers a full refresh cycle outside of the scheduled polling interval. The response includes the count of credentials successfully refreshed in this cycle.

**Authentication**: None required (internal service).

**Request**:

```
POST /api/v1/credentials/refresh-now HTTP/1.1
Host: localhost:8095
Content-Length: 0
```

No request body is required or accepted.

**Response — 200 OK**:

```json
{
  "success": true,
  "message": "Refreshed 5 credentials"
}
```

**Response — 503 Service Unavailable (not initialized)**:

```json
{
  "error": "Service not initialized"
}
```

**Response Fields**:

| Field | Type | Description |
|---|---|---|
| `success` | boolean | `true` on success |
| `message` | string | Human-readable summary including the count of tokens refreshed in this cycle |

**Refresh cycle behavior**:

This endpoint runs exactly one refresh cycle synchronously (relative to the request lifecycle). The cycle:

1. Queries for all active integrations where `expires_at < NOW() + TOKEN_REFRESH_BUFFER`.
2. Calls the platform OAuth token endpoint for each.
3. Writes new tokens to the database.
4. Publishes Redis pub/sub events.
5. Returns the count of successfully refreshed tokens.

The count in the response reflects only tokens that were actually refreshed in this cycle (i.e., those that were expiring or already expired). If no tokens meet the expiry threshold, the count will be `0`, which is a normal response — not an error.

**Important**: Calling this endpoint does not reset or interfere with the background polling schedule. The next scheduled poll will run at the normal `POLL_INTERVAL` offset from the previous poll, regardless of manual calls to this endpoint.

---

## Response Structures

### Health Response

```json
{
  "status": "<string: healthy|degraded>",
  "module": "<string: module name>",
  "version": "<string: semver>",
  "running": "<boolean>",
  "last_cycle": "<string: ISO8601 UTC or null>",
  "total_refreshed": "<integer>",
  "total_errors": "<integer>"
}
```

### Credential Status Response

```json
{
  "success": "<boolean>",
  "stats": [
    {
      "platform": "<string: platform name>",
      "integration_type": "<string: integration type>",
      "total": "<integer>",
      "expiring_soon": "<integer>",
      "expired": "<integer>"
    }
  ]
}
```

### Force Refresh Response

```json
{
  "success": "<boolean>",
  "message": "<string: human-readable result>"
}
```

### Error Response (not initialized)

```json
{
  "error": "<string: error description>"
}
```

---

## Error Reference

| HTTP Status | Condition | Response Body |
|---|---|---|
| `200` | Request succeeded | Endpoint-specific JSON |
| `503` | Module not initialized | `{"error": "Service not initialized"}` |
| `503` | Health check — refresh service not running | Health JSON with `"status": "degraded"` |

The module does not currently return `400`, `401`, `403`, `404`, or `500` status codes from these three endpoints. All internal errors during a refresh cycle are logged and counted in `total_errors` but do not cause the HTTP endpoints to fail — the endpoints return 200 with the actual refresh count.

---

## Redis Event Schema

When the module successfully refreshes a token, it publishes to Redis using the following channel naming convention:

```
credentials:<platform>:<integration_type>[:<community_id>]:refreshed
```

**Channel pattern examples**:

```
credentials:twitch:bot:42:refreshed
credentials:discord:bot:refreshed
credentials:slack:bot:123:refreshed
credentials:youtube:bot:7:refreshed
credentials:spotify:bot:refreshed
credentials:kick:bot:55:refreshed
```

**Message payload**: ISO 8601 UTC timestamp string indicating when the refresh completed.

```
2026-02-16T12:34:56.789012+00:00
```

**Channel construction logic**:
- Prefix: value of `REDIS_KEY_PREFIX` environment variable (default: `credentials:`)
- Platform segment: `platform_integrations.platform` field value
- Integration type segment: `platform_integrations.integration_type` field value
- Community ID segment: `platform_integrations.community_id` if set, omitted if null
- Suffix: `:refreshed`

Subscribers should use pattern subscriptions if they want to receive events for all communities:

```
PSUBSCRIBE credentials:twitch:bot:*:refreshed
```

---

## Database Integration Schema

The module reads from and writes to the `platform_integrations` table. The following columns are used by the Credential Manager:

| Column | Read | Write | Description |
|---|---|---|---|
| `id` | Yes | No | Primary key, used to identify the row on update |
| `platform` | Yes | No | Platform name (`twitch`, `discord`, etc.) |
| `integration_type` | Yes | No | Type of integration (e.g., `bot`) |
| `community_id` | Yes | No | Optional community ID for scoped integrations |
| `user_id` | Yes | No | Optional user ID for user-scoped integrations |
| `access_token` | Yes | Yes | OAuth access token — refreshed by this module |
| `refresh_token` | Yes | Yes | OAuth refresh token — used to get new access token; may be updated on refresh |
| `client_id` | Yes | No | OAuth application client ID |
| `client_secret` | Yes | No | OAuth application client secret |
| `token_type` | Yes | Yes | Token type (typically `Bearer`) |
| `expires_at` | Yes | Yes | UTC timestamp when the access token expires |
| `scopes` | Yes | Yes | Array of authorized scopes |
| `config_data` | Yes | No | Platform-specific JSON configuration |
| `is_active` | Yes | No | Only active integrations (`is_active = TRUE`) are processed |
| `updated_at` | No | Yes | Set to `NOW()` on every successful token update |

**Write behavior**: The module only writes to `access_token`, `refresh_token`, `token_type`, `expires_at`, `scopes`, and `updated_at`. It never modifies `client_id`, `client_secret`, `config_data`, `community_id`, `user_id`, `platform`, `integration_type`, `is_active`, or `id`.
