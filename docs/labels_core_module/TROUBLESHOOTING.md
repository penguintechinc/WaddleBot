# Labels Core Module - Troubleshooting Guide

## Common Issues

### Module Won't Start

#### Problem: "Port already in use"
```
Error: [Errno 98] Address already in use
```

**Solution**:
```bash
# Find process using port 8023
lsof -i :8023

# Kill the process
kill -9 <PID>

# Or change port in .env
MODULE_PORT=8024
```

#### Problem: "Database connection failed"
```
Error: could not connect to server: Connection refused
```

**Solution**:
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Start PostgreSQL
sudo systemctl start postgresql

# Verify connection string
psql postgresql://waddlebot:password@localhost:5432/waddlebot

# Check DATABASE_URL in .env
echo $DATABASE_URL
```

#### Problem: "Module import errors"
```
ModuleNotFoundError: No module named 'flask_core'
```

**Solution**:
```bash
# Ensure libs path is correct
cd core/labels_core_module
ls ../../libs/flask_core  # Should exist

# Check PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:../../libs"

# Or install dependencies
pip install -r requirements.txt
```

---

## API Issues

### Label Creation Fails

#### Problem: "Label already exists in category"
```json
{
  "success": false,
  "error": "Label 'VIP Member' already exists in category 'user'"
}
```

**Solution**:
```bash
# Check existing labels
curl http://localhost:8023/api/v1/labels?category=user

# Use different name or update existing label
curl -X PUT http://localhost:8023/api/v1/labels/1 \
  -H "Content-Type: application/json" \
  -d '{"name": "Updated Name"}'
```

#### Problem: "Invalid category"
```json
{
  "success": false,
  "error": "Invalid category. Must be one of: [...]"
}
```

**Solution**:
```bash
# Check supported entity types
curl http://localhost:8023/api/v1/status | jq .data.supported_entity_types

# Use valid entity type
curl -X POST http://localhost:8023/api/v1/labels \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test",
    "category": "user",
    "created_by": "admin"
  }'
```

### Label Application Fails

#### Problem: "Maximum labels exceeded"
```json
{
  "success": false,
  "error": "user can have maximum 5 labels"
}
```

**Solution**:
```bash
# Check current labels for entity
curl http://localhost:8023/api/v1/entity/user/user_123/labels

# Remove unused labels
curl -X POST http://localhost:8023/api/v1/labels/remove \
  -H "Content-Type: application/json" \
  -d '{
    "entity_id": "user_123",
    "entity_type": "user",
    "label_id": 1
  }'

# Check limits
curl http://localhost:8023/api/v1/status | jq .data.label_limits
```

#### Problem: "Label already applied to this entity"
```json
{
  "success": false,
  "error": "Label already applied to this entity"
}
```

**Solution**:
```bash
# This is expected behavior - label is already assigned
# If you need to update metadata or expiration, remove and re-apply

# Remove existing
curl -X POST http://localhost:8023/api/v1/labels/remove \
  -H "Content-Type: application/json" \
  -d '{
    "entity_id": "user_123",
    "entity_type": "user",
    "label_id": 1
  }'

# Reapply with new data
curl -X POST http://localhost:8023/api/v1/labels/apply \
  -H "Content-Type: application/json" \
  -d '{
    "entity_id": "user_123",
    "entity_type": "user",
    "label_id": 1,
    "applied_by": "admin",
    "expires_at": "2025-12-31T23:59:59Z"
  }'
```

### System Label Protection

#### Problem: "Cannot modify system labels"
```json
{
  "success": false,
  "error": "Cannot modify system labels"
}
```

**Solution**:
```bash
# System labels (is_system=true) are protected
# Check if label is system label
curl http://localhost:8023/api/v1/labels/1 | jq .data.label.is_system

# Create a new non-system label instead
curl -X POST http://localhost:8023/api/v1/labels \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Custom Label",
    "category": "user",
    "created_by": "admin"
  }'
```

---

## Database Issues

### Migration Failures

#### Problem: "Table already exists"
```
psycopg2.errors.DuplicateTable: relation "labels" already exists
```

**Solution**:
```bash
# Check existing tables
psql -d waddlebot -c "\dt"

# Drop old tables if migrating
psql -d waddlebot -c "DROP TABLE IF EXISTS labels CASCADE;"
psql -d waddlebot -c "DROP TABLE IF EXISTS entity_labels CASCADE;"

# Restart module to recreate tables
python app.py
```

#### Problem: "Column does not exist"
```
psycopg2.errors.UndefinedColumn: column "icon" does not exist
```

**Solution**:
```sql
-- Add missing column
ALTER TABLE labels ADD COLUMN icon VARCHAR(50);

