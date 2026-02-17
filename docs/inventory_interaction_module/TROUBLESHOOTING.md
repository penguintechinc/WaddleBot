# Inventory Interaction Module - Troubleshooting Guide

## Common Issues & Solutions

### Database Connection Issues

#### Error: "Connection refused"

**Symptom:** Module fails to start, logs show "connection refused"

**Cause:** PostgreSQL service not running or incorrect connection string

**Solution:**
```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# Test connection directly
psql postgresql://user:pass@host:5432/db -c "SELECT 1;"

# Verify DATABASE_URL
docker exec inventory-interaction env | grep DATABASE_URL

# Restart PostgreSQL
docker restart waddlebot-postgres
```

#### Error: "database does not exist"

**Symptom:** "FATAL: database 'waddlebot' does not exist"

**Cause:** Database not created or migration 014 not applied

**Solution:**
```bash
# Create database
createdb -U postgres waddlebot

# Run migration
psql -U postgres -d waddlebot -f config/postgres/migrations/014_add_quartermaster_tables.sql

# Verify tables exist
psql postgresql://user:pass@host/db -c "\dt inventory_*"
```

#### Error: "role does not exist"

**Symptom:** "FATAL: role 'waddlebot' does not exist"

**Cause:** PostgreSQL user not created

**Solution:**
```bash
# Create role
psql -U postgres -c "CREATE USER waddlebot WITH PASSWORD 'password';"

# Grant privileges
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE waddlebot TO waddlebot;"
```

### Module Startup Issues

#### Error: "Module failed to start"

**Symptom:** Container exits immediately, no error details

**Solution:**
```bash
# View full logs
docker logs inventory-interaction

# Check configuration
docker run -it waddlebot/inventory-interaction:latest env | head -20

# Test configuration manually
python3 -c "
import os
from dotenv import load_dotenv
load_dotenv()
print(f'DATABASE_URL: {os.getenv("DATABASE_URL")}')"
```

#### Error: "Port already in use"

**Symptom:** "Address already in use" on port 8024

**Solution:**
```bash
# Find process using port
lsof -i :8024

# Kill process
kill -9 <PID>

# Use different port
docker run -p 8025:8024 ...
```

#### Error: "Permission denied" in logs

**Symptom:** Cannot write to log directory

**Solution:**
```bash
# Check permissions
ls -la /var/log/waddlebotlog

# Fix permissions
sudo chown waddlebot:waddlebot /var/log/waddlebotlog
chmod 755 /var/log/waddlebotlog

# Or mount from Docker
docker run -v /var/log/waddlebotlog:/var/log/waddlebotlog ...
```

### API & Endpoint Issues

#### Error: "Health check fails"

**Symptom:** `curl http://localhost:8024/health` returns error

**Solution:**
```bash
# Check if port is open
telnet localhost 8024

# View recent logs
docker logs -f inventory-interaction

# Check Hypercorn worker count
docker exec inventory-interaction ps aux | grep hypercorn

# Restart service
docker restart inventory-interaction
```

#### Error: "404 Not Found" on /api/v1/status

**Symptom:** Endpoint not found, returns 404

**Cause:** Blueprint not registered or wrong endpoint

**Solution:**
```bash
# Verify blueprint is registered in app.py
grep "register_blueprint" /home/penguin/code/waddlebot/action/interactive/inventory_interaction_module/app.py

# Check URL is correct
curl -v http://localhost:8024/api/v1/status

# View registered routes
docker exec inventory-interaction python3 -c "
from app import app
print([str(rule) for rule in app.url_map.iter_rules()])"
```

### Checkout & Item Issues

#### Error: "Item not found or community mismatch"

**Symptom:** ValueError when getting item

**Cause:** Item doesn't exist in specified community

**Solution:**
```python
# Verify item exists
item = await service.get_item(community_id=1, item_id=5)
if not item:
    print("Item not found")
    
# Check soft delete flag
result = await service.dal.execute(
    "SELECT deleted_at FROM inventory_items WHERE id = $1",
    [item_id]
)
print(f"Deleted at: {result[0]['deleted_at']}")
```

#### Error: "Insufficient quantity available"

**Symptom:** Cannot checkout even though quantity > 0

**Cause:** Checking available_quantity instead of quantity, or items already checked out

**Solution:**
```python
# Check available_quantity
item = await service.get_item(1, 5)
print(f"Total: {item['quantity']}")
print(f"Available: {item['available_quantity']}")
print(f"Checked out: {item['quantity'] - item['available_quantity']}")

# Only use available_quantity for checkout
if item['available_quantity'] >= needed:
    # Safe to checkout
```

#### Error: "Checkout not found or already processed"

**Symptom:** Checkin fails, checkout doesn't exist

**Cause:** Checkout already returned or invalid ID

**Solution:**
```python
# Verify checkout exists
checkout = await service.dal.execute(
    "SELECT * FROM inventory_checkouts WHERE id = $1 AND status = 'active'",
    [checkout_id]
)
if not checkout:
    print("Checkout not found or already returned")
    
# Check all checkouts for item
checkouts = await service.dal.execute(
    "SELECT * FROM inventory_checkouts WHERE item_id = $1 ORDER BY created_at DESC",
    [item_id]
)
```

### Performance Issues

