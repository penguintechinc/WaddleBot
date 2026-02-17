# Discord Action Module - Overview

## Purpose

The Discord Action Module is a stateless, clusterable microservice that receives event tasks from the Waddlebot router via gRPC and pushes actions to Discord through the Discord Bot API. It provides both gRPC and REST interfaces for sending messages, managing roles, moderating users, and handling webhooks within Discord servers.

**Module Name:** discord_action_module  
**Language:** Python 3.13  
**gRPC Port:** 50051  
**REST Port:** 8070  
**Status:** Production-Ready

## Core Capabilities

The module enables:

- Message Operations: Send text messages, embeds, reactions to Discord channels
- User Management: Add/remove roles, kick, ban, timeout users with moderation support
- Webhook Operations: Create and manage webhooks, send messages via webhooks
- Activity Logging: Log all Discord actions to database for audit trail
- Rate Limit Handling: Built-in rate limit enforcement and exponential backoff
- JWT Authentication: Secure REST API with token-based authentication
- Multi-Protocol Support: Both gRPC (processor integration) and REST (third-party integration)
- High Availability: Horizontal scaling with stateless design

## Architecture Overview

The module contains:

1. Quart REST API Server (Port 8070) - Serves REST endpoints
2. gRPC Server (Port 50051) - Receives tasks from processor/router
3. Discord Service - Handles all Discord API interactions
4. Authentication - JWT token-based access control
5. Database Layer - PyDAL for PostgreSQL
6. Logging System - Comprehensive activity logging
7. Rate Limit Manager - Discord API compliance
8. Error Handler - Exponential backoff and retry logic

## Documentation Index

| Document | Purpose | Audience |
|----------|---------|----------|
| USAGE.md | Getting started, Docker setup, health checks | Developers, DevOps |
| API.md | Complete REST API endpoint reference | API Consumers |
| ARCHITECTURE.md | System design, components, flow diagrams | Architects, Contributors |
| CONFIGURATION.md | Environment variables, credential setup | DevOps, Operators |
| TESTING.md | Unit/integration tests, mock Discord API | QA Engineers |
| TROUBLESHOOTING.md | Common errors, rate limits, solutions | Support Engineers |
| RELEASE_NOTES.md | Version history and release information | All |

## Quick Reference

### Health Check
```bash
curl http://localhost:8070/health
```

### Generate Authentication Token
```bash
curl -X POST http://localhost:8070/api/v1/token \
  -H "Content-Type: application/json" \
  -d '{"client_id":"app1","client_secret":"secret123"}'
```

### Send Message to Discord
```bash
curl -X POST http://localhost:8070/api/v1/message \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "channel_id": "123456789",
    "content": "Hello from WaddleBot!"
  }'
```

### Add Role to User
```bash
curl -X POST http://localhost:8070/api/v1/role \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "guild_id": "987654321",
    "user_id": "123456789",
    "role_id": "555555555",
    "action": "add"
  }'
```

### Ban User with Reason
```bash
curl -X POST http://localhost:8070/api/v1/moderation/ban \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "guild_id": "987654321",
    "user_id": "123456789",
    "reason": "Spam violation",
    "delete_message_days": 7
  }'
```

## Key Features by Category

### Messaging
- Send messages to channels
- Send embeds with rich formatting
- Add emoji reactions
- Edit/delete messages
- Webhook integration

### User Management
- Add/remove roles
- Kick users from server
- Ban users permanently
- Timeout users (temporary mutes)

### Moderation
- Ban with message history deletion
- Timeout with configurable duration
- Kick with reason logging
- Action audit logging to database

### Integration
- gRPC interface for processor communication
- REST API for third-party integrations
- JWT authentication for all API access
- Database logging of all actions

## Dependencies

**Python Libraries:**
- quart - Async web framework
- grpc - gRPC framework
- pydal - Database abstraction layer
- aiohttp - Async HTTP client
- pyjwt - JWT token generation/verification
- hypercorn - ASGI server

**External Services:**
- PostgreSQL (or compatible database)
- Discord Bot Account with necessary permissions

## Performance Characteristics

- Max Concurrent Requests: 100 (configurable)
- Request Timeout: 30 seconds
- Rate Limit (Global): 50 requests/second
- Rate Limit (Per-Channel): 5 requests/second
- Max Retries: 3 with exponential backoff
- Retry Delay: 1.0 second initial

## Source Code Location

All source code is located in:
/home/penguin/code/waddlebot/action/pushing/discord_action_module/

Key files:
- app.py - Main application with REST endpoints
- config.py - Configuration management
- services/discord_service.py - Discord API operations
- services/grpc_handler.py - gRPC service implementation
- proto/ - Protocol buffer definitions

## Deployment

The module runs as a standalone Docker container with horizontal scaling support. Default deployment:

```bash
docker-compose -f docker-compose.yml up -d
```

The module automatically connects to PostgreSQL database and Discord Bot API. See CONFIGURATION.md for credential setup.

## Security

- Authentication: JWT tokens with configurable expiration
- Credentials: Support for database-based credential storage
- Rate Limiting: Discord rate limits enforced
- Input Validation: All user inputs validated before API calls
- Logging: All operations logged for audit trail
- TLS: gRPC server supports TLS configuration

## Version Information

Current Version: 1.0.0
Released: 2025-01-27
Last Updated: 2026-02-16
