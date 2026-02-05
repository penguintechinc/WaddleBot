# Labels Core Module - API Documentation

## Overview

Universal label management system for Waddles supporting any entity type including users, modules, communities, items, events, memories, playlists, and custom entities.

**Base URL**: `http://localhost:8023/api/v1`

**Version**: 2.0.0

---

## Authentication

All endpoints use standard Waddles authentication headers.

---

## Endpoints

### Label Management

#### List Labels
```http
GET /labels
```

List all labels with optional filtering.

**Query Parameters**:
- `category` (optional): Filter by entity type (user, module, community, etc.)
- `is_system` (optional): Filter by system labels (true/false)
- `search` (optional): Search labels by name

**Response**:
```json
{
  "success": true,
  "data": {
    "labels": [
      {
        "id": 1,
        "name": "Premium",
        "category": "user",
        "description": "Premium subscriber",
        "color": "#6366f1",
        "icon": "star",
        "is_system": true,
        "created_by": "system",
        "created_at": "2025-01-15T12:00:00",
        "is_active": true
      }
    ],
    "total": 1,
    "supported_types": ["user", "module", "community", "entityGroup", "item", "event", "memory", "playlist", "browser_source", "command", "alias"]
  }
}
```

#### Create Label
```http
POST /labels
```

Create a new label definition.

**Request Body**:
```json
{
  "name": "VIP Member",
  "category": "user",
  "description": "VIP community member",
  "color": "#fbbf24",
  "icon": "crown",
  "created_by": "admin_user_123"
}
```

**Response** (201):
```json
{
  "success": true,
  "data": {
    "message": "Label 'VIP Member' created successfully",
    "label_id": 42
  }
}
```

#### Get Label
```http
GET /labels/{label_id}
```

Get specific label by ID.

**Response**:
```json
{
  "success": true,
  "data": {
    "label": {
      "id": 42,
      "name": "VIP Member",
      "category": "user",
      "description": "VIP community member",
      "color": "#fbbf24",
      "icon": "crown",
      "is_system": false,
      "created_by": "admin_user_123",
      "created_at": "2025-01-15T14:30:00",
      "is_active": true
    }
  }
}
```

#### Update Label
```http
PUT /labels/{label_id}
```

Update an existing label (system labels cannot be modified).

**Request Body**:
```json
{
  "name": "VIP Member Plus",
  "description": "Enhanced VIP member",
  "color": "#f59e0b",
  "icon": "star"
}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "message": "Label updated successfully"
  }
}
```

#### Delete Label
```http
DELETE /labels/{label_id}
```

Soft delete a label and all its assignments.

**Response**:
```json
{
  "success": true,
  "data": {
    "message": "Label deleted successfully"
  }
}
```

### Label Assignment

#### Apply Label
```http
POST /labels/apply
```

Apply a label to an entity. Supports single or bulk operations.

**Single Application**:
```json
{
  "entity_id": "user_12345",
  "entity_type": "user",
  "label_id": 42,
  "applied_by": "moderator_789",
  "community_id": "community_456",
  "expires_at": "2025-12-31T23:59:59Z",
  "metadata": {
    "reason": "Annual VIP renewal"
  }
}
```

**Bulk Application**:
```json
[
  {
    "entity_id": "user_12345",
    "entity_type": "user",
    "label_id": 42,
    "applied_by": "moderator_789"
  },
  {
    "entity_id": "user_67890",
    "entity_type": "user",
    "label_id": 42,
    "applied_by": "moderator_789"
  }
]
```

**Response** (201):
```json
{
  "success": true,
  "data": {
    "message": "Label applied successfully",
    "entity_label_id": 123
  }
}
```

**Bulk Response**:
```json
{
  "success": true,
  "data": {
    "message": "Bulk operation completed: 2 successful, 0 failed",
    "results": [
      {"success": true, "entity_label_id": 123, "input": {...}},
      {"success": true, "entity_label_id": 124, "input": {...}}
    ],
    "summary": {
      "total": 2,
      "successful": 2,
      "failed": 0
    }
  }
}
```

