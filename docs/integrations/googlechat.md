# Google Chat Integration

This guide covers the setup and configuration of WaddleBot's Google Chat integration, enabling seamless bot communication, interactive cards, and workflow automation within Google Workspace.

## Overview

The Google Chat integration allows WaddleBot to:
- Send messages and interactive cards to Chat spaces and direct messages
- Handle card button clicks and form submissions
- Receive and respond to slash commands
- Manage thread conversations
- Publish real-time updates using Google Cloud Pub/Sub
- Integrate with Google Workspace APIs

## Prerequisites

Before configuring Google Chat integration, you'll need:
- Google Cloud Project with billing enabled
- Google Workspace administrator access
- Google Cloud SDK installed locally
- Service account with appropriate permissions
- Google Chat API enabled

## Google Cloud Project Setup

### Step 1: Create or Select a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click the project dropdown at the top
3. Click "New Project"
4. Configure:
   - **Project name**: `waddlebot-chat`
   - **Organization**: Select your organization
   - **Location**: Select appropriate region
5. Click "Create"

### Step 2: Enable Required APIs

1. In the Cloud Console, go to **APIs & Services** → **Library**
2. Search for and enable these APIs:
   - **Google Chat API**
   - **Cloud Pub/Sub API**
   - **Cloud Logging API**
   - **Cloud Resource Manager API**
3. For each API, click the API name, then click "Enable"

### Step 3: Create Service Account

1. Go to **APIs & Services** → **Service Accounts**
2. Click "Create Service Account"
3. Configure:
   - **Service account name**: `waddlebot-chat-bot`
   - **Service account ID**: auto-populated
   - **Description**: "WaddleBot Google Chat Integration"
4. Click "Create and Continue"
5. Grant roles:
   - **Primary role**: "Basic → Editor" (for development; restrict in production)
   - **Additional roles**:
     - "Pub/Sub Editor" (for event streaming)
     - "Logs Writer" (for logging)
6. Click "Continue"
7. Click "Create Key"
8. Select **JSON** as key type
9. Click "Create" to download the service account key
10. **Save the JSON file securely** - you'll need it for environment configuration

### Step 4: Configure Service Account Permissions

1. In IAM & Admin → IAM, find your service account
2. Add these additional roles:
   - `roles/chat.serviceAgent` (Chat Bot)
   - `roles/pubsub.editor` (Pub/Sub)

## Google Chat App Registration

### Step 1: Create Chat App Manifest

Create a `app.yaml` file to register your bot with Google Chat:

```yaml
apiVersion: chat.googleapis.com/v1
kind: ChatApp
metadata:
  name: waddlebot
displayName: WaddleBot
description: Automation and workflow bot for Google Chat
avatarUrl: https://your-domain/assets/waddlebot-logo.png
functions:
  - name: onMessage
    description: Handles incoming messages
  - name: onCardClick
    description: Handles interactive card button clicks
  - name: onSlashCommand
    description: Handles slash commands
homepageUrl: https://your-domain
supportUrl: https://your-domain/support
```

### Step 2: Register the App

