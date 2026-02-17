# Memories Interaction Module - API Reference

## API Base URL

```
http://localhost:8031/api/v1/memories
```

## Status Endpoint

### GET /status

Get module operational status.

**Request**:
```bash
curl http://localhost:8031/api/v1/memories/status
```

**Response** (200):
```json
{
  "success": true,
  "data": {
    "status": "operational",
    "module": "memories_interaction_module",
    "version": "2.0.0"
  }
}
```

---

## Quotes Endpoints

### POST /quotes

Create a new quote.

**Request**:
```bash
curl -X POST http://localhost:8031/api/v1/memories/quotes \
  -H "Content-Type: application/json" \
  -d '{
    "community_id": 1,
    "quote_text": "Amazing quote here",
    "created_by_username": "alice",
    "created_by_user_id": 101,
    "author_username": "quoted_user",
    "author_user_id": 102,
    "category": "funny"
  }'
```

**Request Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| community_id | integer | ✓ | Community ID (positive) |
| quote_text | string | ✓ | Quote text (1-5000 chars) |
| created_by_username | string | ✓ | Creator username |
| created_by_user_id | integer | - | Creator user ID |
| author_username | string | - | Quoted person username |
| author_user_id | integer | - | Quoted person user ID |
| category | string | - | Quote category (max 100 chars) |

**Response** (200):
```json
{
  "success": true,
  "data": {
    "id": 1,
    "quote_text": "Amazing quote here",
    "author_username": "quoted_user",
    "category": "funny",
    "votes": 0
  }
}
```

**Errors**:
- 400: Invalid input (missing fields, validation error)
- 500: Database error

---

### GET /quotes/<community_id>

Search quotes with full-text search and filters.

**Request**:
```bash
curl "http://localhost:8031/api/v1/memories/quotes/1?q=innovation&category=tech&author=stevejobs&limit=10&offset=0"
```

**Query Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| q | string | - | Full-text search query |
| category | string | - | Filter by category |
| author | string | - | Filter by author username |
| limit | integer | 50 | Results per page (1-100) |
| offset | integer | 0 | Pagination offset |

**Response** (200):
```json
{
  "success": true,
  "data": {
    "quotes": [
      {
        "id": 1,
        "quote_text": "Innovation distinguishes...",
        "author_username": "stevejobs",
        "category": "tech",
        "created_by_username": "alice",
        "votes": 5,
        "created_at": "2026-02-16T10:00:00Z"
      }
    ],
    "count": 1
  }
}
```

---

### GET /quotes/<community_id>/random

Get random quote from community.

**Request**:
```bash
curl http://localhost:8031/api/v1/memories/quotes/1/random
```

**Response** (200):
```json
{
  "success": true,
  "data": {
    "id": 1,
    "quote_text": "Random quote...",
    "author_username": "user",
    "votes": 3,
    "created_at": "2026-02-16T10:00:00Z"
  }
}
```

**Errors**:
- 404: No quotes found in community

---

### GET /quotes/<community_id>/<quote_id>

Get specific quote by ID.

**Request**:
```bash
curl http://localhost:8031/api/v1/memories/quotes/1/5
```

**Response** (200):
```json
{
  "success": true,
  "data": {
    "id": 5,
    "quote_text": "...",
    "author_username": "...",
    "votes": 10,
    "created_at": "2026-02-16T10:00:00Z"
  }
}
```

**Errors**:
- 404: Quote not found

---

### DELETE /quotes/<community_id>/<quote_id>

Delete a quote (must be creator).

**Request**:
```bash
curl -X DELETE http://localhost:8031/api/v1/memories/quotes/1/5 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{"user_id": 101}'
```

**Response** (200):
```json
{
  "success": true,
  "data": {"message": "Quote deleted"}
}
```

**Errors**:
- 403: Unauthorized (not creator)
- 404: Quote not found

---

### POST /quotes/<community_id>/<quote_id>/vote

Vote on a quote (upvote/downvote).

**Request**:
```bash
curl -X POST http://localhost:8031/api/v1/memories/quotes/1/5/vote \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 102,
    "username": "bob",
    "vote_type": "up"
  }'
```

**Request Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| user_id | integer | ✓ | Voting user ID |
| username | string | ✓ | Voting username |
| vote_type | string | ✓ | "up", "down", "upvote", "downvote" |

**Response** (200):
```json
{
  "success": true,
  "data": {
    "quote_id": 5,
    "votes": 6,
    "upvotes": 6,
    "downvotes": 0
  }
}
```

