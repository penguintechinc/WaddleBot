# Alias Interaction Module — Troubleshooting

## Quick Diagnosis

### Health Check

```bash
# Check if service is running
curl http://localhost:8010/health

# Expected response (200 OK):
{
  "status": "healthy",
  "service": "alias_interaction_module",
  "version": "2.0.0",
  "uptime_seconds": 3600,
  "database": "connected"
}
```

### View Recent Logs

```bash
# Docker container logs
docker logs --tail 50 -f alias-interaction

# Direct Python logs
tail -f /var/log/waddlebotlog/alias_interaction_module.log

# System journal (if running as service)
journalctl -u alias-interaction -n 50 -f
```

---

## Common Issues

## Issue 1: Service Won't Start

### Symptom
```
ERROR: alias_interaction_module failed to start
Connection refused / Address already in use / Database error
```

### Diagnosis

```bash
# Check if port is in use
lsof -i :8010

# Check database connectivity
psql $DATABASE_URL -c "SELECT 1"

# Check environment variables
env | grep -E "MODULE|DATABASE"

# Check Python version
python3 --version  # Should be 3.12+
```

### Solutions

**Port In Use:**
```bash
# Find process using port 8010
lsof -i :8010
# Kill the process
kill -9 <PID>

# Or use different port
export MODULE_PORT=8011
python3 app.py
```

**Database Connection Failed:**
```bash
# Verify DATABASE_URL format
echo $DATABASE_URL

# Test connection
psql -U waddlebot -h localhost -d waddlebot -c "SELECT 1"

# Check PostgreSQL is running
sudo systemctl status postgresql
sudo systemctl start postgresql

# If remote database, check network
ping <database-host>
nc -zv <database-host> 5432
```

**Missing Dependencies:**
```bash
# Reinstall requirements
cd action/interactive/alias_interaction_module
pip install --upgrade -r requirements.txt

# Verify Flask core library is installed
python3 -c "from flask_core import setup_aaa_logging; print('OK')"
```

---

## Issue 2: Database Connection Errors

### Symptom
```
psycopg2.OperationalError: could not connect to server
FATAL: Ident authentication failed
```

### Diagnosis

```bash
# Test database credentials
psql postgresql://user:password@host:5432/database

# Check connection string format
echo "DATABASE_URL: $DATABASE_URL"

# Test with psql directly
psql -U waddlebot -h localhost -d waddlebot -W

# Check database exists
psql -U postgres -c "\l" | grep waddlebot

# Check user permissions
psql -U postgres -c "\du" | grep waddlebot
```

### Solutions

**Wrong Credentials:**
```bash
# Verify credentials
psql -U waddlebot -h localhost -d waddlebot -W
# Enter password when prompted

# Reset password if needed
sudo -u postgres psql -c "ALTER USER waddlebot WITH PASSWORD 'new_password';"

# Update connection string
export DATABASE_URL="postgresql://waddlebot:new_password@localhost:5432/waddlebot"
```

**Connection Timeout:**
```bash
# Increase timeout
export DATABASE_URL="postgresql://user:pass@host:5432/db?connect_timeout=15"

# Check firewall
sudo iptables -L | grep 5432

# Check PostgreSQL listening
sudo netstat -tlnp | grep postgres
```

**Database Doesn't Exist:**
```bash
# Create database
sudo -u postgres createdb -O waddlebot waddlebot

# Run migrations
psql -U waddlebot -d waddlebot -f /path/to/migrations.sql
```

---

## Issue 3: Alias Not Found / Execute Returns None

### Symptom
```
POST /api/v1/aliases/execute returns 404
Alias "test_alias" does not exist
```

### Diagnosis

```bash
# Check if alias exists
curl "http://localhost:8010/api/v1/aliases?community_id=YOUR_COMMUNITY"

# Check database directly
psql $DATABASE_URL \
  -c "SELECT alias_name, is_active FROM aliases WHERE alias_name = 'test_alias'"

# Check community_id matches
curl "http://localhost:8010/api/v1/aliases?community_id=wrong_community"
```

### Solutions

**Alias Not Created:**
```bash
# Create the alias
curl -X POST http://localhost:8010/api/v1/aliases \
  -H "Content-Type: application/json" \
  -d '{
    "community_id": "community-123",
    "alias_name": "test_alias",
    "command": "echo test",
    "created_by": "admin"
  }'

# Verify it was created
curl "http://localhost:8010/api/v1/aliases?community_id=community-123"
```

**Typo in Alias Name:**
```bash
# Check exact name (case-sensitive)
curl "http://localhost:8010/api/v1/aliases?community_id=community-123" | jq '.data[].alias_name'

# Use exact name in execute request
curl -X POST http://localhost:8010/api/v1/aliases/execute \
  -d '{"alias_name": "EXACT_NAME", "user": "user", "args": []}'
```

