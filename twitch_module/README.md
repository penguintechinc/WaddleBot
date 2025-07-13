# WaddleBot Twitch Module

A py4web-based module for handling Twitch webhooks and API connections for the WaddleBot platform.

## Features

- **Webhook Handling**: Receives and processes Twitch EventSub webhooks
- **API Integration**: Manages Twitch API connections and data retrieval
- **Authentication**: Handles OAuth flow and token management
- **Activity Tracking**: Tracks user activities (follows, subs, bits, raids, etc.)
- **Database Integration**: Stores events, activities, and user data

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
export TWITCH_APP_ID="your_app_id"
export TWITCH_APP_SECRET="your_app_secret"
export TWITCH_REDIRECT_URI="http://localhost:8000/twitch/auth/callback"
export TWITCH_WEBHOOK_SECRET="your_webhook_secret"
export TWITCH_WEBHOOK_CALLBACK_URL="https://your-domain.com/twitch/webhook"
export CONTEXT_API_URL="http://your-context-api/endpoint"
export REPUTATION_API_URL="http://your-reputation-api/endpoint"
export GATEWAY_ACTIVATE_URL="http://your-gateway-api/activate"
export DB_URI="sqlite://storage.db"
```

## Usage

### Starting the Module

```python
from twitch_module import webhooks, api, auth
```

### API Endpoints

#### Authentication
- `GET /twitch/auth/login` - Initiate OAuth flow
- `GET /twitch/auth/callback` - OAuth callback handler
- `GET /twitch/auth/status?user_id=<id>` - Check auth status
- `POST /twitch/auth/refresh/<user_id>` - Refresh tokens
- `POST /twitch/auth/revoke/<user_id>` - Revoke tokens
- `GET /twitch/auth/users` - List authenticated users

#### API Management
- `GET /twitch/api/user/<user_id>` - Get user information
- `GET /twitch/api/subscriptions` - List EventSub subscriptions
- `POST /twitch/api/subscriptions` - Create subscription
- `DELETE /twitch/api/subscriptions` - Delete subscription
- `GET /twitch/api/channels` - List monitored channels
- `POST /twitch/api/channels` - Add channel
- `POST /twitch/api/setup/<channel_id>` - Setup channel subscriptions

#### Webhooks
- `POST /twitch/webhook` - Receive Twitch webhooks
- `GET /twitch/events` - List recent events
- `GET /twitch/activities` - List recent activities

## Database Schema

### Tables

- **twitch_tokens**: OAuth tokens for authenticated users
- **twitch_channels**: Monitored Twitch channels
- **twitch_subscriptions**: EventSub subscriptions
- **twitch_events**: Webhook events log
- **twitch_activities**: Processed activities for reputation system

## Event Types Supported

- `channel.follow` - New followers
- `channel.subscribe` - New subscriptions
- `channel.cheer` - Bit donations
- `channel.raid` - Channel raids
- `channel.subscription.gift` - Gifted subscriptions

## Activity Points

Default activity point values:
- Follow: 10 points
- Subscribe: 50 points
- Bits: Variable (1 point per bit, configurable)
- Raid: 30 points
- Subscription Gift: 60 points
- Ban: -10 points

## Integration with WaddleBot

The module integrates with the WaddleBot ecosystem through:

1. **Context API**: Retrieves user context and identity information
2. **Reputation API**: Sends processed activities for reputation tracking
3. **Gateway API**: Handles gateway activation during OAuth flow

## Security

- Webhook signatures are verified using HMAC-SHA256
- OAuth state parameters prevent CSRF attacks
- Tokens are automatically refreshed when near expiration
- All API endpoints include proper error handling and logging

## Development

### Running Tests
```bash
# Add test commands when tests are implemented
```

### Database Migrations
The module automatically handles database migrations when started.

### Logging
Configure logging level via environment:
```bash
export LOG_LEVEL=INFO
```

## Contributing

1. Follow the existing code structure
2. Add proper error handling and logging
3. Update this README for new features
4. Ensure webhook signature verification for security