# Quote Interaction Module - Troubleshooting Guide

## Common Issues

### Module Startup Issues

#### Issue: Module Fails to Start - "Connection refused" on database

**Symptoms:**
```
Error: Connection refused at localhost:5432
Failed to connect to database
FATAL: could not connect to server
```

**Causes:**
- PostgreSQL server is not running
- DATABASE_URL environment variable is incorrect
- Database credentials are wrong
- Network connectivity issue

**Solutions:**

1. Verify PostgreSQL is running:
```bash
# macOS
brew services list | grep postgres

# Linux
sudo systemctl status postgresql

# Docker
docker ps | grep postgres
```

2. Check DATABASE_URL format:
```bash
echo $DATABASE_URL
# Expected: postgresql://user:password@host:port/database
```

3. Test database connectivity:
```bash
psql $DATABASE_URL -c "SELECT 1;"
# Should return: 1
```

4. Verify database credentials:
```bash
# From postgres container
docker exec postgres psql -U waddlebot -d waddlebot -c "SELECT 1;"
```

5. Restart PostgreSQL and module:
```bash
# If using Docker Compose
docker-compose restart postgres
docker-compose restart quote_interaction_module

# If local
brew services restart postgres  # or systemctl restart postgresql
python -m action.interactive.quote_interaction_module.app
```

---

#### Issue: Module Fails to Start - "relation quotes does not exist"

**Symptoms:**
```
psycopg2.errors.UndefinedTable: relation "quotes" does not exist
Migration 015 not applied
```

**Causes:**
- Database migrations have not been run
- Migration 015 (quotes table) was not executed

**Solutions:**

1. Run database migrations:
```bash
# From project root
python3 << 'EOF'
import sys
sys.path.insert(0, '/home/penguin/code/waddlebot')
from config.postgres.migrations import run_migrations
run_migrations()
print("Migrations completed")
EOF
```

2. Manually create the quotes table if migration fails:
```bash
psql $DATABASE_URL << 'EOF'
CREATE TABLE quotes (
    id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL,
    quote_text TEXT NOT NULL,
    quoted_user_id INTEGER,
    quoted_username VARCHAR(255),
    added_by_user_id INTEGER,
    platform VARCHAR(50),
    context TEXT,
    tags TEXT[],
    is_approved BOOLEAN DEFAULT TRUE,
    search_vector TSVECTOR GENERATED ALWAYS AS 
        (to_tsvector('english', quote_text)) STORED,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMP
);

CREATE INDEX idx_quotes_community_id ON quotes(community_id, deleted_at);
CREATE INDEX idx_quotes_approved ON quotes(community_id, is_approved) 
    WHERE deleted_at IS NULL;
CREATE INDEX idx_quotes_search_vector ON quotes USING GIN(search_vector);
EOF
```

3. Verify table was created:
```bash
psql $DATABASE_URL -c "\dt quotes"
psql $DATABASE_URL -c "\di" | grep quotes
```

---

### API Endpoint Issues

#### Issue: API Endpoint Returns 404 Not Found

**Symptoms:**
```
HTTP/1.1 404 Not Found
```

**Common Causes:**
- Incorrect endpoint URL
- Module is not running on expected port
- Path parameter is malformed

**Solutions:**

1. Verify module is running:
```bash
curl http://localhost:5012/health
# Should return 200 with health status

# If not found:
docker ps | grep quote
# If no container, start it:
docker-compose up -d quote_interaction_module
```

2. Check endpoint path:
```bash
# CORRECT:
curl http://localhost:5012/api/v1/quotes/search/1?q=test

# INCORRECT:
curl http://localhost:5012/quotes/search/1?q=test
curl http://localhost:5012/api/v2/quotes/search/1?q=test
```

3. Verify path parameters:
```bash
# CORRECT: integer community_id
curl http://localhost:5012/api/v1/quotes/list/42

# INCORRECT: string community_id
curl "http://localhost:5012/api/v1/quotes/list/my-community"
```

---

#### Issue: API Endpoint Returns 400 Bad Request

**Symptoms:**
```json
{
  "error": "Missing required fields: community_id, text",
  "status": "error"
}
```

**Causes:**
- Missing required JSON fields
- Malformed JSON
- Invalid parameter types
- Query string validation failed

**Solutions:**

1. Check required fields in POST body:
```bash
# WRONG - missing text field
curl -X POST http://localhost:5012/api/v1/quotes   -H "Content-Type: application/json"   -d '{"community_id": 1}'

# CORRECT - all required fields present
curl -X POST http://localhost:5012/api/v1/quotes   -H "Content-Type: application/json"   -d '{
    "community_id": 1,
    "text": "Quote here"
  }'
```

2. Validate JSON syntax:
```bash
# Use jq to validate
echo '{"community_id": 1, "text": "Quote"}' | jq .

# If invalid:
# parse error: Expected value (line 1)
```

