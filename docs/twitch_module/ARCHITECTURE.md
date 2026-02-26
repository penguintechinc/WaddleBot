# Twitch Module Architecture

## System Overview

The Twitch Module is a real-time event receiver with dual-ingestion architecture: **TwitchIO IRC bot** for chat messages and **EventSub webhooks** for structured events. Both paths converge on the Router API for command processing and leaderboard tracking.

```
┌─────────────────────────────────────────────────────────────────┐
│                        Twitch Ecosystem                          │
└─────────────────────────────────────────────────────────────────┘
                    ↓ IRC Chat                  ↓ EventSub Events
                    ↓                           ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Twitch Module (Port 8002)                    │
│                                                                  │
│  ┌──────────────────────┐      ┌──────────────────────┐         │
│  │ TwitchBotService     │      │ EventSubHandler      │         │
│  │ (TwitchIO IRC Bot)   │      │ (Quart Webhooks)     │         │
│  │                      │      │                      │         │
│  │ - Join/leave channels│      │ - HMAC verification  │         │
│  │ - Read IRC messages  │      │ - Deduplication      │         │
│  │ - Broadcast responses│      │ - Event routing      │         │
│  │ - Message splitting  │      │ - Subscription mgmt  │         │
│  └──────────────────────┘      └──────────────────────┘         │
│            ↓                                    ↓                │
│            └────────────────┬───────────────────┘                │
│                             ↓                                   │
│                    ┌──────────────────┐                         │
│                    │ ChannelManager   │                         │
│                    │ - Load from DB   │                         │
│                    │ - Refresh (300s) │                         │
│                    │ - Track state    │                         │
│                    └──────────────────┘                         │
│                             ↓                                   │
│  ┌──────────────────────────────────────────────────────┐      │
│  │ TwitchCacheManager (Redis/In-Memory)                │      │
│  │ - Channels cache (TTL: 300s)                         │      │
│  │ - Community mappings (TTL: 3600s)                    │      │
│  │ - User entity cache (TTL: 1800s)                     │      │
│  │ - Message dedup IDs (Last 5000)                      │      │
│  └──────────────────────────────────────────────────────┘      │
│                             ↓                                   │
│  ┌──────────────────────────────────────────────────────┐      │
│  │ ViewerTracker (Chatters API Polling)                │      │
│  │ - Poll interval: 60s                                 │      │
│  │ - Detect join/leave/heartbeat                        │      │
│  │ - Activity retention: 3600s                          │      │
│  └──────────────────────────────────────────────────────┘      │
│                             ↓                                   │
│            ┌────────────────┬────────────────┐                  │
│            ↓                ↓                                   │
└────────────────────────────────────────────────────────────────┘
             ↓                 ↓                 ↓
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │ Router API   │  │  Hub API     │  │  Twitch API  │
    │ (Port 8001)  │  │  (Port 8000) │  │ (REST + IRC) │
    │              │  │              │  │              │
    │ - Commands   │  │ - Leaderboard│  │ - Chatters   │
    │ - Responses  │  │ - Viewer     │  │ - User info  │
    │ - Logging    │  │   presence   │  │ - Token auth │
    └──────────────┘  └──────────────┘  └──────────────┘
```

---

## Component Architecture

### 1. TwitchBotService (IRC Bot)

**Purpose**: Real-time IRC chat monitoring and message broadcasting.

**Responsibilities**:
- Maintain persistent connection to Twitch TMI (IRC endpoint)
- Join/leave channels dynamically
- Parse incoming chat messages
- Extract command, args, sender info, badges
- Enforce broadcaster-only command restrictions
- Split long responses (>500 chars) into multiple messages
- Broadcast responses back to channels
- Reconnect with exponential backoff on connection loss

**Key Methods**:
```python
async def start()              # Start IRC bot, connect to TMI
async def join_channel(ch_id)  # Join channel IRC room
async def leave_channel(ch_id) # Leave channel IRC room
async def send_message(ch_id, msg)  # Send message to channel
async def on_message(msg)      # Handle received IRC message
async def _split_message(msg)  # Split msg if >500 chars
```

**State Management**:
- `active_channels`: Set of currently-joined channels
- `pending_joins`: Queue of channels waiting to join
- `message_handlers`: Registered callbacks for different message types

---

### 2. EventSubHandler (Webhook Receiver)

**Purpose**: Receive and process Twitch EventSub webhooks.

