# Workflow Engine - Comprehensive Reference

Complete documentation for the WaddleBot workflow engine including execution, validation, permissions, scheduling, and node execution.

## Overview

The workflow engine provides a complete visual workflow automation system with:
- REST API for workflow management and execution
- Comprehensive workflow validation and testing
- Permission-based access control
- Cron and interval-based scheduling
- Real-time execution tracking and metrics
- Webhook-based triggering
- License-gated features

## Architecture

```
Workflow API Controller
├── Workflow Service (business logic)
│   ├── License Service (feature gating)
│   ├── Permission Service (RBAC)
│   └── Validation Service (structural integrity)
├── Execution API Controller
│   ├── Workflow Engine (orchestration)
│   ├── Node Executor (individual node execution)
│   └── Execution tracking
├── Schedule Service (cron/interval scheduling)
├── Webhook API (HTTP-based triggers)
└── Database (AsyncDAL with PostgreSQL)
```

## Data Models

### Workflows

Workflows are defined with nodes and connections. Complete model reference in MODELS.md.

- workflow_id: UUID
- name, description, version (semver)
- status: DRAFT, ACTIVE, PAUSED, DISABLED, ARCHIVED
- nodes: 22 node types supported
- connections: DAG structure with validation
- global_variables: shared workflow state

### Execution Context

```python
ExecutionContext:
  execution_id, workflow_id, workflow_version
  session_id, entity_id (community), user_id
  variables: dict[str, any]
  execution_path: list[node_id]
  cancelled: boolean

ExecutionResult:
  status: PENDING | RUNNING | COMPLETED | FAILED | CANCELLED | PAUSED
  execution_path: list[node_id] (execution order)
  node_states: dict[node_id, NodeExecutionState]
  final_variables, final_output
  execution_time_seconds
```

## API Endpoints

### Workflow Management

| Method | Path | Purpose | Auth Required | Permission |
|--------|------|---------|---------------|-----------|
| POST | `/api/v1/workflows` | Create workflow | Yes | None (owner auto) |
| GET | `/api/v1/workflows` | List workflows | Yes | None |
| GET | `/api/v1/workflows/:id` | Get details | Yes | can_view |
| PUT | `/api/v1/workflows/:id` | Update | Yes | can_edit |
| DELETE | `/api/v1/workflows/:id` | Archive | Yes | can_delete |
| POST | `/api/v1/workflows/:id/publish` | Publish | Yes | can_edit |
| POST | `/api/v1/workflows/:id/validate` | Validate | Yes | None |

### Execution Control

| Method | Path | Purpose | Response |
|--------|------|---------|----------|
| POST | `/api/v1/workflows/:id/execute` | Trigger execution | 202 Accepted |
| GET | `/api/v1/workflows/executions/:execId` | Get execution details | 200 OK |
| POST | `/api/v1/workflows/executions/:execId/cancel` | Cancel execution | 200 OK |
| GET | `/api/v1/workflows/:id/executions` | List executions | 200 OK |
| POST | `/api/v1/workflows/:id/test` | Test (dry-run) | 200 OK |

### Webhooks

| Method | Path | Purpose | Auth Required |
|--------|------|---------|---------------|
| POST | `/api/v1/workflows/webhooks/:token` | Trigger via webhook | No (signature-based) |
| GET | `/api/v1/workflows/:id/webhooks` | List webhooks | Yes |
| POST | `/api/v1/workflows/:id/webhooks` | Create webhook | Yes |
| DELETE | `/api/v1/workflows/:id/webhooks/:id` | Delete webhook | Yes |

