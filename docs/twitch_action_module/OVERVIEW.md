# Twitch Action Module - Overview

## Purpose

The Twitch Action Module is a stateless, scalable microservice for pushing interactive content to Twitch platforms. It handles IRC chat messages, EventSub webhook events, OAuth token management, and clip creation through the Twitch Helix API. The module receives tasks from the WaddleBot processor via gRPC and exposes a REST API for third-party integration with JWT authentication.

**Source**: `/home/penguin/code/waddlebot/action/pushing/twitch_action_module/`
**Language**: Python 3.13
**Framework**: Quart (async Python web framework)
**Port (gRPC)**: 50053
**Port (REST)**: 8072
**Organization**: Penguin Tech Inc

## Key Capabilities

- **IRC Chat**: Send messages to Twitch channel chat via IRC protocol
- **EventSub Integration**: Handle Twitch webhook events with signature verification
- **OAuth Token Management**: Store, refresh, and revoke broadcaster OAuth tokens
- **Clip Creation**: Create clips from live streams programmatically
- **Batch Operations**: Execute multiple actions in single batch request
- **Token Refresh**: Automatic OAuth token refresh with expiry handling
- **JWT Authentication**: Secure REST API access with Bearer tokens
- **gRPC Server**: Receive distributed task requests from processor
- **Action History**: Database tracking of all operations with success/failure status
- **Rate Limiting**: Built-in rate limit handling with exponential backoff

## Module Information

| Property | Value |
|----------|-------|
| **Module Name** | `twitch_action_module` |
| **Module Version** | 1.0.0 |
| **gRPC Port** | 50053 |
| **REST Port** | 8072 |
| **Database** | PostgreSQL via PyDAL |
| **Auth Method** | JWT (Bearer token) + Twitch OAuth 2.0 |
| **Max Batch Size** | 100 actions per batch (configurable) |
| **Request Timeout** | 30 seconds (configurable) |

## Documentation Index

| Document | Purpose |
|----------|---------|
| **OVERVIEW.md** (this file) | High-level module purpose, capabilities, and quick reference |
| **USAGE.md** | Docker setup, Twitch app registration, OAuth flow, and examples |
| **API.md** | Complete REST API endpoint documentation with request/response schemas |
| **ARCHITECTURE.md** | IRC lifecycle, OAuth flow, EventSub validation, data flow, and components |
| **CONFIGURATION.md** | Environment variables, OAuth setup, and .env file template |
| **TESTING.md** | IRC mocking, EventSub testing, test payloads, and execution |
| **TROUBLESHOOTING.md** | Authentication errors, token expiry, rate limits, and IRC issues |
| **RELEASE_NOTES.md** | Version history and changes |

## Quick Reference

### Health Check
```bash
curl http://localhost:8072/health
```

### Generate JWT Token
```bash
curl -X POST http://localhost:8072/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"api_key": "your-secret-key", "service": "my-service"}'
```

### Send Chat Message
```bash
curl -X POST http://localhost:8072/api/v1/actions/execute \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action_type": "send_chat_message",
    "broadcaster_id": "123456789",
    "parameters": {
      "message": "Hello Twitch!"
    }
  }'
```

### Store OAuth Token
```bash
curl -X POST http://localhost:8072/api/v1/tokens/store \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "broadcaster_id": "123456789",
    "access_token": "access_token_here",
    "refresh_token": "refresh_token_here",
    "expires_in": 3600,
    "scopes": ["chat:edit", "chat:read"]
  }'
```

### Execute Batch Actions
```bash
curl -X POST http://localhost:8072/api/v1/actions/batch \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "actions": [
      {
        "action_type": "send_chat_message",
        "broadcaster_id": "123456789",
        "parameters": {"message": "Message 1"}
      },
      {
        "action_type": "send_chat_message",
        "broadcaster_id": "123456789",
        "parameters": {"message": "Message 2"}
      }
    ]
  }'
```

