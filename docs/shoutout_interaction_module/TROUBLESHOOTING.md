# Shoutout Interaction Module — Troubleshooting Guide

## Module Won't Start

### Error: Connection refused to PostgreSQL

**Problem:**
```
ERROR: Failed to connect to PostgreSQL at postgresql://localhost:5432/waddlebot
```

**Causes:**
- PostgreSQL not running
- Connection string incorrect
- Database doesn't exist
- Wrong credentials

**Fixes:**

1. Verify PostgreSQL is running:
```bash
# Local PostgreSQL
psql -U waddlebot -d waddlebot -c "SELECT 1"

# Docker PostgreSQL
docker ps | grep postgres
docker logs postgres_container
```

2. Check DATABASE_URL format:
```bash
# Correct format
postgresql://user:password@host:port/dbname

# Check if set
echo $DATABASE_URL
```

3. Create database if missing:
```bash
createdb -U postgres waddlebot
psql -U postgres waddlebot < migrations.sql
```

4. Test connection directly:
```bash
psql postgresql://waddlebot:password@localhost:5432/waddlebot
```

### Error: Invalid Twitch credentials

**Problem:**
```
ERROR: OAuth token request failed: 401 Unauthorized
```

**Causes:**
- TWITCH_CLIENT_ID incorrect
- TWITCH_CLIENT_SECRET incorrect
- Application deleted from Twitch Developer Console
- Credentials expired

**Fixes:**

1. Verify credentials are set:
```bash
echo "Client ID: $TWITCH_CLIENT_ID"
echo "Client Secret: $TWITCH_CLIENT_SECRET"
```

