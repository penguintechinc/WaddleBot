# Slack Action Module - Architecture

## System Design

The Slack Action Module follows a microservice architecture with clear separation of concerns:

### Core Components

```
┌─────────────────────────────────────────────────────┐
│           Slack Action Module (Container)            │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌─────────────────────────────────────────────┐  │
│  │ gRPC Server (Port 50052)                    │  │
│  │ ─ Receives ExecuteAction gRPC messages     │  │
│  │ ─ Parses task payloads                     │  │
│  │ ─ Routes to SlackService.execute()         │  │
│  └──────────────┬──────────────────────────────┘  │
│                 │                                  │
│                 ▼                                  │
│  ┌─────────────────────────────────────────────┐  │
│  │ REST API Server (Port 8071)                 │  │
│  │ ─ Receive HTTP POST/PUT/DELETE requests   │  │
│  │ ─ Validate JWT authentication              │  │
│  │ ─ Route to SlackService methods           │  │
│  │ ─ Return JSON responses                    │  │
│  └──────────────┬──────────────────────────────┘  │
│                 │                                  │
│                 ▼                                  │
│  ┌─────────────────────────────────────────────┐  │
│  │ SlackService (Business Logic)               │  │
│  │ ─ send_message()                            │  │
│  │ ─ send_ephemeral()                          │  │
│  │ ─ update_message()                          │  │
│  │ ─ delete_message()                          │  │
│  │ ─ add_reaction()                            │  │
│  │ ─ remove_reaction()                         │  │
│  │ ─ upload_file()                             │  │
│  │ ─ create_channel()                          │  │
│  │ ─ invite_to_channel()                       │  │
│  │ ─ set_topic()                               │  │
│  │ ─ open_modal()                              │  │
│  │ ─ get_action_history()                      │  │
│  └──────────────┬──────────────────────────────┘  │
│                 │                                  │
│        ┌────────┴─────────┐                       │
│        ▼                  ▼                       │
│  ┌──────────────────┐  ┌──────────────────────┐  │
│  │ slack_sdk        │  │ PyDAL Database       │  │
│  │ (Python SDK)     │  │ Layer                │  │
│  │                  │  │                      │  │
│  │ Client methods:  │  │ ─ Store action      │  │
│  │ ─ chat.postMsgOpt│ │   history            │  │
│  │ ─ reactions.add  │  │ ─ Load credentials  │  │
│  │ ─ files.upload   │  │   from DB           │  │
│  │ ─ channels.create│  │ ─ Manage platform  │  │
│  │ ─ conversations. │  │   integrations      │  │
│  │   invite         │  │                      │  │
│  └──────────────────┘  └──────────────────────┘  │
│        │                       │                  │
└────────┼───────────────────────┼─────────────────┘
         │                       │
         ▼                       ▼
    ┌─────────────┐       ┌──────────────┐
    │ Slack Web   │       │ PostgreSQL   │
    │ API         │       │ Database     │
    │ api.slack.  │       │              │
    │ com/api/    │       │ waddlebot DB │
    └─────────────┘       └──────────────┘
```

## Data Flow

### Message Sending Flow

```
1. Client Request
   ├─ POST /api/v1/message
   ├─ Bearer {JWT_TOKEN}
   └─ JSON payload {channel_id, text, blocks}
        │
        ▼
2. REST API Handler
   ├─ Extract JWT token from header
   ├─ Verify signature with MODULE_SECRET_KEY
   ├─ Check token expiration
   └─ Extract community_id from payload
        │
        ▼
3. SlackService.send_message()
   ├─ Validate inputs (channel_id, text)
   ├─ Format message with Block Kit if blocks provided
   ├─ Call slack_sdk client.chat_postMessage()
   └─ Handle API response
        │
        ▼
4. Slack Web API Call
   ├─ POST https://slack.com/api/chat.postMessage
   ├─ Headers: Authorization: Bearer xoxb-{BOT_TOKEN}
   └─ Data: {channel, text, blocks}
        │
        ▼
5. Database Recording
   ├─ Record action in action_history table
   ├─ Store: action_type, success, error, message_ts
   └─ Timestamp creation time
        │
        ▼
6. Response to Client
   ├─ HTTP 200 with success=true
   ├─ Include message_ts for future reference
   └─ Optional error details if failed
```

### Authentication Flow

