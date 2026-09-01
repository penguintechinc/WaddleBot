# Discord Module Configuration

## Environment Variables

All configuration is managed via environment variables. Create a `.env` file or set them in your deployment platform.

### Required Variables

```bash
# Discord API Credentials (REQUIRED)
DISCORD_BOT_TOKEN="your_bot_token_here"
DISCORD_APPLICATION_ID="your_application_id_here"

# External Service URLs
ROUTER_API_URL="http://router:5000"
CORE_API_URL="http://core:5001"

# Database
DATABASE_URL="postgresql://user:pass@localhost/waddlebot"

# Redis
REDIS_URL="redis://localhost:6379/0"
```

### Optional Variables

```bash
# Service Configuration
MODULE_PORT=8003                    # Default: 8003
LOG_LEVEL=INFO                      # Default: INFO (DEBUG, INFO, WARNING, ERROR)
SECRET_KEY="your_secret_key"        # Default: auto-generated
ENVIRONMENT=development             # Default: development (development, staging, production)

# Discord Bot Configuration
DISCORD_PREFIX="!"                  # Prefix for text commands (default: !)
COMMAND_PREFIX_ENABLED=true         # Enable prefix commands (default: true)
MAX_MESSAGE_LENGTH=2000             # Discord API limit (default: 2000)
MESSAGE_SPLIT_ENABLED=true          # Enable message splitting (default: true)

# Timeout Configuration
INTERACTION_TIMEOUT_SECONDS=900     # Interaction timeout (default: 900)
ROUTER_TIMEOUT_SECONDS=30           # Router request timeout (default: 30)
DATABASE_TIMEOUT_SECONDS=10         # Database timeout (default: 10)

# Redis Configuration
REDIS_MAX_CONNECTIONS=10            # Connection pool size (default: 10)
REDIS_CREDENTIAL_TTL=3600           # Credential cache TTL in seconds (default: 3600)

# Feature Flags
AUTOCOMPLETE_ENABLED=true           # Enable slash command autocomplete (default: true)
MODAL_SUPPORT_ENABLED=true          # Enable modal forms (default: true)
BUTTON_SUPPORT_ENABLED=true         # Enable buttons (default: true)
SELECT_SUPPORT_ENABLED=true         # Enable select menus (default: true)

# Logging
LOG_FORMAT=json                     # json or text (default: json)
LOG_TO_FILE=false                   # Log to file (default: false)
LOG_FILE_PATH=/var/log/discord.log  # Log file path
```

## Getting Discord Credentials

### Bot Token

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Select your application
3. Navigate to "Bot" section
4. Click "Reset Token" or copy the existing token
5. Set `DISCORD_BOT_TOKEN` to this value

**Security Note**: Never commit the bot token to version control. Use environment variables or secret management systems.

### Application ID

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Select your application
3. Copy the "Application ID" from the General Information section
4. Set `DISCORD_APPLICATION_ID` to this value

## Discord Bot Permissions

The bot needs specific permissions to function. Set these in the Developer Portal:

### Required Permissions

| Permission | Reason |
|-----------|--------|
| Send Messages | Post command responses |
| Embed Links | Send rich embeds |
| Attach Files | Send images/files in responses |
| Read Messages/View Channels | Receive user commands |
| Use Slash Commands | Handle slash command interactions |
| Use External Emojis | Use custom emojis in responses |
| Manage Messages | Edit/delete bot messages for error handling |
| Read Message History | Reference previous messages |

### Optional Permissions

| Permission | Reason |
|-----------|--------|
| Manage Roles | Admin commands may require role management |
| Kick Members | For moderation systems |
| Ban Members | For moderation systems |
| Manage Guild | For server linking features |

### Setting Permissions in Developer Portal

1. Go to "OAuth2" → "URL Generator"
2. Select scopes: `bot`, `applications.commands`
3. Select required permissions from checkboxes
4. Copy the generated URL
5. Open URL in browser to add bot to your server

## Database Configuration

### PostgreSQL

```bash
DATABASE_URL="postgresql://waddlebot_user:secure_password@db.example.com:5432/waddlebot"
```

The module creates required tables automatically on startup using PyDAL:
- `discord_guilds` - Guild information and settings
- `discord_credentials` - User credentials per platform
- `discord_interactions` - Interaction history
- `discord_command_metadata` - Command configurations

### Connection Pooling

```bash
# Adjust for your database load
DATABASE_POOL_SIZE=10
DATABASE_POOL_RECYCLE=3600
DATABASE_POOL_TIMEOUT=30
```

## Redis Configuration

### Redis Connection

```bash
REDIS_URL="redis://localhost:6379/0"
```

For clusters:
```bash
REDIS_URL="redis-cluster://node1:6379,node2:6379,node3:6379"
```

For sentinels:
```bash
REDIS_URL="redis+sentinel://sentinel1:26379,sentinel2:26379/mymaster/0"
```

### Cache Settings

```bash
# Credential cache TTL (time to live)
REDIS_CREDENTIAL_TTL=3600          # 1 hour

# Interaction state TTL
REDIS_INTERACTION_TTL=900          # 15 minutes

# Connection pool
REDIS_MAX_CONNECTIONS=10
REDIS_SOCKET_TIMEOUT=5
```

## Service Integration URLs

### Router API

The router processes all events and returns responses:

```bash
ROUTER_API_URL="http://router:5000"
```

The module sends POST requests to:
- `POST {ROUTER_API_URL}/events` - Forward normalized events
- `GET {ROUTER_API_URL}/commands` - Fetch command definitions

### Core API

The core API handles user validation and feature checks:

```bash
CORE_API_URL="http://core:5001"
```

The module makes requests to:
- `GET {CORE_API_URL}/users/{user_id}` - Get user information
- `GET {CORE_API_URL}/features/{user_id}` - Check available features
- `POST {CORE_API_URL}/audit` - Log user actions

## Logging Configuration

### Log Levels

```bash
LOG_LEVEL=INFO
```

Options:
- `DEBUG` - Verbose logging of all operations
- `INFO` - Standard logging of important events
- `WARNING` - Only warnings and errors
- `ERROR` - Only critical errors

### Log Format

```bash
LOG_FORMAT=json
```

Options:
- `json` - Machine-readable JSON format (recommended for production)
- `text` - Human-readable text format (recommended for development)

### Log Output

By default, logs go to stdout. To write to file:

```bash
LOG_TO_FILE=true
LOG_FILE_PATH=/var/log/waddlebot/discord.log
LOG_FILE_MAX_SIZE=104857600        # 100 MB
LOG_FILE_BACKUP_COUNT=10           # Keep 10 backup files
```

## Docker Compose Configuration

### Development

```yaml
services:
  discord-module:
    image: waddlebot/discord-module:latest
    ports:
      - "8003:8003"
    environment:
      - DISCORD_BOT_TOKEN=${DISCORD_BOT_TOKEN}
      - DISCORD_APPLICATION_ID=${DISCORD_APPLICATION_ID}
      - ROUTER_API_URL=http://router:5000
      - CORE_API_URL=http://core:5001
      - DATABASE_URL=postgresql://user:pass@db:5432/waddlebot
      - REDIS_URL=redis://redis:6379/0
      - LOG_LEVEL=DEBUG
    depends_on:
      - db
      - redis
    networks:
      - waddlebot-network
```

### Production

```yaml
services:
  discord-module:
    image: waddlebot/discord-module:v1.0.0
    restart: always
    ports:
      - "8003:8003"
    environment:
      - DISCORD_BOT_TOKEN=${DISCORD_BOT_TOKEN}
      - DISCORD_APPLICATION_ID=${DISCORD_APPLICATION_ID}
      - ROUTER_API_URL=https://router.example.com
      - CORE_API_URL=https://core.example.com
      - DATABASE_URL=postgresql://user:pass@db.example.com:5432/waddlebot
      - REDIS_URL=redis://redis.example.com:6379/0
      - LOG_LEVEL=INFO
      - ENVIRONMENT=production
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8003/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - waddlebot-network
```

## Kubernetes Configuration

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: discord-module
spec:
  replicas: 2
  template:
    spec:
      containers:
      - name: discord-module
        image: waddlebot/discord-module:v1.0.0
        ports:
        - containerPort: 8003
        env:
        - name: DISCORD_BOT_TOKEN
          valueFrom:
            secretKeyRef:
              name: discord-secrets
              key: bot-token
        - name: DISCORD_APPLICATION_ID
          valueFrom:
            secretKeyRef:
              name: discord-secrets
              key: application-id
        - name: ROUTER_API_URL
          value: "http://router:5000"
        - name: CORE_API_URL
          value: "http://core:5001"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secrets
              key: connection-string
        - name: REDIS_URL
          value: "redis://redis:6379/0"
        - name: LOG_LEVEL
          value: "INFO"
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8003
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8003
          initialDelaySeconds: 5
          periodSeconds: 5
```

## Configuration Validation

The module validates configuration on startup. If required variables are missing:

```
ERROR: Missing required environment variable: DISCORD_BOT_TOKEN
ERROR: Missing required environment variable: DISCORD_APPLICATION_ID
```

To validate before starting:

```bash
python -c "from config import validate_config; validate_config()"
```

## Command Registration

### Automatic Registration

Slash commands are registered automatically when the bot starts:

```
[INFO] Registering 24 slash command groups...
[INFO] Registered /waddlebot
[INFO] Registered /form
[INFO] Registered /poll
...
[INFO] All commands registered successfully
```

This may take up to 1 hour to sync globally across Discord.

### Manual Registration

To force re-registration:

```bash
docker-compose exec trigger-discord python -m scripts.register_commands --force
```

### Command Configuration

Command definitions are fetched from the router:

```
GET /commands
```

The router returns:

```json
{
  "commands": [
    {
      "name": "balance",
      "group": "waddlebot",
      "description": "Check your balance",
      "options": [
        {
          "name": "user",
          "type": "string",
          "description": "Optional username",
          "required": false
        }
      ]
    }
  ]
}
```

## Startup and Health Checks

### Health Endpoint

The module provides a health check:

```bash
curl http://localhost:8003/health
```

Returns `OK` with status 200 if healthy.

### Startup Checks

On startup, the module verifies:

1. Discord API connectivity (bot token valid)
2. Router API connectivity
3. Database connectivity
4. Redis connectivity (optional)
5. All required environment variables

If any check fails, startup fails with detailed error messages.

## Troubleshooting Configuration

### Bot Token Invalid

```
ERROR: Invalid bot token
```

Solution: Verify `DISCORD_BOT_TOKEN` is correct and bot has not been deleted.

### Application ID Mismatch

```
ERROR: Application ID does not match bot token
```

Solution: Ensure `DISCORD_APPLICATION_ID` matches the bot's application ID from Developer Portal.

### Router Unreachable

```
ERROR: Cannot connect to router at http://router:5000
```

Solution: Verify `ROUTER_API_URL` is correct and router service is running.

### Database Connection Failed

```
ERROR: Cannot connect to database
```

Solution: Verify `DATABASE_URL` is correct and database is running and accessible.
