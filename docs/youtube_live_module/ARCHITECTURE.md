# YouTube Live Module Architecture

Detailed design and architectural patterns for the YouTube Live module.

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                  YouTube Live Module                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────┐       ┌──────────────────┐           │
│  │  ChatPoller      │       │ WebhookHandler   │           │
│  │  (Background)    │       │ (HTTP Server)    │           │
│  └────────┬─────────┘       └────────┬─────────┘           │
│           │                          │                     │
│  ┌────────▼──────────────────────────▼──────┐             │
│  │     YouTubeClient (Async HTTP)           │             │
│  │  - YouTube Data API v3 communication     │             │
│  │  - OAuth credential management          │             │
│  │  - Response parsing & validation         │             │
│  └────────┬──────────────────────────────────┘             │
│           │                                               │
├───────────┼──────────────────────────────────────────────┤
│           │                                               │
│  ┌────────▼─────────────┐  ┌──────────────────────────┐ │
│  │ PostgreSQL Database  │  │   Redis (Optional)       │ │
│  │ - Channels           │  │ - Credential Cache       │ │
│  │ - Credentials        │  │ - Session Storage        │ │
│  │ - Messages (logged)  │  │ - Rate Limiting          │ │
│  └──────────────────────┘  └──────────────────────────┘ │
│                                                         │
└─────────────────────────────────────────────────────────┘
         │                              │
         ▼                              ▼
┌──────────────────────┐    ┌──────────────────────┐
│  YouTube Data API v3 │    │  YouTube PubSub      │
│  - Live chat         │    │  - Stream events     │
│  - Broadcasts        │    │  - Notifications     │
│  - Channel info      │    │                      │
└──────────────────────┘    └──────────────────────┘
         ▲                              │
         │                              │
└─────────────────────┬────────────────┘
                      │
                      ▼
              ┌──────────────┐
              │ Router API   │
              │ Event Queue  │
              └──────────────┘
```

## Component Architecture

### 1. YouTubeClient Service

**Purpose**: Async HTTP client for YouTube Data API v3 and OAuth 2.0

**Responsibilities**:
- Authenticated requests to YouTube API
- OAuth credential management and refresh
- Response parsing and validation
- Error handling and retry logic

**Key Methods**:

```python
class YouTubeClient:
    async def get_channel_info(channel_id: str) -> dict
    async def get_live_broadcasts(channel_id: str) -> list
    async def get_live_chat_messages(chat_id: str, page_token: str) -> dict
    async def subscribe_channel(channel_id: str) -> bool
    async def unsubscribe_channel(channel_id: str) -> bool
    async def get_channel_token(channel_id: str) -> dict
    async def refresh_channel_token(channel_id: str) -> dict
```

**Data Flow**:

```
┌─ HTTP Request ──────────────────┐
│ GET /youtube/v3/live/chatMessages?
│ - liveChatId (from broadcast)
│ - pageToken (pagination)
│ - maxResults (message limit)
└─────────────────────────────────┘
              │
              ▼
    ┌─────────────────────┐
    │ YouTube Data API v3 │
    └──────────┬──────────┘
               │
    ┌──────────▼──────────────────┐
    │ Response (JSON)             │
    │ - messages array            │
    │ - nextPageToken (optional)  │
    │ - pollingDelayMillis        │
    └──────────┬──────────────────┘
               │
    ┌──────────▼──────────────────────┐
    │ Parse & Validate                │
    │ - Extract message content       │
    │ - Detect message type           │
    │ - Parse Super Chat amounts      │
    │ - Parse membership info         │
    └──────────┬──────────────────────┘
               │
    ┌──────────▼─────────────────┐
    │ Message Objects (typed)    │
    │ - ChatMessage              │
    │ - SuperChatMessage         │
    │ - SuperStickerMessage      │
    │ - MembershipMessage        │
    └────────────────────────────┘
