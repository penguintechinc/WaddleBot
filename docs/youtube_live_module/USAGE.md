# YouTube Live Module Usage Guide

Complete setup and operation instructions for the YouTube Live module.

## Prerequisites

- Python 3.12
- Docker (for container deployment)
- YouTube Data API v3 credentials (API key or OAuth 2.0)
- PostgreSQL database
- Redis cache (optional but recommended)
- Router module running (for message routing)

## Local Development Setup

### 1. Install Dependencies

```bash
cd trigger/receiver/youtube_live_module
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Create Environment File

Create a `.env` file in the module directory:

```bash
# Server Configuration
MODULE_PORT=8006
LOG_LEVEL=DEBUG
SECRET_KEY=your-secret-key-here

# YouTube API Configuration
YOUTUBE_API_KEY=AIzaSyDxxxxxxxxxxxxxxxxxxxxxxxxxx
YOUTUBE_CLIENT_ID=123456789-xxx.apps.googleusercontent.com
YOUTUBE_CLIENT_SECRET=GOCSPX-xxxxxxxxxxxxxxxx
YOUTUBE_WEBHOOK_CALLBACK_URL=https://your-domain.com/api/v1/webhook

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/waddlebot

# Router API
ROUTER_API_URL=http://localhost:8000

# Redis (optional)
REDIS_URL=redis://localhost:6379/0

# Chat Polling
CHAT_POLL_INTERVAL=5
CHAT_MAX_RESULTS=200
```

### 3. Get YouTube API Credentials

#### Option A: API Key (Simple Chat Polling)

For read-only access to public chat:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable YouTube Data API v3
4. Create an API key (Credentials → Create Credentials → API Key)
5. Copy the key to `YOUTUBE_API_KEY`

#### Option B: OAuth 2.0 (Channel Management)

For registering/unregistering channels:

1. Go to Google Cloud Console
2. Create OAuth 2.0 credentials (Credentials → Create Credentials → OAuth Client ID)
3. Choose "Web application"
4. Add authorized redirect URIs
5. Copy Client ID and Secret to `YOUTUBE_CLIENT_ID` and `YOUTUBE_CLIENT_SECRET`

#### Option C: Service Account (Server-to-Server)

For applications without user interaction:

1. Create service account in Google Cloud Console
2. Download JSON key file
3. Store securely and reference in code

### 4. Initialize Database

Ensure PostgreSQL is running and create the database:

```bash
psql -U postgres -c "CREATE DATABASE waddlebot;"
```

The module will automatically create tables on first run via PyDAL.

### 5. Start the Module

```bash
# With debug output
python main.py

# Or via hypercorn directly
hypercorn app:app --bind 0.0.0.0:8006 --reload
```

You should see output like:

```
[2026-02-24 10:30:00] Starting YouTube Live module
[2026-02-24 10:30:01] Database connection successful
[2026-02-24 10:30:01] ChatPoller service started
[2026-02-24 10:30:02] Server running on http://0.0.0.0:8006
```

### 6. Verify Health

```bash
curl http://localhost:8006/health
```

Response:

```json
{
  "status": "healthy",
  "uptime_seconds": 2,
  "version": "1.0.0"
}
```

## Common Tasks

### Register a YouTube Channel

```bash
curl -X POST http://localhost:8006/api/v1/channels/register \
  -H "Content-Type: application/json" \
  -d '{
    "channel_id": "UCxxxxxxxxxx",
    "channel_name": "My YouTube Channel"
  }'
