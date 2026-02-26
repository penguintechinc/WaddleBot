# Discord Module Usage Guide

## Getting Started

### 1. Create a Discord Application

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and name it (e.g., "WaddleBot")
3. Go to "Bot" section and click "Add Bot"
4. Copy the bot token (you'll need this for `DISCORD_BOT_TOKEN`)
5. Go to "OAuth2" → "URL Generator"
6. Select scopes: `bot`, `applications.commands`
7. Select permissions:
   - `Send Messages`
   - `Embed Links`
   - `Attach Files`
   - `Read Messages/View Channels`
   - `Use Slash Commands`
   - `Use External Emojis`
8. Copy the generated URL and open it in browser to invite bot to your server

### 2. Set Required Environment Variables

```bash
export DISCORD_BOT_TOKEN="your_bot_token_here"
export DISCORD_APPLICATION_ID="your_application_id_here"
export ROUTER_API_URL="http://router:5000"
export CORE_API_URL="http://core:5001"
export DATABASE_URL="postgresql://user:pass@localhost/waddlebot"
export REDIS_URL="redis://localhost:6379/0"
```

### 3. Start the Service

```bash
# Using docker-compose
docker-compose up discord-module

# Or directly with Python
python -m uvicorn services.discord_bot:app --port 8003 --reload
```

## Using Slash Commands

### Basic Slash Command

Once the bot joins your server, you can use slash commands:

```
/balance
```

The bot shows your current balance as a Discord embed.

### Slash Command with Parameters

Some commands accept parameters for autocompletion:

```
/give @user 100
```

This gives 100 of your currency to another user.

### Command Groups

Related commands are grouped:

```
/form create               # Create a new form
/form list                 # List all forms
/form submit form-name     # Submit a form

/poll create               # Create a poll
/poll vote poll-name       # Vote on a poll

/ticket create             # Create a support ticket
/ticket close ticket-id    # Close a ticket
```

## Using Prefix Commands

If your server has prefix commands enabled (usually `!`):

```
!help               # Show help message
!balance            # Check balance
!give @user 100     # Give currency
!top                # Show leaderboards
```

## Using Interactive Elements

### Buttons

Click buttons in bot responses:

```
[Accept] [Decline] [More Info]
```

Each button has a `custom_id` that the router processes.

### Select Menus (Dropdowns)

Choose from dropdown menus:

```
Choose a category: [Dropdown ▼]
- Sports
- Music
- Gaming
```

### Modals (Forms)

Some commands open interactive forms:

1. Click the "Open Feedback Form" button
2. Fill in the form fields
3. Click "Submit"

The bot sends your form responses to the router.

## Admin Commands

### Context Switching

Admins can switch the bot's context using:

```
/context switch guild-id
```

This stores the context in the database for subsequent interactions.

### Server Linking

Admins can link servers together:

```
/link primary guild-id-1
/link secondary guild-id-2
```

This allows cross-server interactions and shared state.

## Message Splitting

If a response is longer than 2000 characters, it's automatically split:

```
Results (1/3)
[First 2000 characters]

Results (2/3)
[Next 2000 characters]

Results (3/3)
[Remaining characters]
```

All parts are posted to the same channel.

## Interaction Flow Example

### Step-by-Step Example: Creating a Poll

1. **User types command:**
   ```
   /poll create
   ```

2. **Bot responds with form:**
   ```
   A modal opens with fields:
   - Poll Question
   - Option 1
   - Option 2
   - Option 3 (optional)
   - Option 4 (optional)
   ```

3. **User fills form:**
   ```
   Poll Question: "What's your favorite game?"
   Option 1: "Valorant"
   Option 2: "CS:GO"
   Option 3: "Elden Ring"
   ```

4. **User submits:**
   - Modal data sent to router
   - Router creates poll in database
   - Bot posts poll embed with voting buttons

5. **Users vote:**
   - Click vote buttons
   - Interactions sent to router
   - Router updates vote counts
   - Bot updates embed with new counts

## Error Handling

### Bot Not Responding

If the bot doesn't respond:

1. Check that bot is in the server: `Right-click server → Server Settings → Members`
2. Check bot has required permissions: `Right-click bot → Roles → Verify permissions`
3. Check logs: `docker logs waddlebot-discord-module`

### Command Not Found

If a command doesn't exist:

1. Ensure bot token and application ID are correct
2. Commands may take up to 1 hour to sync with Discord
3. Try: `/` then wait 5 seconds for command suggestions to load
4. Reload Discord client if needed: `Ctrl+Shift+R`

### Rate Limited

If you get a "Rate limited" error:

1. Wait 60 seconds
2. Resume normal usage
3. The bot automatically handles rate limiting with backoff

### Permission Errors

If the bot says "I don't have permission":

1. Check server permissions: `Right-click bot → Roles → Edit Role`
2. Verify the bot can:
   - Send messages in the channel
   - Embed links
   - Use slash commands
   - Use external emojis

## Advanced Usage

### Credential Management

The Discord module stores user credentials in the database with Redis caching:

```python
# Credentials are stored per user per guild
credentials = {
    "user_id": "987654321",
    "guild_id": "123456789",
    "platform": "twitch",
    "token": "encrypted_token",
    "expires_at": "2026-03-24T10:15:30Z"
}
```

Users can manage credentials through the bot:

```
/link twitch-account my-username
```

### Interaction Context

The bot automatically tracks interaction context:

```json
{
  "user_id": "987654321",
  "guild_id": "123456789",
  "channel_id": "channel123",
  "timestamp": "2026-02-24T10:15:30Z"
}
```

The router can use this to provide context-aware responses.

### Logging and Debugging

Enable debug logging:

```bash
export LOG_LEVEL="DEBUG"
docker-compose up discord-module
```

This shows all Discord API calls and event handling:

```
[DEBUG] Event: INTERACTION_CREATE from user 987654321
[DEBUG] Slash command: /balance with options {}
[DEBUG] Forwarding to router: http://router:5000/events
[DEBUG] Router response: {...}
```

## Monitoring

### Check Bot Status

```bash
curl http://localhost:8003/api/v1/status
```

Response:
```json
{
  "status": "ok",
  "guilds_count": 5,
  "latency_ms": 125
}
```

### View Connected Guilds

```bash
curl http://localhost:8003/api/v1/bot/guilds
```

### Check Metrics

```bash
curl http://localhost:8003/metrics
```

## Common Patterns

### Creating Forms

```
/form create
[Modal opens]
Fill fields → Submit → Router processes → Bot confirms
```

### Creating Polls

```
/poll create
[Modal opens with poll options]
Submit → Router creates poll → Bot posts voting embed
```

### Giving Currency

```
/give @user 100
Bot confirms: "You gave 100 gold to @user"
```

### Setting Reminders

```
/remind 10m "Check on project"
Bot confirms: "Reminder set for 10 minutes from now"
[10 minutes later]
Bot: "@user Remember: Check on project"
```

## Troubleshooting Commands

### View Help

```
/waddlebot help
```

### Check Bot Status

```
/waddlebot status
```

### View Command List

```
/
[Wait 5 seconds for suggestions]
```

### Report Issue

```
/feedback "Bot is not responding"
```

This creates a support ticket for the admin team.
