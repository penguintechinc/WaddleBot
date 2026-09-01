# Kick Module Architecture

## System Design

The Kick Module operates as an async event receiver and transformer, handling both synchronous webhook delivery and asynchronous real-time chat via WebSocket. The dual-mode architecture ensures maximum event coverage while maintaining low latency.

```
┌─────────────────────────────────────────────────────────────────┐
│                        Kick Platform                              │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Webhooks (HTTP POST)      Pusher (WebSocket)            │   │
│  │  stream_start              chatrooms.{id}.v2              │   │
│  │  stream_end                ├─ ChatMessage                 │   │
│  │  chat_message              ├─ Subscription                │   │
│  │  subscription              ├─ GiftedSubscription          │   │
│  │  raid                      ├─ UserBanned                  │   │
│  │  ...                       └─ MessageDeleted              │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────┬────────────────────────────────────────┬────────────────┘
         │                                        │
         v                                        v
    ┌─────────────┐                       ┌──────────────────┐
    │   Quart     │                       │ KickChatClient   │
    │  App Server │                       │  (Pusher)        │
    └──────┬──────┘                       └────────┬─────────┘
           │                                       │
           v                                       v
    ┌─────────────────────────────────────────────────────┐
    │                 Event Handlers                       │
    │  ├─ Webhook validation (HMAC-SHA256)                 │
    │  ├─ Signature verification                          │
    │  ├─ Event parsing and validation                    │
    │  └─ Duplicate detection                             │
    └────────────────┬────────────────────────────────────┘
                     │
                     v
    ┌─────────────────────────────────────────────────────┐
    │            Event Normalization                       │
    │  ├─ Platform standardization (kick → waddles)        │
    │  ├─ User context enrichment (Core API)              │
    │  ├─ Badge/metadata mapping                          │
    │  └─ Event type translation                          │
    └────────────────┬────────────────────────────────────┘
                     │
                     v
    ┌─────────────────────────────────────────────────────┐
    │                Router API Integration                │
    │  POST /api/v1/events                                 │
    │  ├─ Async forwarding                                 │
    │  ├─ Retry with backoff                              │
    │  └─ Batch optimization                              │
    └────────────────┬────────────────────────────────────┘
                     │
                     v
    ┌─────────────────────────────────────────────────────┐
    │          WaddleBot Command Processing                │
    │  ├─ Event-specific handlers                          │
    │  ├─ Command execution                               │
    │  └─ Result logging                                   │
    └─────────────────────────────────────────────────────┘
```

## Component Architecture

### Quart Application Layer

**File**: `src/index.js` (originally Flask, refactored to Quart)

Responsibilities:
- HTTP server lifecycle (startup, shutdown)
- Route registration and middleware
- Request/response handling
- Error handling and logging

**Key Routes:**

```
POST /webhook/kick          # Webhook receiver
GET  /api/v1/status        # Health/status endpoint
GET  /health               # Liveness check
GET  /metrics              # Prometheus metrics
```

**Middleware Stack:**

```python
@app.before_request
async def validate_request():
    # Rate limiting, request logging, security headers

@app.errorhandler(Exception)
async def handle_errors(error):
    # Global exception handling with structured logging

@app.after_request
async def add_headers(response):
    # Security headers, CORS, timing information
```

### Webhook Handler

**File**: `src/handlers/webhook.py`

Responsibilities:
- Parse incoming webhook JSON
- Verify HMAC-SHA256 signature
- Detect and reject duplicates
- Queue event for processing
- Return 202 Accepted immediately

**Processing Pipeline:**

```
Input: Raw webhook request
  ↓
[Parse JSON] → 400 if malformed
  ↓
[Extract X-Signature header] → 401 if missing
  ↓
[Compute HMAC-SHA256] → 401 if mismatch
  ↓
[Check duplicate cache] → 202 if duplicate
  ↓
[Queue for processing]
  ↓
Output: 202 Accepted response (processing continues async)
```

**Signature Verification Algorithm:**