### Scheduling

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/schedules` | Create schedule |
| PUT | `/api/v1/schedules/:id` | Update schedule |
| DELETE | `/api/v1/schedules/:id` | Remove schedule |

## Workflow Validation

Comprehensive multi-layer validation using WorkflowValidationService:

### Validation Checks

1. **Complexity Limits**: Max 100 nodes, max depth 10, loop safety 10,000 iterations
2. **Graph Structure**: DAG validation, cycle detection, reachability, orphan detection
3. **Node Configuration**: 22 node type validators, field validation, enum checks
4. **Connections**: Port existence, type compatibility, conditional syntax
5. **Triggers**: At least one required, type validation, capability checks
6. **Security**: Code injection detection, system command blocking, dangerous pattern scanning

### Validation Result

```json
{
  "is_valid": true|false,
  "errors": ["list of critical errors"],
  "warnings": ["list of non-critical warnings"],
  "node_validation_errors": {"node_id": ["errors"]}
}
```

## Permissions

Workflow permissions are granular and composable:

| Permission | Allows |
|-----------|--------|
| can_view | View workflow, definition, execution history |
| can_edit | Modify workflow definition and settings |
| can_execute | Trigger workflow execution |
| can_delete | Archive/delete workflow |
| can_manage_permissions | Grant/revoke permissions |

**Permission Resolution (OR logic):**
1. Owner (creator) → all permissions
2. User-level permission
3. Role-based permission (from user's roles)
4. Entity-level permission (organization-wide)

## Scheduling Service

Complete schedule management with APScheduler integration:

### Schedule Types

**Cron Schedules**
```
0 0 * * *        # Daily at midnight
0 12 * * *       # Daily at noon
0 9-17 * * 1-5   # Every hour 9 AM-5 PM on weekdays
*/15 * * * *     # Every 15 minutes
```

**Interval Schedules**
```
60 seconds, 3600 (hourly), 86400 (daily), 604800 (weekly)
```

**One-Time Schedules**
```
Single execution at specific datetime
```

### Features

- Grace period handling (default 15 min for missed executions)
- Execution limits per schedule
- Custom context data passed with trigger
- Timezone support
- Status tracking (next_execution_at, last_execution_at)

## Node Executor

Specialized execution logic for 22 node types:

### Condition Evaluation

**Operators:** equals, not_equals, greater_than, less_than, greater_equal, less_equal, contains, not_contains, matches_regex, in_list, not_in_list

**Logic:** AND (all conditions must pass)

### Variable Replacement

Template syntax: `{{variable_name}}`

Supported in message templates, webhook URLs/headers/bodies, variable values, content templates

### Security

**RestrictedPython Sandbox (DataTransform):**
- ✓ Basic arithmetic, variable access, safe builtins
- ✗ File I/O, network, system calls, dangerous builtins
- Timeout: 5 seconds per transformation

### Error Handling

- Error types: validation, execution, timeout, api_error, webhook_error, exception
- Automatic retries with exponential backoff for ActionWebhook
- Comprehensive logging of failures

## License Service

Premium feature gating via PenguinTech License Server:

### Tiers

| Tier | Workflows | Features | Cost |
|------|-----------|----------|------|
| Free | 1 per community | Basic | $0 |
| Premium | Unlimited | All | Subscription |

### Integration

Returns HTTP 402 (Payment Required) when license validation fails.

Development mode (RELEASE_MODE=false) bypasses all checks.

## Logging

All operations logged with AAA (Authentication, Authorization, Audit):

**Categories:**
- AUTH: Authentication events
- AUTHZ: Authorization decisions  
- AUDIT: User actions and changes
- ERROR: Errors and failures
- SYSTEM: Service lifecycle

**Format:**
```
[timestamp] LEVEL module:version EVENT_TYPE community=X user=Y action=Z result=STATUS
```

## Error Codes

| Code | HTTP | Meaning |
|------|------|---------|
| BAD_REQUEST | 400 | Invalid input |
| UNAUTHORIZED | 401 | Missing/invalid authentication |
| PAYMENT_REQUIRED | 402 | License validation failed |
| FORBIDDEN | 403 | Permission denied |
| NOT_FOUND | 404 | Resource not found |
| EXECUTION_ERROR | 400 | Workflow engine error |
| EXECUTION_TIMEOUT | 504 | Workflow timeout |

## Configuration

**Environment Variables:**

```bash
# Module
MODULE_PORT=8070

# Database
DATABASE_URI=postgresql://waddlebot:password@localhost:5432/waddlebot

# Execution
WORKFLOW_TIMEOUT_SECONDS=300
MAX_LOOP_ITERATIONS=100
MAX_TOTAL_OPERATIONS=1000
MAX_LOOP_DEPTH=10
MAX_PARALLEL_NODES=10

# Scheduling
SCHEDULER_TIMEZONE=UTC
SCHEDULE_GRACE_PERIOD_MINUTES=15

# License
LICENSE_SERVER_URL=https://license.penguintech.io
RELEASE_MODE=false  # true in production
```

## Database Tables

- `workflows` - Workflow definitions
- `workflow_executions` - Execution history and state
- `workflow_connections` - Node connection definitions
- `workflow_nodes` - Node configurations
- `workflow_permissions` - Permission entries
- `workflow_schedules` - Schedule definitions
- `workflow_webhooks` - Webhook configurations
- `workflow_audit_log` - Audit trail

## Testing

**Unit Tests:**
```bash
pytest core/workflow_core_module/tests/test_workflow_service.py
pytest core/workflow_core_module/services/test_node_executor.py
pytest core/workflow_core_module/services/validation_service_tests.py
```

**Integration Tests:**
```bash
pytest core/workflow_core_module/tests/test_workflow_api.py
```

**Health Check:**
```bash
curl http://localhost:8070/health
```

## Best Practices

1. Always validate before publishing workflows
2. Use test mode to verify logic before production
3. Monitor execution metrics for performance issues
4. Set appropriate timeouts for external calls
5. Use variable replacement for dynamic content
6. Implement error handling with flow control
7. Log execution IDs for debugging and auditing
8. Clean up old executions to manage database growth
9. Regularly audit permission grants and revokes
10. Keep workflows simple and well-organized

## Related Documentation

- **MODELS.md** - Complete data model reference (nodes, workflow, execution)
- **PERMISSION_SERVICE.md** - Detailed permission and RBAC documentation
- **VALIDATION_SERVICE_README.md** - Complete validation rules and error messages
- **SCHEDULE_SERVICE_README.md** - Comprehensive scheduling documentation
- **NODE_EXECUTOR.md** - Detailed node execution logic and patterns
- **LICENSE_SERVICE_README.md** - License validation and feature gating