-- Or drop and recreate table
DROP TABLE labels CASCADE;
-- Restart module
```

### Query Performance Issues

#### Problem: Slow label queries

**Diagnosis**:
```sql
-- Check query performance
EXPLAIN ANALYZE
SELECT * FROM entity_labels
WHERE entity_id = 'user_123' AND entity_type = 'user';
```

**Solution**:
```sql
-- Add indexes
CREATE INDEX IF NOT EXISTS idx_entity_labels_lookup
ON entity_labels(entity_id, entity_type);

CREATE INDEX IF NOT EXISTS idx_entity_labels_label
ON entity_labels(label_id);

CREATE INDEX IF NOT EXISTS idx_labels_category
ON labels(category);

-- Analyze tables
ANALYZE labels;
ANALYZE entity_labels;
```

### Connection Pool Exhaustion

#### Problem: "Too many connections"
```
psycopg2.OperationalError: FATAL: sorry, too many clients already
```

**Solution**:
```sql
-- Check current connections
SELECT count(*) FROM pg_stat_activity;

-- Increase max_connections in postgresql.conf
max_connections = 200

-- Restart PostgreSQL
sudo systemctl restart postgresql

-- Or reduce connections in application
# Add to config.py
DATABASE_POOL_SIZE = 10
```

---

## Performance Issues

### Slow Bulk Operations

#### Problem: Bulk label application takes too long

**Diagnosis**:
```python
import time
start = time.time()
# Bulk operation
print(f"Took {time.time() - start}s")
```

**Solution**:
```python
# Reduce batch size
# Instead of 1000 items, use 500
batch_size = 500
for i in range(0, len(items), batch_size):
    batch = items[i:i+batch_size]
    apply_labels_bulk(batch)

# Or enable async processing
# Use asyncio.gather for parallel operations
```

### High Memory Usage

#### Problem: Module consuming excessive memory

**Diagnosis**:
```bash
# Monitor memory usage
ps aux | grep "python app.py"

# Check for memory leaks
pip install memory_profiler
python -m memory_profiler app.py
```

**Solution**:
```python
# Implement pagination for large queries
limit = 100
offset = 0
while True:
    results = get_labels(limit=limit, offset=offset)
    if not results:
        break
    process_results(results)
    offset += limit

# Clear caches periodically
import gc
gc.collect()
```

---

## Search Issues

### No Search Results

#### Problem: Search returns empty results

**Diagnosis**:
```bash
# Check if labels exist
curl http://localhost:8023/api/v1/labels?search=VIP

# Check if assignments exist
curl http://localhost:8023/api/v1/entity/user/user_123/labels

# Verify label names match exactly
```

**Solution**:
```bash
# Use exact label names (case-sensitive)
curl "http://localhost:8023/api/v1/labels/search?entity_type=user&labels=VIP%20Member"

# Check is_active flag
SELECT * FROM entity_labels WHERE entity_id = 'user_123' AND is_active = true;

# Check expiration
SELECT * FROM entity_labels WHERE expires_at > NOW();
```

### Search Performance Issues

#### Problem: Search queries timeout

**Solution**:
```sql
-- Add search indexes
CREATE INDEX idx_entity_labels_search
ON entity_labels(entity_type, label_id, is_active);

-- Use materialized view for frequent searches
CREATE MATERIALIZED VIEW mv_user_label_counts AS
SELECT entity_id, COUNT(*) as label_count
FROM entity_labels
WHERE entity_type = 'user' AND is_active = true
GROUP BY entity_id;

-- Refresh periodically
REFRESH MATERIALIZED VIEW mv_user_label_counts;
```

---

## Data Consistency Issues

### Orphaned Label Assignments

#### Problem: entity_labels referencing deleted labels

**Diagnosis**:
```sql
SELECT el.*
FROM entity_labels el
LEFT JOIN labels l ON l.id = el.label_id
WHERE l.id IS NULL;
```

**Solution**:
```sql
-- Clean up orphaned assignments
DELETE FROM entity_labels
WHERE label_id NOT IN (SELECT id FROM labels);

-- Add foreign key constraint (if not exists)
ALTER TABLE entity_labels
ADD CONSTRAINT fk_entity_labels_label
FOREIGN KEY (label_id) REFERENCES labels(id)
ON DELETE CASCADE;
```

### Expired Labels Still Active

#### Problem: Expired labels not being removed

**Solution**:
```bash
# Create cleanup cron job
# Add to crontab: crontab -e
0 * * * * psql -d waddlebot -c "UPDATE entity_labels SET is_active = false WHERE expires_at < NOW() AND is_active = true;"

