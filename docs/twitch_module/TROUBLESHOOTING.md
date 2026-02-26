# Twitch Module Troubleshooting

## Common Issues & Solutions

### Service Startup Issues

#### Service fails to start with database connection error

**Symptoms**:
```
ERROR: database_connection_failed: FATAL: password authentication failed for user "waddle_user"
Service initialization failed
```

**Causes**:
- Invalid `DATABASE_URL` syntax
- Wrong database credentials
- Database server not running or unreachable
- PostgreSQL firewall/network issue

**Solutions**:
1. Verify connection string format:
   ```
   postgresql://username:password@host:port/database
   ```
   - Check username, password, host, port, database name

2. Test database connectivity:
   ```bash
   psql "postgresql://waddle_user:password@postgres:5432/waddlebot_db" -c "SELECT 1"
   ```

3. Check database server:
   ```bash
   # Is PostgreSQL running?
   docker logs postgres

   # Can you connect from another container?
   docker exec postgres psql -U waddle_user -d waddlebot_db -c "SELECT 1"
   ```

4. Verify network connectivity:
   ```bash
   docker exec twitch-module nc -zv postgres 5432
   ```

---

#### Service fails with Twitch authentication error

**Symptoms**:
```
ERROR: twitch_auth_failed: Invalid access token or client credentials
Unable to validate Twitch credentials
```

**Causes**:
- Expired OAuth tokens
- Invalid `TWITCH_CLIENT_ID` or `TWITCH_CLIENT_SECRET`
- Token belongs to different Twitch application

**Solutions**:
1. Verify credentials in Twitch console:
   - Go to https://dev.twitch.tv/console/apps
   - Check Client ID and Client Secret match env vars
   - Regenerate if needed

2. Check token expiration:
   ```bash
   # Tokens expire after ~60 days
   # Refresh via OAuth flow
   curl -X POST https://id.twitch.tv/oauth2/token \
     -d "client_id=<ID>&client_secret=<SECRET>&grant_type=refresh_token&refresh_token=<TOKEN>"
   ```

3. Verify bot account token:
   ```bash
   # Test bot token by connecting to IRC
   # Check logs for connection errors
   docker logs twitch-module -f | grep -i "auth\|token"
   ```

---

#### Service fails with "EventSub secret validation error"

**Symptoms**:
```
ERROR: eventsub_secret_mismatch: Cannot start EventSub handler
EVENTSUB_SECRET environment variable is required
```

**Causes**:
- `EVENTSUB_SECRET` not set in environment
- Secret is too short (Twitch requires minimum length)

**Solutions**:
1. Set a strong secret:
   ```bash
   export EVENTSUB_SECRET=$(openssl rand -hex 32)
   ```

2. Verify in Twitch EventSub console:
   - Go to https://dev.twitch.tv/console/extensions/eventsub
   - Create new subscription
   - Copy the secret provided

3. Update environment and restart:
   ```bash
   docker-compose down
   # Update .env with new EVENTSUB_SECRET
   docker-compose up
   ```

---

### Message Handling Issues

#### Bot not responding to messages in chat

**Symptoms**:
- User sends `!ping` in chat
- Bot doesn't respond
- No errors in logs

**Causes**:
- Bot not joined to channel
- IRC connection dropped
- Router API unreachable
- Message processing error

**Solutions**:
1. Verify bot is in channel:
   ```bash
   curl http://localhost:8002/api/v1/bot/channels | jq '.channels[] | select(.channel_name == "TARGET_CHANNEL")'

   # Should show:
   # {
   #   "status": "joined",
   #   "channel_id": "12345",
   #   ...
   # }
   ```

2. Check if channel is in database:
   ```bash
   psql $DATABASE_URL -c "SELECT * FROM channels WHERE channel_name = 'TARGET_CHANNEL';"
   # Must show: is_active = true
   ```

3. Verify IRC connection:
   ```bash
   docker logs twitch-module -f | grep -i "irc\|connected"
   # Should show: "IRC connection established"
   ```

4. Refresh channels and rejoin:
   ```bash
   curl -X POST http://localhost:8002/api/v1/bot/channels/refresh \
     -H "Authorization: Bearer <SERVICE_API_KEY>"

   # Wait 5-10 seconds, then verify
   curl http://localhost:8002/api/v1/bot/channels | jq '.channels[] | select(.channel_name == "TARGET_CHANNEL")'
   ```

5. Check Router API:
   ```bash
   # Is Router running?
   curl http://router:8001/health

   # Can Twitch Module reach it?
   docker exec twitch-module curl http://router:8001/api/v1/messages -v
   ```