```

### 2. ChatPoller Service

**Purpose**: Background async polling service for live chat messages

**Responsibilities**:
- Maintain list of registered channels
- Discover active broadcasts for each channel
- Poll chat at configurable intervals
- Detect stream end conditions
- Track and manage polling errors
- Send messages to router

**Polling Loop**:

```
┌─────────────────────────────────────────┐
│ ChatPoller Main Loop (async)            │
├─────────────────────────────────────────┤
│                                         │
│ while is_running:                      │
│   for each registered_channel:         │
│     try:                               │
│       broadcasts = get_live_broadcasts │
│       if broadcasts:                   │
│         for broadcast in broadcasts:   │
│           chat_id = broadcast.chat_id  │
│           messages = poll_chat(chat_id)│
│           for message in messages:     │
│             route_message(message)     │
│           store_page_token()           │
│       else:                            │
│         stream_ended(channel)          │
│       reset_error_count(channel)       │
│     except Exception as e:             │
│       increment_error_count(channel)   │
│       if error_count > threshold:      │
│         remove_channel(channel)        │
│                                        │
│   await sleep(CHAT_POLL_INTERVAL)     │
│                                        │
└─────────────────────────────────────────┘
```

**Channel State Machine**:

```
┌──────────┐
│ INACTIVE │
└────┬─────┘
     │ (register)
     ▼
┌──────────┐
│ POLLING  │◄──── (error recovery)
└────┬─────┘
     │ (discovers broadcast)
     ▼
┌───────────┐
│ STREAMING │
└────┬──────┘
     │ (stream ends / 10+ errors)
     ▼
┌──────────┐
│ REMOVED  │
└──────────┘
```

**Pagination Strategy**:

```
First Poll:
  - pageToken = null
  - Fetch first batch of messages
  - Store nextPageToken in DB

Subsequent Polls:
  - pageToken = stored nextPageToken
  - Fetch new messages since last poll
  - Only new messages after last polled timestamp
  - Update stored pageToken

Stream Ends:
  - Reset pageToken
  - Wait for next stream
```

### 3. WebhookHandler

**Purpose**: Receives and processes PubSubHubbub notifications from YouTube

**Responsibilities**:
- Handle subscription verification challenges
- Parse Atom XML feeds from YouTube
- Extract stream start/end events
- Forward events to router
- Validate webhook signatures

**Webhook Flow**:

```
┌──────────────────────────────────────┐
│ 1. Subscription Request (automatic)  │
├──────────────────────────────────────┤
│                                      │
│ POST to YouTube Hub:                 │
│ - hub.callback = our webhook URL    │
│ - hub.topic = channel feed URL      │
│ - hub.mode = "subscribe"            │
│                                      │
└──────────────────┬───────────────────┘
                   │
    ┌──────────────▼──────────────────┐
    │ 2. Verification Challenge (GET) │
    ├──────────────────────────────────┤
    │                                  │
    │ GET /api/v1/webhook?            │
    │ - hub.challenge = token         │
    │ - hub.mode = "subscribe"        │
    │ - hub.topic = ...               │
    │                                  │
    │ Response: plain text challenge  │
    │                                  │
    └──────────────┬───────────────────┘
                   │
    ┌──────────────▼─────────────────────┐
    │ 3. Notifications (Atom XML)         │
    ├─────────────────────────────────────┤
    │                                     │
    │ POST /api/v1/webhook               │
    │ Content-Type: application/atom+xml │
    │                                     │
    │ <?xml version="1.0"?>              │
    │ <feed>                             │
    │   <entry>                          │
    │     <link href="watch?v=xyz"/>     │
    │     <published>2026-02-24...       │
    │     <updated>2026-02-24...         │
    │   </entry>                         │
    │ </feed>                            │
    │                                     │
    └──────────────┬─────────────────────┘
                   │
    ┌──────────────▼────────────────────┐
    │ 4. Parse & Route Event             │
    ├────────────────────────────────────┤
    │                                    │
    │ - Extract video_id from link      │
    │ - Determine if new/updated        │
    │ - Create stream_started event     │
    │ - POST to router API              │
    │ - Respond 200 OK to YouTube       │
    │                                    │
    └────────────────────────────────────┘
