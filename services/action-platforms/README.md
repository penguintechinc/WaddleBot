# Action Platforms Service

Combined microservice that consolidates 6 platform action modules into a single Quart application on port 8102.

## Modules Included

1. **Slack Action Module** (port 8102 → `/slack/api/v1`)
   - Message delivery with rich formatting (blocks)
   - Ephemeral messages
   - Message updates
   - Thread support

2. **Teams Action Module** (port 8102 → `/teams/api/v1`)
   - Message delivery with adaptive cards
   - Ephemeral messages
   - Thread support
   - Microsoft Teams API integration

3. **Mattermost Action Module** (port 8102 → `/mattermost/api/v1`)
   - Message delivery with attachments
   - Ephemeral messages
   - Metadata support
   - Mattermost REST API integration

4. **Google Chat Action Module** (port 8102 → `/googlechat/api/v1`)
   - Message delivery with rich card formatting
   - Space (channel) creation
   - Thread support
   - Google Chat API integration

5. **Twitch Action Module** (port 8102 → `/twitch/api/v1`)
   - Action execution (raids, timeouts, slow mode, etc.)
   - OAuth token management
   - Token refresh and storage
   - Twitch API integration

6. **YouTube Action Module** (port 8102 → `/youtube/api/v1`)
   - Live chat message delivery
   - Chat message deletion
   - Video title updates
   - YouTube Data API integration

## Architecture

```
/app/
  app.py                        # Combined Quart entry point
  config.py                     # Unified configuration (if present)
  requirements.txt              # Merged dependencies
  Dockerfile                    # Multi-stage build
  slack_action_module/          # Slack service code
  teams_action_module/          # Teams service code
  mattermost_action_module/     # Mattermost service code
  googlechat_action_module/     # Google Chat service code
  twitch_action_module/         # Twitch service code
  youtube_action_module/        # YouTube service code
```

## API Endpoints

### Health & Status
- `GET /health` - Health check with active platforms

### Slack Endpoints
- `POST /slack/api/v1/message` - Send message to Slack
- `POST /slack/api/v1/ephemeral` - Send ephemeral message to Slack
- `PUT /slack/api/v1/message/<channel_id>/<ts>` - Update Slack message

### Teams Endpoints
- `POST /teams/api/v1/message` - Send message to Teams
- `POST /teams/api/v1/ephemeral` - Send ephemeral message to Teams

### Mattermost Endpoints
- `POST /mattermost/api/v1/message` - Send message to Mattermost
- `POST /mattermost/api/v1/ephemeral` - Send ephemeral message to Mattermost

### Google Chat Endpoints
- `POST /googlechat/api/v1/message` - Send message to Google Chat
- `POST /googlechat/api/v1/space` - Create space in Google Chat

### Twitch Endpoints
- `POST /twitch/api/v1/actions/execute` - Execute Twitch action
- `POST /twitch/api/v1/tokens/store` - Store Twitch OAuth token

### YouTube Endpoints
- `POST /youtube/api/v1/chat/send` - Send chat message to YouTube live chat
- `POST /youtube/api/v1/chat/delete` - Delete YouTube live chat message
- `PUT /youtube/api/v1/video/title` - Update YouTube video title

## Environment Variables

```bash
# Service
MODULE_PORT=8102
MODULE_HOST=0.0.0.0

# Slack
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
SLACK_MODULE_SECRET_KEY=your-slack-secret

# Teams
TEAMS_APP_ID=your-teams-app-id
TEAMS_APP_PASSWORD=your-teams-app-password
TEAMS_MODULE_SECRET_KEY=your-teams-secret

# Mattermost
MATTERMOST_URL=https://mattermost.example.com
MATTERMOST_BOT_TOKEN=your-mattermost-bot-token
MATTERMOST_MODULE_SECRET_KEY=your-mattermost-secret

# Google Chat
GOOGLE_CHAT_SERVICE_ACCOUNT_KEY={"type": "service_account", ...}
GOOGLECHAT_MODULE_SECRET_KEY=your-googlechat-secret

# Twitch
TWITCH_CLIENT_ID=your-twitch-client-id
TWITCH_CLIENT_SECRET=your-twitch-client-secret
TWITCH_MODULE_SECRET_KEY=your-twitch-secret

# YouTube
YOUTUBE_SERVICE_ACCOUNT_KEY={"type": "service_account", ...}
YOUTUBE_MODULE_SECRET_KEY=your-youtube-secret

# Database
DATABASE_URL=sqlite:action_platforms.db
DB_POOL_SIZE=10

# Logging
LOG_LEVEL=INFO
```

## Building

### Local Build
```bash
docker build -t action-platforms:latest .
```

### Run Locally
```bash
docker run -d \
  -p 8102:8102 \
  -e SLACK_BOT_TOKEN=xoxb-your-token \
  -e TEAMS_APP_ID=your-teams-id \
  -e TEAMS_APP_PASSWORD=your-teams-password \
  -e MATTERMOST_URL=https://mattermost.example.com \
  -e MATTERMOST_BOT_TOKEN=your-mattermost-token \
  -e GOOGLE_CHAT_SERVICE_ACCOUNT_KEY='{"type":"service_account",...}' \
  -e TWITCH_CLIENT_ID=your-twitch-id \
  -e TWITCH_CLIENT_SECRET=your-twitch-secret \
  -e YOUTUBE_SERVICE_ACCOUNT_KEY='{"type":"service_account",...}' \
  action-platforms:latest
```

## Ports

- **8102** - HTTP REST API (all 6 platform modules)

## JWT Authentication

All non-health endpoints require JWT bearer token authentication via the `Authorization` header:

```bash
curl -H "Authorization: Bearer eyJhbGciOiJIUzI1NiI..." \
  http://localhost:8102/slack/api/v1/message
```

The service validates tokens against each platform module's `MODULE_SECRET_KEY`. If a token is valid for any platform, the request is authorized.

Health endpoint is exempt:
```bash
curl http://localhost:8102/health
```

## Database Schema

The service initializes database tables for all 6 platform modules. Uses PyDAL with `migrate=False` (schema via Alembic only).

## Logging

Uses structured logging to stdout:
- All startup/shutdown events logged
- JWT validation failures logged
- Per-platform initialization status tracked
- Request errors logged with full context

## Service Initialization

Each platform service initializes independently on startup. If a platform's configuration is missing or invalid, the service logs a warning but continues (graceful degradation). Only platforms with successfully initialized services will respond to requests.

Check the `/health` endpoint to see which platforms are active:
```bash
curl http://localhost:8102/health
```

Response includes `active_platforms` list showing all successfully initialized platform services.