---

### GET /quotes/<community_id>/categories

Get all quote categories in community.

**Request**:
```bash
curl http://localhost:8031/api/v1/memories/quotes/1/categories
```

**Response** (200):
```json
{
  "success": true,
  "data": {
    "categories": ["funny", "inspirational", "technical"]
  }
}
```

---

### GET /quotes/<community_id>/stats

Get quote statistics.

**Request**:
```bash
curl http://localhost:8031/api/v1/memories/quotes/1/stats
```

**Response** (200):
```json
{
  "success": true,
  "data": {
    "total_quotes": 150,
    "unique_authors": 42,
    "categories": 8,
    "latest_quote": "2026-02-16T10:00:00Z",
    "avg_votes": 2.5
  }
}
```

---

## Bookmarks Endpoints

### POST /bookmarks

Create a new bookmark.

**Request**:
```bash
curl -X POST http://localhost:8031/api/v1/memories/bookmarks \
  -H "Content-Type: application/json" \
  -d '{
    "community_id": 1,
    "url": "https://example.com/guide",
    "created_by_username": "alice",
    "created_by_user_id": 101,
    "title": "Example Guide",
    "description": "A helpful guide",
    "tags": ["guide", "tutorial"],
    "auto_fetch_metadata": true
  }'
```

**Request Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| community_id | integer | ✓ | Community ID |
| url | string | ✓ | URL to bookmark |
| created_by_username | string | ✓ | Creator username |
| created_by_user_id | integer | - | Creator user ID |
| title | string | - | Custom title (auto-fetched if not provided) |
| description | string | - | Description (auto-fetched if not provided) |
| tags | array | - | List of tags (max 100 chars each) |
| auto_fetch_metadata | boolean | true | Auto-fetch title/description |

**Response** (200):
```json
{
  "success": true,
  "data": {
    "id": 1,
    "url": "https://example.com/guide",
    "title": "Example Guide",
    "description": "A helpful guide",
    "tags": ["guide", "tutorial"],
    "visits": 0
  }
}
```

---

### GET /bookmarks/<community_id>

Search bookmarks.

**Request**:
```bash
curl "http://localhost:8031/api/v1/memories/bookmarks/1?q=guide&tags=tutorial&limit=10"
```

**Query Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| q | string | - | Full-text search query |
| tags | array | - | Filter by tags |
| created_by | string | - | Filter by creator |
| limit | integer | 50 | Results per page (1-100) |
| offset | integer | 0 | Pagination offset |

**Response** (200):
```json
{
  "success": true,
  "data": {
    "bookmarks": [
      {
        "id": 1,
        "url": "https://example.com/guide",
        "title": "Example Guide",
        "description": "A helpful guide",
        "tags": ["guide", "tutorial"],
        "created_by_username": "alice",
        "visits": 5,
        "created_at": "2026-02-16T10:00:00Z"
      }
    ],
    "count": 1
  }
}
```

---

### GET /bookmarks/<community_id>/<bookmark_id>

Get bookmark and increment visit count.

**Request**:
```bash
curl http://localhost:8031/api/v1/memories/bookmarks/1/5
```

**Response** (200):
```json
{
  "success": true,
  "data": {
    "id": 5,
    "url": "https://example.com",
    "title": "...",
    "visits": 6
  }
}
```

---

### DELETE /bookmarks/<community_id>/<bookmark_id>

Delete a bookmark (must be creator).

**Request**:
```bash
curl -X DELETE http://localhost:8031/api/v1/memories/bookmarks/1/5 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{"user_id": 101}'
```

---

### GET /bookmarks/<community_id>/popular

Get most-visited bookmarks.

**Request**:
```bash
curl "http://localhost:8031/api/v1/memories/bookmarks/1/popular?limit=5"
```

**Response** (200):
```json
{
  "success": true,
  "data": {
    "bookmarks": [
      {
        "id": 1,
        "url": "https://example.com",
        "title": "Most Visited",
        "visits": 100
      }
    ]
  }
}
```

---

### GET /bookmarks/<community_id>/tags

Get all tags used in community.

**Request**:
```bash
curl http://localhost:8031/api/v1/memories/bookmarks/1/tags
```

**Response** (200):
```json
{
  "success": true,
  "data": {
    "tags": ["guide", "tutorial", "reference"]
  }
}
```

---

### GET /bookmarks/<community_id>/stats

Get bookmark statistics.

**Request**:
```bash
curl http://localhost:8031/api/v1/memories/bookmarks/1/stats
```

