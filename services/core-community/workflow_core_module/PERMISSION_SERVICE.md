# Workflow Permission Service

## Overview

The `PermissionService` provides granular, role-based access control for workflows in the WaddleBot system. It manages permissions at three levels:

- **User-level**: Specific permissions for individual users
- **Role-level**: Group-based permissions through roles
- **Entity-level**: Organization-wide permissions

## Architecture

### Database Table Structure

The service uses the `workflow_permissions` table:

```sql
CREATE TABLE workflow_permissions (
    id SERIAL PRIMARY KEY,
    workflow_id UUID NOT NULL REFERENCES workflows(workflow_id),
    permission_type VARCHAR(50) NOT NULL,  -- user, role, entity
    target_id INTEGER NOT NULL,
    can_view BOOLEAN NOT NULL DEFAULT false,
    can_edit BOOLEAN NOT NULL DEFAULT false,
    can_execute BOOLEAN NOT NULL DEFAULT false,
    can_delete BOOLEAN NOT NULL DEFAULT false,
    can_manage_permissions BOOLEAN NOT NULL DEFAULT false,
    granted_by INTEGER,
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (workflow_id, permission_type, target_id)
);
```

## Permission Types

### Granular Permissions

| Permission | Description |
|------------|-------------|
| `can_view` | View workflow details, definition, and execution history |
| `can_edit` | Modify workflow definition, settings, and configuration |
| `can_execute` | Trigger workflow execution manually |
| `can_delete` | Delete the workflow and associated data |
| `can_manage_permissions` | Grant/revoke permissions for other users |

### Permission Targets

| Target Type | Description | Examples |
|------------|-------------|----------|
| `user` | Specific user by `user_id` | Grant permission to user ID 123 |
| `role` | Role-based access by `role_id` | Grant permission to "moderator" role |
| `entity` | Organization-wide by `entity_id` | Grant to entire entity/team |

## Core Methods

### 1. check_permission()

Check if a user has a specific permission for a workflow.

```python
async def check_permission(
    workflow_id: str,
    user_id: int,
    permission_type: str,
    community_id: int = None,
) -> bool:
```

**Parameters:**
- `workflow_id`: UUID of the workflow
- `user_id`: Hub user ID to check
- `permission_type`: One of the granular permissions
- `community_id`: Optional context (for logging)

**Returns:** `True` if user has permission, `False` otherwise

**Example:**
```python
can_edit = await permission_service.check_permission(
    workflow_id="550e8400-e29b-41d4-a716-446655440000",
    user_id=42,
    permission_type="can_edit",
    community_id=1
)
```

**Permission Resolution:**
1. Owner check: Workflow creator has all permissions automatically
2. User-level: Direct user permission
3. Role-level: Check user's roles in the community
4. Entity-level: Check organization-wide permissions

### 2. grant_permission()

Grant permissions to a user, role, or entity.

```python
async def grant_permission(
    workflow_id: str,
    target_type: str,
    target_id: int,
    permissions_dict: Dict[str, bool],
    granted_by: int = None,
) -> GrantResult:
```

**Parameters:**
- `workflow_id`: UUID of the workflow
- `target_type`: One of `user`, `role`, `entity`
- `target_id`: ID of the target (user_id, role_id, or entity_id)
- `permissions_dict`: Dictionary mapping permission names to booleans
- `granted_by`: User ID granting the permission (for audit logging)

**Returns:** `GrantResult` with success status

**Example:**
```python
result = await permission_service.grant_permission(
    workflow_id="550e8400-e29b-41d4-a716-446655440000",
    target_type="user",
    target_id=42,
    permissions_dict={
        "can_view": True,
        "can_edit": True,
        "can_execute": True,
        "can_delete": False,
        "can_manage_permissions": False,
    },
    granted_by=1
)

if result.success:
    print(f"✓ {result.message}")
else:
    print(f"✗ Error: {result.error}")
```

### 3. revoke_permission()

Revoke all permissions for a target on a workflow.

```python
async def revoke_permission(
    workflow_id: str,
    target_type: str,
    target_id: int,
    revoked_by: int = None,
) -> GrantResult:
```

**Parameters:**
- `workflow_id`: UUID of the workflow
- `target_type`: One of `user`, `role`, `entity`
- `target_id`: ID of the target
- `revoked_by`: User ID revoking the permission (for audit)

**Returns:** `GrantResult` with success status

**Example:**
```python
result = await permission_service.revoke_permission(
    workflow_id="550e8400-e29b-41d4-a716-446655440000",
    target_type="user",
    target_id=42,
    revoked_by=1
)
```

### 4. get_user_permissions()

Get all permissions a user has for a workflow (aggregated).

```python
async def get_user_permissions(
    workflow_id: str,
    user_id: int,
    community_id: int = None,
) -> PermissionInfo:
```