**Responsibilities**:
- Expose HTTP endpoint for EventSub callbacks
- Verify HMAC-SHA256 signatures (security critical)
- Deduplicate messages via message_id tracking
- Route events to specialized handlers
- Manage EventSub subscription lifecycle

**Event Types Handled**:
- `channel.subscribe` - New subscription (tier 1, 2, 3)
- `channel.subscription.gift` - Gift subscription (bulk)
- `channel.raid` - Channel raid with viewer count
- `channel.follow` - New follower
- `channel.cheer` - Bits donation
- `stream.online` - Stream started
- `stream.offline` - Stream ended

**Key Methods**:
```python
async def webhook_handler(request)     # HTTP POST handler
def _verify_signature(msg, sig, secret)  # HMAC-SHA256 verification
async def _route_event(event_type, payload)  # Dispatch to handlers
async def _handle_subscribe(event)       # Process subscribe event
async def _handle_raid(event)            # Process raid event
```

**Deduplication**:
- Tracks last 5000 message IDs (configurable)
- Returns 409 Conflict if duplicate detected
- Prevents double-processing of webhook retries

---

### 3. ChannelManager

**Purpose**: Load and sync channel list from database; manage join/leave state.

**Responsibilities**:
- Load active channels from database periodically (300s default)
- Compare current state with database state
- Trigger joins for new channels
- Trigger leaves for removed channels
- Cache channel metadata (channel_id, name, community_id, is_live)
- Track join/leave timestamps

**Key Methods**:
```python
async def refresh_channels()    # Reload from DB, sync state
async def get_channels()         # Return current channel list
async def add_channel(ch_id)     # Trigger join
async def remove_channel(ch_id)  # Trigger leave
async def update_channel_status(ch_id, is_live)  # Update live status
```

**Sync Logic**:
```
DB Channels: [ch1, ch2, ch3, ch4]
Current:     [ch1, ch2, ch5]

New:   [ch3, ch4]       → JOIN
Gone:  [ch5]            → LEAVE
Same:  [ch1, ch2]       → NO CHANGE
```

---

### 4. ViewerTracker (Chatters API Polling)

**Purpose**: Poll Twitch Chatters API to detect viewer activity for leaderboards.

**Responsibilities**:
- Poll Chatters API every 60s (configurable)
- Compare current viewers with previous poll
- Detect join (new viewer), leave (absent viewer), heartbeat (continued presence)
- Send activity events to Hub API
- Cache viewer list per channel (TTL: 300s)

**Key Methods**:
```python
async def poll_chatters()        # Main polling loop
async def get_chatters(ch_id)    # Fetch viewers for channel
async def detect_activity()       # Compare old vs new viewers
async def send_to_hub_api()       # POST activity to hub
```

**Activity Detection**:
```
Previous: [user1, user2, user3]
Current:  [user2, user3, user4]

Join:     [user4]         → NEW
Leave:    [user1]         → GONE
Heartbeat:[user2, user3]  → STILL HERE
```

---

### 5. TwitchCacheManager (Distributed Cache)

**Purpose**: Cache frequently-accessed data to reduce API calls.

**Responsibilities**:
- Store channel list (TTL: 300s)
- Store community mappings (TTL: 3600s)
- Store user entity info (TTL: 1800s)
- Deduplicate EventSub message IDs (sliding window: last 5000)
- Implement fallback to API on cache miss

**Cache Types**:
- **Redis** (Production): Distributed, shared across instances
- **In-Memory** (Development): Local dictionary, per-instance

**Key Methods**:
```python
async def get(key, ttl)          # Get with TTL
async def set(key, value, ttl)   # Set with TTL
async def delete(key)             # Delete key
async def add_message_id(msg_id) # Track for dedup
async def has_message_id(msg_id) # Check dedup
```

---

## Data Flow Diagrams

### Chat Message Flow (IRC → Router)

```
1. User sends message in Twitch chat:
   "!ping"

2. TwitchBotService receives via IRC:
   IRCMessage {
     channel: "#example_channel",
     user: "user123",
     message: "!ping",
     badges: ["broadcaster"]
   }

3. Parse message:
   command: "ping"
   args: []
   sender_id: "user123"
   is_broadcaster: false

4. Router check:
   → Send to Router API

5. Router processes:
   POST /api/v1/messages → {
     channel_id: "12345",
     user_id: "user123",
     command: "ping",
     args: []
   }

6. Router returns response:
   "pong! Latency: 45ms"

7. Message split (if >500 chars):
   ["pong! Latency: 45ms"]

8. Send to chat:
   POST /api/v1/bot/send → {
     channel_id: "12345",
     message: "pong! Latency: 45ms"
   }

9. IRC sends to Twitch:
   PRIVMSG #example_channel :pong! Latency: 45ms
```