### Get Module Statistics
```bash
curl http://localhost:8072/api/v1/stats \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Default Configuration Values

| Environment Variable | Default | Purpose |
|----------------------|---------|---------|
| `TWITCH_CLIENT_ID` | (required) | Twitch application client ID |
| `TWITCH_CLIENT_SECRET` | (required) | Twitch application secret |
| `TWITCH_API_BASE_URL` | https://api.twitch.tv/helix | Twitch API endpoint |
| `GRPC_PORT` | 50053 | gRPC server listening port |
| `REST_PORT` | 8072 | REST API server listening port |
| `DATABASE_URL` | postgresql://... | PostgreSQL connection string |
| `MODULE_SECRET_KEY` | (required) | Secret for JWT signing |
| `JWT_ALGORITHM` | HS256 | JWT algorithm (HMAC SHA256) |
| `JWT_EXPIRATION_SECONDS` | 3600 | JWT token expiration (1 hour) |
| `MAX_WORKERS` | 20 | Max concurrent worker threads |
| `MAX_BATCH_SIZE` | 100 | Max actions per batch request |
| `REQUEST_TIMEOUT` | 30 | HTTP request timeout in seconds |
| `TOKEN_REFRESH_BUFFER` | 300 | Seconds before expiry to refresh (5 min) |
| `LOG_LEVEL` | INFO | Logging verbosity |
| `LOG_DIR` | /var/log/waddlebotlog | Directory for log files |

## Dependencies

- `requests` or `httpx`: HTTP client for Twitch Helix API
- `irc` or `python-irc`: IRC protocol implementation for chat
- `quart`: Async Python ASGI web framework
- `pydal`: Database abstraction layer
- `pyjwt`: JWT token handling
- `grpcio`: gRPC framework
- `protobuf`: Protocol Buffers for gRPC

## Twitch OAuth Scopes

For broadcaster token management, ensure these scopes are granted:

- `chat:edit` - Send messages to chat
- `chat:read` - Read chat messages
- `clips:edit` - Create clips
- `moderator:manage:chat_settings` - Manage chat (slow mode, etc.)
- `user:read:email` - Read broadcaster email (optional)

## Architecture Pattern

```
┌──────────────────────┐
│  WaddleBot Router    │ (sends gRPC task requests)
└──────────┬───────────┘
           │
           │ (gRPC Task)
           ▼
┌─────────────────────────────────────────────┐
│   Twitch Action Module                      │
│  ┌───────────────────────────────────────┐  │
│  │ gRPC Server (Port 50053)              │  │
│  │ - Receives ExecuteAction requests     │  │
│  │ - Routes to TwitchService             │  │
│  │ - Batch action support                │  │
│  └───────────────────────────────────────┘  │
│  ┌───────────────────────────────────────┐  │
│  │ REST API (Port 8072)                  │  │
│  │ - /api/v1/actions/execute (POST)      │  │
│  │ - /api/v1/actions/batch (POST)        │  │
│  │ - /api/v1/tokens/store (POST)         │  │
│  │ - /api/v1/tokens/revoke (POST)        │  │
│  │ - /api/v1/stats (GET)                 │  │
│  └───────────────────────────────────────┘  │
│  ┌───────────────────────────────────────┐  │
│  │ TwitchService                         │  │
│  │ - Helix API integration               │  │
│  │ - OAuth token management              │  │
│  │ - IRC chat connection                 │  │
│  │ - EventSub webhook handling           │  │
│  └───────────────────────────────────────┘  │
│  ┌───────────────────────────────────────┐  │
│  │ TokenManager                          │  │
│  │ - Store broadcaster tokens            │  │
│  │ - Refresh expired tokens              │  │
│  │ - Revoke tokens                       │  │
│  └───────────────────────────────────────┘  │
│  ┌───────────────────────────────────────┐  │
│  │ PyDAL Database Layer                  │  │
│  │ - Token persistence                   │  │
│  │ - Action history                      │  │
│  │ - Credential management               │  │
│  └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
           │                    │
           │ (REST HTTP)        │ (Database)
           ▼                    ▼
    ┌──────────────────┐    ┌──────────────┐
    │ Twitch Helix API │    │ PostgreSQL   │
    │ api.twitch.tv/   │    │ Database     │
    │ helix            │    │              │
    └──────────────────┘    └──────────────┘
           │
           ├─ IRC Chat Endpoint
           │  irc.chat.twitch.tv:6667
           │
           └─ EventSub Webhooks
              https://api.twitch.tv/eventsub
```

## IRC Connection Pattern

```
WaddleBot → Twitch Action Module
              ├─ OAuth Token Manager (validates/refreshes tokens)
              ├─ IRC Connection Pool (maintains 1-N connections)
              │  ├─ irc.chat.twitch.tv (TLS)
              │  ├─ Authenticate with token
              │  └─ JOIN #channel
              │
              └─ Message Handler
                 ├─ Queue outgoing messages
                 ├─ Send via IRC PRIVMSG
                 └─ Log/track delivery
```

## EventSub Webhook Validation

All EventSub webhooks are validated:

```
Twitch → EventSub Webhook
         ├─ Verify X-Twitch-Eventsub-Message-Retry header
         ├─ Check X-Twitch-Eventsub-Subscription-Type
         ├─ Validate X-Twitch-Eventsub-Message-Signature
         │  (HMAC-SHA256: timestamp + body + secret)
         └─ If valid: Process event
            If invalid: Return 403 Forbidden
```

## Related Documentation

- **WaddleBot Project**: See `/home/penguin/code/waddlebot/docs/` for system-wide documentation
- **Module Standards**: See `.claude/technology.md` for microservice architecture patterns
- **Kubernetes Deployment**: See `k8s/` directory for container orchestration
- **Twitch API Docs**: https://dev.twitch.tv/docs/api
- **EventSub Documentation**: https://dev.twitch.tv/docs/eventsub
