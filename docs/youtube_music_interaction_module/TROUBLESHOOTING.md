# YouTube Music Interaction Module - Troubleshooting

## Common Issues and Solutions

This guide helps diagnose and fix common problems with the YouTube Music Interaction Module.

## Module Startup Issues

### Issue: Module Fails to Start - Address Already in Use

**Error Message**:
```
Address already in use
OSError: [Errno 48] Address already in use
```

**Cause**: Another process is using port 8025

**Solutions**:

1. Find and stop the process using the port:
```bash
# Find process
lsof -i :8025

# Kill the process
kill -9 <PID>
```

2. Use a different port:
```bash
export MODULE_PORT=8026
hypercorn app:app --bind 0.0.0.0:8026
```

3. Check if another container is running:
```bash
docker ps | grep youtube-music
docker-compose down
```

---

### Issue: Module Startup Hangs

**Symptoms**: Module starts but never becomes ready

**Cause**: Usually database connection timeout or missing dependencies

**Solutions**:

1. Check database connectivity:
```bash
# Test database connection
psql "$DATABASE_URL"

# Check database URL format
echo $DATABASE_URL
# Should be: postgresql://user:password@host:port/database
```

2. Check dependencies are installed:
```bash
pip list | grep -E "quart|hypercorn|httpx|python-dotenv"
```

3. Enable debug logging to see where it hangs:
```bash
export LOG_LEVEL=DEBUG
hypercorn app:app --bind 0.0.0.0:8025
```

4. Check if flask_core library is available:
```bash
python3 -c "from flask_core import init_database; print('OK')"
```

---

## Database Connection Issues

### Issue: Database Connection Refused

**Error Message**:
```
psycopg2.OperationalError: could not connect to server: Connection refused
```

**Cause**: PostgreSQL is not running or credentials are wrong

**Solutions**:

1. Verify PostgreSQL is running:
```bash
# Check if PostgreSQL service is running
docker ps | grep postgres

# Or if using system PostgreSQL
pg_isready -h localhost -p 5432
```

2. Verify connection string:
```bash
# Test connection manually
psql postgresql://waddlebot:password@localhost:5432/waddlebot

# Check for typos
echo $DATABASE_URL
```

3. Check credentials:
```bash
# Correct format
# postgresql://username:password@host:port/database_name

# Common mistakes
# postgresql://username:password@host:5432  <- Missing database name
# postgresql://user:pass@localhost/db       <- Missing port (defaults to 5432)
# postgresql://user:p@ss@word@localhost/db  <- Special chars in password need URL encoding
```

4. If password has special characters, URL-encode them:
```bash
# Use Python to encode
python3 -c "from urllib.parse import quote; print(quote('p@ss:word'))"
# Output: p%40ss%3Aword

# Then use in connection string
DATABASE_URL=postgresql://user:p%40ss%3Aword@localhost:5432/db
```

5. Start PostgreSQL in Docker:
```bash
docker run -d \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=waddlebot \
  -p 5432:5432 \
  postgres:15
```

---

### Issue: Database Permissions Error

**Error Message**:
```
permission denied for schema public
FATAL: role "waddlebot" does not exist
```

**Cause**: Database user or schema doesn't exist

**Solutions**:

1. Create database user:
```bash
psql -U postgres -c "CREATE USER waddlebot WITH PASSWORD 'password';"
psql -U postgres -c "CREATE DATABASE waddlebot OWNER waddlebot;"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE waddlebot TO waddlebot;"
```

2. Check existing users:
```bash
psql -U postgres -c "\du"
```

3. Check database exists:
```bash
psql -U postgres -c "\l" | grep waddlebot
```

---

## OAuth Configuration Issues

### Issue: OAuth Credentials Not Loaded

**Symptoms**: Module starts but OAuth endpoints fail with "missing credentials"

**Cause**: YOUTUBE_CLIENT_ID or YOUTUBE_CLIENT_SECRET not set

