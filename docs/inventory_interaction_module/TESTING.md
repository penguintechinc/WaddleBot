# Inventory Interaction Module - Testing Guide

## Test Strategy

The Inventory Interaction Module requires comprehensive testing to ensure reliability, performance, and data integrity across all inventory operations.

## Test Categories

### Unit Tests

Tests for individual service methods in isolation.

**InventoryService CRUD Tests:**
```python
async def test_add_item_success():
    item = await service.add_item(
        community_id=1, name="Test Item", quantity=5
    )
    assert item['id'] is not None
    assert item['quantity'] == 5

async def test_get_item_by_id():
    item = await service.get_item(community_id=1, item_id=1)
    assert item['name'] == "Test Item"

async def test_update_item():
    updated = await service.update_item(
        community_id=1, item_id=1, quantity=10
    )
    assert updated['quantity'] == 10

async def test_delete_item():
    success = await service.delete_item(community_id=1, item_id=1)
    assert success is True
```

**Checkout Tests:**
```python
async def test_checkout_item_success():
    checkout = await service.checkout_item(
        community_id=1, item_id=1, user_id=100, quantity=1
    )
    assert checkout['status'] == 'active'
    assert checkout['due_at'] is not None

async def test_checkin_item():
    returned = await service.checkin_item(
        community_id=1, checkout_id=1
    )
    assert returned['status'] == 'returned'
    assert returned['returned_at'] is not None

async def test_checkout_insufficient_quantity():
    with pytest.raises(ValueError):
        await service.checkout_item(
            community_id=1, item_id=1, user_id=100, quantity=999
        )
```

**Stock Management Tests:**
```python
async def test_add_stock():
    updated = await service.add_stock(
        community_id=1, item_id=1, quantity=10
    )
    assert updated['quantity'] >= 10

async def test_remove_stock():
    updated = await service.remove_stock(
        community_id=1, item_id=1, quantity=2
    )
    assert updated['quantity'] < 10
```

**Search Tests:**
```python
async def test_search_items():
    results = await service.search_items(
        community_id=1, query="laptop"
    )
    assert len(results) > 0

async def test_get_items_by_category():
    electronics = await service.get_items_by_category(
        community_id=1, category="electronics"
    )
    assert all(item['category'] == 'electronics' for item in electronics)

async def test_get_available_items():
    available = await service.get_available_items(community_id=1)
    assert all(item['available_quantity'] > 0 for item in available)
```

### Integration Tests

Tests that verify interactions between components.

**Checkout Workflow:**
```python
async def test_complete_checkout_workflow():
    # Add item
    item = await service.add_item(
        community_id=1, name="Laptop", quantity=2
    )
    
    # Verify available
    assert item['available_quantity'] == 2
    
    # Checkout
    checkout = await service.checkout_item(
        community_id=1, item_id=item['id'], user_id=100, quantity=1
    )
    
    # Verify quantity updated
    updated = await service.get_item(community_id=1, item_id=item['id'])
    assert updated['available_quantity'] == 1
    
    # Return
    returned = await service.checkin_item(
        community_id=1, checkout_id=checkout['id']
    )
    
    # Verify quantity restored
    final = await service.get_item(community_id=1, item_id=item['id'])
    assert final['available_quantity'] == 2
```

**Audit Trail:**
```python
async def test_audit_logging():
    # Add item
    item = await service.add_item(
        community_id=1, name="Test", quantity=5
    )
    
    # Get audit log
    logs = await service.get_audit_log(
        community_id=1, item_id=item['id']
    )
    
    # Verify logged
    assert any(log['action'] == 'add_stock' for log in logs)
```

### Performance Tests

Tests for performance and scalability.

**Query Performance:**
```python
import time

async def test_search_performance():
    start = time.time()
    results = await service.search_items(
        community_id=1, query="laptop", limit=100
    )
    elapsed = time.time() - start
    assert elapsed < 0.5  # Should complete in <500ms

async def test_get_inventory_summary_performance():
    start = time.time()
    summary = await service.get_inventory_summary(community_id=1)
    elapsed = time.time() - start
    assert elapsed < 1.0  # Should complete in <1s
```

**Concurrency:**
```python
async def test_concurrent_checkouts():
    tasks = []
    for i in range(10):
        task = service.checkout_item(
            community_id=1, item_id=1, user_id=100+i, quantity=1
        )
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    assert len([r for r in results if not isinstance(r, Exception)]) >= 1
```

### E2E Tests

Tests that simulate real-world usage scenarios.

