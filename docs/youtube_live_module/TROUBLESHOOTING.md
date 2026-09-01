# YouTube Live Module Troubleshooting Guide

Solutions for common issues and error scenarios.

## General Troubleshooting Process

1. **Check health status**: `curl http://localhost:8006/health`
2. **Review logs**: `docker-compose logs -f youtube-live` or stdout
3. **Check configuration**: Verify all environment variables are set
4. **Test connectivity**: `curl -I https://www.googleapis.com/youtube/v3/`
5. **Verify database**: `psql $DATABASE_URL -c "SELECT * FROM youtube_channels;"`

## Common Issues & Solutions

### 1. Module Won't Start

#### Error: "Failed to connect to database"

**Symptoms:**
```
ERROR: Could not connect to database at postgresql://localhost:5432/waddlebot
Connection refused
```

**Root Causes:**
- PostgreSQL server not running
- Incorrect DATABASE_URL
- Database doesn't exist
- Insufficient permissions

**Solutions:**

```bash
# Check PostgreSQL is running
sudo systemctl status postgresql
# or (Docker)
docker-compose ps | grep postgres

# Verify connection string
echo $DATABASE_URL
# Should look like: postgresql://user:password@host:5432/dbname

# Create database if missing
psql -U postgres -c "CREATE DATABASE waddlebot;"

# Test connection
psql $DATABASE_URL -c "SELECT 1;"
```

If still failing:

```bash
# Check PostgreSQL logs
docker-compose logs postgres

# Verify host resolution
ping $(echo $DATABASE_URL | sed -E 's/.*@([^:\/]+).*/\1/')
```

---

#### Error: "Module port already in use"

**Symptoms:**
```
ERROR: Address already in use: ('0.0.0.0', 8006)
```

**Solution:**

```bash
# Find process using port
lsof -i :8006
# or
netstat -tulpn | grep 8006

# Kill process
kill -9 <PID>

# Or use different port
MODULE_PORT=8007 python main.py
```

---

#### Error: "YOUTUBE_API_KEY not configured"

**Symptoms:**
```
ERROR: Missing required environment variable: YOUTUBE_API_KEY
```

**Solution:**

```bash
# Get API key from Google Cloud Console
export YOUTUBE_API_KEY="AIzaSyD..."

# Or add to .env file
echo "YOUTUBE_API_KEY=AIzaSyD..." >> .env

# Verify
echo $YOUTUBE_API_KEY
```

See [CONFIGURATION.md](CONFIGURATION.md) for complete setup instructions.

---

### 2. Chat Polling Not Working

#### No messages captured

**Symptoms:**
- `/api/v1/channels` shows 0 active streams
- No messages in logs
- ChatPoller appears to be running

**Debugging Steps:**

```bash
# Check if channels are registered
curl http://localhost:8006/api/v1/channels | jq .

# Check if broadcast is live
curl http://localhost:8006/api/v1/broadcasts/UCxxxxxxxxxx | jq .

# Check logs for polling errors
docker-compose logs youtube-live | grep -i "error\|exception\|failed"

# Verify API key works
curl "https://www.googleapis.com/youtube/v3/channels?part=statistics&forUsername=youtube&key=$YOUTUBE_API_KEY"
```

**Root Causes & Solutions:**

| Issue | Cause | Solution |
|-------|-------|----------|
| No active streams | YouTube channel not currently live | Wait for stream to start or test with known live channel |
| API key invalid | Wrong API key or key disabled | Get new key from Google Cloud Console |
| Quota exceeded | Too many polling requests | Increase CHAT_POLL_INTERVAL or reduce CHAT_MAX_RESULTS |
| Channel not registered | Channel never registered | Register via `/api/v1/channels/register` |

---

#### Error: "403 Forbidden" during polling

**Symptoms:**
```
ERROR: YouTube API returned 403: forbidden
```

**Root Causes:**
- Stream is no longer live (expected)
- API key disabled
- YouTube account restrictions
- Channel privacy settings

**Solution:**

