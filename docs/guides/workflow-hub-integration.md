# Workflow Hub Backend Integration

## Overview

This document describes the complete workflow backend integration into the Waddles hub module. The implementation provides Express controllers and routes that proxy workflow management operations to the workflow-core microservice while enforcing license validation and permission checks.

## Implementation Details

### Files Created

#### 1. `/admin/hub_module/backend/src/controllers/workflowController.js` (19 KB)

The main controller that handles all workflow operations through a proxy pattern to workflow-core.

**Key Features:**
- License validation before workflow operations
- HTTP proxy to workflow-core API (`http://workflow-core:8070`)
- Comprehensive AAA logging (Authentication, Authorization, Auditing)
- Error handling with proper HTTP status codes
- Support for all workflow operations

**Exported Functions:**

**CRUD Operations:**
- `createWorkflow(req, res, next)` - POST `/api/v1/admin/:communityId/workflows`
- `listWorkflows(req, res, next)` - GET `/api/v1/admin/:communityId/workflows`
- `getWorkflow(req, res, next)` - GET `/api/v1/admin/:communityId/workflows/:workflowId`
- `updateWorkflow(req, res, next)` - PUT `/api/v1/admin/:communityId/workflows/:workflowId`
- `deleteWorkflow(req, res, next)` - DELETE `/api/v1/admin/:communityId/workflows/:workflowId`

**Workflow Operations:**
- `publishWorkflow(req, res, next)` - POST `/api/v1/admin/:communityId/workflows/:workflowId/publish`
- `validateWorkflow(req, res, next)` - POST `/api/v1/admin/:communityId/workflows/validate`

**Execution Operations:**
- `executeWorkflow(req, res, next)` - POST `/api/v1/admin/:communityId/workflows/:workflowId/execute`
- `testWorkflow(req, res, next)` - POST `/api/v1/admin/:communityId/workflows/:workflowId/test`
- `getExecution(req, res, next)` - GET `/api/v1/admin/:communityId/workflows/:workflowId/executions/:executionId`
- `cancelExecution(req, res, next)` - POST `/api/v1/admin/:communityId/workflows/:workflowId/executions/:executionId/cancel`
- `listExecutions(req, res, next)` - GET `/api/v1/admin/:communityId/workflows/:workflowId/executions`

**Webhook Operations:**
- `listWebhooks(req, res, next)` - GET `/api/v1/admin/:communityId/workflows/:workflowId/webhooks`
- `createWebhook(req, res, next)` - POST `/api/v1/admin/:communityId/workflows/:workflowId/webhooks`
- `deleteWebhook(req, res, next)` - DELETE `/api/v1/admin/:communityId/workflows/:workflowId/webhooks/:webhookId`

**Internal Helpers:**
- `validateLicense(communityId)` - Checks community has valid workflow license (pro/enterprise/premium tier)
- `proxyRequest(method, path, data, params)` - Makes HTTP requests to workflow-core

#### 2. `/admin/hub_module/backend/src/routes/workflow.js` (2.9 KB)

Express router that defines all workflow-related endpoints with proper authentication and authorization.

**Features:**
- All routes require authentication via `requireAuth` middleware
- All routes require community admin role via `requireCommunityAdmin` middleware
- Clean separation of route definitions by operation category
- RESTful endpoint design following Waddles patterns

**Route Groups:**

1. **CRUD Operations** - Basic workflow management
2. **Workflow Operations** - Publish and validation
3. **Execution Operations** - Run and monitor workflow executions
4. **Webhook Operations** - Manage event webhooks

#### 3. Modified `/admin/hub_module/backend/src/routes/admin.js`

Updated to register workflow routes as a nested router:
```javascript
import workflowRoutes from './workflow.js';
// ... in router setup ...
router.use('/:communityId/workflows', workflowRoutes);
```

## License Validation

The controller enforces license validation for premium features:

**License Check Triggers:**
- Workflow creation
- Workflow publishing
- Workflow execution

**License Requirements:**
- License key must exist
- License must not be expired
- License tier must be one of: `pro`, `enterprise`, `premium`

**Validation Response:**
```javascript
{
  valid: true/false,
  reason: "descriptive message if invalid"
}
```

## API Endpoint Mapping

### Workflow CRUD

| Operation | Method | Endpoint |
|-----------|--------|----------|
| List | GET | `/api/v1/admin/{communityId}/workflows` |
| Create | POST | `/api/v1/admin/{communityId}/workflows` |
| Get | GET | `/api/v1/admin/{communityId}/workflows/{workflowId}` |
| Update | PUT | `/api/v1/admin/{communityId}/workflows/{workflowId}` |
| Delete | DELETE | `/api/v1/admin/{communityId}/workflows/{workflowId}` |

### Workflow Operations

| Operation | Method | Endpoint |
|-----------|--------|----------|
| Publish | POST | `/api/v1/admin/{communityId}/workflows/{workflowId}/publish` |
| Validate | POST | `/api/v1/admin/{communityId}/workflows/validate` |

### Execution Operations

