# Engagement Module — Troubleshooting Guide

## Database Connection Errors

### Symptoms
- Module fails to start with database connection error
- Logs show "Connection refused" or "No such file or directory"
- Health check returns 503 with database error

### Root Causes
1. PostgreSQL server not running
2. Incorrect database connection parameters
3. Firewall blocking database port
4. Database user credentials invalid

### Solutions

**Check PostgreSQL is Running**
```bash
# Docker: Check container status
docker ps | grep postgres

# Linux: Check service status
systemctl status postgresql

# Mac: Check if Postgres is running
brew services list | grep postgres
```

**Verify Connection Parameters**
```bash
# Test connection manually
psql postgres://waddlebot:password@localhost:5432/waddlebot

# Check environment variables
echo $DATABASE_URL
echo $DB_HOST $DB_PORT $DB_NAME $DB_USER
```

**Check Firewall**
```bash
# Linux: Check PostgreSQL port
sudo netstat -tulpn | grep 5432

# Allow port in firewall
sudo ufw allow 5432
```

**Verify Credentials**
```bash
# Create database if missing
createdb -h localhost -U waddlebot waddlebot

# Test user password
psql postgres://waddlebot:password@localhost:5432/waddlebot -c "SELECT 1"
```

### Prevention
- Always test database connection before deployment
- Use `.env` file to manage credentials
- Keep database server running in monitoring system

---

## JWT Token Validation Failures

### Symptoms
- API returns 401 "Invalid or expired token"
- All authenticated endpoints return 401
- Error: "token signature verification failed"

### Root Causes
1. JWT_SECRET not configured or mismatched
2. Token expired (older than JWT_EXPIRATION_HOURS)
3. Invalid token format
4. Wrong algorithm configured

### Solutions

**Verify JWT Secret**
```bash
# Check if JWT_SECRET is set
echo $JWT_SECRET

# Ensure it's the same across all services
# If changed, all old tokens become invalid

# Generate new secret if needed
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Check Token Expiration**
```bash
# Decode token to see expiration (without verification)
python3 << 'EOF'
import jwt
import json
from base64 import urlsafe_b64decode

token = "your-token-here"
parts = token.split('.')
payload = parts[1] + '=' * (4 - len(parts[1]) % 4)
decoded = urlsafe_b64decode(payload)
print(json.dumps(json.loads(decoded), indent=2))
EOF
```

**Verify Algorithm Configuration**
```bash
# Check algorithm matches token creation
echo $JWT_ALGORITHM

# Default: HS256 (HMAC with SHA-256)
# Should match token signing algorithm
```

**Generate New Token**
```bash
python3 << 'EOF'
import jwt
from datetime import datetime, timedelta

secret = "your-jwt-secret"
payload = {
    "user_id": 1,
    "username": "testuser",
    "exp": datetime.utcnow() + timedelta(hours=24)
}
token = jwt.encode(payload, secret, algorithm="HS256")
print(f"Authorization: Bearer {token}")
EOF
```

### Prevention
- Store JWT secrets in environment variables or secrets management system
- Implement token refresh mechanism
- Monitor token validation failures in logs

---

## Duplicate Vote Prevention Failures

### Symptoms
- User able to vote multiple times on same poll
- Vote count inconsistent with expected count
- Database constraint violations

### Root Causes
1. Race condition in concurrent requests
2. Incorrect vote check query
3. Database transaction isolation issues
4. Multiple instances not sharing state properly

### Solutions

**Verify Vote Check Logic**
```python
# Current implementation checks for existing vote:
existing = db(
    (db.poll_votes.poll_id == poll_id) &
    (db.poll_votes.user_id == user_id)
).select().first()

if existing:
    return jsonify({"error": "Already voted"}), 409
```

**Add Database Constraint**
```sql
-- Prevent duplicate votes at database level
ALTER TABLE poll_votes
ADD CONSTRAINT unique_user_poll_vote
UNIQUE (poll_id, user_id);
```

**Implement Optimistic Locking**
```python
# Add version field to polls table
# Increment on each vote
# Retry on version mismatch

