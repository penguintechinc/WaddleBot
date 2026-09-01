# Discord Action Module - Usage Guide

## Getting Started

The Discord Action Module is a containerized service that pushes actions to Discord. This guide walks through setup, configuration, and basic usage.

## Prerequisites

Before running the module, you need:

1. **Discord Bot Account**
   - Create on Discord Developer Portal: https://discord.com/developers/applications
   - Enable these intents: Message Content, Guild Members, Guilds, Direct Messages
   - Set permissions: Manage Roles, Kick Members, Ban Members, Manage Messages, Send Messages, Add Reactions, Manage Webhooks

2. **Discord Bot Token**
   - Copy from Bot settings in Developer Portal
   - Keep this token secret - never commit to git

3. **Database**
   - PostgreSQL 12+ (included in docker-compose.yml)
   - Can use existing database with DATABASE_URL environment variable

4. **Docker & Docker Compose**
   - Docker Engine 20.10+
   - Docker Compose 2.0+

## Quick Start with Docker Compose

### 1. Clone Repository
```bash
cd /home/penguin/code/waddlebot/action/pushing/discord_action_module
```

### 2. Create Environment File
```bash
cp .env.example .env
```

Edit .env and set:
```
DISCORD_BOT_TOKEN=your_bot_token_here
MODULE_SECRET_KEY=your_64_character_secret_key_here
```

### 3. Start the Service
```bash
docker-compose up -d
```

Verify it's running:
```bash
docker-compose logs -f discord_action_module
```

### 4. Check Health
```bash
curl http://localhost:8070/health
```

Expected response:
```json
{
  "status": "healthy",
  "module": "discord_action_module",
  "version": "1.0.0",
  "timestamp": "2026-02-16T10:30:45.123456",
  "config": {
    "module_name": "discord_action_module",
    "grpc_port": 50051,
    "rest_port": 8070,
    "database_configured": true,
    "discord_token_configured": true
  }
}
```

## Obtaining a Discord Bot Token

1. Go to Discord Developer Portal: https://discord.com/developers/applications
2. Click "New Application" and name it
3. Go to "Bot" section and click "Add Bot"
4. Under TOKEN, click "Copy" to copy bot token
5. Enable these Intents:
   - Message Content Intent
   - Server Members Intent
6. Set Permissions (551911541):
   - Manage Roles
   - Kick Members
   - Ban Members
   - Manage Messages
   - Send Messages
   - Add Reactions
   - Manage Webhooks

## First API Request

### 1. Generate Authentication Token
```bash
curl -X POST http://localhost:8070/api/v1/token \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "my_app",
    "client_secret": "my_secret"
  }'
```

Response:
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 3600
}
```

### 2. Send Message to Discord Channel
```bash
curl -X POST http://localhost:8070/api/v1/message \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "channel_id": "YOUR_CHANNEL_ID",
    "content": "Hello from WaddleBot!"
  }'
```

Response:
```json
{
  "success": true,
  "message_id": "123456789987654321"
}
```

## Docker Compose Configuration

The included docker-compose.yml includes:

- discord_action_module (Python service)
- PostgreSQL database
- Redis (optional credential caching)

```yaml
version: '3.8'
services:
  discord_action_module:
    build: .
    environment:
      DISCORD_BOT_TOKEN: ${DISCORD_BOT_TOKEN}
      MODULE_SECRET_KEY: ${MODULE_SECRET_KEY}
      DATABASE_URL: postgresql://waddlebot:password@postgres:5432/waddlebot
      GRPC_PORT: 50051
      REST_PORT: 8070
    ports:
      - "50051:50051"
      - "8070:8070"
    depends_on:
      - postgres

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: waddlebot
      POSTGRES_USER: waddlebot
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

## Logging

View real-time logs:
```bash
docker-compose logs -f discord_action_module
```

View specific module logs:
```bash
docker-compose exec discord_action_module tail -f /var/log/waddlebotlog/discord_action_module.log
```

## Configuration

See CONFIGURATION.md for all environment variables and their meanings.

Key variables:
- DISCORD_BOT_TOKEN - Discord bot authentication token
- DATABASE_URL - PostgreSQL connection string
- GRPC_PORT - gRPC server port (default: 50051)
- REST_PORT - REST API port (default: 8070)
- MODULE_SECRET_KEY - JWT signing key
- JWT_EXPIRATION_SECONDS - Token expiration time
- LOG_LEVEL - Logging level (DEBUG, INFO, WARNING, ERROR)

## Health Check Endpoint

Health endpoint with authentication check:
```bash
curl http://localhost:8070/health
```

Returns:
- status: "healthy" or "unhealthy"
- module: module name
- version: module version
- timestamp: current timestamp
- config: configuration summary (no secrets)

If status is "unhealthy", check:
1. Database connectivity (PostgreSQL running?)
2. Discord bot token validity
3. Network connectivity
4. Logs for error details

## Common Tasks

### Send Message with Embed
```bash
curl -X POST http://localhost:8070/api/v1/embed \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{
    "channel_id": "123456789",
    "embed": {
      "title": "Embed Title",
      "description": "Embed description",
      "color": 3447003,
      "fields": [
        {
          "name": "Field Name",
          "value": "Field value",
          "inline": false
        }
      ]
    }
  }'
```

### Add Emoji Reaction
```bash
curl -X POST http://localhost:8070/api/v1/reaction \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{
    "channel_id": "123456789",
    "message_id": "987654321",
    "emoji": "👍"
  }'
```

### Create Webhook
```bash
curl -X POST http://localhost:8070/api/v1/webhook \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{
    "channel_id": "123456789",
    "name": "WaddleBot Webhook"
  }'
```

### Send via Webhook
```bash
curl -X POST http://localhost:8070/api/v1/webhook/send \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{
    "webhook_url": "https://discord.com/api/webhooks/...",
    "content": "Message via webhook"
  }'
```

## Troubleshooting

**Module fails to start:**
- Check DATABASE_URL is valid: `psql $DATABASE_URL`
- Check DISCORD_BOT_TOKEN is valid
- Check logs: `docker-compose logs discord_action_module`

**Health check fails:**
- Database connectivity: Check PostgreSQL is running
- Discord token: Verify bot token in Discord Developer Portal
- Logs show permission denied: Check bot has correct permissions in Discord server

**Messages not sending:**
- Bot not in server: Invite bot with correct permissions
- Channel permissions: Bot must have "Send Messages" permission
- Rate limited: Check rate limit settings in CONFIGURATION.md

See TROUBLESHOOTING.md for more detailed error resolution.
