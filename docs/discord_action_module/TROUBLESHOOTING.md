# Discord Action Module - Troubleshooting Guide

## Common Issues and Solutions

### Module Startup Issues

#### 1. Module Won't Start - Database Connection Error

**Error Message:**
```
ERROR Configuration errors: DATABASE_URL is required
ERROR Failed to connect to database: connection refused
```

**Causes:**
- PostgreSQL is not running
- DATABASE_URL is invalid
- Network connectivity issue
- Wrong credentials

**Solutions:**

Check PostgreSQL is running:
```bash
docker-compose ps
# Should show 'postgres' container as 'Up'
```

If not running, start it:
```bash
docker-compose up -d postgres
```

Verify DATABASE_URL format:
```bash
# Should be: postgresql://user:pass@host:port/database
export DATABASE_URL="postgresql://waddlebot:password@postgres:5432/waddlebot"
```

Test connection:
```bash
psql $DATABASE_URL -c "SELECT 1"
```

If "connection refused", check:
- PostgreSQL listening on correct port: `netstat -tuln | grep 5432`
- Firewall rules allow connection
- HOST and PORT in DATABASE_URL are correct

#### 2. JWT Token Generation Fails

**Error Message:**
```
ValueError: MODULE_SECRET_KEY must be set to a secure value
```

**Cause:**
- MODULE_SECRET_KEY not set or too short

**Solution:**

Generate secure key:
```bash
export MODULE_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
```

Add to .env:
```bash
MODULE_SECRET_KEY=your_generated_key_here
```

Restart module:
```bash
docker-compose restart action-discord
```

#### 3. Module Crashes on Startup

**Check logs:**
```bash
docker-compose logs action-discord
```

**Common causes:**
- Port already in use
- Database schema not migrated
- Missing required environment variables

**Solutions:**

Check ports are available:
```bash
netstat -tuln | grep -E ':(8070|50051)'
```

If ports in use, change in environment:
```bash
export GRPC_PORT=50052
export REST_PORT=8071
```

---

### API Request Issues

#### 1. Health Check Fails - Service Unhealthy

**Error Response:**
```json
{
  "status": "unhealthy",
  "error": "Database connection error"
}
```

**Check:**
1. Database running: `docker-compose ps infra-postgres`
2. Database accessible: `psql $DATABASE_URL -c "SELECT 1"`
3. Logs: `docker-compose logs action-discord`

**Solution:**
```bash
# Restart database connection
docker-compose restart action-discord
```

#### 2. Authentication Failures

**Error Response:**
```json
{
  "error": "Missing or invalid authorization header"
}
```

**Cause:**
- Missing Authorization header
- Invalid JWT token
- Token expired

**Solution - Get new token:**
```bash
curl -X POST http://localhost:8070/api/v1/token   -H "Content-Type: application/json"   -d '{
    "client_id": "app1",
    "client_secret": "secret123"
  }' | jq -r '.token'
```

Use token in subsequent requests:
```bash
curl http://localhost:8070/api/v1/health   -H "Authorization: Bearer YOUR_TOKEN"
```

#### 3. Missing Authorization Header

**Error Response:**
```json
{
  "error": "Missing or invalid authorization header"
}
```

**Cause:**
- No Authorization header in request
- Wrong header format

**Solution:**

Correct format:
```bash
curl http://localhost:8070/api/v1/message   -H "Authorization: Bearer YOUR_JWT_TOKEN"   -H "Content-Type: application/json"   -d '{"channel_id":"123","content":"test"}'
```

Invalid formats:
```bash
# WRONG - no Bearer
-H "Authorization: YOUR_TOKEN"

# WRONG - wrong case
-H "authorization: Bearer YOUR_TOKEN"

# WRONG - extra header
-H "Bearer YOUR_TOKEN"
```

---

### Discord API Issues

#### 1. Discord API Returns 401 Unauthorized

**Error Message:**
```json
{
  "success": false,
  "error": "401 Unauthorized"
}
```

**Causes:**
- Invalid or expired Discord bot token
- Bot token not in environment

**Solutions:**

Verify token in Discord Developer Portal:
1. Go to https://discord.com/developers/applications
2. Select your app
3. Go to "Bot" section
4. Check token (click "Reset Token" if needed)