poll = db(db.community_polls.id == poll_id).select().first()
current_version = poll.version

# Check again before insert
db.poll_votes.insert(
    poll_id=poll_id,
    option_id=option_id,
    user_id=user_id
)

# Update poll version
db(db.community_polls.id == poll_id).update(
    version=current_version + 1
)
```

**Monitor Concurrent Requests**
```bash
# Check for concurrent vote requests in logs
docker logs -f engagement-module | grep "vote"

# Use database transaction logs
sudo tail -f /var/log/postgresql/postgresql.log | grep "poll_votes"
```

### Prevention
- Add unique database constraint on (poll_id, user_id)
- Implement retry logic for concurrent requests
- Use database-level locking for critical operations

---

## Missing Form Data / Incomplete Submissions

### Symptoms
- Form submissions created but field values missing
- Empty submission records
- "values" object in response is empty

### Root Causes
1. Incorrect field ID in submission request
2. Field IDs changed after form creation
3. Transaction rolled back due to validation error
4. Form field values inserted but submission not committed

### Solutions

**Verify Field IDs Match**
```bash
# Get form with fields to get correct IDs
curl -X GET http://localhost:8091/api/v1/forms/12

# Use returned field IDs in submission
# Ensure keys in "values" object match field IDs exactly
```

**Check Field Existence**
```python
# Verify all field IDs exist before submission
required_fields = db(db.form_fields.form_id == form_id).select()
field_ids = [f.id for f in required_fields]

for field_id in request_values.keys():
    if int(field_id) not in field_ids:
        return jsonify({"error": f"Field {field_id} not found"}), 400
```

**Enable Debug Logging**
```bash
# Set log level to DEBUG
docker run -e LOG_LEVEL=DEBUG engagement-module:latest

# Monitor submission processing
docker logs -f engagement-module | grep "form_field_values"
```

**Check Database Directly**
```sql
-- Verify submission records exist
SELECT * FROM form_submissions WHERE form_id = 12;

-- Check field values
SELECT * FROM form_field_values WHERE submission_id = 95;

-- Count values per submission
SELECT submission_id, COUNT(*) as field_count
FROM form_field_values
GROUP BY submission_id;
```

### Prevention
- Return field IDs in form creation response
- Validate all field IDs before processing submission
- Use transactions to ensure atomicity (all-or-nothing)

---

## Performance Issues / Slow Requests

### Symptoms
- API responses slow (>1 second)
- High CPU usage on module container
- Database connection pool exhausted
- Memory usage growing

### Root Causes
1. Database connection pool too small
2. Missing database indexes
3. N+1 query problem (inefficient data loading)
4. Large result sets returned
5. Unoptimized queries

### Solutions

**Increase Connection Pool**
```bash
# Set in environment or .env
DB_POOL_SIZE=50  # Increase from default 10

# For high-traffic: 20-100 depending on load
# Monitor pool usage in logs
```

**Add Database Indexes**
```sql
-- Critical indexes for performance
CREATE INDEX idx_polls_community ON community_polls(community_id);
CREATE INDEX idx_polls_active ON community_polls(is_active, created_at);
CREATE INDEX idx_votes_poll ON poll_votes(poll_id);
CREATE INDEX idx_votes_user_poll ON poll_votes(user_id, poll_id);
CREATE INDEX idx_forms_community ON community_forms(community_id);
CREATE INDEX idx_forms_active ON community_forms(is_active, created_at);
CREATE INDEX idx_submissions_form ON form_submissions(form_id);
CREATE INDEX idx_submissions_user_form ON form_submissions(user_id, form_id);

