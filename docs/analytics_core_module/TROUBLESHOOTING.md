# Analytics Core Module — Troubleshooting Guide

**Version:** 1.0.0
**Last Updated:** 2026-02-16

---

## Table of Contents

1. [Module Won't Start](#module-wont-start)
2. [Database Connection Issues](#database-connection-issues)
3. [Missing Metrics & Events](#missing-metrics--events)
4. [High Latency Queries](#high-latency-queries)
5. [Bot Detection Issues](#bot-detection-issues)
6. [API Errors](#api-errors)
7. [Memory & Performance](#memory--performance)
8. [Logging & Debugging](#logging--debugging)
9. [Common Error Messages](#common-error-messages)

---

## Module Won't Start

### Port Already in Use

**Symptom:**
```
ERROR: Address already in use
Error binding to port 8040
```

**Diagnosis:**
```bash
# Check what's using port 8040
lsof -i :8040
# Output: nginx    1234  user    10u  IPv4  99999  0t0  TCP *:8040 (LISTEN)
```

**Solution:**

```bash
# Option 1: Kill the process using the port
kill -9 1234

# Option 2: Use a different port
export MODULE_PORT=8041
python app.py

# Option 3: Stop conflicting service
docker-compose down nginx
docker-compose up analytics-core
```

### Module Exits on Startup

**Symptom:**
```
Starting analytics-core on port 8040
Traceback (most recent call last):
  ...
SystemExit: 1
```

**Diagnosis:**

```bash
# Check startup logs
docker-compose logs analytics-core

# Check for database connection error
grep -i "database\|connection\|failed" docker-compose.logs
```

**Solution:**

```bash
# Verify DATABASE_URL is set
echo $DATABASE_URL

# Test database connection manually
psql $DATABASE_URL -c "SELECT 1;"

# If no output, check connection string format
# Expected: postgresql://user:pass@host:5432/dbname
```

### Missing Dependencies

**Symptom:**
```
ModuleNotFoundError: No module named 'quart'
```

**Solution:**

```bash
# Install dependencies
cd core/analytics_core_module
pip install -r requirements.txt

# Verify installation
python -c "import quart; print(quart.__version__)"

# In Docker, rebuild image
docker-compose build analytics-core
docker-compose up analytics-core
```

### Configuration Error

**Symptom:**
```
ValueError: Insecure SECRET_KEY in production
Error: DATABASE_URL required
```

**Solution:**

```bash
# Check .env file exists
ls -la .env

# Check required env vars are set
env | grep -E "DATABASE_URL|SECRET_KEY|MODULE_PORT"

# Set missing vars
export DATABASE_URL="postgresql://..."
export SECRET_KEY="$(openssl rand -hex 32)"
```

---

## Database Connection Issues

### Connection Timeout

**Symptom:**
```
psycopg2.OperationalError: could not connect to server: Connection timed out
```

**Diagnosis:**

```bash
# Test connectivity to database server
nc -zv postgres.example.com 5432

# Check if server is running
docker ps | grep postgres

# Check firewall rules
sudo iptables -L | grep 5432
```

**Solution:**

```bash
# If using Docker Compose, ensure postgres container is running
docker-compose ps postgres

# If missing, start it
docker-compose up -d postgres

# Check network connectivity
docker exec analytics-core ping postgres

# Verify DATABASE_URL is correct
echo $DATABASE_URL
# Should be: postgresql://user:pass@postgres:5432/waddlebot
```

### Authentication Failed

**Symptom:**
```
psycopg2.OperationalError: FATAL: password authentication failed
```

**Diagnosis:**

```bash
# Test with correct credentials
psql postgresql://waddlebot:waddlebot123@localhost:5432/waddlebot

# Check DATABASE_URL has correct password
echo $DATABASE_URL | grep -o ":[^@]*@" | head -c 50
```

**Solution:**

```bash
# Correct password in DATABASE_URL
export DATABASE_URL="postgresql://waddlebot:CORRECT_PASSWORD@postgres:5432/waddlebot"

# If password contains special characters, URL-encode them
# @ -> %40
# : -> %3A
# Example: "pass@word!" becomes "pass%40word%21"
```

### Database Doesn't Exist

**Symptom:**
```
psycopg2.OperationalError: FATAL: database "waddlebot" does not exist
```

**Solution:**

```bash
# Create database
createdb waddlebot

# Or via Docker
docker exec postgres createdb -U waddlebot waddlebot

# Run migrations
python -m alembic upgrade head
```

### Tables Don't Exist

**Symptom:**
```
psycopg2.ProgrammingError: relation "analytics_config" does not exist
```

**Solution:**

```bash
# Check if tables exist
psql $DATABASE_URL -c "\dt analytics_*"

# If empty, run migrations
cd core/analytics_core_module
python -m alembic upgrade head

# Or create tables manually
psql $DATABASE_URL -f schema.sql
```

### Connection Pool Exhaustion

**Symptom:**
```
QueuePool limit exceeded with overflow
```

**Diagnosis:**

```bash
# Check active connections
psql $DATABASE_URL -c "SELECT count(*) FROM pg_stat_activity;"

# Monitor connections over time
watch -n 5 'psql $DATABASE_URL -c "SELECT count(*) FROM pg_stat_activity;"'
```

**Solution:**

```bash
# Increase connection pool size in config
# In config.py
pool_size = 50        # Increase from default 20
max_overflow = 100    # Increase from default 40

# Kill idle connections
psql $DATABASE_URL -c "
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE state = 'idle'
AND query_start < NOW() - INTERVAL '30 minutes';
"
```

---

## Missing Metrics & Events

### Events Not Being Stored

**Symptom:**
```bash
curl http://localhost:8040/api/v1/analytics/123/basic
# Returns: total_chatters: 0
```

**Diagnosis:**

```bash
# Check if events table has data
psql $DATABASE_URL -c "
SELECT COUNT(*) FROM activity_message_events
WHERE community_id = 123;
"

# Check recent events
psql $DATABASE_URL -c "
SELECT * FROM activity_message_events
WHERE community_id = 123
ORDER BY created_at DESC
LIMIT 5;
"
```

**Solution:**

```bash
# Send test events to verify endpoint works
curl -X POST http://localhost:8040/api/v1/internal/events \
  -H "Content-Type: application/json" \
  -H "X-Service-API-Key: test-key" \
  -d '{
    "community_id": 123,
    "events": [
      {
        "event_type": "message",
        "platform": "discord",
        "platform_user_id": "test_user",
        "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",
        "metadata": {}
      }
    ]
  }'

# Check if event was stored
psql $DATABASE_URL -c "
SELECT * FROM activity_message_events
WHERE community_id = 123
ORDER BY created_at DESC LIMIT 1;
"
```

### Metrics Not Being Aggregated

**Symptom:**
```bash
curl http://localhost:8040/api/v1/analytics/123/metrics?metric_type=messages
# Returns: data: [], count: 0
```

**Diagnosis:**

```bash
# Check if raw events exist
psql $DATABASE_URL -c "
SELECT COUNT(*) FROM activity_message_events
WHERE community_id = 123
AND created_at >= NOW() - INTERVAL '7 days';
"

# Check if aggregated metrics exist
psql $DATABASE_URL -c "
SELECT COUNT(*) FROM analytics_metrics_timeseries
WHERE community_id = 123;
"

# Check last aggregation time
psql $DATABASE_URL -c "
SELECT MAX(timestamp_bucket) FROM analytics_metrics_timeseries
WHERE community_id = 123;
"
```

**Solution:**

```bash
# Manually trigger aggregation
curl -X POST http://localhost:8040/api/v1/internal/aggregate \
  -H "Content-Type: application/json" \
  -H "X-Service-API-Key: test-key" \
  -d '{
    "community_id": 123,
    "force": true
  }'

# Wait a few seconds for aggregation to complete
sleep 5

# Check metrics again
curl http://localhost:8040/api/v1/analytics/123/metrics?metric_type=messages
```

### Partial Data in Results

**Symptom:**
```bash
curl http://localhost:8040/api/v1/analytics/123/basic
# Returns: total_chatters: 50, but expected 500
```

**Diagnosis:**

```bash
# Verify data completeness
psql $DATABASE_URL -c "
SELECT
  COUNT(*) as total_events,
  COUNT(DISTINCT hub_user_id) as unique_users,
  MIN(created_at) as oldest_event,
  MAX(created_at) as newest_event
FROM activity_message_events
WHERE community_id = 123;
"
```

**Solution:**

```bash
# Resend events if data was incomplete
# Or check Router module is sending events correctly
curl http://localhost:8040/api/v1/analytics/123/config
# Verify basic_stats_enabled = true
```

---

## High Latency Queries

### Slow Basic Stats Query

**Symptom:**
```
Request took 5 seconds (expected < 500ms)
```

**Diagnosis:**

```bash
# Check explain plan
psql $DATABASE_URL -c "
EXPLAIN ANALYZE
SELECT COUNT(DISTINCT hub_user_id)
FROM activity_message_events
WHERE community_id = 123;
"

# Look for missing indexes
psql $DATABASE_URL -c "
SELECT * FROM pg_stat_user_indexes
WHERE schemaname = 'public'
AND tablename = 'activity_message_events';
"
```

**Solution:**

```bash
# Add indexes if missing
psql $DATABASE_URL -c "
CREATE INDEX CONCURRENTLY idx_activity_msg_community
ON activity_message_events(community_id);

CREATE INDEX CONCURRENTLY idx_activity_msg_user
ON activity_message_events(hub_user_id);

CREATE INDEX CONCURRENTLY idx_activity_msg_time
ON activity_message_events(created_at);
"

# Or combined index
psql $DATABASE_URL -c "
CREATE INDEX CONCURRENTLY idx_activity_msg_community_time
ON activity_message_events(community_id, created_at);
"
```

### Slow Metrics Query

**Symptom:**
```
Metrics query on 1 year of data takes 10 seconds
```

**Diagnosis:**

```bash
# Check metrics table size
psql $DATABASE_URL -c "
SELECT
  pg_size_pretty(pg_total_relation_size('analytics_metrics_timeseries')) as size,
  COUNT(*) as row_count
FROM analytics_metrics_timeseries;
"

# Check indexes
psql $DATABASE_URL -c "
SELECT * FROM pg_stat_user_indexes
WHERE tablename = 'analytics_metrics_timeseries';
"
```

**Solution:**

```bash
# Add composite index for query patterns
psql $DATABASE_URL -c "
CREATE INDEX CONCURRENTLY idx_metrics_query
ON analytics_metrics_timeseries(community_id, metric_type, timestamp_bucket)
WHERE bucket_size = '1d';
"

# Consider partitioning for large deployments
# Partition by community_id or timestamp
```

### High Database Load

**Symptom:**
```
Database CPU: 95%+
Connection pool near max
```

**Diagnosis:**

```bash
# Check what queries are slow
psql $DATABASE_URL -c "
SELECT query, mean_exec_time, max_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
"

# Monitor active connections
psql $DATABASE_URL -c "
SELECT usename, state, COUNT(*) as count
FROM pg_stat_activity
GROUP BY usename, state;
"
```

**Solution:**

```bash
# Enable query logging for slow queries
psql $DATABASE_URL -c "
ALTER SYSTEM SET log_min_duration_statement = 1000;
SELECT pg_reload_conf();
"

# Scale horizontally with read replicas
# Update read-only config for metrics queries

# Add Redis caching
export REDIS_URL="redis://redis:6379"
```

---

## Bot Detection Issues

### Bot Score Not Calculated

**Symptom:**
```bash
curl http://localhost:8040/api/v1/analytics/123/bot-score
# Returns 404 or cached: false, always recalculating
```

**Diagnosis:**

```bash
# Check if bot_scores table exists
psql $DATABASE_URL -c "SELECT * FROM analytics_bot_scores WHERE community_id = 123;"

# Check if data is being stored
psql $DATABASE_URL -c "SELECT COUNT(*) FROM analytics_bot_scores;"
```

**Solution:**

```bash
# Force recalculation
curl -X POST http://localhost:8040/api/v1/analytics/123/bot-score/calculate

# Check calculation worked
curl http://localhost:8040/api/v1/analytics/123/bot-score
# Should show: calculated_at, next_recalculation
```

### Bot Scores Always Return Same Value

**Symptom:**
```
Score always 50 (default/neutral)
```

**Diagnosis:**

```bash
# Check component scores
psql $DATABASE_URL -c "
SELECT component_scores FROM analytics_bot_scores
WHERE community_id = 123;
"

# Expected: {"bad_actor_score": 85, "reputation_score": 70, ...}
# If all 50s, service is returning defaults
```

**Solution:**

```bash
# Check service logs for errors
docker-compose logs analytics-core | grep -i "bot\|error"

# Verify required tables exist
psql $DATABASE_URL -c "
SELECT tablename FROM pg_tables
WHERE tablename LIKE 'analytics%' OR tablename LIKE 'activity%';
"

# Check Reputation service is accessible
curl http://reputation:8021/health
```

### Suspected Bots Not Detected

**Symptom:**
```bash
curl http://localhost:8040/api/v1/analytics/123/suspected-bots
# Returns: suspected_bots: []
```

**Diagnosis:**

```bash
# Check if suspected_bots table has data
psql $DATABASE_URL -c "
SELECT COUNT(*) FROM analytics_suspected_bots
WHERE community_id = 123;
"

# Check for bad actor alerts
psql $DATABASE_URL -c "
SELECT COUNT(*) FROM analytics_bad_actor_alerts
WHERE community_id = 123 AND status = 'pending';
"
```

**Solution:**

```bash
# Insert test suspected bot
psql $DATABASE_URL -c "
INSERT INTO analytics_suspected_bots (
  community_id, platform_user_id, confidence_score, detected_at
) VALUES (123, 'test_bot', 85, NOW());
"

# Query again
curl http://localhost:8040/api/v1/analytics/123/suspected-bots?limit=10&min_confidence=50
```

---

## API Errors

### 401 Unauthorized

**Symptom:**
```
curl http://localhost:8040/api/v1/analytics/123/basic
# Returns: 401 Unauthorized
```

**Solution:**

```bash
# Add authentication token (if required)
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8040/api/v1/analytics/123/basic

# Or check if Flask-Security-Too is configured
docker-compose logs analytics-core | grep -i "auth\|security"
```

### 403 Forbidden

**Symptom:**
```
curl http://localhost:8040/api/v1/analytics/123/suspected-bots
# Returns: 403 Forbidden (Premium feature)
```

**Solution:**

```bash
# Enable premium for community
curl -X PUT http://localhost:8040/api/v1/analytics/123/config \
  -H "Content-Type: application/json" \
  -d '{"is_premium": true}'

# Verify setting
curl http://localhost:8040/api/v1/analytics/123/config
```

### 500 Internal Server Error

**Symptom:**
```
curl http://localhost:8040/api/v1/analytics/123/metrics
# Returns: 500 Internal Server Error
```

**Diagnosis:**

```bash
# Check application logs
docker-compose logs analytics-core | tail -50

# Look for stack trace
grep -A 20 "Traceback\|Exception" docker-compose.logs
```

**Solution:**

```bash
# Common causes and fixes:
# 1. Database connection error
echo $DATABASE_URL  # Verify set correctly

# 2. Missing table
psql $DATABASE_URL -c "\dt analytics_*"

# 3. Invalid query parameters
# Check query string is URL-encoded
# :
# /api/v1/analytics/123/metrics?start_date=2026-02-01T00:00:00Z
# NOT: /api/v1/analytics/123/metrics?start_date=2026-02-01 00:00:00Z

# 4. Enable debug logging
export LOG_LEVEL=DEBUG
docker-compose restart analytics-core
```

### 400 Bad Request

**Symptom:**
```
curl -X POST http://localhost:8040/api/v1/internal/events \
  -d '{invalid json}'
# Returns: 400 Bad Request
```

**Solution:**

```bash
# Verify JSON is valid
echo '{
  "community_id": 123,
  "events": []
}' | python -m json.tool

# Add Content-Type header
curl -X POST http://localhost:8040/api/v1/internal/events \
  -H "Content-Type: application/json" \
  -d '{"community_id": 123, "events": []}'
```

---

## Memory & Performance

### High Memory Usage

**Symptom:**
```
Docker container: Memory 2GB / 4GB limit
```

**Diagnosis:**

```bash
# Check memory usage
docker stats analytics-core

# Monitor over time
watch -n 5 'docker stats analytics-core'

# Check Python processes
docker exec analytics-core ps aux | grep python
```

**Solution:**

```bash
# Increase container memory limit
# In docker-compose.yml
services:
  analytics-core:
    deploy:
      resources:
        limits:
          memory: 4G
        reservations:
          memory: 2G

# Restart
docker-compose up -d analytics-core

# Or optimize queries (add indexes, pagination)
```

### Slow Aggregation Job

**Symptom:**
```
Aggregation takes 30 minutes for 100k events
```

**Diagnosis:**

```bash
# Time the aggregation manually
time curl -X POST http://localhost:8040/api/v1/internal/aggregate \
  -H "X-Service-API-Key: key" \
  -d '{"community_id": 123, "force": true}'
```

**Solution:**

```bash
# Run aggregation on schedule (off-peak)
# Add to crontab: 0 2 * * * curl -X POST http://localhost:8040/api/v1/internal/aggregate

# Parallelize aggregation across multiple workers
# Use distributed task queue (Celery, RQ)

# Optimize event queries with indexes
psql $DATABASE_URL -c "
CREATE INDEX idx_msg_events_community_time
ON activity_message_events(community_id, created_at);
"
```

---

## Logging & Debugging

### Enable Debug Logging

```bash
# Set LOG_LEVEL environment variable
export LOG_LEVEL=DEBUG

# Restart service
docker-compose restart analytics-core

# View logs
docker-compose logs -f analytics-core
```

### Capture HTTP Requests/Responses

```bash
# Use verbose curl
curl -v http://localhost:8040/api/v1/analytics/123/basic

# Or use tcpdump to capture traffic
sudo tcpdump -i lo -A 'tcp port 8040' | head -100
```

### Database Query Logging

```bash
# Enable PostgreSQL query logging
psql $DATABASE_URL -c "
ALTER SYSTEM SET log_statement = 'all';
ALTER SYSTEM SET log_duration = 'on';
SELECT pg_reload_conf();
"

# View logs
tail -f /var/log/postgresql/postgresql.log

# Disable when done
psql $DATABASE_URL -c "
ALTER SYSTEM SET log_statement = 'none';
SELECT pg_reload_conf();
"
```

### Trace Service Calls

```bash
# Add tracing headers to requests
curl -v \
  -H "X-Trace-ID: debug-123" \
  http://localhost:8040/api/v1/analytics/123/basic

# Check logs for trace ID
docker-compose logs analytics-core | grep "debug-123"
```

---

## Common Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| `ModuleNotFoundError: No module named 'quart'` | Dependencies not installed | `pip install -r requirements.txt` |
| `psycopg2.OperationalError: could not connect` | Database unreachable | Verify DATABASE_URL, check postgres container |
| `psycopg2.ProgrammingError: relation "..." does not exist` | Missing table | Run migrations: `alembic upgrade head` |
| `ValueError: Insecure SECRET_KEY` | Production security | Set strong SECRET_KEY env var |
| `QueuePool limit exceeded` | Connection pool exhausted | Increase pool_size or close idle connections |
| `StaleDataError` | Concurrent modification | Add database locking for aggregation |
| `TimeoutError: timeout waiting for database` | Query too slow | Add indexes, check query plan with EXPLAIN |
| `400 Bad Request` | Invalid JSON or parameters | Validate request body, check Content-Type |
| `401 Unauthorized` | Auth failure | Provide auth token if required |
| `403 Forbidden` | Premium feature | Enable premium for community |
| `404 Not Found` | Community or resource missing | Verify community_id exists |
| `500 Internal Server Error` | Unhandled exception | Check logs, enable DEBUG logging |

---

**Last Updated:** 2026-02-16
**Maintained By:** Penguin Tech Inc
