# Workflow Execution API

## Overview

The Execution API provides REST endpoints for triggering, monitoring, and managing workflow executions with comprehensive tracking, real-time status queries, and detailed execution traces.

**Module**: `controllers/execution_api.py`
**Blueprint**: `execution_api` (prefix: `/api/v1/workflows`)
**Framework**: Quart (async Flask alternative)

## Features

- Real-time execution status tracking
- Permission-based execution control
- Dry-run testing (test mode without side effects)
- Execution cancellation
- Detailed execution logs and node state inspection
- Performance metrics tracking
- Paginated execution history
- Comprehensive AAA logging (Authentication, Authorization, Auditing)

## Base URL

```
POST   /api/v1/workflows/:id/execute
GET    /api/v1/workflows/executions/:execId
POST   /api/v1/workflows/executions/:execId/cancel
GET    /api/v1/workflows/:id/executions
POST   /api/v1/workflows/:id/test
```

## Endpoints

### 1. Trigger Workflow Execution

**Endpoint**: `POST /api/v1/workflows/:id/execute`

Trigger a workflow execution with permission validation. The workflow begins executing asynchronously and returns immediately with the execution ID.

**Authentication**: Required (API Key in `X-API-Key` header)

**Path Parameters**:
- `id` (string, required): Workflow UUID

**Request Body**:
```json
{
  "community_id": 123,
  "variables": {
    "param1": "value1",
    "param2": "value2"
  },
  "metadata": {
    "trigger_source": "api",
    "session_id": "sess_123"
  }
}
```

**Response** (202 Accepted):
```json
{
  "success": true,
  "message": "Workflow execution started",
  "data": {
    "execution_id": "550e8400-e29b-41d4-a716-446655440000",
    "workflow_id": "550e8400-e29b-41d4-a716-446655440001",
    "status": "running",
    "start_time": "2025-12-09T12:00:00Z",
    "execution_path": []
  }
}
```

**Error Responses**:
- `400 Bad Request`: Missing required fields, invalid input
- `401 Unauthorized`: Missing or invalid authentication
- `403 Forbidden`: User lacks `can_execute` permission
- `404 Not Found`: Workflow not found
- `500 Internal Server Error`: Server error

**Permissions Required**: `can_execute`

**Logging**:
- AUDIT: Successful execution start
- AUTHZ: Permission denied (if applicable)
- ERROR: Execution failure

---

### 2. Get Execution Details

**Endpoint**: `GET /api/v1/workflows/executions/:execId`

Get detailed information about a specific execution including node states, logs, and performance metrics.

**Authentication**: Required

**Path Parameters**:
- `execId` (string, required): Execution UUID

**Query Parameters**:
- `include_logs` (boolean, default: true): Include node execution logs
- `include_metrics` (boolean, default: false): Include performance metrics

**Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "execution_id": "550e8400-e29b-41d4-a716-446655440000",
    "workflow_id": "550e8400-e29b-41d4-a716-446655440001",
    "status": "completed",
    "start_time": "2025-12-09T12:00:00Z",
    "end_time": "2025-12-09T12:05:00Z",
    "execution_time_seconds": 300,
    "execution_path": ["trigger_node", "condition_node", "action_node"],
    "node_states": {
      "trigger_node": {
        "node_id": "trigger_node",
        "status": "completed",
        "started_at": "2025-12-09T12:00:00Z",
        "completed_at": "2025-12-09T12:00:01Z",
        "input_data": {},
        "output_data": {
          "result": {
            "port_name": "result",
            "data": { "message": "triggered" },
            "timestamp": "2025-12-09T12:00:01Z"
          }
        },
        "retry_count": 0,
        "logs": ["Node execution started", "Node execution completed"],
        "error": null,
        "error_type": null,
        "metadata": {}
      },
      "condition_node": {
        "node_id": "condition_node",
        "status": "completed",
        "started_at": "2025-12-09T12:00:01Z",
        "completed_at": "2025-12-09T12:00:02Z",
        "input_data": {},
        "output_data": {},
        "retry_count": 0,
        "logs": [],
        "error": null,
        "error_type": null,
        "metadata": {}
      }
    },
    "final_variables": {
      "count": 5,
      "status": "success"
    },
    "final_output": {
      "message": "Workflow completed",
      "result": "success"
    },
    "error_message": null,
    "error_node_id": null,
    "metrics": {
      "execution_id": "550e8400-e29b-41d4-a716-446655440000",
      "workflow_id": "550e8400-e29b-41d4-a716-446655440001",
      "total_duration_seconds": 300,
      "node_count": 10,
      "nodes_executed": 3,
      "nodes_skipped": 5,
      "nodes_failed": 0,
      "average_node_time_seconds": 100,
      "slowest_node_id": "action_node",
      "slowest_node_time_seconds": 200,
      "variable_count": 2,
      "memory_used_mb": null,
      "timestamp": "2025-12-09T12:05:00Z"
    }
  }
}
```

**Error Responses**:
- `401 Unauthorized`: Missing authentication
- `404 Not Found`: Execution not found
- `500 Internal Server Error`: Server error

---

### 3. Cancel Execution

**Endpoint**: `POST /api/v1/workflows/executions/:execId/cancel`

Cancel a running workflow execution. Only affects currently running executions.

**Authentication**: Required

**Path Parameters**:
- `execId` (string, required): Execution UUID

**Request Body**: Empty

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Execution cancelled successfully",
  "data": {
    "execution_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "cancelled",
    "cancelled_at": "2025-12-09T12:00:05Z"
  }
}
```

**Error Responses**:
- `400 Bad Request`: Execution cannot be cancelled (not running)
- `401 Unauthorized`: Missing authentication
- `404 Not Found`: Execution not found
- `500 Internal Server Error`: Server error

**Logging**:
- AUDIT: Successful cancellation
- ERROR: Failure to cancel

---

### 4. List Workflow Executions

**Endpoint**: `GET /api/v1/workflows/:id/executions`

List all executions for a workflow with pagination and filtering.

**Authentication**: Required

**Path Parameters**:
- `id` (string, required): Workflow UUID

**Query Parameters**:
- `community_id` (number, required): Community ID for context
- `status` (string, optional): Filter by status (`running`, `completed`, `failed`, `cancelled`)
- `page` (number, default: 1): Page number
- `per_page` (number, default: 20, max: 100): Items per page
- `sort_by` (string, default: start_time): Sort field (`start_time`, `status`, `execution_time`)
- `sort_order` (string, default: desc): Sort order (`asc`, `desc`)

**Response** (200 OK):
```json
{
  "success": true,
  "data": [
    {
      "execution_id": "550e8400-e29b-41d4-a716-446655440000",
      "workflow_id": "550e8400-e29b-41d4-a716-446655440001",
      "status": "completed",
      "start_time": "2025-12-09T12:00:00Z",
      "end_time": "2025-12-09T12:05:00Z",
      "execution_time_seconds": 300,
      "nodes_executed": 5,
      "error": null,
      "success": true
    },
    {
      "execution_id": "550e8400-e29b-41d4-a716-446655440002",
      "workflow_id": "550e8400-e29b-41d4-a716-446655440001",
      "status": "failed",
      "start_time": "2025-12-09T11:50:00Z",
      "end_time": "2025-12-09T11:55:00Z",
      "execution_time_seconds": 300,
      "nodes_executed": 3,
      "error": "Node execution failed: API timeout",
      "success": false
    }
  ],
  "meta": {
    "pagination": {
      "page": 1,
      "per_page": 20,
      "total": 150,
      "total_pages": 8,
      "has_next": true,
      "has_prev": false
    }
  }
}
```

**Error Responses**:
- `400 Bad Request`: Invalid pagination or filter parameters
- `401 Unauthorized`: Missing authentication
- `403 Forbidden`: User lacks `can_view` permission
- `404 Not Found`: Workflow not found
- `500 Internal Server Error`: Server error

**Permissions Required**: `can_view`

---

### 5. Test Workflow (Dry-Run)

**Endpoint**: `POST /api/v1/workflows/:id/test`

