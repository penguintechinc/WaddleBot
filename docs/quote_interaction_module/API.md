# Quote Interaction Module - API Reference

## API Overview

The Quote Interaction Module provides RESTful endpoints for managing community quotes. All endpoints use JSON for request/response bodies and support pagination where applicable.

**Base URL:** `http://localhost:5012/api/v1`  
**Version:** 1.0.0  
**Authentication:** Inherited from WaddleBot platform (JWT via Authorization header)

## Status & Health Endpoints

### Get Module Status

```http
GET /api/v1/status HTTP/1.1
Host: localhost:5012
```

**Response (200 OK):**
```json
{
  "status": "operational",
  "module": "quote_interaction_module",
  "version": "1.0.0"
}
```

### Health Check

```http
GET /health HTTP/1.1
Host: localhost:5012
```

**Response (200 OK):**
```json
{
  "status": "healthy",
  "module": "quote_interaction_module",
  "version": "1.0.0",
  "timestamp": "2026-02-16T10:30:45.123Z"
}
```

### Prometheus Metrics

```http
GET /metrics HTTP/1.1
Host: localhost:5012
```

**Response (200 OK):** Prometheus-format metrics including request counts, response times, and connection pool statistics.

## Quote Management Endpoints

### Create Quote

Creates a new quote in a community. Quotes can be auto-approved or require manual review based on configuration.

```http
POST /api/v1/quotes HTTP/1.1
Host: localhost:5012
Content-Type: application/json

{
  "community_id": 42,
  "text": "The only way to do great work is to love what you do",
  "author": "Steve Jobs",
  "added_by_user_id": 123,
  "quoted_user_id": 456,
  "platform": "twitch",
  "context": "Said during community call",
  "tags": ["leadership", "inspiration"],
  "is_approved": false
}
```

**Request Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| community_id | integer | YES | ID of the community |
| text | string | YES | The quote text |
| author | string | NO | Author name |
| added_by_user_id | integer | NO | User ID who submitted the quote |
| quoted_user_id | integer | NO | User ID being quoted |
| platform | string | NO | Origin platform (e.g., "twitch", "discord") |
| context | string | NO | Additional context about the quote |
| tags | array[string] | NO | Categorization tags |
| is_approved | boolean | NO | Approval status (default: AUTO_APPROVE_QUOTES config) |

**Response (201 Created):**
```json
{
  "id": 1,
  "community_id": 42,
  "quote_text": "The only way to do great work is to love what you do",
  "author": "Steve Jobs",
  "added_by_user_id": 123,
  "created_at": "2026-02-16T10:30:45Z",
  "updated_at": "2026-02-16T10:30:45Z"
}
```

**Error Responses:**
- `400 Bad Request` - Missing required fields (community_id, text)
- `500 Internal Server Error` - Database insertion error

---

### Get Quote by ID

Retrieves a specific quote by its ID.

```http
GET /api/v1/quotes/1 HTTP/1.1
Host: localhost:5012
```

**Response (200 OK):**
```json
{
  "id": 1,
  "community_id": 42,
  "quote_text": "The only way to do great work is to love what you do",
  "quoted_user_id": 456,
  "quoted_username": "Steve Jobs",
  "added_by_user_id": 123,
  "platform": "twitch",
  "context": "Said during community call",
  "tags": ["leadership", "inspiration"],
  "is_approved": true,
  "created_at": "2026-02-16T10:30:45Z",
  "updated_at": "2026-02-16T10:30:45Z",
  "deleted_at": null
}
```

**Error Responses:**
- `404 Not Found` - Quote ID does not exist or has been deleted
- `500 Internal Server Error` - Database query error

---

### Get Random Quote

Retrieves a random approved quote from a community.

```http
GET /api/v1/quotes/random/42 HTTP/1.1
Host: localhost:5012
```

**Response (200 OK):**
```json
{
  "id": 1,
  "community_id": 42,
  "quote_text": "The only way to do great work is to love what you do",
  "quoted_user_id": 456,
  "quoted_username": "Steve Jobs",
  "added_by_user_id": 123,
  "platform": "twitch",
  "context": "Said during community call",
  "tags": ["leadership", "inspiration"],
  "is_approved": true,
  "created_at": "2026-02-16T10:30:45Z"
}
```

**Error Responses:**
- `404 Not Found` - No approved quotes available for the community
- `500 Internal Server Error` - Database query error

---

### List Quotes with Pagination

Retrieves paginated list of quotes for a community.

```http
GET /api/v1/quotes/list/42?limit=20&offset=0&approved=true HTTP/1.1
Host: localhost:5012
```

**Query Parameters:**

| Parameter | Type | Default | Max | Description |
|-----------|------|---------|-----|-------------|
| limit | integer | 50 | 100 | Results per page |
| offset | integer | 0 | - | Pagination offset |
| approved | boolean | true | - | Filter to approved quotes only |

**Response (200 OK):**
```json
{
  "quotes": [
    {
      "id": 1,
      "community_id": 42,
      "quote_text": "The only way to do great work is to love what you do",
      "quoted_username": "Steve Jobs",
      "added_by_user_id": 123,
      "is_approved": true,
      "created_at": "2026-02-16T10:30:45Z"
    }
  ],
  "pagination": {
    "limit": 20,
    "offset": 0,
    "total": 150,
    "has_more": true
  }
}
```

**Error Responses:**
- `400 Bad Request` - Invalid limit or offset values
- `500 Internal Server Error` - Database query error