**Parameters:**
- `workflow_id`: UUID of the workflow
- `user_id`: Hub user ID
- `community_id`: Optional context

**Returns:** `PermissionInfo` dataclass with all permission flags

**Example:**
```python
perms = await permission_service.get_user_permissions(
    workflow_id="550e8400-e29b-41d4-a716-446655440000",
    user_id=42
)

print(f"Can view: {perms.can_view}")
print(f"Can edit: {perms.can_edit}")
print(f"Can execute: {perms.can_execute}")

# Convert to dict
perms_dict = perms.to_dict()

# Check if any permissions granted
if perms:
    print("User has at least one permission")
```

### 5. list_workflows_for_user()

List all workflows a user can access with a specific permission.

```python
async def list_workflows_for_user(
    user_id: int,
    entity_id: int,
    permission: str = "view",
    community_id: int = None,
) -> List[str]:
```

**Parameters:**
- `user_id`: Hub user ID
- `entity_id`: Entity ID for context
- `permission`: Permission type to filter (default: `can_view`)
- `community_id`: Optional context

**Returns:** List of workflow UUIDs accessible to the user

**Example:**
```python
workflows = await permission_service.list_workflows_for_user(
    user_id=42,
    entity_id=1,
    permission="can_edit"
)

print(f"User can edit {len(workflows)} workflows")
for workflow_id in workflows:
    print(f"  - {workflow_id}")
```

## Data Classes

### PermissionInfo

Holds permission flags for a user on a workflow.

```python
@dataclass(slots=True)
class PermissionInfo:
    can_view: bool = False
    can_edit: bool = False
    can_execute: bool = False
    can_delete: bool = False
    can_manage_permissions: bool = False

    def to_dict(self) -> Dict[str, bool]: ...
    def has_any_permission(self) -> bool: ...
    def __bool__(self) -> bool: ...
```

### GrantResult

Result of a permission operation (grant or revoke).

```python
@dataclass(slots=True)
class GrantResult:
    success: bool
    message: str
    workflow_id: Optional[str] = None
    target_type: Optional[str] = None
    target_id: Optional[int] = None
    error: Optional[str] = None
```

## Permission Resolution Logic

The service uses the following permission resolution strategy:

### 1. Owner Bypass
If the user is the workflow creator (`workflows.created_by`), they automatically have all permissions.

### 2. Permission Aggregation (OR Logic)
Permissions are aggregated using OR logic. A user has a permission if:
- They are the owner, OR
- They have user-level permission, OR
- Any of their roles have the permission, OR
- The entity has the permission

### 3. Role Inheritance
Roles are looked up from the `user_roles` table:
```sql
SELECT role_id FROM user_roles WHERE user_id = ? AND community_id = ?
```

### 4. Entity-Level Permissions
Entity-level permissions apply to all workflows in an entity. They are checked via:
```sql
SELECT ... FROM workflow_permissions
WHERE permission_type = 'entity' AND target_id = workflows.entity_id
```

## AAA Logging

The service implements comprehensive Authentication, Authorization, and Audit (AAA) logging:

### Authentication (AUTH)
- User identity validation during permission checks

### Authorization (AUTHZ)
- Permission grants/revokes
- Permission checks (allowed/denied)
- Access to workflow lists

### Audit (AUDIT)
- All permission changes
- Who granted/revoked permissions
- When permissions were modified

**Log Format:**
```
[timestamp] LEVEL module:version EVENT_TYPE community=X user=Y action=Z result=STATUS [additional_fields]
```

**Example Logs:**
```
[2025-12-09 10:23:45.123] INFO workflow_core_module:1.0.0 AUTHZ community=1 user=42 action=check_permission result=ALLOWED workflow_id=550e8400-e29b-41d4-a716-446655440000 permission=can_edit
[2025-12-09 10:24:12.456] INFO workflow_core_module:1.0.0 AUDIT user=1 action=grant_permission result=SUCCESS workflow_id=550e8400-e29b-41d4-a716-446655440000 target_type=user target_id=42
```

## Usage Example

### Full Permission Management Workflow

