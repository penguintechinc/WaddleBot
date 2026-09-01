# Slack Action Module - Overview

## Purpose

The Slack Action Module is a stateless, scalable microservice responsible for pushing messages, reactions, files, and channel management operations to Slack workspaces. It receives tasks from the WaddleBot processor via gRPC and exposes a REST API for third-party integration. The module handles authentication, message formatting (including Block Kit), thread management, and action history tracking.

**Source**: `/home/penguin/code/waddlebot/action/pushing/slack_action_module/`
**Language**: Python 3.13
**Framework**: Quart (async Python web framework)
**Port (gRPC)**: 50052
**Port (REST)**: 8071
**Organization**: Penguin Tech Inc

## Key Capabilities

- **Message Operations**: Send, update, delete messages with text and Block Kit formatting
- **Ephemeral Messages**: Send temporary messages visible only to specific users
- **Reactions**: Add and remove emoji reactions to messages
- **File Uploads**: Push files to channels with descriptions and titles
- **Channel Management**: Create channels, invite/kick users, set topics
- **Modal Dialogs**: Open interactive modals in Slack for user interactions
- **Action Tracking**: Maintains database history of all operations with success/failure status
- **JWT Authentication**: Secure REST API access with configurable tokens
- **gRPC Server**: Receive distributed task requests from processor for scalable operations
- **Thread Management**: Post messages to threads using timestamps

## Module Information

| Property | Value |
|----------|-------|
| **Module Name** | `slack_action_module` |
| **Module Version** | 1.0.0 |
| **gRPC Port** | 50052 |
| **REST Port** | 8071 |
| **Database** | PostgreSQL via PyDAL |
| **Auth Method** | JWT (Bearer token) |
| **Max Concurrent Requests** | 100 (configurable) |
| **Request Timeout** | 30 seconds (configurable) |

## Documentation Index

| Document | Purpose |
|----------|---------|
| **OVERVIEW.md** (this file) | High-level module purpose, capabilities, and quick reference |
| **USAGE.md** | Docker setup, configuration walkthrough, and practical examples |
| **API.md** | Complete REST API endpoint documentation with request/response schemas |
| **ARCHITECTURE.md** | Internal design, Slack Web API integration, data flow, and components |
| **CONFIGURATION.md** | Environment variables, token setup, and .env file template |
| **TESTING.md** | Unit testing, mock utilities, test payloads, and test execution |
| **TROUBLESHOOTING.md** | Common error codes, debugging strategies, and solutions |
| **RELEASE_NOTES.md** | Version history and changes |

## Quick Reference

### Health Check
```bash
curl http://localhost:8071/health
```

### Generate JWT Token
```bash
curl -X POST http://localhost:8071/api/v1/token \
  -H "Content-Type: application/json" \
  -d '{"api_key": "your-secret-key", "client_id": "my-client"}'
```

### Send Message
```bash
curl -X POST http://localhost:8071/api/v1/message \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "community_id": "community-123",
    "channel_id": "C01234567",
    "text": "Hello Slack!",
    "blocks": []
  }'
```

### Add Reaction
```bash
curl -X POST http://localhost:8071/api/v1/reaction \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "community_id": "community-123",
    "channel_id": "C01234567",
    "ts": "1234567890.123456",
    "emoji": "thumbsup"
  }'
```

### Get Action History
```bash
curl http://localhost:8071/api/v1/history/community-123?limit=50 \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Default Configuration Values

| Environment Variable | Default | Purpose |
|----------------------|---------|---------|
| `SLACK_BOT_TOKEN` | (required) | OAuth bot token for Slack workspace |
| `SLACK_APP_TOKEN` | (optional) | App-level token for socket mode (if needed) |
| `GRPC_PORT` | 50052 | gRPC server listening port |
| `REST_PORT` | 8071 | REST API server listening port |
| `DATABASE_URL` | postgresql://... | PostgreSQL connection string |
| `MODULE_SECRET_KEY` | (required) | Secret for JWT signing |
| `JWT_ALGORITHM` | HS256 | JWT algorithm (HMAC SHA256) |
| `JWT_EXPIRY_SECONDS` | 3600 | JWT token expiration (1 hour) |
| `MAX_CONCURRENT_REQUESTS` | 100 | Max concurrent request handler threads |
| `REQUEST_TIMEOUT` | 30 | HTTP request timeout in seconds |
| `LOG_LEVEL` | INFO | Logging verbosity |
| `LOG_DIR` | /var/log/waddlebotlog | Directory for log files |

## Dependencies

- `slack-sdk` (Python): Official Slack SDK for API calls
- `quart`: Async Python ASGI web framework
- `pydal`: Database abstraction layer (PyDAL)
- `pyjwt`: JWT token handling
- `grpcio`: gRPC framework
- `protobuf`: Protocol Buffers for gRPC communication

## Workspace Scopes Required

For the bot token, ensure these Slack workspace scopes are enabled:

- `chat:write` - Send messages to channels
- `chat:write.public` - Send to public channels
- `files:write` - Upload files
- `emoji:read` - Read emoji information
- `channels:manage` - Create and manage channels
- `users:read` - Read user information
- `views:open` - Open modals and interactive components
- `reactions:write` - Add/remove reactions
- `reactions:read` - Read reactions
- `groups:write` - Manage private channels (groups)
- `groups:manage` - Manage group membership

## Architecture Pattern

```
┌─────────────────────┐
│  WaddleBot Router   │ (sends gRPC task requests)
└──────────┬──────────┘
           │
           │ (gRPC Task)
           ▼
┌─────────────────────────────────────────────┐
│   Slack Action Module                       │
│  ┌───────────────────────────────────────┐  │
│  │ gRPC Server (Port 50052)              │  │
│  │ - Receives ExecuteAction requests     │  │
│  │ - Parses task payloads                │  │
│  │ - Routes to SlackService              │  │
│  └───────────────────────────────────────┘  │
│  ┌───────────────────────────────────────┐  │
│  │ REST API (Port 8071)                  │  │
│  │ - /api/v1/message (POST/PUT/DELETE)  │  │
│  │ - /api/v1/reaction (POST/DELETE)     │  │
│  │ - /api/v1/file (POST)                │  │
│  │ - /api/v1/channel/* (POST/PUT)       │  │
│  │ - /api/v1/modal (POST)               │  │
│  │ - /api/v1/history (GET)              │  │
│  └───────────────────────────────────────┘  │
│  ┌───────────────────────────────────────┐  │
│  │ SlackService                          │  │
│  │ - Slack Web API integration           │  │
│  │ - Message formatting                 │  │
│  │ - Error handling & retries            │  │
│  └───────────────────────────────────────┘  │
│  ┌───────────────────────────────────────┐  │
│  │ PyDAL Database Layer                  │  │
│  │ - Action history persistence          │  │
│  │ - Credential management               │  │
│  └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
           │
           │ (REST HTTP)
           ▼
┌─────────────────────┐
│ Slack Web API       │ (api.slack.com)
└─────────────────────┘
```

## Related Documentation

- **WaddleBot Project**: See `/home/penguin/code/waddlebot/docs/` for system-wide documentation
- **Module Standards**: See `.claude/technology.md` for microservice architecture patterns
- **Kubernetes Deployment**: See `k8s/` directory for container orchestration
