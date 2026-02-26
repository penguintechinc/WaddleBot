# Kick Module Usage Guide

## Quick Start

### Local Development

1. **Clone the repository:**

```bash
git clone https://github.com/penguintechinc/waddlebot.git
cd waddlebot
```

2. **Install dependencies:**

```bash
cd trigger/receiver/kick_module_flask
pip install -r requirements.txt
```

3. **Configure environment (`.env`):**

```bash
MODULE_PORT=8007
DATABASE_URL=postgresql://user:password@localhost:5432/waddlebot
CORE_API_URL=http://localhost:8000
ROUTER_API_URL=http://localhost:8001
LOG_LEVEL=DEBUG
SECRET_KEY=your-secret-key-min-32-chars
KICK_WEBHOOK_SECRET=webhook-secret-from-kick-console
KICK_PUSHER_KEY=eb1d5f283081a78b932c
KICK_PUSHER_CLUSTER=us2
REDIS_URL=redis://localhost:6379/0
```

4. **Run the module:**

```bash
python -m quart run --port 8007
# Or with hypercorn:
hypercorn -b 0.0.0.0:8007 -w 4 app:app
```

5. **Verify operation:**

```bash
curl http://localhost:8007/health
# Expected: {"status": "healthy"}

curl http://localhost:8007/api/v1/status
# Expected: {"module": "kick", "status": "operational", ...}
```

### Docker Deployment

1. **Build the image:**

```bash
docker build -t waddlebot/kick-module:latest trigger/receiver/kick_module_flask/
```

2. **Run container:**

```bash
docker run -d \
  --name kick-module \
  -p 8007:8007 \
  -e MODULE_PORT=8007 \
  -e DATABASE_URL=postgresql://... \
  -e CORE_API_URL=http://core-api:8000 \
  -e ROUTER_API_URL=http://router-api:8001 \
  -e KICK_WEBHOOK_SECRET=your-secret \
  -e KICK_PUSHER_KEY=eb1d5f283081a78b932c \
  -e KICK_PUSHER_CLUSTER=us2 \
  -e REDIS_URL=redis://redis:6379/0 \
  waddlebot/kick-module:latest
```

3. **Health check:**

```bash
docker exec kick-module curl http://localhost:8007/health
```

## Webhook Setup

### Configure Kick Platform Webhook

1. Log in to Kick creator dashboard
2. Navigate to **Integrations** → **Webhooks**
3. Add new webhook endpoint:
   - **URL**: `https://your-domain.com/webhook/kick`
   - **Secret**: Use value from `KICK_WEBHOOK_SECRET` env var (min 32 characters)
   - **Events**: Select all desired event types
4. Test webhook delivery (Kick dashboard provides test button)
5. Verify logs: `curl http://localhost:8007/api/v1/status | jq .stats`

### Webhook Event Types

Enable these in Kick dashboard:

- **Chat Messages** - `chat_message`
- **Subscriptions** - `subscription`
- **Gift Subscriptions** - `gifted_subscription`
- **Channel Follows** - `channel_follow`
- **Stream Events** - `stream_start`, `stream_end`
- **Raids** - `raid`
- **Moderation** - `ban`, `timeout`, `user_banned_from_channel`

## Real-Time Chat Integration

### Manual Chat Client Connection

The module automatically connects to Pusher chatrooms for tracked channels. To verify connection:

```bash
# Check active WebSocket connections
curl http://localhost:8007/api/v1/status | jq .components.websocket

# View connection logs
docker logs kick-module | grep "Pusher\|WebSocket"
```

### Monitoring Chat Events

View incoming chat events in logs:

```bash
# Filter for chat messages
docker logs kick-module | grep "chat_message"

# Filter for all events
docker logs kick-module | grep "event="

# Real-time tail with filtering
docker logs -f kick-module | grep -E "chat_message|subscription|raid"
```

### Event Processing Flow

1. **Webhook/WebSocket** → Module receives event
2. **Validation** → Event type and channel verification
3. **Enrichment** → Fetch user context from Core API
4. **Normalization** → Convert to standard schema
5. **Router** → Forward to `ROUTER_API_URL/api/v1/events`
6. **Processing** → Router delegates to command processors

## Database Integration

### Setup Database Schema

```bash
# Run migrations (if applicable)
cd trigger/receiver/kick_module_flask
python -m flask db upgrade

# Or manually ensure tables exist:
# - kick_events (event history)
# - kick_webhooks (webhook metadata)
# - channel_subscriptions (tracked channels)
```

### Query Event History

```sql
-- Count events by type (last 24h)
SELECT event_type, COUNT(*) as count
FROM kick_events
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY event_type
ORDER BY count DESC;

-- Find events from specific channel
SELECT * FROM kick_events
WHERE channel_id = '12345'
ORDER BY created_at DESC
LIMIT 100;

-- Check webhook delivery status
SELECT COUNT(*) as total,
       SUM(CASE WHEN router_status = 'success' THEN 1 ELSE 0 END) as delivered
FROM kick_webhooks
WHERE created_at > NOW() - INTERVAL '1 hour';
```

## Testing

### Unit Testing

```bash
cd trigger/receiver/kick_module_flask
pytest tests/unit/ -v

# Test specific module
pytest tests/unit/test_kick_api.py -v

# With coverage
pytest tests/unit/ --cov=src --cov-report=html
```

### Integration Testing

```bash
# Test with live database
pytest tests/integration/ -v --tb=short

# Test webhook signature verification
pytest tests/integration/test_webhook.py::test_hmac_validation -v
```