3. Check search query minimum length:
```bash
# WRONG - query too short (must be >= 2 chars)
curl "http://localhost:5012/api/v1/quotes/search/1?q=a"

# CORRECT - query >= 2 chars
curl "http://localhost:5012/api/v1/quotes/search/1?q=test"
```

4. Verify query parameters are properly URL-encoded:
```bash
# WRONG - space in query
curl "http://localhost:5012/api/v1/quotes/search/1?q=hello world"

# CORRECT - space encoded as %20 or use single quotes
curl "http://localhost:5012/api/v1/quotes/search/1?q=hello%20world"
curl 'http://localhost:5012/api/v1/quotes/search/1?q=hello world'
```

---

#### Issue: API Endpoint Returns 500 Internal Server Error

**Symptoms:**
```json
{
  "error": "Internal server error",
  "status": "error"
}
```

**Causes:**
- Unhandled exception in code
- Database connection lost
- Out of memory
- Corrupted data

**Solutions:**

1. Check module logs:
```bash
# Docker logs
docker-compose logs -f quote_interaction_module

# Kubernetes logs
kubectl logs -f deployment/quote-interaction-module

# File logs (if configured)
tail -f /var/log/waddlebot/quote-module.log
```

2. Enable debug logging:
```bash
export LOG_LEVEL=DEBUG
python -m action.interactive.quote_interaction_module.app

# Look for stack trace in logs
```

3. Test database connectivity:
```bash
psql $DATABASE_URL -c "SELECT COUNT(*) FROM quotes;"

# If connection fails, see PostgreSQL issues section
```

4. Check module health:
```bash
curl -v http://localhost:5012/health
curl -v http://localhost:5012/metrics
```

5. Restart module:
```bash
docker-compose restart quote_interaction_module
```

---

### Search Issues

#### Issue: Full-Text Search Returns No Results

**Symptoms:**
```bash
curl "http://localhost:5012/api/v1/quotes/search/1?q=keyword"
# Returns: {"quotes": [], "total": 0}
```

**Causes:**
- No quotes exist in community
- search_vector column not populated
- Query doesn't match any quotes
- Quotes are soft-deleted (deleted_at is not NULL)

**Solutions:**

1. Verify quotes exist:
```bash
psql $DATABASE_URL -c "SELECT COUNT(*) FROM quotes WHERE community_id = 1;"
```

2. Check search_vector is populated:
```bash
psql $DATABASE_URL -c "SELECT id, quote_text, search_vector FROM quotes LIMIT 5;"
# search_vector should show tokens like: 'dog':1 'quick':2
```

3. Test search_vector generation:
```bash
psql $DATABASE_URL -c "
  SELECT id, quote_text, 
         to_tsvector('english', quote_text) as generated_vector
  FROM quotes 
  WHERE community_id = 1 
  LIMIT 5;
"
```

4. Manually search with psql to debug:
```bash
psql $DATABASE_URL << 'EOF'
SELECT id, quote_text 
FROM quotes 
WHERE community_id = 1 
  AND deleted_at IS NULL 
  AND search_vector @@ plainto_tsquery('english', 'keyword');
EOF
```

5. Create test quotes:
```bash
psql $DATABASE_URL << 'EOF'
INSERT INTO quotes (community_id, quote_text, created_at, updated_at)
VALUES 
  (1, 'The quick brown fox jumps', NOW(), NOW()),
  (1, 'Testing search functionality', NOW(), NOW()),
  (1, 'Another test quote', NOW(), NOW());
EOF

# Now search should work
curl "http://localhost:5012/api/v1/quotes/search/1?q=quick"
```

---

#### Issue: Author Search Returns Wrong Results

**Symptoms:**
```bash
# Searching for "Jobs"
curl "http://localhost:5012/api/v1/quotes/author/1?author=Jobs"
# Returns quotes by "Bobby Jobs" but not "Steve Jobs"
```

**Causes:**
- Case sensitivity issues
- ILIKE pattern matching behavior
- Database encoding issues

**Solutions:**

1. Check exact author names in database:
```bash
psql $DATABASE_URL -c "
  SELECT DISTINCT quoted_username 
  FROM quotes 
  WHERE community_id = 1 
  ORDER BY quoted_username;
"
```

2. Test ILIKE pattern matching:
```bash
psql $DATABASE_URL -c "
  SELECT quoted_username 
  FROM quotes 
  WHERE quoted_username ILIKE '%Jobs%'
  LIMIT 5;
"
```

3. Try exact match first:
```bash
curl "http://localhost:5012/api/v1/quotes/author/1?author=Steve%20Jobs"
```

4. Check for leading/trailing spaces:
```bash
psql $DATABASE_URL -c "
  SELECT id, 'X' || quoted_username || 'X' as quoted_name
  FROM quotes 
  WHERE community_id = 1 
  LIMIT 5;
"
```

---

### Performance Issues

#### Issue: Search Queries Are Slow

**Symptoms:**
- Search takes > 1 second
- `GET /api/v1/quotes/search/<community_id>?q=...` is slow

**Causes:**
- Missing search_vector index
- Index corruption
- Too many quotes in community
- Database not optimized

