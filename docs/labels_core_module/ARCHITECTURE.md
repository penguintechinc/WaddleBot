# Labels Core Module - Architecture

## Overview

The Labels Core Module provides universal label management for Waddles, enabling flexible categorization and tagging of any entity type across the platform.

**Technology Stack**:
- **Framework**: Quart (async Python web framework)
- **Database**: PostgreSQL with pyDAL ORM
- **Architecture**: REST API microservice
- **Logging**: AAA (Audit, Access, Activity) logging via flask_core

---

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Labels Core Module                      │
│                     (Port 8023)                          │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐      ┌──────────────────────┐        │
│  │  Health/     │      │   API Blueprint       │        │
│  │  Metrics     │      │   (/api/v1)          │        │
│  │  Endpoints   │      │                       │        │
│  └──────────────┘      │  - Label CRUD         │        │
│                        │  - Label Assignment   │        │
│                        │  - Entity Queries     │        │
│                        │  - Search             │        │
│                        └──────────────────────┘        │
│                                 │                        │
│                                 ▼                        │
│                        ┌──────────────────────┐        │
│                        │   Database Layer      │        │
│                        │   (pyDAL)             │        │
│                        │                       │        │
│                        │  - labels table       │        │
│                        │  - entity_labels      │        │
│                        └──────────────────────┘        │
└─────────────────────────────────────────────────────────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │   PostgreSQL Database  │
                    └────────────────────────┘
```

---

## Core Components

### 1. Application Layer (`app.py`)

**Responsibilities**:
- HTTP request handling
- Route registration
- Database initialization
- Startup/shutdown lifecycle

**Key Features**:
- Async endpoint decorators
- Health check endpoints
- AAA logging integration
- Error handling with standard responses

### 2. Data Models

#### LabelInfo Dataclass
```python
@dataclass
class LabelInfo:
    id: int
    name: str
    category: str
    description: str
    color: str
    icon: Optional[str]
    is_system: bool
    created_by: str
    created_at: str
    is_active: bool
```

#### EntityLabelInfo Dataclass
```python
@dataclass
class EntityLabelInfo:
    id: int
    entity_id: str
    entity_type: str
    label_id: int
    label_name: str
    label_color: str
    label_icon: Optional[str]
    applied_by: str
    applied_at: str
    expires_at: Optional[str]
    metadata: Dict[str, Any]
```

### 3. Database Schema

#### labels Table
- Primary storage for label definitions
- Supports soft deletes via `is_active`
- Category field links to entity types
- System flag protects critical labels

#### entity_labels Table
- Junction table for label assignments
- Supports expiration via `expires_at`
- Flexible metadata in JSON field
- Community context for multi-tenant support

### 4. API Endpoints

**Label Management**:
- `GET /labels`: List/filter labels
- `POST /labels`: Create label
- `GET /labels/{id}`: Get specific label
- `PUT /labels/{id}`: Update label
- `DELETE /labels/{id}`: Soft delete label

**Label Assignment**:
- `POST /labels/apply`: Apply label(s) to entity
- `POST /labels/remove`: Remove label from entity
- `GET /entity/{type}/{id}/labels`: Get entity labels

**Search**:
- `GET /labels/search`: Search entities by labels

---

## Data Flow

### Creating a Label

```
1. Client → POST /labels
2. Validate request data
3. Check entity type is supported
4. Check for duplicate label name in category
5. Insert into labels table
6. Commit transaction
7. Log audit event
8. Return label ID
```

### Applying a Label

```
1. Client → POST /labels/apply
2. Validate entity_id, entity_type, label_id
3. Check label exists
4. Check entity type is valid
5. Check label limit for entity type
6. Check for existing assignment
7. Parse optional expires_at
8. Insert into entity_labels
9. Commit transaction
10. Log audit event
11. Return assignment ID
```

### Searching by Labels

```
1. Client → GET /labels/search?entity_type=user&labels=VIP,Premium
2. Validate entity type
3. Parse comma-separated label names
4. Lookup label IDs from names
5. Query entity_labels for matching labels
6. Group results by entity_id
7. Apply match_all filter if requested
8. Return paginated results
```

---

## Entity Type System

### Extensible Design

The module supports any entity type via the `ENTITY_TYPES` list:

```python
ENTITY_TYPES = [
    'user', 'module', 'community', 'entityGroup',
    'item', 'event', 'memory', 'playlist',
    'browser_source', 'command', 'alias'
]
```

**Adding New Types**:
1. Add type to `ENTITY_TYPES` list
2. Define label limit in `LABEL_LIMITS`
3. No schema changes required

### Entity Identification

Entities are identified by:
- `entity_id`: Unique identifier (string, max 255 chars)
- `entity_type`: Type from `ENTITY_TYPES`

Example:
- `entity_id="user_12345"`, `entity_type="user"`
- `entity_id="playlist_abc123"`, `entity_type="playlist"`

---

## Label Limits Enforcement

```python
LABEL_LIMITS = {
    'community': 5,
    'user': 5,
    'item': 10,
    'event': 5,
    'memory': 10,
    'default': 5
}
```

**Enforcement Flow**:
1. Check current label count for entity
2. Compare against limit for entity type
3. If limit reached, return 400 error
4. Otherwise, proceed with assignment

---

## Bulk Operations

### Architecture

Bulk label application processes up to 1000 assignments in a single request:

```python
async def apply_labels_bulk(label_applications: List[Dict]):
    results = []
    for app in label_applications:
        try:
            # Validate and apply
            entity_label_id = dal.entity_labels.insert(...)
            results.append({'success': True, 'entity_label_id': entity_label_id})
        except Exception as e:
            results.append({'success': False, 'error': str(e)})

    dal.commit()  # Single commit for all operations
    return results
