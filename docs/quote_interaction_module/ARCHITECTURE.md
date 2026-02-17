# Quote Interaction Module - Architecture

## System Architecture

The Quote Interaction Module follows a layered architecture with clear separation of concerns:

```
┌─────────────────────────────────────┐
│      HTTP Clients (Web, API)        │
└────────────────┬────────────────────┘
                 │
┌─────────────────▼────────────────────┐
│    Quart Application Layer           │
│  - Route handling                    │
│  - Request/response serialization    │
│  - Error handling                    │
│  - Async endpoint decorators         │
└────────────────┬────────────────────┘
                 │
┌─────────────────▼────────────────────┐
│    Quote Service Layer               │
│  - Business logic                    │
│  - Query orchestration               │
│  - Data transformation               │
│  - Validation                        │
└────────────────┬────────────────────┘
                 │
┌─────────────────▼────────────────────┐
│    AsyncDAL Database Layer           │
│  - Connection pooling                │
│  - Query execution                   │
│  - Parameter binding                 │
│  - Read replica support              │
└────────────────┬────────────────────┘
                 │
┌─────────────────▼────────────────────┐
│   PostgreSQL Database                │
│  - Quote storage                     │
│  - Full-text search indices          │
│  - ACID transactions                 │
└─────────────────────────────────────┘
```

## Component Breakdown

### 1. Quart Application (app.py)

**Purpose:** HTTP request/response handling and routing

**Key Responsibilities:**
- Endpoint route definitions
- Request parameter validation
- Response formatting (success/error)
- Async request handling
- Health check endpoints
- Module status reporting

**Key Functions:**
- `startup()` - Initialize database and services on server start
- `add_quote()` - POST /api/v1/quotes
- `get_quote()` - GET /api/v1/quotes/<id>
- `get_random_quote()` - GET /api/v1/quotes/random/<community_id>
- `list_quotes()` - GET /api/v1/quotes/list/<community_id>
- `search_quotes()` - GET /api/v1/quotes/search/<community_id>
- `get_by_author()` - GET /api/v1/quotes/author/<community_id>
- `update_quote()` - PUT /api/v1/quotes/<id>
- `delete_quote()` - DELETE /api/v1/quotes/<id>
- `get_stats()` - GET /api/v1/quotes/stats/<community_id>

**Dependencies:**
- Quart framework
- flask_core (AAA logging, health blueprint)
- Quote Service
- AsyncDAL

### 2. Quote Service (services/quote_service.py)

**Purpose:** Core business logic and data operations

**Key Responsibilities:**
- Quote CRUD operations
- Search query execution
- Author filtering logic
- Statistics calculation
- Data normalization
- Error handling and logging

**Key Methods:**

| Method | Purpose | Complexity |
|--------|---------|-----------|
| `add_quote()` | Create new quote | O(1) |
| `get_quote()` | Fetch single quote | O(1) |
| `get_random_quote()` | Get random approved quote | O(1) |
| `get_quotes()` | List paginated quotes | O(k) |
| `search_quotes()` | Full-text search | O(log n) |
| `get_quotes_by_author()` | Filter by author | O(n) |
| `update_quote()` | Modify quote | O(1) |
| `delete_quote()` | Soft-delete quote | O(1) |
| `get_quote_count()` | Count quotes | O(1) |
| `get_quote_stats()` | Aggregate statistics | O(n) |
| `_row_to_dict()` | Format database row | O(1) |

**Error Handling:**
- Validates required fields before database operations
- Catches and logs all database exceptions
- Re-raises exceptions for endpoint error handling
- Provides descriptive error messages

### 3. Configuration (config.py)

**Purpose:** Centralized configuration and environment management

**Key Features:**
- Environment variable loading with defaults
- Database connection configuration
- API settings (timeout, pagination limits)
- Search configuration (language, min length)
- Moderation settings (auto-approval)
- Credential management
- Thread-safe credential updates

**Configuration Class Fields:**
```python
MODULE_NAME = 'quote_interaction_module'
MODULE_PORT = 5012
DATABASE_URL = <postgresql connection string>
READ_REPLICA_URL = <optional read replica>
DB_POOL_SIZE = 10
API_TIMEOUT = 30
MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 50
SEARCH_LANGUAGE = 'english'
MIN_SEARCH_QUERY_LENGTH = 2
AUTO_APPROVE_QUOTES = true
LOG_LEVEL = 'INFO'
```