6. Check logs for errors:
   ```bash
   docker logs twitch-module -f | grep -E "ERROR|WARNING"

   # Look for:
   # - API timeouts
   # - Auth failures
   # - Message parsing errors
   ```

---

#### Messages not being split when exceeding 500 characters

**Symptoms**:
- Bot tries to send 1000-char message in one line
- Gets silenced/rate limited by Twitch

**Causes**:
- `CHANNEL_MESSAGE_SPLIT_LENGTH` set too high
- Message splitting logic not triggered
- Twitch 500-char limit enforced by platform

**Solutions**:
1. Verify split length setting:
   ```bash
   curl http://localhost:8002/api/v1/status | jq '.config.channel_message_split_length'
   # Should be 500 (or lower)
   ```

2. Check actual message size:
   ```bash
   # Message size in characters (including special chars)
   python3 -c "import sys; print(len('YOUR_MESSAGE'))"
   ```

3. Test message split manually:
   ```bash
   curl -X POST http://localhost:8002/api/v1/bot/send \
     -H "Authorization: Bearer <SERVICE_API_KEY>" \
     -d '{
       "channel_id": "12345",
       "message": "'"$(python3 -c "print('test ' * 300)")"'"
     }' | jq '.split_count'

   # Should return: 2 (or higher, if split)
   ```

4. Check logs for split operations:
   ```bash
   docker logs twitch-module -f | grep -i "split"
   ```

---

#### Message appears as duplicate or repeated

**Symptoms**:
- Same message posted to chat multiple times
- Router sends response, bot sends it again
- Bot sends own responses multiple times

**Causes**:
- Retry logic triggering unnecessarily
- Duplicate message ID not being tracked
- EventSub deduplication failing

**Solutions**:
1. Check deduplication window:
   ```bash
   curl http://localhost:8002/api/v1/status | jq '.cache.dedup_window'
   # Should be: 5000 (tracks last 5000 message IDs)
   ```

2. Verify message ID tracking in logs:
   ```bash
   docker logs twitch-module -f | grep -i "dedup"
   ```

3. Increase dedup window if needed:
   ```bash
   # Edit .env and set:
   EVENTSUB_DEDUP_WINDOW=10000

   docker-compose restart twitch-module
   ```

---

### EventSub Webhook Issues

#### Webhooks not being received

**Symptoms**:
- EventSub events (subscribe, raid, follow) not triggering bot responses
- Logs show no webhook attempts
- `/api/v1/status` shows `eventsub_connected: false`

**Causes**:
- EventSub callback URL not publicly accessible
- Webhook not registered in Twitch console
- HMAC signature verification failing
- Network/firewall blocking incoming requests

**Solutions**:
1. Verify callback URL is reachable:
   ```bash
   # From internet (not from localhost)
   curl -I https://waddlebot.penguintech.cloud/eventsub/webhook
   # Should return 400 (no body) not connection error
   ```

2. Check EventSub subscriptions in Twitch console:
   - Go to https://dev.twitch.tv/console/extensions/eventsub
   - Verify subscriptions exist for target channels
   - Check status (should be "enabled", not "pending" or "failed")

3. Test webhook manually:
   ```bash
   # Generate HMAC signature
   MSG_ID="test-123"
   TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
   BODY='{"subscription":{"type":"channel.subscribe"},"event":{"broadcaster_user_id":"12345"}}'
   SECRET="your_eventsub_secret"

   HMAC=$(echo -n "${MSG_ID}${TIMESTAMP}${BODY}" | openssl dgst -sha256 -hmac "$SECRET" -hex | awk '{print $2}')

   curl -X POST http://localhost:8002/eventsub/webhook \
     -H "Twitch-Eventsub-Message-Id: $MSG_ID" \
     -H "Twitch-Eventsub-Timestamp: $TIMESTAMP" \
     -H "Twitch-Eventsub-Signature: sha256=$HMAC" \
     -d "$BODY"
   ```

4. Check webhook verification in logs:
   ```bash
   docker logs twitch-module -f | grep -i "hmac\|signature\|verification"
   ```

5. Verify EVENTSUB_SECRET is set correctly:
   ```bash
   # The secret must match what's in Twitch console
   # Can't retrieve existing secret, must regenerate

   # Get new secret from Twitch console, update .env, restart
   docker-compose down
   # Edit .env with new secret
   docker-compose up
   ```

---

#### "HMAC signature verification failed" error

**Symptoms**:
```
ERROR: eventsub_verification_failed: HMAC signature mismatch
403 Forbidden returned to webhook
```

**Causes**:
- `EVENTSUB_SECRET` doesn't match Twitch console
- Request body modified in transit
- Timestamp too old (>10 min)

