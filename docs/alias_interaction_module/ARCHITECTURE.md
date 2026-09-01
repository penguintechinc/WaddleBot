# Alias Interaction Module — Architecture

## System Overview

The Alias Interaction Module is a microservice component of the WaddleBot ecosystem designed to manage Linux-style command aliases with dynamic variable substitution. It operates as a stateless HTTP service with persistent storage in PostgreSQL.

```
External Clients (API Consumers)
        |
        | HTTP REST
        v
Alias Interaction Module (Quart Application)
  +----------------------------------+
  | Flask Blueprint: /api/v1         |
  | - GET /status                    |
  | - GET /aliases                   |
  | - POST /aliases                  |
  | - DELETE /aliases/<id>           |
  | - POST /aliases/execute          |
  +----------------------------------+
        |
        v
AliasService (Business Logic)
  - create_alias()
  - list_aliases()
  - delete_alias()
  - execute_alias()
        |
        v
PyDAL Data Access Layer
  - table: aliases
  - async operations
        |
        | SQL
        v
PostgreSQL Database
  Table: aliases
  - id (UUID)
  - community_id (VARCHAR)
  - alias_name (VARCHAR)
  - command (TEXT)
  - created_by (VARCHAR)
  - created_at (TIMESTAMP)
  - usage_count (INTEGER)
  - is_active (BOOLEAN)
```

## Core Components

### 1. Quart Application (app.py)

**Role:** HTTP request handling and endpoint routing

**Key Classes & Functions:**
- `app = Quart(__name__)` - Async Flask-compatible framework
- `@app.before_serving` - Startup lifecycle hook
- `health_bp` - Health check blueprint
- `api_bp` - API Blueprint with URL prefix `/api/v1`

**Endpoints:**
```
GET  /health                      - Standard health check
GET  /metrics                     - Prometheus metrics
GET  /api/v1/status              - Module status
GET  /api/v1/aliases             - List aliases
POST /api/v1/aliases             - Create alias
DELETE /api/v1/aliases/<id>      - Delete alias
POST /api/v1/aliases/execute     - Execute with substitution
```

**Request Flow:**
1. Client sends HTTP request
2. Quart routes to appropriate handler
3. Handler calls AliasService method
4. Response formatted using `success_response()` or `error_response()`
5. JSON envelope returned to client

### 2. AliasService (services/alias_service.py)

**Role:** Business logic and alias operations

**Key Methods:**

#### create_alias(community_id, alias_name, command, created_by)
- Inserts new record into aliases table
- Returns alias object with ID
- Database: `INSERT INTO aliases VALUES (...)`

#### list_aliases(community_id)
- Queries all active aliases for community
- Filters: `community_id == X AND is_active == TRUE`
- Returns list of alias dictionaries

#### delete_alias(alias_id)
- Soft deletes by setting `is_active = FALSE`
- Preserves historical data
- Database: `UPDATE aliases SET is_active = FALSE WHERE id = X`

#### execute_alias(alias_name, user, args)
- Fetches alias command from database
- Performs variable substitution:
  - {user} becomes parameter value
  - {args} becomes joined args list
  - {arg1}, {arg2} become individual args
  - {all_args} becomes same as {args}
- Increments usage_count
- Returns expanded command string

**Variable Substitution Algorithm:**
```python
substitutions = {
    '{user}': user,
    '{args}': ' '.join(args) if args else '',
    '{arg1}': args[0] if len(args) > 0 else '',
    '{arg2}': args[1] if len(args) > 1 else '',
    '{all_args}': ' '.join(args) if args else ''
}

for var, value in substitutions.items():
    command = command.replace(var, value)
```

### 3. Configuration (config.py)

**Role:** Environment variable management and credentials

**Key Configuration Items:**
- `MODULE_NAME = 'alias_interaction_module'`
- `MODULE_VERSION = '2.0.0'`
- `MODULE_PORT = 8010` (default)
- `DATABASE_URL` - PostgreSQL connection string
- `CORE_API_URL` - Router service base URL
- `REDIS_URL` - Optional Redis for credential events

**Credential Management:**
- `load_credentials_from_db()` - Loads from platform_integrations table
- `start_credential_listener()` - Background Redis listener
- Thread-safe credential state with `_credential_lock`

**Environment Variable Hierarchy:**
1. OS environment variables (highest priority)
2. .env file (via dotenv)
3. Hardcoded defaults (lowest priority)

### 4. Database Schema

**Table: aliases**

```sql
CREATE TABLE aliases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    community_id VARCHAR(255) NOT NULL,
    alias_name VARCHAR(255) NOT NULL,
    command TEXT NOT NULL,
    created_by VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    usage_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    
    UNIQUE (community_id, alias_name)
);

CREATE INDEX idx_aliases_community ON aliases(community_id, is_active);
CREATE INDEX idx_aliases_name ON aliases(alias_name, is_active);
```

**Key Constraints:**
- `UNIQUE (community_id, alias_name)` - No duplicate names per community
- `is_active` flag enables soft deletion
- Indexes on community_id for fast community-scoped queries

## Data Flow

### Create Alias Flow

```
Client
  ├─ POST /api/v1/aliases
  │  ├─ Headers: Content-Type: application/json
  │  └─ Body: {community_id, alias_name, command, created_by}
  │
  ├─ @async_endpoint decorator
  │  └─ Async context setup
  │
  ├─ route handler: aliases()
  │  └─ Parse JSON from request
  │
  ├─ AliasService.create_alias()
  │  ├─ Validation checks
  │  └─ Database INSERT
  │     └─ INSERT INTO aliases(community_id, alias_name, command, ...)
  │
  └─ Response
     ├─ Status: 201 Created
     └─ Body: {data: {id, alias_name, command, ...}}
```