# Or run manual cleanup
curl -X POST http://localhost:8023/api/v1/admin/cleanup-expired
```

---

## Logging and Debugging

### Enable Debug Logging

```bash
# Set log level in .env
LOG_LEVEL=DEBUG

# Or set at runtime
export LOG_LEVEL=DEBUG
python app.py
```

### View Audit Logs

```bash
# Check AAA logs
tail -f /var/log/waddlebot/labels_core_module.log

# Filter for specific operations
grep "create_label" /var/log/waddlebot/labels_core_module.log
grep "apply_label" /var/log/waddlebot/labels_core_module.log

# Check error logs
grep "ERROR" /var/log/waddlebot/labels_core_module.log
```

### Database Query Logging

```sql
-- Enable query logging in PostgreSQL
ALTER DATABASE waddlebot SET log_statement = 'all';

-- View logs
tail -f /var/log/postgresql/postgresql-13-main.log
```

---

## Testing and Validation

### Validate Module Health

```bash
# Health check
curl http://localhost:8023/health

# Status check
curl http://localhost:8023/api/v1/status

# Database connectivity
psql postgresql://waddlebot:password@localhost:5432/waddlebot -c "SELECT 1;"
```

### Validate Data Integrity

```sql
-- Check for duplicate active labels
SELECT name, category, COUNT(*)
FROM labels
WHERE is_active = true
GROUP BY name, category
HAVING COUNT(*) > 1;

-- Check for label assignments exceeding limits
SELECT el.entity_id, el.entity_type, COUNT(*) as label_count
FROM entity_labels el
WHERE el.is_active = true
GROUP BY el.entity_id, el.entity_type
HAVING COUNT(*) > 10;

-- Check for invalid entity types
SELECT DISTINCT entity_type
FROM entity_labels
WHERE entity_type NOT IN ('user', 'module', 'community', 'item', 'event', 'memory', 'playlist', 'browser_source', 'command', 'alias', 'entityGroup');
```

---

## Emergency Procedures

### Module Crash Recovery

```bash
# 1. Check logs for errors
tail -100 /var/log/waddlebot/labels_core_module.log

# 2. Check database connectivity
psql -d waddlebot -c "SELECT 1;"

# 3. Restart module
pkill -f "python app.py"
python app.py &

# 4. Verify health
curl http://localhost:8023/health
```

### Database Corruption Recovery

```bash
# 1. Stop module
pkill -f "python app.py"

# 2. Backup database
pg_dump waddlebot > waddlebot_backup_$(date +%Y%m%d_%H%M%S).sql

# 3. Check database integrity
psql -d waddlebot -c "REINDEX DATABASE waddlebot;"

# 4. Restore from backup if needed
psql -d waddlebot < waddlebot_backup_20250115_120000.sql

# 5. Restart module
python app.py &
```

### Data Recovery

```sql
-- Recover soft-deleted labels
UPDATE labels
SET is_active = true
WHERE id = 123;

-- Recover soft-deleted assignments
UPDATE entity_labels
SET is_active = true
WHERE id = 456;
```

---

## Getting Help

### Information to Provide

When reporting issues, include:

1. **Module version**: `curl http://localhost:8023/api/v1/status | jq .data.version`
2. **Error message**: Full error text from logs
3. **Request details**: Full cURL command or code snippet
4. **Database version**: `psql --version`
5. **Python version**: `python --version`
6. **Environment**: Development/Staging/Production

### Support Channels

- GitHub Issues: [Waddles Issues](https://github.com/waddlebot/waddlebot/issues)
- Documentation: `/docs/labels_core_module/`
- Logs: `/var/log/waddlebot/labels_core_module.log`

### Useful Diagnostic Commands

```bash
# Complete diagnostic dump
cat > diagnostic.sh << 'EOF'
#!/bin/bash
echo "=== Module Status ==="
curl -s http://localhost:8023/api/v1/status | jq .

echo -e "\n=== Health Check ==="
curl -s http://localhost:8023/health | jq .

echo -e "\n=== Database Stats ==="
psql -d waddlebot -c "SELECT COUNT(*) FROM labels WHERE is_active = true;"
psql -d waddlebot -c "SELECT COUNT(*) FROM entity_labels WHERE is_active = true;"

echo -e "\n=== Recent Errors ==="
tail -20 /var/log/waddlebot/labels_core_module.log | grep ERROR

echo -e "\n=== Environment ==="
python --version
psql --version
echo "LOG_LEVEL: $LOG_LEVEL"
echo "DATABASE_URL: $DATABASE_URL"
EOF

chmod +x diagnostic.sh
./diagnostic.sh
```