-- Check index usage
SELECT schemaname, tablename, indexname
FROM pg_indexes
WHERE schemaname = 'public';
```

**Optimize Vote Count Queries**
```python
# Current: N queries (one per option)
for opt in opts:
    count = db(db.poll_votes.option_id == opt.id).count()
    vote_counts[opt.id] = count

# Better: Single aggregation query
from sqlalchemy import func
vote_counts = db.executesql(
    "SELECT option_id, COUNT(*) FROM poll_votes WHERE poll_id = ? GROUP BY option_id",
    [poll_id]
)
```

**Paginate Large Result Sets**
```python
# Don't return all submissions at once
submissions = db(db.form_submissions.form_id == form_id).select(
    limitby=(0, 100)  # First 100 results
)

# Add pagination parameters to API
@app.route("/api/v1/forms/<int:form_id>/submissions")
async def get_submissions(form_id: int):
    limit = request.args.get("limit", 100, type=int)
    offset = request.args.get("offset", 0, type=int)

    submissions = db(db.form_submissions.form_id == form_id).select(
        limitby=(offset, offset + limit)
    )
```

**Monitor Query Performance**
```bash
# Enable slow query logging in PostgreSQL
docker exec postgres psql -U waddlebot -d waddlebot -c \
  "ALTER SYSTEM SET log_min_duration_statement = 1000;"

# Reload configuration
docker exec postgres psql -U waddlebot -d waddlebot -c "SELECT pg_reload_conf();"

# Check slow queries
docker logs postgres | grep "duration:"
```

**Profile Module Performance**
```python
# Add timing to endpoints
import time

@app.route("/api/v1/polls/<int:poll_id>")
async def get_poll(poll_id: int):
    start = time.time()

    # ... endpoint logic ...

    elapsed = time.time() - start
    logger.info(f"get_poll({poll_id}) took {elapsed:.3f}s")

    if elapsed > 1.0:  # Alert on slow requests
        logger.warning(f"Slow request: get_poll({poll_id}) took {elapsed:.3f}s")
```

### Prevention
- Monitor response times in production
- Use APM tools (New Relic, Datadog) to detect bottlenecks
- Regularly review and optimize slow queries

---

## Memory Leaks / Memory Growth

### Symptoms
- Container memory usage constantly increasing
- Module crashes with out-of-memory error
- Slow degradation in performance over time

### Root Causes
1. Unbounded caches or collections
2. Database connection not closed properly
3. Circular references preventing garbage collection
4. Large requests not being garbage collected

### Solutions

**Monitor Memory Usage**
```bash
# Docker: Check memory usage
docker stats engagement-module

# Linux: Check process memory
ps aux | grep engagement | grep -v grep

# Watch memory growth over time
watch -n 5 'ps aux | grep engagement'
```

**Check Database Connections**
```python
# Verify connections are closed
# Add logging to connection lifecycle

@app.before_serving
async def startup():
    logger.info(f"Pool size: {db.pool_size}")

@app.after_serving
async def shutdown():
    db.close()
    logger.info("Database closed")
```

**Use Memory Profiler**
```bash
# Install memory profiler
pip install memory-profiler

# Profile module
python -m memory_profiler app.py

# Or use objgraph
pip install objgraph
```

**Check for Reference Cycles**
```python
import gc

@app.route("/debug/memory")
async def debug_memory():
    """Debug endpoint to check memory status."""
    gc.collect()

    import sys
    size = sys.getsizeof(db)

    return jsonify({
        "gc_stats": gc.get_stats(),
        "db_size": size
    })
```

### Prevention
- Use context managers for resource cleanup
- Monitor memory in staging environment before production
- Implement periodic restart in orchestration (graceful shutdown)

---

## Configuration Validation Errors

### Symptoms
- Module fails to start with "Config error"
- Log shows "Required configuration not properly set"
- Unknown environment variable ignored

### Root Causes
1. Missing required environment variables
2. Invalid port numbers
3. Mismatched secrets between environments
4. Typo in environment variable name

### Solutions

**Check Required Variables**
```bash
# These must be set in production:
# - MODULE_SECRET_KEY (not "change-me-in-production")
# - JWT_SECRET (not "jwt-secret-key-change-in-prod")
# - DATABASE_URL or all DB_* variables