```bash
# If expected (stream ended): no action needed
# Module will continue polling for next stream

# If unexpected:
# 1. Check API key is active
# 2. Check YouTube account has no restrictions
# 3. Check channel is public
# 4. Check API quota: https://console.cloud.google.com/apis/dashboard

# Manual recovery: unregister and re-register
curl -X DELETE http://localhost:8006/api/v1/channels/UCxxxxxxxxxx
curl -X POST http://localhost:8006/api/v1/channels/register \
  -H "Content-Type: application/json" \
  -d '{"channel_id": "UCxxxxxxxxxx", "channel_name": "Channel"}'
```

---

#### Error: "429 Too Many Requests"

**Symptoms:**
```
ERROR: YouTube API returned 429: quota_exceeded
```

**Cause**: API quota limit exceeded (10,000 units per day)

**Solution:**

```bash
# Option 1: Increase polling interval (saves 50% quota)
export CHAT_POLL_INTERVAL=10

# Option 2: Reduce messages per poll (saves bandwidth)
export CHAT_MAX_RESULTS=50

# Option 3: Monitor fewer channels
# Unregister low-priority channels

# Option 4: Request quota increase
# Go to https://console.cloud.google.com/apis/dashboard
# Select YouTube Data API v3
# Quotas → Request quota increase

# Calculate current usage
channels=$( curl -s http://localhost:8006/api/v1/channels | jq '.total_channels' )
interval=${CHAT_POLL_INTERVAL:-5}
daily_quota=$(( 86400 / interval * channels ))
echo "Estimated daily quota: $daily_quota units"
```

---

#### Error: "401 Unauthorized"

**Symptoms:**
```
ERROR: YouTube API returned 401: invalid_credentials
```

**Root Causes:**
- API key revoked
- OAuth token expired
- Invalid credentials in database

**Solution:**

```bash
# Option 1: Get new API key
# Go to Google Cloud Console → Credentials
# Create new API key

# Option 2: Clear corrupted credentials
psql $DATABASE_URL -c "DELETE FROM youtube_credentials;"

# Option 3: Refresh OAuth tokens
# Manually via Python:
python -c "
import asyncio
from services.youtube_client import YouTubeClient
client = YouTubeClient()
asyncio.run(client.refresh_channel_token('UCxxxxxxxxxx'))
"

# Then restart module
```

---

### 3. Messages Not Reaching Router

#### Messages captured but not routed

**Symptoms:**
- `/api/v1/status` shows messages_processed > 0
- Router API not receiving messages
- No errors in YouTube Live module logs

**Debugging:**

```bash
# Check router connectivity
curl http://router:8000/health

# Check router API endpoint
curl -X POST http://router:8000/api/v1/message \
  -H "Content-Type: application/json" \
  -d '{"test": true}'

# Check YouTube Live logs for routing errors
docker-compose logs youtube-live | grep "router\|failed"

# Monitor outgoing requests
docker-compose logs youtube-live | grep "POST.*router"
```

**Solutions:**

| Issue | Solution |
|-------|----------|
| Router not running | Start router: `docker-compose up -d router` |
| Wrong ROUTER_API_URL | Check: `echo $ROUTER_API_URL` |
| Network blocked | Check firewall, service discovery, DNS |
| Router rejecting messages | Check message format matches router schema |
| Slow router | Increase ROUTER_API_TIMEOUT |

---

### 4. Database Issues

#### "Database connection pool exhausted"

**Symptoms:**
```
ERROR: QueuePool limit exceeded, timeout waiting for connection
```

**Cause**: Too many concurrent database operations, connection pool too small

**Solution:**

```bash
# Increase connection pool size
export DB_POOL_SIZE=30
export DB_MAX_OVERFLOW=10

# Restart module
docker-compose restart youtube-live

# Check current connections
psql $DATABASE_URL -c "SELECT count(*) FROM pg_stat_activity;"

# Close idle connections if needed
psql $DATABASE_URL -c "
SELECT pid, usename, state FROM pg_stat_activity
WHERE state = 'idle' AND duration > '10 minutes';
"
```

---

#### "Disk space full" or "no space left on device"

**Symptoms:**
```
ERROR: PostgreSQL error: disk full
```

**Solution:**

```bash
# Check disk usage
df -h

# Check PostgreSQL data directory
du -sh /var/lib/postgresql/

# Clean old messages (if stored)
psql $DATABASE_URL -c "
DELETE FROM youtube_messages
WHERE created_at < NOW() - INTERVAL '30 days';
"

# Or disable message logging
# In config.py: STORE_MESSAGES = False
```