```

Response:

```json
{
  "status": "success",
  "channel_id": "UCxxxxxxxxxx",
  "channel_name": "My YouTube Channel",
  "registered_at": "2026-02-24T10:30:00Z"
}
```

The ChatPoller will automatically begin monitoring this channel.

### Unregister a Channel

```bash
curl -X DELETE http://localhost:8006/api/v1/channels/UCxxxxxxxxxx
```

### View Registered Channels

```bash
curl http://localhost:8006/api/v1/channels
```

Response:

```json
{
  "status": "success",
  "channels": [
    {
      "channel_id": "UCxxxxxxxxxx",
      "channel_name": "My Channel",
      "is_active": true,
      "broadcast_id": "YxxxxxxxxxB",
      "registered_at": "2026-02-24T09:00:00Z",
      "last_message_at": "2026-02-24T10:35:15Z",
      "error_count": 0
    }
  ],
  "total_channels": 1,
  "active_streams": 1
}
```

### Check Active Broadcasts

```bash
curl http://localhost:8006/api/v1/broadcasts/UCxxxxxxxxxx
```

### View Metrics

```bash
curl http://localhost:8006/metrics
```

## Docker Deployment

### Build Image

```bash
cd trigger/receiver/youtube_live_module
docker build -t youtube-live-module:latest .
```

### Run Container

```bash
docker run -d \
  -p 8006:8006 \
  -e YOUTUBE_API_KEY=AIzaSyDxxxxxxxxxx \
  -e DATABASE_URL=postgresql://user:pass@db:5432/waddlebot \
  -e ROUTER_API_URL=http://router:8000 \
  -e LOG_LEVEL=INFO \
  --name youtube-live-module \
  youtube-live-module:latest
```

### Docker Compose Integration

Add to `docker-compose.yml`:

```yaml
youtube-live:
  build:
    context: trigger/receiver/youtube_live_module
    dockerfile: Dockerfile
  ports:
    - "8006:8006"
  environment:
    MODULE_PORT: 8006
    YOUTUBE_API_KEY: ${YOUTUBE_API_KEY}
    DATABASE_URL: postgresql://waddlebot:password@postgres:5432/waddlebot
    ROUTER_API_URL: http://router:8000
    REDIS_URL: redis://redis:6379/0
    LOG_LEVEL: INFO
  depends_on:
    - postgres
    - redis
    - router
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8006/health"]
    interval: 30s
    timeout: 10s
    retries: 3
```

Then start:

```bash
docker-compose up -d youtube-live
```

## Operational Workflows

### Monitor a Live Stream

1. **Ensure stream is live on YouTube**

2. **Register the channel** (if not already registered):
   ```bash
   curl -X POST http://localhost:8006/api/v1/channels/register \
     -H "Content-Type: application/json" \
     -d '{"channel_id": "UCxxxxxxxxxx", "channel_name": "Stream Channel"}'
   ```

3. **ChatPoller automatically discovers active broadcasts** (checks every 5 seconds)

4. **Messages are captured and routed**:
   - Chat messages → Routed with type `youtube_chat`
   - Super Chats → Routed with type `youtube_super_chat` + amount/currency
   - Super Stickers → Routed with type `youtube_super_sticker`
   - Memberships → Routed with type `youtube_membership`

5. **Stream end is auto-detected** when API returns HTTP 403 (no active broadcast)

### Handle Stream End

The module automatically detects stream end when:
- API call returns HTTP 403 (broadcast no longer live)
- `last_message_at` timestamp stops updating
- Broadcast status changes to `completed`

When detected:
- Polling stops for that broadcast
- Module continues monitoring for new broadcasts from the channel
- Error counter resets

### Manage Polling Configuration

Adjust polling behavior via environment variables:

```bash
# Poll every 3 seconds (faster, more API quota usage)
CHAT_POLL_INTERVAL=3

# Poll every 10 seconds (slower, saves quota)
CHAT_POLL_INTERVAL=10

# Fetch more messages per poll (up to 200)
CHAT_MAX_RESULTS=200

# Fetch fewer messages per poll
CHAT_MAX_RESULTS=50
```

After changing variables, restart the module:

```bash
# Development
pkill -f "python main.py"
python main.py

# Docker
docker-compose restart trigger-youtube
```

### Webhook Integration

The module receives stream events via PubSubHubbub:

1. **Subscribe to channel** (manual or automatic):
   ```python
   youtube_client = YouTubeClient(api_key, oauth_tokens)
   await youtube_client.subscribe_channel("UCxxxxxxxxxx")
   ```

2. **YouTube sends GET request to verify**:
   - Module responds with challenge token
   - Subscription confirmed

3. **YouTube sends POST notifications** on stream start/end:
   - Module parses Atom XML
   - Routes event with type `youtube_stream_started` or `youtube_stream_ended`

4. **Unsubscribe** (manual or automatic):
   ```python
   await youtube_client.unsubscribe_channel("UCxxxxxxxxxx")
   ```

### Credential Management

OAuth tokens are stored in database with Redis caching:

```python
# Tokens are automatically refreshed when expired
# No manual refresh needed
token = await youtube_client.get_channel_token("UCxxxxxxxxxx")

