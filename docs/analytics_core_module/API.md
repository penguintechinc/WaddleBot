# Analytics Core Module — API Reference

**Version:** 1.0.0
**Base URL:** `http://analytics-core:8040/api/v1/`
**Last Updated:** 2026-02-16

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Health Endpoints](#health-endpoints)
4. [Public API Endpoints](#public-api-endpoints)
5. [Internal Service Endpoints](#internal-service-endpoints)
6. [Bot Detection Endpoints](#bot-detection-endpoints)
7. [Response Formats](#response-formats)
8. [Error Codes](#error-codes)

---

## Overview

### Base Paths

- **Public API**: `/api/v1/analytics/` - Available to authenticated clients
- **Internal API**: `/api/v1/internal/` - Service-to-service communication
- **Health**: `/health` - Module status

### Protocol

- **HTTP Method**: GET/POST/PUT as specified
- **Content-Type**: `application/json`
- **Response Format**: JSON with `data` and `status` fields

### Authentication

- **Public endpoints**: Requires authentication via Flask-Security-Too
- **Internal endpoints**: Requires `X-Service-API-Key` header
- **Health endpoint**: No authentication required

---

## Health Endpoints

### Get Module Health

Check if the module is running and dependencies are available.

**Endpoint:** `GET /health`

**Request:**
```bash
curl http://localhost:8040/health
```

**Response (200 OK):**
```json
{
  "status": "healthy",
  "module": "analytics-core",
  "version": "1.0.0",
  "timestamp": "2026-02-16T10:30:00Z",
  "dependencies": {
    "database": "ok",
    "redis": "ok"
  }
}
```

**Response (503 Service Unavailable):**
```json
{
  "status": "unhealthy",
  "module": "analytics-core",
  "error": "Database connection failed"
}
```

---

## Public API Endpoints

### 1. Get Module Status

Basic module information endpoint.

**Endpoint:** `GET /analytics/status`

**Request:**
```bash
curl http://localhost:8040/api/v1/analytics/status
```

**Response (200 OK):**
```json
{
  "data": {
    "module": "analytics-core",
    "version": "1.0.0",
    "status": "healthy"
  },
  "status": "success"
}
```

---

### 2. Get Basic Statistics

Retrieve fundamental analytics metrics (Free tier).

**Endpoint:** `GET /analytics/{community_id}/basic`

**Parameters:**
- `community_id` (path, required): Community identifier

**Request:**
```bash
curl http://localhost:8040/api/v1/analytics/123/basic
```

**Response Schema:**

```json
{
  "data": {
    "total_chatters": 150,
    "total_stream_time_hours": 2450.5,
    "messages_per_user": {
      "alice": 1250,
      "bob": 890,
      "charlie": 750,
      "user_4": 600,
      "user_5": 450,
      "user_6": 380,
      "user_7": 320,
      "user_8": 290,
      "user_9": 250,
      "user_10": 225
    },
    "active_chatters_7d": 85,
    "active_chatters_30d": 120,
    "updated_at": "2026-02-16T10:30:00Z"
  },
  "status": "success"
}
```

**Field Descriptions:**
- `total_chatters` (int): Unique users who sent messages (all-time)
- `total_stream_time_hours` (float): Sum of all watch session durations in hours
- `messages_per_user` (object): Top 10 users by message count
- `active_chatters_7d` (int): Unique users with messages in last 7 days
- `active_chatters_30d` (int): Unique users with messages in last 30 days
- `updated_at` (ISO datetime): When metrics were last calculated

**Error Responses:**
```json
{
  "error": "Community not found",
  "status": "error"
}
```

---

### 3. Get Time-Series Metrics

Query aggregated metrics with configurable time windows and bucket sizes.

**Endpoint:** `GET /analytics/{community_id}/metrics`

**Parameters:**
- `community_id` (path, required): Community identifier
- `metric_type` (query, required): Type of metric
  - `messages` - Message count per bucket
  - `viewers` - Unique viewer count
  - `engagement` - Engagement score
  - `growth` - User growth rate
- `bucket_size` (query, optional, default: `1d`): Time bucket size
  - `1h` - Hourly
  - `1d` - Daily
  - `1w` - Weekly
  - `1m` - Monthly
- `start_date` (query, optional): ISO date (default: 30 days ago)
- `end_date` (query, optional): ISO date (default: now)

**Request:**
```bash
# Last 30 days, daily buckets
curl "http://localhost:8040/api/v1/analytics/123/metrics?metric_type=messages&bucket_size=1d"

# Custom range, hourly buckets
curl "http://localhost:8040/api/v1/analytics/123/metrics?metric_type=messages&bucket_size=1h&start_date=2026-02-15&end_date=2026-02-16"

# Weekly buckets, last quarter
curl "http://localhost:8040/api/v1/analytics/123/metrics?metric_type=engagement&bucket_size=1w&start_date=2025-11-16"
```

**Response Schema:**

```json
{
  "data": {
    "community_id": 123,
    "metric_type": "messages",
    "bucket_size": "1d",
    "start_date": "2026-01-17T00:00:00Z",
    "end_date": "2026-02-16T23:59:59Z",
    "data": [
      {
        "timestamp": "2026-01-17T00:00:00Z",
        "value": 2500.0,
        "metadata": {
          "peak_hour": "19:00",
          "avg_msg_length": 45,
          "unique_users": 120
        }
      },
      {
        "timestamp": "2026-01-18T00:00:00Z",
        "value": 2150.0,
        "metadata": {
          "peak_hour": "20:00",
          "avg_msg_length": 42,
          "unique_users": 110
        }
      }
    ],
    "count": 31
  },
  "status": "success"
}
```

**Field Descriptions:**
- `timestamp` (ISO datetime): Start of time bucket
- `value` (float): Metric value for bucket
- `metadata` (object): Optional additional data for bucket

---

### 4. Get Configuration

Retrieve analytics configuration for a community.

**Endpoint:** `GET /analytics/{community_id}/config`

**Parameters:**
- `community_id` (path, required): Community identifier

**Request:**
```bash
curl http://localhost:8040/api/v1/analytics/123/config
```

**Response Schema:**

```json
{
  "data": {
    "community_id": 123,
    "is_premium": true,
    "basic_stats_enabled": true,
    "community_health_enabled": true,
    "bad_actor_detection_enabled": true,
    "user_journey_enabled": true,
    "polling_interval_seconds": 30
  },
  "status": "success"
}
```

**Field Descriptions:**
- `is_premium` (bool): Premium subscription status
- `basic_stats_enabled` (bool): Free tier stats enabled
- `community_health_enabled` (bool): Premium health scoring
- `bad_actor_detection_enabled` (bool): Premium bot detection
- `user_journey_enabled` (bool): Premium user tracking
- `polling_interval_seconds` (int): Client polling interval

---

### 5. Update Configuration

Modify analytics configuration for a community.

**Endpoint:** `PUT /analytics/{community_id}/config`

**Parameters:**
- `community_id` (path, required): Community identifier

**Request Body:**
```json
{
  "is_premium": true,
  "basic_stats_enabled": true,
  "community_health_enabled": true,
  "bad_actor_detection_enabled": true,
  "user_journey_enabled": true,
  "polling_interval_seconds": 15,
  "raw_data_retention_days": 30,
  "aggregated_data_retention_days": 365
}
```

**Request:**
```bash
curl -X PUT http://localhost:8040/api/v1/analytics/123/config \
  -H "Content-Type: application/json" \
  -d '{
    "is_premium": true,
    "polling_interval_seconds": 15
  }'
```

**Response Schema:**
```json
{
  "data": {
    "community_id": 123,
    "is_premium": true,
    "basic_stats_enabled": true,
    "community_health_enabled": true,
    "bad_actor_detection_enabled": true,
    "user_journey_enabled": true,
    "polling_interval_seconds": 15
  },
  "status": "success"
}
```

---

### 6. Poll for Updates

Real-time update polling endpoint for client applications.

**Endpoint:** `GET /analytics/{community_id}/poll`

**Parameters:**
- `community_id` (path, required): Community identifier
- `since` (query, optional): ISO timestamp of last update

**Request:**
```bash
curl "http://localhost:8040/api/v1/analytics/123/poll?since=2026-02-16T10:00:00Z"
```

**Response Schema:**

```json
{
  "data": {
    "community_id": 123,
    "new_messages": 150,
    "new_viewers": 25,
    "removed_viewers": 10,
    "updates_since": "2026-02-16T10:00:00Z",
    "timestamp": "2026-02-16T10:30:00Z",
    "has_new_data": true
  },
  "status": "success"
}
```

---

## Internal Service Endpoints

### 1. Receive Activity Events

Process activity events from platform modules (service-to-service).

**Endpoint:** `POST /internal/events`

**Headers Required:**
- `X-Service-API-Key`: Service authentication key
- `Content-Type: application/json`

**Request Body Schema:**
```json
{
  "community_id": 123,
  "events": [
    {
      "event_type": "message",
      "platform": "discord",
      "platform_user_id": "user123",
      "timestamp": "2026-02-16T10:30:00Z",
      "metadata": {
        "channel_id": "chan123",
        "message_length": 150,
        "has_media": false
      }
    },
    {
      "event_type": "viewer_join",
      "platform": "twitch",
      "platform_user_id": "twitch456",
      "timestamp": "2026-02-16T10:35:00Z",
      "metadata": {
        "session_id": "sess789",
        "country": "US"
      }
    },
    {
      "event_type": "viewer_leave",
      "platform": "twitch",
      "platform_user_id": "twitch456",
      "timestamp": "2026-02-16T11:00:00Z",
      "metadata": {
        "session_id": "sess789",
        "duration_seconds": 1500
      }
    }
  ]
}
```

**Event Type Descriptions:**
- `message`: User sent a message/chat
- `viewer_join`: User started watching/listening
- `viewer_leave`: User stopped watching/listening
- `reaction`: User reacted to content
- `moderation`: Moderation action taken

**Request:**
```bash
curl -X POST http://localhost:8040/api/v1/internal/events \
  -H "Content-Type: application/json" \
  -H "X-Service-API-Key: your-key" \
  -d '{
    "community_id": 123,
    "events": [
      {
        "event_type": "message",
        "platform": "discord",
        "platform_user_id": "user123",
        "timestamp": "2026-02-16T10:30:00Z",
        "metadata": {}
      }
    ]
  }'
```

**Response Schema:**
```json
{
  "data": {
    "processed": 3,
    "status": "success"
  },
  "status": "success"
}
```

**Field Descriptions:**
- `processed` (int): Number of events successfully processed

---

### 2. Trigger Aggregation

Manually trigger metrics aggregation.

**Endpoint:** `POST /internal/aggregate`

**Headers Required:**
- `X-Service-API-Key`: Service authentication key
- `Content-Type: application/json`

**Request Body Schema:**
```json
{
  "community_id": 123,
  "force": false
}
```

**Parameters:**
- `community_id` (optional): Specific community, all if omitted
- `force` (optional, default: false): Force aggregation even if recent

**Request:**
```bash
# Aggregate all communities
curl -X POST http://localhost:8040/api/v1/internal/aggregate \
  -H "Content-Type: application/json" \
  -H "X-Service-API-Key: your-key" \
  -d '{}'

# Aggregate specific community
curl -X POST http://localhost:8040/api/v1/internal/aggregate \
  -H "Content-Type: application/json" \
  -H "X-Service-API-Key: your-key" \
  -d '{
    "community_id": 123,
    "force": true
  }'
```

**Response Schema:**
```json
{
  "data": {
    "status": "queued",
    "community_id": 123,
    "timestamp": "2026-02-16T10:30:00Z"
  },
  "status": "success"
}
```

---

## Bot Detection Endpoints

### 1. Get Bot Score

Retrieve bot detection score for a community.

**Endpoint:** `GET /analytics/{community_id}/bot-score`

**Parameters:**
- `community_id` (path, required): Community identifier

**Request:**
```bash
curl http://localhost:8040/api/v1/analytics/123/bot-score
```

**Response Schema:**

```json
{
  "data": {
    "community_id": 123,
    "overall_score": 85,
    "grade": "B",
    "size_category": "medium",
    "component_scores": {
      "bad_actor_score": 90,
      "reputation_score": 80,
      "security_score": 88,
      "ai_behavioral_score": 82
    },
    "component_weights": {
      "bad_actor": 0.30,
      "reputation": 0.25,
      "security": 0.20,
      "ai_behavioral": 0.25
    },
    "calculated_at": "2026-02-16T09:00:00Z",
    "next_recalculation": "2026-02-17T09:00:00Z",
    "cached": true
  },
  "status": "success"
}
```

**Score Interpretation:**
- `overall_score`: 0-100 composite score
- `grade`: A (90+), B (80-89), C (70-79), D (60-69), F (<60)
- `size_category`: small (<50 members), medium (50-500), large (>500)
- `cached`: true if score was loaded from cache

**Component Scores:**
- `bad_actor_score`: Bad actor percentage score (100 = clean)
- `reputation_score`: Community health and engagement
- `security_score`: Content filter violations
- `ai_behavioral_score`: Pattern anomaly detection

---

### 2. Calculate Bot Score

Force immediate bot score recalculation.

**Endpoint:** `POST /analytics/{community_id}/bot-score/calculate`

**Parameters:**
- `community_id` (path, required): Community identifier

**Request:**
```bash
curl -X POST http://localhost:8040/api/v1/analytics/123/bot-score/calculate
```

**Response Schema:** Same as Get Bot Score endpoint

---

### 3. Get Suspected Bots

Retrieve list of suspected bot users (Premium feature).

**Endpoint:** `GET /analytics/{community_id}/suspected-bots`

**Parameters:**
- `community_id` (path, required): Community identifier
- `limit` (query, optional, default: 50): Max results to return
- `min_confidence` (query, optional, default: 50): Minimum confidence score (0-100)

**Request:**
```bash
# Get top 10 suspected bots with 70%+ confidence
curl "http://localhost:8040/api/v1/analytics/123/suspected-bots?limit=10&min_confidence=70"
```

**Response Schema:**

```json
{
  "data": {
    "suspected_bots": [
      {
        "community_id": 123,
        "hub_user_id": 456,
        "platform_user_id": "bot_user_1",
        "platform_username": "automation_bot",
        "confidence_score": 92,
        "bot_indicators": {
          "rapid_posting": true,
          "duplicate_messages": true,
          "unusual_timing": false,
          "account_age_hours": 5
        },
        "detected_patterns": [
          "same message 5x in 2 minutes",
          "100+ messages/hour",
          "messages at 3am"
        ],
        "is_false_positive": false,
        "reviewed_by": null,
        "reviewed_at": null,
        "detected_at": "2026-02-15T15:30:00Z",
        "updated_at": "2026-02-16T10:30:00Z"
      }
    ]
  },
  "status": "success"
}
```

**Field Descriptions:**
- `confidence_score`: 0-100 confidence that user is a bot
- `bot_indicators`: Flags and metrics for detection
- `detected_patterns`: Human-readable pattern descriptions
- `is_false_positive`: true if marked as incorrect detection
- `reviewed_by`: User ID of reviewer (if reviewed)
- `reviewed_at`: Timestamp of review (if reviewed)

---

### 4. Review Suspected Bot

Mark a suspected bot as reviewed (false positive or confirmed).

**Endpoint:** `PUT /analytics/{community_id}/suspected-bots/{bot_id}/review`

**Parameters:**
- `community_id` (path, required): Community identifier
- `bot_id` (path, required): Suspected bot ID

**Headers Required:**
- `X-User-ID`: Reviewer's user ID
- `Content-Type: application/json`

**Request Body:**
```json
{
  "is_false_positive": true
}
```

**Request:**
```bash
curl -X PUT http://localhost:8040/api/v1/analytics/123/suspected-bots/456/review \
  -H "Content-Type: application/json" \
  -H "X-User-ID: moderator_id" \
  -d '{
    "is_false_positive": true
  }'
```

**Response Schema:**

```json
{
  "data": {
    "community_id": 123,
    "hub_user_id": 456,
    "platform_user_id": "bot_user_1",
    "platform_username": "automation_bot",
    "confidence_score": 92,
    "bot_indicators": { ... },
    "detected_patterns": [ ... ],
    "is_false_positive": true,
    "reviewed_by": "moderator_id",
    "reviewed_at": "2026-02-16T10:30:00Z",
    "detected_at": "2026-02-15T15:30:00Z",
    "updated_at": "2026-02-16T10:30:00Z"
  },
  "status": "success"
}
```

---

## Response Formats

### Success Response

All successful responses follow this format:

```json
{
  "data": { /* response data */ },
  "status": "success"
}
```

### Error Response

All error responses follow this format:

```json
{
  "error": "Error message describing the issue",
  "status": "error",
  "code": "ERROR_CODE"
}
```

---

## Error Codes

| HTTP Status | Code | Description |
|-------------|------|-------------|
| 200 | OK | Request successful |
| 400 | BAD_REQUEST | Invalid parameters or request body |
| 401 | UNAUTHORIZED | Missing or invalid authentication |
| 403 | FORBIDDEN | Insufficient permissions (e.g., premium-only feature) |
| 404 | NOT_FOUND | Community or resource not found |
| 500 | INTERNAL_ERROR | Server error |
| 503 | SERVICE_UNAVAILABLE | Database or dependency unavailable |

**Example Error Response:**
```json
{
  "error": "Community 999 not found",
  "status": "error",
  "code": "NOT_FOUND"
}
```

---

## Rate Limiting

Currently no rate limiting is implemented, but it's recommended to add:

- **Public endpoints**: 100 requests/minute per user
- **Internal endpoints**: 1000 requests/minute per service
- **Bot detection**: 10 recalculations/hour per community

---

## Next Steps

- Read [USAGE.md](USAGE.md) for practical usage examples
- Read [ARCHITECTURE.md](ARCHITECTURE.md) for system design
- Read [CONFIGURATION.md](CONFIGURATION.md) for configuration options

---

**Last Updated:** 2026-02-16
**Maintained By:** Penguin Tech Inc