Execute a workflow in test mode without side effects. Useful for validating workflow logic before production use.

**Authentication**: Required

**Path Parameters**:
- `id` (string, required): Workflow UUID

**Request Body**:
```json
{
  "community_id": 123,
  "variables": {
    "param1": "test_value"
  },
  "metadata": {
    "session_id": "test_sess_123"
  }
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Workflow test completed",
  "data": {
    "execution_id": "550e8400-e29b-41d4-a716-446655440000",
    "workflow_id": "550e8400-e29b-41d4-a716-446655440001",
    "test_mode": true,
    "status": "completed",
    "execution_time_seconds": 1.5,
    "trace": [
      {
        "node_id": "node1",
        "status": "completed",
        "duration_seconds": 0.5,
        "input": {},
        "output": {
          "result": { "message": "success" }
        },
        "logs": ["Node execution log 1"],
        "error": null,
        "error_type": null
      },
      {
        "node_id": "node2",
        "status": "completed",
        "duration_seconds": 0.8,
        "input": { "input_port": { "message": "success" } },
        "output": { "output_port": { "status": "ok" } },
        "logs": [],
        "error": null,
        "error_type": null
      },
      {
        "node_id": "node3",
        "status": "completed",
        "duration_seconds": 0.2,
        "input": {},
        "output": {},
        "logs": [],
        "error": null,
        "error_type": null
      }
    ],
    "final_variables": {
      "param1": "test_value",
      "result": "success"
    },
    "summary": {
      "nodes_executed": 3,
      "nodes_failed": 0,
      "total_duration": 1.5,
      "passed": true
    }
  }
}
```

**Error Responses**:
- `400 Bad Request`: Invalid input or workflow not found
- `401 Unauthorized`: Missing authentication
- `403 Forbidden`: User lacks `can_execute` permission
- `504 Gateway Timeout`: Test execution timeout
- `500 Internal Server Error`: Server error

**Permissions Required**: `can_execute`

**Logging**:
- AUDIT: Test execution result
- ERROR: Test failure

---

## Data Models

### ExecutionStatus Enum
```python
class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"
```

### NodeExecutionStatus Enum
```python
class NodeExecutionStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"
    PAUSED = "paused"
```

### ExecutionContext
Context containing execution state and variables during workflow execution.

**Key Fields**:
- `execution_id`: Unique execution identifier
- `workflow_id`: Workflow being executed
- `workflow_version`: Version of workflow
- `session_id`: Session identifier
- `entity_id`: Community/entity ID
- `user_id`: User who triggered execution
- `variables`: Runtime variables
- `execution_path`: List of executed node IDs
- `current_node_id`: Node currently executing

### ExecutionResult
Final result of workflow execution.

**Key Fields**:
- `execution_id`: Unique identifier
- `workflow_id`: Workflow ID
- `status`: Final execution status
- `execution_path`: Nodes executed in order
- `node_states`: Dict of node states
- `final_variables`: Final variable values
- `final_output`: Output from end node
- `error_message`: Error message if failed
- `start_time` / `end_time`: Execution timestamps
- `execution_time_seconds`: Total duration

### NodeExecutionState
State of a single node within execution.

**Key Fields**:
- `node_id`: Node identifier
- `status`: Current node status
- `input_data`: Input received
- `output_data`: Output produced
- `started_at` / `completed_at`: Timestamps
- `error`: Error message if failed
- `retry_count`: Number of retries
- `logs`: Execution logs

### ExecutionMetrics
Performance metrics for execution.

**Key Fields**:
- `total_duration_seconds`: Total execution time
- `node_count`: Total nodes in workflow
- `nodes_executed`: Nodes actually executed
- `nodes_skipped`: Nodes skipped
- `nodes_failed`: Nodes that failed
- `average_node_time_seconds`: Average node duration
- `slowest_node_id`: ID of slowest node
- `slowest_node_time_seconds`: Slowest node duration
- `variable_count`: Number of final variables

---

## Error Handling

### HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Successful execution details retrieval |
| 202 | Accepted | Execution started (async) |
| 400 | Bad Request | Invalid input, missing fields |
| 401 | Unauthorized | Missing/invalid authentication |
| 403 | Forbidden | Permission denied (AUTHZ) |
| 404 | Not Found | Resource not found |
| 500 | Internal Server Error | Server error |
| 504 | Gateway Timeout | Workflow timeout |

### Error Response Format

```json
{
  "success": false,
  "message": "Error message",
  "error_code": "ERROR_CODE",
  "details": {}
}
```

### Common Error Codes

- `BAD_REQUEST`: Invalid input parameters
- `UNAUTHORIZED`: Missing/invalid API key
- `PERMISSION_DENIED`: User lacks required permission
- `WORKFLOW_NOT_FOUND`: Workflow doesn't exist
- `EXECUTION_ERROR`: Workflow engine error
- `EXECUTION_TIMEOUT`: Workflow timeout
- `INTERNAL_ERROR`: Server error
- `NOT_FOUND`: Resource not found

---

## Authentication

All endpoints require authentication via API Key in the `X-API-Key` header.

```bash
curl -H "X-API-Key: your-api-key" \
  https://api.example.com/api/v1/workflows/workflow-id/execute \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "community_id": 123,
    "variables": {"param1": "value"}
  }'
```

---

## Authorization

Permission checks are performed for:

- **`can_execute`**: Required to execute or test workflows
- **`can_view`**: Required to list executions and get details

Owners of workflows have all permissions automatically.

---

## Rate Limiting

Rate limits are enforced per API key:
- Standard tier: 100 requests/minute
- Premium tier: 1000 requests/minute

---

## Logging (AAA)

All operations are logged with comprehensive AAA tracking:

**Categories**:
- **AUTH**: Authentication events
- **AUTHZ**: Authorization decisions
- **AUDIT**: User actions and changes
- **ERROR**: Errors and failures
- **SYSTEM**: System events

**Log Format**:
```
[timestamp] LEVEL module:version EVENT_TYPE community=X user=Y action=Z result=STATUS
```

**Example**:
```
[2025-12-09T12:00:00Z] INFO workflow_core_module:1.0.0 AUDIT community=123 user=456 action=execute_workflow result=SUCCESS
```

---

## Usage Examples

### Execute Workflow

```bash
curl -X POST \
  https://api.example.com/api/v1/workflows/550e8400-e29b-41d4-a716-446655440001/execute \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "community_id": 123,
    "variables": {
      "user_name": "john_doe",
      "action": "send_message"
    },
    "metadata": {
      "session_id": "sess_abc123"
    }
  }'
```

### Get Execution Details

```bash
curl https://api.example.com/api/v1/workflows/executions/550e8400-e29b-41d4-a716-446655440000 \
  -H "X-API-Key: your-api-key"
```

### List Executions

```bash
curl "https://api.example.com/api/v1/workflows/550e8400-e29b-41d4-a716-446655440001/executions?community_id=123&status=completed&page=1&per_page=20" \
  -H "X-API-Key: your-api-key"
```

### Test Workflow

```bash
curl -X POST \
  https://api.example.com/api/v1/workflows/550e8400-e29b-41d4-a716-446655440001/test \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "community_id": 123,
    "variables": {
      "test_param": "test_value"
    }
  }'
```

### Cancel Execution

```bash
curl -X POST \
  https://api.example.com/api/v1/workflows/executions/550e8400-e29b-41d4-a716-446655440000/cancel \
  -H "X-API-Key: your-api-key"
```

---

## Performance Considerations

- Executions are async (202 response doesn't mean completion)
- Use polling or webhooks to track execution status
- Large execution histories should use pagination
- Include only needed fields with query parameters
- Metrics computation may have slight overhead

---

## Best Practices

1. **Always check permissions** before user-facing operations
2. **Use test mode** to validate workflows before production
3. **Monitor execution metrics** for performance issues
4. **Implement retry logic** for network failures
5. **Log execution IDs** for debugging and auditing
6. **Use pagination** for listing executions
7. **Cancel stuck executions** to free resources
8. **Set appropriate timeouts** for long-running workflows

