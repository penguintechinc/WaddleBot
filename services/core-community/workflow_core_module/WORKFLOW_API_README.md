# Workflow API Documentation

## Overview

The Workflow API provides comprehensive REST endpoints for managing visual workflow automation in WaddleBot. This API integrates with the License Service (premium features), Permission Service (access control), and Validation Service (workflow integrity).

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Workflow API Controller                  │
│                    (controllers/workflow_api.py)             │
│  - REST endpoints with authentication                        │
│  - Error handling and HTTP status mapping                    │
│  - Pagination support                                        │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    Workflow Service                          │
│                 (services/workflow_service.py)               │
│  - Business logic and orchestration                          │
│  - License validation (HTTP 402 on failure)                  │
│  - Permission checks                                         │
│  - Audit logging                                             │
└──────┬───────────────┬────────────────┬─────────────────────┘
       │               │                │
       ▼               ▼                ▼
┌─────────────┐ ┌──────────────┐ ┌────────────────┐
│   License   │ │  Permission  │ │   Validation   │
│   Service   │ │   Service    │ │    Service     │
└─────────────┘ └──────────────┘ └────────────────┘
       │               │                │
       └───────────────┴────────────────┘
                       │
                       ▼
              ┌─────────────────┐
              │   PostgreSQL    │
              │   (AsyncDAL)    │
              └─────────────────┘
