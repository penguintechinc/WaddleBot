# Combined Webhook Receiver Service

A unified Quart application that consolidates webhook receivers for Slack, Microsoft Teams, Mattermost, and Google Chat into a single service running on port 8100.

## Service Structure

```
trigger-webhooks/
├── app.py                  # Main combined Quart application
├── requirements.txt        # Union of all dependencies
├── Dockerfile             # Multi-stage build
├── slack_module/          # Slack receiver (url_prefix: /slack)
├── teams_module/          # Teams receiver (url_prefix: /teams)
├── mattermost_module/     # Mattermost receiver (url_prefix: /mattermost)
└── googlechat_module/     # Google Chat receiver (url_prefix: /googlechat)
```

## URL Prefixes by Platform

Each platform maintains its own URL prefix and routes:

### Slack (prefix: `/slack`)
- `POST /slack/events` - Slack Events API
- `POST /slack/commands` - Slash commands
- `POST /slack/actions` - Interactive components
- `POST /slack/shortcuts` - Shortcuts

### Teams (prefix: `/teams`)
- `POST /teams/api/messages` - Microsoft Bot Framework webhook

### Mattermost (prefix: `/mattermost`)
- `POST /mattermost/events` - Webhook events
- `POST /mattermost/commands` - Slash commands

### Google Chat (prefix: `/googlechat`)
- `POST /googlechat/events` - Google Chat Events API

### Internal Relay Routes (prefix: `/internal`)
- `POST /internal/slack/relay` - Relay to Slack
- `POST /internal/teams/relay` - Relay to Teams
- `POST /internal/mattermost/relay` - Relay to Mattermost
- `POST /internal/googlechat/relay` - Relay to Google Chat

## Health & Status

- `GET /healthz` - Health check endpoint
- `GET /metrics` - Prometheus metrics
- `GET /api/v1/status` - Combined service status

## Environment Variables

All environment variables from the original receiver modules are supported:

**Slack:**
- `SLACK_BOT_TOKEN`
- `SLACK_SIGNING_SECRET`
- `SLACK_APP_TOKEN`
- `USE_SOCKET_MODE`

**Teams:**
- `TEAMS_APP_ID`
- `TEAMS_APP_PASSWORD`
- `TEAMS_TENANT_ID`

**Mattermost:**
- `MATTERMOST_URL`
- `MATTERMOST_BOT_TOKEN`
- `MATTERMOST_WEBHOOK_SECRET`

**Google Chat:**
- `GOOGLE_CHAT_SERVICE_ACCOUNT_KEY`
- `GOOGLE_CHAT_PROJECT_ID`

**Common:**
- `DATABASE_URL` - Shared database connection string
- `ROUTER_API_URL` - Hub router service URL
- `LOG_LEVEL` - Logging level

## Building & Running

### Docker Build
```bash
docker build -t trigger-webhooks:latest .
```

### Docker Run
```bash
docker run -p 8100:8100 \
  -e DATABASE_URL="postgresql://user:pass@localhost/waddlebot" \
  -e SLACK_BOT_TOKEN="xoxb-..." \
  -e SLACK_SIGNING_SECRET="..." \
  trigger-webhooks:latest
```

### Local Development
```bash
pip install -r requirements.txt
python3 app.py
```

## Features

Each platform receiver is independently configurable:
- If credentials are missing, that receiver is gracefully disabled
- Startup logs indicate which receivers are active/skipped
- Combined status endpoint shows real-time receiver connectivity
- All routing, event handling, and relay logic preserved from original modules

## Notes

- All 4 module directories (`slack_module`, `teams_module`, `mattermost_module`, `googlechat_module`) are required at runtime
- Shared libraries are loaded from the original receiver location: `trigger/receiver/libs`
- Each module maintains its own `config.py` for platform-specific settings
- Database is shared across all receivers (single DAL instance)