```
1. Get JWT Token
   ├─ POST /api/v1/token
   ├─ Body: {api_key: "MODULE_SECRET_KEY", client_id}
   └─ No Authorization header required
        │
        ▼
2. Server Verification
   ├─ Check api_key against Config.MODULE_SECRET_KEY
   ├─ If mismatch, return 401 Unauthorized
   └─ If valid, proceed
        │
        ▼
3. Token Generation
   ├─ Create JWT payload:
   │  ├─ iss: "slack_action_module"
   │  ├─ sub: client_id
   │  ├─ exp: now + JWT_EXPIRY_SECONDS (3600)
   │  └─ iat: now
   ├─ Sign with HS256 + MODULE_SECRET_KEY
   └─ Return token + expires_in
        │
        ▼
4. Using Token
   ├─ Include: Authorization: Bearer {token}
   ├─ Server decodes JWT with MODULE_SECRET_KEY
   ├─ Verify signature
   ├─ Check expiration time
   └─ If valid, allow request; else 401
```

## Slack Web API Integration

### API Endpoints Used

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `chat.postMessage` | POST | Send message to channel |
| `chat.postEphemeral` | POST | Send ephemeral message |
| `chat.update` | POST | Update existing message |
| `chat.delete` | POST | Delete message |
| `reactions.add` | POST | Add emoji reaction |
| `reactions.remove` | POST | Remove emoji reaction |
| `files.upload` | POST (multipart) | Upload file to channel |
| `conversations.create` | POST | Create new channel |
| `conversations.invite` | POST | Invite users to channel |
| `conversations.kick` | POST | Remove user from channel |
| `conversations.setTopic` | POST | Set channel topic |
| `views.open` | POST | Open modal dialog |
| `auth.test` | GET | Test token validity |

### Error Handling

```python
try:
    response = slack_sdk_client.chat_postMessage(
        channel=channel_id,
        text=text,
        blocks=blocks
    )
except SlackApiError as e:
    if e.response['error'] == 'not_in_channel':
        # Bot not in channel - log and return error
    elif e.response['error'] == 'channel_not_found':
        # Channel ID invalid - check channel_id format
    elif e.response['error'] == 'invalid_auth':
        # Token expired/revoked - reload from DB
    elif e.response['error'] == 'rate_limited':
        # Rate limit hit - implement backoff
    else:
        # Other API error - log and re-raise
```

## Message Formatting

### Block Kit Blocks

The module supports all Slack Block Kit block types:

**Section Block**
```json
{
  "type": "section",
  "text": {
    "type": "mrkdwn",
    "text": "*Bold* _italic_ ~strikethrough~"
  }
}
```

**Divider Block**
```json
{
  "type": "divider"
}
```

**Image Block**
```json
{
  "type": "image",
  "image_url": "https://example.com/image.jpg",
  "alt_text": "Alt text"
}
```

**Actions Block**
```json
{
  "type": "actions",
  "elements": [
    {
      "type": "button",
      "text": {"type": "plain_text", "text": "Click me"},
      "value": "click_me_123"
    }
  ]
}
```

**Input Block**
```json
{
  "type": "input",
  "label": {"type": "plain_text", "text": "Label"},
  "element": {
    "type": "plain_text_input",
    "action_id": "input_action"
  }
}
```

## Database Schema

### action_history Table

```sql
CREATE TABLE action_history (
  id INT PRIMARY KEY AUTO_INCREMENT,
  community_id VARCHAR(255) NOT NULL,
  action_type VARCHAR(50) NOT NULL,
  channel_id VARCHAR(50),
  user_id VARCHAR(50),
  success BOOLEAN NOT NULL DEFAULT FALSE,
  error TEXT,
  details JSON,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_community_id (community_id),
  INDEX idx_action_type (action_type),
  INDEX idx_created_at (created_at)
);
```

### platform_integrations Table

```sql
CREATE TABLE platform_integrations (
  id INT PRIMARY KEY AUTO_INCREMENT,
  community_id VARCHAR(255) NOT NULL,
  platform VARCHAR(50) NOT NULL,
  integration_type VARCHAR(50) NOT NULL,
  workspace_id VARCHAR(255),
  team_id VARCHAR(255),
  access_token VARCHAR(1000),
  refresh_token VARCHAR(1000),
  config_data JSON,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_platform (platform),
  UNIQUE KEY unique_integration (community_id, platform, integration_type)
);
```

## Credential Management

### Token Loading Strategy