**Response** (200):
```json
{
  "success": true,
  "data": {
    "total_bookmarks": 250,
    "contributors": 35,
    "total_visits": 5000,
    "latest_bookmark": "2026-02-16T10:00:00Z"
  }
}
```

---

## Reminders Endpoints

### POST /reminders

Create a reminder.

**Request**:
```bash
curl -X POST http://localhost:8031/api/v1/memories/reminders \
  -H "Content-Type: application/json" \
  -d '{
    "community_id": 1,
    "user_id": 101,
    "username": "alice",
    "reminder_text": "Team standup",
    "remind_in": "2h",
    "channel": "discord",
    "platform_channel_id": "discord_channel_123",
    "recurring_rule": "FREQ=DAILY;BYDAY=MO,TU,WE,TH,FR"
  }'
```

**Request Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| community_id | integer | ✓ | Community ID |
| user_id | integer | ✓ | User to remind |
| username | string | ✓ | Username |
| reminder_text | string | ✓ | Reminder message (1-1000 chars) |
| remind_in | string | ✓ | "5m", "2h", "1d" or ISO timestamp |
| channel | string | - | "twitch", "discord", "slack", "kick" |
| platform_channel_id | string | - | Channel ID on platform |
| recurring_rule | string | - | RRULE format (e.g., "FREQ=DAILY") |

**Response** (200):
```json
{
  "success": true,
  "data": {
    "id": 1,
    "user_id": 101,
    "username": "alice",
    "reminder_text": "Team standup",
    "remind_at": "2026-02-16T12:00:00Z",
    "is_recurring": true,
    "channel": "discord"
  }
}
```

---

### GET /reminders/pending

Get pending reminders for processor.

**Request**:
```bash
curl http://localhost:8031/api/v1/memories/reminders/pending
```

**Response** (200):
```json
{
  "success": true,
  "data": {
    "reminders": [
      {
        "id": 1,
        "community_id": 1,
        "user_id": 101,
        "username": "alice",
        "reminder_text": "Team standup",
        "remind_at": "2026-02-16T10:00:00Z",
        "channel": "discord",
        "platform_channel_id": "discord_123",
        "is_recurring": false
      }
    ],
    "count": 1
  }
}
```

---

### POST /reminders/<reminder_id>/sent

Mark reminder as sent and schedule next for recurring.

**Request**:
```bash
curl -X POST http://localhost:8031/api/v1/memories/reminders/1/sent \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{"schedule_next": true}'
```

**Response** (200):
```json
{
  "success": true,
  "data": {
    "message": "Reminder marked as sent",
    "next_reminder": {
      "id": 2,
      "remind_at": "2026-02-17T10:00:00Z"
    }
  }
}
```

---

### GET /reminders/<community_id>/user/<user_id>

Get user's reminders.

**Request**:
```bash
curl "http://localhost:8031/api/v1/memories/reminders/1/user/101?include_sent=false"
```

**Query Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| include_sent | boolean | false | Include sent reminders |

**Response** (200):
```json
{
  "success": true,
  "data": {
    "reminders": [
      {
        "id": 1,
        "reminder_text": "Team standup",
        "remind_at": "2026-02-16T10:00:00Z",
        "is_recurring": true,
        "is_sent": false,
        "channel": "discord"
      }
    ],
    "count": 1
  }
}
```

---

### DELETE /reminders/<community_id>/<reminder_id>

Cancel a reminder (must be owner).

**Request**:
```bash
curl -X DELETE http://localhost:8031/api/v1/memories/reminders/1/5 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{"user_id": 101}'
```

---

### GET /reminders/<community_id>/stats

Get reminder statistics.

**Request**:
```bash
curl http://localhost:8031/api/v1/memories/reminders/1/stats
```

**Response** (200):
```json
{
  "success": true,
  "data": {
    "pending_reminders": 45,
    "sent_reminders": 320,
    "recurring_reminders": 12,
    "unique_users": 28
  }
}
```

---

## Error Responses

All error responses follow this format:

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable error message",
    "details": {}
  }
}
```

### Common Error Codes

| Code | HTTP | Description |
|------|------|-------------|
| VALIDATION_ERROR | 400 | Invalid input data |
| UNAUTHORIZED | 401 | Missing or invalid authentication |
| FORBIDDEN | 403 | User not authorized for operation |
| NOT_FOUND | 404 | Resource not found |
| INTERNAL_ERROR | 500 | Server error |

---

**Last Updated**: February 16, 2026  
**Module Version**: 2.0.0
