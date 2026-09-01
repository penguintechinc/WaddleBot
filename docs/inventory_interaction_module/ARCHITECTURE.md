# Inventory Interaction Module - Architecture

## System Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Quart Web Application                        │
│                         (app.py)                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Blueprint Registration                       │  │
│  │  - Health/Metrics Blueprint                              │  │
│  │  - API v1 Blueprint (/api/v1)                            │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────┬─────────────────────────────────────────────┬─────┘
             │                                             │
             ▼                                             ▼
    ┌──────────────────┐                    ┌──────────────────┐
    │   Hypercorn      │                    │  AsyncDAL        │
    │   ASGI Server    │                    │  Database Layer  │
    │  (4 workers)     │                    │  Connection Pool │
    │  Port: 8024      │                    │  (pool_size=10)  │
    └──────────────────┘                    └────────┬─────────┘
                                                     │
                                                     ▼
                                            ┌──────────────────┐
                                            │   PostgreSQL     │
                                            │   Database       │
                                            │  (migrations/014)│
                                            └──────────────────┘
```

### Service Layer Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   InventoryService                              │
│                   (services/inventory_service.py)               │
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐   │
│  │              Item Management                           │   │
│  │  - add_item()                                          │   │
│  │  - get_item()                                          │   │
│  │  - update_item()                                       │   │
│  │  - delete_item()                                       │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐   │
│  │              Checkout Operations                       │   │
│  │  - checkout_item()                                     │   │
│  │  - checkin_item()                                      │   │
│  │  - get_active_checkouts()                              │   │
│  │  - get_overdue_checkouts()                             │   │
│  │  - get_user_checkouts()                                │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐   │
│  │              Stock Management                          │   │
│  │  - add_stock()                                         │   │
│  │  - remove_stock()                                      │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐   │
│  │              Search & Filtering                        │   │
│  │  - search_items() [Full-Text Search - GIN Index]       │   │
│  │  - get_items_by_category()                             │   │
│  │  - get_items_by_type()                                 │   │
│  │  - get_available_items()                               │   │
│  │  - get_low_stock_items()                               │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐   │
│  │              Reporting & Analytics                     │   │
│  │  - get_inventory_summary()                             │   │
│  │  - get_audit_log()                                     │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐   │
│  │              Internal Utilities                        │   │
│  │  - _log_action() [Audit Trail]                         │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                 │
└────────────┬─────────────────────────────────────────────────────┘
             │
             ▼
    ┌──────────────────┐
    │   AsyncDAL       │
    │   Query Executor │
    │  (self.dal)      │
    └──────────────────┘
```

## Data Flow Diagrams

### Item Checkout Flow

```
┌──────────────┐
│  User        │
│  checkout()  │
└────┬─────────┘
     │
     ▼
┌────────────────────────────────┐
│  InventoryService              │
│  checkout_item()               │
└────┬───────────────────────────┘
     │
     ├─── Validate: Item exists
     │     & quantity available
     │
     ├─── Create: inventory_checkouts
     │     record (status='active')
     │
     ├─── Update: inventory_items
     │     available_quantity -= qty
     │
     ├─── Log: _log_action()
     │     action='checkout'
     │
     └─── Return: checkout record
          with due_at timestamp
```

### Item Return (Checkin) Flow

```
┌──────────────┐
│  User        │
│  checkin()   │
└────┬─────────┘
     │
     ▼
┌────────────────────────────────┐
│  InventoryService              │
│  checkin_item()                │
└────┬───────────────────────────┘
     │
     ├─── Validate: Checkout exists
     │     & is 'active'
     │
     ├─── Update: inventory_checkouts
     │     status='returned'
     │     returned_at=NOW()
     │
     ├─── Update: inventory_items
     │     available_quantity += qty
     │
     ├─── Determine: Status check
     │     if returned_at > due_at
     │     then status='overdue'
     │
     ├─── Log: _log_action()
     │     action='return'
     │
     └─── Return: updated checkout
          record
```

### Search Flow (Full-Text)

```
┌──────────────┐
│  Query       │
│  "gaming"    │
└────┬─────────┘
     │
     ▼
┌────────────────────────────────┐
│  InventoryService              │
│  search_items()                │
└────┬───────────────────────────┘
     │
     ├─── Execute: PostgreSQL
     │     FTS query with GIN
     │     index
     │
     ├─── Search: Columns
     │     - name
     │     - description
     │     - category
     │     - item_type
     │
     ├─── Apply: Filter
     │     community_id
     │     deleted_at IS NULL
     │
     ├─── Rank: Results by
     │     relevance
     │
     └─── Return: List of items
          (up to limit)
```