```

**XML Parsing**:

```python
# YouTube sends Atom format
<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>YouTube video feed</title>
  <link rel="hub" href="https://pubsubhubbub.appspot.com"/>
  <link rel="self" href="https://www.youtube.com/xml/feeds/videos.xml"/>
  <entry>
    <id>yt:video:dQw4w9WgXcQ</id>
    <yt:videoId>dQw4w9WgXcQ</yt:videoId>
    <title>Video Title</title>
    <link rel="alternate" href="http://www.youtube.com/watch?v=dQw4w9WgXcQ"/>
    <author>
      <name>Channel Name</name>
      <uri>http://www.youtube.com/channel/UCxxxxxxxxxx</uri>
    </author>
    <published>2026-02-24T10:00:00Z</published>
    <updated>2026-02-24T10:35:15Z</updated>
  </entry>
</feed>
```

## Data Flow

### Message Routing Pipeline

```
YouTube API
    │
    ▼
ChatPoller (async polling)
    │
    ├─ Parse ChatMessage
    ├─ Parse SuperChatMessage
    ├─ Parse SuperStickerMessage
    └─ Parse MembershipMessage
    │
    ▼
Message Enrichment
    ├─ Add channel_id
    ├─ Add broadcast_id
    ├─ Add timestamp
    └─ Add source="youtube_live"
    │
    ▼
Message Validation
    ├─ Check required fields
    ├─ Sanitize text content
    ├─ Validate amounts (Super Chat)
    └─ Validate URLs
    │
    ▼
Router API (POST /api/v1/message)
    │
    ├─ Queue storage
    ├─ Event broadcasting
    └─ Consumer routing
    │
    ▼
Core Platform Processing
    ├─ Reputation system
    ├─ Command parsing
    ├─ Channel distribution
    └─ Analytics
```

## Database Schema

### Core Tables

```sql
-- Registered channels
CREATE TABLE youtube_channels (
  id SERIAL PRIMARY KEY,
  channel_id VARCHAR(255) UNIQUE NOT NULL,
  channel_name VARCHAR(255) NOT NULL,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  error_count INTEGER DEFAULT 0,
  last_message_at TIMESTAMP,
  webhook_subscribed BOOLEAN DEFAULT false
);

-- Active broadcast tracking
CREATE TABLE youtube_broadcasts (
  id SERIAL PRIMARY KEY,
  channel_id VARCHAR(255) FOREIGN KEY,
  broadcast_id VARCHAR(255) UNIQUE NOT NULL,
  chat_id VARCHAR(255) NOT NULL,
  title VARCHAR(255),
  status VARCHAR(50), -- 'live', 'upcoming', 'completed'
  started_at TIMESTAMP,
  ended_at TIMESTAMP,
  last_page_token VARCHAR(255),
  last_message_id VARCHAR(255),
  created_at TIMESTAMP DEFAULT NOW()
);

