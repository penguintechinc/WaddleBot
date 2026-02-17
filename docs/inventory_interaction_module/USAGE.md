# Inventory Interaction Module - Usage Guide

## Getting Started

This guide covers setup, health checks, common workflows, and integration patterns for the Inventory Interaction Module.

## Installation & Setup

### Prerequisites

- Python 3.12+
- PostgreSQL 13+ with migration 014 applied
- Docker (optional, for containerized deployment)
- Redis (optional, for credential management)

### Local Development Setup

```bash
# Navigate to module directory
cd /home/penguin/code/waddlebot/action/interactive/inventory_interaction_module/

# Install dependencies
pip install -r requirements.txt

# Install shared library
cd /home/penguin/code/waddlebot
pip install -e libs/flask_core

# Set environment variables
export DATABASE_URL="postgresql://user:pass@localhost:5432/waddlebot"
export MODULE_PORT=8024
export CORE_API_URL="http://localhost:8000"
export ROUTER_API_URL="http://localhost:8000/api/v1/router"

# Start module
cd action/interactive/inventory_interaction_module
python app.py
```

### Docker Setup

#### Build the image:
```bash
cd /home/penguin/code/waddlebot

docker build \
  -f action/interactive/inventory_interaction_module/Dockerfile \
  -t waddlebot/inventory-interaction:latest \
  .
```

#### Run the container:
```bash
docker run -d \
  --name inventory-interaction \
  -p 8024:8024 \
  -e DATABASE_URL="postgresql://user:pass@db:5432/waddlebot" \
  -e CORE_API_URL="http://router-service:8000" \
  -e ROUTER_API_URL="http://router-service:8000/api/v1/router" \
  -e MODULE_PORT=8024 \
  -e LOG_LEVEL=INFO \
  -v /var/log/waddlebotlog:/var/log/waddlebotlog \
  waddlebot/inventory-interaction:latest
```

#### Docker Compose Example:
```yaml
version: '3.8'
services:
  inventory-interaction:
    build:
      context: .
      dockerfile: action/interactive/inventory_interaction_module/Dockerfile
    container_name: inventory-interaction
    ports:
      - "8024:8024"
    environment:
      DATABASE_URL: postgresql://waddlebot:password@postgres:5432/waddlebot
      CORE_API_URL: http://router-service:8000
      ROUTER_API_URL: http://router-service:8000/api/v1/router
      MODULE_PORT: 8024
      LOG_LEVEL: INFO
    volumes:
      - /var/log/waddlebotlog:/var/log/waddlebotlog
    depends_on:
      - postgres
      - router-service
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8024/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

## Health Checks

### Endpoint: `/health`

Check module health and operational status:

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
  "uptime_seconds": 1234
}
```

### Endpoint: `/metrics`

Performance and usage metrics:

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

### Endpoint: `/api/v1/status`

Quick status check:

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

## Common Workflows

### Workflow 1: Set Up New Community Inventory

```python
from flask_core import init_database
from action.interactive.inventory_interaction_module.services import InventoryService

# Initialize database
dal = init_database(uri="postgresql://user:pass@localhost/waddlebot")
inventory_service = InventoryService(dal)

# Create items
items = [
    {
        'name': 'Gaming Laptop',
        'description': 'High-performance gaming laptop',
        'item_type': 'equipment',
        'category': 'electronics',
        'quantity': 2,
        'checkout_price': 100,
        'max_checkout_duration_hours': 72,
    },
    {
        'name': 'Microphone',
        'description': 'Professional streaming microphone',
        'item_type': 'equipment',
        'category': 'audio',
        'quantity': 5,
        'checkout_price': 25,
        'max_checkout_duration_hours': 48,
    }
]

async def setup_inventory():
    for item_data in items:
        item = await inventory_service.add_item(
            community_id=1,
            created_by_user_id=1,
            **item_data
        )
        print(f"Created: {item['name']} (ID: {item['id']})")

import asyncio
asyncio.run(setup_inventory())
```

### Workflow 2: Member Checkout

```python
# Check item availability
item = await inventory_service.get_item(community_id=1, item_id=5)
print(f"Available: {item['available_quantity']}/{item['quantity']}")

if item['available_quantity'] > 0:
    # Checkout item
    checkout = await inventory_service.checkout_item(
        community_id=1,
        item_id=5,
        user_id=100,
        quantity=1,
        checkout_duration_hours=48,
        notes="For streaming event"
    )
    print(f"Checkout ID: {checkout['id']}")
    print(f"Due: {checkout['due_at']}")
```

### Workflow 3: Item Return

```python
# Return checked-out item
returned = await inventory_service.checkin_item(
    community_id=1,
    checkout_id=10,
    quantity=1,
    returned_condition="Good",
    returned_by_user_id=100
)
print(f"Item returned - Status: {returned['status']}")
print(f"Returned at: {returned['returned_at']}")
```

### Workflow 4: Restock Item

```python
# Add stock to inventory
updated_item = await inventory_service.add_stock(
    community_id=1,
    item_id=5,
    quantity=5,
    reason="Monthly restock",
    added_by_user_id=1
)
print(f"New quantity: {updated_item['quantity']}")
print(f"Available: {updated_item['available_quantity']}")
```

### Workflow 5: Search Inventory

```python
# Full-text search
results = await inventory_service.search_items(
    community_id=1,
    query="gaming laptop",
    limit=10
)
print(f"Found {len(results)} items")
for item in results:
    print(f"- {item['name']}: {item['available_quantity']} available")
```

### Workflow 6: Browse by Category

```python
# Get all items in category with availability
electronics = await inventory_service.get_items_by_category(
    community_id=1,
    category="electronics",
    include_unavailable=False
)
print(f"Available electronics: {len(electronics)} items")
for item in electronics:
    print(f"- {item['name']}: ${item['checkout_price']}")
```