| Operation | Method | Endpoint |
|-----------|--------|----------|
| Execute | POST | `/api/v1/admin/{communityId}/workflows/{workflowId}/execute` |
| Test | POST | `/api/v1/admin/{communityId}/workflows/{workflowId}/test` |
| List | GET | `/api/v1/admin/{communityId}/workflows/{workflowId}/executions` |
| Get | GET | `/api/v1/admin/{communityId}/workflows/{workflowId}/executions/{executionId}` |
| Cancel | POST | `/api/v1/admin/{communityId}/workflows/{workflowId}/executions/{executionId}/cancel` |

### Webhook Operations

| Operation | Method | Endpoint |
|-----------|--------|----------|
| List | GET | `/api/v1/admin/{communityId}/workflows/{workflowId}/webhooks` |
| Create | POST | `/api/v1/admin/{communityId}/workflows/{workflowId}/webhooks` |
| Delete | DELETE | `/api/v1/admin/{communityId}/workflows/{workflowId}/webhooks/{webhookId}` |

## Proxy Pattern

The controller uses a centralized `proxyRequest()` helper that:

1. Constructs the workflow-core API URL
2. Makes the HTTP request with proper headers
3. Handles axios errors and converts them to AppError format
4. Returns the response data or throws normalized errors

**Error Handling:**
- Network errors: `SERVICE_UNAVAILABLE` (500)
- HTTP errors from workflow-core: Preserves status code and original message
- Database errors: `INTERNAL_ERROR` (500)

## Authentication & Authorization

**Authentication:**
- All routes require valid JWT token (Bearer token or cookie)
- Token verification via `requireAuth` middleware
- Session validation against `hub_sessions` table

**Authorization:**
- All routes require community admin role
- Admin roles: `community-owner`, `community-admin`, `moderator`
- Super admins and platform admins have implicit access
- Community membership verified for each request

## Logging & Audit Trail

**Log Categories:**
- `AUTH` - Authentication events (token validation)
- `AUTHZ` - Authorization events (permission checks)
- `AUDIT` - Action logging (create, update, delete, execute, publish)
- `DEBUG` - Development debugging information
- `ERROR` - Error conditions

**Audit Log Example:**
```json
{
  "timestamp": "2025-12-09T15:30:45.123Z",
  "level": "INFO",
  "module": "hub_module",
  "message": "AUDIT: Workflow created",
  "category": "AUDIT",
  "communityId": 42,
  "workflowId": "wf-abc123",
  "workflowName": "Daily Report",
  "createdBy": "user#twitch:123456"
}
```

## Error Handling

The controller returns consistent error responses using the `errors` factory from errorHandler middleware:

**Error Types:**
- `400 BAD_REQUEST` - Invalid input parameters
- `401 UNAUTHORIZED` - Authentication required or invalid token
- `403 FORBIDDEN` - License not valid or insufficient permissions
- `404 NOT_FOUND` - Workflow/execution/webhook not found
- `500 INTERNAL_ERROR` - Workflow service error or database error

**Error Response Format:**
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message"
  }
}
```

## Configuration

**Environment Variable:**
- `WORKFLOW_CORE_URL` - URL to workflow-core API (default: `http://workflow-core:8070`)

**Database Requirements:**
- Must have access to `communities` table with columns:
  - `id` - Community ID
  - `license_key` - License key
  - `license_expires_at` - License expiration timestamp
  - `license_tier` - License tier (pro, enterprise, premium)

## Integration with Existing Hub Patterns

The implementation follows established Waddles hub patterns:

1. **Controller Pattern** - Similar to `marketplaceController.js`
2. **Route Structure** - Follows admin route nesting pattern
3. **Error Handling** - Uses centralized `AppError` and `errors` factory
4. **Logging** - Uses AAA logger with categories
5. **Authentication** - Uses existing JWT and role-based access control
6. **Permission Checks** - Validates community admin role before operations

## Usage Examples

### Create a Workflow
```bash
curl -X POST http://localhost:8000/api/v1/admin/42/workflows \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Daily Report",
    "description": "Generate daily community report",
    "definition": {
      "steps": [
        {
          "id": "step1",
          "action": "fetch_data",
          "params": {}
        }
      ]
    }
  }'
```

### List Workflows
```bash
curl http://localhost:8000/api/v1/admin/42/workflows \
  -H "Authorization: Bearer {token}"
```

### Execute Workflow
```bash
curl -X POST http://localhost:8000/api/v1/admin/42/workflows/wf-123/execute \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "param1": "value1"
    }
  }'
```

## Testing

All files pass Node.js syntax validation:
```bash
node --check controllers/workflowController.js
node --check routes/workflow.js
node --check routes/admin.js
```

## Future Enhancements

1. **Rate Limiting** - Add rate limiting for workflow execution
2. **Workflow Templates** - Support for workflow templates
3. **Conditional Routing** - Advanced workflow routing rules
4. **Bulk Operations** - Batch create/delete workflows
5. **Workflow Versioning** - Support for workflow versions
6. **Execution History** - Archive and analyze execution history
7. **Performance Metrics** - Track workflow performance and SLAs

## Deployment Checklist

- [ ] Ensure `workflow-core:8070` service is running
- [ ] Verify `WORKFLOW_CORE_URL` environment variable is set correctly
- [ ] Confirm communities table has license fields
- [ ] Test license validation with valid/invalid licenses
- [ ] Verify authentication and authorization for each endpoint
- [ ] Monitor workflow-core service connectivity
- [ ] Set up log aggregation for audit trails
- [ ] Test all CRUD, execution, and webhook operations
