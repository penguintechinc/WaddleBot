# Twitch Action Module - Architecture

## System Design

The Twitch Action Module implements a multi-protocol architecture supporting IRC chat, Twitch Helix API, and OAuth token management:

### Core Components

```
┌─────────────────────────────────────────────────────┐
│           Twitch Action Module (Container)           │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌─────────────────────────────────────────────┐  │
│  │ gRPC Server (Port 50053)                    │  │
│  │ ─ Receives ExecuteAction gRPC messages     │  │
│  │ ─ Parses task payloads                     │  │
│  │ ─ Routes to TwitchService.execute()        │  │
│  │ ─ Supports batch action requests           │  │
│  └──────────────┬──────────────────────────────┘  │
│                 │                                  │
│                 ▼                                  │
│  ┌─────────────────────────────────────────────┐  │
│  │ REST API Server (Port 8072)                 │  │
│  │ ─ POST /api/v1/actions/execute (single)   │  │
│  │ ─ POST /api/v1/actions/batch (multiple)   │  │
│  │ ─ POST /api/v1/tokens/store               │  │
│  │ ─ POST /api/v1/tokens/revoke              │  │
│  │ ─ GET /api/v1/stats                       │  │
│  └──────────────┬──────────────────────────────┘  │
│                 │                                  │
│                 ▼                                  │
│  ┌─────────────────────────────────────────────┐  │
│  │ TwitchService (Business Logic)              │  │
│  │ ─ execute_action()                          │  │
│  │ ─ send_chat_message()                       │  │
│  │ ─ create_clip()                             │  │
│  │ ─ moderate_chat()                           │  │
│  └──────────────┬──────────────────────────────┘  │
│                 │                                  │
│        ┌────────┼──────────┬─────────┐            │
│        ▼        ▼          ▼         ▼            │
│  ┌──────────┐ ┌─────────┐ ┌──────┐ ┌────────┐   │
│  │ IRC      │ │ Helix   │ │Token │ │PyDAL  │   │
│  │ Client   │ │ API     │ │Mgr   │ │ DB    │   │
│  │          │ │ Client  │ │      │ │       │   │
│  │ Chat     │ │ Clips   │ │Refresh│ │Action│   │
│  │ Protocol │ │ Moderate│ │Store │ │History│   │
│  └──────────┘ └─────────┘ └──────┘ └────────┘   │
└─────────────────────────────────────────────────┘
         │              │          │         │
         │              │          │         ▼
         │              │          │    ┌──────────┐
         │              │          │    │Postgres  │
         │              │          │    │ DB       │
         │              │          │    │          │
         │              │          │    │action_   │
         │              │          │    │history   │
         │              │          │    │tokens    │
         │              │          │    └──────────┘
         │              │          │
         ▼              ▼          ▼
    ┌─────────────┐ ┌──────────┐ ┌──────────────┐
    │ IRC         │ │ Twitch   │ │ Twitch       │
    │ Network     │ │ Helix    │ │ Auth         │
    │             │ │ API      │ │ api.twitch   │
    │irc.chat.    │ │api.twitch│ │.tv/          │
    │twitch.tv    │ │.tv/helix │ │oauth2        │
    │:6667        │ └──────────┘ └──────────────┘
    └─────────────┘
```

## Data Flow

### Chat Message Send Flow

```
1. Client Request
   ├─ POST /api/v1/actions/execute
   ├─ Bearer {JWT_TOKEN}
   └─ JSON: {action_type, broadcaster_id, parameters}
        │
        ▼
2. REST API Handler
   ├─ Extract JWT token from header
   ├─ Verify signature with MODULE_SECRET_KEY
   ├─ Check token expiration
   └─ Validate action_type and broadcaster_id
        │
        ▼
3. TwitchService.execute_action()
   ├─ Get broadcaster's OAuth token from database
   ├─ Check if token expired
   │  ├─ If yes: Refresh via Twitch API
   │  └─ If refreshed: Update database
   ├─ Parse action parameters
   └─ Route to specific action handler
        │
        ▼
4. TwitchService.send_chat_message()
   ├─ Get IRC connection for broadcaster
   ├─ If no connection: Create new
   │  ├─ Connect to irc.chat.twitch.tv:6667
   │  ├─ Authenticate: PASS oauth:{token}
   │  ├─ Send NICK waddlebot
   │  └─ JOIN #{broadcaster_channel}
   ├─ Send PRIVMSG to channel
   └─ Handle IRC response
        │
        ▼
5. Database Recording
   ├─ Record action in action_history table
   ├─ Store: action_type, success, error, parameters
   └─ Timestamp creation time
        │
        ▼
6. Response to Client
   ├─ HTTP 200 with success=true
   ├─ Include message_id and timestamp
   └─ Optional error details if failed
```