### Execute Alias Flow

```
Client
  ├─ POST /api/v1/aliases/execute
  │  ├─ Headers: Content-Type: application/json
  │  └─ Body: {alias_name, user, args}
  │
  ├─ route handler: execute_alias()
  │  └─ Parse JSON from request
  │
  ├─ AliasService.execute_alias()
  │  ├─ Database SELECT
  │  │  └─ SELECT command FROM aliases
  │  │     WHERE alias_name = X AND is_active = TRUE
  │  │
  │  ├─ Variable Substitution Loop
  │  │  ├─ Replace {user} with parameter value
  │  │  ├─ Replace {arg1}, {arg2} with positional args
  │  │  └─ Replace {all_args} with joined args
  │  │
  │  ├─ Database UPDATE (usage_count++)
  │  │  └─ UPDATE aliases SET usage_count = usage_count + 1
  │  │
  │  └─ Response
  │     ├─ Status: 200 OK
  │     └─ Body: {data: {command: expanded command string}}
```

## Async Architecture

The module uses Python async/await pattern throughout:

```python
# Quart request handlers are async
@api_bp.route('/aliases', methods=['GET', 'POST'])
@async_endpoint
async def aliases():
    # async_endpoint is from flask_core library
    # Enables async/await in Flask-style handlers

# AliasService methods are async
async def create_alias(self, community_id, alias_name, command, created_by):
    alias_id = await self.dal.insert_async(...)
    return {"id": alias_id, ...}

# Startup is async
@app.before_serving
async def startup():
    dal = init_database(Config.DATABASE_URL)
    alias_service = AliasService(dal)
```

**Benefits:**
- Non-blocking I/O for database queries
- High concurrency with limited threads
- Efficient resource utilization
- Scales to thousands of concurrent connections

## Integration Points

### Flask Core Library
Located at `libs/flask_core`, provides:
- `setup_aaa_logging()` - Standardized logging
- `init_database()` - Database connection factory
- `async_endpoint` - Async decorator for handlers
- `success_response()` / `error_response()` - Response formatters
- `create_health_blueprint()` - Health check endpoints

### Router Service
Optional integration via `CORE_API_URL`:
- Could delegate complex command routing
- Enables action chaining
- Configurable via environment variable

### PostgreSQL
Primary data persistence:
- ACID transactions
- Connection pooling via PyDAL
- Full-text search capabilities (future)

### Redis (Optional)
Credential refresh notifications:
- Pub/sub channel: `credentials:alias_interaction:bot:refreshed`
- Background listener thread
- Signals credential reload

## Performance Characteristics

**Latency:**
- List aliases: approximately 10-50ms (depends on alias count)
- Create alias: approximately 5-20ms
- Execute alias: approximately 10-30ms (includes usage count update)
- Health check: less than 5ms

**Throughput:**
- Single instance: approximately 1000 req/sec (4 workers)
- Horizontal scaling: Linear with instance count
- Database: Connection pooling at 20 concurrent connections

**Resource Usage:**
- Memory: approximately 50MB base plus 10MB per active connection
- CPU: Minimal when idle, scales with request rate
- Database connections: 4-20 per instance

## Security Architecture

**Data Isolation:**
- Community-scoped aliases prevent cross-contamination
- SQL queries filter by community_id
- No global aliases across communities

**Access Control:**
- No built-in authentication (implement via gateway)
- Credentials in database/environment only
- No hardcoded secrets in code

**Input Validation:**
- Flask/Quart automatic JSON validation
- Type hints in AliasService
- Database constraints (UNIQUE, NOT NULL)

**Audit Trail:**
- `created_by` field tracks alias creators
- `created_at` timestamp
- `usage_count` for analytics
- Soft delete preserves history

## Deployment Architecture

**Container Image:**
- Base: `python:3.12-slim`
- Non-root user: `waddlebot`
- Log directory: `/var/log/waddlebotlog`
- Working directory: `/app`

**Process Model:**
- Hypercorn ASGI server
- 4 worker processes (configurable)
- No threading (Python async instead)

**Health Checks:**
- HTTP GET /health
- 30s interval
- 3 retries before restart

**Scaling:**
- Stateless design enables horizontal scaling
- Load balance traffic across instances
- Shared PostgreSQL backend
- Optional Redis for credential sync

## Dependency Graph

```
alias_interaction_module
├── quart>=0.19.0
├── hypercorn>=0.16.0
├── httpx>=0.27.0
├── python-dotenv>=1.0.0
└── libs/flask_core
    ├── Flask
    ├── pydal
    ├── python-dotenv
    └── (development: pytest, pytest-asyncio)
```

## Error Handling

**Strategy:**
- Exceptions caught at request handler level
- Errors formatted as `error_response()`
- HTTP status codes match error type:
  - 400 - Invalid input
  - 404 - Not found
  - 409 - Conflict (duplicate)
  - 500 - Database/server error

**Logging:**
- All operations logged via flask_core logger
- Log level configurable via `LOG_LEVEL` env var
- Request ID tracking for debugging

## Future Enhancements

1. **Caching** - Redis cache for frequently used aliases
2. **Rate Limiting** - Per-community, per-user quotas
3. **Audit Logging** - Detailed execution audit trail
4. **Alias Chaining** - Support alias-in-alias references
5. **Advanced Substitution** - Regex, conditional logic
6. **API Versioning** - Backward compatible evolution
7. **Webhook Support** - Trigger external systems on execution
8. **Analytics** - Usage dashboards and trends