```

## API Endpoints

### Base URL
```
/api/v1/workflows
```

### Authentication
All endpoints require authentication via:
- **JWT Token**: `Authorization: Bearer <token>`
- **API Key**: `X-API-Key: <key>`

User information is attached to `request.current_user` after authentication.

---

## Endpoints

### 1. Create Workflow

**POST** `/api/v1/workflows`

Create a new workflow with license validation.

#### Request Body
```json
{
  "name": "My Workflow",
  "description": "Workflow description",
  "community_id": 1,
  "entity_id": 100,
  "nodes": {
    "node1": {
      "node_id": "node1",
      "type": "trigger_command",
      "label": "Command Trigger",
      "config": {}
    }
  },
  "connections": [
    {
      "connection_id": "conn1",
      "from_node_id": "node1",
      "from_port_name": "output",
      "to_node_id": "node2",
      "to_port_name": "input"
    }
  ],
  "trigger_type": "command",
  "trigger_config": {
    "command_pattern": "!test",
    "platforms": ["twitch"]
  },
  "global_variables": {},
  "license_key": "PENG-XXXX-XXXX-XXXX-XXXX-ABCD"
}
```

#### Response
```json
{
  "success": true,
  "data": {
    "workflow_id": "uuid-here",
    "metadata": { ... },
    "nodes": { ... },
    "connections": [ ... ],
    "status": "draft",
    "created_at": "2025-12-09T12:00:00Z"
  },
  "message": "Workflow created successfully",
  "timestamp": "2025-12-09T12:00:00Z"
}
```

#### Status Codes
- `201 Created`: Workflow created successfully
- `400 Bad Request`: Invalid input data
- `401 Unauthorized`: Missing or invalid authentication
- `402 Payment Required`: License validation failed (free tier limit)
- `500 Internal Server Error`: Server error

---

### 2. List Workflows

**GET** `/api/v1/workflows`

List accessible workflows with pagination and filtering.

#### Query Parameters
- `entity_id` (required): Entity ID
- `community_id` (optional): Community ID for context
- `status` (optional): Filter by status (`draft`, `active`, `archived`)
- `search` (optional): Search in name/description
- `page` (optional): Page number (default: 1)
- `per_page` (optional): Items per page (default: 20, max: 100)

#### Example Request
```
GET /api/v1/workflows?entity_id=100&status=active&page=1&per_page=20
```

#### Response
```json
{
  "success": true,
  "data": [
    {
      "workflow_id": "uuid-1",
      "name": "Workflow 1",
      "description": "Description",
      "status": "active",
      "is_active": true,
      "trigger_type": "command",
      "execution_count": 42,
      "success_count": 40,
      "failure_count": 2,
      "created_at": "2025-12-09T12:00:00Z",
      "updated_at": "2025-12-09T13:00:00Z",
      "last_executed_at": "2025-12-09T14:00:00Z"
    }
  ],
  "meta": {
    "pagination": {
      "page": 1,
      "per_page": 20,
      "total": 5,
      "total_pages": 1,
      "has_next": false,
      "has_prev": false
    }
  }
}
```

#### Status Codes
- `200 OK`: Success
- `400 Bad Request`: Invalid parameters
- `401 Unauthorized`: Authentication required

---

### 3. Get Workflow

**GET** `/api/v1/workflows/:id`

Get complete workflow details by ID.

#### Path Parameters
- `workflow_id`: Workflow UUID

#### Query Parameters
- `community_id` (optional): Community ID for permission context

#### Example Request
```
GET /api/v1/workflows/550e8400-e29b-41d4-a716-446655440000?community_id=1
```

#### Response
```json
{
  "success": true,
  "data": {
    "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
    "community_id": 1,
    "entity_id": 100,
    "name": "My Workflow",
    "description": "Description",
    "version": 1,
    "status": "active",
    "is_active": true,
    "nodes": { ... },
    "connections": [ ... ],
    "trigger_type": "command",
    "trigger_config": { ... },
    "max_execution_time": 300,
    "execution_count": 42,
    "success_count": 40,
    "failure_count": 2,
    "created_at": "2025-12-09T12:00:00Z",
    "updated_at": "2025-12-09T13:00:00Z",
    "last_executed_at": "2025-12-09T14:00:00Z"
  }
}
```

#### Status Codes
- `200 OK`: Success
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Permission denied (user lacks `can_view`)
- `404 Not Found`: Workflow not found

---

### 4. Update Workflow

**PUT** `/api/v1/workflows/:id`

Update workflow fields.

#### Path Parameters
- `workflow_id`: Workflow UUID

#### Request Body
```json
{
  "name": "Updated Name",
  "description": "Updated Description",
  "nodes": { ... },
  "connections": [ ... ],
  "community_id": 1
}
```

#### Updateable Fields
- `name`
- `description`
- `nodes`
- `connections`
- `trigger_type`
- `trigger_config`
- `max_execution_time`
- `max_iterations`
- `retry_config`

#### Response
```json
{
  "success": true,
  "data": { ... },
  "message": "Workflow updated successfully"
}
```

#### Status Codes
- `200 OK`: Success
- `400 Bad Request`: Invalid input
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Permission denied (user lacks `can_edit`)
- `404 Not Found`: Workflow not found

---

### 5. Delete Workflow

**DELETE** `/api/v1/workflows/:id`

Archive (soft delete) workflow.

#### Path Parameters
- `workflow_id`: Workflow UUID

#### Query Parameters
- `community_id` (optional): Community ID for permission context

#### Example Request
```
DELETE /api/v1/workflows/550e8400-e29b-41d4-a716-446655440000?community_id=1
```

#### Response
```json
{
  "success": true,
  "data": {
    "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "archived",
    "message": "Workflow archived successfully"
  },
  "message": "Workflow archived successfully"
}
```

#### Status Codes
- `200 OK`: Success
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Permission denied (user lacks `can_delete`)
- `404 Not Found`: Workflow not found

---

### 6. Publish Workflow

**POST** `/api/v1/workflows/:id/publish`

Validate and publish workflow, activating it for execution.

#### Path Parameters
- `workflow_id`: Workflow UUID

#### Request Body (optional)
```json
{
  "community_id": 1
}
```

#### Response
```json
{
  "success": true,
  "data": {
    "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "active",
    "is_active": true,
    ...
  },
  "message": "Workflow published successfully"
}
```

#### Status Codes
- `200 OK`: Success
- `400 Bad Request`: Validation failed
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Permission denied (user lacks `can_edit`)
- `404 Not Found`: Workflow not found

---

### 7. Validate Workflow

**POST** `/api/v1/workflows/:id/validate`

Validate workflow structure without publishing.

#### Path Parameters
- `workflow_id`: Workflow UUID

#### Example Request
```
POST /api/v1/workflows/550e8400-e29b-41d4-a716-446655440000/validate
```

#### Response
```json
{
  "success": true,
  "data": {
    "is_valid": true,
    "errors": [],
    "warnings": [
      "Workflow depth (8) exceeds recommended maximum (10)"
    ],
    "node_validation_errors": {},
    "error_count": 0,
    "warning_count": 1
  },
  "message": "Validation completed"
}
```

#### Validation Failure Example
```json
{
  "success": true,
  "data": {
    "is_valid": false,
    "errors": [
      "Cycle detected in workflow: node1 -> node2 -> node1"
    ],
    "warnings": [],
    "node_validation_errors": {
      "node3": [
        "Command pattern cannot be empty"
      ]
    },
    "error_count": 2,
    "warning_count": 0
  }
}
```

#### Status Codes
- `200 OK`: Validation completed (check `is_valid` in response)
- `401 Unauthorized`: Authentication required
- `404 Not Found`: Workflow not found

---

## Error Response Format

All errors follow a consistent format:

```json
{
  "success": false,
  "error": {
    "message": "Error message here",
    "code": "ERROR_CODE",
    "timestamp": "2025-12-09T12:00:00Z"
  }
}
```

### Common Error Codes

| Code | Status | Description |
|------|--------|-------------|
| `BAD_REQUEST` | 400 | Invalid request parameters |
| `UNAUTHORIZED` | 401 | Authentication required |
| `PAYMENT_REQUIRED` | 402 | License validation failed |
| `FORBIDDEN` | 403 | Permission denied |
| `NOT_FOUND` | 404 | Resource not found |
| `WORKFLOW_NOT_FOUND` | 404 | Workflow not found |
| `PERMISSION_DENIED` | 403 | Insufficient permissions |
| `WORKFLOW_ERROR` | 400-500 | Workflow operation error |
| `INTERNAL_ERROR` | 500 | Server error |

---

## License Validation

Workflow creation validates against the PenguinTech License Server:

### License Tiers
- **Free**: 0 workflows allowed
- **Premium**: Unlimited workflows

### HTTP 402 Response
When license validation fails:

```json
{
  "success": false,
  "error": {
    "message": "Free tier does not support workflows. Upgrade to Premium.",
    "code": "PAYMENT_REQUIRED",
    "timestamp": "2025-12-09T12:00:00Z",
    "details": {
      "community_id": 1
    }
  }
}
```

### Development Mode
When `RELEASE_MODE=false`, license checks are bypassed and all communities are treated as Premium.

---

## Permissions

Workflow operations require specific permissions:

| Operation | Required Permission |
|-----------|-------------------|
| View workflow | `can_view` |
| Create workflow | Owner (automatic) |
| Update workflow | `can_edit` |
| Delete workflow | `can_delete` |
| Publish workflow | `can_edit` |
| Validate workflow | No permission check |

### Permission Levels
- **Owner**: Automatic full permissions (creator)
- **User**: Direct user-level permissions
- **Role**: Role-based permissions
- **Entity**: Entity-level permissions (all users in entity)

---

## Audit Logging

All workflow operations are logged to `workflow_audit_log` table:

```sql
INSERT INTO workflow_audit_log (
  workflow_id,
  action,
  action_by,
  changes,
  metadata
)
```

### Logged Actions
- `created`
- `updated`
- `published`
- `archived`
- `deleted`

---

## Example Usage

### Python Example

```python
import requests