**Alias Was Deleted:**
```bash
# Check is_active flag
psql $DATABASE_URL \
  -c "SELECT id, alias_name, is_active FROM aliases WHERE alias_name = 'test_alias'"

# If is_active = false, recreate it
# Or restore from backup
```

**Wrong Community ID:**
```bash
# Verify community_id in request matches database
curl "http://localhost:8010/api/v1/aliases?community_id=correct-community-id"
```

---

## Issue 4: Variable Substitution Not Working

### Symptom
```
Command returns with literal {user}, {arg1}, etc. not expanded
```

### Diagnosis

```bash
# Check alias command
curl "http://localhost:8010/api/v1/aliases?community_id=community-1" \
  | jq '.data[] | select(.alias_name == "test") | .command'

# Test execute request
curl -X POST http://localhost:8010/api/v1/aliases/execute \
  -H "Content-Type: application/json" \
  -d '{
    "alias_name": "test",
    "user": "john_doe",
    "args": ["arg1", "arg2"]
  }' | jq '.data.command'
```

### Solutions

**Missing User Parameter:**
```bash
# Ensure user is provided in request
curl -X POST http://localhost:8010/api/v1/aliases/execute \
  -d '{"alias_name": "test", "user": "required_user", "args": []}'
```

**Args Array Format:**
```bash
# Use JSON array format, not string
# Correct:
{"args": ["arg1", "arg2", "arg3"]}

# Incorrect:
{"args": "arg1 arg2 arg3"}
```

**Check Variable Names (Case-Sensitive):**
```bash
# Variable names are case-sensitive
{user}   # Correct
{User}   # Incorrect - will not be replaced
{USER}   # Incorrect - will not be replaced

# Supported variables:
{user}      # Current user
{args}      # All args space-separated
{arg1}      # First arg
{arg2}      # Second arg
{all_args}  # Same as {args}
```

**Escape Special Characters:**
```bash
# If command contains quotes or special chars
"command": "echo 'user: {user}' "quoted""

# Test substitution
curl -X POST http://localhost:8010/api/v1/aliases/execute \
  -d '{"alias_name": "test", "user": "value", "args": []}' \
  | jq '.data.command'
```

---

## Issue 5: Redis Connection Problems

### Symptom
```
WARNING: Failed to connect to Redis
Credential listener not started
```

### Diagnosis

```bash
# Check REDIS_URL is set
echo $REDIS_URL

# Test Redis connectivity
redis-cli -u $REDIS_URL ping
# Expected: PONG

# Check Redis is running
sudo systemctl status redis-server

# Check network connectivity
ping <redis-host>
nc -zv <redis-host> 6379
```

### Solutions

**Redis Not Running:**
```bash
# Start Redis
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Or start via Docker
docker run -d -p 6379:6379 redis:latest
```

**Wrong Connection String:**
```bash
# Verify Redis URL format
redis://[user]:[password]@host:port/db

# Test with redis-cli
redis-cli -u "redis://localhost:6379/0" ping

# Update environment variable
export REDIS_URL="redis://localhost:6379/0"
```

**Redis Listener Not Required:**
```bash
# If Redis is optional, leaving REDIS_URL empty is fine
unset REDIS_URL
# Service will start without credential listener

# Check logs
LOG_LEVEL=INFO python3 app.py 2>&1 | grep -i redis
```

---

## Issue 6: High Memory Usage

### Symptom
```
Container/process using more than expected memory
Memory leaks or growing memory usage
```

### Diagnosis

```bash
# Check memory usage
ps aux | grep app.py

# Monitor over time
watch -n 1 'ps aux | grep app.py'

# Check connections
netstat -anp | grep 8010

# View database connections
psql $DATABASE_URL -c "SELECT count(*) FROM pg_stat_activity;"
```

### Solutions

**Connection Leaks:**
```bash
# Limit concurrent connections in DATABASE_URL
export DATABASE_URL="postgresql://user:pass@host:5432/db?pool_size=10&max_overflow=5"

# Check for unclosed connections in code
# Ensure all database operations use async/await properly
```

**Reduce Worker Count:**
```bash
# Use fewer workers
hypercorn app:app --bind 0.0.0.0:8010 --workers 2

# Or in docker-compose
command: hypercorn app:app --bind 0.0.0.0:8010 --workers 2
```

**Enable Connection Pooling:**
```python
# In config.py or PyDAL configuration
pool_size=10
max_overflow=20
pool_recycle=3600
```

---

## Issue 7: Slow Performance / High Latency

### Symptom
```
Requests taking >1 second
list_aliases endpoint is slow
```

### Diagnosis

