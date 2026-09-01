# YouTube Action Module - Overview

## Purpose

The YouTube Action Module is a stateless, scalable microservice for pushing content and managing interactions on YouTube. It handles YouTube Data API v3 operations including live chat messaging, video management, playlist operations, broadcast control, and comment moderation. The module receives tasks from the WaddleBot processor via gRPC and exposes a REST API for third-party integration with OAuth 2.0 authorization code flow.

**Source**: `/home/penguin/code/waddlebot/action/pushing/youtube_action_module/`
**Language**: Python 3.13
**Framework**: Quart (async Python web framework)
**Port (gRPC)**: 50054
**Port (REST)**: 8073
**Organization**: Penguin Tech Inc

## Key Capabilities

- **Live Chat Messaging**: Send messages, ban/unban users, manage moderators
- **Video Management**: Update titles, descriptions, video metadata
- **Playlist Management**: Create playlists, add/remove videos, manage items
- **Broadcast Control**: Update broadcast status, insert ad break cuepoints
- **Comment Moderation**: Post comments, reply, delete, set moderation status
- **OAuth 2.0 Flow**: Authorization code flow with token refresh
- **Multi-Channel Support**: Manage tokens for multiple YouTube channels
- **JWT Authentication**: Secure REST API access with Bearer tokens
- **gRPC Server**: Receive distributed task requests from processor
- **Action History**: Database tracking of operations with results
- **Feature Flags**: Enable/disable action categories (chat, video, playlist, etc.)

## Module Information

| Property | Value |
|----------|-------|
| **Module Name** | `youtube_action_module` |
| **Module Version** | 1.0.0 |
| **gRPC Port** | 50054 |
| **REST Port** | 8073 |
| **Database** | PostgreSQL via PyDAL |
| **Auth Method** | OAuth 2.0 (Authorization Code) + JWT (REST API) |
| **Max Workers** | 20 (configurable) |
| **Request Timeout** | 30 seconds (configurable) |
| **Rate Limiting** | 100 requests/60 seconds per API (configurable) |

## Documentation Index

| Document | Purpose |
|----------|---------|
| **OVERVIEW.md** (this file) | High-level module purpose, capabilities, and quick reference |
| **USAGE.md** | Docker setup, OAuth 2.0 setup, live chat examples |
| **API.md** | Complete REST API endpoint documentation with request/response schemas |
| **ARCHITECTURE.md** | OAuth flow, YouTube Data API v3 integration, live chat polling, data flow |
| **CONFIGURATION.md** | Environment variables, OAuth setup, feature flags, .env template |
| **TESTING.md** | Google API client mocking, test fixtures, test execution |
| **TROUBLESHOOTING.md** | OAuth errors, quota issues, authentication problems, solutions |
| **RELEASE_NOTES.md** | Version history and changes |

## Quick Reference

### Health Check
```bash
curl http://localhost:8073/health
```

### Get OAuth Authorization URL
```bash
curl -G http://localhost:8073/oauth/authorize \
  -d "state=your-channel-id"
```

### Send Live Chat Message
```bash
TOKEN=$(curl -s -X POST http://localhost:8073/api/v1/token/generate \
  -H "Content-Type: application/json" \
  -d '{"secret": "your-module-secret"}' | jq -r '.token')

curl -X POST http://localhost:8073/api/v1/chat/send \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "channel_id": "UCxxxxx",
    "live_chat_id": "AimFLc...",
    "message": "Hello YouTube Live!"
  }'
```

### Ban User from Live Chat
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
```

### Create Playlist
```bash
curl -X POST http://localhost:8073/api/v1/playlist/create \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "channel_id": "UCxxxxx",
    "title": "My Playlist",
    "description": "Playlist description",
    "privacy": "private"
  }'
```

### Post Comment on Video
```bash
curl -X POST http://localhost:8073/api/v1/comment/post \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "channel_id": "UCxxxxx",
    "video_id": "dQw4w9WgXcQ",
    "text": "Great video!"
  }'