### OAuth Token Lifecycle

```
1. Initial OAuth Flow
   ├─ User grants permission to app
   ├─ Module receives authorization code
   ├─ Exchange code for access_token + refresh_token
   └─ Store both tokens in database
        │
        ▼
2. Token Usage
   ├─ On each action, check token expiration
   ├─ If expires_at - now < TOKEN_REFRESH_BUFFER (300s)
   │  ├─ Refresh token via Twitch API
   │  ├─ Get new access_token + refresh_token
   │  └─ Update database with new tokens
   └─ Use token for action (chat, clips, etc.)
        │
        ▼
3. Token Refresh
   ├─ Call POST https://id.twitch.tv/oauth2/token
   ├─ Body: grant_type=refresh_token, refresh_token=...
   ├─ Twitch returns: new access_token, new refresh_token
   ├─ Update TokenManager cache
   └─ Continue with action
        │
        ▼
4. Token Revocation
   ├─ Admin calls POST /api/v1/tokens/revoke
   ├─ Delete token from database
   ├─ Close IRC connection if exists
   ├─ Revoke with Twitch API
   └─ Return success
```

### IRC Connection Lifecycle

```
1. Connection Pool
   ├─ One IRC connection per broadcaster
   ├─ Connection created on demand
   ├─ Cached in memory for reuse
   └─ Auto-close after inactivity

2. Connection Establishment
   ├─ Resolve irc.chat.twitch.tv → IP
   ├─ Create TCP socket (TLS)
   ├─ Send: CAP REQ :twitch.tv/tags twitch.tv/commands
   ├─ Send: PASS oauth:{access_token}
   ├─ Send: NICK {bot_username}
   ├─ Receive: :tmi.twitch.tv NOTICE
   └─ JOIN #{broadcaster_channel}

3. Message Sending
   ├─ Queue outgoing message
   ├─ Send PRIVMSG #{channel} :{message}
   ├─ Twitch acknowledges in chat
   ├─ Log message_id from response
   └─ Return success to client

4. Connection Closure
   ├─ On token revocation
   ├─ On long inactivity (configurable)
   ├─ On stream end (if configured)
   └─ Send PART #{channel}
      Send QUIT

5. Error Handling
   ├─ On connection error: Reconnect with exponential backoff
   ├─ On auth error: Refresh token and retry
   ├─ On rate limit: Queue and retry after delay
   └─ After 3 failures: Mark broadcaster as failed
```

## Protocol Specifications

### IRC Protocol

**Connection:**
```
Host: irc.chat.twitch.tv
Port: 6667 (TLS)
Username: WaddleBot (or any name)
```

**Authentication:**
```
CAP REQ :twitch.tv/tags twitch.tv/commands
PASS oauth:ACCESS_TOKEN
NICK waddlebot
JOIN #channel_name
```

**Sending Message:**
```
PRIVMSG #channel_name :This is a message
```

**Message Format:**
```
@msg-id=abc123;tmi-sent-ts=1234567890 :waddlebot!waddlebot@waddlebot.tmi.twitch.tv PRIVMSG #channel :message text
```

### Twitch Helix API

**Base URL:**
```
https://api.twitch.tv/helix
```

**Authentication Header:**
```
Authorization: Bearer {access_token}
Client-ID: {client_id}
```

**Clip Creation Endpoint:**
```
POST /clips
Headers:
  Authorization: Bearer {access_token}
  Client-ID: {client_id}

Body:
{
  "broadcaster_id": "123456789",
  "title": "Epic Moment",
  "has_delay": false
}

Response:
{
  "data": [
    {
      "id": "clip_123456",
      "url": "https://clips.twitch.tv/...",
      "edit_url": "https://clips.twitch.tv/.../edit"
    }
  ]
}
```

## Database Schema

### twitch_action_tokens Table

```sql
CREATE TABLE twitch_action_tokens (
  id INT PRIMARY KEY AUTO_INCREMENT,
  broadcaster_id VARCHAR(50) NOT NULL UNIQUE,
  broadcaster_login VARCHAR(100),
  access_token VARCHAR(1000) NOT NULL,
  refresh_token VARCHAR(1000) NOT NULL,
  expires_at TIMESTAMP NOT NULL,
  token_type VARCHAR(50),
  scopes JSON,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  last_used_at TIMESTAMP,
  failed_attempts INT DEFAULT 0,
  is_active BOOLEAN DEFAULT TRUE,
  INDEX idx_broadcaster_id (broadcaster_id),
  INDEX idx_expires_at (expires_at)
);
```