Set token:
```bash
export DISCORD_BOT_TOKEN="your_new_token"
```

Reload module:
```bash
docker-compose restart action-discord
```

Verify token is loaded:
```bash
curl http://localhost:8070/health | jq '.config.discord_token_configured'
# Should return: true
```

#### 2. Discord API Returns 403 Forbidden

**Error Message:**
```json
{
  "success": false,
  "error": "403 Forbidden - Missing permissions"
}
```

**Causes:**
- Bot lacks required permissions in Discord server
- Channel permissions prevent bot access

**Solutions:**

Check bot permissions in Discord:
1. Open Discord server
2. Go to Settings > Integrations > Bots
3. Click on your bot
4. Check permissions (should have):
   - Send Messages
   - Manage Roles (if managing roles)
   - Manage Messages (if deleting/editing)
   - Add Reactions
   - Manage Webhooks (if using webhooks)
   - Ban Members (if banning)
   - Kick Members (if kicking)

Re-invite bot with correct permissions:
1. Go to Discord Developer Portal
2. Select your app
3. Go to OAuth2 > URL Generator
4. Select scopes: "bot"
5. Select permissions: 551911541
6. Copy URL and open in browser
7. Select server and authorize

#### 3. Discord API Returns 404 Not Found

**Error Message:**
```json
{
  "success": false,
  "error": "404 Not Found"
}
```

**Causes:**
- Channel ID doesn't exist
- User not in server
- Message already deleted
- Role doesn't exist

**Solutions:**

Verify channel ID:
```bash
# In Discord, enable Developer Mode
# Right-click channel > Copy ID
curl http://localhost:8070/api/v1/message   -H "Authorization: Bearer TOKEN"   -H "Content-Type: application/json"   -d '{
    "channel_id": "CORRECT_CHANNEL_ID",
    "content": "test"
  }'
```

Verify user is in server:
```bash
# Check user appears in members list
# Use correct user_id when managing roles
```

Verify role exists:
```bash
# In Discord, check role exists in server settings
# Use correct role_id
```

#### 4. Discord API Rate Limiting (429 Too Many Requests)

**Error Message:**
```json
{
  "success": false,
  "error": "429 Too Many Requests"
}
```

**Cause:**
- Exceeded Discord API rate limits
- Global limit: 50 requests/second
- Per-channel limit: 5 requests/second

**Solutions:**

Check rate limit configuration:
```bash
# In .env or environment
DISCORD_RATE_LIMIT_GLOBAL=50
DISCORD_RATE_LIMIT_PER_CHANNEL=5
```