```python
import hmac
import hashlib

def verify_signature(payload_bytes, signature_header, secret):
    """
    Verify HMAC-SHA256 signature from Kick platform.

    Args:
        payload_bytes: Raw request body (bytes)
        signature_header: X-Signature header value (sha256=...)
        secret: KICK_WEBHOOK_SECRET

    Returns:
        bool: True if signature valid
    """
    expected = 'sha256=' + hmac.new(
        secret.encode(),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(signature_header, expected)
```

### KickAPI Service

**File**: `src/services/kick_api.py`

REST client for Kick API v2 interactions.

**Methods:**

```python
class KickAPI:
    async def get_channel(self, channel_id: int) -> dict
        """Fetch channel info (name, verified status, follower count)"""

    async def get_livestream(self, channel_id: int) -> dict
        """Get active livestream data (viewers, title, game)"""

    async def get_chatroom_info(self, chatroom_id: int) -> dict
        """Fetch chatroom metadata (emotes, rules, state)"""

    async def send_chat_message(
        self,
        chatroom_id: int,
        message: str,
        token: str
    ) -> dict
        """Send message as authenticated user"""
```

**Implementation Details:**

```python
# HTTP client pooling
connector = aiohttp.TCPConnector(
    limit=20,              # Total connections
    limit_per_host=10,     # Per Kick API host
    ttl_dns_cache=300      # 5-minute DNS cache
)
session = aiohttp.ClientSession(connector=connector)

# Request/response patterns
Base URL: https://api.kick.com/v2/
Headers: Authorization: Bearer {token}
Timeout: 10s
Retries: 3 with exponential backoff
```

**Error Handling:**

```python
# Graceful degradation for API failures
try:
    channel_data = await kick_api.get_channel(channel_id)
except aiohttp.ClientError:
    # Log error, use cached data if available
    channel_data = cache.get(f'channel:{channel_id}') or {}

# Rate limiting
if response.status == 429:
    retry_after = int(response.headers.get('Retry-After', 60))
    await asyncio.sleep(retry_after)
```

### KickChatClient Service

**File**: `src/services/kick_chat_client.py`

Pusher-based WebSocket client for real-time chat.

**Architecture:**

```python
class KickChatClient:
    def __init__(self, pusher_key, cluster, redis_url):
        self.pusher = pysher.Pusher(
            app_id='pusher_app_id',
            key=pusher_key,           # eb1d5f283081a78b932c
            cluster=cluster,           # us2
            ssl=True
        )
        self.channels = {}            # {channel_id: handler}
        self.redis = aioredis.from_url(redis_url)

    async def subscribe_channel(self, channel_id: int, chatroom_id: int):
        """Subscribe to chatroom WebSocket channel"""

    async def handle_message(self, event_name: str, data: dict):
        """Process incoming Pusher events"""

    async def unsubscribe_channel(self, channel_id: int):
        """Graceful disconnect"""
```

**Event Subscription Pattern:**

```
Kick Platform            KickChatClient          WaddleBot
      │                       │                       │
      │  Subscribe request    │                       │
      │──────────────────────>│                       │
      │                       │                       │
      │  WebSocket handshake  │                       │
      │<──────────────────────>                       │
      │                       │                       │
      │  ChatMessage event    │  Event normalization  │
      │──────────────────────>│──────────────────────>
      │                       │  Forward to Router    │
      │                       │                       │
      │  Subscription event   │  (repeat for each)    │
      │──────────────────────>│──────────────────────>
      │                       │                       │
      │  [Connection stable]  │  [Heartbeat every 3s] │
      │<──────────────────────>                       │
      │                       │                       │
      │  [Network error]      │                       │
      │  [Reconnect attempt] │                       │
      │──────────────────────>│  [Exponential backoff]│
```

**Pusher Event Handling:**

```python
async def handle_message(self, event_name: str, data: dict):
    """
    Process events from Pusher channel.

    Event names from chatrooms.{id}.v2:
    - ChatMessage: User sent message
    - Subscription: New subscription
    - GiftedSubscription: Gift subscription
    - UserBanned: User banned
    - MessageDeleted: Message removed by mods
    """

    handlers = {
        'ChatMessage': self.handle_chat_message,
        'Subscription': self.handle_subscription,
        'GiftedSubscription': self.handle_gift,
        'UserBanned': self.handle_ban,
        'MessageDeleted': self.handle_message_delete,
    }

    handler = handlers.get(event_name)
    if handler:
        await handler(data)
```