**Solutions**:
1. Verify secret matches Twitch:
   - Twitch console shows secret only once during creation
   - If lost, create new subscription with new secret
   - Update `EVENTSUB_SECRET` env var with new value

2. Check timestamp is recent:
   - Twitch rejects requests >10 minutes old
   - Verify system clock is synced: `ntpdate -q pool.ntp.org`

3. Enable debug logging:
   ```bash
   # Set LOG_LEVEL=debug to see detailed HMAC info
   LOG_LEVEL=debug docker-compose up twitch-module

   docker logs twitch-module -f | grep -i "hmac\|verification"
   ```

---

#### Webhooks keep showing "pending" status in Twitch console

**Symptoms**:
- Twitch console shows subscription status as "pending"
- Never transitions to "enabled"
- After ~10 minutes, status becomes "failed"

**Causes**:
- Callback URL not responding to challenge
- 403 response to challenge request
- Timeout on challenge response

**Solutions**:
1. Verify challenge handling:
   - Twitch sends GET request with `challenge` param
   - Service should echo back the challenge value
   - Check logs for challenge requests

2. Check endpoint is accessible:
   ```bash
   # Test from internet
   curl -v https://waddlebot.penguintech.cloud/eventsub/webhook

   # Should return 400 (not 403, not timeout, not connection error)
   ```

3. Verify EventSub handler accepts GET requests:
   ```python
   @app.route('/eventsub/webhook', methods=['GET', 'POST'])
   async def eventsub_webhook():
       if request.method == 'GET':
           # Return challenge from query param
           challenge = request.args.get('challenge')
           return challenge, 200
   ```

4. Restart service and re-register subscription:
   ```bash
   docker-compose restart twitch-module

   # Delete old subscription, create new one
   # New subscription should transition to "enabled"
   ```

---

### Viewer Tracking Issues

#### Leaderboard not updating with viewer activity

**Symptoms**:
- Hub API not receiving viewer updates
- `/api/v1/status` shows `viewer_tracking_enabled: true` but `last_poll` is old
- Leaderboard shows no viewer presence changes

**Causes**:
- `VIEWER_TRACKING_ENABLED=false`
- Viewer polling not working
- Hub API unreachable or rejecting requests
- Stream not live (only tracks active streams)

**Solutions**:
1. Verify viewer tracking is enabled:
   ```bash
   curl http://localhost:8002/api/v1/status | jq '.viewer_tracking'

   # Should show:
   # "enabled": true,
   # "channels_tracked": 42,
   # "last_poll": "2025-02-24T10:29:45Z"
   ```

2. Check if stream is live:
   ```bash
   # Only active streams are tracked
   curl http://localhost:8002/api/v1/bot/channels | jq '.channels[] | select(.is_live == true)'
   ```

3. Verify polling is working:
   ```bash
   docker logs twitch-module -f | grep -i "viewer\|chatter"

   # Should show polls every 60s:
   # "component": "ViewerTracker",
   # "event": "chatters_poll_complete",
   # "channel_id": "12345",
   # "viewers_count": 420
   ```

4. Check Hub API connectivity:
   ```bash
   # Is Hub running?
   curl http://hub:8000/health

   # Can Twitch Module reach it?
   docker exec twitch-module curl http://hub:8000/api/v1/leaderboards/12345 -v
   ```

5. Verify polling interval:
   ```bash
   curl http://localhost:8002/api/v1/status | jq '.config.viewer_poll_interval'

   # Default is 60 seconds
   # Can reduce for faster updates (minimum 30s)
   ```

6. Check for Chatters API errors:
   ```bash
   docker logs twitch-module -f | grep -i "chatters\|error"

   # Look for rate limit (429) or auth errors (401)
   ```

---

#### Viewer count showing incorrect numbers

**Symptoms**:
- Leaderboard shows wrong number of viewers
- Same viewer appearing multiple times
- Viewers showing as "left" when still in chat

**Causes**:
- Poll interval too long (missing join/leave events)
- Cache not being cleared between polls
- User filter or bot exclusion not working

**Solutions**:
1. Reduce poll interval for accuracy:
   ```bash
   # Edit .env:
   VIEWER_POLL_INTERVAL=30  # Default is 60

   docker-compose restart twitch-module
   ```

2. Check viewer cache TTL:
   ```bash
   curl http://localhost:8002/api/v1/status | jq '.cache.viewer_ttl'
   ```

3. Verify bot is excluded from viewer list:
   ```bash
   # Bot (WaddleBot) shouldn't count as viewer
   docker logs twitch-module -f | grep -i "viewer\|chatter" | head -20
   ```

---

### Cache Issues

#### Cache not working / high API calls