If hitting limits, increase (be cautious of Discord's global limits):
```bash
export DISCORD_RATE_LIMIT_GLOBAL=100
export DISCORD_RATE_LIMIT_PER_CHANNEL=10
docker-compose restart action-discord
```

Better solution - Implement request queueing:
- Batch operations when possible
- Stagger requests over time
- Increase MAX_RETRIES for automatic backoff

#### 5. Discord API Returns 400 Bad Request

**Error Message:**
```json
{
  "success": false,
  "error": "400 Bad Request - Invalid embed"
}
```

**Causes:**
- Invalid JSON in embed
- Content exceeds 2000 characters
- Embed exceeds 6000 characters total

**Solutions:**

Check message content length:
```python
content = "Your message here"
assert len(content) <= 2000, "Message too long"
```

Check embed validity:
```python
embed = {
    "title": "Title (max 256 chars)",
    "description": "Description (max 4096 chars)",
    "fields": [
        {
            "name": "Name (max 256 chars)",
            "value": "Value (max 1024 chars)",
            "inline": False
        }
    ]
    # Total embed size: max 6000 chars
}
```

---

### Performance and Rate Limiting

#### 1. Requests Are Very Slow

**Symptom:**
- Message send takes >5 seconds
- API responses timeout

**Causes:**
- Discord API is slow
- Network latency
- Database slow queries
- Rate limiting causing delays

**Solutions:**

Check Discord API status:
```bash
# https://status.discord.com
curl https://status.discordapp.com/api/v2/status.json | jq '.status.indicator'
```

Check network latency:
```bash
ping discord.com
ping postgres  # if using docker
```

Check logs for slowness:
```bash
docker-compose logs action-discord | grep "slow\|timeout"
```

Increase timeout if needed (default: 30s):
```bash
export REQUEST_TIMEOUT=60
docker-compose restart action-discord
```

#### 2. Rate Limit Errors Occurring Frequently

**Symptom:**
- 429 errors regularly
- Module logs show "Rate limited"

**Causes:**
- High request volume
- Rate limits too low
- Burst traffic

**Solutions:**

Monitor rate limits:
```bash
# Check configuration
docker-compose exec action-discord   curl http://localhost:8070/health | jq '.config'
```

Adjust limits (carefully):
```bash
export DISCORD_RATE_LIMIT_GLOBAL=100
export DISCORD_RATE_LIMIT_PER_CHANNEL=10
```

Implement exponential backoff in client code:
```python
import time
import random

def retry_with_backoff(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return func()
        except RateLimitError:
            wait_time = (2 ** attempt) + random.random()
            time.sleep(wait_time)
```

---

### Logging and Debugging

#### 1. Check Module Logs

View real-time logs:
```bash
docker-compose logs -f action-discord
```

View with timestamps:
```bash
docker-compose logs -f --timestamps discord_action_module
```

Filter by log level:
```bash
docker-compose logs action-discord | grep ERROR
docker-compose logs action-discord | grep WARNING
```

#### 2. Enable Debug Logging

Set log level to DEBUG:
```bash
export LOG_LEVEL=DEBUG
docker-compose restart action-discord
```

Check logs for detailed output:
```bash
docker-compose logs action-discord | head -50
```

#### 3. Database Query Logging

Check database logs:
```bash
docker-compose logs infra-postgres | grep ERROR
```

Check database connections:
```bash
docker-compose exec infra-postgres psql -U waddlebot -d waddlebot -c "SELECT count(*) FROM pg_stat_activity;"
```

#### 4. Check Activity Log

Query discord_actions table:
```bash
docker-compose exec infra-postgres psql -U waddlebot -d waddlebot << 'SQL'
SELECT action_type, success, error_message, created_at 
FROM discord_actions 
ORDER BY created_at DESC 
LIMIT 10;
SQL
```

---

### Docker Issues

#### 1. Container Won't Start

**Check container status:**
```bash
docker-compose ps
```

**View startup logs:**
```bash
docker-compose logs action-discord
```

**Rebuild container:**
```bash
docker-compose build --no-cache discord_action_module
docker-compose up -d discord_action_module
```

#### 2. Port Already in Use

**Error:**
```
Error response from daemon: driver failed programming external connectivity on endpoint discord_action_module: Bind for 0.0.0.0:8070 failed
```

**Solution:**

Find what's using the port:
```bash
lsof -i :8070
```

Either kill that process or use different port:
```bash
# In .env or docker-compose.yml
REST_PORT=8071
GRPC_PORT=50052
```

#### 3. Disk Space Issues

**Error:**
```
no space left on device
```

**Solution:**

Check disk space:
```bash
df -h
```

Clean up Docker:
```bash
docker system prune -a
```

---

### Getting Help

If you can't resolve the issue:

1. **Gather information:**
   ```bash
   docker-compose logs action-discord > logs.txt
   curl http://localhost:8070/health | jq . > health.json
   env | grep -E "DISCORD|DATABASE|JWT" > env.txt
   ```

2. **Check documentation:**
   - CONFIGURATION.md - All environment variables
   - API.md - Endpoint reference
   - ARCHITECTURE.md - System design

3. **Contact support:**
   - Create issue with logs attached
   - Include version: `docker-compose exec action-discord cat requirements.txt`
   - Include configuration summary (no secrets)

---

## Quick Reference - Common Fixes

| Problem | Quick Fix |
|---------|-----------|
| Module won't start | Check DATABASE_URL and DISCORD_BOT_TOKEN |
| Health check fails | Verify database is running |
| API returns 401 | Generate new JWT token via /api/v1/token |
| Discord API returns 401 | Check DISCORD_BOT_TOKEN is valid |
| Discord API returns 403 | Check bot permissions in Discord server |
| Discord API returns 429 | Wait or increase rate limits |
| Slow requests | Check Discord API status or increase timeout |
| Port already in use | Change REST_PORT or GRPC_PORT |
| Container won't start | Rebuild: docker-compose build --no-cache |
| Disk full | Run docker system prune -a |
