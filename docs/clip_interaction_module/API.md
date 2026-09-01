# Clip Interaction Module - API Reference

Complete REST API documentation for the Clip Interaction Module with examples and response schemas.

## Base URL

```
http://localhost:8098
```

## Authentication

All endpoints require Bearer token in Authorization header:

```
Authorization: Bearer <jwt-token>
```

Tokens are issued by core-api and validated by the auth middleware.

## Clip Creation

### Create Clip via Twitch Proxy

Creates a new clip by proxying to the action-twitch module. The actual clip creation happens on Twitch, and this endpoint manages the process.

```
POST /api/v1/clips/<community_id>/create
```

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `community_id` | UUID | Community identifier |

**Request Body**

```json
{
  "broadcast_id": "string",
  "title": "string",
  "language": "string (optional, default: en)",
  "has_delay": "boolean (optional, default: false)"
}
```

**Response** (200 OK)

```json
{
  "id": "uuid",
  "status": "created",
  "clip_id": "string",
  "clip_url": "string",
  "title": "string",
  "created_at": "ISO8601 datetime"
}
```

**Example**

```bash
curl -X POST http://localhost:8098/api/v1/clips/123e4567-e89b-12d3-a456-426614174000/create \
  -H "Authorization: Bearer eyJhbGc..." \
  -H "Content-Type: application/json" \
  -d '{
    "broadcast_id": "twitch_broadcast_123",
    "title": "Amazing Clutch Play!",
    "language": "en",
    "has_delay": false
  }'
```

**Error Responses**

| Status | Code | Description |
|--------|------|-------------|
| 400 | BAD_REQUEST | Invalid broadcast_id or title |
| 401 | UNAUTHORIZED | Invalid or missing token |
| 404 | COMMUNITY_NOT_FOUND | Community does not exist |
| 503 | SERVICE_UNAVAILABLE | action-twitch module unreachable |

---

## Clip Bookmarking

### Bookmark a Clip

Saves a clip to the community's bookmark collection with optional tags.

```
POST /api/v1/clips/<community_id>/bookmark
```

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `community_id` | UUID | Community identifier |

**Request Body**

```json
{
  "clip_id": "string",
  "clip_url": "string",
  "title": "string",
  "game": "string (optional)",
  "tags": ["string"] (optional, default: [])
}
```

**Response** (201 Created)

```json
{
  "id": "uuid",
  "community_id": "uuid",
  "clip_id": "string",
  "clip_url": "string",
  "title": "string",
  "game": "string or null",
  "tags": ["string"],
  "bookmarked_by": "uuid",
  "is_highlight": false,
  "created_at": "ISO8601 datetime"
}
```

**Example**

```bash
curl -X POST http://localhost:8098/api/v1/clips/123e4567-e89b-12d3-a456-426614174000/bookmark \
  -H "Authorization: Bearer eyJhbGc..." \
  -H "Content-Type: application/json" \
  -d '{
    "clip_id": "twitch_clip_abc123",
    "clip_url": "https://twitch.tv/clip/abc123",
    "title": "Insane 1v4 Teamfight",
    "game": "League of Legends",
    "tags": ["teamfight", "clutch", "s-tier"]
  }'
```

**Error Responses**

| Status | Code | Description |
|--------|------|-------------|
| 400 | BAD_REQUEST | Missing required fields |
| 409 | CONFLICT | Clip already bookmarked (duplicate community_id + clip_id) |
| 401 | UNAUTHORIZED | Invalid token |

---

## List Clips

### Get Bookmarked Clips

Retrieves clips with filtering and pagination support.

```
GET /api/v1/clips/<community_id>
```

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `community_id` | UUID | Community identifier |

**Query Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `game` | string | None | Filter by game name |
| `tag` | string | None | Filter by tag (case-insensitive) |
| `highlights_only` | boolean | false | Return only highlighted clips |
| `limit` | integer | 50 | Maximum results (1-100) |
| `offset` | integer | 0 | Pagination offset |

**Response** (200 OK)

```json
{
  "total": 150,
  "clips": [
    {
      "id": "uuid",
      "community_id": "uuid",
      "clip_id": "string",
      "clip_url": "string",
      "title": "string",
      "game": "string or null",
      "tags": ["string"],
      "bookmarked_by": "uuid",
      "is_highlight": boolean,
      "created_at": "ISO8601 datetime"
    }
  ],
  "limit": 50,
  "offset": 0
}
```

**Example**

```bash
# Get all clips for a community
curl http://localhost:8098/api/v1/clips/123e4567-e89b-12d3-a456-426614174000 \
  -H "Authorization: Bearer eyJhbGc..."

# Filter by game
curl "http://localhost:8098/api/v1/clips/123e4567-e89b-12d3-a456-426614174000?game=Valorant" \
  -H "Authorization: Bearer eyJhbGc..."

# Get only highlights with pagination
curl "http://localhost:8098/api/v1/clips/123e4567-e89b-12d3-a456-426614174000?highlights_only=true&limit=20&offset=0" \
  -H "Authorization: Bearer eyJhbGc..."
```

---

## Clip Tagging

### Update Clip Tags

Modifies tags for an existing bookmarked clip.

```
PUT /api/v1/clips/<community_id>/<clip_id>/tags
```

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `community_id` | UUID | Community identifier |
| `clip_id` | UUID | Clip bookmark identifier |

**Request Body**

```json
{
  "tags": ["string"]
}
```

**Response** (200 OK)

```json
{
  "id": "uuid",
  "tags": ["string"],
  "updated_at": "ISO8601 datetime"
}
```

**Example**