```python
from flask_core import init_database, setup_aaa_logging
from core.workflow_core_module.services import PermissionService

# Initialize
dal = init_database("postgresql://...")
logger = setup_aaa_logging("workflow_core_module", "1.0.0")
perm_service = PermissionService(dal, logger)

workflow_id = "550e8400-e29b-41d4-a716-446655440000"

# 1. Grant a user edit permissions
result = await perm_service.grant_permission(
    workflow_id=workflow_id,
    target_type="user",
    target_id=42,
    permissions_dict={
        "can_view": True,
        "can_edit": True,
        "can_execute": False,
        "can_delete": False,
        "can_manage_permissions": False,
    },
    granted_by=1
)

# 2. Check if user can edit
can_edit = await perm_service.check_permission(
    workflow_id=workflow_id,
    user_id=42,
    permission_type="can_edit"
)
print(f"User can edit: {can_edit}")

# 3. Get all user permissions
perms = await perm_service.get_user_permissions(
    workflow_id=workflow_id,
    user_id=42
)
print(f"Permissions: {perms.to_dict()}")

# 4. Grant role-based permissions
result = await perm_service.grant_permission(
    workflow_id=workflow_id,
    target_type="role",
    target_id=5,  # e.g., "moderator" role
    permissions_dict={
        "can_view": True,
        "can_edit": False,
        "can_execute": True,
        "can_delete": False,
        "can_manage_permissions": False,
    },
    granted_by=1
)

# 5. Revoke user permissions
result = await perm_service.revoke_permission(
    workflow_id=workflow_id,
    target_type="user",
    target_id=42,
    revoked_by=1
)

# 6. List workflows user can edit
workflows = await perm_service.list_workflows_for_user(
    user_id=42,
    entity_id=1,
    permission="can_edit"
)
print(f"Workflows user can edit: {workflows}")
```

## Error Handling

The service handles errors gracefully:

1. **Invalid input validation**: Returns `False` or empty results
2. **Database errors**: Logs errors and returns safe defaults
3. **Missing data**: Returns `None` or empty lists
4. **Permission resolution**: Returns `False` for access checks

## Performance Considerations

### Query Optimization
- Uses indexed lookups on `workflow_id`, `permission_type`, and `target_id`
- Single query for workflow ownership check
- Separate queries for user, role, and entity permissions (can be cached)

### Caching Strategy (Recommended)
```python
# Cache permission checks for 5 minutes
@cache.cached(timeout=300, key_prefix="perm_check_{workflow_id}_{user_id}")
async def cached_check_permission(workflow_id, user_id, permission_type):
    return await perm_service.check_permission(...)
```

### Bulk Operations
For bulk permission grants, consider:
```python
# Grant same permission to multiple users
for user_id in user_ids:
    await perm_service.grant_permission(
        workflow_id=workflow_id,
        target_type="user",
        target_id=user_id,
        permissions_dict=permissions,
        granted_by=admin_id
    )
```

## Integration with Workflow Controllers

### Example Controller Usage

```python
from quart import request
from flask_core import auth_required, success_response, error_response
from core.workflow_core_module.services import PermissionService

@app.route('/api/v1/workflows/<workflow_id>/edit', methods=['PUT'])
@auth_required
async def edit_workflow(workflow_id):
    user_id = request.auth.user_id

    # Check edit permission
    has_edit = await perm_service.check_permission(
        workflow_id=workflow_id,
        user_id=user_id,
        permission_type="can_edit"
    )

    if not has_edit:
        return error_response(
            "FORBIDDEN",
            "You do not have permission to edit this workflow",
            403
        )

    # Proceed with edit
    # ...

    return success_response(data=workflow_data)
```

## Database Schema

The service operates on this schema:

**Table: workflow_permissions**
```
id                        SERIAL PRIMARY KEY
workflow_id              UUID NOT NULL (FK to workflows)
permission_type          VARCHAR(50) NOT NULL (user, role, entity)
target_id               INTEGER NOT NULL
can_view                BOOLEAN NOT NULL DEFAULT false
can_edit                BOOLEAN NOT NULL DEFAULT false
can_execute             BOOLEAN NOT NULL DEFAULT false
can_delete              BOOLEAN NOT NULL DEFAULT false
can_manage_permissions  BOOLEAN NOT NULL DEFAULT false
granted_by              INTEGER (user_id)
granted_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP

Indexes:
- idx_workflow_permissions_workflow_id
- idx_workflow_permissions_target
- UNIQUE (workflow_id, permission_type, target_id)
```

**Related Tables**
- `workflows`: Contains `created_by`, `entity_id`
- `user_roles`: Contains user role assignments
- `community_members`: For role lookups

## Future Enhancements

1. **Permission Inheritance**: Permissions inherit from parent workflows/templates
2. **Time-Limited Permissions**: Temporary access with expiration
3. **Delegation**: Users can temporarily delegate permissions
4. **Approval Workflow**: Permissions require approval before activation
5. **Permission Groups**: Pre-defined permission sets (viewer, editor, admin)
6. **Audit Trail**: Full change history for compliance

## Security Considerations

1. **Owner Check**: Always performed first to prevent bypasses
2. **Validation**: All inputs validated before database operations
3. **Logging**: All permission changes logged for audit trails
4. **SQL Injection**: Uses parameterized queries via AsyncDAL
5. **Authorization Checks**: Required at controller level and service level
6. **Role Lookup**: Includes community context to prevent cross-community access