```bash
# Measure endpoint latency
time curl "http://localhost:8010/api/v1/aliases?community_id=test"

# Check database query performance
psql $DATABASE_URL \
  -c "EXPLAIN ANALYZE SELECT * FROM aliases WHERE community_id = 'test' AND is_active = true;"

# Check database load
psql $DATABASE_URL \
  -c "SELECT count(*) FROM aliases WHERE community_id = 'test';"

# Check index usage
psql $DATABASE_URL \
  -c "\d aliases"
```

### Solutions

**Missing Indexes:**
```sql
-- Create indexes if missing
CREATE INDEX idx_aliases_community ON aliases(community_id, is_active);
CREATE INDEX idx_aliases_name ON aliases(alias_name, is_active);
```

**Too Many Aliases:**
```bash
# Implement pagination
# Archive old aliases
# Consider caching with Redis

# Delete inactive aliases (after backup)
psql $DATABASE_URL -c "DELETE FROM aliases WHERE is_active = false AND created_at < NOW() - INTERVAL '90 days';"
```

**Database Server Overloaded:**
```bash
# Check database server resources
top -p <postgres_pid>

# Check for long-running queries
psql $DATABASE_URL \
  -c "SELECT pid, now() - pg_stat_activity.query_start AS duration, query FROM pg_stat_activity WHERE state != 'idle' AND query NOT LIKE '%idle%';"

# Increase database resources
# Scale database vertically or horizontally
```

**Increase Hypercorn Workers:**
```bash
# More workers for high concurrency
hypercorn app:app --bind 0.0.0.0:8010 --workers 8
```

---

## Issue 8: Port Already in Use

### Symptom
```
Address already in use
OSError: [Errno 98] Address already in use
```

### Solutions

```bash
# Find process using port 8010
lsof -i :8010
# Output shows PID and command

# Kill the process
kill -9 <PID>

# Or use different port
export MODULE_PORT=8011
python3 app.py

# Or restart the service
sudo systemctl restart alias-interaction
```

---

## Issue 9: Docker Container Exits Immediately

### Symptom
```
docker run alias-interaction -> exits with code 1
Container starts then stops
```

### Diagnosis

```bash
# Check logs
docker logs alias-interaction
docker logs --tail 100 -f alias-interaction

# Check configuration
docker inspect alias-interaction | jq '.[0].Config.Env'

# Test container startup with override
docker run -it alias-interaction /bin/bash
```

### Solutions

**Missing Environment Variables:**
```bash
docker run -d \
  -e DATABASE_URL="postgresql://..." \
  -e MODULE_PORT=8010 \
  -e LOG_LEVEL=INFO \
  alias-interaction
```

**Database Not Ready:**
```yaml
# Use depends_on with healthcheck
services:
  postgres:
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U waddlebot"]
      interval: 5s
      timeout: 5s
      retries: 10
  
  alias-interaction:
    depends_on:
      postgres:
        condition: service_healthy
```

**Check Application Logs:**
```bash
docker run -it \
  -e DATABASE_URL="postgresql://..." \
  -e LOG_LEVEL=DEBUG \
  alias-interaction
```

---

## Debug Mode

### Enable Debug Logging

```bash
# Set verbose logging
export LOG_LEVEL=DEBUG
python3 app.py

# Or with Docker
docker run -e LOG_LEVEL=DEBUG alias-interaction
```

### View Request Details

```python
# Add to app.py for debugging
@app.before_request
async def log_request():
    import flask
    app.logger.debug(f"Request: {flask.request.method} {flask.request.path}")
    app.logger.debug(f"Headers: {dict(flask.request.headers)}")
```

### Database Query Debugging

```bash
# Enable PostgreSQL query logging
psql $DATABASE_URL \
  -c "ALTER SYSTEM SET log_statement = 'all';"

sudo systemctl reload postgresql
tail -f /var/log/postgresql/postgresql.log
```

---

## Getting Help

### Collect Diagnostic Information

```bash
#!/bin/bash
echo "=== Environment ===" 
env | grep -E "MODULE|DATABASE|REDIS"

echo "=== Service Status ===" 
curl -s http://localhost:8010/health | jq '.'

echo "=== Recent Logs ===" 
tail -20 /var/log/waddlebotlog/alias_interaction_module.log

echo "=== Database Status ===" 
psql $DATABASE_URL -c "SELECT version();"

echo "=== Container Info (if Docker) ===" 
docker ps --filter name=alias
docker inspect alias-interaction | jq '.[0].State'
```

### Contact Support

- **Email:** support@penguintech.io
- **Status:** https://status.penguintech.io
- **Documentation:** https://docs.penguintech.io
- **GitHub Issues:** Report in repository

Include diagnostic output when requesting help.