```

## Default Configuration Values

| Environment Variable | Default | Purpose |
|----------------------|---------|---------|
| `YOUTUBE_CLIENT_ID` | (required) | OAuth 2.0 client ID |
| `YOUTUBE_CLIENT_SECRET` | (required) | OAuth 2.0 client secret |
| `YOUTUBE_REDIRECT_URI` | http://localhost:8073/oauth/callback | OAuth callback URL |
| `YOUTUBE_API_VERSION` | v3 | YouTube Data API version |
| `GRPC_PORT` | 50054 | gRPC server port |
| `REST_PORT` | 8073 | REST API server port |
| `DATABASE_URL` | postgresql://... | PostgreSQL connection |
| `MODULE_SECRET_KEY` | (required) | Secret for JWT signing |
| `MAX_WORKERS` | 20 | Max concurrent workers |
| `REQUEST_TIMEOUT` | 30 | HTTP timeout (seconds) |
| `MAX_RETRIES` | 3 | Max retry attempts |
| `RATE_LIMIT_REQUESTS` | 100 | Rate limit requests |
| `RATE_LIMIT_WINDOW` | 60 | Rate limit window (seconds) |
| `LOG_LEVEL` | INFO | Logging verbosity |
| `LOG_DIR` | /var/log/waddlebotlog | Log directory |

## Feature Flags

Control which features are enabled:

| Flag | Default | Purpose |
|------|---------|---------|
| `ENABLE_CHAT_ACTIONS` | true | Enable live chat operations |
| `ENABLE_VIDEO_ACTIONS` | true | Enable video metadata updates |
| `ENABLE_PLAYLIST_ACTIONS` | true | Enable playlist operations |
| `ENABLE_BROADCAST_ACTIONS` | true | Enable broadcast control |
| `ENABLE_COMMENT_ACTIONS` | true | Enable comment operations |

## YouTube Data API Scopes

The module uses these OAuth scopes:

- `https://www.googleapis.com/auth/youtube` - Full YouTube access
- `https://www.googleapis.com/auth/youtube.force-ssl` - Secure YouTube access

These scopes grant permissions for:
- Reading/writing live chat messages
- Managing videos (titles, descriptions, privacy)
- Creating/managing playlists
- Managing broadcasts and streams
- Posting/managing comments and replies

## Architecture Pattern

```
┌──────────────────────┐
│  WaddleBot Router    │ (sends gRPC task requests)
└──────────┬───────────┘
           │
           │ (gRPC Task)
           ▼
┌─────────────────────────────────────────────┐
│   YouTube Action Module                     │
│  ┌───────────────────────────────────────┐  │
│  │ gRPC Server (Port 50054)              │  │
│  │ - Receives ExecuteAction requests     │  │
│  │ - Routes to YouTubeService            │  │
│  └───────────────────────────────────────┘  │
│  ┌───────────────────────────────────────┐  │
│  │ REST API (Port 8073)                  │  │
│  │ - /api/v1/chat/* (messages)           │  │
│  │ - /api/v1/video/* (management)        │  │
│  │ - /api/v1/playlist/* (playlists)      │  │
│  │ - /api/v1/broadcast/* (control)       │  │
│  │ - /api/v1/comment/* (comments)        │  │
│  │ - /oauth/* (OAuth flow)               │  │
│  └───────────────────────────────────────┘  │
│  ┌───────────────────────────────────────┐  │
│  │ YouTubeService                        │  │
│  │ - YouTube Data API v3 client          │  │
│  │ - Feature-specific handlers           │  │
│  │ - Error handling & retries            │  │
│  └───────────────────────────────────────┘  │
│  ┌───────────────────────────────────────┐  │
│  │ OAuthManager                          │  │
│  │ - OAuth authorization code flow      │  │
│  │ - Token storage & refresh             │  │
│  │ - Credential lifecycle management    │  │
│  └───────────────────────────────────────┘  │
│  ┌───────────────────────────────────────┐  │
│  │ PyDAL Database Layer                  │  │
│  │ - Channel credentials storage         │  │
│  │ - Action history                      │  │
│  └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
         │                    │
         │ (REST HTTP)        │ (Database)
         ▼                    ▼
    ┌──────────────────┐    ┌──────────────┐
    │ YouTube Data     │    │ PostgreSQL   │
    │ API v3           │    │ Database     │
    │ www.googleapis.  │    │              │
    │ com/youtube      │    │              │
    └──────────────────┘    └──────────────┘
```

## Dependencies

- `google-auth-oauthlib`: Google OAuth library for authorization code flow
- `google-auth-httplib2`: Google Auth HTTP integration
- `google-api-python-client`: Official Google API client library
- `quart`: Async Python web framework
- `pydal`: Database abstraction layer
- `pyjwt`: JWT token handling
- `grpcio`: gRPC framework
- `protobuf`: Protocol Buffers for gRPC

## Related Documentation

- **WaddleBot Project**: See `/home/penguin/code/waddlebot/docs/` for system-wide documentation
- **Module Standards**: See `.claude/technology.md` for microservice patterns
- **Kubernetes Deployment**: See `k8s/` directory for orchestration
- **YouTube API Docs**: https://developers.google.com/youtube/v3
- **Google OAuth**: https://developers.google.com/identity/protocols/oauth2
