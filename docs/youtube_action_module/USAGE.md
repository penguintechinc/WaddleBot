# YouTube Action Module - Usage Guide

## Docker Setup

### Building the Container

```bash
# From repository root
docker build -f action/pushing/youtube_action_module/Dockerfile \
  -t waddlebot/youtube-action-module:latest \
  action/pushing/youtube_action_module/

# Or with version tag
docker build -f action/pushing/youtube_action_module/Dockerfile \
  -t waddlebot/youtube-action-module:1.0.0 \
  action/pushing/youtube_action_module/
```

### Docker Compose Configuration

Add to your `docker-compose.yml`:

```yaml
youtube-action-module:
  image: waddlebot/youtube-action-module:latest
  container_name: youtube-action-module
  ports:
    - "8073:8073"  # REST API
    - "50054:50054" # gRPC
  environment:
    # YouTube OAuth Configuration
    YOUTUBE_CLIENT_ID: ${YOUTUBE_CLIENT_ID}
    YOUTUBE_CLIENT_SECRET: ${YOUTUBE_CLIENT_SECRET}
    YOUTUBE_REDIRECT_URI: http://localhost:8073/oauth/callback

    # Server Configuration
    REST_PORT: 8073
    GRPC_PORT: 50054

    # Database Configuration
    DATABASE_URL: postgresql://user:password@postgres:5432/waddlebot
    REDIS_URL: redis://redis:6379/0

    # Security
    MODULE_SECRET_KEY: ${MODULE_SECRET_KEY}

    # Performance
    MAX_WORKERS: 20
    REQUEST_TIMEOUT: 30
    MAX_RETRIES: 3
    RATE_LIMIT_REQUESTS: 100
    RATE_LIMIT_WINDOW: 60

    # Feature Flags
    ENABLE_CHAT_ACTIONS: "true"
    ENABLE_VIDEO_ACTIONS: "true"
    ENABLE_PLAYLIST_ACTIONS: "true"
    ENABLE_BROADCAST_ACTIONS: "true"
    ENABLE_COMMENT_ACTIONS: "true"

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
    test: ["CMD", "curl", "-f", "http://localhost:8073/health"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 10s
```

### Running the Container

```bash
# Development mode
docker-compose up action-youtube

# Production mode (background)
docker-compose up -d youtube-action-module

# View logs
docker-compose logs -f action-youtube

# Stop container
docker-compose down action-youtube
```

## OAuth 2.0 Setup (Client ID/Secret)

### Create Google Cloud Project

1. Go to https://console.cloud.google.com
2. Create new project: `WaddleBot`
3. Enable YouTube Data API v3:
   - Search for "YouTube Data API v3"
   - Click "Enable"

### Create OAuth 2.0 Credentials

1. Go to "Credentials" in left sidebar
2. Click "Create Credentials" → "OAuth 2.0 Client ID"
3. Select "Web application"
4. Add Authorized Redirect URIs:
   - `http://localhost:8073/oauth/callback` (development)
   - `https://yourdomain.com/oauth/callback` (production)
5. Copy **Client ID** and **Client Secret**

### Store Credentials

```bash
# Add to .env file
YOUTUBE_CLIENT_ID=your-client-id-here.apps.googleusercontent.com
YOUTUBE_CLIENT_SECRET=your-client-secret-here
YOUTUBE_REDIRECT_URI=http://localhost:8073/oauth/callback
```

## Health Check

### REST Endpoint

```bash
# Check module health
curl http://localhost:8073/health

# Response (200 OK):
{
  "status": "healthy",
  "module": "youtube_action_module",
  "version": "1.0.0",
  "timestamp": "2024-01-15T10:30:00",
  "grpc_port": 50054,
  "rest_port": 8073
}

# If unhealthy (503 Service Unavailable):
{
  "status": "unhealthy",
  "error": "database connection failed",
  "timestamp": "2024-01-15T10:30:00"
}
```

### Via Docker Compose

```bash
# Docker health check
docker-compose ps action-youtube

# Should show: healthy status after 30 seconds
```

## OAuth 2.0 Authorization Flow

### Step 1: Get Authorization URL

```bash
# Request authorization URL
curl -G http://localhost:8073/oauth/authorize \
  -d "state=channel-id-123456789"

# Response:
{
  "success": true,
  "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?client_id=...&redirect_uri=...&response_type=code&scope=..."
}
```

### Step 2: User Grants Permission

User visits the authorization URL and grants WaddleBot permissions to manage their YouTube channel.

### Step 3: Handle Callback

Module automatically receives callback with authorization code and exchanges it for access token.

**Callback URL**: `http://localhost:8073/oauth/callback?code=abc123&state=channel-id`

```bash
# Module exchanges code for token automatically
# Token stored in database for future use
```

### Step 4: Verify Authorization

```bash
# Generate JWT token
TOKEN=$(curl -s -X POST http://localhost:8073/api/v1/token/generate \
  -H "Content-Type: application/json" \
  -d '{"secret": "'$MODULE_SECRET_KEY'", "channel_id": "UCxxxxx"}' | jq -r '.token')

# List authorized channels
curl http://localhost:8073/oauth/channels \
  -H "Authorization: Bearer $TOKEN"

# Response:
{
  "success": true,
  "channels": [
    {
      "channel_id": "UCxxxxx",
      "channel_name": "My Channel",
      "authorized_at": "2024-01-15T10:00:00Z"
    }
  ]
}
```