**Credential Management:**
- `load_credentials_from_db()` - Load from platform_integrations table
- `start_credential_listener()` - Listen for Redis refresh notifications
- Thread-safe credential updates with locks

## Data Flow Diagrams

### Create Quote Flow

```
POST /api/v1/quotes (with quote data)
  │
  ├─ Validate required fields (community_id, text)
  │
  ├─ Call quote_service.add_quote()
  │   │
  │   ├─ Generate SQL INSERT statement
  │   │
  │   ├─ Execute via AsyncDAL.execute()
  │   │   │
  │   │   └─ PostgreSQL INSERT & RETURNING
  │   │
  │   ├─ Format result as dict
  │   │
  │   └─ Return quote object
  │
  └─ Return 201 Created with quote data
```

### Search Quote Flow

```
GET /api/v1/quotes/search/{community_id}?q=keyword
  │
  ├─ Validate query length (>= 2 chars)
  │
  ├─ Call quote_service.search_quotes()
  │   │
  │   ├─ Count results with plainto_tsquery()
  │   │   └─ SELECT COUNT(*) WHERE search_vector @@ query
  │   │
  │   ├─ Get paginated results with ranking
  │   │   └─ SELECT * ORDER BY ts_rank() DESC
  │   │
  │   ├─ Format each row to dict
  │   │
  │   └─ Return (quotes_list, total_count)
  │
  ├─ Merge pagination metadata
  │
  └─ Return 200 OK with results
```

### Get Random Quote Flow

```
GET /api/v1/quotes/random/{community_id}
  │
  ├─ Call quote_service.get_random_quote()
  │   │
  │   ├─ SELECT * WHERE is_approved=TRUE ORDER BY RANDOM()
  │   │
  │   ├─ Format result as dict
  │   │
  │   └─ Return quote object (or None)
  │
  ├─ Check if quote exists
  │   ├─ If yes: return 200 OK
  │   └─ If no: return 404 Not Found
  │
  └─ Return quote data
```

## Database Schema

**Table Name:** `quotes`

**Columns:**

| Column | Type | Constraints | Description |
|--------|------|-----------|-------------|
| id | SERIAL | PRIMARY KEY | Unique quote identifier |
| community_id | INTEGER | NOT NULL | Community ownership |
| quote_text | TEXT | NOT NULL | The quote content |
| quoted_user_id | INTEGER | - | User being quoted |
| quoted_username | VARCHAR(255) | - | Author name |
| added_by_user_id | INTEGER | - | User who submitted |
| platform | VARCHAR(50) | - | Origin platform |
| context | TEXT | - | Additional context |
| tags | TEXT[] | - | Array of tags |
| is_approved | BOOLEAN | DEFAULT TRUE | Approval status |
| search_vector | TSVECTOR | GENERATED | Full-text index |
| created_at | TIMESTAMP | NOT NULL | Creation timestamp |
| updated_at | TIMESTAMP | NOT NULL | Last update timestamp |
| deleted_at | TIMESTAMP | - | Soft-delete marker |

**Indices:**
```sql
-- Full-text search index
CREATE INDEX idx_quotes_search_vector ON quotes USING GIN(search_vector);

-- Community queries
CREATE INDEX idx_quotes_community_id ON quotes(community_id, deleted_at);

-- Approval filtering
CREATE INDEX idx_quotes_approved ON quotes(community_id, is_approved) 
  WHERE deleted_at IS NULL;

-- Author searches
CREATE INDEX idx_quotes_author ON quotes(community_id, quoted_username)
  WHERE deleted_at IS NULL;

-- Random selection
CREATE INDEX idx_quotes_random ON quotes(community_id, is_approved, created_at)
  WHERE deleted_at IS NULL;
```

**Constraints:**
```sql
-- Community isolation
ALTER TABLE quotes ADD CONSTRAINT fk_quotes_community 
  FOREIGN KEY (community_id) REFERENCES communities(id);

-- Data integrity
ALTER TABLE quotes ADD CONSTRAINT ck_quote_text_not_empty 
  CHECK (LENGTH(TRIM(quote_text)) > 0);
```

