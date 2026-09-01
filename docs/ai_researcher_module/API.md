# AI Researcher Module — API Reference

## Overview

The AI Researcher Module exposes a REST API with the following endpoint groups:

- **Public Endpoints** — Authenticated, user-facing research and insights
- **Admin Endpoints** — Community admin configuration and analysis
- **System Endpoints** — Health checks and internal metrics

All endpoints use JSON for request/response bodies. Timestamps are ISO 8601 format (UTC).

## HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad request (validation error) |
| 401 | Unauthorized (missing auth) |
| 403 | Forbidden (insufficient permission) |
| 404 | Not found |
| 429 | Rate limited |
| 500 | Server error |

## Authentication

### Standard Authentication

Use bearer token in Authorization header:
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8070/api/v1/...
```

### Service Key Authentication

Internal service endpoints require `X-Service-Key` header:
```bash
curl -H "X-Service-Key: YOUR_SERVICE_KEY" http://localhost:8070/api/v1/researcher/messages/firehose
```

---

## Public Endpoints

### GET /api/v1/status

Get module status and available features.

**Request:**
```http
GET /api/v1/status HTTP/1.1
Host: localhost:8070
Authorization: Bearer YOUR_TOKEN
```

**Response (200):**
```json
{
  "success": true,
  "status": "operational",
  "module": "ai_researcher_module",
  "version": "1.0.0",
  "features": {
    "ai_research": true,
    "bot_detection": true,
    "mem0_integration": true,
    "context_tracking": true,
    "stream_awareness": true
  }
}
```

---

### POST /api/v1/researcher/research

Perform topic research with optional context awareness.

**Request:**
```json
{
  "community_id": 123,
  "user_id": 456,
  "platform": "discord",
  "query": "What is semantic search?",
  "max_queries": 5
}
```

**Parameters:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| community_id | int | Yes | Community identifier |
| user_id | int | Yes | User performing research |
| platform | string | Yes | Platform (discord, twitch, etc.) |
| query | string | Yes | Research topic |
| max_queries | int | No | Max search queries (default: 3) |

**Response (200):**
```json
{
  "success": true,
  "content": "Semantic search is a technique where the search engine...",
  "tokens_used": 156,
  "processing_time_ms": 1840,
  "was_cached": false,
  "blocked_reason": null
}
```

**Errors:**
- 400: community_id or query missing
- 429: Rate limit exceeded

---

### POST /api/v1/researcher/ask

Ask a question with community context awareness.

**Request:**
```json
{
  "community_id": 123,
  "user_id": 456,
  "platform": "discord",
  "question": "What features did we decide to build?",
  "include_context": true
}
```

**Parameters:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| community_id | int | Yes | Community identifier |
| user_id | int | Yes | User asking question |
| platform | string | Yes | Platform |
| question | string | Yes | Question text |
| include_context | bool | No | Use conversation context (default: true) |

**Response (200):**
```json
{
  "success": true,
  "content": "Based on our earlier discussion, the team decided to...",
  "tokens_used": 89,
  "processing_time_ms": 1050,
  "was_cached": false,
  "blocked_reason": null
}
```

**Errors:**
- 400: community_id or question missing
- 429: Rate limit exceeded

---

### POST /api/v1/researcher/recall

Perform semantic search through stored memories.

**Request:**
```json
{
  "community_id": 123,
  "user_id": 456,
  "platform": "discord",
  "query": "meetings",
  "limit": 5
}
```

**Parameters:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| community_id | int | Yes | Community identifier |
| user_id | int | Yes | User recalling |
| platform | string | Yes | Platform |
| query | string | Yes | Search query |
| limit | int | No | Max results (default: 10) |

**Response (200):**
```json
{
  "success": true,
  "content": "Found memories: Q1 Planning Meeting 2026-02-10...",
  "tokens_used": 0,
  "processing_time_ms": 234,
  "was_cached": false,
  "blocked_reason": null
}
```

**Errors:**
- 400: community_id or query missing
- 429: Rate limit exceeded

---

### POST /api/v1/researcher/summarize

Summarize recent conversation or stream activity.

**Request:**
```json
{
  "community_id": 123,
  "user_id": 456,
  "platform": "discord",
  "duration_minutes": 120,
  "topic": "product announcements"
}
```

**Parameters:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| community_id | int | Yes | Community identifier |
| user_id | int | Yes | User requesting summary |
| platform | string | Yes | Platform |
| duration_minutes | int | No | Time window (default: 60) |
| topic | string | No | Specific topic to focus on |

**Response (200):**
```json
{
  "success": true,
  "content": "Over the past 2 hours, the community discussed...",
  "tokens_used": 234,
  "processing_time_ms": 2100,
  "was_cached": false,
  "blocked_reason": null
}
```

---

### GET /api/v1/researcher/{community_id}/context

Get recent conversation context messages.

**Request:**
```http
GET /api/v1/researcher/123/context?limit=50&since=2026-02-16T10:00:00Z HTTP/1.1
```

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| limit | int | 100 | Max messages to return |
| since | string | null | ISO 8601 timestamp to fetch messages since |

**Response (200):**
```json
{
  "success": true,
  "community_id": 123,
  "messages": [
    {
      "id": 1,
      "platform": "discord",
      "platform_user_id": "user123",
      "platform_username": "john_doe",
      "message_content": "Hello everyone!",
      "message_type": "chat",
      "metadata": {"channel": "general"},
      "created_at": "2026-02-16T14:30:00Z"
    }
  ],
  "count": 1
}
```

---

### GET /api/v1/researcher/{community_id}/memory

Get stored memories for a community.

**Request:**
```http
GET /api/v1/researcher/123/memory?query=python&limit=10 HTTP/1.1
```

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| query | string | null | Search query for memories |
| limit | int | 10 | Max memories to return |

**Response (200):**
```json
{
  "success": true,
  "community_id": 123,
  "memories": [
    {
      "id": "mem_001",
      "text": "Discussion about Python 3.12 release",
      "relevance_score": 0.94,
      "created_at": "2026-02-10T10:30:00Z"
    }
  ],
  "count": 1
}
```

---

### GET /api/v1/researcher/{community_id}/insights

Get previously generated insights.

**Request:**
```http
GET /api/v1/researcher/123/insights?limit=20&type=sentiment&days=90 HTTP/1.1
```

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| limit | int | 20 | Max insights |
| type | string | null | Filter by type (activity, sentiment, trending) |
| days | int | 90 | Historical period |

**Response (200):**
```json
{
  "success": true,
  "community_id": 123,
  "insights": [
    {
      "id": 1,
      "type": "sentiment",
      "content": "Community sentiment is positive...",
      "metadata": {"score": 0.78},
      "period_start": "2026-02-10T00:00:00Z",
      "period_end": "2026-02-16T23:59:59Z",
      "created_at": "2026-02-16T10:00:00Z"
    }
  ],
  "count": 1
}
```

---

### POST /api/v1/researcher/{community_id}/insights/generate

Generate new AI-powered insights.

**Request:**
```json
{
  "timeframe": "7d",
  "insight_types": ["activity", "trending", "sentiment"]
}
```

**Parameters:**
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| timeframe | string | 7d | Period (1d, 7d, 30d, 90d) |
| insight_types | array | ["activity"] | Types to generate |

**Response (200):**
```json
{
  "success": true,
  "insight_id": "insight_001",
  "content": "Community activity increased 45% this week...",
  "insight_type": "activity",
  "tokens_used": 289,
  "processing_time_ms": 3200
}
```

---

### GET /api/v1/researcher/{community_id}/sentiment

Get sentiment analysis for community.

**Request:**
```http
GET /api/v1/researcher/123/sentiment?timeframe=7d HTTP/1.1
```

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| timeframe | string | 7d | Analysis period |

**Response (200):**
```json
{
  "success": true,
  "community_id": 123,
  "overall_sentiment": "positive",
  "sentiment_score": 0.78,
  "message_count": 542,
  "sentiment_distribution": {
    "positive": 75,
    "neutral": 20,
    "negative": 5
  },
  "trends": ["increasing_positivity"],
  "processing_time_ms": 1500
}
```

---

### GET /api/v1/researcher/{community_id}/anomalies

Get detected anomalies.

**Request:**
```http
GET /api/v1/researcher/123/anomalies?hours=24&acknowledged=false&limit=50 HTTP/1.1
```

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| hours | int | 24 | Time window |
| acknowledged | bool | false | Filter by review status |
| limit | int | 50 | Max results |

**Response (200):**
```json
{
  "success": true,
  "community_id": 123,
  "anomalies": [
    {
      "id": 1,
      "anomaly_type": "spike",
      "description": "Message volume spike detected",
      "severity": "medium",
      "acknowledged": false,
      "created_at": "2026-02-16T10:00:00Z"
    }
  ],
  "count": 1
}
```

---

### POST /api/v1/researcher/{community_id}/anomalies/{anomaly_id}/acknowledge

Mark anomaly as reviewed.

**Request:**
```json
{
  "admin_id": 789,
  "notes": "Confirmed - valid activity spike"
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Anomaly acknowledged"
}
```

---

### GET /api/v1/researcher/{community_id}/user/{platform}/{user_id}/profile

Get user behavior profile.

**Request:**
```http
GET /api/v1/researcher/123/user/discord/user456/profile?days=90 HTTP/1.1
```

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| days | int | 90 | Historical period |

**Response (200):**
```json
{
  "success": true,
  "profile_id": "profile_001",
  "user_id": "user456",
  "activity_level": "high",
  "communication_style": "collaborative",
  "preferred_hours": "18:00-23:00",
  "average_message_length": 156,
  "total_messages": 342,
  "community_role": "moderator",
  "processing_time_ms": 800
}
```

---

### GET /api/v1/researcher/{community_id}/users/profiles

Get all user profiles in community.

**Request:**
```http
GET /api/v1/researcher/123/users/profiles?role=moderator&limit=100 HTTP/1.1
```

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| role | string | null | Filter by role |
| limit | int | 100 | Max profiles |

**Response (200):**
```json
{
  "success": true,
  "community_id": 123,
  "profiles": [
    {
      "profile_id": "profile_001",
      "user_id": "user456",
      "activity_level": "high",
      "communication_style": "collaborative",
      "community_role": "moderator"
    }
  ],
  "count": 1
}
```

---

## Admin Endpoints

All admin endpoints require `X-Service-Key` header.

### POST /api/v1/researcher/messages/firehose

Ingest messages for context tracking.

**Request:**
```json
{
  "messages": [
    {
      "community_id": 123,
      "user_id": 456,
      "platform": "discord",
      "platform_user_id": "user123",
      "username": "john_doe",
      "platform_username": "john_doe",
      "message": "Hello everyone!",
      "timestamp": "2026-02-16T14:30:00Z",
      "metadata": {
        "channel": "general",
        "message_id": "msg_789"
      }
    }
  ]
}
```

**Response (200):**
```json
{
  "success": true,
  "processed": 1,
  "total": 1
}
```

---

### POST /api/v1/researcher/stream/end

Notify stream end and trigger summary.

**Request:**
```json
{
  "community_id": 123,
  "platform": "discord",
  "ended_at": "2026-02-16T16:00:00Z",
  "duration_minutes": 120
}
```

**Response (200):**
```json
{
  "success": true,
  "summary": "Stream summary text..."
}
```

---

### GET /api/v1/admin/{community_id}/ai-insights

Get AI insights (admin view).

**Request:**
```http
GET /api/v1/admin/123/ai-insights?limit=20&type=sentiment HTTP/1.1
X-Service-Key: YOUR_SERVICE_KEY
```

**Response (200):**
```json
{
  "success": true,
  "community_id": 123,
  "insights": [
    {
      "id": 1,
      "insight_type": "sentiment",
      "title": "Weekly Sentiment Summary",
      "content": "Content here...",
      "content_html": "<p>Content here...</p>",
      "metadata": {"score": 0.78},
      "period_start": "2026-02-10T00:00:00Z",
      "period_end": "2026-02-16T23:59:59Z",
      "created_at": "2026-02-16T10:00:00Z"
    }
  ],
  "count": 1
}
```

---

### GET /api/v1/admin/{community_id}/ai-researcher/config

Get AI Researcher configuration.

**Response (200):**
```json
{
  "success": true,
  "config": {
    "community_id": 123,
    "firehose_enabled": true,
    "bot_detection_enabled": true,
    "bot_detection_threshold": 0.7,
    "research_max_queries": 30,
    "summary_enabled": true,
    "mem0_enabled": true,
    "ai_provider": "ollama",
    "is_premium": false,
    "created_at": "2026-02-01T10:00:00Z",
    "updated_at": "2026-02-16T10:00:00Z"
  }
}
```

---

### PUT /api/v1/admin/{community_id}/ai-researcher/config

Update AI Researcher configuration.

**Request:**
```json
{
  "admin_id": 789,
  "firehose_enabled": true,
  "bot_detection_enabled": true,
  "bot_detection_threshold": 0.75,
  "research_max_queries": 50,
  "mem0_enabled": true
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Configuration updated"
}
```

---

### GET /api/v1/admin/{community_id}/bot-detection

Get bot detection results.

**Request:**
```http
GET /api/v1/admin/123/bot-detection?limit=50&threshold=0.7&flagged_only=false HTTP/1.1
```

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| limit | int | 50 | Max results |
| threshold | float | 0.5 | Min confidence score |
| flagged_only | bool | false | Only unreviewed results |

**Response (200):**
```json
{
  "success": true,
  "community_id": 123,
  "results": [
    {
      "id": 1,
      "platform": "discord",
      "platform_user_id": "bot_user123",
      "platform_username": "suspicious",
      "confidence_score": 0.89,
      "behavioral_patterns": {
        "regular_intervals": true,
        "copy_paste": true
      },
      "timing_regularity": 0.95,
      "response_latency_avg": 0.5,
      "emote_text_ratio": 0.2,
      "copy_paste_frequency": 0.45,
      "account_age_days": 2,
      "recommended_action": "review",
      "is_reviewed": false,
      "admin_notes": null,
      "created_at": "2026-02-16T10:00:00Z"
    }
  ],
  "count": 1,
  "threshold": 0.7
}
```

---

## System Endpoints

### GET /healthz

Health check for Kubernetes.

**Response (200):**
```json
{
  "status": "healthy",
  "module": "ai_researcher_module",
  "version": "1.0.0",
  "checks": {
    "database": "ok",
    "redis": "ok",
    "qdrant": "ok"
  }
}
```

---

## Rate Limiting

All endpoints are rate-limited. Limits are per user and community:

| Endpoint | Default Limit | Per |
|----------|---------------|-----|
| /research | 30/min | user |
| /ask | 30/min | user |
| /recall | 100/min | user |
| /summarize | 10/min | user |
| /insights/generate | 5/min | community |

When rate limited, responses include:
```
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 30
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1645009800
```

---

## Error Responses

All error responses follow this format:

```json
{
  "success": false,
  "error": "Description of error",
  "error_code": "SPECIFIC_ERROR"
}
```

Common error codes:
- `RATE_LIMIT_EXCEEDED` — Too many requests
- `INVALID_PARAMETERS` — Missing or invalid request data
- `UNAUTHORIZED` — Missing authentication
- `COMMUNITY_NOT_FOUND` — Invalid community_id
- `PROVIDER_ERROR` — AI provider error
- `DATABASE_ERROR` — Database error
- `CACHE_ERROR` — Cache/Redis error

---

## API Versioning

Current version: **v1**

Endpoint pattern: `/api/v1/...`

Legacy endpoints (v0) are not supported.

---

## Examples

See [USAGE.md](USAGE.md) for complete workflow examples.
