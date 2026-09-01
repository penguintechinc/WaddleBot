# Clip Interaction Module - Troubleshooting Guide

Common issues, diagnostics, and solutions for the Clip Interaction Module.

## Table of Contents

1. [Startup Issues](#startup-issues)
2. [Database Problems](#database-problems)
3. [API Errors](#api-errors)
4. [Performance Issues](#performance-issues)
5. [Integration Problems](#integration-problems)
6. [Cache Issues](#cache-issues)
7. [Diagnostic Commands](#diagnostic-commands)

## Startup Issues

### Module Fails to Start - Port Already in Use

**Symptom:**

```
ERROR: Address already in use: 0.0.0.0:8098
```

**Cause**: Another process is listening on port 8098.

**Solution:**

```bash
# Find process using port 8098
lsof -i :8098
# or
netstat -tlnp | grep 8098

# Kill the process
kill -9 <PID>

# Or change MODULE_PORT
export MODULE_PORT=8099
hypercorn app.py --bind 0.0.0.0:8099
```

### Module Fails to Start - Database Connection Error

**Symptom:**

```
CRITICAL: Failed to connect to database
PostgreSQL connection timeout after 30s
```

**Cause**: Database unreachable or credentials wrong.

**Solution:**

```bash
# Verify DATABASE_URL format
echo $DATABASE_URL
# Should be: postgresql://user:password@host:5432/dbname

# Test connection directly
psql "$DATABASE_URL"

# If using Docker, verify container is running
docker ps | grep postgres

# Check network connectivity
nc -zv db.host 5432

# View detailed logs
docker logs waddlebot-clip-interaction 2>&1 | tail -50
```

### Module Fails to Start - Secret Key Generation Error

**Symptom:**

```
WARNING: Could not generate SECRET_KEY
```

**Solution:**

Provide explicit SECRET_KEY:

```bash
export SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
echo "Generated SECRET_KEY: $SECRET_KEY"
hypercorn app.py
```

## Database Problems

### Database Connection Pool Exhausted

**Symptom:**

```
Error: QueuePool limit exceeded (max 20)
All database connections in use, timeout waiting for free connection
```

**Cause**: Too many concurrent queries or slow queries holding connections.

**Solution:**

```bash
# Check current connections
psql $DATABASE_URL -c "SELECT count(*) as connections FROM pg_stat_activity WHERE datname='waddlebot';"

# View long-running queries
psql $DATABASE_URL -c "SELECT pid, usename, duration, query FROM pg_stat_statements WHERE duration > 5000;"

# Increase pool size in code (requires code change)
db = DAL(DATABASE_URL, pool_size=30)

# Kill long-running queries
psql $DATABASE_URL -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE duration > 60000;"
```

### Unique Constraint Violation on Bookmark

**Symptom:**

```
Error 409: Clip already bookmarked
UNIQUE constraint failed: clip_bookmarks.community_id, clip_bookmarks.clip_id
```

**Cause**: Attempting to bookmark a clip that's already bookmarked in this community.

**Solution**:

Check if clip already exists:

```bash
COMMUNITY_ID="550e8400-e29b-41d4-a716-446655440000"
CLIP_ID="twitch_clip_abc"

# Query clips
curl "http://localhost:8098/api/v1/clips/$COMMUNITY_ID" \
  -H "Authorization: Bearer $TOKEN" | jq --arg cid "$CLIP_ID" \
  '.clips[] | select(.clip_id == $cid)'

# If exists, either update tags or get clip ID
# Update tags instead of re-bookmarking
```

### Table Does Not Exist / Migration Failed

**Symptom:**

```
Error: Relation "clip_bookmarks" does not exist
```

**Cause**: Database migrations not run.

**Solution**:

```bash
# Run migrations manually
python3 -c "from app.models import db; db.executescript('migrations/*.sql')"

# Or check migration status
psql $DATABASE_URL -c "SELECT * FROM schema_migrations ORDER BY version;"

# View available migrations
ls migrations/ | sort

# Apply specific migration
psql $DATABASE_URL -f migrations/001_create_clip_bookmarks.sql
```

## API Errors

### 401 Unauthorized - Invalid Token

**Symptom:**

```json
{
  "error": "UNAUTHORIZED",
  "message": "Invalid or expired token"
}
```

**Cause**: Missing, expired, or malformed JWT token.

**Solution**:

```bash
# Verify token is in request
curl -v http://localhost:8098/api/v1/clips/123 \
  -H "Authorization: Bearer $TOKEN" 2>&1 | grep Authorization

# Check token format (should be 3 parts separated by dots)
echo $TOKEN | awk -F. '{print "Parts: " NF}'

# Decode JWT header
echo $TOKEN | cut -d. -f1 | base64 -d | jq .

# Decode JWT payload
echo $TOKEN | cut -d. -f2 | base64 -d | jq .

# Check expiration time
EXP=$(echo $TOKEN | cut -d. -f2 | base64 -d | jq '.exp')
NOW=$(date +%s)
if [ $EXP -lt $NOW ]; then echo "Token expired"; else echo "Token valid"; fi

# Get fresh token
TOKEN=$(curl -s -X POST http://core-api:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"pass"}' | jq -r '.token')
```

### 404 Not Found - Community Doesn't Exist

**Symptom:**

```json
{
  "error": "COMMUNITY_NOT_FOUND",
  "message": "Community 123... does not exist"
}
```

**Cause**: Invalid community ID or user doesn't have access.

**Solution**:

```bash
# Verify community exists
COMMUNITY_ID="550e8400-e29b-41d4-a716-446655440000"

curl http://core-api:8000/api/v1/communities/$COMMUNITY_ID \
  -H "Authorization: Bearer $TOKEN"

# Check user's communities
curl http://core-api:8000/api/v1/user/communities \
  -H "Authorization: Bearer $TOKEN" | jq '.communities[] | .id'

# Verify community ID format (should be UUID)
echo $COMMUNITY_ID | grep -E '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
```

### 409 Conflict - Duplicate Bookmark

**Symptom:**

```json
{
  "error": "CONFLICT",
  "message": "Clip already bookmarked in this community"
}
```

**Solution**:

Either update existing bookmark or use different clip:

```bash
COMMUNITY_ID="550e8400-e29b-41d4-a716-446655440000"
CLIP_ID="twitch_clip_abc"

# Find existing bookmark
BOOKMARK_ID=$(curl -s "http://localhost:8098/api/v1/clips/$COMMUNITY_ID" \
  -H "Authorization: Bearer $TOKEN" | jq -r --arg cid "$CLIP_ID" \
  '.clips[] | select(.clip_id == $cid) | .id')

# Update tags instead
curl -X PUT http://localhost:8098/api/v1/clips/$COMMUNITY_ID/$BOOKMARK_ID/tags \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tags": ["new-tag"]}'
```

### 422 Validation Error - Invalid Tags

**Symptom:**

```json
{
  "error": "VALIDATION_ERROR",
  "message": "Tags: use lowercase alphanumeric and hyphens only"
}
```

**Cause**: Tags contain invalid characters.

**Solution**:

```bash
# Valid tags: lowercase, alphanumeric, hyphens
VALID_TAGS=["clutch-play", "eco-round", "5k-ace"]

# Invalid tags (will be rejected)
INVALID_TAGS=["Clutch!", "eco_round", "5K Ace"]

# Correct tags before posting
curl -X POST http://localhost:8098/api/v1/clips/$COMMUNITY_ID/bookmark \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "clip_id": "clip123",
    "clip_url": "https://twitch.tv/clip/clip123",
    "title": "Amazing Play",
    "tags": ["clutch-play", "tournament", "highlights"]
  }'
```

### 503 Service Unavailable - Twitch Module Unreachable

**Symptom:**

```json
{
  "error": "SERVICE_UNAVAILABLE",
  "message": "action-twitch service temporarily unavailable"
}
```

**Cause**: action-twitch module down or network issue.

**Solution**:

```bash
# Check if Twitch module is running
curl http://action-twitch:8010/health

# Verify network connectivity
ping -c 3 action-twitch

# Check Docker network
docker network inspect waddlebot

# View Twitch module logs
docker logs waddlebot-action-twitch

# Retry clip creation (implement exponential backoff)
for attempt in 1 2 3; do
  if curl -X POST http://localhost:8098/api/v1/clips/$COMMUNITY_ID/create \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{...}'; then
    break
  fi
  sleep $((attempt * 2))
done
```

## Performance Issues

### Slow Clip List Queries

**Symptom**: `GET /api/v1/clips/{cid}` takes >2 seconds

**Cause**: Missing indexes, large dataset, or slow database.

**Solution**:

```bash
# Verify indexes exist
psql $DATABASE_URL -c "SELECT indexname FROM pg_indexes WHERE tablename='clip_bookmarks';"

# Check query plan
psql $DATABASE_URL -c "EXPLAIN ANALYZE SELECT * FROM clip_bookmarks WHERE community_id='...' LIMIT 50;"
# Look for Sequential Scan (bad) vs Index Scan (good)

# Optimize: Use pagination
curl "http://localhost:8098/api/v1/clips/$COMMUNITY_ID?limit=50&offset=0" \
  -H "Authorization: Bearer $TOKEN"

# Check database performance
psql $DATABASE_URL -c "SELECT * FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"

# Enable query logging in PostgreSQL
psql $DATABASE_URL -c "ALTER SYSTEM SET log_min_duration_statement = 1000;"
psql $DATABASE_URL -c "SELECT pg_reload_conf();"

# View slow query log
tail -f /var/log/postgresql/postgresql.log | grep duration
```

### High Memory Usage

**Symptom**: Container memory exceeds 512Mi limit

**Cause**: Memory leak, large result sets, or many concurrent connections.

**Solution**:

```bash
# Check container memory
docker stats waddlebot-clip-interaction --no-stream

# Check Python memory usage
ps aux | grep python3

# Profile memory
python3 -m memory_profiler app.py

# Limit result sets
curl "http://localhost:8098/api/v1/clips/$COMMUNITY_ID?limit=50" \
  -H "Authorization: Bearer $TOKEN"

# Monitor connection pool
psql $DATABASE_URL -c "WATCH 'SELECT count(*) FROM pg_stat_activity;'"

# Restart service (last resort)
docker restart waddlebot-clip-interaction
```

### Cache Misses Causing DB Load

**Symptom**: High database load despite low request rate

**Cause**: Cache disabled or cache TTL too short.

**Solution**:

```bash
# Verify Redis is running
redis-cli ping

# Check cache configuration
echo $ENABLE_QUERY_CACHE
echo $CACHE_TTL_SECONDS

# Monitor cache hits/misses
redis-cli INFO stats | grep keyspace

# Force cache repopulation
for i in {0..100..50}; do
  curl "http://localhost:8098/api/v1/clips/$COMMUNITY_ID?limit=50&offset=$i" \
    -H "Authorization: Bearer $TOKEN" > /dev/null
done

# Check cache keys
redis-cli KEYS "clip:*"
```

## Integration Problems

### Core API Not Responding

**Symptom**:

```
Error: Failed to reach core-api after 3 retries
```

**Cause**: core-api down, network issue, or service URL misconfigured.

**Solution**:

```bash
# Verify core-api URL
echo $CORE_API_URL

# Test connectivity
curl -v $CORE_API_URL/health

# Check DNS resolution
nslookup core-api
dig core-api

# Test from inside container
docker exec waddlebot-clip-interaction curl http://core-api:8000/health

# View core-api logs
docker logs waddlebot-core-api

# Check Docker network connectivity
docker network inspect waddlebot | jq '.Containers'
```

### Router Service Not Publishing Events

**Symptom**: Events created but not appearing in logs/UI

**Cause**: Router unreachable or event format wrong.

**Solution**:

```bash
# Test router connectivity
curl -X POST $ROUTER_API_URL/api/v1/events \
  -H "Content-Type: application/json" \
  -d '{"type":"test","payload":{}}'

# Verify event was sent
docker logs waddlebot-router | grep "test"

# Check event format
curl -s $ROUTER_API_URL/api/v1/events/schema | jq .

# Monitor events in real-time
docker logs -f waddlebot-router | grep "clip"
```

### Twitch Module Returns Invalid Response

**Symptom**:

```json
{
  "error": "INVALID_RESPONSE",
  "message": "Twitch module returned malformed JSON"
}
```

**Cause**: action-twitch version mismatch or API change.

**Solution**:

```bash
# Verify action-twitch version
curl http://action-twitch:8010/version

# Check API compatibility
curl -X POST http://action-twitch:8010/api/v1/clips \
  -H "Content-Type: application/json" \
  -d '{"broadcast_id":"test","title":"test"}' | jq .

# Update clip_interaction_module to match action-twitch API
# Review action-twitch API documentation

# Log full response for debugging
DEBUG_TWITCH_RESPONSE=1 hypercorn app.py
```

## Cache Issues

### Redis Connection Fails

**Symptom**:

```
ERROR: Failed to connect to Redis
redis.connection.ConnectionError: Connection refused
```

**Cause**: Redis not running or REDIS_URL wrong.

**Solution**:

```bash
# Verify Redis is running
docker ps | grep redis

# Test connection
redis-cli ping

# Check REDIS_URL
echo $REDIS_URL

# Verify Redis port
netstat -tlnp | grep 6379

# Restart Redis
docker restart waddlebot-redis

# Disable caching if Redis unavailable
export ENABLE_QUERY_CACHE=false
hypercorn app.py
```

### Stale Cache Data

**Symptom**: Clips appear/disappear inconsistently

**Cause**: Cache TTL too long or cache not invalidating on writes.

**Solution**:

```bash
# Reduce cache TTL
export CACHE_TTL_SECONDS=60

# Clear cache manually
redis-cli FLUSHDB
redis-cli DEL "clip:*"

# Monitor cache operations
redis-cli MONITOR | grep clip

# Verify cache invalidation logic in code
grep -r "cache.*invalidate" src/
```

## Diagnostic Commands

### Health Check

```bash
# Module health
curl http://localhost:8098/health

# Database health
psql $DATABASE_URL -c "SELECT 1"

# Redis health
redis-cli ping

# All dependencies
curl -s http://localhost:8098/health/full | jq .
```

### View Logs

```bash
# Docker logs
docker logs waddlebot-clip-interaction -f

# View last 100 lines
docker logs waddlebot-clip-interaction --tail 100

# Search logs
docker logs waddlebot-clip-interaction 2>&1 | grep ERROR

# Timestamps
docker logs waddlebot-clip-interaction -t
```

### Database Diagnostics

```bash
# Connection count
psql $DATABASE_URL -c "SELECT count(*) FROM pg_stat_activity;"

# Table sizes
psql $DATABASE_URL -c "SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) FROM pg_tables ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;"

# Index usage
psql $DATABASE_URL -c "SELECT schemaname, tablename, indexname, idx_scan FROM pg_stat_user_indexes ORDER BY idx_scan DESC;"

# Vacuum/analyze status
psql $DATABASE_URL -c "SELECT * FROM pg_stat_user_tables ORDER BY last_vacuum DESC;"
```

### Performance Profiling

```bash
# Python profile
python3 -m cProfile -s cumulative app.py 2>&1 | head -20

# Async profiling
pip install py-spy
py-spy record -o profile.svg -- hypercorn app.py

# View profile
open profile.svg
```

### Network Debugging

```bash
# TCP connections
netstat -anp | grep 8098

# DNS resolution
nslookup localhost
dig +short core-api

# Network trace
tcpdump -i lo port 8098
```

## When to Escalate

Contact support if:

1. Database corruption suspected (constraint violations not from user action)
2. Unrecoverable data loss
3. Persistent 503 errors from all external services
4. Memory leaks despite restart
5. Security incidents or unauthorized access

**Support Contact**: support@penguintech.io

## Log File Locations

| Component | Log Path |
|-----------|----------|
| Container Logs | `docker logs waddlebot-clip-interaction` |
| PostgreSQL | `/var/log/postgresql/postgresql.log` |
| Redis | `/var/log/redis/redis-server.log` |
| Kubernetes | `kubectl logs -n waddlebot clip-interaction-xyz` |
