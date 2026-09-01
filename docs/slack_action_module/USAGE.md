# Slack Action Module - Usage Guide

## Docker Setup

### Building the Container

```bash
# From repository root
docker build -f action/pushing/slack_action_module/Dockerfile \
  -t waddlebot/slack-action-module:latest \
  action/pushing/slack_action_module/

# Or with version tag
docker build -f action/pushing/slack_action_module/Dockerfile \
  -t waddlebot/slack-action-module:1.0.0 \
  action/pushing/slack_action_module/
```

### Docker Compose Configuration

Add to your `docker-compose.yml`:

```yaml
slack-action-module:
  image: waddlebot/slack-action-module:latest
  container_name: slack-action-module
  ports:
    - "8071:8071"  # REST API
    - "50052:50052" # gRPC
  environment:
    # Slack Configuration
    SLACK_BOT_TOKEN: ${SLACK_BOT_TOKEN}
    SLACK_APP_TOKEN: ${SLACK_APP_TOKEN}

    # Server Configuration
    REST_PORT: 8071
    GRPC_PORT: 50052

    # Database Configuration
    DATABASE_URL: postgresql://user:password@postgres:5432/waddlebot
    REDIS_URL: redis://redis:6379/0

    # Security
    MODULE_SECRET_KEY: ${MODULE_SECRET_KEY}
    JWT_ALGORITHM: HS256
    JWT_EXPIRY_SECONDS: 3600

    # Performance
    MAX_CONCURRENT_REQUESTS: 100
    REQUEST_TIMEOUT: 30
    GRPC_MAX_WORKERS: 10

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
    test: ["CMD", "curl", "-f", "http://localhost:8071/health"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 10s
```

### Running the Container

```bash
# Development mode
docker-compose up action-slack

# Production mode (background)
docker-compose up -d slack-action-module

# View logs
docker-compose logs -f action-slack

# Stop container
docker-compose down action-slack
```

## SLACK_BOT_TOKEN Setup

### Create Slack App

1. Go to https://api.slack.com/apps
2. Click "Create New App" → "From scratch"
3. Enter app name: `WaddleBot`
4. Select your workspace
5. Click "Create App"

### Grant OAuth Scopes

1. In left sidebar, click "OAuth & Permissions"
2. Under "Scopes" → "Bot Token Scopes", add:
   - `chat:write`
   - `chat:write.public`
   - `emoji:read`
   - `files:write`
   - `channels:manage`
   - `groups:write`
   - `groups:manage`
   - `users:read`
   - `views:open`
   - `reactions:write`
   - `reactions:read`

### Install App to Workspace

1. At top of "OAuth & Permissions" page, click "Install to Workspace"
2. Review permissions, then click "Allow"
3. Copy the **Bot User OAuth Token** (starts with `xoxb-`)
4. Store in `.env` file as `SLACK_BOT_TOKEN=xoxb-...`

### Verify Installation

```bash
# Test the token
curl -X POST https://slack.com/api/auth.test \
  -H "Authorization: Bearer xoxb-YOUR-TOKEN-HERE"

# Response should include: "ok": true, "user_id": "U...", "team_id": "T..."
```

## Workspace Scopes Required

The following scopes must be granted for all features to work:

| Scope | Purpose |
|-------|---------|
| `chat:write` | Send messages in channels |
| `chat:write.public` | Send messages in public channels |
| `files:write` | Upload files to channels |
| `emoji:read` | Read emoji information and reactions |
| `channels:manage` | Create channels and manage settings |
| `groups:write` | Write to private channels (groups) |
| `groups:manage` | Manage private channel membership |
| `users:read` | Retrieve user information |
| `views:open` | Open modals and interactive components |
| `reactions:write` | Add and remove emoji reactions |
| `reactions:read` | Read reaction information |

## Health Check

### REST Endpoint

```bash
# Check module health
curl http://localhost:8071/health

# Response (200 OK):
{
  "status": "healthy",
  "module": "slack_action_module",
  "version": "1.0.0",
  "grpc_port": 50052,
  "rest_port": 8071
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
docker-compose ps action-slack

# Should show: healthy status after 10-30 seconds
```

## Send Message Example

### Basic Text Message

```bash
# Generate JWT token first
TOKEN=$(curl -s -X POST http://localhost:8071/api/v1/token \
  -H "Content-Type: application/json" \
  -d '{
    "api_key": "your-module-secret-key",
    "client_id": "test-client"
  }' | jq -r '.token')

# Send message
curl -X POST http://localhost:8071/api/v1/message \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "community_id": "acme-community",
    "channel_id": "C01234567",
    "text": "Hello from WaddleBot!"
  }'

# Response (200 OK):
{
  "success": true,
  "message_ts": "1234567890.123456",
  "channel_id": "C01234567"
}
```

### Message to Thread

```bash
curl -X POST http://localhost:8071/api/v1/message \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "community_id": "acme-community",
    "channel_id": "C01234567",
    "text": "Reply in thread",
    "thread_ts": "1234567890.123456"
  }'
```

## Block Kit Example

### Rich Message with Blocks