#### Problem: Slow search queries

**Symptom:** `search_items()` takes >1 second

**Cause:** Missing GIN index or large dataset

**Solution:**
```sql
-- Check if GIN index exists
SELECT indexname FROM pg_indexes 
WHERE tablename = 'inventory_items' AND indexname LIKE '%search%';

-- Recreate if missing
CREATE INDEX idx_inventory_items_search 
    ON inventory_items USING GIN(to_tsvector('english', 
        name || ' ' || COALESCE(description, '') || ' ' || 
        COALESCE(category, '') || ' ' || COALESCE(item_type, '')));

-- Analyze tables
ANALYZE inventory_items;
```

#### Problem: Database connections exhausted

**Symptom:** "too many connections" error

**Cause:** Connection pool too small or connections not released

**Solution:**
```python
# Increase pool size in flask_core initialization
dal = init_database(
    uri=DATABASE_URL,
    pool_size=20,  # Increase from 10
    max_overflow=30
)

# Check active connections
SELECT count(*) FROM pg_stat_activity WHERE datname = 'waddlebot';

# Check module configuration
docker exec inventory-interaction env | grep DATABASE
```

#### Problem: Memory usage growing

**Symptom:** Container memory increases over time

**Cause:** Connection pool leak or unclosed queries

**Solution:**
```bash
# Monitor memory
docker stats inventory-interaction

# Restart container
docker restart inventory-interaction

# Check for connection leaks in code
# All await statements should complete or error
```

### Audit Log Issues

#### Problem: Audit logs missing

**Symptom:** `get_audit_log()` returns empty

**Cause:** Logging not working or logs deleted

**Solution:**
```sql
-- Check if table has data
SELECT COUNT(*) FROM inventory_log;

-- Check recent entries
SELECT * FROM inventory_log ORDER BY created_at DESC LIMIT 10;

-- Verify constraints
SELECT * FROM information_schema.table_constraints 
WHERE table_name = 'inventory_log';
```

#### Problem: Audit log growing too large

**Symptom:** Database size increasing rapidly

**Solution:**
```sql
-- Archive old logs
CREATE TABLE inventory_log_archive AS
SELECT * FROM inventory_log WHERE created_at < NOW() - INTERVAL '1 year';

DELETE FROM inventory_log WHERE created_at < NOW() - INTERVAL '1 year';

-- Check table size
SELECT pg_size_pretty(pg_total_relation_size('inventory_log'));
```

### Docker Issues

#### Error: "Image not found"

**Symptom:** "docker: image not found"

**Solution:**
```bash
# Build image
docker build -f action/interactive/inventory_interaction_module/Dockerfile     -t waddlebot/inventory-interaction:latest .

# Or use specific version
docker build ... -t waddlebot/inventory-interaction:v1.0.0 .
```

#### Error: "Volume mount fails"

**Symptom:** "cannot mount file"

**Cause:** Directory doesn't exist or permissions wrong

**Solution:**
```bash
# Create directory
mkdir -p /var/log/waddlebotlog

# Fix permissions
sudo chown $(id -u):$(id -g) /var/log/waddlebotlog
chmod 755 /var/log/waddlebotlog

# Try mount again
docker run -v /var/log/waddlebotlog:/var/log/waddlebotlog ...
```

## Debugging Techniques

### View Logs

```bash
# Real-time logs
docker logs -f inventory-interaction

# Last 100 lines
docker logs inventory-interaction | tail -100

# With timestamps
docker logs -t inventory-interaction

# Specific level
docker logs inventory-interaction 2>&1 | grep ERROR
```

### Execute Commands in Container

```bash
# Interactive shell
docker exec -it inventory-interaction /bin/bash

# Single command
docker exec inventory-interaction ps aux

# Python debug
docker exec -it inventory-interaction python3 -c "
import sys; print(sys.version)"
```

### Database Debugging

```bash
# Connect to database in container
docker exec -it inventory-interaction psql $DATABASE_URL

# Query logs
psql $DATABASE_URL -c "SELECT * FROM inventory_log ORDER BY created_at DESC LIMIT 10;"

# Check table structure
psql $DATABASE_URL -c "\d inventory_items"
```

### Performance Profiling

```bash
# Enable debug logging
docker run -e LOG_LEVEL=DEBUG ...

# Monitor performance
docker stats inventory-interaction

# Check slow queries (PostgreSQL)
psql $DATABASE_URL -c "
  SELECT query, calls, mean_time 
  FROM pg_stat_statements 
  ORDER BY mean_time DESC 
  LIMIT 10;"
```

## Support & Resources

### Getting Help

1. Check logs: `docker logs inventory-interaction`
2. Verify configuration: `env | grep MODULE`
3. Test connectivity: `curl http://localhost:8024/health`
4. Review CONFIGURATION.md for settings

### Quick Diagnostics

```bash
# Health status
curl -v http://localhost:8024/health

# Module status
curl -v http://localhost:8024/api/v1/status

# Database test
docker exec inventory-interaction     psql $DATABASE_URL -c "SELECT COUNT(*) FROM inventory_items;"

# Port accessibility
telnet localhost 8024
```

---

**Module**: inventory_interaction_module  
**Version**: 2.0.0  
**Last Updated**: 2026-02-16