## Send Live Chat Message Example

### Prerequisites

1. Channel must have an active live stream
2. Must have `chat:edit` and `chat:read` scopes granted
3. Need `live_chat_id` (from live stream details)

### Get Live Chat ID

```bash
# Using YouTube API (requires authorized channel)
# Live chat ID is returned in liveBroadcastContent response

# Example live_chat_id: "AimFLc3KqxWP..."
```

### Send Message

```bash
# Generate JWT token
TOKEN=$(curl -s -X POST http://localhost:8073/api/v1/token/generate \
  -H "Content-Type: application/json" \
  -d '{"secret": "'$MODULE_SECRET_KEY'", "channel_id": "UCxxxxx"}' | jq -r '.token')

# Send message
curl -X POST http://localhost:8073/api/v1/chat/send \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "channel_id": "UCxxxxx",
    "live_chat_id": "AimFLc...",
    "message": "Hello from WaddleBot!"
  }'

# Response (200 OK):
{
  "success": true,
  "data": {
    "message_id": "msg_123456",
    "published_at": "2024-01-15T10:30:00Z"
  }
}
```

## Ban User from Live Chat

```bash
curl -X POST http://localhost:8073/api/v1/chat/ban \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "channel_id": "UCxxxxx",
    "live_chat_id": "AimFLc...",
    "target_channel_id": "UCyyyyyy",
    "duration_seconds": null
  }'

# Response:
{
  "success": true,
  "data": {
    "banned_at": "2024-01-15T10:30:00Z"
  }
}
```

## Create Playlist

```bash
curl -X POST http://localhost:8073/api/v1/playlist/create \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "channel_id": "UCxxxxx",
    "title": "My Gaming Playlist",
    "description": "Best gaming videos",
    "privacy": "private"
  }'

# Response:
{
  "success": true,
  "data": {
    "playlist_id": "PLxxxxx",
    "title": "My Gaming Playlist",
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

## Add Video to Playlist

```bash
curl -X POST http://localhost:8073/api/v1/playlist/add \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "channel_id": "UCxxxxx",
    "playlist_id": "PLxxxxx",
    "video_id": "dQw4w9WgXcQ"
  }'

# Response:
{
  "success": true,
  "data": {
    "playlist_item_id": "PLitem_123"
  }
}
```

## Update Video Title

```bash
curl -X PUT http://localhost:8073/api/v1/video/title \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "channel_id": "UCxxxxx",
    "video_id": "dQw4w9WgXcQ",
    "title": "New Video Title"
  }'

# Response:
{
  "success": true,
  "data": {
    "video_id": "dQw4w9WgXcQ",
    "title": "New Video Title"
  }
}
```

## Post Comment on Video

```bash
curl -X POST http://localhost:8073/api/v1/comment/post \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "channel_id": "UCxxxxx",
    "video_id": "dQw4w9WgXcQ",
    "text": "Great video! Thanks for sharing!"
  }'

# Response:
{
  "success": true,
  "data": {
    "comment_id": "comment_123",
    "text": "Great video! Thanks for sharing!"
  }
}
```

## Reply to Comment

```bash
curl -X POST http://localhost:8073/api/v1/comment/reply \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "channel_id": "UCxxxxx",
    "parent_id": "comment_123",
    "text": "Thanks for watching!"
  }'

# Response:
{
  "success": true,
  "data": {
    "comment_id": "comment_reply_456"
  }
}
```

## Update Broadcast Status

```bash
curl -X PUT http://localhost:8073/api/v1/broadcast/status \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "channel_id": "UCxxxxx",
    "broadcast_id": "broadcast_123",
    "status": "live"
  }'

# Status options: testing, live, all

# Response:
{
  "success": true,
  "data": {
    "broadcast_id": "broadcast_123",
    "status": "live",
    "updated_at": "2024-01-15T10:30:00Z"
  }
}
```

## Delete Comment

```bash
curl -X DELETE http://localhost:8073/api/v1/comment/delete \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "channel_id": "UCxxxxx",
    "comment_id": "comment_123"
  }'

# Response:
{
  "success": true
}
```

## Revoke Channel Authorization

```bash
curl -X DELETE http://localhost:8073/oauth/revoke/UCxxxxx \
  -H "Authorization: Bearer $TOKEN"

# Response:
{
  "success": true,
  "message": "Authorization revoked"
}
```

## Configuration Example

```bash
# .env file
YOUTUBE_CLIENT_ID=123456789.apps.googleusercontent.com
YOUTUBE_CLIENT_SECRET=your-secret-here
YOUTUBE_REDIRECT_URI=http://localhost:8073/oauth/callback
YOUTUBE_API_VERSION=v3

REST_PORT=8073
GRPC_PORT=50054

DATABASE_URL=postgresql://user:pass@postgres:5432/waddlebot
REDIS_URL=redis://redis:6379/0

MODULE_SECRET_KEY=your-super-secret-key-change-this

MAX_WORKERS=20
REQUEST_TIMEOUT=30
MAX_RETRIES=3
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60

ENABLE_CHAT_ACTIONS=true
ENABLE_VIDEO_ACTIONS=true
ENABLE_PLAYLIST_ACTIONS=true
ENABLE_BROADCAST_ACTIONS=true
ENABLE_COMMENT_ACTIONS=true

LOG_LEVEL=INFO
LOG_DIR=/var/log/waddlebotlog
ENABLE_SYSLOG=false
```