```bash
curl -X POST http://localhost:8071/api/v1/message \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "community_id": "acme-community",
    "channel_id": "C01234567",
    "text": "Fallback text for clients without Block Kit support",
    "blocks": [
      {
        "type": "header",
        "text": {
          "type": "plain_text",
          "text": "WaddleBot Notification",
          "emoji": true
        }
      },
      {
        "type": "section",
        "text": {
          "type": "mrkdwn",
          "text": "*Event Title*\nSomething important happened in your community."
        }
      },
      {
        "type": "divider"
      },
      {
        "type": "section",
        "fields": [
          {
            "type": "mrkdwn",
            "text": "*Severity:*\nCritical"
          },
          {
            "type": "mrkdwn",
            "text": "*Status:*\nResolved"
          }
        ]
      },
      {
        "type": "actions",
        "elements": [
          {
            "type": "button",
            "text": {
              "type": "plain_text",
              "text": "View Details",
              "emoji": true
            },
            "value": "click_me_123",
            "url": "https://example.com/details"
          },
          {
            "type": "button",
            "text": {
              "type": "plain_text",
              "text": "Dismiss",
              "emoji": true
            },
            "value": "dismiss"
          }
        ]
      }
    ]
  }'
```

### Button and Interactive Elements

```bash
# Message with buttons and dropdown
curl -X POST http://localhost:8071/api/v1/message \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "community_id": "acme-community",
    "channel_id": "C01234567",
    "blocks": [
      {
        "type": "section",
        "text": {
          "type": "mrkdwn",
          "text": "What would you like to do?"
        }
      },
      {
        "type": "actions",
        "elements": [
          {
            "type": "static_select",
            "placeholder": {
              "type": "plain_text",
              "text": "Select an action",
              "emoji": true
            },
            "options": [
              {
                "text": {
                  "type": "plain_text",
                  "text": "Approve",
                  "emoji": true
                },
                "value": "approve"
              },
              {
                "text": {
                  "type": "plain_text",
                  "text": "Reject",
                  "emoji": true
                },
                "value": "reject"
              },
              {
                "text": {
                  "type": "plain_text",
                  "text": "Review",
                  "emoji": true
                },
                "value": "review"
              }
            ]
          }
        ]
      }
    ]
  }'
```

## Ephemeral Message

Send a message visible only to a specific user:

```bash
curl -X POST http://localhost:8071/api/v1/ephemeral \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "community_id": "acme-community",
    "channel_id": "C01234567",
    "user_id": "U01234567",
    "text": "This message is only visible to you!"
  }'
```

## Update Message

```bash
# Update existing message
curl -X PUT http://localhost:8071/api/v1/message/C01234567/1234567890.123456 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "community_id": "acme-community",
    "text": "Updated message text"
  }'
```

## Delete Message

```bash
curl -X DELETE http://localhost:8071/api/v1/message/C01234567/1234567890.123456 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"community_id": "acme-community"}'
```

## Add Reaction

```bash
curl -X POST http://localhost:8071/api/v1/reaction \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "community_id": "acme-community",
    "channel_id": "C01234567",
    "ts": "1234567890.123456",
    "emoji": "thumbsup"
  }'
```

## Remove Reaction

```bash
curl -X DELETE http://localhost:8071/api/v1/reaction \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "community_id": "acme-community",
    "channel_id": "C01234567",
    "ts": "1234567890.123456",
    "emoji": "thumbsup"
  }'
```

## Upload File

```bash
# Encode file as base64 first
FILE_CONTENT=$(base64 -w0 < /path/to/file.pdf)

curl -X POST http://localhost:8071/api/v1/file \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"community_id\": \"acme-community\",
    \"channel_id\": \"C01234567\",
    \"file_content_base64\": \"$FILE_CONTENT\",
    \"filename\": \"document.pdf\",
    \"title\": \"Important Document\"
  }"
```

## Create Channel

```bash
curl -X POST http://localhost:8071/api/v1/channel \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "community_id": "acme-community",
    "name": "team-announcements",
    "is_private": false
  }'
```

## Invite Users to Channel

```bash
curl -X POST http://localhost:8071/api/v1/channel/invite \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "community_id": "acme-community",
    "channel_id": "C01234567",
    "user_ids": ["U01234567", "U02345678"]
  }'
```

## Set Channel Topic

```bash
curl -X PUT http://localhost:8071/api/v1/channel/topic \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "community_id": "acme-community",
    "channel_id": "C01234567",
    "topic": "Team announcements and important updates"
  }'
```

## Open Modal

```bash
curl -X POST http://localhost:8071/api/v1/modal \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "community_id": "acme-community",
    "trigger_id": "13345224609.619783",
    "view": {
      "type": "modal",
      "callback_id": "view_callback_id",
      "title": {
        "type": "plain_text",
        "text": "My Modal",
        "emoji": true
      },
      "submit": {
        "type": "plain_text",
        "text": "Submit",
        "emoji": true
      },
      "close": {
        "type": "plain_text",
        "text": "Cancel",
        "emoji": true
      },
      "blocks": [
        {
          "type": "input",
          "element": {
            "type": "plain_text_input"
          },
          "label": {
            "type": "plain_text",
            "text": "Label",
            "emoji": true
          }
        }
      ]
    }
  }'
```

## Get Action History

```bash
# Get last 50 actions
curl http://localhost:8071/api/v1/history/acme-community?limit=50 \
  -H "Authorization: Bearer $TOKEN"

# Response:
{
  "history": [
    {
      "id": 1,
      "action_type": "send_message",
      "success": true,
      "error": null,
      "created_at": "2024-01-15T10:30:00Z"
    },
    {
      "id": 2,
      "action_type": "add_reaction",
      "success": true,
      "error": null,
      "created_at": "2024-01-15T10:31:00Z"
    }
  ]
}
```