### Workflow 7: Monitor Overdue Items

```python
# Get overdue checkouts
overdue = await inventory_service.get_overdue_checkouts(community_id=1)
print(f"Overdue items: {len(overdue)}")
for checkout in overdue:
    print(f"- Item {checkout['item_id']} (User {checkout['user_id']})")
    print(f"  Due: {checkout['due_at']}")
```

### Workflow 8: Generate Inventory Report

```python
# Get comprehensive summary
summary = await inventory_service.get_inventory_summary(community_id=1)
print(f"Total items: {summary['total_items']}")
print(f"Total quantity: {summary['total_quantity']}")
print(f"Available: {summary['total_available']}")
print(f"Active checkouts: {summary['active_checkouts']}")
print(f"Overdue: {summary['overdue_checkouts']}")
print(f"Low stock items: {summary['low_stock_items']}")
```

### Workflow 9: Review Audit Trail

```python
# Get audit logs
logs = await inventory_service.get_audit_log(
    community_id=1,
    action='checkout',
    limit=50
)
print(f"Recent checkouts: {len(logs)}")
for log in logs:
    print(f"[{log['created_at']}] User {log['user_id']} "
          f"checked out Item {log['item_id']}")
```

### Workflow 10: View User Checkout History

```python
# Get user's checkout history
history = await inventory_service.get_user_checkouts(
    community_id=1,
    user_id=100
)
print(f"User has {len(history)} checkouts")
for checkout in history:
    status_icon = "✓" if checkout['status'] == 'returned' else "⏳"
    print(f"{status_icon} Item {checkout['item_id']}: {checkout['status']}")
```

## Error Handling

All service methods raise exceptions on failure. Implement proper error handling:

```python
try:
    checkout = await inventory_service.checkout_item(
        community_id=1,
        item_id=5,
        user_id=100,
        quantity=10
    )
except ValueError as e:
    print(f"Invalid request: {e}")
    # Item not found, insufficient quantity, etc.
except Exception as e:
    print(f"Database error: {e}")
    # Database connection or query error
```

### Common Error Scenarios

| Error | Cause | Solution |
|-------|-------|----------|
| `ValueError: Item not found` | Item doesn't exist in community | Verify item_id and community_id |
| `ValueError: Insufficient quantity` | Not enough stock available | Check available_quantity field |
| `ValueError: Checkout not found` | Checkout ID doesn't exist | Verify checkout_id and community_id |
| `ValueError: Item already checked out` | Quantity validation failure | Check quantity <= available_quantity |
| Database connection error | PostgreSQL unreachable | Verify DATABASE_URL and DB connection |

## Integration with Community Currency

Checkout pricing is tracked but currency deduction must be handled separately:

```python
# After successful checkout
checkout = await inventory_service.checkout_item(
    community_id=1,
    item_id=5,
    user_id=100,
    quantity=1
)

# Get item details for price
item = await inventory_service.get_item(community_id=1, item_id=5)
if item['checkout_price'] > 0:
    # Deduct from user's currency balance
    # Integrate with community currency module
    await currency_service.deduct_balance(
        user_id=100,
        community_id=1,
        amount=item['checkout_price'],
        reason=f"Checkout: {item['name']}"
    )
```

## Async/Await Usage

All service methods are async and must be awaited:

```python
import asyncio

async def manage_inventory():
    # All methods must be awaited
    item = await inventory_service.get_item(1, 5)
    checkout = await inventory_service.checkout_item(1, 5, 100, 1)
    summary = await inventory_service.get_inventory_summary(1)

# Run in async context
asyncio.run(manage_inventory())
```

## Environment Variables

Key configuration variables:

```bash
# Required
DATABASE_URL=postgresql://user:pass@localhost:5432/waddlebot
MODULE_PORT=8024

# API Integration
CORE_API_URL=http://router-service:8000
ROUTER_API_URL=http://router-service:8000/api/v1/router

# Logging
LOG_LEVEL=INFO

# Security
SECRET_KEY=your-production-key-here

# Optional: Redis for credential management
REDIS_URL=redis://localhost:6379/0
```

See [CONFIGURATION.md](CONFIGURATION.md) for complete list.

## Testing

Run included examples for testing:

```python
from action.interactive.inventory_interaction_module.EXAMPLES import InventoryExamples

examples = InventoryExamples(inventory_service)

# Run complete workflow test
await examples.run_complete_workflow(community_id=1)
```

## Best Practices

1. **Always await async methods**: Never forget `await` keyword
2. **Validate inputs**: Check IDs and permissions before operations
3. **Handle exceptions**: Implement proper error handling
4. **Log operations**: Use audit log for compliance
5. **Monitor stock**: Regular low stock checks
6. **Track overdue**: Daily monitoring of overdue items
7. **Test workflows**: Use examples.py patterns
8. **Use metadata**: Store custom properties in metadata field

## Debugging

### View logs
```bash
# Docker logs
docker logs -f inventory-interaction

# File logs
tail -f /var/log/waddlebotlog/inventory_interaction_module.log
```

### Health check
```bash
curl -v http://localhost:8024/health
```

### Database connection test
```bash
psql postgresql://user:pass@localhost/waddlebot -c "SELECT 1"
```

## Next Steps

- Review [API.md](API.md) for complete endpoint documentation
- Check [ARCHITECTURE.md](ARCHITECTURE.md) for internal design
- See [CONFIGURATION.md](CONFIGURATION.md) for deployment options
- Consult [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for issues

---

**Module**: inventory_interaction_module  
**Port**: 8024  
**Language**: Python  
**Framework**: Quart
