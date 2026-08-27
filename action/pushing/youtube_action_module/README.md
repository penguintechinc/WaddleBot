# YouTube Action Module

Stateless, clusterable container module for pushing actions to YouTube via gRPC and REST API.

## Overview

This module receives tasks from the processor/router and executes YouTube Data API v3 actions including:
- Live chat management (send, delete messages, ban/unban users)
- Moderator management (add, remove moderators)
- Video management (update titles, descriptions)
- Playlist management (create, add/remove videos)
- Broadcast management (start/stop streams, insert ad breaks)
- Comment management (post, reply, delete, moderate)

## Architecture

- **Stateless Container**: Fully clusterable for horizontal scaling
- **PyDAL**: Database operations with PostgreSQL
- **gRPC**: Primary interface for processor/router communication
- **REST API**: Secondary interface for third-party integrations
- **JWT Authentication**: 64-character shared key for secure access
- **OAuth2**: Per-channel token management with automatic refresh

## Installation

### Docker Build

```bash
docker build -t waddlebot/youtube-action:latest .
```

### Docker Run

```bash
docker run -d \
  --name youtube-action \
  -p 8073:8073 \
  -p 50054:50054 \
  -e DATABASE_URL="postgresql://user:pass@host:5432/waddlebot" \
  -e YOUTUBE_CLIENT_ID="your_client_id" \
  -e YOUTUBE_CLIENT_SECRET="your_client_secret" \
  -e MODULE_SECRET_KEY="your_64_char_secret_key" \
  waddlebot/youtube-action:latest
```

## Environment Variables

### Required

- `DATABASE_URL` - PostgreSQL connection string
- `YOUTUBE_CLIENT_ID` - YouTube OAuth client ID
- `YOUTUBE_CLIENT_SECRET` - YouTube OAuth client secret
- `MODULE_SECRET_KEY` - 64-character shared secret for JWT

### Optional

- `GRPC_PORT` - gRPC server port (default: 50054)
- `REST_PORT` - REST API port (default: 8073)
- `YOUTUBE_API_KEY` - YouTube API key (optional)
- `YOUTUBE_REDIRECT_URI` - OAuth redirect URI (default: http://localhost:8073/oauth/callback)
- `MAX_WORKERS` - Size of the thread pool that absorbs blocking YouTube Data API calls (default: 20)
- `REQUEST_TIMEOUT` - API request timeout (default: 30)
- `LOG_LEVEL` - Logging level (default: INFO)
- `ENABLE_CHAT_ACTIONS` - Enable chat actions (default: true)
- `ENABLE_VIDEO_ACTIONS` - Enable video actions (default: true)
- `ENABLE_PLAYLIST_ACTIONS` - Enable playlist actions (default: true)
- `ENABLE_BROADCAST_ACTIONS` - Enable broadcast actions (default: true)
- `ENABLE_COMMENT_ACTIONS` - Enable comment actions (default: true)

## gRPC API

### Service Definition

See `proto/youtube_action.proto` for complete service definition.

### Example Usage

```python
import grpc
import youtube_action_pb2
import youtube_action_pb2_grpc

channel = grpc.insecure_channel('localhost:50054')
stub = youtube_action_pb2_grpc.YouTubeActionStub(channel)

# Send chat message
request = youtube_action_pb2.SendMessageRequest(
    live_chat_id="chat_id",
    message="Hello from WaddleBot!",
    channel_id="channel_id"
)

response = stub.SendLiveChatMessage(request)
print(response.success, response.message)
```

## REST API

### Authentication

All REST endpoints require JWT authentication via `Authorization: Bearer <token>` header.

Generate token:

```bash
curl -X POST http://localhost:8073/api/v1/token/generate \
  -H "Content-Type: application/json" \
  -d '{"secret": "your_secret_key", "channel_id": "channel_id"}'
```

### Endpoints

#### Health Check

```
GET /health
```

#### OAuth Management

```
GET  /oauth/authorize?state=channel_id
GET  /oauth/callback?code=auth_code&state=channel_id
GET  /oauth/channels
DELETE /oauth/revoke/<channel_id>
```

#### Chat Actions

```
POST /api/v1/chat/send
POST /api/v1/chat/delete
POST /api/v1/chat/ban
POST /api/v1/chat/unban
```

#### Moderation

```
POST /api/v1/moderator/add
POST /api/v1/moderator/remove
```

#### Video Management

```
PUT /api/v1/video/title
PUT /api/v1/video/description
```

#### Playlist Management

```
POST /api/v1/playlist/add
POST /api/v1/playlist/remove
POST /api/v1/playlist/create
```

#### Broadcast Management

```
PUT /api/v1/broadcast/status
POST /api/v1/broadcast/cuepoint
```

#### Comment Management

```
POST /api/v1/comment/post
POST /api/v1/comment/reply
DELETE /api/v1/comment/delete
PUT /api/v1/comment/moderate
```

## OAuth Flow

1. Get authorization URL: `GET /oauth/authorize?state=channel_id`
2. User authorizes application via returned URL
3. OAuth callback receives code: `GET /oauth/callback?code=...&state=channel_id`
4. Token stored in database with automatic refresh

## Database Schema

### youtube_oauth_tokens

- `channel_id` - YouTube channel ID (unique)
- `access_token` - OAuth access token
- `refresh_token` - OAuth refresh token
- `token_uri` - Token endpoint URL
- `client_id` - OAuth client ID
- `client_secret` - OAuth client secret
- `scopes` - List of granted scopes
- `expires_at` - Token expiration timestamp
- `created_at` - Token creation timestamp
- `updated_at` - Token update timestamp

## Security

- JWT authentication for REST API with configurable secret
- OAuth2 tokens stored securely in database
- Automatic token refresh before expiration
- Non-root container user
- Feature flags for action type gating
- Comprehensive audit logging

## Logging

All actions logged with AAA (Authentication, Authorization, Auditing) format:

```
[timestamp] LEVEL module:function - AUTH/AUTHZ/AUDIT channel=X action=Y result=Z
```

## Performance

- Thread pool executor for concurrent operations
- Connection pooling for database access
- Stateless design for horizontal scaling
- gRPC for efficient processor communication
- JWT caching for authentication

## Development

### Generate Protobuf Files

```bash
python -m grpc_tools.protoc \
  -I./proto \
  --python_out=./proto \
  --grpc_python_out=./proto \
  ./proto/youtube_action.proto
```

### Run Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Generate protobuf
python -m grpc_tools.protoc -I./proto --python_out=./proto --grpc_python_out=./proto ./proto/youtube_action.proto

# Run application
python app.py
```

## Integration with WaddleBot

1. Processor/router sends gRPC requests to this module
2. Module executes YouTube API actions using stored OAuth tokens
3. Results returned to processor/router for response handling
4. Audit logs maintained for all actions

## License

Limited AGPL3 - See LICENSE file
