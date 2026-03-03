# Mattermost Integration

This guide covers the setup and configuration of WaddleBot's Mattermost integration, enabling seamless bot communication, interactive messages, and workflow automation within Mattermost workspaces.

## Overview

The Mattermost integration allows WaddleBot to:
- Send messages to channels and direct messages
- Create and respond to slash commands
- Handle interactive button clicks and message actions
- Manage bot mentions and notifications
- Perform channel and user operations
- Maintain presence and status information

## Prerequisites

Before configuring Mattermost integration, you'll need:
- Mattermost server (v6.0 or later)
- System Administrator access to your Mattermost workspace
- WaddleBot deployment accessible from your Mattermost server
- Mattermost desktop or web client for testing

## Mattermost Server Setup

### Step 1: Enable Developer/Bot Account Creation

1. Log in to Mattermost as a System Administrator
2. Go to **System Console** → **Developer**
3. Ensure the following are enabled:
   - **Enable Developer Mode**: ON
   - **Enable BOT Account Creation**: ON
   - **Enable Custom Slash Commands**: ON
4. Save changes

### Step 2: Create Bot Account

1. Go to **Settings** → **Integrations** (or use System Console)
2. Select **Bot Accounts**
3. Click "Create New Bot Account"
4. Configure:
   - **Username**: `waddlebot`
   - **Display Name**: `WaddleBot`
   - **Role**: Select "Can manage slash commands and incoming webhooks"
   - **Icon**: Upload WaddleBot logo if desired
5. Click "Create Bot Account"
6. **Save the Bot Token** (displayed once - copy and store securely)

### Step 3: Grant Bot Permissions

Add the bot user to channels where it should operate:

1. Create or select a channel (e.g., `#waddlebot-testing`)
2. Click channel name → "Add Members"
3. Search for and add `@waddlebot`
4. Configure bot permissions if needed:
   - Allow message posting
   - Allow reactions
   - Allow message updates

## Webhook Configuration

### Incoming Webhooks (Server → WaddleBot)

Create incoming webhooks for your Mattermost server to send events to WaddleBot:

1. Go to **Main Menu** → **Integrations** → **Incoming Webhooks**
2. Click "Add Incoming Webhook"
3. Configure:
   - **Title**: "WaddleBot Events"
   - **Description**: "Webhook for WaddleBot workflow events"
   - **Channel**: Select channel or leave for Direct Messages
   - **Locked to Team**: Leave unchecked for all teams
   - **Display Name**: "WaddleBot"
   - **Profile Picture**: Upload WaddleBot icon
4. Click "Save"
5. **Copy the Webhook URL** (begins with `https://...`)

### Outgoing Webhooks (WaddleBot → Server)

Create outgoing webhooks to send events from WaddleBot to Mattermost:

1. Go to **Main Menu** → **Integrations** → **Outgoing Webhooks**
2. Click "Add Outgoing Webhook"
3. Configure:
   - **Title**: "WaddleBot Outgoing"
   - **Description**: "WaddleBot to Mattermost events"
   - **Content Type**: "application/json"
   - **Trigger Words**: Leave empty to trigger on all posts
   - **Trigger When**: Select "A post is made"
   - **Callback URL**: `https://{your-domain}/mattermost/webhooks`
4. Click "Save"
5. **Copy the Token** for validation

## Slash Commands Configuration

Create custom slash commands for interactive workflows:

1. Go to **Main Menu** → **Integrations** → **Slash Commands**
2. Click "Add Slash Command"
3. Configure for each command (e.g., `/waddlebot-action`):
   - **Command Trigger Word**: `/waddlebot-action`
   - **Request URL**: `https://{your-domain}/mattermost/slash-commands`
   - **Request Method**: "POST"
   - **Response Username**: "WaddleBot"
   - **Response Icon**: Upload WaddleBot icon
   - **Autocomplete**: Enable if desired
   - **Autocomplete Hint**: `[action-name]`
   - **Autocomplete Description**: "Execute a WaddleBot action"
4. Click "Save"

## Message Actions Configuration

Create message action menus for quick interactions:

1. Go to **System Console** → **Integrations** → **Message Actions**
2. Add custom message actions:
   - **Action ID**: `waddlebot_approve`
   - **Action Name**: "Approve with WaddleBot"
   - **Trigger**: "Post Menu"
   - **Integration URL**: `https://{your-domain}/mattermost/actions`
3. Save and test by right-clicking a message

## Environment Variables

Configure the following environment variables in your deployment:

