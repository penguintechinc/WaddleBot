# Discord Module Architecture

## System Design Overview

```
┌─────────────────┐
│ Discord Servers │
└────────┬────────┘
         │ WebSocket Events
         │ (py-cord handles)
         ▼
┌──────────────────────────────┐
│   py-cord Bot Instance       │
│  (Connection Management)     │
└────────┬─────────────────────┘
         │
         ├─────────────────────────────────────┐
         │                                     │
         ▼                                     ▼
┌──────────────────────┐          ┌────────────────────────┐
│ DiscordBotService    │          │ InteractionHandler     │
│  (Main Logic)        │          │  (UI Building)         │
│                      │          │                        │
│ - Event normalization│          │ - Modal creation       │
│ - Command routing    │          │ - Button rendering     │
│ - Credential mgmt    │          │ - Embed formatting     │
│ - Response rendering │          │ - Select menu builder  │
└──────────┬───────────┘          └────────────────────────┘
           │
           │ (Normalized events)
           ▼
┌──────────────────────────────┐
│   Router API                 │
│  /events endpoint            │
└──────────┬───────────────────┘
           │
           ├──────────────────┬─────────────────┬──────────────┐
           ▼                  ▼                 ▼              ▼
        [Core]           [Database]         [Features]    [Platform Svc]
```

## Core Components

### 1. DiscordBotService

**File**: `trigger/receiver/discord_module/services/discord_bot.py`

Main orchestrator that:
- Manages py-cord bot lifecycle
- Registers slash command groups dynamically
- Handles all Discord events (message, interaction, guild_join, etc.)
- Normalizes events to WaddleBot standard format
- Forwards events to router API
- Renders router responses back to Discord

**Key Methods**:
```python
class DiscordBotService:
    async def register_commands()      # Register all slash command groups
    async def on_message()             # Handle text messages
    async def on_interaction()         # Handle button/select/modal interactions
    async def on_slash_command()       # Handle slash commands
    async def on_guild_join()          # Handle bot joining guild
    async def forward_to_router()      # Send normalized event to router
    async def render_response()        # Build Discord UI from router response
```

**Event Flow**:
```
Discord Event
  ▼
py-cord Handler (on_message, on_interaction, etc.)
  ▼
DiscordBotService.normalize_event()
  ▼
DiscordBotService.forward_to_router()
  ▼
Router processes event
  ▼
Router returns response
  ▼
DiscordBotService.render_response()
  ▼
InteractionHandler builds Discord components
  ▼
Send message/embed/modal back to Discord
```

### 2. InteractionHandler

**File**: `trigger/receiver/discord_module/services/interaction_handler.py`

Builds Discord UI components from router responses:

**Key Methods**:
```python
class InteractionHandler:
    def build_embed()           # Create Discord embed from response
    def build_buttons()         # Create button rows
    def build_select_menu()     # Create dropdown/select menu
    def build_modal()           # Create modal form
    def format_text()           # Format text with Discord markdown
    def split_message()         # Split long responses (>2000 chars)
```

**Supported Components**:
- **Embeds**: Rich text with colors, fields, footers, images
- **Buttons**: Primary, secondary, success, danger, link styles
- **Select Menus**: Dropdown menus with options and groups
- **Modals**: Forms with text inputs, select menus
- **Text**: Plain text with Discord markdown formatting

### 3. Event Normalization

All Discord events are normalized to a standard format before forwarding to router:

```python
{
    "entity_id": "guild:channel",           # Key for context
    "message_type": "slashCommand",         # slashCommand|chatMessage|interaction
    "platform": "discord",                  # Always "discord"
    "user_id": "987654321",                # Discord user ID
    "guild_id": "123456789",               # Discord guild ID
    "channel_id": "channel123",            # Discord channel ID
    "message_id": "msg123",                # Discord message ID (for references)
    "content": "help",                     # User input/command text
    "interaction_token": "token_xyz",      # For interaction responses
    "timestamp": "2026-02-24T10:15:30Z",  # UTC timestamp
    "metadata": {                          # Command-specific metadata
        "command_name": "balance",
        "command_group": "waddlebot",
        "options": {"user": "someuser"}
    }
}
```

### 4. Credential Management

Credentials are stored per-user-per-guild and cached in Redis:

```
User connects platform account (e.g., Twitch)
  ▼
/link twitch-account my-username
  ▼
Bot stores in database:
  {
    "user_id": "987654321",
    "guild_id": "123456789",
    "platform": "twitch",
    "token": "encrypted_token",
    "username": "my-username",
    "expires_at": "2026-03-24T10:15:30Z"
  }
  ▼
Redis caches for 1 hour
  ▼
When user runs command, credentials loaded from cache/database
```