**Solutions**:

1. Verify environment variables are set:
```bash
# Check in current shell
echo $YOUTUBE_CLIENT_ID
echo $YOUTUBE_CLIENT_SECRET

# If empty, set them
export YOUTUBE_CLIENT_ID="your-client-id"
export YOUTUBE_CLIENT_SECRET="your-client-secret"
```

2. Check .env file:
```bash
# Verify .env exists and has values
cat .env | grep YOUTUBE_

# Reload environment from .env
source .env
```

3. Check inside container:
```bash
# For Docker
docker-compose exec interactive-youtube-music env | grep YOUTUBE_

# For Kubernetes
kubectl exec -it deployment/youtube-music-interaction -- env | grep YOUTUBE_
```

4. Verify credentials format:
```bash
# Client ID format: xxx.apps.googleusercontent.com
# Client Secret format: GOCSPX-xxx...

# Check if they're valid
[[ $YOUTUBE_CLIENT_ID == *".apps.googleusercontent.com" ]] && echo "Client ID format OK"
[[ $YOUTUBE_CLIENT_SECRET == GOCSPX-* ]] && echo "Client Secret format OK"
```

---

### Issue: OAuth Authorization Code Exchange Fails

**Error Message**:
```
{
  "status": "error",
  "error": "INVALID_CODE",
  "message": "Authorization code is invalid or expired"
}
```

**Causes**:
1. Authorization code is expired (typically 10 minutes)
2. Code was already used
3. Client ID/Secret mismatch
4. Redirect URI mismatch

**Solutions**:

1. Verify redirect URI is registered:
```bash
# Go to Google Cloud Console
# Project Settings > Credentials > OAuth 2.0 Client ID
# Check "Authorized redirect URIs" includes your callback URL

# Common redirect URIs:
# Development: http://localhost:8025/oauth/callback
# Production: https://your-domain.com/oauth/callback
```

2. Get a fresh authorization code (old one expired):
```bash
# Old code expires after 10 minutes, get new one
# Visit: https://accounts.google.com/o/oauth2/v2/auth?...
```

3. Verify client credentials match:
```bash
# The client_id and client_secret must match those in Google Cloud Console
echo "Client ID: $YOUTUBE_CLIENT_ID"
echo "Client Secret: $YOUTUBE_CLIENT_SECRET"

# Go to console and verify they match exactly
```

4. Check logs for more details:
```bash
docker-compose logs interactive-youtube-music | grep -i "oauth\|token"
```

---

### Issue: Token Refresh Fails

**Error Message**:
```
{
  "status": "error",
  "error": "INVALID_REFRESH_TOKEN",
  "message": "Refresh token is invalid or revoked"
}
```

**Cause**: Refresh token expired or was revoked

**Solutions**:

1. Check token expiration:
```bash
# Query database for token expiration
psql "$DATABASE_URL" << SQL
SELECT credential_id, token_expires_at, NOW() 
FROM platform_integrations 
WHERE platform = 'youtube' AND is_active = TRUE;
SQL
```

2. Manually refresh OAuth tokens:
   - Go to Google Account Settings
   - Security > Your apps with access to your Google Account
   - Find WaddleBot
   - Click "Remove access"
   - Re-authorize the app to get new tokens

3. Check if refresh token is stored:
```bash
psql "$DATABASE_URL" << SQL
SELECT credential_id, platform, 
  (access_token IS NOT NULL) as has_access,
  (refresh_token IS NOT NULL) as has_refresh
FROM platform_integrations 
WHERE platform = 'youtube';
SQL
```

---

## Health Check Issues

### Issue: Health Check Endpoint Returns 503

**Error Message**:
```
HTTP/1.1 503 Service Unavailable
{
  "status": "degraded",
  "checks": {
    "database": "disconnected"
  }
}
```

**Cause**: Health check dependency failed

**Solutions**:

