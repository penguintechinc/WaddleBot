# LFG Interaction Module - API Reference

## Base URL

```
http://localhost:8096/api/v1
```

All endpoints return JSON responses with standard HTTP status codes and error messages.

## Authentication

Authentication is handled via the Core API. Include `Authorization: Bearer {token}` header for authenticated endpoints. The module validates tokens via Core API before processing requests.

## Response Format

### Success Response
```json
{
  "status": "success",
  "data": { /* endpoint-specific data */ },
  "timestamp": "2026-02-24T10:30:00Z"
}
```

### Error Response
```json
{
  "status": "error",
  "error": "error_code",
  "message": "Human-readable error message",
  "timestamp": "2026-02-24T10:30:00Z"
}
```

## Endpoints

### 1. Create LFG Post

**POST** `/lfg/posts`

Create a new LFG post for a community.

#### Request Body
```json
{
  "community_id": "uuid-string",
  "user_id": "uuid-string",
  "platform": "discord",
  "game": "Valorant",
  "activity": "ranked",
  "role": "DPS",
  "rank_or_level": "Immortal",
  "player_count_needed": 3,
  "message": "Looking for 3v3 players, EU servers preferred"
}
```

#### Parameters
| Parameter | Type | Required | Notes |
|-----------|------|----------|-------|
| community_id | UUID | Yes | Community ID from Core API |
| user_id | UUID | Yes | Creator's user ID |
| platform | String | Yes | discord, twitch, youtube, slack, kick |
| game | String | Yes | Game title (searchable) |
| activity | String | Yes | raid, pvp, pve, coop, casual, ranked |
| role | String | Yes | DPS, tank, healer, support, any |
| rank_or_level | String | Yes | Skill level or rank |
| player_count_needed | Integer | Yes | Players needed (1-100) |
| message | String | No | Optional context (max 500 chars) |

#### Response
```json
{
  "status": "success",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "community_id": "uuid-string",
    "user_id": "uuid-string",
    "platform": "discord",
    "game": "Valorant",
    "activity": "ranked",
    "role": "DPS",
    "rank_or_level": "Immortal",
    "player_count_needed": 3,
    "current_player_count": 1,
    "message": "Looking for 3v3 players, EU servers preferred",
    "status": "open",
    "expires_at": "2026-02-24T12:30:00Z",
    "created_at": "2026-02-24T10:30:00Z"
  }
}
```

#### Status Codes
- `201 Created` — Post created successfully
- `400 Bad Request` — Invalid input (missing fields, invalid platform, etc.)
- `401 Unauthorized` — Invalid token
- `409 Conflict` — User has reached max active posts (3)
- `500 Internal Server Error` — Database error

#### Example Request
```bash
curl -X POST http://localhost:8096/api/v1/lfg/posts \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer token" \
  -d '{
    "community_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": "550e8400-e29b-41d4-a716-446655440001",
    "platform": "discord",
    "game": "Valorant",
    "activity": "ranked",
    "role": "DPS",
    "rank_or_level": "Immortal",
    "player_count_needed": 3,
    "message": "Looking for 3v3 players, EU servers preferred"
  }'
```

---

### 2. List LFG Posts

**GET** `/lfg/posts/{community_id}`

List all active LFG posts in a community with optional filtering.

#### Path Parameters
| Parameter | Type | Required | Notes |
|-----------|------|----------|-------|
| community_id | UUID | Yes | Community ID |

#### Query Parameters
| Parameter | Type | Notes |
|-----------|------|-------|
| game | String | Filter by game title (optional) |
| activity | String | Filter by activity type (optional) |
| status | String | Filter by status: open, filled, all (default: open) |
| limit | Integer | Max results (default: 50, max: 200) |
| offset | Integer | Pagination offset (default: 0) |

#### Response
```json
{
  "status": "success",
  "data": {
    "posts": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "community_id": "uuid-string",
        "user_id": "uuid-string",
        "game": "Valorant",
        "activity": "ranked",
        "role": "DPS",
        "rank_or_level": "Immortal",
        "player_count_needed": 3,
        "current_player_count": 2,
        "message": "Looking for 3v3 players, EU servers preferred",
        "status": "open",
        "expires_at": "2026-02-24T12:30:00Z",
        "created_at": "2026-02-24T10:30:00Z"
      }
    ],
    "total": 42,
    "limit": 50,
    "offset": 0
  }
}
```