---

### 5. Performance Issues

#### High memory usage

**Symptoms:**
- Memory usage grows over time
- Eventually crashes with OOM
- `docker stats` shows high MEM%

**Causes & Solutions:**

| Cause | Solution |
|-------|----------|
| Message buffer leak | Increase CHAT_POLL_INTERVAL to give poller breathing room |
| Cache not expiring | Check REDIS_CACHE_TTL, ensure Redis is running |
| Connection pool growth | Set DB_POOL_SIZE appropriately, restart module |
| Large message batch | Reduce CHAT_MAX_RESULTS to 50-100 |
| Python memory bloat | Restart module periodically via cron job |

```bash
# Monitor memory in real-time
docker stats youtube-live --no-stream | watch

# Set memory limit in Docker
# Add to docker-compose.yml:
# mem_limit: 512m
# memswap_limit: 512m

# Restart module weekly to clear memory
0 2 * * 0 docker-compose restart youtube-live
```

---

#### High CPU usage

**Symptoms:**
- CPU at 100% consistently
- Slow API response times
- Module unresponsive

**Causes & Solutions:**

| Cause | Solution |
|-------|----------|
| Polling interval too aggressive | Increase CHAT_POLL_INTERVAL from 5 to 10 seconds |
| Too many channels | Reduce registered channels or shard across instances |
| Inefficient parsing | Profile with `python -m cProfile app.py` |
| Router API slow | Increase ROUTER_API_TIMEOUT, check router performance |
| Busy-wait loop | Check for infinite loops in code (should use await) |

```bash
# Profile CPU usage
docker exec youtube-live python -m cProfile -s cumtime main.py 2>&1 | head -20

# Check processes
top -p $(docker exec youtube-live pgrep -f python)
```

---

#### Slow API responses

**Symptoms:**
- HTTP requests taking >5 seconds
- `/api/v1/channels` slow
- Timeouts on client side

**Causes:**

```bash
# Check module logs for slow operations
docker-compose logs youtube-live | grep "slow\|latency"

# Check database query performance
psql $DATABASE_URL << EOF
\timing
SELECT * FROM youtube_channels;
SELECT * FROM youtube_broadcasts WHERE channel_id = 'UCxxxxxxxxxx';
EOF

# Check router API latency
time curl http://router:8000/api/v1/message -X POST -d '{}'
```

**Solutions:**

- Add database indices: `CREATE INDEX idx_channel_id ON youtube_broadcasts(channel_id);`
- Reduce CHAT_MAX_RESULTS to lower processing load
- Increase server capacity (CPU, RAM, connections)
- Implement response caching for `/api/v1/channels`

---

### 6. Webhook Issues

#### Webhook never receives notifications

**Symptoms:**
- Subscribed to channel (no errors)
- Never receives POST requests
- `/api/v1/webhook` logs show no requests

**Debugging:**

```bash
# Verify subscription
curl http://localhost:8006/api/v1/channels | jq '.[] | select(.webhook_subscribed == true)'

# Check webhook URL is reachable
curl -I $YOUTUBE_WEBHOOK_CALLBACK_URL

# Enable webhook request logging
LOG_LEVEL=DEBUG python main.py

# Check module can reach YouTube PubSub
curl https://pubsubhubbub.appspot.com/
```

**Solutions:**

| Issue | Solution |
|-------|----------|
| Callback URL not HTTPS | Change to HTTPS or use expose tunneling |
| URL not publicly accessible | Test with `curl -I <url>` from external host |
| Firewall blocking | Check ingress rules, open port 443 |
| Wrong port in URL | Verify port matches actual module port |
| Subscription not confirmed | Check module logs for verification challenge |

---

#### Webhook signature verification fails

**Symptoms:**
```
ERROR: Webhook signature verification failed
```

**Solution:**

```bash
# Ensure SECRET_KEY matches webhook secret
echo $SECRET_KEY
echo $WEBHOOK_SECRET

# If mismatch, set both to same value
export SECRET_KEY="my-secret-key"
export WEBHOOK_SECRET="my-secret-key"

# Disable verification (not recommended)
# WEBHOOK_VERIFY_SIGNATURE=false python main.py

# Restart module
docker-compose restart youtube-live
```