-- OAuth credentials
CREATE TABLE youtube_credentials (
  id SERIAL PRIMARY KEY,
  channel_id VARCHAR(255) UNIQUE FOREIGN KEY,
  access_token TEXT ENCRYPTED,
  refresh_token TEXT ENCRYPTED,
  token_type VARCHAR(50),
  expires_at TIMESTAMP,
  scopes TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Message log (optional)
CREATE TABLE youtube_messages (
  id SERIAL PRIMARY KEY,
  channel_id VARCHAR(255),
  broadcast_id VARCHAR(255),
  message_id VARCHAR(255) UNIQUE,
  author_id VARCHAR(255),
  author_name VARCHAR(255),
  message_type VARCHAR(50), -- 'chat', 'super_chat', 'super_sticker', 'membership'
  text_content TEXT,
  super_chat_amount DECIMAL(10, 2),
  super_chat_currency VARCHAR(10),
  routed_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW()
);
```

## Error Handling Strategy

### Polling Error Categories

```
┌──────────────────────────────────────────┐
│ Polling Error Handling                   │
├──────────────────────────────────────────┤
│                                          │
│ Transient (auto-recover):               │
│   - Timeout: retry after delay          │
│   - 429 (rate limit): wait + retry     │
│   - 503 (service down): exponential bk  │
│   - Network error: auto-reconnect       │
│                                          │
│ Expected (not errors):                  │
│   - 403 (stream ended): reset & retry   │
│   - Empty chat: normal, keep polling    │
│   - No broadcast: expected, keep trying │
│                                          │
│ Critical (disable channel):             │
│   - 401 (auth failed): 10+ consecutive  │
│   - 400 (invalid): 10+ consecutive      │
│   - Other 4xx: 10+ consecutive          │
│                                          │
│ After 10+ errors:                       │
│   - Set error_count = 11+              │
│   - Log error_count                     │
│   - Remove from polling loop            │
│   - Keep in database (for manual review)│
│                                          │
└──────────────────────────────────────────┘
```

### Retry Strategy

```python
# Exponential backoff with jitter
base_delay = 1  # seconds
max_delay = 300  # 5 minutes

for attempt in range(1, max_retries + 1):
    try:
        # Attempt request
        response = await youtube_client.get_chat()
        return response
    except Exception as e:
        if should_retry(e):
            delay = min(base_delay ** attempt, max_delay)
            jitter = random.uniform(0, delay * 0.1)
            await asyncio.sleep(delay + jitter)
            continue
        else:
            raise
```

## Concurrency Model

### Async/Await Architecture

```python
# Main server (Quart ASGI)
- Handles HTTP requests concurrently
- Event loop processes I/O without blocking

# ChatPoller background task
- Single background task (cooperative)
- Polls all channels sequentially in loop
- Yields control with await sleep()
- Server remains responsive to requests

# Concurrent operations
- Polling + HTTP requests overlap
- HTTP request handling + polling overlap
- Database operations non-blocking (async)
```

**Concurrency Limits**:

- **HTTP Handlers**: ~100+ concurrent requests (ASGI workers)
- **Chat Polling**: ~1000+ channels per poller (sequential, async)
- **Database**: Connection pool of 10-30 concurrent connections
- **Redis**: No limit (cache provider)

## Performance Characteristics

### API Quota Usage

```
Single channel at 5s interval:
- 1 request per poll = 1 API unit
- 12 polls per minute = 12 units/minute
- 720 polls per hour = 720 units/hour
- 17,280 polls per day = 17,280 units/day
- Quota limit: 10,000 units/day
- Can monitor max 0.5 channels at 5s

Single channel at 10s interval:
- 1 request per poll = 1 API unit
- 6 polls per minute = 6 units/minute
- 360 polls per hour = 360 units/hour
- 8,640 polls per day = 8,640 units/day
- Can monitor 1 channel comfortably
- Can monitor 3-5 channels with margin

100 channels at 10s interval:
- 100 * 8,640 units/day = 864,000 units/day
- Exceeds quota by 86x
- Solution: Increase interval to 5-10 minutes
- Or purchase extended quota
```

### Memory Usage

```
Per channel:
- Channel metadata: ~500 bytes
- Last page token: ~200 bytes
- Error tracking: ~100 bytes
- Total per channel: ~800 bytes

100 channels:
- ~80 KB for channel data
- Message buffer (in-transit): ~10-50 KB
- Connection pools: ~5-10 MB
- Python overhead: ~50-100 MB
- Total: ~70-150 MB

Message throughput:
- High stream: 10-50 messages/second
- Each message: ~1-2 KB JSON
- Buffer limit: 1000 messages max
- Max memory for buffer: ~2 MB
```

### Latency Characteristics

```
Message capture to routing:
- Poll interval: 5-10 seconds (configurable)
- API response: 200-500ms
- Parsing: 10-50ms
- Database write: 10-20ms
- Router API call: 50-200ms
- Total latency: 300-1000ms per poll

Webhook latency (stream events):
- YouTube → Webhook: 100-500ms
- Parsing: 10-20ms
- Router API: 50-200ms
- Total: 200-700ms

User message visibility:
- Within 1-15 seconds (depends on poll interval)
- Typically 5-10 seconds
```

## Deployment Patterns

### Single Instance

```
┌─────────────────────────┐
│ YouTube Live Module     │
│ - Single Quart server   │
│ - Single ChatPoller     │
│ - PostgreSQL conn pool  │
│ - Redis cache           │
└─────────────────────────┘
        │
        ├─ Can handle 1000+ channels
        ├─ Scales to 10K messages/minute
        └─ Suitable for most deployments
```

### Multi-Instance (Load-Balanced)

```
┌──────────────────────────────────────┐
│ Load Balancer (upstream)             │
├──────────────────────────────────────┤
│                                      │
├─ Instance 1: youtube-live (port 8006)
├─ Instance 2: youtube-live (port 8006)
└─ Instance 3: youtube-live (port 8006)
        │
        └─ Shared Database + Redis
        └─ Distributed chat polling (channel-sharded)
```

**Challenge**: Each instance polls all channels (duplicates)

**Solution**: Implement channel sharding:

```python
# Instance 1: Poll channels 0-33
# Instance 2: Poll channels 34-66
# Instance 3: Poll channels 67-99

def should_poll_channel(channel_id, instance_id, total_instances):
    hash_value = hash(channel_id) % total_instances
    return hash_value == instance_id
```

## Monitoring & Observability

### Key Metrics

```
youtube_chat_messages_total{type}
  - Cumulative messages by type
  - Labels: type=chat|super_chat|super_sticker|membership

youtube_polling_errors_total{channel_id}
  - Cumulative errors by channel
  - Reset on successful poll

youtube_active_streams
  - Gauge: current active broadcast count
  - Updated real-time

youtube_polling_latency_seconds
  - Histogram: time per polling cycle
  - Buckets: 0.1, 0.5, 1.0, 5.0, 10.0 seconds

youtube_api_calls_total{method,status}
  - HTTP request metrics by method and status
  - Tracks quota usage

youtube_db_operations_total{operation,status}
  - Database transaction metrics
```

### Health Checks

```
/health endpoint:
- Database connectivity ✓
- Redis connectivity (if enabled) ✓
- YouTube API reachability ✓
- ChatPoller running ✓
- Router API reachability ✓
```

## Security Architecture

### Credential Management

```
┌─────────────────┐
│ OAuth 2.0 Token │
└────────┬────────┘
         │
  ┌──────▼──────────┐
  │ Encrypt with    │
  │ fernet.key      │
  └──────┬──────────┘
         │
  ┌──────▼──────────────┐
  │ Store in PostgreSQL │
  └──────┬──────────────┘
         │
  ┌──────▼──────────────┐
  │ Cache in Redis      │
  │ (TTL = token exp)   │
  └─────────────────────┘

On Each Request:
1. Check Redis cache
2. If expired → Check database (decrypt)
3. If near expiry → Refresh via OAuth
4. Update Redis
```

### Webhook Signature Verification

```python
# YouTube sends webhook with signature
# X-Hub-Signature header

import hmac
import hashlib

received_signature = request.headers['X-Hub-Signature']
payload = request.get_data()
calculated = 'sha1=' + hmac.new(
    SECRET_KEY.encode(),
    payload,
    hashlib.sha1
).hexdigest()

if calculated != received_signature:
    raise SecurityError("Invalid signature")
```

## Related Files

- `services/youtube_client.py` - HTTP client implementation
- `services/chat_poller.py` - Polling service implementation
- `services/webhook_handler.py` - Webhook handler implementation
- `routes/channels.py` - Channel management routes
- `models/schemas.py` - Data validation schemas