#### Status Codes
- `200 OK` — Posts retrieved
- `400 Bad Request` — Invalid query parameters
- `404 Not Found` — Community not found
- `500 Internal Server Error` — Database error

#### Example Requests
```bash
# List all open posts
curl http://localhost:8096/api/v1/lfg/posts/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer token"

# Filter by game
curl http://localhost:8096/api/v1/lfg/posts/550e8400-e29b-41d4-a716-446655440000?game=Valorant \
  -H "Authorization: Bearer token"

# Filter by activity and status
curl http://localhost:8096/api/v1/lfg/posts/550e8400-e29b-41d4-a716-446655440000?activity=raid&status=open \
  -H "Authorization: Bearer token"
```

---

### 3. Join LFG Post

**POST** `/lfg/posts/{post_id}/join`

Join an existing LFG post as a participant.

#### Path Parameters
| Parameter | Type | Required | Notes |
|-----------|------|----------|-------|
| post_id | UUID | Yes | Post ID |

#### Request Body
```json
{
  "user_id": "uuid-string",
  "platform": "discord",
  "display_name": "PlayerName#1234"
}
```

#### Parameters
| Parameter | Type | Required | Notes |
|-----------|------|----------|-------|
| user_id | UUID | Yes | Participant's user ID |
| platform | String | Yes | discord, twitch, youtube, slack, kick |
| display_name | String | Yes | User's display name |

#### Response
```json
{
  "status": "success",
  "data": {
    "post_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": "uuid-string",
    "current_player_count": 3,
    "player_count_needed": 3,
    "status": "filled",
    "joined_at": "2026-02-24T10:35:00Z"
  }
}
```

#### Status Codes
- `200 OK` — Successfully joined
- `400 Bad Request` — Invalid input
- `401 Unauthorized` — Invalid token
- `404 Not Found` — Post not found or post is not open
- `409 Conflict` — User already joined, post is filled, or post is expired
- `500 Internal Server Error` — Database error

#### Example Request
```bash
curl -X POST http://localhost:8096/api/v1/lfg/posts/550e8400-e29b-41d4-a716-446655440000/join \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer token" \
  -d '{
    "user_id": "550e8400-e29b-41d4-a716-446655440002",
    "platform": "discord",
    "display_name": "PlayerName#1234"
  }'
```

#### Behavior
- If `current_player_count` reaches `player_count_needed`, post status automatically transitions to `filled`
- User can only join once per post (enforced by unique constraint)
- Cannot join expired or cancelled posts

---

### 4. Leave LFG Post

**DELETE** `/lfg/posts/{post_id}/join`

Leave an LFG post as a participant.

#### Path Parameters
| Parameter | Type | Required | Notes |
|-----------|------|----------|-------|
| post_id | UUID | Yes | Post ID |

#### Request Body
```json
{
  "user_id": "uuid-string"
}
```

#### Parameters
| Parameter | Type | Required | Notes |
|-----------|------|----------|-------|
| user_id | UUID | Yes | User leaving the post |

#### Response
```json
{
  "status": "success",
  "data": {
    "post_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": "uuid-string",
    "current_player_count": 2,
    "player_count_needed": 3,
    "status": "open",
    "left_at": "2026-02-24T10:40:00Z"
  }
}
```

#### Status Codes
- `200 OK` — Successfully left
- `400 Bad Request` — Invalid input
- `401 Unauthorized` — Invalid token
- `404 Not Found` — Post or join record not found
- `500 Internal Server Error` — Database error

#### Example Request
```bash
curl -X DELETE http://localhost:8096/api/v1/lfg/posts/550e8400-e29b-41d4-a716-446655440000/join \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer token" \
  -d '{
    "user_id": "550e8400-e29b-41d4-a716-446655440002"
  }'
```

#### Behavior
- If post was `filled` and removing user brings count below needed, status reverts to `open`
- Post creator cannot leave their own post (use cancel endpoint instead)

---

### 5. Cancel LFG Post

**DELETE** `/lfg/posts/{post_id}`

