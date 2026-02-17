# Inventory Interaction Module - API Reference

Complete documentation of all endpoints and service methods for the Inventory Interaction Module.

## HTTP Endpoints

### Health Check Endpoint

#### GET `/health`

Check module health and status.

**Request:**
```bash
curl http://localhost:8024/health
```

**Response (200 OK):**
```json
{
  "status": "healthy",
  "module": "inventory_interaction_module",
  "version": "2.0.0",
  "timestamp": "2026-02-16T10:30:45Z",
  "database": "connected",
  "uptime_seconds": 3600
}
```

### Metrics Endpoint

#### GET `/metrics`

Retrieve performance metrics and statistics.

**Request:**
```bash
curl http://localhost:8024/metrics
```

**Response (200 OK):**
```json
{
  "requests_total": 1523,
  "requests_per_second": 12.3,
  "average_response_time_ms": 45.2,
  "database_connections": {
    "active": 5,
    "idle": 5,
    "pool_size": 10
  },
  "cache_stats": {
    "hits": 923,
    "misses": 600,
    "hit_rate": 0.606
  }
}
```

### Status Endpoint

#### GET `/api/v1/status`

Quick operational status check.

**Request:**
```bash
curl http://localhost:8024/api/v1/status
```

**Response (200 OK):**
```json
{
  "status": "operational",
  "module": "inventory_interaction_module"
}
```

## Service Methods (Python API)

All service methods are async and must be awaited. The InventoryService provides the following methods:

### Item Management Methods

#### add_item()

Create a new inventory item.

**Signature:**
```python
async def add_item(
    community_id: int,
    name: str,
    description: Optional[str] = None,
    item_type: Optional[str] = None,
    category: Optional[str] = None,
    quantity: int = 0,
    checkout_price: int = 0,
    max_checkout_duration_hours: Optional[int] = None,
    image_url: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    created_by_user_id: Optional[int] = None
) -> Dict[str, Any]
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `community_id` | int | Yes | Community ID |
| `name` | str | Yes | Item name |
| `description` | str | No | Item description |
| `item_type` | str | No | Type (equipment, consumable, collectible) |
| `category` | str | No | Category for filtering |
| `quantity` | int | No | Initial quantity (default: 0) |
| `checkout_price` | int | No | Community currency cost (default: 0) |
| `max_checkout_duration_hours` | int | No | Maximum checkout duration |
| `image_url` | str | No | Item image URL |
| `metadata` | dict | No | Custom metadata |
| `created_by_user_id` | int | No | User creating item |

**Response:**
```python
{
    'id': 5,
    'community_id': 1,
    'name': 'Gaming Laptop',
    'description': 'High-performance laptop',
    'item_type': 'equipment',
    'category': 'electronics',
    'quantity': 2,
    'available_quantity': 2,
    'checkout_price': 100,
    'max_checkout_duration_hours': 72,
    'image_url': 'https://example.com/laptop.jpg',
    'metadata': {},
    'created_at': datetime(...),
    'updated_at': datetime(...)
}
```

**Errors:**
- `ValueError`: Invalid input parameters
- `Exception`: Database error

**Example:**
```python
item = await inventory_service.add_item(
    community_id=1,
    name="Gaming Laptop",
    description="High-performance laptop for events",
    item_type="equipment",
    category="electronics",
    quantity=2,
    checkout_price=100,
    max_checkout_duration_hours=72,
    created_by_user_id=42
)
```

#### get_item()

Retrieve a specific item by ID.

**Signature:**
```python
async def get_item(
    community_id: int,
    item_id: int
) -> Optional[Dict[str, Any]]
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `community_id` | int | Yes | Community ID |
| `item_id` | int | Yes | Item ID |

**Response:**
Item dictionary or None if not found.

**Example:**
```python
item = await inventory_service.get_item(community_id=1, item_id=5)
if item:
    print(f"{item['name']}: {item['available_quantity']}/{item['quantity']}")
```

#### update_item()

Update item properties.

**Signature:**
```python
async def update_item(
    community_id: int,
    item_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    item_type: Optional[str] = None,
    category: Optional[str] = None,
    checkout_price: Optional[int] = None,
    max_checkout_duration_hours: Optional[int] = None,
    image_url: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    updated_by_user_id: Optional[int] = None
) -> Dict[str, Any]
```

**Response:**
Updated item dictionary.

**Example:**
```python
updated = await inventory_service.update_item(
    community_id=1,
    item_id=5,
    checkout_price=150,
    updated_by_user_id=42
)
```

#### delete_item()

Soft delete an item (marks as deleted, preserves audit trail).

**Signature:**
```python
async def delete_item(
    community_id: int,
    item_id: int,
    deleted_by_user_id: Optional[int] = None
) -> bool
```

**Response:**
True if deletion successful.

**Example:**
```python
success = await inventory_service.delete_item(
    community_id=1,
    item_id=5,
    deleted_by_user_id=42
)
```

### Checkout Methods

