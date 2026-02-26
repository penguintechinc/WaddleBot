# Twitch Module Usage Guide

## Quick Start

### Local Development

```bash
# Clone and setup
git clone https://github.com/penguintechinc/waddlebot.git
cd waddlebot/trigger/receiver/twitch_module

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your Twitch credentials and API URLs

# Run locally
python -m hypercorn main:app --bind 0.0.0.0:8002 --reload
```

### Docker Deployment

```bash
# Build image
docker build -t twitch-module:latest .

# Run container
docker run -p 8002:8002 \
  --env-file .env \
  twitch-module:latest

# Verify health
curl http://localhost:8002/health
```

---

## Common Tasks

### Add a Channel to Monitor

**Via Database** (automated sync):
```sql
INSERT INTO channels (channel_id, channel_name, community_id, is_active)
VALUES ('12345', 'example_channel', 'comm-123', true);
```

The bot auto-discovers this channel on the next refresh cycle (default: 300 seconds). Force immediate sync:

```bash
curl -X POST http://localhost:8002/api/v1/bot/channels/refresh \
  -H "Authorization: Bearer <SERVICE_API_KEY>"
```

**Verify Channel Joined**:
```bash
curl http://localhost:8002/api/v1/bot/channels | jq '.channels[] | select(.channel_name == "example_channel")'
```

---

### Remove a Channel

**Via Database**:
```sql
UPDATE channels SET is_active = false WHERE channel_id = '12345';
```

The bot will leave the channel on the next refresh cycle. Force immediate disconnect:

```bash
curl -X POST http://localhost:8002/api/v1/bot/channels/12345/leave \
  -H "Authorization: Bearer <SERVICE_API_KEY>"
```

---

### Send a Message to Chat

**From Internal Service** (Router, Hub, etc.):
```bash
curl -X POST http://localhost:8002/api/v1/bot/send \
  -H "Authorization: Bearer <SERVICE_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "channel_id": "12345",
    "message": "Hello, community! This is a test message."
  }'
```

**Example with Reply**:
```bash
curl -X POST http://localhost:8002/api/v1/bot/send \
  -H "Authorization: Bearer <SERVICE_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "channel_id": "12345",
    "message": "@user Here is your response!",
    "reply_to_message_id": "original_msg_id"
  }'
```

**Long Messages** (auto-split):
```bash
# Message longer than 500 chars automatically split into multiple messages
curl -X POST http://localhost:8002/api/v1/bot/send \
  -H "Authorization: Bearer <SERVICE_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "channel_id": "12345",
    "message": "'"$(python3 -c "print('x' * 1500)")"'"
  }'
```

---

## Command Handling

### Broadcaster-Only Commands

Commands prefixed with `!!` are restricted to channel broadcaster:

```
User: !test    → Allowed (normal command)
User: !!admin  → Only broadcaster can use this

If non-broadcaster tries !!admin:
Bot: @user This command is restricted to the broadcaster.
```

### Message Splitting Example

If command response exceeds 500 characters:

```
Input:  "This is a very long response that exceeds 500 characters..."
Output:
  [1/3] "This is a very long response that exceeds... [continue]"
  [2/3] "[continue] of the response... [continue]"
  [3/3] "[continue] final part of response."
```

---

## Monitoring & Debugging

### Check Service Status

```bash
curl http://localhost:8002/api/v1/status | jq .
```

**Output example**:
```json
{
  "service": "twitch-module",
  "version": "v1.2.0",
  "bot": {
    "enabled": true,
    "connected": true,
    "active_channels": 42,
    "total_channels": 50
  },
  "eventsub": {
    "enabled": true,
    "connected": true,
    "subscriptions_active": 210
  },
  "viewer_tracking": {
    "enabled": true,
    "channels_tracked": 42,
    "last_poll": "2025-02-24T10:29:45Z"
  }
}
```

### View Prometheus Metrics

```bash
curl http://localhost:8002/metrics | grep twitch

# Example output:
# twitch_messages_total{source="irc"} 125000
# twitch_errors_total{type="api"} 8
# twitch_channels_active 42
```

### Check Channel Status

```bash
# List all joined channels
curl http://localhost:8002/api/v1/bot/channels | jq '.channels'

# Filter by live status
curl http://localhost:8002/api/v1/bot/channels | jq '.channels[] | select(.is_live == true)'

# Find specific channel
curl http://localhost:8002/api/v1/bot/channels | jq '.channels[] | select(.channel_name == "example_channel")'
```

### View Logs

```bash
# Docker container logs
docker logs twitch-module -f

# Follow specific log level
docker logs twitch-module -f | grep "ERROR\|WARNING"

# Parse JSON logs
docker logs twitch-module -f | jq '.message, .error'
```

---

## Integration Patterns

### Router Integration

The router calls the bot to send command responses:

```
1. User sends: !ping
2. Bot receives in IRC chat
3. Bot POSTs to Router: { channel_id, user_id, message, command }
4. Router processes command, returns response
5. Bot receives response, sends to chat via /api/v1/bot/send
```

**Example router response**:
```bash
# From router to twitch-module
curl -X POST http://twitch-module:8002/api/v1/messages \
  -H "Authorization: Bearer <ROUTER_API_KEY>" \
  -d '{
    "channel_id": "12345",
    "user_id": "67890",
    "message": "@user pong! Latency: 45ms",
    "context": { "command": "!ping" }
  }'
```

### Hub Integration (Leaderboards)

Viewer activity is sent to Hub API for leaderboard tracking:

```
1. Viewer tracker polls Chatters API every 60s
2. Detects join/leave/heartbeat for each viewer
3. POSTs to Hub API: { channel_id, viewers[], events[] }
4. Hub updates leaderboard with viewer presence
```

**Example hub payload**:
```json
{
  "channel_id": "12345",
  "viewers": [
    { "user_id": "u1", "user_login": "viewer1", "event": "join" },
    { "user_id": "u2", "user_login": "viewer2", "event": "heartbeat" },
    { "user_id": "u3", "user_login": "viewer3", "event": "leave" }
  ],
  "poll_timestamp": "2025-02-24T10:30:00Z"
}
```

---

## EventSub Webhooks

### Manual Webhook Testing

Register a webhook with Twitch (via Twitch console), then verify delivery:

```bash
# Check EventSub metrics
curl http://localhost:8002/metrics | grep eventsub

# Sample webhook payload (for testing)
curl -X POST http://localhost:8002/eventsub/webhook \
  -H "Twitch-Eventsub-Message-Id: 123e4567-e89b-12d3-a456-426614174000" \
  -H "Twitch-Eventsub-Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  -H "Twitch-Eventsub-Signature: sha256=abc123def456" \
  -H "Content-Type: application/json" \
  -d '{
    "subscription": {
      "id": "sub-123",
      "type": "channel.subscribe",
      "condition": { "broadcaster_user_id": "12345" }
    },
    "event": {
      "broadcaster_user_id": "12345",
      "broadcaster_user_name": "Channel Owner",
      "user_id": "67890",
      "user_login": "new_subscriber",
      "tier": "1000"
    }
  }'
```

### Event Handling

**Subscribe event**:
- Triggers announcement: "@new_subscriber Welcome to the channel!"
- Updates leaderboard with tier information
- Sends to Hub API for tracking

**Raid event**:
- Bot posts: "@raiding_user Thanks for the raid with 100 viewers!"
- Tracks raid origin and viewer count

**Follow event**:
- Bot posts: "New follower: @follower_name"
- Updates engagement metrics

**Cheer event**:
- Bot posts: "@cheerer Thanks for the 500 bits!"
- Tracks total bits donated

**Stream.online event**:
- Bot posts: "Stream is now LIVE! Come watch!"
- Activates leaderboard tracking
- Updates channel status

**Stream.offline event**:
- Deactivates leaderboard tracking
- Archives final viewer metrics

---

## Troubleshooting

### Bot Not Responding to Messages

**Check**:
1. Is bot joined to channel? `curl http://localhost:8002/api/v1/bot/channels | jq '.channels[] | select(.channel_name == "YOUR_CHANNEL")'`
2. Is `TWITCH_BOT_ENABLED=true`?
3. Are logs showing errors? `docker logs twitch-module -f`

**Fix**:
```bash
# Refresh channels and force rejoin
curl -X POST http://localhost:8002/api/v1/bot/channels/refresh \
  -H "Authorization: Bearer <SERVICE_API_KEY>"

# Check logs for rejection reason
docker logs twitch-module -f | grep -i "error\|failed"
```

### EventSub Webhooks Not Received

**Check**:
1. Is `EVENTSUB_ENABLED=true`?
2. Is `EVENTSUB_CALLBACK_URL` correct and publicly accessible?
3. Is webhook registered in Twitch console?

**Test**:
```bash
# Verify callback URL is reachable from internet
curl -I https://waddlebot.penguintech.cloud/eventsub/webhook

# Check HMAC verification in logs
docker logs twitch-module -f | grep -i "hmac\|signature"
```

### Viewer Tracking Not Working

**Check**:
1. Is stream live? (only tracks active streams)
2. Is `VIEWER_TRACKING_ENABLED=true`?
3. Does channel have viewers?

**Debug**:
```bash
# Check last poll time
curl http://localhost:8002/api/v1/status | jq '.viewer_tracking'

# Check metrics for poll success rate
curl http://localhost:8002/metrics | grep viewer
```

### Message Split Not Working

**Check**:
1. Is message longer than 500 chars?
2. Check `CHANNEL_MESSAGE_SPLIT_LENGTH` env var

**Test**:
```bash
# Send 1500-char message
curl -X POST http://localhost:8002/api/v1/bot/send \
  -H "Authorization: Bearer <SERVICE_API_KEY>" \
  -d '{
    "channel_id": "12345",
    "message": "'"$(python3 -c "print('test ' * 300)")"'"
  }' | jq '.split_count'
```

---

## Performance Tips

1. **Reduce VIEWER_POLL_INTERVAL** if you need faster leaderboard updates (minimum: 30s)
2. **Use Redis caching** for distributed deployments (set `CACHE_TYPE=redis`)
3. **Increase DB_POOL_SIZE** if monitoring 100+ channels
4. **Monitor metrics** regularly: `curl http://localhost:8002/metrics`

---

## Scaling

### Single Region (Development)

- One Twitch Module instance
- In-memory cache
- Database connection pool: 10-20

### Multi-Region (Production)

- Multiple Twitch Module instances
- Shared Redis cache
- Database connection pool: 20-50
- Load balancer (ALB) distributes HTTP requests
- EventSub webhooks go to single entry point (ALB handles distribution)

---

## Maintenance

### Daily

- Check `/health` endpoint responds 200
- Monitor error rate: `curl http://localhost:8002/metrics | grep error`

### Weekly

- Review logs for warnings
- Check channel join/leave accuracy: `curl http://localhost:8002/api/v1/bot/channels`
- Verify viewer tracking poll frequency

### Monthly

- Review Twitch API rate limit usage
- Optimize VIEWER_POLL_INTERVAL based on load
- Refresh access tokens if approaching expiration