### Manual Testing with curl

**Test webhook delivery:**

```bash
# Generate HMAC signature
PAYLOAD='{"event":"chat_message","created_at":"2026-02-24T12:34:56Z","data":{"channel_id":12345,"username":"test_user","message":"Hello!"}}'
SECRET="your-webhook-secret"
SIGNATURE=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$SECRET" -hex | cut -d' ' -f2)

# Send request
curl -X POST http://localhost:8007/webhook/kick \
  -H "X-Signature: sha256=$SIGNATURE" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD"

# Expected response: 202 Accepted
```

**Test health endpoints:**

```bash
# Health check
curl http://localhost:8007/health

# Status with components
curl http://localhost:8007/api/v1/status | jq .

# Metrics
curl http://localhost:8007/metrics
```

## Monitoring & Observability

### Prometheus Metrics

The module exposes metrics at `/metrics` endpoint:

```bash
# View all kick-related metrics
curl http://localhost:8007/metrics | grep kick_

# Common queries:
# - kick_webhook_received_total - total webhooks
# - kick_event_processed_total - events by type
# - kick_websocket_connections_active - active chat connections
# - kick_router_api_latency_ms - processing latency
```

### Structured Logging

Logs are JSON-formatted for easy parsing:

```bash
# Filter for errors
docker logs kick-module | grep '"level":"ERROR"'

# Find slow router API calls
docker logs kick-module | grep '"router_latency_ms":' | awk -F'router_latency_ms":' '{print $2}' | awk -F',' '{print $1}' | awk '$1 > 1000'

# Track reconnection attempts
docker logs kick-module | grep '"event":"websocket_reconnect"'
```

### Setting Log Levels

```bash
# In .env file:
LOG_LEVEL=DEBUG    # Verbose (development)
LOG_LEVEL=INFO     # Standard (production)
LOG_LEVEL=WARNING  # Errors and warnings only
LOG_LEVEL=ERROR    # Critical errors only
```

## Performance Tuning

### Connection Pool Configuration

Edit `src/services/kick_api.py`:

```python
# Increase HTTP connection pool for high-load scenarios
connector = aiohttp.TCPConnector(
    limit=20,           # Total connections
    limit_per_host=10,  # Per-host limit (Kick API)
    ttl_dns_cache=300   # DNS cache timeout
)
```

### WebSocket Optimization

For streams with high chat volume:

```python
# In KickChatClient initialization:
# Batch message processing to reduce CPU
batch_size = 50
batch_timeout = 0.1  # seconds
```

### Database Connection Pool

In `config.py`:

```python
# Increase pool size for concurrent event processing
DB_POOL_SIZE = 20
DB_POOL_OVERFLOW = 10
DB_POOL_TIMEOUT = 30
```

## Troubleshooting Common Issues

### "Signature mismatch" errors

1. Verify `KICK_WEBHOOK_SECRET` matches Kick dashboard
2. Check for timestamp drift (system clock)
3. Ensure webhook secret is at least 32 characters

### WebSocket reconnecting frequently

1. Check network connectivity to `pusher.us2.pusher.com`
2. Verify `KICK_PUSHER_KEY` and `KICK_PUSHER_CLUSTER` are correct
3. Review logs for specific error messages
4. Check for firewall/proxy blocking Pusher connections

### Router API timeouts

1. Verify `ROUTER_API_URL` is reachable: `curl -I $ROUTER_API_URL/health`
2. Check Router API logs for capacity/errors
3. Increase timeout value: `ROUTER_TIMEOUT=30` (in seconds)
4. Consider load balancing if high event volume

### Database connection errors

1. Verify `DATABASE_URL` format: `postgresql://user:pass@host:5432/db`
2. Test connection: `psql $DATABASE_URL -c "SELECT 1;"`
3. Check connection limits: `PGCONNECT_TIMEOUT=10`
4. Monitor connection pool: `SELECT count(*) FROM pg_stat_activity;`

## Advanced Usage

### Scaling with Multiple Instances

Deploy multiple module instances behind a load balancer:

```yaml
# Kubernetes deployment example
replicas: 3
selector:
  app: kick-module
ports:
  - 8007
liveness_probe:
  httpGet: {path: /health, port: 8007}
  periodSeconds: 10
readiness_probe:
  httpGet: {path: /api/v1/status, port: 8007}
  periodSeconds: 5
```

**Redis Coordination:**

Use Redis for shared state across instances:

```python
# In app initialization
redis = Redis(url=REDIS_URL)

# Check active connections from all instances
redis.get('kick:active_channels')

# Coordinate Pusher subscriptions (avoid duplicate connections)
redis.incr(f'kick:websocket:{channel_id}')
```

### Custom Event Handlers

Extend event processing in `src/handlers/`:

```python
# src/handlers/custom.py
async def handle_custom_event(event):
    """Custom processing for specific event types"""
    if event.type == 'chat':
        # Custom logic
        await my_processor.process(event)
    return event
```

### Webhook Signature Debugging

```bash
# Enable detailed signature logging in .env
LOG_LEVEL=DEBUG
KICK_DEBUG_SIGNATURES=true

# Then check logs
docker logs kick-module | grep "signature\|hmac"
```

## See Also

- [API Documentation](API.md)
- [Configuration Guide](CONFIGURATION.md)
- [Architecture Details](ARCHITECTURE.md)
- [Troubleshooting Guide](TROUBLESHOOTING.md)