#### checkout_item()

Check out item(s) from inventory.

**Signature:**
```python
async def checkout_item(
    community_id: int,
    item_id: int,
    user_id: int,
    quantity: int = 1,
    checkout_duration_hours: Optional[int] = None,
    notes: Optional[str] = None,
    checked_out_by_user_id: Optional[int] = None
) -> Dict[str, Any]
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `community_id` | int | Yes | Community ID |
| `item_id` | int | Yes | Item ID to checkout |
| `user_id` | int | Yes | User checking out item |
| `quantity` | int | No | Quantity to checkout (default: 1) |
| `checkout_duration_hours` | int | No | Duration until due date |
| `notes` | str | No | Checkout notes |
| `checked_out_by_user_id` | int | No | Staff member recording checkout |

**Response:**
```python
{
    'id': 10,
    'item_id': 5,
    'user_id': 100,
    'quantity': 1,
    'checked_out_at': datetime(...),
    'due_at': datetime(...),
    'status': 'active',
    'notes': 'For streaming event'
}
```

**Errors:**
- `ValueError`: Item not found, insufficient quantity
- `Exception`: Database error

**Example:**
```python
checkout = await inventory_service.checkout_item(
    community_id=1,
    item_id=5,
    user_id=100,
    quantity=1,
    checkout_duration_hours=48,
    notes="For streaming setup"
)
```

#### checkin_item()

Return checked-out item(s).

**Signature:**
```python
async def checkin_item(
    community_id: int,
    checkout_id: int,
    quantity: Optional[int] = None,
    returned_condition: Optional[str] = None,
    returned_by_user_id: Optional[int] = None
) -> Dict[str, Any]
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `community_id` | int | Yes | Community ID |
| `checkout_id` | int | Yes | Checkout record ID |
| `quantity` | int | No | Quantity returned (all if None) |
| `returned_condition` | str | No | Item condition on return |
| `returned_by_user_id` | int | No | Staff member recording return |

**Response:**
Updated checkout record with status='returned'.

**Example:**
```python
returned = await inventory_service.checkin_item(
    community_id=1,
    checkout_id=10,
    returned_condition="Good",
    returned_by_user_id=100
)
```

#### get_active_checkouts()

Get currently active checkouts.

**Signature:**
```python
async def get_active_checkouts(
    community_id: int,
    user_id: Optional[int] = None,
    limit: int = 100
) -> List[Dict[str, Any]]
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `community_id` | int | Yes | Community ID |
| `user_id` | int | No | Filter by specific user |
| `limit` | int | No | Maximum results (default: 100) |

**Response:**
List of active checkout records.

**Example:**
```python
active = await inventory_service.get_active_checkouts(
    community_id=1,
    user_id=100
)
```

#### get_overdue_checkouts()

Get overdue (past due date) checkouts.

**Signature:**
```python
async def get_overdue_checkouts(
    community_id: int,
    limit: int = 100
) -> List[Dict[str, Any]]
```

**Response:**
List of overdue checkout records.

**Example:**
```python
overdue = await inventory_service.get_overdue_checkouts(community_id=1)
for checkout in overdue:
    print(f"Overdue: Item {checkout['item_id']} (User {checkout['user_id']})")
```

#### get_user_checkouts()

Get user's complete checkout history.

**Signature:**
```python
async def get_user_checkouts(
    community_id: int,
    user_id: int,
    status: Optional[str] = None,
    limit: int = 100
) -> List[Dict[str, Any]]
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `community_id` | int | Yes | Community ID |
| `user_id` | int | Yes | User ID |
| `status` | str | No | Filter by status (active/returned) |
| `limit` | int | No | Maximum results |

**Response:**
List of checkout records.

**Example:**
```python
history = await inventory_service.get_user_checkouts(
    community_id=1,
    user_id=100,
    status='active'
)
```

### Stock Management Methods

#### add_stock()

Add items to inventory stock.