# Authentication
headers = {
    "Authorization": "Bearer <jwt-token>",
    # OR
    "X-API-Key": "<api-key>"
}

# Create workflow
response = requests.post(
    "http://workflow-service:8070/api/v1/workflows",
    json={
        "name": "My Workflow",
        "community_id": 1,
        "entity_id": 100,
        "nodes": {...},
        "connections": [...],
        "trigger_type": "command",
        "trigger_config": {"command_pattern": "!test"}
    },
    headers=headers
)

workflow_id = response.json()["data"]["workflow_id"]

# Validate workflow
response = requests.post(
    f"http://workflow-service:8070/api/v1/workflows/{workflow_id}/validate",
    headers=headers
)

if response.json()["data"]["is_valid"]:
    # Publish workflow
    response = requests.post(
        f"http://workflow-service:8070/api/v1/workflows/{workflow_id}/publish",
        headers=headers
    )
    print("Workflow published!")
```

### cURL Example

```bash
# Create workflow
curl -X POST http://workflow-service:8070/api/v1/workflows \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Workflow",
    "community_id": 1,
    "entity_id": 100,
    "nodes": {},
    "connections": [],
    "trigger_type": "command",
    "trigger_config": {}
  }'

# List workflows
curl -X GET "http://workflow-service:8070/api/v1/workflows?entity_id=100&page=1&per_page=20" \
  -H "Authorization: Bearer <token>"

# Get workflow
curl -X GET "http://workflow-service:8070/api/v1/workflows/<workflow-id>" \
  -H "Authorization: Bearer <token>"

# Publish workflow
curl -X POST "http://workflow-service:8070/api/v1/workflows/<workflow-id>/publish" \
  -H "Authorization: Bearer <token>"
```

---

## Integration with Existing Services

### License Service
```python
# Validates against PenguinTech License Server
await license_service.validate_workflow_creation(
    community_id=community_id,
    entity_id=str(entity_id),
    license_key=license_key
)
```

### Permission Service
```python
# Checks user permissions
can_edit = await permission_service.check_permission(
    workflow_id=workflow_id,
    user_id=user_id,
    permission_type="can_edit",
    community_id=community_id
)
```

### Validation Service
```python
# Validates workflow structure
validation_result = validation_service.validate_workflow(workflow_def)
```

---

## Testing

### Unit Tests
```bash
pytest core/workflow_core_module/tests/test_workflow_service.py
```

### Integration Tests
```bash
pytest core/workflow_core_module/tests/test_workflow_api.py
```

### Manual Testing
```bash
# Start module
cd core/workflow_core_module
python app.py

# Test endpoints
curl http://localhost:8070/health
```

---

## Configuration

Environment variables in `.env`:

```bash
# Module Configuration
MODULE_PORT=8070

# Database
DATABASE_URI=postgresql://waddlebot:password@localhost:5432/waddlebot

# Redis
REDIS_URL=redis://localhost:6379/0

# License Server
LICENSE_SERVER_URL=https://license.penguintech.io
RELEASE_MODE=false

# Feature Flags
FEATURE_WORKFLOWS_ENABLED=true
```

---

## See Also

- [License Service Documentation](LICENSE_SERVICE_README.md)
- [Permission Service Documentation](PERMISSION_SERVICE.md)
- [Validation Service Documentation](VALIDATION_SERVICE_README.md)
- [Workflow Models](MODELS.md)
- [Database Schema](../../config/postgres/migrations/003_add_workflow_tables.sql)