Cancel an LFG post (creator only).

#### Path Parameters
| Parameter | Type | Required | Notes |
|-----------|------|----------|-------|
| post_id | UUID | Yes | Post ID |

#### Request Body
```json
{
  "user_id": "uuid-string"
}
```

#### Parameters
| Parameter | Type | Required | Notes |
|-----------|------|----------|-------|
| user_id | UUID | Yes | Creator's user ID (verified) |

#### Response
```json
{
  "status": "success",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "cancelled",
    "cancelled_at": "2026-02-24T10:45:00Z",
    "previous_status": "open"
  }
}
```

#### Status Codes
- `200 OK` — Post cancelled
- `401 Unauthorized` — Invalid token or user is not creator
- `404 Not Found` — Post not found
- `409 Conflict` — Post already cancelled or expired
- `500 Internal Server Error` — Database error

#### Example Request
```bash
curl -X DELETE http://localhost:8096/api/v1/lfg/posts/550e8400-e29b-41d4-a716-446655440000 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer token" \
  -d '{
    "user_id": "550e8400-e29b-41d4-a716-446655440001"
  }'
```

#### Behavior
- Only post creator can cancel
- All joins are automatically cleaned up
- Status transitions to `cancelled`
- Cannot cancel already expired or cancelled posts

---

### 6. Expire Old Posts

**POST** `/lfg/expire`

Background cron endpoint to expire old posts (system-only).

#### Request Body
```json
{
  "cron_token": "secret-token"
}
```

#### Parameters
| Parameter | Type | Required | Notes |
|-----------|------|----------|-------|
| cron_token | String | Yes | Internal cron token (from environment) |

#### Response
```json
{
  "status": "success",
  "data": {
    "expired_count": 12,
    "timestamp": "2026-02-24T10:50:00Z"
  }
}
```

#### Status Codes
- `200 OK` — Expiry process completed
- `401 Unauthorized` — Invalid cron token
- `500 Internal Server Error` — Database error

#### Example Request
```bash
curl -X POST http://localhost:8096/api/v1/lfg/expire \
  -H "Content-Type: application/json" \
  -d '{
    "cron_token": "internal-secret-token"
  }'
```

#### Behavior
- Scans all posts with `status = open` or `status = filled`
- Transitions posts with `expires_at < now()` to `expired`
- Cleans up associated join records
- Run hourly via scheduler or orchestration system

---

## Common Error Codes

| Error Code | HTTP Status | Description |
|-----------|-----------|-------------|
| VALIDATION_ERROR | 400 | Invalid input parameters |
| UNAUTHORIZED | 401 | Invalid or missing token |
| COMMUNITY_NOT_FOUND | 404 | Community does not exist |
| POST_NOT_FOUND | 404 | LFG post does not exist |
| POST_NOT_OPEN | 409 | Post is filled, expired, or cancelled |
| ALREADY_JOINED | 409 | User already joined this post |
| MAX_POSTS_EXCEEDED | 409 | User has reached max active posts limit |
| INSUFFICIENT_PERMISSIONS | 401 | User is not post creator |
| DATABASE_ERROR | 500 | Internal database error |
| SERVICE_UNAVAILABLE | 503 | Service temporarily unavailable |

---

## Rate Limiting

The module implements optional rate limiting via Redis:
- **Per-user**: 100 requests/minute
- **Per-IP**: 500 requests/minute
- **Headers**: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`

---

## Pagination

List endpoints support pagination:
```
?limit=50&offset=0
```

- **Default limit**: 50
- **Max limit**: 200
- **Default offset**: 0

Response includes `total`, `limit`, `offset` for client-side pagination.

---

## Filtering

### By Game
```
GET /lfg/posts/{community_id}?game=Valorant
```

Case-insensitive prefix match.

### By Activity
```
GET /lfg/posts/{community_id}?activity=raid
```

Exact match. Valid values: raid, pvp, pve, coop, casual, ranked

### By Status
```
GET /lfg/posts/{community_id}?status=open
```

Valid values: open, filled, expired, cancelled, all (default: open)

---

## Webhooks & Integrations

Future versions may support webhooks for post creation, status changes, and expiry events. Subscribe via Core API integration settings.