## Query Performance Analysis

### Full-Text Search (search_quotes)

**Query:**
```sql
SELECT * FROM quotes
WHERE community_id = ? AND deleted_at IS NULL
  AND search_vector @@ plainto_tsquery('english', ?)
ORDER BY ts_rank(search_vector, plainto_tsquery('english', ?)) DESC
LIMIT ? OFFSET ?
```

**Performance:** O(log n) with GIN index on search_vector
**Typical Response Time:** <50ms for communities with <100k quotes

### Author Search (get_quotes_by_author)

**Query:**
```sql
SELECT * FROM quotes
WHERE community_id = ? AND deleted_at IS NULL
  AND quoted_username ILIKE ?
ORDER BY created_at DESC
LIMIT ? OFFSET ?
```

**Performance:** O(n) - sequential scan with case-insensitive matching
**Typical Response Time:** 10-200ms depending on author name popularity

### Random Quote (get_random_quote)

**Query:**
```sql
SELECT * FROM quotes
WHERE community_id = ? AND deleted_at IS NULL AND is_approved = TRUE
ORDER BY RANDOM()
LIMIT 1
```

**Performance:** O(1) with index on (community_id, is_approved)
**Typical Response Time:** <10ms

## Concurrency Model

The module uses async/await throughout for high concurrency:

```python
async def search_quotes(self, community_id, query, limit, offset):
    # Count results
    count_result = await self.dal.execute(count_sql, params)
    
    # Get paginated results
    results = await self.dal.execute(search_sql, params)
    
    # Both operations can run in parallel if needed
    return quotes, total_count
```

**Benefits:**
- Non-blocking I/O - thousands of concurrent requests
- Connection pooling - max 10 concurrent database connections
- Async database driver - efficient resource usage

## Dependency Tree

```
quote_interaction_module/
  ├── Quart (async web framework)
  │   └── asyncio
  ├── flask_core (shared utilities)
  │   ├── AAA logging
  │   └── Health/metrics blueprints
  ├── AsyncDAL (database layer)
  │   └── psycopg2 (PostgreSQL driver)
  ├── hypercorn (ASGI server)
  │   └── asyncio
  └── Python standard library
      ├── logging
      ├── threading
      └── typing
```

## External Integrations

### PostgreSQL Database
- Connection pool: 10 concurrent connections
- Connection reuse and pooling via AsyncDAL
- Optional read replica support for scaling reads

### Redis (Optional)
- Credential refresh notifications
- Channel: `credentials:quote_interaction:bot:refreshed`
- Enables zero-downtime credential updates

### Platform Integrations Table
- Stores quote_interaction credentials
- `platform = 'quote_interaction'`
- `integration_type = 'bot'`
- Supports multiple active credentials

## Scalability Considerations

### Horizontal Scaling
- Stateless module design enables easy horizontal scaling
- Multiple instances can share same PostgreSQL database
- Load balancer can distribute requests across instances
- Database connection pooling handles concurrent access

### Vertical Scaling
- Increase `DB_POOL_SIZE` for higher concurrency
- Optimize PostgreSQL buffer cache for larger datasets
- Use read replicas for query-heavy workloads

### Performance Optimization
1. **Indexing:** Full-text search uses GIN index on tsvector
2. **Connection Pooling:** AsyncDAL maintains connection pool
3. **Query Optimization:** Parameterized queries prevent re-parsing
4. **Caching (Optional):** Front-end can cache random quotes
5. **Read Replicas:** Optional READ_REPLICA_URL for read scaling

## Security Architecture

1. **SQL Injection Prevention:** All queries use parameterized statements via AsyncDAL
2. **Community Isolation:** All queries include `community_id` filter
3. **Data Audit Trail:** Soft-deletes preserve deleted quote data with timestamp
4. **User Attribution:** `added_by_user_id` and `quoted_user_id` tracked
5. **Authentication:** Inherited from WaddleBot platform via JWT
6. **Credential Management:** Stored in platform_integrations table, not in code