#### Remove Label
```http
POST /labels/remove
```

Remove a label from an entity.

**Request Body**:
```json
{
  "entity_id": "user_12345",
  "entity_type": "user",
  "label_id": 42
}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "message": "Label removed successfully"
  }
}
```

#### Get Entity Labels
```http
GET /entity/{entity_type}/{entity_id}/labels
```

Get all labels for a specific entity.

**Response**:
```json
{
  "success": true,
  "data": {
    "entity_id": "user_12345",
    "entity_type": "user",
    "labels": [
      {
        "id": 123,
        "entity_id": "user_12345",
        "entity_type": "user",
        "label_id": 42,
        "label_name": "VIP Member",
        "label_color": "#fbbf24",
        "label_icon": "crown",
        "applied_by": "moderator_789",
        "applied_at": "2025-01-15T14:30:00",
        "expires_at": "2025-12-31T23:59:59",
        "metadata": {"reason": "Annual VIP renewal"}
      }
    ],
    "total": 1,
    "limit": 5
  }
}
```

### Search

#### Search By Labels
```http
GET /labels/search
```

Search entities by their labels.

**Query Parameters**:
- `entity_type` (required): Type of entity to search
- `labels` (required): Comma-separated label names
- `community_id` (optional): Filter by community
- `match_all` (optional): Require all labels to match (default: false)
- `limit` (optional): Maximum results (default: 100, max: 1000)

**Response**:
```json
{
  "success": true,
  "data": {
    "entity_type": "user",
    "searched_labels": ["VIP Member", "Premium"],
    "match_all": true,
    "results": [
      {
        "entity_id": "user_12345",
        "entity_type": "user",
        "labels": [
          {
            "label_id": 42,
            "label_name": "VIP Member",
            "label_color": "#fbbf24"
          },
          {
            "label_id": 1,
            "label_name": "Premium",
            "label_color": "#6366f1"
          }
        ],
        "match_count": 2
      }
    ],
    "total": 1
  }
}
```

### Status

#### Get Status
```http
GET /status
```

Get module status and capabilities.

**Response**:
```json
{
  "success": true,
  "data": {
    "status": "operational",
    "module": "labels_core_module",
    "version": "2.0.0",
    "supported_entity_types": ["user", "module", "community", "entityGroup", "item", "event", "memory", "playlist", "browser_source", "command", "alias"],
    "label_limits": {
      "community": 5,
      "user": 5,
      "item": 10,
      "event": 5,
      "memory": 10,
      "default": 5
    }
  }
}
```

---

## Error Responses

All endpoints return errors in standard format:

```json
{
  "success": false,
  "error": "Error message here"
}
```

**Common Status Codes**:
- `200`: Success
- `201`: Created
- `400`: Bad Request (validation error)
- `403`: Forbidden (e.g., modifying system labels)
- `404`: Not Found
- `409`: Conflict (e.g., duplicate label)
- `500`: Internal Server Error

---

## Label Limits

Each entity type has a maximum number of labels:

- **Community**: 5 labels
- **User**: 5 labels (per community)
- **Item**: 10 labels
- **Event**: 5 labels
- **Memory**: 10 labels
- **Default**: 5 labels (for unlisted types)

Attempting to exceed these limits returns a 400 error.

---

## Supported Entity Types

- `user`: User labels
- `module`: Module labels
- `community`: Community labels
- `entityGroup`: Entity group labels
- `item`: Generic items (inventory, resources, etc.)
- `event`: Calendar events
- `memory`: Memories (quotes, URLs, notes)
- `playlist`: Music playlists
- `browser_source`: Browser sources
- `command`: Custom commands
- `alias`: Command aliases

The system is extensible for additional entity types.