**Symptoms**:
- Metrics show high Twitch API call count
- Cache hits are 0
- Redis connection errors in logs

**Causes**:
- `CACHE_TYPE=memory` (single-instance cache)
- Redis not running or unreachable
- Cache TTL set to 0
- Cache keys not being set

**Solutions**:
1. Verify cache type:
   ```bash
   curl http://localhost:8002/api/v1/status | jq '.cache.type'
   # Should be "redis" for production
   ```

2. Check Redis connectivity:
   ```bash
   docker logs redis -f

   # From twitch-module:
   docker exec twitch-module redis-cli -h redis ping
   # Should return: PONG
   ```

3. Check cache TTLs:
   ```bash
   curl http://localhost:8002/api/v1/status | jq '.cache'

   # Should show: channel_cache_ttl: 300
   ```

4. Monitor cache hits:
   ```bash
   curl http://localhost:8002/metrics | grep cache

   # Should show increasing hit count
   ```

---

### Performance Issues

#### High latency or slow responses

**Symptoms**:
- Bot takes 2-5 seconds to respond to messages
- `/metrics` shows high `message_latency_ms`
- Server CPU/memory usage high

**Causes**:
- Database connection pool exhausted
- Slow Twitch API calls
- Message queue backing up
- Cache misses causing fallback API calls

**Solutions**:
1. Check database pool:
   ```bash
   curl http://localhost:8002/api/v1/status | jq '.database.pool_size'

   # Increase if monitoring 100+ channels:
   DB_POOL_SIZE=50  # Default is 10
   ```

2. Monitor metrics:
   ```bash
   curl http://localhost:8002/metrics | grep -E "latency|error"

   # Look for high error rate or latency spikes
   ```

3. Check Twitch API rate limits:
   ```bash
   docker logs twitch-module -f | grep -i "rate_limit\|429"

   # If rate limited, reduce polling frequency
   ```

4. Scale horizontally:
   ```bash
   # Multiple instances with shared Redis
   docker-compose up -d --scale twitch-module=3
   ```

---

### Network & Connectivity Issues

#### "Connection refused" errors to Router or Hub

**Symptoms**:
```
ERROR: api_error: connection refused to http://router:8001
ERROR: api_error: connection refused to http://hub:8000
```

**Causes**:
- Router/Hub service not running
- Wrong service URL in env vars
- Network connectivity issue between containers
- Container DNS not resolving service names

**Solutions**:
1. Verify services are running:
   ```bash
   docker-compose ps

   # Should show: router UP, hub UP
   ```

2. Check service URLs:
   ```bash
   # Must match container names (if using docker-compose)
   ROUTER_API_URL=http://router:8001
   HUB_API_URL=http://hub:8000
   ```

3. Test connectivity from container:
   ```bash
   docker exec twitch-module curl http://router:8001/health
   docker exec twitch-module curl http://hub:8000/health
   ```

4. Check Docker network:
   ```bash
   docker network ls | grep waddlebot

   # All services must be on same network
   docker network inspect waddlebot-network
   ```

---

## Debug Mode

Enable full debug logging:

```bash
LOG_LEVEL=debug docker-compose up twitch-module
```

**Debug output includes**:
- All API calls and responses
- Cache operations
- Message processing steps
- IRC protocol messages
- EventSub verification details

## Log Analysis Tips

### Find errors quickly
```bash
docker logs twitch-module | grep -i error
```

### View specific component logs
```bash
docker logs twitch-module | grep TwitchBotService
docker logs twitch-module | grep EventSubHandler
docker logs twitch-module | grep ViewerTracker
```

### Parse JSON logs
```bash
docker logs twitch-module | jq '.message, .error'
```

### Follow logs with filtering
```bash
docker logs twitch-module -f | grep -E "ERROR|WARN"
```

## Performance Diagnosis

```bash
# Check service health
curl http://localhost:8002/health

# Get detailed status
curl http://localhost:8002/api/v1/status | jq .

# View metrics
curl http://localhost:8002/metrics | head -50

# Check database connections
psql $DATABASE_URL -c "SELECT datname, usename, count(*) FROM pg_stat_activity GROUP BY datname, usename;"

# Check Redis keys
docker exec redis redis-cli KEYS '*' | wc -l
docker exec redis redis-cli INFO stats
```

## Getting Help

If issues persist:
1. Collect logs: `docker logs twitch-module > twitch-module.log`
2. Collect status: `curl http://localhost:8002/api/v1/status > status.json`
3. Collect metrics: `curl http://localhost:8002/metrics > metrics.txt`
4. Include environment: `env | grep -E "TWITCH|ROUTER|HUB|CACHE" > env.txt`
5. Contact support with these files
