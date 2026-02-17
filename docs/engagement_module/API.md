# Engagement Module — API Reference

## Base URL

```
http://localhost:8091/api/v1
```

## Authentication

All endpoints except `/health` require JWT authentication via `Authorization` header:

```
Authorization: Bearer <JWT_TOKEN>
```

## Response Format

All responses are JSON with consistent structure:

**Success (2xx)**:
```json
{
  "success": true,
  "data": { ... }
}
```

**Error (4xx/5xx)**:
```json
{
  "error": "Error message describing what went wrong"
}
```

---

## Health Check

### GET /health

Health check endpoint for monitoring and load balancer health probes.

**Authentication**: Not required

**Parameters**: None

**Response (200)**:
```json
{
  "status": "healthy",
  "module": "engagement_module",
  "version": "1.0.0",
  "timestamp": "2026-02-16T10:30:45.123456"
}
```

**Response (503)**:
```json
{
  "status": "unhealthy",
  "error": "Connection refused"
}
```

---

## Polls API

### POST /polls

Create a new poll in a community.

**Authentication**: Required (Bearer token)

**Request Body**:
```json
{
  "community_id": 1,
  "title": "string (max 255 chars, required)",
  "description": "string (optional)",
  "options": ["option1", "option2", "option3"],
  "view_visibility": "community|public|registered|admins",
  "submit_visibility": "community|public|registered|admins",
  "allow_multiple_choices": false,
  "max_choices": 1,
  "expires_at": "2026-02-28T23:59:59Z"
}
```

**Validation Rules**:
- `community_id`: Required, must be positive integer
- `title`: Required, 1-255 characters
- `options`: Required, minimum 2 options
- `max_choices`: Only applies if `allow_multiple_choices` is true
- `expires_at`: Optional ISO 8601 datetime string

**Response (201)**:
```json
{
  "success": true,
  "poll": {
    "id": 42,
    "community_id": 1,
    "title": "What is your favorite language?",
    "description": "string|null",
    "options": [
      {"id": 1, "text": "Python"},
      {"id": 2, "text": "JavaScript"}
    ],
    "view_visibility": "community",
    "submit_visibility": "community",
    "allow_multiple_choices": false,
    "max_choices": 1,
    "expires_at": "2026-02-28T23:59:59",
    "is_active": true,
    "created_at": "2026-02-16T10:30:45"
  }
}
```

**Error Responses**:
- `400`: Missing required fields or validation failed
- `401`: Invalid or missing authentication token
- `500`: Server error

---

### GET /polls/:poll_id

Retrieve poll details with vote counts.

**Authentication**: Not required (respects visibility)

**Path Parameters**:
- `poll_id` (integer): The poll ID

**Query Parameters**: None

**Response (200)**:
```json
{
  "success": true,
  "poll": {
    "id": 42,
    "community_id": 1,
    "title": "What is your favorite language?",
    "description": "string|null",
    "options": [
      {"id": 1, "text": "Python"},
      {"id": 2, "text": "JavaScript"}
    ],
    "vote_counts": {
      "1": 25,
      "2": 18
    },
    "view_visibility": "community",
    "submit_visibility": "community",
    "allow_multiple_choices": false,
    "max_choices": 1,
    "expires_at": "2026-02-28T23:59:59",
    "is_active": true,
    "created_at": "2026-02-16T10:30:45"
  }
}
```

**Error Responses**:
- `404`: Poll not found
- `500`: Server error

---

### GET /polls/community/:community_id

List all active polls for a community.

**Authentication**: Not required (respects visibility)

**Path Parameters**:
- `community_id` (integer): The community ID

**Query Parameters**: None

**Response (200)**:
```json
{
  "success": true,
  "count": 3,
  "polls": [
    {
      "id": 42,
      "community_id": 1,
      "title": "What is your favorite language?",
      "view_visibility": "community",
      "created_at": "2026-02-16T10:30:45"
    }
  ]
}
```

**Error Responses**:
- `500`: Server error

---

### POST /polls/:poll_id/vote

Record a vote in a poll.

**Authentication**: Required (Bearer token)

**Path Parameters**:
- `poll_id` (integer): The poll ID

**Request Body**:
```json
{
  "option_ids": [1]
}
```

**Validation Rules**:
- `option_ids`: Array of option IDs (required)
- Must have at least 1 option
- Cannot exceed `max_choices` if multiple choices enabled
- User cannot vote twice on same poll
- Poll must be active and not expired

**Response (200)**:
```json
{
  "success": true,
  "message": "Vote recorded"
}
```

**Error Responses**:
- `400`: Poll expired, invalid choices, or validation failed
- `401`: Invalid or missing authentication token
- `404`: Poll or option not found
- `409`: User already voted on this poll
- `500`: Server error

---

## Forms API

### POST /forms

Create a new form in a community.

**Authentication**: Required (Bearer token)

**Request Body**:
```json
{
  "community_id": 1,
  "title": "string (max 255 chars, required)",
  "description": "string (optional)",
  "fields": [
    {
      "type": "text|textarea|email|number|select|radio|checkbox|date",
      "label": "string (required)",
      "placeholder": "string (optional)",
      "required": false,
      "options": ["opt1", "opt2"],
      "validation": {
        "min": 5,
        "max": 100,
        "pattern": "^[a-zA-Z]+$"
      }
    }
  ],
  "view_visibility": "community|public|registered|admins",
  "submit_visibility": "community|public|registered|admins",
  "allow_anonymous": false,
  "submit_once_per_user": true
}
```