**Reconnection Logic:**

```python
async def reconnect_with_backoff(self, attempt: int = 0):
    """Exponential backoff: 1s, 2s, 4s, 8s, 16s, 30s (max)"""
    max_delay = 30
    delay = min(2 ** attempt, max_delay)

    logger.warning(f"Reconnecting in {delay}s (attempt {attempt})")
    await asyncio.sleep(delay)

    try:
        await self.subscribe_channel(self.channel_id, self.chatroom_id)
    except Exception as e:
        logger.error(f"Reconnection failed: {e}")
        await self.reconnect_with_backoff(attempt + 1)
```

### Event Normalization Layer

**File**: `src/models/events.py`

Dataclass definitions for type-safe event handling:

```python
@dataclass
class KickSender:
    """User who triggered event"""
    id: str
    username: str
    display_name: str
    avatar_url: str
    badges: List[str]  # ['moderator', 'subscriber', etc]
    is_verified: bool

@dataclass
class ChatMessageEvent:
    """Chat message event"""
    platform: str = 'kick'
    event_type: str = 'chat'
    channel_id: str
    sender: KickSender
    message: str
    message_id: str
    timestamp: str
    is_reply: bool = False
    reply_to_user: Optional[str] = None
    emotes: List[str] = field(default_factory=list)

@dataclass
class SubscriptionEvent:
    """Channel subscription"""
    platform: str = 'kick'
    event_type: str = 'subscription'
    channel_id: str
    subscriber: KickSender
    tier: str  # '1', '2', '3'
    months: int
    message: Optional[str] = None
    is_gift: bool = False
```

### Router Integration

**File**: `src/handlers/router.py`

Async event forwarding to WaddleBot Router.

**Integration Pattern:**

```python
async def forward_event(event: NormalizedEvent):
    """
    Send normalized event to Router API.

    Implements:
    - Async non-blocking dispatch
    - Retry with exponential backoff
    - Batch optimization (collect events, send in groups)
    - Failure logging without re-signaling client
    """

    # Batching optimization
    batch = [event]

    # Wait for more events (up to 50ms)
    async def collect_events():
        for _ in range(50):  # 50ms
            try:
                event = queue.get_nowait()
                batch.append(event)
            except asyncio.QueueEmpty:
                break
            await asyncio.sleep(0.001)  # 1ms check interval

    await collect_events()

    # Send batch to Router
    async with aiohttp.ClientSession() as session:
        await session.post(
            f'{ROUTER_API_URL}/api/v1/events',
            json={'events': [e.to_dict() for e in batch]},
            timeout=aiohttp.ClientTimeout(total=10)
        )
```

## Data Flow Diagrams

### Webhook Event Flow

```
Client (Kick Platform)
    │
    ├─ POST /webhook/kick
    │ ├─ Headers: X-Signature: sha256=...
    │ └─ Body: {"event": "chat_message", "data": {...}}
    │
    v
Quart Handler
    │
    ├─ Receive request
    ├─ Extract raw body (bytes)
    ├─ Parse JSON
    │
    v
Signature Verification
    │
    ├─ Extract X-Signature header
    ├─ Compute HMAC-SHA256(body, SECRET)
    ├─ Compare signatures (constant-time)
    │
    ├─ MISMATCH? → Return 401 Unauthorized
    │ └─ Log security event
    │
    └─ MATCH? → Continue

    v
Duplicate Detection
    │
    ├─ Check Redis: exists(event_id)?
    ├─ DUPLICATE? → Return 202 Accepted (no reprocessing)
    │ └─ Log duplicate
    │
    └─ NEW? → Continue

    v
Event Normalization
    │
    ├─ Parse event type
    ├─ Extract event data
    ├─ Fetch user context (Core API)
    ├─ Map to NormalizedEvent dataclass
    │
    v
Queue for Processing
    │
    ├─ Add to async queue
    ├─ Return 202 Accepted immediately
    │
    v
Background Task
    │
    ├─ Retrieve from queue
    ├─ Batch with other events
    ├─ POST to ROUTER_API_URL/api/v1/events
    ├─ Retry on failure (backoff)
    ├─ Log results (no client re-signal)
```