## Data Flow

### Slash Command Flow

```
User: /balance
  ▼
py-cord receives interaction
  ▼
on_app_command_error() or on_app_command()
  ▼
DiscordBotService.handle_slash_command()
  ▼
normalize_event({
    "message_type": "slashCommand",
    "metadata": {
        "command_name": "balance",
        "command_group": "waddlebot",
        "options": {}
    }
})
  ▼
POST /events to router
  ▼
Router processes and returns:
  {
    "type": "embed",
    "content": {
      "title": "Balance",
      "description": "Your balance is 1000 gold",
      "fields": [{"name": "Gold", "value": "1000", "inline": true}]
    }
  }
  ▼
InteractionHandler.build_embed()
  ▼
respond_with_embed()
  ▼
Discord shows embed in channel
```

### Button Interaction Flow

```
User clicks [Accept] button
  ▼
py-cord receives interaction with custom_id
  ▼
on_interaction()
  ▼
DiscordBotService.handle_interaction()
  ▼
normalize_event({
    "message_type": "interaction",
    "metadata": {
        "interaction_type": "button",
        "interaction_id": "accept_123",
        "interaction_values": []
    }
})
  ▼
POST /events to router
  ▼
Router processes button action
  ▼
Router returns next state (new embed, new buttons, or confirmation)
  ▼
InteractionHandler renders response
  ▼
update_message() or send_message()
  ▼
Discord updates or sends message
```

### Modal Submission Flow

```
User fills and submits modal form
  ▼
py-cord receives modal_submit interaction
  ▼
on_interaction()
  ▼
DiscordBotService.handle_modal_submit()
  ▼
extract_form_data()
  ▼
normalize_event({
    "message_type": "interaction",
    "metadata": {
        "interaction_type": "modal",
        "interaction_id": "feedback_form_123",
        "interaction_values": {
            "feedback_text": "Great bot!",
            "rating_select": "5_stars"
        }
    }
})
  ▼
POST /events to router
  ▼
Router processes form submission
  ▼
Router returns confirmation or next step
  ▼
respond_with_message() or respond_with_embed()
  ▼
Discord shows response
```

## Command Registration

### Registration Process

1. **Startup**: Service reads slash command definitions
2. **Sync**: Registers commands with Discord API
3. **Sync**: Commands propagate to all connected guilds (up to 1 hour)
4. **User sees**: `/` prefix reveals registered commands

```
Service Start
  ▼
Load command definitions from config
  ▼
FOR EACH command group:
  - Create group (/form, /poll, etc.)
  - Add subcommands (create, list, delete, etc.)
  - Set descriptions and options
  ▼
Call Discord API: register commands
  ▼
Wait for global sync (up to 1 hour)
  ▼
Users can now see commands in /
```

### Dynamic Autocomplete

Commands with autocomplete show suggestions:

```
User types: /give @
  ▼
py-cord detects autocomplete event
  ▼
autocomplete_handler("user", "", context)
  ▼
Query database for online users
  ▼
Return suggestions:
  - @alice
  - @bob
  - @charlie
  ▼
Discord shows dropdown suggestions
  ▼
User clicks @alice
  ▼
/give @alice
```

## Router Integration

### Event Forwarding

```python
async def forward_to_router(event: dict):
    # POST normalized event to router
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{ROUTER_API_URL}/events",
            json=event,
            timeout=30
        )
        return response.json()
```

### Response Rendering

```python
def render_response(router_response: dict):
    response_type = router_response.get("type")

    if response_type == "embed":
        return interaction_handler.build_embed(router_response)
    elif response_type == "button":
        return interaction_handler.build_buttons(router_response)
    elif response_type == "modal":
        return interaction_handler.build_modal(router_response)
    elif response_type == "text":
        return router_response.get("content")
```

## Error Handling

### Graceful Degradation

If router is unavailable:
```
POST /events fails
  ▼
Retry with exponential backoff (1s, 2s, 4s)
  ▼
After 3 retries, respond to Discord:
  "Sorry, I'm having trouble processing that right now"
```

### Validation Errors

Invalid command parameters:
```
/give @user abc
  ▼
Validate amount is number
  ▼
Invalid, respond:
  "Amount must be a number (e.g., /give @user 100)"
```

### Permission Checks