| Variable | Description | Example |
|----------|-------------|---------|
| `MATTERMOST_URL` | Base URL of your Mattermost server | `https://mattermost.company.com` |
| `MATTERMOST_BOT_TOKEN` | Bot account token from Step 2 above | (generated token) |
| `MATTERMOST_WEBHOOK_SECRET` | Secret for webhook validation | (generate random 32+ char string) |
| `MATTERMOST_INCOMING_WEBHOOK_URL` | Incoming webhook URL | `https://.../hooks/xxxxx` |
| `REST_PORT` | Port for Mattermost module REST API | `8075` |
| `GRPC_PORT` | Port for Mattermost module gRPC server | `50058` |
| `DATABASE_URL` | PostgreSQL connection string | `postgres://user:pass@host:5432/db` |
| `REDIS_URL` | Redis connection for caching | `redis://localhost:6379/0` |
| `LOG_LEVEL` | Logging verbosity | `INFO`, `DEBUG`, `WARNING`, `ERROR` |
| `MATTERMOST_REQUEST_TIMEOUT` | HTTP request timeout in seconds | `30` |

## Message Formatting

### Simple Text Messages

```json
{
  "channel": "channel-name",
  "text": "This is a message from WaddleBot"
}
```

### Message with Attachments

```json
{
  "channel": "channel-name",
  "text": "Action notification",
  "attachments": [
    {
      "fallback": "Action available",
      "color": "#FF9800",
      "title": "Approval Required",
      "title_link": "https://example.com/action/123",
      "text": "User action requires approval",
      "actions": [
        {
          "type": "button",
          "name": "Approve",
          "integration": {
            "url": "https://your-domain/mattermost/actions/approve",
            "context": {
              "action_id": "123"
            }
          }
        },
        {
          "type": "button",
          "name": "Reject",
          "integration": {
            "url": "https://your-domain/mattermost/actions/reject",
            "context": {
              "action_id": "123"
            }
          }
        }
      ]
    }
  ]
}
```

### Slash Command Response

```json
{
  "response_type": "in_channel",
  "text": "Command executed successfully",
  "attachments": [
    {
      "color": "good",
      "title": "Result",
      "text": "Operation completed with status: SUCCESS"
    }
  ]
}
```

## Testing the Integration

### Test Bot Connection

1. Create a Direct Message with `@waddlebot`
2. Send: `@waddlebot help`
3. Verify bot responds (if help command is implemented)

### Test Slash Command

1. In any channel, type `/waddlebot-action test-action`
2. Verify command executes and returns response
3. Check bot responds in the channel

### Test Message Actions

1. Post a message in a channel
2. Right-click or hover on the message
3. Look for "Approve with WaddleBot" action
4. Click to execute and verify response

### Test Webhooks

Test incoming webhook manually:

```bash
curl -X POST https://mattermost-server/hooks/xxxxx \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "testing",
    "text": "Test message from WaddleBot",
    "username": "waddlebot"
  }'
```

## Troubleshooting

### Bot Not Responding

**Problem**: Bot doesn't acknowledge messages or commands

**Solutions**:
1. Verify bot account is active: **System Console** → **Users** → find `waddlebot` → confirm active
2. Check bot is added to the channel
3. Verify `MATTERMOST_BOT_TOKEN` is set correctly
4. Check module logs for connection errors

### Webhook Validation Failures

**Problem**: Webhooks rejected or validation fails

**Solutions**:
1. Verify `MATTERMOST_WEBHOOK_SECRET` is set and consistent
2. Check webhook URL is accessible from Mattermost server
3. Ensure HTTPS is configured with valid certificate
4. Check firewall rules allow communication

### Message Formatting Issues

**Problem**: Messages display incorrectly or attachments don't render

**Solutions**:
1. Validate JSON structure against Mattermost API docs
2. Test with simple text message first, then add attachments
3. Check color codes are valid hex values
4. Ensure URLs are properly formatted and accessible

### Rate Limiting

**Problem**: Mattermost returns rate limit errors

**Solutions**:
1. Reduce message frequency
2. Implement backoff retry logic (module does this by default)
3. Contact Mattermost admin to adjust rate limit settings if needed

## Security Considerations

1. **Token Security**: Store `MATTERMOST_BOT_TOKEN` securely - never commit to version control
2. **Webhook Validation**: Always validate webhook signatures using the webhook secret
3. **HTTPS Only**: Ensure all URLs use HTTPS with valid certificates
4. **User Context**: Include user IDs in requests to maintain proper audit trail
5. **Command Validation**: Validate slash command parameters to prevent injection attacks
6. **Data Protection**: Ensure sensitive data is not logged or exposed in error messages

## Rate Limiting and Performance

Mattermost enforces rate limits to prevent abuse:
- **Webhooks**: 300 requests per minute per webhook
- **API**: 180 requests per minute per token by default
- **Slash Commands**: Subject to webhook rate limits

The Mattermost action module implements intelligent request batching and exponential backoff to work within these limits.

## Additional Resources

- [Mattermost Integration Documentation](https://docs.mattermost.com/integrate/webhooks/incoming-webhooks.html)
- [Mattermost Bot Documentation](https://developers.mattermost.com/integrate/admin-guide/)
- [Mattermost API Reference](https://api.mattermost.com/)
- [Slash Commands Guide](https://docs.mattermost.com/developer/slash-commands.html)
- [Message Actions Guide](https://docs.mattermost.com/developer/message-actions.html)