## Database Schema

### inventory_items Table

```sql
CREATE TABLE inventory_items (
    id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    item_type VARCHAR(50),
    category VARCHAR(100),
    quantity INTEGER DEFAULT 0,
    available_quantity INTEGER DEFAULT 0,
    checkout_price INTEGER DEFAULT 0,
    max_checkout_duration_hours INTEGER,
    image_url TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    deleted_at TIMESTAMP DEFAULT NULL,
    created_by_user_id INTEGER,
    updated_by_user_id INTEGER,
    deleted_by_user_id INTEGER,
    
    UNIQUE(community_id, name, deleted_at)
);

-- Indexes
CREATE INDEX idx_inventory_items_community 
    ON inventory_items(community_id);
CREATE INDEX idx_inventory_items_active 
    ON inventory_items(community_id, deleted_at, created_at DESC);
CREATE INDEX idx_inventory_items_category 
    ON inventory_items(category, community_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_inventory_items_type 
    ON inventory_items(item_type, community_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_inventory_items_stock 
    ON inventory_items(available_quantity, community_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_inventory_items_search 
    ON inventory_items USING GIN(to_tsvector('english', 
        name || ' ' || COALESCE(description, '') || ' ' || 
        COALESCE(category, '') || ' ' || COALESCE(item_type, '')));
```

### inventory_checkouts Table

```sql
CREATE TABLE inventory_checkouts (
    id SERIAL PRIMARY KEY,
    item_id INTEGER NOT NULL REFERENCES inventory_items(id),
    user_id INTEGER NOT NULL,
    quantity INTEGER DEFAULT 1,
    checked_out_at TIMESTAMP DEFAULT NOW(),
    due_at TIMESTAMP,
    returned_at TIMESTAMP DEFAULT NULL,
    returned_condition VARCHAR(100),
    status VARCHAR(20) DEFAULT 'active',
    notes TEXT,
    checked_out_by_user_id INTEGER,
    returned_by_user_id INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT valid_status CHECK (status IN ('active', 'returned', 'overdue'))
);

-- Indexes
CREATE INDEX idx_inventory_checkouts_active 
    ON inventory_checkouts(status) WHERE status = 'active';
CREATE INDEX idx_inventory_checkouts_overdue 
    ON inventory_checkouts(due_at) WHERE status IN ('active', 'overdue');
CREATE INDEX idx_inventory_checkouts_item 
    ON inventory_checkouts(item_id);
CREATE INDEX idx_inventory_checkouts_user 
    ON inventory_checkouts(user_id);
CREATE INDEX idx_inventory_checkouts_community 
    ON inventory_checkouts(item_id) 
    WHERE status IN ('active', 'overdue');
```

### inventory_log Table

```sql
CREATE TABLE inventory_log (
    id SERIAL PRIMARY KEY,
    item_id INTEGER NOT NULL REFERENCES inventory_items(id),
    user_id INTEGER,
    community_id INTEGER NOT NULL,
    action VARCHAR(50) NOT NULL,
    quantity_change INTEGER,
    details JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT valid_action CHECK (action IN 
        ('checkout', 'return', 'add_stock', 'remove_stock', 'update', 'delete'))
);

-- Indexes
CREATE INDEX idx_inventory_log_community 
    ON inventory_log(community_id);
CREATE INDEX idx_inventory_log_item 
    ON inventory_log(item_id);
CREATE INDEX idx_inventory_log_user 
    ON inventory_log(user_id);
CREATE INDEX idx_inventory_log_action 
    ON inventory_log(action);
CREATE INDEX idx_inventory_log_created_at 
    ON inventory_log(created_at DESC);
```

## Component Interactions

### Configuration (config.py)

Manages:
- Module metadata (name, version, port)
- Database connection string
- API endpoint URLs
- Logging configuration
- Redis credential listener
- Environment variable loading with sensible defaults

**Key Classes:**
- `Config`: Central configuration management with:
  - `load_credentials_from_db()`: Load credentials from platform_integrations
  - `start_credential_listener()`: Background thread for Redis notifications

### Application (app.py)

Manages:
- Quart application initialization
- Blueprint registration (health, metrics, API v1)
- AsyncDAL database initialization
- Hypercorn ASGI server configuration
- Async startup lifecycle