**Signature:**
```python
async def add_stock(
    community_id: int,
    item_id: int,
    quantity: int,
    reason: Optional[str] = None,
    added_by_user_id: Optional[int] = None
) -> Dict[str, Any]
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `community_id` | int | Yes | Community ID |
| `item_id` | int | Yes | Item ID |
| `quantity` | int | Yes | Quantity to add |
| `reason` | str | No | Reason for addition |
| `added_by_user_id` | int | No | User adding stock |

**Response:**
Updated item with new quantity.

**Example:**
```python
updated = await inventory_service.add_stock(
    community_id=1,
    item_id=5,
    quantity=10,
    reason="Monthly restock",
    added_by_user_id=1
)
```

#### remove_stock()

Remove items from inventory stock.

**Signature:**
```python
async def remove_stock(
    community_id: int,
    item_id: int,
    quantity: int,
    reason: Optional[str] = None,
    removed_by_user_id: Optional[int] = None
) -> Dict[str, Any]
```

**Response:**
Updated item with new quantity.

**Example:**
```python
updated = await inventory_service.remove_stock(
    community_id=1,
    item_id=5,
    quantity=2,
    reason="Damaged items",
    removed_by_user_id=1
)
```

### Search & Filtering Methods

#### search_items()

Full-text search across item names, descriptions, categories, and types.

**Signature:**
```python
async def search_items(
    community_id: int,
    query: str,
    limit: int = 50
) -> List[Dict[str, Any]]
```

**Example:**
```python
results = await inventory_service.search_items(
    community_id=1,
    query="gaming laptop",
    limit=20
)
```

#### get_items_by_category()

Get items filtered by category.

**Signature:**
```python
async def get_items_by_category(
    community_id: int,
    category: str,
    include_unavailable: bool = False,
    limit: int = 100
) -> List[Dict[str, Any]]
```

**Example:**
```python
electronics = await inventory_service.get_items_by_category(
    community_id=1,
    category="electronics",
    include_unavailable=False
)
```

#### get_items_by_type()

Get items filtered by item type.

**Signature:**
```python
async def get_items_by_type(
    community_id: int,
    item_type: str,
    include_unavailable: bool = False,
    limit: int = 100
) -> List[Dict[str, Any]]
```

**Example:**
```python
equipment = await inventory_service.get_items_by_type(
    community_id=1,
    item_type="equipment"
)
```

#### get_available_items()

Get items with available inventory.

**Signature:**
```python
async def get_available_items(
    community_id: int,
    limit: int = 100
) -> List[Dict[str, Any]]
```

**Example:**
```python
available = await inventory_service.get_available_items(community_id=1)
```

#### get_low_stock_items()

Get items with low availability.

**Signature:**
```python
async def get_low_stock_items(
    community_id: int,
    threshold: int = 2,
    limit: int = 100
) -> List[Dict[str, Any]]
```

**Example:**
```python
low_stock = await inventory_service.get_low_stock_items(community_id=1)
```

### Reporting Methods

#### get_inventory_summary()

Get comprehensive inventory statistics.

**Signature:**
```python
async def get_inventory_summary(
    community_id: int
) -> Dict[str, Any]
```

**Response:**
```python
{
    'total_items': 10,
    'total_quantity': 45,
    'total_available': 35,
    'total_checked_out': 10,
    'active_checkouts': 8,
    'overdue_checkouts': 2,
    'low_stock_items': 3,
    'categories': {
        'electronics': 5,
        'audio': 3,
        'lighting': 2
    }
}
```

**Example:**
```python
summary = await inventory_service.get_inventory_summary(community_id=1)
print(f"Available: {summary['total_available']}/{summary['total_quantity']}")
```

#### get_audit_log()

Get audit trail of operations.

**Signature:**
```python
async def get_audit_log(
    community_id: int,
    item_id: Optional[int] = None,
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    limit: int = 100
) -> List[Dict[str, Any]]
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `community_id` | int | Community ID |
| `item_id` | int | Filter by item |
| `user_id` | int | Filter by user |
| `action` | str | Filter by action (checkout, return, add_stock, remove_stock, update, delete) |
| `limit` | int | Maximum results |

**Response:**
```python
[
    {
        'id': 45,
        'item_id': 5,
        'user_id': 42,
        'community_id': 1,
        'action': 'checkout',
        'quantity_change': -1,
        'details': {'quantity': 1, 'notes': 'For event'},
        'created_at': datetime(...)
    }
]
```

**Example:**
```python
logs = await inventory_service.get_audit_log(
    community_id=1,
    action='checkout',
    limit=50
)
```

## Error Responses

All methods raise exceptions on failure:

```python
try:
    item = await inventory_service.get_item(1, 99999)
except ValueError as e:
    print(f"Validation error: {e}")
except Exception as e:
    print(f"Database error: {e}")
```

### Common Error Messages

| Error | Cause | Resolution |
|-------|-------|-----------|
| `ValueError: Item not found` | Item ID doesn't exist | Check item_id and community_id |
| `ValueError: Insufficient quantity available` | Checkout exceeds available stock | Check available_quantity |
| `ValueError: Checkout not found` | Checkout ID doesn't exist | Verify checkout_id |
| Database connection error | PostgreSQL unreachable | Check DATABASE_URL and connection |
| `ValueError: Invalid community_id` | Community doesn't exist | Verify community_id |

## Rate Limits

- No built-in rate limiting (implement at API gateway)
- Recommended: 1000 requests/second per community

## Data Types

### DateTime Format
All timestamps use ISO 8601 format:
```
2026-02-16T10:30:45.123456Z
```

### Metadata
Metadata field accepts arbitrary JSON:
```python
metadata={
    'color': 'blue',
    'weight_kg': 2.5,
    'serial_number': 'ABC123',
    'warranty_until': '2026-12-31'
}
```

---

**Module**: inventory_interaction_module  
**API Version**: v1  
**Service Version**: 1.0.0  
**Last Updated**: 2026-02-16