2. Regenerate credentials from [Twitch Developer Console](https://dev.twitch.tv/console/apps):
   - Log in as bot account owner
   - Go to Applications → Your app
   - Click "Manage" → "Client Secret"
   - Generate new secret

3. Update .env file:
```bash
TWITCH_CLIENT_ID=new_client_id
TWITCH_CLIENT_SECRET=new_client_secret
```

4. Restart module

### Error: Module port already in use

**Problem:**
```
ERROR: Address already in use: 0.0.0.0:8011
```

**Causes:**
- Another instance running on same port
- Port 8011 already bound by different application

**Fixes:**

1. Find process using port:
```bash
# Linux/Mac
lsof -i :8011

# Windows
netstat -ano | findstr :8011
```

2. Kill the process:
```bash
# Linux/Mac
kill -9 <PID>

# Windows
taskkill /PID <PID> /F
```

3. Or change MODULE_PORT:
```bash
MODULE_PORT=8012
```

## Shoutout Generation Issues

### Error: User not found on Twitch

**Problem:**
```json
{
  "success": false,
  "error": "User 'xyz' not found on Twitch"
}
```

**Causes:**
- Username spelled incorrectly
- Twitch account deleted
- Twitch API not returning user (temporary issue)

**Fixes:**

1. Verify username spelling:
   - Twitch usernames are case-insensitive
   - Check if account still exists at twitch.tv/username

2. Check circuit breaker status:
```bash
curl http://localhost:8011/api/v1/circuit-breaker/metrics \
  -H "Authorization: Bearer YOUR_TOKEN"
```

If circuit breaker is OPEN, Twitch API had too many failures. Wait 60 seconds.

3. Check Twitch API status:
   - Visit [Twitch Status Page](https://status.twitch.tv/)
   - May have temporary outage

4. Test with known user:
```bash
curl -X POST http://localhost:8011/api/v1/shoutout \
  -H "Content-Type: application/json" \
  -d '{
    "username": "twitch",
    "community_id": 123,
    "platform": "twitch"
  }'
```

### Error: Permission denied

**Problem:**
```json
{
  "success": false,
  "error": "Permission denied. Requires: mod or higher"
}
```

**Causes:**
- User doesn't have required role
- Community config requires higher permission than user has

**Fixes:**

1. Verify user roles:
   - Check if user is mod, vip, or subscriber
   - User roles passed in request should match actual roles

2. Check community permission config:
```bash
curl http://localhost:8011/api/v1/video-shoutout/config/123 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Response shows `vso_permission`. Ensure user has that role or higher.

3. Update permission if needed:
```bash
curl -X PUT http://localhost:8011/api/v1/video-shoutout/config/123 \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "vso_permission": "everyone"
  }'
```

### Error: User is on cooldown

**Problem:**
```json
{
  "success": false,
  "error": "User is on cooldown. Please wait 30 more seconds."
}
```

**Causes:**
- User triggered a shoutout recently
- Cooldown period not yet expired

**Fixes:**

1. Check community cooldown setting:
```bash
curl http://localhost:8011/api/v1/video-shoutout/config/123 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Look for `cooldown_minutes` (default: 60).

2. Wait for cooldown to expire or update config:
```bash
curl -X PUT http://localhost:8011/api/v1/video-shoutout/config/123 \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "cooldown_minutes": 30
  }'
```

3. Check cooldown database directly:
```bash
psql waddlebot -c "SELECT * FROM shoutout_cooldowns WHERE community_id = 123;"
```

## Video Shoutout Issues

### Error: No video content found

**Problem:**
```json
{
  "success": false,
  "error": "No video content found"
}
```

**Causes:**
- User has no Twitch clips
- YouTube fallback not configured
- YouTube not linked to Twitch account
- No videos on YouTube channel

**Fixes:**

1. Check if user has Twitch clips:
```bash
curl "http://localhost:8011/api/v1/video-shoutout/video/twitch/pokimane" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Should return video object
```

2. Check identity linking:
```bash
# Query identity service
curl "http://localhost:8050/api/v1/identities/lookup?platform=twitch&platform_user_id=88888888"

# Should show linked YouTube account
```

3. Verify YouTube API key is configured:
```bash
echo $YOUTUBE_API_KEY

# If empty, set it:
export YOUTUBE_API_KEY=your_youtube_key
```

4. Test YouTube video search manually:
```bash
curl "https://www.googleapis.com/youtube/v3/search?part=snippet&q=username&type=channel&key=$YOUTUBE_API_KEY"
```

5. As fallback, trigger video shoutout with manual clip URL:
   - Users can clip their own videos on Twitch
   - Clips appear within 1-5 minutes

### Error: Cross-platform identity resolution failed

**Problem:**
```json
{
  "success": false,
  "error": "Unable to resolve identity for cross-platform lookup"
}
```

**Causes:**
- Identity service unreachable
- User has no linked identities
- Identity database empty

**Fixes:**

1. Check identity service availability:
```bash
curl http://localhost:8050/health
# Should return 200 OK
```

2. Verify IDENTITY_URL is correct:
```bash
echo $IDENTITY_URL
# Default: http://identity-core:8050
```

3. Check network connectivity:
```bash
docker logs identity-core  # if using Docker
ping -c 1 identity-core
```

4. Manually query linked identities:
```bash
curl "http://localhost:8050/api/v1/identities/lookup?platform=twitch&platform_user_id=88888888"

# If empty response, link identities in identity_core first
```

5. Fallback: Ensure user has Twitch clips (doesn't require YouTube link)

## API Response Issues

### Error: 401 Unauthorized

**Problem:**
```json
{
  "success": false,
  "error": "Authorization required"
}
```

**Causes:**
- No Bearer token provided
- Invalid or expired token
- Endpoint requires authentication

**Fixes:**

1. Verify token is included in request:
```bash
curl http://localhost:8011/api/v1/history/123 \
  -H "Authorization: Bearer YOUR_TOKEN"

# Without token will get 401
```

2. Get new token from authentication service:
   - Contact identity service or auth module
   - Usually from login endpoint

3. Check token validity:
```bash
# Decode JWT token
python -c "import jwt; print(jwt.decode('YOUR_TOKEN', options={'verify_signature': False}))"

# Check expiration claim ("exp")
```

### Error: 400 Bad Request

**Problem:**
```json
{
  "success": false,
  "error": "community_id and target_username required"
}
```

**Causes:**
- Missing required field
- Invalid field value
- Malformed JSON

**Fixes:**

1. Check request body has all required fields:
```bash
# Required fields vary by endpoint
# For video-shoutout: community_id, target_username
# For shoutout: username, community_id

curl -X POST http://localhost:8011/api/v1/video-shoutout \
  -H "Content-Type: application/json" \
  -d '{
    "community_id": 123,
    "target_username": "pokimane",
    "target_platform": "twitch",
    "user_roles": ["mod"]
  }'
```

2. Validate JSON syntax:
```bash
# Use jq to validate JSON
echo '{"community_id": 123}' | jq .
```

3. Check field types:
   - `community_id` should be integer, not string
   - `username` should be string
   - `user_roles` should be array

### Error: 500 Internal Server Error

**Problem:**
```json
{
  "success": false,
  "error": "Internal server error"
}
```

**Causes:**
- Unhandled exception in module
- Database connection lost
- Third-party API timeout
- Memory/resource exhaustion

**Fixes:**

1. Check module logs:
```bash
# Local
tail -f /tmp/shoutout-module.log

# Docker
docker logs shoutout-module

# Kubernetes
kubectl logs pod/shoutout-module-xyz
```

2. Check detailed error in logs:
```bash
# Find traceback in logs
grep -A 10 "Traceback" logs.txt
```

3. Verify all services are healthy:
```bash
# Database
psql waddlebot -c "SELECT 1"

# Identity service
curl http://identity-core:8050/health

# Twitch API
curl -I https://api.twitch.tv/helix/users
```

4. Restart module:
```bash
docker restart shoutout-module
# or
systemctl restart shoutout-module
```

5. Increase log level to DEBUG for more details:
```bash
LOG_LEVEL=DEBUG
```

## Database Issues

### Error: Database table doesn't exist

**Problem:**
```
ERROR: relation "shoutout_history" does not exist
```

**Causes:**
- Migrations not run
- Wrong database selected
- Database created but not initialized

**Fixes:**

1. Run migrations:
```bash
# Find migration files
ls config/postgres/migrations/

# Run them
psql waddlebot < config/postgres/migrations/*.sql
```

2. Verify database contains tables:
```bash
psql waddlebot -c "\dt"

# Should list: shoutout_history, video_shoutout_history, shoutout_templates, etc.
```

3. Check if using correct database:
```bash
psql waddlebot -c "SELECT current_database();"
```

### Error: Lock wait timeout

**Problem:**
```
ERROR: lock timeout. deadlock detected
```

**Causes:**
- Database query took too long
- Too many concurrent connections
- Slow query blocking others

**Fixes:**

1. Check long-running queries:
```bash
psql waddlebot -c "SELECT pid, query, state FROM pg_stat_activity WHERE state != 'idle';"
```

2. Kill blocking query:
```bash
psql waddlebot -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE query ILIKE '%SELECT%' AND pid != pg_backend_pid();"
```

3. Increase connection pool size:
   - Currently asyncpg uses default pool
   - Can adjust in code if needed

## Circuit Breaker Tripped

### Error: Circuit breaker open

**Problem:**
```json
{
  "success": false,
  "error": "Circuit breaker is OPEN. Service temporarily unavailable."
}
```

**Status:**
```bash
curl http://localhost:8011/api/v1/circuit-breaker/metrics \
  -H "Authorization: Bearer YOUR_TOKEN"

# Shows: "state": "open"
```

**Causes:**
- 5+ failed requests to Twitch API
- Service in recovery cooldown (60 seconds)

**Fixes:**

1. Wait for recovery timeout (60 seconds):
   - Circuit breaker automatically transitions to HALF_OPEN
   - Next request tries to recover

2. Check if Twitch API is up:
   - Visit [Twitch Status Page](https://status.twitch.tv/)
   - May have outage

3. Verify credentials are correct:
   - Invalid credentials cause repeated failures
   - Update TWITCH_CLIENT_ID/SECRET if needed

4. Monitor recovery:
```bash
# Poll circuit breaker status
watch -n 5 'curl -s http://localhost:8011/api/v1/circuit-breaker/metrics | jq ".data.circuit_breaker.state"'

# Wait for "closed"
```

## Rate Limiting Issues

### Error: Twitch API rate limit exceeded

**Problem:**
```
ERROR: Twitch API rate limit exceeded. Retry after X seconds.
```

**Causes:**
- Too many requests to Twitch API
- Multiple module instances competing for same credentials
- Hammering endpoint without backoff

**Fixes:**

1. Check request volume:
```bash
# Twitch allows ~120 requests/minute per credential
# Calculate: total_communities × request_frequency
```

2. Reduce request frequency:
   - Cache results longer
   - Batch requests where possible
   - Use clips instead of searching every time

3. Use separate credentials per environment:
   - Development: one set of credentials
   - Production: different set
   - Staging: different set

4. Implement backoff in calling service:
   - Exponential backoff on rate limit response
   - Don't retry immediately on 429 status

## Performance Issues

### Shoutout generation slow

**Problem:**
- Requests taking >5 seconds
- Timeouts in chat bot

**Causes:**
- Slow database queries
- Slow Twitch API response
- Network latency

**Fixes:**

1. Profile request time:
```bash
curl -w "Total time: %{time_total}s\n" \
  -X POST http://localhost:8011/api/v1/shoutout \
  -d '{"username":"ninja","community_id":123}'
```

2. Check Twitch API latency:
```bash
curl -w "Twitch API time: %{time_connect}s\n" \
  https://api.twitch.tv/helix/users?login=ninja
```

3. Optimize template lookup:
   - Template queries are now cached
   - If still slow, add database index:
```sql
CREATE INDEX idx_templates_community ON shoutout_templates(community_id);
```

4. Monitor database slow query log:
```bash
# PostgreSQL
psql waddlebot -c "ALTER SYSTEM SET log_min_duration_statement = 1000;"
psql waddlebot -c "SELECT pg_reload_conf();"
```

## Memory Issues

### Error: Out of memory

**Problem:**
```
MemoryError: Unable to allocate X bytes
```

**Causes:**
- Too many concurrent connections
- Large response caching
- Database connection pool too large

**Fixes:**

1. Monitor memory usage:
```bash
# Docker
docker stats shoutout-module

# Linux
top -p $(pidof python)
```

2. Reduce pool size:
   - Database connection pool default is 10
   - Adjust in startup code if needed

3. Add memory limit in Docker:
```yaml
resources:
  limits:
    memory: 512M
  requests:
    memory: 256M
```

4. Clear old history periodically:
```sql
DELETE FROM shoutout_history WHERE created_at < NOW() - INTERVAL '90 days';
DELETE FROM video_shoutout_history WHERE created_at < NOW() - INTERVAL '90 days';
```

## Still Having Issues?

1. **Collect diagnostic information:**
```bash
# Check module health
curl http://localhost:8011/health

# Get module logs
docker logs shoutout-module > logs.txt 2>&1

# Check database connectivity
psql waddlebot -c "SELECT version();"

# Check Twitch API key validity
curl -H "Authorization: Bearer $(python get_twitch_token.py)" \
  https://api.twitch.tv/helix/users?login=twitch
```

2. **Review logs for specific error messages:**
```bash
grep -i "error\|exception\|failed" logs.txt | head -20
```

3. **Contact support:**
   - Email: support@penguintech.io
   - Provide logs and environment info
   - Describe steps to reproduce issue