# Verify they're set
echo "MODULE_SECRET_KEY=$MODULE_SECRET_KEY"
echo "JWT_SECRET=$JWT_SECRET"
echo "DATABASE_URL=$DATABASE_URL"
```

**Validate Port Numbers**
```bash
# Ports must be between 1-65535
# Check current configuration
echo "MODULE_PORT=$MODULE_PORT"
echo "GRPC_PORT=$GRPC_PORT"

# Ensure not already in use
sudo netstat -tulpn | grep -E ":(8091|50061)"
```

**Review Environment File**
```bash
# Check .env file syntax
cat .env

# Common issues:
# - Missing quotes around values with spaces
# - Invalid YAML syntax (if using YAML)
# - Typos in variable names

# Test loading .env
python3 -c "import os; os.load_dotenv(); print(os.environ.get('DATABASE_URL'))"
```

### Prevention
- Use configuration schema validation at startup
- Document all required variables with examples
- Implement pre-flight checks before starting module

---

## API Response Format Errors

### Symptoms
- Responses not valid JSON
- Content-Type header incorrect
- Client unable to parse response

### Root Causes
1. Exception thrown before jsonify
2. Wrong content-type header
3. Invalid JSON in response

### Solutions

**Check Response Content-Type**
```bash
# Inspect response headers
curl -v -X GET http://localhost:8091/health

# Should show: Content-Type: application/json
```

**Validate JSON Response**
```bash
# Test response is valid JSON
curl -s -X GET http://localhost:8091/health | jq .

# If jq fails, response is not valid JSON
```

**Review Error Handling**
```python
# All endpoints should return JSON
@app.route("/api/v1/polls/<int:poll_id>")
async def get_poll(poll_id: int):
    try:
        poll = db.community_polls[poll_id]
        if not poll:
            return jsonify({"error": "Poll not found"}), 404

        return jsonify({
            "success": True,
            "poll": format_poll(poll)
        })
    except Exception as e:
        logger.error(f"Get poll failed: {e}")
        return jsonify({"error": str(e)}), 500  # Always jsonify
```

### Prevention
- Test all endpoints with curl or Postman
- Use JSON schema validation in tests
- Monitor invalid response errors in logs

---

## Quick Diagnostic Checklist

1. **Module Running?**
   ```bash
   docker ps | grep engagement
   ```

2. **Health Check Passing?**
   ```bash
   curl -v http://localhost:8091/health
   ```

3. **Database Connected?**
   ```bash
   curl -s http://localhost:8091/health | jq .status
   ```

4. **JWT Secret Configured?**
   ```bash
   echo $JWT_SECRET | wc -c  # Should be >20 chars
   ```

5. **Database Migrations Run?**
   ```bash
   docker logs engagement-module | grep "tables initialized"
   ```

6. **Logs Show Errors?**
   ```bash
   docker logs engagement-module | grep ERROR
   ```

---

## Getting Help

1. **Check Recent Logs**
   ```bash
   docker logs --tail 100 engagement-module
   ```

2. **Enable Debug Logging**
   ```bash
   docker run -e LOG_LEVEL=DEBUG engagement-module:latest
   ```

3. **Test Endpoint Directly**
   ```bash
   curl -v -X GET http://localhost:8091/health
   ```

4. **Contact Support**
   - Email: support@penguintech.io
   - Documentation: See other docs in this directory

---

## Next Steps

- See [USAGE.md](USAGE.md) for deployment instructions
- See [CONFIGURATION.md](CONFIGURATION.md) for environment setup
- See [API.md](API.md) for endpoint documentation

**Company**: Penguin Tech Inc
**License**: Limited AGPL-3.0
**Last Updated**: 2026-02-16
