# Twitch Action Module - Usage Guide

## Docker Setup

### Building the Container

```bash
# From repository root
docker build -f action/pushing/twitch_action_module/Dockerfile \
  -t waddlebot/twitch-action-module:latest \
  action/pushing/twitch_action_module/

# Or with version tag
docker build -f action/pushing/twitch_action_module/Dockerfile \
  -t waddlebot/twitch-action-module:1.0.0 \
  action/pushing/twitch_action_module/
```

### Docker Compose Configuration

Add to your `docker-compose.yml`:

```yaml
twitch-action-module:
  image: waddlebot/twitch-action-module:latest
  container_name: twitch-action-module
  ports:
    - "8072:8072"  # REST API
    - "50053:50053" # gRPC
  environment:
    # Twitch Configuration
    TWITCH_CLIENT_ID: ${TWITCH_CLIENT_ID}
    TWITCH_CLIENT_SECRET: ${TWITCH_CLIENT_SECRET}

    # Server Configuration
    REST_PORT: 8072
    GRPC_PORT: 50053

    # Database Configuration
    DATABASE_URL: postgresql://user:password@postgres:5432/waddlebot
    REDIS_URL: redis://redis:6379/0

    # Security
    MODULE_SECRET_KEY: ${MODULE_SECRET_KEY}
    JWT_ALGORITHM: HS256
    JWT_EXPIRATION_SECONDS: 3600

    # Performance
    MAX_WORKERS: 20
    REQUEST_TIMEOUT: 30
    MAX_BATCH_SIZE: 100
    TOKEN_REFRESH_BUFFER: 300

    # Logging
    LOG_LEVEL: INFO
    LOG_DIR: /var/log/waddlebotlog

  depends_on:
    - postgres
    - redis
  networks:
    - waddlebot
  restart: unless-stopped
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8072/health"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 10s
```

### Running the Container

```bash
# Development mode
docker-compose up action-twitch

# Production mode (background)
docker-compose up -d twitch-action-module

# View logs
docker-compose logs -f action-twitch

# Stop container
docker-compose down action-twitch
```

## Twitch App Registration

### Create Application

1. Go to https://dev.twitch.tv/console/apps
2. Click "Create Application"
3. Enter app name: `WaddleBot`
4. Select category: `Chat Bot` or `Application`
5. Accept terms and create app
6. Copy **Client ID** and **Client Secret**

### Configure OAuth Redirect

1. In Console, find your app and click "Manage"
2. Under "OAuth Redirect URLs", add:
   - `http://localhost:8072/oauth/callback` (development)
   - `https://yourdomain.com/oauth/callback` (production)
3. Save changes

### Request OAuth Scopes

Your app will request these scopes during OAuth flow:

```
chat:edit - Send messages to chat
chat:read - Read chat messages
clips:edit - Create clips from streams
moderator:manage:chat_settings - Manage chat settings
```

## OAuth Token Setup

### Authorization Code Flow (User-Initiated)

```bash
# 1. Redirect user to authorization URL
curl -G https://id.twitch.tv/oauth2/authorize \
  -d "client_id=$TWITCH_CLIENT_ID" \
  -d "redirect_uri=http://localhost:8072/oauth/callback" \
  -d "response_type=code" \
  -d "scope=chat:edit+chat:read+clips:edit" \
  -d "state=random_state_string"

# Result: User grants permission, gets redirected with:
# http://localhost:8072/oauth/callback?code=abc123&state=random_state_string

# 2. Module receives callback, exchanges code for token
# (Automatic in module's /oauth/callback endpoint)

# 3. Token stored in database twitch_action_tokens table
```

### Storing Token Manually

If you have a token from elsewhere:

```bash
# Generate JWT token first
TOKEN=$(curl -s -X POST http://localhost:8072/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"api_key": "'$MODULE_SECRET_KEY'", "service": "admin"}' | jq -r '.token')

# Store token for broadcaster
curl -X POST http://localhost:8072/api/v1/tokens/store \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "broadcaster_id": "123456789",
    "access_token": "access_token_here",
    "refresh_token": "refresh_token_here",
    "expires_in": 3600,
    "scopes": ["chat:edit", "chat:read", "clips:edit"]
  }'
```

## Health Check

### REST Endpoint

```bash
# Check module health
curl http://localhost:8072/health

# Response (200 OK):
{
  "status": "healthy",
  "module": "twitch_action_module",
  "version": "1.0.0",
  "timestamp": "2024-01-15T10:30:00",
  "database": "connected",
  "grpc_port": 50053,
  "rest_port": 8072
}

# If unhealthy (503 Service Unavailable):
{
  "status": "unhealthy",
  "error": "database connection failed"
}
```

### Via Docker Compose

```bash
# Docker health check
docker-compose ps action-twitch

# Should show: healthy status after 30 seconds
```

## IRC Connection Walkthrough

### Connect to Twitch IRC

The module automatically establishes IRC connection when needed:

```python
# Internal connection flow:
1. Get broadcaster's OAuth token from database
2. If expired, refresh via Twitch API
3. Connect to irc.chat.twitch.tv:6667 (TLS)
4. Authenticate: PASS oauth:ACCESS_TOKEN
5. NICK waddlebot
6. JOIN #broadcaster_channel
7. Ready to send messages
```

### Send Chat Message via IRC

```bash
# Generate JWT token
TOKEN=$(curl -s -X POST http://localhost:8072/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"api_key": "'$MODULE_SECRET_KEY'", "service": "test"}' | jq -r '.token')

# Send message
curl -X POST http://localhost:8072/api/v1/actions/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action_type": "send_chat_message",
    "broadcaster_id": "123456789",
    "parameters": {
      "message": "Hello Twitch chat!"
    }
  }'

# Response (200 OK):
{
  "success": true,
  "message": "Message sent successfully",
  "metadata": {
    "message_id": "msg_123",
    "timestamp": 1234567890
  }
}
```