```

**Benefits**:
- Single database transaction
- Partial success handling
- Detailed result reporting

---

## Soft Delete Pattern

All deletions are soft deletes using `is_active` flag:

```python
# Delete label
dal(dal.labels.id == label_id).update(is_active=False)

# Delete all assignments
dal(dal.entity_labels.label_id == label_id).update(is_active=False)
```

**Benefits**:
- Audit trail preservation
- Reversible operations
- Historical data retention

**Queries always filter**:
```python
query = dal.labels.is_active == True
```

---

## Multi-Tenancy Support

Labels support multi-tenant architecture via `community_id`:

```python
entity_labels:
    community_id: "community_456"  # Optional context
```

**Use Cases**:
- User labels scoped to specific communities
- Community-specific label sets
- Cross-community label search

---

## Expiration Handling

Labels can expire automatically:

```python
entity_labels:
    expires_at: "2025-12-31T23:59:59Z"
```

**Implementation Notes**:
- Expiration is NOT automatically enforced
- Requires periodic cleanup job
- Query time filtering recommended

**Example Cleanup**:
```sql
UPDATE entity_labels
SET is_active = false
WHERE expires_at < NOW() AND is_active = true
```

---

## Integration Points

### Upstream Dependencies
- **Router Service**: Service discovery and routing
- **PostgreSQL**: Data persistence

### Downstream Consumers
- Any module needing entity categorization
- Admin interfaces for label management
- Search/filter features

---

## Error Handling

All endpoints use standard response format from `flask_core`:

**Success**:
```python
success_response({"data": ...}, status_code=200)
```

**Error**:
```python
error_response("Error message", status_code=400)
```

**Exception Handling**:
```python
try:
    # Operation
except Exception as e:
    logger.error(f"Error: {e}")
    return error_response(str(e), 500)
```

---

## Logging Architecture

Uses AAA logging from `flask_core`:

```python
logger = setup_aaa_logging(Config.MODULE_NAME, Config.MODULE_VERSION)

# Audit events
logger.audit("Label created", user=created_by, action="create_label", result="SUCCESS")

# Errors
logger.error(f"Error message: {e}")

# System events
logger.system("Module started", action="startup", result="SUCCESS")
```

**Log Levels**:
- `DEBUG`: Detailed debug information
- `INFO`: General informational messages
- `WARNING`: Warning messages
- `ERROR`: Error conditions
- `AUDIT`: Audit trail events
- `SYSTEM`: System lifecycle events

---

## Performance Considerations

### Database Optimization
1. **Indexes**: Create indexes on frequently queried fields
2. **Joins**: Use left joins for entity label queries
3. **Pagination**: Support limit/offset for large result sets

### Query Patterns
1. **Label lookup**: O(1) by ID, O(log n) by name with index
2. **Entity labels**: O(1) with entity_id + entity_type index
3. **Search**: O(n) for label matching, optimized with indexes

### Scalability
- Horizontal scaling: Stateless API design
- Database pooling: Multiple connections
- Caching layer: Add Redis for hot labels

---

## Security Architecture

### Protection Mechanisms
1. **System labels**: Cannot be modified/deleted (`is_system` check)
2. **Entity type validation**: Whitelist enforcement
3. **Input sanitization**: String trimming and validation
4. **SQL injection**: Protected by pyDAL ORM
5. **Audit logging**: All changes tracked

### Access Control
- Implemented at application layer
- `created_by` and `applied_by` fields track actors
- Integration with Waddles authentication system

---

## Future Enhancements

1. **Label hierarchies**: Parent-child relationships
2. **Label groups**: Mutually exclusive label sets
3. **Auto-expiration**: Background worker for cleanup
4. **Label templates**: Pre-defined label sets
5. **Analytics**: Label usage statistics
6. **Permissions**: Fine-grained access control per label