**Field Types**:
- `text`: Single line text (supports min/max length)
- `textarea`: Multi-line text
- `email`: Email with validation
- `number`: Numeric input (supports min/max)
- `select`: Dropdown list (requires `options`)
- `radio`: Radio button group (requires `options`)
- `checkbox`: Checkbox group (requires `options`)
- `date`: Date picker

**Validation Rules**:
- `community_id`: Required, positive integer
- `title`: Required, 1-255 characters
- Fields: At least 0 fields allowed
- Field types: Must be from allowed list

**Response (201)**:
```json
{
  "success": true,
  "form": {
    "id": 12,
    "community_id": 1,
    "title": "Community Feedback",
    "description": "string|null",
    "view_visibility": "community",
    "submit_visibility": "community",
    "allow_anonymous": false,
    "submit_once_per_user": true,
    "is_active": true,
    "created_at": "2026-02-16T10:30:45"
  }
}
```

**Error Responses**:
- `400`: Missing required fields or validation failed
- `401`: Invalid or missing authentication token
- `500`: Server error

---

### GET /forms/:form_id

Retrieve form details with all fields.

**Authentication**: Not required (respects visibility)

**Path Parameters**:
- `form_id` (integer): The form ID

**Response (200)**:
```json
{
  "success": true,
  "form": {
    "id": 12,
    "community_id": 1,
    "title": "Community Feedback",
    "description": "string|null",
    "fields": [
      {
        "id": 1,
        "type": "text",
        "label": "Name",
        "placeholder": "Your full name",
        "required": true,
        "options": null,
        "validation": null
      },
      {
        "id": 2,
        "type": "email",
        "label": "Email",
        "placeholder": null,
        "required": true,
        "options": null,
        "validation": null
      }
    ],
    "view_visibility": "community",
    "submit_visibility": "community",
    "allow_anonymous": false,
    "submit_once_per_user": true,
    "is_active": true,
    "created_at": "2026-02-16T10:30:45"
  }
}
```

**Error Responses**:
- `404`: Form not found
- `500`: Server error

---

### GET /forms/community/:community_id

List all active forms for a community.

**Authentication**: Not required (respects visibility)

**Path Parameters**:
- `community_id` (integer): The community ID

**Response (200)**:
```json
{
  "success": true,
  "count": 2,
  "forms": [
    {
      "id": 12,
      "community_id": 1,
      "title": "Community Feedback",
      "view_visibility": "community",
      "created_at": "2026-02-16T10:30:45"
    }
  ]
}
```

**Error Responses**:
- `500`: Server error

---

### POST /forms/:form_id/submit

Submit a completed form.

**Authentication**: Required (Bearer token) unless `allow_anonymous` is true

**Path Parameters**:
- `form_id` (integer): The form ID

**Request Body**:
```json
{
  "values": {
    "1": "Jane Doe",
    "2": "jane@example.com",
    "3": "Great community",
    "4": ["option1", "option2"]
  }
}
```

**Validation Rules**:
- `values`: Key-value pairs where keys are field IDs (as strings)
- Required fields must be present
- Field values undergo type and format validation
- If `submit_once_per_user` is true, user can only submit once
- Form must be active

**Response (201)**:
```json
{
  "success": true,
  "submission_id": 95
}
```

**Error Responses**:
- `400`: Validation failed or form inactive
- `401`: Invalid or missing authentication token
- `404`: Form not found
- `409`: User already submitted this form
- `500`: Server error

---

### GET /forms/:form_id/submissions

Retrieve all submissions for a form (admin only).

**Authentication**: Required (Bearer token)

**Path Parameters**:
- `form_id` (integer): The form ID

**Response (200)**:
```json
{
  "success": true,
  "count": 42,
  "submissions": [
    {
      "id": 95,
      "user_id": 128,
      "submitted_at": "2026-02-16T14:22:15",
      "values": {
        "1": "Jane Doe",
        "2": "jane@example.com",
        "3": "Great community",
        "4": "Very satisfied"
      }
    },
    {
      "id": 94,
      "user_id": 127,
      "submitted_at": "2026-02-16T12:08:43",
      "values": {
        "1": "John Smith",
        "2": "john@example.com",
        "3": "Good feedback",
        "4": "Satisfied"
      }
    }
  ]
}
```

**Error Responses**:
- `401`: Invalid or missing authentication token
- `404`: Form not found
- `500`: Server error

---

## Visibility Model

Both polls and forms support four visibility levels with separate `view_visibility` and `submit_visibility`:

| Level | View | Vote/Submit | Description |
|-------|------|-------------|-------------|
| `public` | Anyone | Anyone | Completely open |
| `registered` | Any logged-in user | Any logged-in user | Login required |
| `community` | Community members | Community members | Community membership required |
| `admins` | Admins only | Admins only | Administrators only |

---

## Error Codes

| Code | Description |
|------|-------------|
| 200 | Successful GET or POST response |
| 201 | Successful resource creation |
| 400 | Bad request (missing fields, validation failed) |
| 401 | Unauthorized (missing or invalid token) |
| 404 | Resource not found |
| 409 | Conflict (e.g., duplicate vote or submission) |
| 500 | Internal server error |
| 503 | Service unavailable (database down) |

---

## Rate Limiting

Currently unlimited. Implement rate limiting at API gateway if needed.

---

## Pagination

Not implemented. List endpoints return all results. Add limit/offset parameters if needed.

---

## Next Steps

- See [CONFIGURATION.md](CONFIGURATION.md) for environment setup
- See [USAGE.md](USAGE.md) for practical examples
- See [ARCHITECTURE.md](ARCHITECTURE.md) for system design details

**Company**: Penguin Tech Inc
**License**: Limited AGPL-3.0
**Last Updated**: 2026-02-16