**Key Functions:**
- `@app.before_serving`: Initialize database on startup
- `@api_bp.route('/status')`: Health check endpoint
- Main block: Start Hypercorn server on configured port

### InventoryService (services/inventory_service.py)

Manages:
- All business logic for inventory operations
- AsyncDAL database interactions
- Audit logging through _log_action()
- Transaction management
- Error handling and validation

**Key Methods by Category:**

**CRUD (4 methods):**
- `add_item()` - Create with full details
- `get_item()` - Retrieve single item
- `update_item()` - Modify existing item
- `delete_item()` - Soft delete with audit

**Checkout (5 methods):**
- `checkout_item()` - Reserve item with due date
- `checkin_item()` - Return item
- `get_active_checkouts()` - All active borrows
- `get_overdue_checkouts()` - Overdue items
- `get_user_checkouts()` - User's history

**Stock (2 methods):**
- `add_stock()` - Add quantity
- `remove_stock()` - Remove quantity

**Search (5 methods):**
- `search_items()` - Full-text (GIN index)
- `get_items_by_category()` - Category filter
- `get_items_by_type()` - Type filter
- `get_available_items()` - Has stock
- `get_low_stock_items()` - Low availability

**Reporting (2 methods):**
- `get_inventory_summary()` - Statistics
- `get_audit_log()` - Operation history

**Internal (1 method):**
- `_log_action()` - Audit trail creation

## Async/Await Pattern

All database operations use async/await:

```python
# In async context
async def checkout():
    # All calls must be awaited
    item = await inventory_service.get_item(1, 5)
    checkout = await inventory_service.checkout_item(1, 5, 100, 1)
    return checkout

# Must run in async event loop
import asyncio
result = asyncio.run(checkout())
```

## Performance Characteristics

### Database Indexes
- Community lookups: O(1) with `idx_inventory_items_community`
- Full-text search: O(log n) with GIN index
- Category/type filter: O(log n) with composite indexes
- Stock lookups: O(log n) with range index

### Async Non-Blocking
- All I/O operations are non-blocking
- Connection pooling handles concurrency
- Worker threads scale with Hypercorn configuration

### Query Optimization
- Specific column selection (no SELECT *)
- Indexed WHERE clauses
- JOIN operations on indexed fields
- LIMIT clauses for pagination

## Dependency Management

### External Dependencies
- **quart**: ASGI web framework
- **hypercorn**: ASGI server
- **httpx**: Async HTTP client
- **python-dotenv**: Environment configuration
- **flask_core**: Shared library (AsyncDAL, logging, etc.)
- **PostgreSQL**: Database backend

### Internal Dependencies
- `config.py`: Configuration management
- `services/inventory_service.py`: Core service logic
- `flask_core`: Shared infrastructure from parent project

## Error Handling Strategy

### Validation Layer
- Input validation in InventoryService methods
- Raises `ValueError` for bad requests
- Specific error messages for debugging

### Database Layer
- AsyncDAL handles connection errors
- SQL constraint violations propagate as exceptions
- Transaction rollback on failure

### Application Layer
- Exception handlers in app.py
- Logging of all errors with context
- Graceful error responses

### Audit Trail
- All actions logged even if failed
- Error details included in audit log
- Immutable record for compliance

## Extensibility Points

### Custom Metadata
Items support arbitrary JSON metadata for extensions:
```python
metadata={
    'color': 'blue',
    'weight_kg': 2.5,
    'warranty_expires': '2026-12-31',
    'custom_field': 'any_value'
}
```

### Community Currency Integration
Checkout pricing field ready for integration with currency module

### Notification Hooks
`get_overdue_checkouts()` enables notification systems
`get_audit_log()` enables reporting systems

### Custom Attributes
Can store additional fields in metadata without schema changes

## Scaling Considerations

### Horizontal Scaling
- Stateless service design (no in-memory state)
- AsyncDAL connection pooling handles multiple instances
- Database as single source of truth

### Vertical Scaling
- Increase Hypercorn workers for more concurrency
- Increase AsyncDAL pool size for more DB connections
- Adjust PostgreSQL pool settings

### Performance Tuning
- Full-text search uses GIN indexes for speed
- Strategic database indexes on common queries
- Connection pooling reduces overhead

---

**Architecture Version**: 2.0.0  
**Service Version**: 1.0.0  
**Last Updated**: 2026-02-16