```
1. Application Startup
   ├─ Read SLACK_BOT_TOKEN from environment
   ├─ If empty, wait for database load
   └─ Store in Config.SLACK_BOT_TOKEN

2. Database Credential Load (Optional)
   ├─ Query platform_integrations table
   ├─ Search: platform='slack' AND integration_type='bot' AND is_active=TRUE
   ├─ Extract access_token from row
   ├─ Override Config.SLACK_BOT_TOKEN
   └─ Set _credentials_loaded flag

3. Credential Refresh Listener (Optional with Redis)
   ├─ Subscribe to Redis channel: credentials:slack:bot:refreshed
   ├─ On notification, set _credentials_loaded = False
   ├─ Next request triggers reload from DB
   └─ Seamless token rotation without restart
```

### Lock Mechanism

Uses `threading.Lock` to prevent race conditions during credential reload:

```python
with Config._credential_lock:
    # Only one thread can update credentials at a time
    Config.SLACK_BOT_TOKEN = new_token
    Config._credentials_loaded = True
```

## Performance Considerations

### Concurrency Model

- **Async Framework**: Quart handles many concurrent requests efficiently
- **Max Workers**: Default 10 gRPC workers, adjustable via `GRPC_MAX_WORKERS`
- **Max Requests**: Default 100 concurrent requests, adjustable via `MAX_CONCURRENT_REQUESTS`
- **Connection Pool**: PyDAL maintains 10 database connections by default

### Rate Limiting

Slack API has strict rate limits:

```
- 1 message per second per channel
- 50 requests per second per app
- File uploads: 20 per second per workspace
```

Module implements:
- Per-request timeouts (30 seconds default)
- Exponential backoff for rate-limited responses
- Action history tracking for monitoring

### Caching

Currently no in-memory caching; all operations are immediate:
- Message sends hit Slack API immediately
- No message body cache
- Credential reloads from DB when needed
- Action history stored in database for persistence

## Security Architecture

### JWT Implementation

```python
# Token generation
import jwt
from datetime import datetime, timedelta

payload = {
    'exp': datetime.utcnow() + timedelta(seconds=3600),
    'iat': datetime.utcnow(),
    'sub': 'client_id',
    'permissions': ['execute_actions']
}

token = jwt.encode(
    payload,
    Config.MODULE_SECRET_KEY,
    algorithm='HS256'
)
```

### Secret Storage

- `SLACK_BOT_TOKEN`: Environment variable or database
- `MODULE_SECRET_KEY`: Environment variable only (not in DB)
- `JWT_ALGORITHM`: HS256 (HMAC with SHA256)
- **Never logged**: Tokens are redacted from logs

### Validation

Every request validates:

1. **Authorization Header**
   - Format: `Bearer <token>`
   - Presence: Required (except /health and /token)

2. **JWT Signature**
   - Algorithm: HS256
   - Secret: MODULE_SECRET_KEY
   - Mismatch returns 401

3. **Token Expiration**
   - Check exp claim
   - Expired returns 401

4. **Request Parameters**
   - community_id: String, required
   - channel_id: Slack format `C...` or `G...`
   - user_id: Slack format `U...`
   - emoji: Valid emoji name

## Event Handling

### gRPC Message Structure

```protobuf
message ExecuteActionRequest {
  string action_type = 1;
  string community_id = 2;
  string channel_id = 3;
  string text = 4;
  string user_id = 5;
  map<string, string> parameters = 6;
  int64 timestamp = 7;
  string request_id = 8;
}

message ExecuteActionResponse {
  bool success = 1;
  string message = 2;
  string error = 3;
  map<string, string> metadata = 4;
}
```

### Request Processing

1. Receive gRPC message
2. Extract action_type from message
3. Route to appropriate SlackService method
4. Execute with provided parameters
5. Record result to action_history
6. Return response with success/error

## Deployment Architecture

### Container Networking

```
waddlebot-network (Docker bridge)
├── slack-action-module:8071 (REST)
├── slack-action-module:50052 (gRPC)
├── waddlebot-router:50051 (sends gRPC requests)
├── postgres:5432 (database)
└── redis:6379 (credential notifications)
```

### Health Monitoring

- **Endpoint**: GET /health (port 8071)
- **Docker Compose**: Built-in healthcheck
- **Kubernetes**: Readiness/liveness probes
- **Checks**: Database connectivity + Slack API token validity

### Scaling Considerations

The module is stateless and designed for horizontal scaling:

- Each instance is independent
- Shared database for action history
- Shared Redis for credential refresh notifications
- Load balancer can route to any instance
- No session affinity required

Scaling example:

```yaml
slack-action-module:
  replicas: 3
  ports: [8071, 50052]
  # Each instance gets:
  # - Unique container name
  # - Same database connection
  # - Shared Redis subscription
```