**Complete Inventory Lifecycle:**
```python
async def test_inventory_lifecycle():
    # Setup
    item = await service.add_item(
        community_id=1, name="Equipment", quantity=5
    )
    
    # Member checkout
    checkout1 = await service.checkout_item(
        community_id=1, item_id=item['id'], user_id=100
    )
    
    # Another member checkout
    checkout2 = await service.checkout_item(
        community_id=1, item_id=item['id'], user_id=101
    )
    
    # Check status
    summary = await service.get_inventory_summary(community_id=1)
    assert summary['total_checked_out'] == 2
    
    # Return items
    await service.checkin_item(community_id=1, checkout_id=checkout1['id'])
    await service.checkin_item(community_id=1, checkout_id=checkout2['id'])
    
    # Verify restored
    final = await service.get_item(community_id=1, item_id=item['id'])
    assert final['available_quantity'] == 5
```

## Test Data

### Sample Items for Testing

```python
test_items = [
    {
        'name': 'Gaming Laptop',
        'description': 'High-performance gaming laptop',
        'item_type': 'equipment',
        'category': 'electronics',
        'quantity': 2,
        'checkout_price': 100,
    },
    {
        'name': 'Microphone',
        'description': 'Professional streaming microphone',
        'item_type': 'equipment',
        'category': 'audio',
        'quantity': 5,
        'checkout_price': 25,
    },
    {
        'name': 'Ring Light',
        'description': 'LED ring light for streaming',
        'item_type': 'equipment',
        'category': 'lighting',
        'quantity': 3,
        'checkout_price': 15,
    },
    {
        'name': 'Board Games',
        'description': 'Collection of strategy games',
        'item_type': 'collectible',
        'category': 'games',
        'quantity': 10,
        'checkout_price': 0,
    }
]
```

### Fixture Setup

```python
import pytest

@pytest.fixture
async def inventory_service():
    dal = init_database(uri="sqlite:///:memory:")
    return InventoryService(dal)

@pytest.fixture
async def test_community(inventory_service):
    return 1  # Test community ID

@pytest.fixture
async def test_items(inventory_service, test_community):
    created = []
    for item_data in test_items:
        item = await inventory_service.add_item(
            community_id=test_community,
            created_by_user_id=1,
            **item_data
        )
        created.append(item)
    return created
```

## Running Tests

### Run All Tests

```bash
pytest tests/ -v
```

### Run Specific Test File

```bash
pytest tests/test_inventory_service.py -v
```

### Run Specific Test

```bash
pytest tests/test_inventory_service.py::test_checkout_item_success -v
```

### Run with Coverage

```bash
pytest tests/ --cov=app --cov-report=html
```

### Run Only Unit Tests

```bash
pytest tests/unit/ -v
```

### Run Only Integration Tests

```bash
pytest tests/integration/ -v
```

### Run with Output

```bash
pytest tests/ -v -s  # Show print statements
```

## Smoke Tests

Quick validation tests to ensure basic functionality:

```bash
# Health check
curl http://localhost:8024/health

# API status
curl http://localhost:8024/api/v1/status

# Database connectivity
docker exec inventory-interaction psql $DATABASE_URL -c "SELECT 1;"
```

## Validation Procedures

### Pre-Deployment Validation

1. All tests pass with 100% success rate
2. No SQL injection vulnerabilities
3. All required indexes present
4. Database migration 014 applied
5. Performance tests pass (query <500ms)
6. Concurrent operations handled correctly

### Data Integrity Checks

```sql
-- Verify inventory consistency
SELECT 
    i.id, 
    i.quantity, 
    i.available_quantity,
    COUNT(c.id) as active_checkouts
FROM inventory_items i
LEFT JOIN inventory_checkouts c 
    ON i.id = c.item_id AND c.status = 'active'
GROUP BY i.id
HAVING i.available_quantity + COUNT(c.id) != i.quantity;

-- Check for orphaned records
SELECT * FROM inventory_checkouts 
WHERE item_id NOT IN (SELECT id FROM inventory_items);

-- Verify audit log completeness
SELECT 
    COUNT(*) as total_logs,
    COUNT(DISTINCT community_id) as communities,
    COUNT(DISTINCT item_id) as items
FROM inventory_log;
```

## Debugging Tests

### Enable Verbose Logging

```bash
pytest tests/ -v --log-cli-level=DEBUG
```

### Debug Single Test

```bash
pytest tests/test_inventory_service.py::test_checkout_item_success -v -s --pdb
```

### Check Database State

```python
# In test
async def test_with_debug(inventory_service, test_community):
    item = await inventory_service.add_item(...)
    
    # Debug query
    result = await inventory_service.dal.execute(
        "SELECT * FROM inventory_items WHERE id = $1",
        [item['id']]
    )
    print(result)
```

---

**Module**: inventory_interaction_module  
**Version**: 2.0.0  
**Last Updated**: 2026-02-16
