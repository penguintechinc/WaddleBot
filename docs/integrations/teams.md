# Microsoft Teams Integration

This guide covers the setup and configuration of WaddleBot's Microsoft Teams integration, enabling seamless communication and action distribution through Teams channels and direct messages.

## Overview

The Teams integration allows WaddleBot to:
- Send messages and adaptive cards to Teams channels and users
- Receive interactive responses through button clicks and form submissions
- Manage team membership and presence synchronization
- Distribute workflow actions through Teams notifications

## Prerequisites

Before configuring Teams integration, you'll need:
- Microsoft Azure account with administrative access
- Azure AD (Entra ID) tenant
- Teams desktop or web client for testing
- Access to Teams app management portal

## Azure AD App Registration

### Step 1: Create Azure AD Application

1. Navigate to [Azure Portal](https://portal.azure.com)
2. Go to Azure Active Directory → App registrations
3. Click "New registration"
4. Configure:
   - **Name**: "WaddleBot Teams Action Module"
   - **Supported account types**: "Accounts in this organizational directory only"
   - **Redirect URI**: Leave blank for now
5. Click "Register"

### Step 2: Configure API Permissions

1. In your app registration, go to "API permissions"
2. Click "Add a permission"
3. Select "Microsoft Graph"
4. Add the following permissions:
   - **Application**: `Chat.Create`, `Chat.ReadWrite`, `TeamsAppInstallation.ReadWrite.All`
   - **Delegated**: `Teams.ReadWrite`, `User.Read`
5. Click "Grant admin consent for [Organization]"

### Step 3: Create Application Secret

1. Go to "Certificates & secrets"
2. Click "New client secret"
3. Configure:
   - **Description**: "WaddleBot Teams Module Secret"
   - **Expires**: Choose 24 months or longer for production
4. Copy the secret value immediately (it won't be shown again)

## Bot Channel Registration

### Step 1: Register Bot in Azure

1. Go to Azure Portal → Create a resource
2. Search for "Bot Channels Registration"
3. Click "Create"
4. Configure:
   - **Resource name**: "waddlebot-teams-bot"
   - **Subscription**: Select your subscription
   - **Resource group**: Create or select existing
   - **Pricing tier**: "F0" (free) or "S1" (standard)
   - **App ID**: Use the app ID from your Azure AD registration
   - **Password**: Use the client secret from above
   - **Messaging endpoint**: (will configure after deployment)
5. Review and create

### Step 2: Configure Messaging Endpoint

After deploying WaddleBot, configure the messaging endpoint:

1. Go to your Bot Channel Registration in Azure Portal
2. Click "Settings" or "Configuration"
3. Set **Messaging endpoint** to: `https://{your-domain}/teams/messages`
4. Save changes

### Step 3: Add Teams Channel

1. In Bot Channel Registration, go to "Channels"
2. Click "Microsoft Teams"
3. Review the agreement and click "Agree"
4. Close the configuration dialog (Teams channel is now added)

## Adaptive Cards Configuration

WaddleBot uses Adaptive Cards for rich interactive experiences. The Teams module includes support for:

- **Text cards**: Simple text messages
- **Action cards**: Cards with buttons for user interaction
- **Form cards**: Multi-field forms for data collection
- **Hero cards**: Large visual cards with images and calls to action

Example Adaptive Card structure for actions:
```json
{
  "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
  "type": "AdaptiveCard",
  "version": "1.4",
  "body": [
    {
      "type": "TextBlock",
      "text": "Action Required",
      "weight": "bolder",
      "size": "large"
    }
  ],
  "actions": [
    {
      "type": "Action.OpenUrl",
      "title": "Approve",
      "url": "https://{your-domain}/actions/approve?id={action_id}"
    },
    {
      "type": "Action.OpenUrl",
      "title": "Reject",
      "url": "https://{your-domain}/actions/reject?id={action_id}"
    }
  ]
}
```

## Environment Variables

Configure the following environment variables in your deployment:

| Variable | Description | Example |
|----------|-------------|---------|
| `TEAMS_APP_ID` | Azure AD application ID | `550e8400-e29b-41d4-a716-446655440000` |
| `TEAMS_APP_PASSWORD` | Azure AD application client secret | (60-char secret) |
| `TEAMS_TENANT_ID` | Azure AD tenant ID | `550e8400-e29b-41d4-a716-446655440000` |
| `TEAMS_BOT_ID` | Bot's Microsoft App ID | `28:550e8400-e29b-41d4-a716-446655440000` |
| `MODULE_SECRET_KEY` | JWT signing key for module authentication | (generate random 32+ char string) |
| `REST_PORT` | Port for Teams module REST API | `8074` |
| `GRPC_PORT` | Port for Teams module gRPC server | `50057` |
| `DATABASE_URL` | PostgreSQL connection string | `postgres://user:pass@host:5432/db` |
| `REDIS_URL` | Redis connection for caching | `redis://localhost:6379/0` |
| `LOG_LEVEL` | Logging verbosity | `INFO`, `DEBUG`, `WARNING`, `ERROR` |

## Webhook URL Configuration

After deployment, teams will send messages to your webhook endpoint:

1. **Base URL**: Your WaddleBot deployment domain
2. **Teams endpoint**: `/teams/messages`
3. **Full webhook URL**: `https://{your-domain}/teams/messages`

The module automatically validates incoming webhook requests using the Bot App Secret.

## Message Formatting

### Text Messages

```json
{
  "type": "message",
  "from": {
    "id": "29:{bot-id}",
    "name": "WaddleBot"
  },
  "conversation": {
    "isGroup": false,
    "id": "a:user-id"
  },
  "recipient": {
    "id": "{user-id}",
    "name": "John Doe"
  },
  "text": "Hello! This is a message from WaddleBot.",
  "channelData": {
    "notification": {
      "alert": true
    }
  }
}
```

### Adaptive Cards

Send rich interactive content using Adaptive Cards. The Teams module will render these as interactive elements in Teams channels and direct messages.

## Testing the Integration

### Using Microsoft Teams Desktop Client

1. Install WaddleBot from the Teams app store or sideload manually
2. Open a direct message conversation with WaddleBot
3. Send a test message to verify connectivity
4. Click action buttons in Adaptive Cards to test interactive flows

### Using Graph API Testing Tool

Test API calls directly:

```bash
curl -X POST https://graph.microsoft.com/v1.0/me/sendMail \
  -H "Authorization: Bearer {access-token}" \
  -H "Content-Type: application/json" \
  -d '{
    "message": {
      "subject": "Test",
      "body": {
        "contentType": "HTML",
        "content": "Test message"
      },
      "toRecipients": [{
        "emailAddress": {
          "address": "user@example.com"
        }
      }]
    }
  }'
```

## Troubleshooting

### Connection Issues

**Problem**: Bot doesn't respond to messages
- Verify Teams channel is configured in Azure Bot Channels Registration
- Check messaging endpoint URL is publicly accessible
- Confirm firewall rules allow incoming HTTPS requests on port 443

**Solution**:
1. Verify the messaging endpoint in Bot settings
2. Test endpoint with curl: `curl -X POST https://your-endpoint/teams/messages`
3. Check module logs for authentication errors

### Authentication Failures

**Problem**: "Unauthorized" errors in logs
- Ensure TEAMS_APP_ID and TEAMS_APP_PASSWORD are correctly set
- Verify the app secret hasn't expired
- Check the app has required API permissions granted

**Solution**:
1. Verify credentials in Azure Portal
2. Regenerate the client secret if needed
3. Re-grant admin consent for API permissions

### Message Delivery Issues

**Problem**: Messages not delivered to channels
- Verify bot has appropriate permissions in the team/channel
- Check message format is valid JSON
- Ensure recipient channel/user IDs are correct

**Solution**:
1. Add bot to target teams and channels manually
2. Validate message JSON schema
3. Check recipient IDs in the database

## Rate Limiting

Microsoft Teams enforces rate limits on bot API calls:
- **Messages**: 30 per second per user conversation
- **Adaptive Card updates**: 1 per second per card

The Teams action module implements backoff retry logic to handle rate limits gracefully.

## Security Considerations

1. **Secret Management**: Store TEAMS_APP_PASSWORD securely using your secret management system
2. **HTTPS Only**: Always use HTTPS for the messaging endpoint
3. **Message Validation**: All incoming webhooks are validated using the Bot App Secret
4. **User Isolation**: Ensure users can only interact with authorized content
5. **Data Protection**: Comply with organizational policies for data in Teams

## Additional Resources

- [Microsoft Teams Bot Documentation](https://learn.microsoft.com/en-us/azure/bot-service/bot-service-quickstart-create-bot?view=azure-bot-service-4.0)
- [Adaptive Cards Documentation](https://adaptivecards.io)
- [Microsoft Graph API Reference](https://docs.microsoft.com/en-us/graph/api/overview)
- [Azure Bot Service Best Practices](https://learn.microsoft.com/en-us/azure/bot-service/bot-service-design-principles)