### Chat Event Flow (WebSocket)

```
Kick Platform (Pusher)
    │
    └─ chatrooms.{id}.v2 channel
       │
       ├─ ChatMessage event → {type: "message", data: {...}}
       ├─ Subscription event → {type: "subscription", data: {...}}
       └─ [Other events]

    v
KickChatClient
    │
    ├─ Subscribe to channel (one per chatroom)
    ├─ Receive Pusher message
    │
    v
Event Handler (handle_message)
    │
    ├─ Extract event type from message
    ├─ Route to appropriate handler
    │  ├─ ChatMessage → handle_chat_message()
    │  ├─ Subscription → handle_subscription()
    │  ├─ GiftedSubscription → handle_gift()
    │  └─ [etc]
    │
    v
Handler Logic (e.g., handle_chat_message)
    │
    ├─ Parse message data
    ├─ Extract user info
    ├─ Fetch badges from Core API (if needed)
    ├─ Create ChatMessageEvent dataclass
    │
    v
Queue for Processing
    │
    ├─ Add normalized event to async queue
    │
    v
Background Task (same as webhook)
    │
    └─ Batch and forward to Router
```

## Error Handling Strategy

### Graceful Degradation

1. **API Failures**: Use cached data or continue with minimal context
2. **Router Unavailable**: Queue events locally (via Redis), retry later
3. **WebSocket Disconnect**: Auto-reconnect with exponential backoff
4. **Database Error**: Log and continue (don't block event processing)

### Retry Policies

| Component | Retries | Backoff | Max Delay |
|-----------|---------|---------|-----------|
| HMAC Verification | 0 | N/A | N/A |
| Router API | 3 | exponential | 30s |
| WebSocket reconnect | ∞ | exponential | 30s |
| Database query | 2 | linear | 5s |
| Core API call | 2 | exponential | 10s |

### Monitoring & Observability

**Metrics:**

```
kick_webhook_received_total          # All webhooks
kick_webhook_rejected_total          # Bad sig/format
kick_event_processed_total{type}     # By type
kick_router_api_latency_ms           # Processing time
kick_websocket_connections_active    # Active chats
kick_websocket_reconnect_total       # Reconnections
```

**Structured Logging:**

```json
{
  "timestamp": "2026-02-24T12:34:56.789Z",
  "level": "INFO",
  "event": "chat_message_processed",
  "channel_id": "12345",
  "user_id": "54321",
  "router_latency_ms": 145,
  "message_length": 42,
  "badges": ["subscriber", "moderator"]
}
```

## Performance Characteristics

### Throughput

- **Webhook processing**: &lt;50ms per event (excluding Router latency)
- **WebSocket handling**: &lt;100ms per event
- **Router forwarding**: 200-500ms (depends on Router capacity)
- **Batching**: Up to 100 events/batch, 50ms collection window

### Concurrency

- **WebSocket connections**: 1 per chatroom (lightweight)
- **HTTP connections**: Pool of 20 (configurable)
- **Database connections**: Pool of 10-20 (configurable)
- **Async tasks**: Unlimited (Quart/asyncio managed)

### Memory Usage

- Base: ~100 MB
- Per WebSocket: ~2 MB
- Per event (cached): ~1 KB
- Long-term: Stable (no memory leaks with proper cleanup)

### Latency SLA

- Webhook to Router: &lt;500ms (p99)
- WebSocket to Router: &lt;300ms (p99)
- Health check response: &lt;10ms
- Metrics generation: &lt;50ms

## See Also

- [API Documentation](API.md)
- [Configuration Guide](CONFIGURATION.md)
- [Usage Guide](USAGE.md)
- [Troubleshooting Guide](TROUBLESHOOTING.md)