```bash
curl -X PUT http://localhost:8098/api/v1/clips/123e4567-e89b-12d3-a456-426614174000/550e8400-e29b-41d4-a716-446655440000/tags \
  -H "Authorization: Bearer eyJhbGc..." \
  -H "Content-Type: application/json" \
  -d '{
    "tags": ["gameplay", "highlights", "tips"]
  }'
```

---

## Highlighting

### Mark Clip as Highlight

Flags a clip for inclusion in highlight reels.

```
POST /api/v1/clips/<community_id>/<clip_id>/highlight
```

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `community_id` | UUID | Community identifier |
| `clip_id` | UUID | Clip bookmark identifier |

**Request Body**

```json
{}
```

**Response** (200 OK)

```json
{
  "id": "uuid",
  "is_highlight": true,
  "updated_at": "ISO8601 datetime"
}
```

**Example**

```bash
curl -X POST http://localhost:8098/api/v1/clips/123e4567-e89b-12d3-a456-426614174000/550e8400-e29b-41d4-a716-446655440000/highlight \
  -H "Authorization: Bearer eyJhbGc..." \
  -H "Content-Type: application/json" \
  -d '{}'
```

---

## Highlight Reels

### Create Highlight Reel

Combines multiple highlighted clips into a new reel.

```
POST /api/v1/reels/<community_id>
```

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `community_id` | UUID | Community identifier |

**Request Body**

```json
{
  "name": "string",
  "description": "string (optional)",
  "clip_ids": ["uuid"]
}
```

**Response** (201 Created)

```json
{
  "id": "uuid",
  "community_id": "uuid",
  "name": "string",
  "description": "string or null",
  "clip_ids": ["uuid"],
  "created_by": "uuid",
  "is_published": false,
  "created_at": "ISO8601 datetime"
}
```

**Example**

```bash
curl -X POST http://localhost:8098/api/v1/reels/123e4567-e89b-12d3-a456-426614174000 \
  -H "Authorization: Bearer eyJhbGc..." \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Week 1 Highlights",
    "description": "Best plays from week 1 tournament run",
    "clip_ids": [
      "550e8400-e29b-41d4-a716-446655440000",
      "660e8400-e29b-41d4-a716-446655440001",
      "770e8400-e29b-41d4-a716-446655440002"
    ]
  }'
```

---

### Get Highlight Reel

Retrieves a specific reel with all clip metadata.

```
GET /api/v1/reels/<community_id>/<reel_id>
```

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `community_id` | UUID | Community identifier |
| `reel_id` | UUID | Reel identifier |

**Response** (200 OK)

```json
{
  "id": "uuid",
  "community_id": "uuid",
  "name": "string",
  "description": "string or null",
  "clips": [
    {
      "id": "uuid",
      "clip_id": "string",
      "title": "string",
      "clip_url": "string"
    }
  ],
  "created_by": "uuid",
  "is_published": boolean,
  "created_at": "ISO8601 datetime"
}
```

**Example**

```bash
curl http://localhost:8098/api/v1/reels/123e4567-e89b-12d3-a456-426614174000/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer eyJhbGc..."
```

---

### Publish Highlight Reel

Marks a reel as published (ready for sharing).

```
PUT /api/v1/reels/<community_id>/<reel_id>/publish
```

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `community_id` | UUID | Community identifier |
| `reel_id` | UUID | Reel identifier |

**Request Body**

```json
{}
```

**Response** (200 OK)

```json
{
  "id": "uuid",
  "is_published": true,
  "published_at": "ISO8601 datetime"
}
```

**Example**

```bash
curl -X PUT http://localhost:8098/api/v1/reels/123e4567-e89b-12d3-a456-426614174000/550e8400-e29b-41d4-a716-446655440000/publish \
  -H "Authorization: Bearer eyJhbGc..." \
  -H "Content-Type: application/json" \
  -d '{}'
```

---

## OBS Overlay

### Get Overlay Data

Returns the 5 most recent highlighted clips for OBS overlay display.

```
GET /api/v1/overlay/<community_id>
```

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `community_id` | UUID | Community identifier |

**Response** (200 OK)

```json
{
  "community_id": "uuid",
  "highlights": [
    {
      "id": "uuid",
      "title": "string",
      "clip_url": "string",
      "created_at": "ISO8601 datetime"
    }
  ],
  "total": integer,
  "last_updated": "ISO8601 datetime"
}
```

**Example**

```bash
curl http://localhost:8098/api/v1/overlay/123e4567-e89b-12d3-a456-426614174000 \
  -H "Authorization: Bearer eyJhbGc..."
```

---

## Health & Status

### Health Check

```
GET /health
```

**Response** (200 OK)

```json
{
  "status": "healthy",
  "timestamp": "ISO8601 datetime"
}
```

---

## Error Handling

All error responses follow this format:

```json
{
  "error": "ERROR_CODE",
  "message": "Human-readable description",
  "request_id": "correlation-uuid",
  "timestamp": "ISO8601 datetime"
}
```

**Common Error Codes**

| Code | HTTP | Description |
|------|------|-------------|
| BAD_REQUEST | 400 | Invalid request parameters |
| UNAUTHORIZED | 401 | Missing or invalid token |
| FORBIDDEN | 403 | Insufficient permissions |
| NOT_FOUND | 404 | Resource not found |
| CONFLICT | 409 | Resource already exists |
| VALIDATION_ERROR | 422 | Request validation failed |
| RATE_LIMITED | 429 | Too many requests |
| INTERNAL_ERROR | 500 | Server error |
| SERVICE_UNAVAILABLE | 503 | External service error |