### action_history Table

```sql
CREATE TABLE action_history (
  id INT PRIMARY KEY AUTO_INCREMENT,
  broadcaster_id VARCHAR(50) NOT NULL,
  action_type VARCHAR(50) NOT NULL,
  request_id VARCHAR(100),
  success BOOLEAN NOT NULL DEFAULT FALSE,
  error VARCHAR(255),
  parameters JSON,
  response_data JSON,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  duration_ms INT,
  INDEX idx_broadcaster_id (broadcaster_id),
  INDEX idx_action_type (action_type),
  INDEX idx_created_at (created_at)
);
```

## Token Manager Implementation

### Token Refresh Strategy

```python
class TokenManager:
    def get_valid_token(self, broadcaster_id):
        """Get valid token, refreshing if needed"""
        token = self.db.get_token(broadcaster_id)

        # Check if refresh needed
        time_until_expiry = token.expires_at - now()
        if time_until_expiry < TOKEN_REFRESH_BUFFER:  # 300s
            # Token expiring soon, refresh now
            token = self.refresh_token(broadcaster_id)

        return token

    def refresh_token(self, broadcaster_id):
        """Refresh OAuth token"""
        old_token = self.db.get_token(broadcaster_id)

        # Call Twitch OAuth endpoint
        response = requests.post(
            "https://id.twitch.tv/oauth2/token",
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "refresh_token",
                "refresh_token": old_token.refresh_token
            }
        )

        # Update token in database
        new_token = response.json()
        self.db.update_token(broadcaster_id, {
            "access_token": new_token["access_token"],
            "refresh_token": new_token["refresh_token"],
            "expires_at": now() + timedelta(seconds=new_token["expires_in"])
        })

        return new_token
```

## EventSub Webhook Signature Verification

For future EventSub support:

```python
def verify_eventsub_signature(request):
    """Verify Twitch EventSub webhook signature"""
    message_id = request.headers.get("Twitch-Eventsub-Message-Id")
    timestamp = request.headers.get("Twitch-Eventsub-Message-Timestamp")
    signature = request.headers.get("Twitch-Eventsub-Message-Signature")
    body = request.get_data()

    # Construct verification string
    hmac_message = f"{message_id}{timestamp}{body.decode()}"

    # Calculate expected signature
    expected_signature = "sha256=" + hmac.new(
        self.webhook_secret.encode(),
        hmac_message.encode(),
        hashlib.sha256
    ).hexdigest()

    # Verify signature matches
    return hmac.compare_digest(signature, expected_signature)
```

## Performance Considerations

### Connection Pooling

- **IRC Connections**: One per broadcaster (cached)
- **HTTP Connections**: Reused via requests session
- **Database Pool**: 10 connections default

### Rate Limiting Strategy

```
Twitch Limits:
├─ 1 message/second per channel
├─ 50 API requests/second per app
└─ 20 clips/second per workspace

Module Implementation:
├─ Per-channel message queue
├─ Exponential backoff on rate limit
├─ Track reset times
└─ Automatic retry with jitter
```

### Token Caching

- **In-Memory**: Recent tokens cached for 60 seconds
- **Database**: Source of truth for all tokens
- **Refresh**: Proactive refresh 5 minutes before expiry
- **Invalidation**: Clear cache on token revocation

## Error Handling

### IRC Connection Errors

```python
try:
    connect_to_irc()
except ConnectionError:
    # Retry with exponential backoff: 1s, 2s, 4s, 8s...
    # Max 3 retries, then fail action
except AuthenticationError:
    # Refresh token and retry
    # If still fails, mark broadcaster as failed
```

### Token Refresh Errors

```python
try:
    refresh_token()
except TokenRefreshError:
    # Increment failed_attempts
    # After 3 failures, notify admin
    # Return error to client
```

## Deployment Architecture

### Container Networking

```
waddlebot-network (Docker bridge)
├── twitch-action-module:8072 (REST)
├── twitch-action-module:50053 (gRPC)
├── waddlebot-router:50051 (sends gRPC)
├── postgres:5432 (tokens, history)
└── redis:6379 (credential notifications)
```

### Scaling Considerations

The module is stateless except for IRC connections:

- **Sticky Sessions**: Broadcaster IRC connections should route to same instance
- **Or**: Use external IRC connection pool (redis, memcached)
- **Or**: Implement IRC connection migration on pod restart

**Recommended**: External IRC connection state management

```yaml
# Kubernetes example
spec:
  replicas: 3
  sessionAffinity: ClientIP  # Route same broadcaster to same pod
  sessionAffinityConfig:
    clientIP:
      timeoutSeconds: 10800  # 3 hours
```