### EventSub Event Flow (Webhook → Hub)

```
1. Twitch sends webhook:
   POST /eventsub/webhook {
     subscription.type: "channel.subscribe"
     event: {
       broadcaster_id: "12345",
       user_id: "67890",
       user_login: "new_sub"
     }
   }

2. EventSubHandler receives:
   - Verify HMAC-SHA256 signature
   - Check for duplicate message_id
   - Route to event handler

3. Handle subscribe event:
   - Generate announcement: "@new_sub Welcome!"
   - Post to Router API (if announcement cmd exists)

4. Update leaderboard:
   POST /api/v1/leaderboards/{channel_id} {
     event: "subscribe",
     user_id: "67890",
     tier: "1000"
   }

5. Cache update:
   - Store subscriber info
   - Update channel metadata
```

### Viewer Tracking Flow (Chatters → Hub)

```
1. ViewerTracker polls (every 60s):
   GET https://api.twitch.tv/helix/chat/chatters
   → [user1, user2, user3, ... userN]

2. Compare with cache:
   Previous: [user1, user2, user3]
   Current:  [user2, user3, user4]

3. Detect activity:
   Join:     [user4]
   Leave:    [user1]
   Heartbeat:[user2, user3]

4. Send to Hub API:
   POST /api/v1/leaderboards/{channel_id} {
     viewers: [
       { user_id: "u4", event: "join" },
       { user_id: "u1", event: "leave" },
       { user_id: "u2", event: "heartbeat" },
       { user_id: "u3", event: "heartbeat" }
     ]
   }

5. Cache update:
   Cache[channel_id] = [user2, user3, user4]
```

---

## API Integration Points

### Router API (`ROUTER_API_URL`)

**Message Ingestion**:
```
POST /api/v1/messages {
  channel_id: "12345",
  user_id: "user123",
  message: "!ping",
  badges: { broadcaster: true }
}
→ Response: { response: "pong! Latency: 45ms" }
```

**Service Role**: Twitch Module → Router (message → response)

---

### Hub API (`HUB_API_URL`)

**Leaderboard Updates**:
```
POST /api/v1/leaderboards/{channel_id} {
  viewers: [
    { user_id: "u1", event: "join", timestamp: "..." },
    { user_id: "u2", event: "heartbeat", timestamp: "..." }
  ]
}
```

**Service Role**: Twitch Module → Hub (viewer activity)

---

### Twitch API

**User/Channel Info**:
```
GET /helix/users?login=channel_name
→ { id, display_name, profile_image_url }

GET /helix/channels?broadcaster_id=12345
→ { broadcaster_id, game_name, title, is_live }

GET /helix/chat/chatters?broadcaster_id=12345
→ [ { user_id, user_login, user_name }, ... ]
```

**Service Role**: Twitch Module → Twitch (read-only API calls)

---

## Error Handling & Resilience

### Retry Logic

**HTTP Requests** (to Router, Hub, Twitch):
```python
max_retries = 3
base_delay = 1.0
backoff_multiplier = 1.5

Attempt 1: delay 1.0s
Attempt 2: delay 1.5s  (1.0 * 1.5)
Attempt 3: delay 2.25s (1.5 * 1.5)
Attempt 4: FAIL
```

**IRC Connection**:
```python
max_reconnect_attempts = 5
base_interval = 5s

Attempt 1: wait 5s
Attempt 2: wait 10s  (5 * 2)
Attempt 3: wait 20s  (10 * 2)
Attempt 4: wait 40s  (20 * 2)
Attempt 5: wait 80s  (40 * 2)
After 5: backoff to 120s, then constant
```

### Circuit Breaker Pattern

```python
# Twitch API circuit breaker
if error_count > threshold (5):
    state = "open"
    wait 60s before retry

if error_count drops below threshold:
    state = "half-open"
    try limited requests

if requests succeed:
    state = "closed"
    resume normal operation
```

### Graceful Degradation

- **Cache miss** → Fallback to API call
- **Twitch API timeout** → Use cached data, retry later
- **EventSub unavailable** → Continue with IRC only
- **Viewer tracking poll fails** → Retry on next cycle
- **Database unavailable** → Fail startup with clear error