---

### 7. Docker-Specific Issues

#### Container exits immediately

**Symptoms:**
```
youtube-live exited with code 1
```

**Solution:**

```bash
# Check logs
docker-compose logs youtube-live

# Run with interactive terminal
docker-compose run --rm youtube-live python main.py

# Check Dockerfile
docker build -t youtube-live:test . --verbose
```

---

#### Permission denied errors

**Symptoms:**
```
ERROR: Permission denied: '/home/user/.env'
```

**Solution:**

```bash
# Fix file permissions
chmod 644 .env
chmod 755 trigger/receiver/youtube_live_module

# Run as correct user
docker-compose exec -u root youtube-live chown -R nobody:nobody /app
```

---

### 8. Debugging Tools

#### Enable verbose logging

```bash
# Maximum verbosity
LOG_LEVEL=DEBUG python main.py 2>&1 | tee debug.log

# Filter specific module
docker-compose logs youtube-live | grep "ChatPoller"
```

---

#### Monitor API quota usage

```bash
# Check quota via Google API
curl "https://www.googleapis.com/youtube/v3/i18nLanguages?part=snippet&key=$YOUTUBE_API_KEY"

# Monitor quota in Google Cloud Console
# https://console.cloud.google.com/apis/dashboard → YouTube Data API v3 → Quotas
```

---

#### Test API connectivity

```bash
# Test API key
curl "https://www.googleapis.com/youtube/v3/channels?part=statistics&forUsername=youtube&key=$YOUTUBE_API_KEY" | jq .

# Test channel info
curl "https://www.googleapis.com/youtube/v3/channels?part=snippet,statistics&id=UCxxxxxxxxxx&key=$YOUTUBE_API_KEY" | jq .

# Test live broadcasts
curl "https://www.googleapis.com/youtube/v3/search?part=snippet&channelId=UCxxxxxxxxxx&eventType=live&type=video&key=$YOUTUBE_API_KEY" | jq .
```

---

#### Test router connectivity

```bash
# Test router health
curl -v http://router:8000/health

# Test message endpoint
curl -X POST http://router:8000/api/v1/message \
  -H "Content-Type: application/json" \
  -d '{
    "type": "youtube_chat",
    "channel_id": "UCxxxxxxxxxx",
    "text": "test message"
  }' -v
```

---

#### Database diagnostics

```bash
# Check table sizes
psql $DATABASE_URL << EOF
SELECT table_name,
  pg_size_pretty(pg_total_relation_size(quote_ident(table_name))) AS size
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY pg_total_relation_size(quote_ident(table_name)) DESC;
EOF

# Check slow queries
psql $DATABASE_URL << EOF
ALTER SYSTEM SET log_min_duration_statement = 1000;
SELECT pg_reload_conf();
EOF

# View logs
docker-compose exec postgres tail -f /var/log/postgresql/postgresql.log
```

---

## Health Checks

### Automated Health Monitoring

```bash
#!/bin/bash
# health-monitor.sh

while true; do
  if ! curl -sf http://localhost:8006/health > /dev/null; then
    echo "YouTube Live module is unhealthy!"
    # Send alert
    curl -X POST https://alerts.example.com \
      -d "YouTube Live module failed health check"

    # Auto-restart
    docker-compose restart youtube-live
  fi

  sleep 60
done
```

Run with: `bash health-monitor.sh &`

---

## Support Resources

- **Google YouTube API**: https://developers.google.com/youtube/v3
- **PubSubHubbub Spec**: https://github.com/pubsubhubbub/PubSubHubbub/wiki/Subscribers
- **PostgreSQL Docs**: https://www.postgresql.org/docs/
- **Quart Documentation**: https://quart.palletsprojects.com/
- **WaddleBot Issues**: https://github.com/penguintechinc/waddlebot/issues

---

## Getting Help

1. **Check logs**: `docker-compose logs -f youtube-live`
2. **Check this guide**: Search for your error message
3. **Check health**: `curl http://localhost:8006/health`
4. **Debug configuration**: `env | grep YOUTUBE`
5. **Report issue**: Include logs, configuration (redacted), and reproduction steps

For issues related to WaddleBot core, see main project troubleshooting.