### Connect with Different Broadcasters

Each broadcaster has their own OAuth token and IRC connection:

```bash
# Send to broadcaster 1
curl -X POST http://localhost:8072/api/v1/actions/execute \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "action_type": "send_chat_message",
    "broadcaster_id": "111111111",
    "parameters": {"message": "Hello broadcaster 1!"}
  }'

# Send to broadcaster 2 (same module, different token)
curl -X POST http://localhost:8072/api/v1/actions/execute \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "action_type": "send_chat_message",
    "broadcaster_id": "222222222",
    "parameters": {"message": "Hello broadcaster 2!"}
  }'
```

## Send Chat Message Example

### Basic Message

```bash
curl -X POST http://localhost:8072/api/v1/actions/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action_type": "send_chat_message",
    "broadcaster_id": "123456789",
    "parameters": {
      "message": "PogU WaddleBot is here!"
    }
  }'
```

### Message with Emotes

```bash
curl -X POST http://localhost:8072/api/v1/actions/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action_type": "send_chat_message",
    "broadcaster_id": "123456789",
    "parameters": {
      "message": "PogU Kreygasm EZ Clap"
    }
  }'
```

### Message with /me (action)

```bash
curl -X POST http://localhost:8072/api/v1/actions/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action_type": "send_chat_message",
    "broadcaster_id": "123456789",
    "parameters": {
      "message": "/me waves at everyone!"
    }
  }'
```

## Store Broadcaster Token

```bash
curl -X POST http://localhost:8072/api/v1/tokens/store \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "broadcaster_id": "123456789",
    "access_token": "access_token_here",
    "refresh_token": "refresh_token_here",
    "expires_in": 3600,
    "scopes": ["chat:edit", "chat:read", "clips:edit"]
  }'

# Response (200 OK):
{
  "success": true,
  "message": "Token stored successfully"
}
```

## Revoke Broadcaster Token

```bash
curl -X POST http://localhost:8072/api/v1/tokens/revoke \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "broadcaster_id": "123456789"
  }'

# Response (200 OK):
{
  "success": true,
  "message": "Token revoked successfully"
}
```

## Batch Execute Actions

Send multiple actions in one request:

```bash
curl -X POST http://localhost:8072/api/v1/actions/batch \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "actions": [
      {
        "action_type": "send_chat_message",
        "broadcaster_id": "123456789",
        "request_id": "msg_1",
        "parameters": {
          "message": "First message"
        }
      },
      {
        "action_type": "send_chat_message",
        "broadcaster_id": "123456789",
        "request_id": "msg_2",
        "parameters": {
          "message": "Second message"
        }
      },
      {
        "action_type": "send_chat_message",
        "broadcaster_id": "123456789",
        "request_id": "msg_3",
        "parameters": {
          "message": "Third message"
        }
      }
    ]
  }'

# Response (200 OK):
{
  "success": true,
  "results": [
    {
      "request_id": "msg_1",
      "success": true,
      "message": "Message sent"
    },
    {
      "request_id": "msg_2",
      "success": true,
      "message": "Message sent"
    },
    {
      "request_id": "msg_3",
      "success": true,
      "message": "Message sent"
    }
  ]
}
```

## Create Clip

Create a clip from a live stream:

```bash
curl -X POST http://localhost:8072/api/v1/actions/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action_type": "create_clip",
    "broadcaster_id": "123456789",
    "parameters": {
      "title": "Epic Moment",
      "has_delay": false
    }
  }'

# Response (200 OK):
{
  "success": true,
  "data": {
    "id": "clip_12345",
    "url": "https://clips.twitch.tv/...",
    "edit_url": "https://clips.twitch.tv/.../edit"
  }
}
```

## Get Module Statistics

```bash
curl http://localhost:8072/api/v1/stats \
  -H "Authorization: Bearer $TOKEN"

# Response (200 OK):
{
  "module": "twitch_action_module",
  "version": "1.0.0",
  "stats": {
    "registered_broadcasters": 42,
    "grpc_port": 50053,
    "rest_port": 8072
  },
  "timestamp": "2024-01-15T10:30:00"
}
```

## OAuth Callback Handling

The module automatically handles OAuth callbacks:

```bash
# User authorizes app, redirected to:
# http://localhost:8072/oauth/callback?code=abc123&state=random_state

# Module:
# 1. Receives callback
# 2. Exchanges code for token with Twitch API
# 3. Stores token in database
# 4. Returns success response

# Expected response:
{
  "success": true,
  "message": "Authorization successful",
  "channel_id": "123456789",
  "expires_at": "2024-01-15T11:30:00"
}
```

## Configuration Example

```bash
# .env file
TWITCH_CLIENT_ID=your_client_id_here
TWITCH_CLIENT_SECRET=your_client_secret_here
TWITCH_API_BASE_URL=https://api.twitch.tv/helix

REST_PORT=8072
GRPC_PORT=50053

DATABASE_URL=postgresql://mod_action_twitch:changeme@postgres:5432/waddlebot
REDIS_URL=redis://redis:6379/0

MODULE_SECRET_KEY=your-super-secret-key-change-this-in-production

MAX_WORKERS=20
REQUEST_TIMEOUT=30
MAX_BATCH_SIZE=100
TOKEN_REFRESH_BUFFER=300

LOG_LEVEL=INFO
LOG_DIR=/var/log/waddlebotlog
```