---

## Performance Characteristics

### Latency

| Operation | Latency | Notes |
|-----------|---------|-------|
| IRC message → Router | ~50-100ms | Network + processing |
| EventSub webhook → Hub | ~20-50ms | Webhook validation + routing |
| Viewer poll | ~500ms-1s | Chatters API call |
| Cache hit | <1ms | In-memory lookup |
| Cache miss + fallback | ~100-200ms | API call required |

### Throughput

| Operation | Throughput | Bottleneck |
|-----------|-----------|-----------|
| Messages | ~500 msgs/sec | Network I/O |
| EventSub events | ~100 events/sec | Twitch API rate limit |
| Viewer polls | 1 poll/60s per channel | Intentional (60s interval) |
| API responses | 50+ req/sec | HTTP server (Quart) |

### Scalability

**Vertical**:
- Increase `DB_POOL_SIZE` for more concurrent DB connections
- Increase `VIEWER_POLL_INTERVAL` (lower = more frequent polls)
- Use Redis for distributed cache

**Horizontal**:
- Multiple instances share Redis cache
- EventSub webhooks distributed via load balancer
- Each instance monitors independent set of channels (via database)

---

## Security Considerations

### HMAC-SHA256 Verification

All EventSub webhooks verified:
```python
expected_sig = sha256(
    msg_id + timestamp + body,
    secret
)
actual_sig = request.headers['Twitch-Eventsub-Signature']
if expected_sig != actual_sig:
    return 403 Forbidden
```

### Token Management

- **Access tokens**: Stored in environment, never logged
- **API keys**: Service API key for internal endpoints only
- **Database credentials**: In environment, encrypted at rest
- **Redis password**: Optional, in environment

### Rate Limiting

- Twitch IRC: ~20 msgs/30s per channel (enforced by Twitch)
- Twitch API: 120 req/min (Helix)
- EventSub: Unlimited (but Twitch enforces 10k subscriptions/app)

---

## Monitoring & Observability

### Metrics (Prometheus)

```
twitch_messages_total{source="irc"}
twitch_events_total{type="subscribe|raid|follow"}
twitch_errors_total{type="auth|api|network"}
twitch_latency_ms{operation="send|poll"}
twitch_channels_active
twitch_viewers_tracked
twitch_cache_hits_total
twitch_cache_misses_total
```

### Logging

```json
{
  "timestamp": "2025-02-24T10:30:00Z",
  "level": "info",
  "component": "TwitchBotService",
  "event": "channel_joined",
  "channel_id": "12345",
  "channel_name": "example_channel",
  "duration_ms": 1234
}
```

### Health Checks

- **Liveness** (`/health`): Bot connected, HTTP server running
- **Readiness** (`/health?type=ready`): All dependencies available (DB, cache, Twitch)

---

## Testing Strategy

### Unit Tests

- Message parsing (commands, args, badges)
- Message splitting logic
- HMAC verification
- Cache get/set operations
- Deduplication logic

### Integration Tests

- IRC bot connection/disconnection
- EventSub webhook handling
- Database channel sync
- Router API communication
- Hub API communication

### E2E Tests

- Full message flow: IRC → Router → Response
- Full webhook flow: EventSub → Handler → Hub
- Full viewer tracking: Chatters poll → Hub update
- Multi-channel scenarios
- Error recovery scenarios

---

## Deployment Topology

### Single Instance

```
┌─────────────────────────────────┐
│   Twitch Module (Port 8002)     │
│   - TwitchBotService            │
│   - EventSubHandler             │
│   - ViewerTracker               │
│   - In-memory cache             │
└──────────────┬──────────────────┘
               │
        ┌──────┴──────────────────────┐
        ↓                             ↓
   PostgreSQL              Twitch API
```

### Distributed (Production)

```
┌─────────────────────────────────┐
│  ALB (Internal Load Balancer)   │
└──────────────┬──────────────────┘
      ↓        ↓        ↓
┌──────┐  ┌──────┐  ┌──────┐
│ TM-1 │  │ TM-2 │  │ TM-3 │  (Twitch Module instances)
└──┬───┘  └──┬───┘  └──┬───┘
   │         │         │
   └─────────┴────┬────┘
            ┌─────┴──────────────┐
            ↓                    ↓
         Redis            PostgreSQL
```