# Force refresh if needed
token = await youtube_client.refresh_channel_token("UCxxxxxxxxxx")
```

### Error Recovery

The module has built-in error resilience:

**Error Tracking:**
- Each channel tracks consecutive polling errors
- After 10+ errors, channel is automatically removed
- Error counter resets after successful poll

**Common Errors:**

- `403 Forbidden`: Stream no longer active (expected, not an error)
- `401 Unauthorized`: Invalid API key or expired token → Check credentials
- `429 Too Many Requests`: Quota exceeded → Increase poll interval
- `500 Server Error`: YouTube API issue → Retry automatically

**Manual Recovery:**

```bash
# View error status
curl http://localhost:8006/api/v1/channels

# If a channel has high error_count, unregister and re-register
curl -X DELETE http://localhost:8006/api/v1/channels/UCxxxxxxxxxx
curl -X POST http://localhost:8006/api/v1/channels/register \
  -H "Content-Type: application/json" \
  -d '{"channel_id": "UCxxxxxxxxxx", "channel_name": "My Channel"}'
```

## Performance Tuning

### Reduce API Quota Usage

```bash
# Increase poll interval
CHAT_POLL_INTERVAL=10

# Reduce results per poll
CHAT_MAX_RESULTS=50

# Single channel: ~288 API units/day (1 per 5 seconds)
# 10 channels: ~2,880 API units/day
# 100 channels: ~28,800 API units/day (quota exceeded!)
```

### Optimize Concurrent Polling

The module uses async/await for concurrent channel polling:

```python
# Default: Polls all channels concurrently
# Each poll completes in ~500ms
# 100 channels = ~500ms total (not 50 seconds)
```

### Database Connection Pooling

Adjust for high throughput:

```bash
# In config.py
DB_POOL_SIZE=20        # Default 10
DB_MAX_OVERFLOW=10     # Default 5
```

## Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for detailed troubleshooting guide including:
- Chat polling not working
- Messages not reaching router
- API authentication errors
- Database connection issues
- High memory usage
- Webhook subscription failures

## Testing

See [TESTING.md](TESTING.md) for unit, integration, and end-to-end testing procedures.

## Monitoring & Observability

### Log Levels

Control verbosity via `LOG_LEVEL` environment variable:

```bash
LOG_LEVEL=DEBUG      # Verbose, includes all API calls
LOG_LEVEL=INFO       # Standard, production recommended
LOG_LEVEL=WARNING    # Errors and warnings only
LOG_LEVEL=ERROR      # Errors only
```

### Key Metrics to Monitor

Via `/metrics` endpoint:

```
youtube_chat_messages_total{type="chat"}        # Chat message count
youtube_chat_messages_total{type="super_chat"}  # Super Chat count
youtube_chat_messages_total{type="membership"}  # Membership count
youtube_polling_errors_total                    # Error count
youtube_active_streams                          # Active broadcast count
```

### Health Monitoring

```bash
# Monitor every 30 seconds
watch -n 30 'curl -s http://localhost:8006/health | jq .'

# Set up alerting for unhealthy status
```

## Security Considerations

### API Key Protection

- Never commit API keys to version control
- Use environment variables or secret management
- Rotate keys regularly
- Restrict API key to YouTube Data API only

### OAuth Token Security

- Tokens stored encrypted in database
- Refresh tokens rotated automatically
- Never log tokens in output
- Use HTTPS in production

### Webhook Verification

- Verify webhook signature if enabled
- Validate callback URL matches registered

## Next Steps

- Review [CONFIGURATION.md](CONFIGURATION.md) for all environment options
- Check [ARCHITECTURE.md](ARCHITECTURE.md) to understand system design
- Run tests with [TESTING.md](TESTING.md)
- Monitor with [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