1. Check database connection:
```bash
# Test PostgreSQL directly
psql "$DATABASE_URL" -c "SELECT 1"

# Check if service is running
docker ps | grep postgres
```

2. Check Redis connection (if enabled):
```bash
# Test Redis
redis-cli -u "$REDIS_URL" PING

# Check if Redis is running
docker ps | grep redis
```

3. View logs for dependency check errors:
```bash
docker-compose logs interactive-youtube-music | grep -i "health\|check"
```

---

### Issue: Kubernetes Liveness Probe Failing

**Symptoms**: Pod keeps restarting, logs show 503s on /healthz

**Cause**: Health check too strict or dependencies slow to start

**Solutions**:

1. Adjust probe settings in Kubernetes manifest:
```yaml
livenessProbe:
  httpGet:
    path: /healthz
    port: 8025
  initialDelaySeconds: 30      # Wait 30s before first check
  periodSeconds: 10            # Check every 10s
  timeoutSeconds: 5            # Wait 5s for response
  failureThreshold: 3          # Fail after 3 failures

readinessProbe:
  httpGet:
    path: /healthz
    port: 8025
  initialDelaySeconds: 10      # First check after 10s
  periodSeconds: 5             # Check every 5s
  failureThreshold: 2          # Fail after 2 failures
```

2. Check if startup is slow:
```bash
kubectl describe pod <pod-name> -n waddlebot
# Look for "Liveness probe failed" messages

kubectl logs <pod-name> -n waddlebot
# Look for slow startup messages
```

---

## API Endpoint Issues

### Issue: 404 Errors on API Endpoints

**Error Message**:
```
HTTP/1.1 404 Not Found
```

**Cause**: Endpoint not found or wrong path

**Solutions**:

1. Verify endpoint path:
```bash
# Correct paths
/health
/healthz
/metrics
/api/v1/status
/api/v1/oauth/token
/api/v1/oauth/refresh

# Check path in request
curl http://localhost:8025/api/v1/status  # Correct
curl http://localhost:8025/api/status     # Wrong
```

2. Check if module is running:
```bash
curl http://localhost:8025/health
```

3. List available routes:
```bash
# In Python
from app import app
for rule in app.url_map.iter_rules():
    print(rule.rule)
```

---

### Issue: 401 Unauthorized on Protected Endpoints

**Error Message**:
```
{
  "status": "error",
  "error": "UNAUTHORIZED",
  "message": "Missing or invalid authentication"
}
```

**Cause**: Missing or invalid Authorization header

**Solutions**:

1. Include Authorization header:
```bash
# With bearer token
curl -H "Authorization: Bearer <your-token>" \
  http://localhost:8025/api/v1/credentials

# Without token
curl http://localhost:8025/api/v1/credentials  # Fails with 401
```

2. Verify token format:
```bash
# Correct format: Bearer <token>
# Authorization: Bearer ya29.a0AfH6SMBxxx...
```

3. Check token validity:
```bash
# Token should be from OAuth
# Not from basic auth or other methods
```

---

### Issue: 400 Bad Request on Token Exchange

**Error Message**:
```
{
  "status": "error",
  "error": "MISSING_FIELDS",
  "message": "Missing required fields: code"
}
```

**Cause**: Request body missing required fields

**Solutions**:

1. Verify request body format:
```bash
# Correct request
curl -X POST http://localhost:8025/api/v1/oauth/token \
  -H "Content-Type: application/json" \
  -d '{
    "code": "4/0AdY47_bXxxx...",
    "redirect_uri": "http://localhost:8025/oauth/callback"
  }'

# Wrong - missing code
curl -X POST http://localhost:8025/api/v1/oauth/token \
  -H "Content-Type: application/json" \
  -d '{"redirect_uri": "..."}'
```

2. Check Content-Type header:
```bash
# Must be application/json
curl -H "Content-Type: application/json" ...
```