---

### Search Quotes (Full-Text)

Performs full-text search on quote text using PostgreSQL tsvector. Supports natural language queries with ranking.

```http
GET /api/v1/quotes/search/42?q=work&limit=10&offset=0 HTTP/1.1
Host: localhost:5012
```

**Query Parameters:**

| Parameter | Type | Default | Min | Description |
|-----------|------|---------|-----|-------------|
| q | string | - | 2 chars | Search query (case-insensitive) |
| limit | integer | 50 | - | Results per page |
| offset | integer | 0 | - | Pagination offset |

**Response (200 OK):**
```json
{
  "query": "work",
  "quotes": [
    {
      "id": 1,
      "community_id": 42,
      "quote_text": "The only way to do great work is to love what you do",
      "quoted_username": "Steve Jobs",
      "is_approved": true,
      "created_at": "2026-02-16T10:30:45Z"
    }
  ],
  "pagination": {
    "limit": 10,
    "offset": 0,
    "total": 42,
    "has_more": false
  }
}
```

**Error Responses:**
- `400 Bad Request` - Search query less than 2 characters
- `500 Internal Server Error` - Database search error

---

### Get Quotes by Author

Filters quotes by author name using case-insensitive pattern matching.

```http
GET /api/v1/quotes/author/42?author=Jobs&limit=25&offset=0 HTTP/1.1
Host: localhost:5012
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| author | string | - | Author name to search (partial match) |
| limit | integer | 50 | Results per page |
| offset | integer | 0 | Pagination offset |

**Response (200 OK):**
```json
{
  "author": "Jobs",
  "quotes": [
    {
      "id": 1,
      "community_id": 42,
      "quote_text": "The only way to do great work is to love what you do",
      "quoted_username": "Steve Jobs",
      "created_at": "2026-02-16T10:30:45Z"
    },
    {
      "id": 2,
      "community_id": 42,
      "quote_text": "Innovation distinguishes a leader from a follower",
      "quoted_username": "Steve Jobs",
      "created_at": "2026-02-16T10:31:15Z"
    }
  ],
  "pagination": {
    "limit": 25,
    "offset": 0,
    "total": 5,
    "has_more": false
  }
}
```

**Error Responses:**
- `400 Bad Request` - Missing author parameter
- `500 Internal Server Error` - Database query error

---

### Update Quote

Updates specific fields of an existing quote.

```http
PUT /api/v1/quotes/1 HTTP/1.1
Host: localhost:5012
Content-Type: application/json

{
  "text": "The only way to do great work is to love what you do (revised)",
  "author": "Steve Jobs",
  "context": "Updated context",
  "tags": ["leadership", "innovation"],
  "is_approved": true,
  "platform": "discord"
}
```

**Request Fields (all optional):**

| Field | Type | Description |
|-------|------|-------------|
| text | string | Updated quote text |
| author | string | Updated author name |
| context | string | Updated context |
| tags | array[string] | Updated tags |
| is_approved | boolean | Updated approval status |
| platform | string | Updated platform origin |

**Response (200 OK):**
```json
{
  "id": 1,
  "message": "Quote updated successfully"
}
```

**Error Responses:**
- `404 Not Found` - Quote does not exist or is deleted
- `500 Internal Server Error` - Database update error

---

### Delete Quote (Soft-Delete)

Soft-deletes a quote by setting the deleted_at timestamp. Quote data is preserved for audit purposes.

```http
DELETE /api/v1/quotes/1 HTTP/1.1
Host: localhost:5012
```

**Response (200 OK):**
```json
{
  "id": 1,
  "message": "Quote deleted successfully"
}
```

**Error Responses:**
- `404 Not Found` - Quote does not exist or is already deleted
- `500 Internal Server Error` - Database delete error

---

## Statistics Endpoint

### Get Quote Statistics

Returns aggregated statistics about quotes in a community.

```http
GET /api/v1/quotes/stats/42 HTTP/1.1
Host: localhost:5012
```

**Response (200 OK):**
```json
{
  "total_quotes": 150,
  "approved_quotes": 145,
  "pending_quotes": 5,
  "unique_authors": 87,
  "latest_quote_date": "2026-02-16T10:30:45Z"
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| total_quotes | integer | Total number of quotes (excluding deleted) |
| approved_quotes | integer | Number of approved quotes |
| pending_quotes | integer | Number of pending approval quotes |
| unique_authors | integer | Count of distinct authors |
| latest_quote_date | string (ISO 8601) | Most recent quote creation date |

**Error Responses:**
- `500 Internal Server Error` - Database query error

---

## Error Response Format

All error responses follow this standard format:

```json
{
  "status": "error",
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message"
  },
  "meta": {
    "timestamp": "2026-02-16T10:30:45Z",
    "request_id": "abc123def456"
  }
}
```

**Common Error Codes:**
- `VALIDATION_ERROR` - Input validation failed
- `NOT_FOUND` - Resource not found
- `DATABASE_ERROR` - Database operation failed
- `INTERNAL_ERROR` - Unexpected server error

## Rate Limiting

Rate limiting is handled at the platform level (API gateway). Check platform documentation for limits.

## CORS Headers

CORS headers are inherited from the WaddleBot platform configuration.

## Authentication

Authentication is inherited from WaddleBot platform via JWT in Authorization header:

```http
Authorization: Bearer <JWT_TOKEN>
```