Admin-only commands:
```
/context switch 999
  ▼
Check user is admin in guild
  ▼
Not admin, respond:
  "Only admins can use this command"
```

## Database Schema

### discord_guilds
```sql
CREATE TABLE discord_guilds (
    id SERIAL PRIMARY KEY,
    guild_id VARCHAR(20) UNIQUE,
    name VARCHAR(100),
    icon_url VARCHAR(255),
    owner_id VARCHAR(20),
    prefix VARCHAR(5),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### discord_credentials
```sql
CREATE TABLE discord_credentials (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(20),
    guild_id VARCHAR(20),
    platform VARCHAR(50),
    token TEXT ENCRYPTED,
    username VARCHAR(100),
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, guild_id, platform)
);
```

### discord_interactions
```sql
CREATE TABLE discord_interactions (
    id SERIAL PRIMARY KEY,
    interaction_id VARCHAR(20),
    user_id VARCHAR(20),
    guild_id VARCHAR(20),
    interaction_type VARCHAR(50),
    command_name VARCHAR(100),
    options JSONB,
    response JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## Redis Cache Strategy

### Credential Caching

```
Key: discord:cred:{user_id}:{guild_id}:{platform}
Value: {encrypted_token, username, expires_at}
TTL: 3600 seconds (1 hour)

On credential access:
  1. Check Redis cache
  2. If miss, query database
  3. If found, cache in Redis
  4. Return credential
```

### Interaction State

```
Key: discord:interaction:{interaction_id}
Value: {user_id, guild_id, context_data}
TTL: 900 seconds (15 minutes)

Used for multi-step interactions:
  1. User clicks button → store state
  2. User fills modal → retrieve state
  3. User submits → clear state
```

## Concurrency and Scaling

### Async Architecture

All I/O operations are async:
- py-cord handles Discord connections (async WebSocket)
- httpx for async HTTP requests to router/core
- aioredis for async Redis operations
- asyncpg for async database connections

### Message Queue

For high-volume events, queue events in Redis:

```
1. Receive event
2. Add to Redis queue: discord:events:{timestamp}
3. Background task processes queue
4. Forward to router
5. Handle response
```

### Rate Limiting

Discord API rate limits handled by py-cord:
- Automatic retry with exponential backoff
- Respect Discord's rate limit headers
- Split message if content exceeds 2000 chars

## Security Considerations

### Credential Encryption

Credentials stored encrypted in database:
```
1. User provides credential
2. Encrypt with SECRET_KEY
3. Store encrypted in database
4. When accessed, decrypt with SECRET_KEY
5. Never log plaintext credentials
```

### Admin Commands

Admin-only commands validated on each request:
```
/context switch {guild_id}
  ▼
Check user has ADMIN permission
  ▼
Check user is in target guild
  ▼
Allow or deny with clear error message
```

### Input Validation

All user input validated:
```
- Command names must match whitelist
- Numeric inputs parsed and range-checked
- User IDs must be valid Discord IDs
- Guild IDs must match current guild
- Message content max 2000 characters (Discord limit)
```

## Monitoring and Observability

### Prometheus Metrics

```
discord_bot_events_total{event_type="..."} - Total events
discord_bot_latency_ms - Milliseconds to process events
discord_bot_guilds_total - Number of connected guilds
discord_bot_errors_total{error_type="..."} - Error counts
```

### Logging

```
[2026-02-24 10:15:30] INFO: Event received: slash_command
[2026-02-24 10:15:31] DEBUG: Forwarding to router...
[2026-02-24 10:15:32] INFO: Response received from router
[2026-02-24 10:15:33] INFO: Message posted to Discord
```

### Health Checks

```
GET /health
- Bot is connected to Discord
- Router API is reachable
- Database is accessible
- Redis is accessible (if enabled)
```

## Deployment Architecture

### Single Instance

```
┌─────────────────┐
│ discord-module  │
│  (one replica)  │
│  Port: 8003     │
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
 Router   Database
```

### Scaled Deployment

```
┌─────────────────┐ ┌─────────────────┐
│ discord-module  │ │ discord-module  │
│  (replica 1)    │ │  (replica 2)    │
│  Port: 8003     │ │  Port: 8003     │
└────────┬────────┘ └────────┬────────┘
         │                   │
         └───────────┬───────┘
                     │
            ┌────────┴────────┐
            ▼                 ▼
          Router        (Shared)
                      Database & Redis
```

For multiple replicas:
- Each bot instance registers same commands once (Discord deduplicates)
- Events distributed across replicas via load balancer
- Shared database and Redis for state