1. Go to [Google Chat Marketplace](https://chat.google.com/u/0/marketplacebeta)
2. Click "Create App"
3. Enter details from your manifest
4. Set **App Homepage**: `https://your-domain/googlechat`
5. Set **Configuration URL**: `https://your-domain/googlechat/config`
6. Configure permissions needed:
   - "See, create, edit, and permanently delete all Chat messages"
   - "View spaces, tabs, and messages in Chat"
   - "Create, update, and delete spaces in Chat"
7. Review and publish to workspace

## Pub/Sub Topic Configuration

### Step 1: Create Pub/Sub Topic

1. Go to **Pub/Sub** → **Topics**
2. Click "Create Topic"
3. Configure:
   - **Name**: `waddlebot-chat-events`
   - **Retention duration**: 7 days
4. Click "Create Topic"

### Step 2: Create Subscription

1. Open your topic
2. Click "Create Subscription"
3. Configure:
   - **Subscription ID**: `waddlebot-chat-sub`
   - **Delivery type**: "Pull"
   - **Expiration policy**: Never (recommended)
   - **Dead letter policy**: Create a dead-letter topic if desired
4. Click "Create Subscription"

### Step 3: Create Pub/Sub Push Subscription (Optional)

For real-time webhook delivery instead of polling:

1. Click "Create Subscription"
2. Configure:
   - **Subscription ID**: `waddlebot-chat-push`
   - **Delivery type**: "Push"
   - **Push endpoint**: `https://your-domain/googlechat/webhook`
   - **Authentication**: Service Account (select your service account)
3. Click "Create Subscription"

## Environment Variables

Configure the following environment variables in your deployment:

| Variable | Description | Example |
|----------|-------------|---------|
| `GOOGLE_CHAT_SERVICE_ACCOUNT_KEY` | Base64-encoded service account JSON | (see below) |
| `GOOGLE_CHAT_PROJECT_ID` | Google Cloud Project ID | `waddlebot-chat-xyz` |
| `GOOGLE_CHAT_PUBSUB_TOPIC` | Pub/Sub topic for events | `projects/xyz/topics/waddlebot-chat-events` |
| `GOOGLE_CHAT_PUBSUB_SUBSCRIPTION` | Pub/Sub subscription ID | `waddlebot-chat-sub` |
| `REST_PORT` | Port for Google Chat module REST API | `8076` |
| `GRPC_PORT` | Port for Google Chat module gRPC server | `50059` |
| `DATABASE_URL` | PostgreSQL connection string | `postgres://user:pass@host:5432/db` |
| `REDIS_URL` | Redis connection for caching | `redis://localhost:6379/0` |
| `LOG_LEVEL` | Logging verbosity | `INFO`, `DEBUG`, `WARNING`, `ERROR` |

### Encoding Service Account Key

Encode your service account JSON for the environment variable:

```bash
cat /path/to/service-account-key.json | base64 -w 0 > key.b64
export GOOGLE_CHAT_SERVICE_ACCOUNT_KEY=$(cat key.b64)
```

Then add to your deployment configuration.

## Message Formatting

### Simple Text Messages

```json
{
  "text": "Hello from WaddleBot!"
}
```

### Interactive Cards

```json
{
  "cardsV2": [
    {
      "cardId": "action-card-1",
      "card": {
        "header": {
          "title": "Action Required",
          "subtitle": "Please review and respond"
        },
        "sections": [
          {
            "widgets": [
              {
                "textParagraph": {
                  "text": "This action requires your approval."
                }
              },
              {
                "buttonList": {
                  "buttons": [
                    {
                      "text": "Approve",
                      "onClick": {
                        "action": {
                          "function": "approveAction",
                          "parameters": [
                            {
                              "key": "action_id",
                              "value": "123"
                            }
                          ]
                        }
                      }
                    },
                    {
                      "text": "Reject",
                      "onClick": {
                        "action": {
                          "function": "rejectAction",
                          "parameters": [
                            {
                              "key": "action_id",
                              "value": "123"
                            }
                          ]
                        }
                      }
                    }
                  ]
                }
              }
            ]
          }
        ]
      }
    }
  ]
}
```

### Card with Form Input

```json
{
  "cardsV2": [
    {
      "cardId": "form-card-1",
      "card": {
        "header": {
          "title": "Submit Information"
        },
        "sections": [
          {
            "widgets": [
              {
                "textInput": {
                  "label": "Your Name",
                  "name": "userName",
                  "hintText": "Enter your full name"
                }
              },
              {
                "selectionInput": {
                  "label": "Priority Level",
                  "name": "priority",
                  "items": [
                    {
                      "text": "Low",
                      "value": "low"
                    },
                    {
                      "text": "Medium",
                      "value": "medium"
                    },
                    {
                      "text": "High",
                      "value": "high"
                    }
                  ]
                }
              },
              {
                "buttonList": {
                  "buttons": [
                    {
                      "text": "Submit",
                      "onClick": {
                        "action": {
                          "function": "submitForm"
                        }
                      }
                    }
                  ]
                }
              }
            ]
          }
        ]
      }
    }
  ]
}
```

## Slash Commands

Implement slash commands for user interactions:

### Registering Slash Commands

```python
# Register when bot initializes
@app.route('/googlechat/register-commands', methods=['POST'])
def register_commands():
    commands = [
        {
            'name': '/waddlebot-help',
            'description': 'Get help about WaddleBot'
        },
        {
            'name': '/waddlebot-status',
            'description': 'Check system status'
        },
        {
            'name': '/waddlebot-action',
            'description': 'Execute a WaddleBot action'
        }
    ]
    # Register with Google Chat API
    return jsonify({"status": "registered"})
```

### Handling Slash Command Invocation

```python
@app.route('/googlechat/slash-command', methods=['POST'])
def handle_slash_command():
    payload = request.json
    command = payload['message']['slashCommand']['commandId']
    user = payload['user']['displayName']

    if command == '/waddlebot-help':
        return jsonify({
            "text": f"Hello {user}! Here's how to use WaddleBot..."
        })
```

## Testing the Integration

### Test with Interactive Card

1. Open Google Chat in a space
2. Send a message mentioning the bot: `@WaddleBot help`
3. Verify the bot responds with an interactive card
4. Click buttons to test card interactions

### Test Slash Commands

1. In a Chat space, type `/waddlebot-status`
2. Verify the bot responds with current status
3. Test other slash commands

### Test with Pub/Sub

Monitor messages in real-time:

```bash
gcloud pubsub subscriptions pull waddlebot-chat-sub --auto-ack --limit=10
```

### Manual API Testing

Send a test message using the API:

```bash
curl -X POST https://chat.googleapis.com/v1/spaces/SPACE_ID/messages \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Test message from WaddleBot"
  }'
```

## Troubleshooting

### Bot Not Responding

**Problem**: Bot doesn't acknowledge messages in space

**Solutions**:
1. Verify bot is added to the space: right-click space → "App management" → verify WaddleBot is enabled
2. Check service account permissions are correct
3. Verify `GOOGLE_CHAT_SERVICE_ACCOUNT_KEY` is properly encoded
4. Check module logs for authentication errors

### Cards Not Rendering

**Problem**: Interactive cards display as plain text

**Solutions**:
1. Validate JSON structure against [Cards API schema](https://developers.google.com/chat/api/reference/rest/v1/cards)
2. Check all required fields are present
3. Verify button actions have proper function names
4. Test with simpler card first, then add complexity

### Pub/Sub Message Issues

**Problem**: Messages not appearing in subscription

**Solutions**:
1. Verify Pub/Sub topic is created and accessible
2. Check service account has `pubsub.editor` role
3. Verify topic is being published to correctly
4. Check dead-letter topic for failed messages

### Rate Limiting

**Problem**: Google Chat returns rate limit errors

**Solutions**:
1. Implement exponential backoff (module does this by default)
2. Reduce message frequency
3. Batch operations where possible
4. Contact Google Cloud support if limits are too restrictive

## Security Considerations

1. **Service Account Key**: Store securely, never commit to version control, rotate regularly
2. **API Scopes**: Only request necessary scopes and permissions
3. **Webhook Validation**: Validate all incoming requests are from Google Chat
4. **User Authorization**: Implement proper authorization checks before executing actions
5. **Data Protection**: Don't log sensitive data, comply with workspace data policies
6. **Access Control**: Use Google Chat space-level permissions to control bot access

## Additional Resources

- [Google Chat API Documentation](https://developers.google.com/chat)
- [Google Chat Bots Guide](https://developers.google.com/chat/how-tos/bots)
- [Interactive Cards API](https://developers.google.com/chat/api/guides/message-formats/cards)
- [Google Cloud Pub/Sub Documentation](https://cloud.google.com/pubsub/docs)
- [Service Accounts Guide](https://cloud.google.com/iam/docs/service-accounts)