**Solutions:**

1. Check if search_vector index exists:
```bash
psql $DATABASE_URL -c "
  SELECT indexname, indexdef 
  FROM pg_indexes 
  WHERE tablename = 'quotes' AND indexname LIKE '%search%';
"
```

2. Recreate index if missing:
```bash
psql $DATABASE_URL -c "
  CREATE INDEX idx_quotes_search_vector ON quotes USING GIN(search_vector);
"
```

3. Analyze index usage:
```bash
psql $DATABASE_URL << 'EOF'
EXPLAIN ANALYZE
SELECT * FROM quotes
WHERE community_id = 1 
  AND search_vector @@ plainto_tsquery('english', 'keyword');
EOF
```

4. Check table statistics:
```bash
psql $DATABASE_URL -c "ANALYZE quotes;"
```

5. Monitor query performance:
```bash
# Enable slow query log
ALTER SYSTEM SET log_min_duration_statement = 1000;
SELECT pg_reload_conf();

# Check logs for slow queries
tail -f /var/log/postgresql/postgresql.log
```

---

#### Issue: High Database Connection Pool Usage

**Symptoms:**
- "too many connections" errors
- Module performance degrades under load
- Database refuses new connections

**Causes:**
- DB_POOL_SIZE too small
- Connections not being released
- Database has low max_connections setting

**Solutions:**

1. Increase connection pool:
```bash
export DB_POOL_SIZE=20
# Then restart module
docker-compose restart quote_interaction_module
```

2. Check current connections:
```bash
psql postgresql://postgres@localhost/postgres -c "
  SELECT datname, count(*) as connections 
  FROM pg_stat_activity 
  GROUP BY datname;
"
```

3. Monitor connection usage:
```bash
# Watch connections in real-time
watch "psql postgresql://postgres@localhost/postgres -c 'SELECT datname, count(*) FROM pg_stat_activity GROUP BY datname;'"
```

4. Increase PostgreSQL max_connections:
```bash
# In postgresql.conf
max_connections = 200

# Then restart PostgreSQL
sudo systemctl restart postgresql
```

---

### Deployment Issues

#### Issue: Module Not Accessible After Docker Deployment

**Symptoms:**
```
Cannot connect to http://localhost:5012
docker ps shows container running
```

**Causes:**
- Port mapping is incorrect
- Container is not listening on correct port
- Network isolation issue

**Solutions:**

1. Verify container port mapping:
```bash
docker ps | grep quote
# Should show: 0.0.0.0:5012->5012/tcp

# If not, check docker-compose.yml:
# ports:
#   - "5012:5012"
```

2. Check if container is listening:
```bash
docker exec quote_interaction_module netstat -tlnp | grep 5012
# Should show listening on 0.0.0.0:5012
```

3. Test from inside container:
```bash
docker exec quote_interaction_module curl http://localhost:5012/health
```

4. Check container logs for startup errors:
```bash
docker logs quote_interaction_module
```

5. Restart container with debugging:
```bash
docker-compose up -d --no-deps --build quote_interaction_module
docker-compose logs -f quote_interaction_module
```

---

## Debug Commands Reference

### Health & Status

```bash
# Health check
curl http://localhost:5012/health

# Module status
curl http://localhost:5012/api/v1/status

# Prometheus metrics
curl http://localhost:5012/metrics

# Check if port is in use
lsof -i :5012
netstat -tlnp | grep 5012
```

### Database Debugging

```bash
# Connect to database
psql $DATABASE_URL

# List tables
psql $DATABASE_URL -c "\dt"

# Check quotes table
psql $DATABASE_URL -c "SELECT COUNT(*) FROM quotes;"

# View quote schema
psql $DATABASE_URL -c "\d quotes"

# Check indices
psql $DATABASE_URL -c "\di" | grep quotes

# Test full-text search
psql $DATABASE_URL -c "
  SELECT * FROM quotes 
  WHERE search_vector @@ plainto_tsquery('english', 'test');
"
```

### Logging & Diagnostics

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# View application logs
docker-compose logs -f quote_interaction_module

# View PostgreSQL logs
docker-compose logs -f postgres

# Follow all logs
docker-compose logs -f

# View specific error
grep "ERROR" /var/log/waddlebot/quote-module.log
```

### Module Restart & Recovery

```bash
# Soft restart (reload config)
kill -HUP $(pgrep -f quote_interaction_module)

# Hard restart
docker-compose restart quote_interaction_module

# Full restart with rebuild
docker-compose down
docker-compose up -d quote_interaction_module
```

## Getting Help

If issues persist after troubleshooting:

1. Check [CONFIGURATION.md](CONFIGURATION.md) for correct setup
2. Review [ARCHITECTURE.md](ARCHITECTURE.md) for system design
3. See [TESTING.md](TESTING.md) for validation procedures
4. Enable DEBUG logging and capture full error traces
5. Contact WaddleBot support with:
   - Full error logs
   - Environment variables (without secrets)
   - Recent changes
   - Module version