3. Validate JSON syntax:
```bash
# Test JSON is valid
echo '{"code": "test"}' | jq .
```

---

## Rate Limiting Issues

### Issue: 429 Too Many Requests

**Error Message**:
```
HTTP/1.1 429 Too Many Requests
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1645011300
```

**Cause**: Rate limit exceeded

**Solutions**:

1. Wait for rate limit window to reset:
```bash
# X-RateLimit-Reset is Unix timestamp
# Wait until that time

# Convert to readable time
date -d @1645011300
```

2. Reduce request frequency:
```bash
# Default limit: 100 requests/minute
# Space requests out: 1 per 0.6 seconds

for i in {1..10}; do
  curl http://localhost:8025/api/v1/status
  sleep 1
done
```

3. Check rate limit configuration:
```bash
# Adjust in code or via environment variable
# Default: 100 req/min per IP
```

---

## Performance Issues

### Issue: Slow Response Times

**Symptoms**: Requests take >1-2 seconds to respond

**Solutions**:

1. Check database performance:
```bash
# Time a database query
psql "$DATABASE_URL" -c "EXPLAIN ANALYZE SELECT * FROM platform_integrations;"

# Check for missing indexes
psql "$DATABASE_URL" << SQL
SELECT tablename, indexname 
FROM pg_indexes 
WHERE tablename = 'platform_integrations';
SQL
```

2. Check network latency:
```bash
# Measure response time
time curl http://localhost:8025/health

# Check network connectivity
ping $(echo $DATABASE_URL | cut -d'@' -f2 | cut -d':' -f1)
```

3. Check module logs:
```bash
docker-compose logs interactive-youtube-music | tail -50
```

4. Monitor resource usage:
```bash
# CPU and memory
docker stats youtube-music-interaction

# Or in Kubernetes
kubectl top pod <pod-name> -n waddlebot
```

---

### Issue: High Memory Usage

**Symptoms**: Module memory keeps growing

**Cause**: Memory leak or credential cache growing unbounded

**Solutions**:

1. Check memory growth pattern:
```bash
# Monitor over time
watch -n 5 'docker stats youtube-music-interaction'
```

2. Check if credentials are being cached:
```bash
# Look at Config._credentials_loaded flag
# Verify cache is cleared on errors
```

3. Restart module to reset memory:
```bash
docker-compose restart interactive-youtube-music
```

---

## Logging & Debugging

### Enable Debug Logging

```bash
# Set LOG_LEVEL to DEBUG
export LOG_LEVEL=DEBUG

# Restart module
docker-compose restart interactive-youtube-music

# View debug logs
docker-compose logs -f interactive-youtube-music
```

### View Full Logs

```bash
# All logs for module
docker-compose logs interactive-youtube-music

# Last 100 lines
docker-compose logs --tail=100 youtube-music-interaction

# Follow in real-time
docker-compose logs -f interactive-youtube-music

# Filter by keyword
docker-compose logs interactive-youtube-music | grep -i "oauth\|error"
```

### Extract Request/Response

```bash
# Find request details in logs
docker-compose logs interactive-youtube-music | grep "POST /api/v1"

# See full request with curl verbose
curl -v -X POST http://localhost:8025/api/v1/oauth/token \
  -H "Content-Type: application/json" \
  -d '{"code": "test"}'
```

---

## Getting Help

If you still need help:

1. Check the logs thoroughly
2. Review the relevant documentation section:
   - [CONFIGURATION.md](CONFIGURATION.md) - Environment setup
   - [USAGE.md](USAGE.md) - Getting started
   - [API.md](API.md) - Endpoint reference
   - [ARCHITECTURE.md](ARCHITECTURE.md) - How it works

3. Verify all prerequisites are met
4. Try the exact steps from USAGE.md
5. Contact support with:
   - Error message or logs
   - What you were trying to do
   - Your configuration (with secrets redacted)

---

**Last Updated**: 2026-02-16
