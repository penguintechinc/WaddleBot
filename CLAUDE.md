# WaddleBot Project Context

## Project Overview

WaddleBot is a multi-platform chat bot system with a modular, microservices architecture. The system consists of:

- **Core**: Central API layer with routing (the "router")
- **Collector Modules**: Platform-specific modules that receive webhooks/chat from platforms like Twitch, Discord, Slack
- **Action Modules**: Executed in AWS Lambda for processing and responses
- **Database**: PostgreSQL with read replicas for configuration, routing, logins, roles, etc.

## Architecture

### Core Components
- **Router/Core**: py4web-based API layer that handles routing to Lambda functions
- **Collectors**: Individual Docker containers, each with py4web implementation
- **Actions**: AWS Lambda functions for processing
- **Database**: PostgreSQL server storing:
  - `servers` table: owner, platform (twitch/discord/slack), channel, configuration
  - Routes to Lambda functions
  - User logins, roles, permissions
  - Module registrations and configurations

### Technology Stack
- **Primary Framework**: py4web on Python 3.12
- **Database**: PostgreSQL with read replicas
- **Session Management**: Redis for session ID tracking
- **Containerization**: Docker containers
- **Orchestration**: Kubernetes (longer term)
- **Cloud Functions**: AWS Lambda for actions
- **Future Migration**: Parts may migrate to Golang later

## Current Implementation

### Core System Components
- **router_module/**: High-performance command router with multi-threading, caching, and read replicas
- **marketplace_module/**: py4web-based community module marketplace and management system
- **portal_module/**: py4web-based community management portal with authentication and user dashboard
- **chat/**: Matterbridge-based chat integration
- **gateway/**: Flask-based API gateway (to be migrated to py4web)
- **listener/**: Legacy Twitch authentication and activity listeners
- **libs/**: Shared libraries across modules

### Collector Modules (py4web-based)
- **twitch_module/**: Complete Twitch collector with EventSub webhooks, OAuth, and API integration
- **discord_module/**: Discord collector using py-cord library for bot events and slash commands
- **slack_module/**: Slack collector using Slack SDK for events and slash commands

### Collector Architecture
Each collector module:
- Runs as its own Docker container
- Has its own py4web implementation
- Pulls monitored servers/channels from PostgreSQL `servers` table
- Communicates with core via API when receiving chat/events
- Registers itself with core API
- All configuration comes from environment variables

### Database Schema (Key Tables)
```sql
-- Shared across all collectors
servers (
    id, owner, platform, channel, server_id, 
    is_active, webhook_url, config, 
    last_activity, created_at, updated_at
)

-- Module registration
collector_modules (
    module_name, module_version, platform, endpoint_url,
    health_check_url, status, last_heartbeat, config,
    created_at, updated_at
)
```

## Current State vs Vision

**Vision**: py4web-based core with collector modules reaching out to platforms
**Current**: Mixed Flask/web2py implementation with some py4web components

**Completed**: 
- Twitch collector module in py4web with full Docker/Kubernetes support
- PostgreSQL integration with servers table
- Core API communication patterns
- Webhook handling for Twitch EventSub
- Authentication and token management

## Development Guidelines

### Code Patterns
- **Native Library Usage**: Always prioritize native functionality of specified libraries (py4web, py-cord, etc.) over custom implementations
- Follow existing WaddleBot dataclass patterns (see `listener/WaddleBot-Twitch-Activity-Listener/src/dataclasses/`)
- Use environment variables for all configuration
- Implement proper logging and error handling
- Include database migrations
- Follow security best practices (webhook signature verification, token management)

### Performance Considerations
- **Threading**: Utilize ThreadPoolExecutor for concurrent operations when dealing with thousands of entities
  - RBAC service uses 10 worker threads for bulk operations
  - Bulk permission checks, role assignments, and user management operations
  - Concurrent processing for thousands of users/entities simultaneously
- **Database**: Separate RBAC operations into dedicated `community_rbac` table for better locking performance
  - Reduces contention on main community_memberships table
  - Allows concurrent role assignments without blocking membership operations
- **Bulk Operations**: Implement bulk processing methods for role assignments, permission checks, and user management
  - `check_permissions_bulk()` - Check multiple permissions concurrently
  - `assign_roles_bulk()` - Assign roles to multiple users concurrently
  - `ensure_users_in_global_community_bulk()` - Batch user onboarding
  - `get_user_roles_bulk()` - Retrieve roles for multiple users concurrently
- **Caching**: Use in-memory caching for frequently accessed permissions and roles
- **Connection Pooling**: Leverage database connection pooling for high-concurrency scenarios

### Activity Processing
- Activities have point values: follow=10, sub=50, bits=variable, raid=30, subgift=60, ban=-10
- Process through context API to get user identity
- Send to reputation API for point tracking
- Log all events and activities for audit

### Docker/Kubernetes
- Each collector is a separate container
- Use proper health checks and readiness probes
- Include resource limits and autoscaling
- Secure with non-root users and read-only filesystems
- Environment-based configuration

## File Structure
```
/workspaces/WaddleBot/
├── router_module/          # High-performance command router (CORE)
│   ├── controllers/        # Router endpoints, health, metrics
│   ├── models.py          # Commands, entities, executions tables
│   ├── config.py          # Router and execution configuration
│   ├── services/          # Command processor, cache, rate limiter
│   │   ├── command_processor.py  # Multi-threaded command processing
│   │   ├── cache_manager.py     # High-performance caching
│   │   ├── rate_limiter.py      # Sliding window rate limiting
│   │   ├── execution_engine.py  # Lambda/OpenWhisk execution
│   │   ├── rbac_service.py      # Role-based access control
│   │   └── session_manager.py   # Redis session management
│   ├── middleware/        # RBAC middleware for permission checking
│   ├── k8s/              # Kubernetes deployment configs
│   └── Dockerfile        # Container definition
├── marketplace_module/    # Community module marketplace (CORE)
│   ├── controllers/       # Module browsing, installation, management
│   ├── models.py         # Modules, installations, reviews tables
│   ├── services/         # Module management, router sync
│   ├── k8s/             # Kubernetes deployment configs
│   └── Dockerfile       # Container definition
├── portal_module/        # Community management portal (CORE)
│   ├── app.py           # Main py4web application
│   ├── controllers/     # Portal endpoints and authentication
│   ├── templates/       # HTML templates for portal UI
│   ├── services/        # Portal services (auth, email, community data)
│   │   ├── auth_service.py     # Portal authentication with temp passwords
│   │   ├── email_service.py    # Email service (SMTP/sendmail)
│   │   └── portal_service.py   # Community data retrieval
│   ├── k8s/            # Kubernetes deployment configs
│   └── Dockerfile      # Container definition
├── twitch_module/        # py4web Twitch collector
│   ├── controllers/      # Webhook, API, auth handlers
│   ├── models.py        # Database models and tables
│   ├── config.py        # Configuration management
│   ├── services/        # Core API communication & bot service
│   ├── k8s/            # Kubernetes deployment configs
│   └── Dockerfile      # Container definition
├── discord_module/      # py4web Discord collector
│   ├── controllers/     # Event handlers, API, auth
│   ├── models.py       # Database models for Discord
│   ├── config.py       # Discord bot configuration
│   ├── services/       # Core API & py-cord bot service
│   ├── dataclasses.py  # Discord-specific data structures
│   └── requirements.txt # Python dependencies
├── slack_module/       # py4web Slack collector
│   ├── controllers/    # Event handlers, slash commands
│   ├── models.py      # Database models for Slack
│   ├── config.py      # Slack app configuration
│   ├── services/      # Core API communication
│   └── requirements.txt # Python dependencies
├── chat/              # Existing Matterbridge integration
├── gateway/          # Existing Flask gateway (DEPRECATED)
├── listener/         # Existing Twitch listeners (LEGACY)
└── libs/            # Shared libraries
```

## Integration Points

### Router API Endpoints (Core Component)
- `POST /router/events` - Single event processing from collectors (returns session_id)
- `POST /router/events/batch` - Batch event processing (up to 100 events)
- `GET /router/commands` - List available commands with filters
- `GET /router/entities` - List registered entities
- `GET /router/metrics` - Performance metrics and statistics (includes string matching stats)
- `GET /router/health` - Health check with database connectivity
- `GET /router/string-rules` - List string matching rules (with entity filtering)
- `POST /router/string-rules` - Create new string matching rule
- `PUT /router/string-rules/<id>` - Update existing string matching rule
- `DELETE /router/string-rules/<id>` - Delete (deactivate) string matching rule
- `POST /router/responses` - Submit response from interaction module or webhook (requires session_id)
- `GET /router/responses/<execution_id>` - Get responses for specific execution
- `GET /router/responses/recent` - Get recent module responses with filtering

### Coordination API Endpoints (Horizontal Scaling)
- `POST /router/coordination/claim` - Claim available entities for container
- `POST /router/coordination/release` - Release claimed entities
- `POST /router/coordination/checkin` - Container checkin to maintain claims (every 5 minutes)
- `POST /router/coordination/heartbeat` - Send heartbeat and extend claims
- `POST /router/coordination/status` - Update entity status (live, viewer count, etc.)
- `POST /router/coordination/error` - Report error for entity
- `POST /router/coordination/release-offline` - Release offline entities and claim new ones
- `GET /router/coordination/stats` - Get coordination system statistics
- `GET /router/coordination/entities` - List entities with filtering
- `POST /router/coordination/populate` - Populate coordination table from servers

### Marketplace API Endpoints 
- `GET /marketplace` - Browse featured/popular modules
- `GET /marketplace/browse` - Search and filter modules
- `GET /marketplace/module/<id>` - Module details with versions/reviews
- `POST /marketplace/install` - Install module for entity
- `POST /marketplace/uninstall` - Remove module from entity
- `GET /marketplace/entity/<id>/modules` - List entity's installed modules
- `POST /marketplace/entity/<id>/toggle` - Enable/disable module

### Legacy Core API Endpoints
- `POST /api/modules/register` - Module registration
- `POST /api/modules/heartbeat` - Health monitoring
- `GET /api/servers?platform=twitch&active=true` - Get monitored servers
- `POST /api/context` - User identity lookup
- `POST /api/reputation` - Activity point submission
- `POST /api/events` - Event forwarding
- `POST /api/gateway/activate` - Gateway activation

### Environment Variables

#### Twitch Module
```bash
# Twitch API
TWITCH_APP_ID=your_app_id
TWITCH_APP_SECRET=your_app_secret
TWITCH_WEBHOOK_SECRET=webhook_secret
TWITCH_WEBHOOK_CALLBACK_URL=https://domain.com/twitch/webhook
TWITCH_REDIRECT_URI=https://domain.com/twitch/auth/callback

# Database
DATABASE_URL=postgresql://user:pass@host:5432/waddlebot

# Core API
CORE_API_URL=http://core-api:8001
CONTEXT_API_URL=http://core-api:8001/api/context
REPUTATION_API_URL=http://core-api:8001/api/reputation
GATEWAY_ACTIVATE_URL=http://core-api:8001/api/gateway/activate

# Coordination System
MAX_CLAIMS=5
HEARTBEAT_INTERVAL=300
CONTAINER_ID=twitch_container_1

# Module Info
MODULE_NAME=twitch
MODULE_VERSION=1.0.0
```

#### Discord Module
```bash
# Discord Bot
DISCORD_BOT_TOKEN=your_bot_token
DISCORD_APPLICATION_ID=your_app_id
DISCORD_PUBLIC_KEY=your_public_key
DISCORD_COMMAND_PREFIX=!

# Core API (same as above)
CORE_API_URL=http://core-api:8001
# ... other core API URLs

# Module Info
MODULE_NAME=discord
MODULE_VERSION=1.0.0
```

#### Slack Module
```bash
# Slack App
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token
SLACK_CLIENT_ID=your_client_id
SLACK_CLIENT_SECRET=your_client_secret
SLACK_SIGNING_SECRET=your_signing_secret
SLACK_OAUTH_REDIRECT_URI=https://domain.com/slack/oauth/callback
SLACK_SOCKET_MODE=false

# Core API (same as above)
CORE_API_URL=http://core-api:8001
# ... other core API URLs

# Module Info
MODULE_NAME=slack
MODULE_VERSION=1.0.0
```

#### Router Module
```bash
# Database (Primary + Read Replica)
DATABASE_URL=postgresql://user:pass@host:5432/waddlebot
READ_REPLICA_URL=postgresql://user:pass@read-host:5432/waddlebot

# Redis (Session Management)
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password
REDIS_DB=0
SESSION_TTL=3600
SESSION_PREFIX=waddlebot:session:

# Performance Settings
ROUTER_MAX_WORKERS=20
ROUTER_MAX_CONCURRENT=100
ROUTER_REQUEST_TIMEOUT=30
ROUTER_DEFAULT_RATE_LIMIT=60

# Caching
ROUTER_COMMAND_CACHE_TTL=300
ROUTER_ENTITY_CACHE_TTL=600

# AWS Lambda
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
LAMBDA_FUNCTION_PREFIX=waddlebot-

# OpenWhisk
OPENWHISK_API_HOST=openwhisk.example.com
OPENWHISK_AUTH_KEY=your_auth_key
OPENWHISK_NAMESPACE=waddlebot

# Module Info
MODULE_NAME=router
MODULE_VERSION=1.0.0
```

#### Marketplace Module
```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/waddlebot

# Core API Integration
CORE_API_URL=http://router-service:8000
ROUTER_API_URL=http://router-service:8000/router

# Module Info
MODULE_NAME=marketplace
MODULE_VERSION=1.0.0
```

## System Components Details

### Router Module (`router_module/`) - CORE COMPONENT
- **High-Performance Processing**: Multi-threaded command processing with ThreadPoolExecutor
- **Command Routing**: Parses `!` (local container) and `#` (community Lambda/OpenWhisk) prefixed commands
- **Database Optimization**: Uses read replicas for command lookups, primary for writes
- **Caching Layer**: In-memory caching with TTL for commands and entity permissions
- **Rate Limiting**: Sliding window rate limiter with per-user/command/entity tracking
- **Execution Engine**: Routes to local containers, AWS Lambda, OpenWhisk, or webhook endpoints
- **Metrics & Monitoring**: Real-time performance metrics and health monitoring
- **Batch Processing**: Supports up to 100 concurrent event processing

### Marketplace Module (`marketplace_module/`) - CORE COMPONENT
- **Module Management**: Browse, search, install, and manage community modules
- **Permission System**: Entity-based permissions for module installation/management
- **Version Control**: Multiple module versions with upgrade/downgrade support
- **Review System**: User reviews and ratings for modules
- **Router Integration**: Automatic command registration/removal with router
- **Usage Analytics**: Track module usage and performance statistics
- **Category System**: Hierarchical module categorization

### Collector Modules

#### Twitch Module (`twitch_module/`)
- **EventSub Webhooks**: Handles follow, subscribe, cheer, raid, gift subscription events
- **OAuth Integration**: Complete OAuth flow with token management and refresh
- **API Integration**: Twitch Helix API for user info and subscription management
- **Activity Points**: follow=10, sub=50, bits=variable, raid=30, subgift=60, ban=-10

#### Discord Module (`discord_module/`)
- **py-cord Integration**: Uses py-cord library for Discord bot functionality
- **Event Handling**: Messages, reactions, member joins, voice states, server boosts
- **Slash Commands**: Built-in slash command support with py-cord
- **Voice Tracking**: Tracks voice channel participation with time-based points
- **Activity Points**: message=5, reaction=2, member_join=10, voice_join=8, voice_time=1/min, boost=100

#### Slack Module (`slack_module/`)
- **Event API**: Handles messages, reactions, file shares, channel joins
- **Slash Commands**: Custom `/waddlebot` command with help, status, points subcommands
- **Slack SDK**: Uses official Slack SDK for Python
- **User Caching**: Caches user information for performance
- **Activity Points**: message=5, file_share=15, reaction=3, member_join=10, app_mention=8

## Shared Patterns

### Database Schema (All Collectors)
```sql
-- Platform-specific tokens/auth
{platform}_tokens (team_id/guild_id/user_id, tokens, scopes, etc.)

-- Platform entities 
{platform}_teams/guilds/channels (platform_id, name, config, etc.)

-- Event logging
{platform}_events (event_id, type, platform_ids, event_data, processed)

-- Activity tracking
{platform}_activities (event_id, activity_type, user, amount, context_sent)

-- Shared tables
servers (owner, platform, channel, server_id, config)
collector_modules (module_name, platform, endpoint_url, status)
```

### Router Database Schema
```sql
-- Commands with execution routing
commands (
    id, command, prefix, description, location_url,
    location,      -- 'internal' for !, 'community' for #
    type,          -- 'container', 'lambda', 'openwhisk', 'webhook'
    method, timeout, headers, auth_required, rate_limit,
    is_active, module_type, module_id, version,
    trigger_type,  -- 'command', 'event', 'both'
    event_types,   -- JSON array of event types that trigger this module
    priority,      -- Lower number = higher priority
    execution_mode -- 'sequential', 'parallel'
)

-- Entity mappings (platform:server:channel)
entities (
    id, entity_id, platform, server_id, channel_id,
    owner, is_active, config
)

-- Command permissions per entity
command_permissions (
    id, command_id, entity_id, is_enabled, config,
    permissions, usage_count, last_used
)

-- Command execution audit log
command_executions (
    id, execution_id, command_id, entity_id, user_id,
    message_content, parameters, location_url,
    request_payload, response_status, response_data,
    execution_time_ms, error_message, retry_count, status
)

-- Rate limiting tracking
rate_limits (
    id, command_id, entity_id, user_id, window_start,
    request_count
)

-- String matching for content moderation and auto-responses
stringmatch (
    id, string, match_type, case_sensitive, enabled_entity_ids,
    action, command_to_execute, command_parameters, webhook_url,
    warning_message, block_message, priority, is_active,
    match_count, last_matched, created_by
)

-- Module responses from interaction modules and webhooks
module_responses (
    id, execution_id, module_name, success, response_action,
    response_data, media_type, media_url, ticker_text, ticker_duration,
    chat_message, error_message, processing_time_ms, created_at
)

-- Coordination table for dynamic server/channel assignment
coordination (
    id, platform, server_id, channel_id, entity_id, claimed_by,
    claimed_at, status, is_live, live_since, viewer_count,
    last_activity, last_check, last_checkin, claim_expires, 
    heartbeat_interval, error_count, metadata, priority, 
    max_containers, config, created_at, updated_at
)
```

### Event Processing Flow
1. **Message Reception**: Collector receives message/event from platform
2. **Message Type Classification**: Determine message type (chatMessage, subscription, follow, donation, etc.)
3. **Router Forwarding**: Send to router with entity context and message type
4. **Session Creation**: Router generates session_id and stores entity mapping in Redis
5. **Event-Based Processing**: Router processes differently based on message type:
   - **chatMessage**: Check for commands and string matches
   - **Non-chat events**: Process reputation and event-triggered modules directly
6. **Command Processing** (for chatMessage only):
   - **Command Detection**: Check for `!` (local container) or `#` (community module) prefix
   - **Command Lookup**: Router queries commands table with read replica
   - **String Matching Fallback**: If no command found, check message against string patterns for:
     - **Content Moderation**: Warn or block inappropriate content
     - **Auto-Responses**: Trigger commands based on message patterns
     - **Custom Actions**: Execute community modules based on string matches
7. **Permission Check**: Verify entity has command/module enabled
8. **Rate Limiting**: Check user/command/entity rate limits
9. **Multiple Module Execution**: 
   - **Sequential Modules**: Execute in priority order, wait for completion
   - **Parallel Modules**: Execute concurrently using ThreadPoolExecutor
   - **Event-Triggered Modules**: Execute modules configured for specific event types
10. **Execution Routing**: 
    - `!` commands → Local container interaction modules
    - `#` commands → Community Lambda/OpenWhisk functions
    - String match actions → warn, block, execute commands, or send to webhooks
    - Event triggers → Configured interaction modules
11. **Reputation Processing**: Process reputation points for all message types
12. **Module Response Processing**: Interaction modules respond back to router with:
    - **Session ID**: Required session_id for tracking
    - **Success Status**: Whether module executed properly
    - **Response Action**: chat, media, ticker, or form
    - **Response Data**: Content specific to action type
13. **Session Validation**: Router validates session_id matches entity_id
14. **Response Handling**: Return result to collector for user response and OBS integration
15. **Logging**: Record execution, performance metrics, usage stats, string match statistics, and module responses

### Command Prefix Architecture
- **`!` (Local Container Modules)**: Interaction modules running in local containers
  - Fast execution (container-to-container communication)
  - Full control over execution environment
  - Can maintain state and persistent connections
  - Examples: `!help`, `!stats`, `!admin`
  
- **`#` (Community Modules)**: Marketplace modules running in Lambda/OpenWhisk
  - Serverless execution for scalability
  - Community-contributed and marketplace-managed
  - Stateless functions with cold start considerations
  - Examples: `#weather`, `#translate`, `#game`

### Activity Processing Flow (Legacy)
1. **Event Reception**: Platform-specific webhook/event handler
2. **Event Logging**: Store raw event in `{platform}_events`
3. **Activity Extraction**: Determine activity type and point value
4. **Context Lookup**: Get user identity from core via `identity_name`
5. **Reputation Submission**: Send activity to core reputation API
6. **Activity Logging**: Store processed activity in `{platform}_activities`

### Router Architecture
- **Multi-Threading**: ThreadPoolExecutor with configurable worker count
- **Read Replicas**: Separate read connections for command lookups
- **Caching**: In-memory cache with TTL for frequently accessed data
- **Rate Limiting**: Sliding window algorithm with background cleanup
- **Batch Processing**: Process up to 100 events concurrently
- **Execution Engines**: Support for containers, Lambda, OpenWhisk, and webhooks
- **String Matching**: Content moderation and auto-response system with pattern matching
- **Metrics**: Real-time performance monitoring and health checks

### Router Communication Protocol
- **To Interaction Modules**: Router sends userID, community context, and user level for that community
- **Module Installation**: 
  - Marketplace modules are by default NOT added to communities
  - Core interaction modules are added to communities by default
  - Community owners can uninstall core interaction modules
  - Community modules can replace core interaction modules
- **Context Passing**: All module communications include full user context and permission level

### Community Portal System
- **Portal Access**: Community owners can generate portal access via `!community portal login add email@domain.com`
- **Native py4web Features**:
  - py4web Auth for user authentication and session management
  - py4web Mailer for email sending (SMTP/sendmail support)
  - py4web Forms for user input handling with validation
  - py4web Grid for data display and pagination
  - py4web Flash for user notifications
  - py4web Fixtures for access control and authentication
- **Dashboard Features**: 
  - View community members with roles and reputation scores
  - Monitor installed modules (core vs marketplace)
  - Community statistics and activity metrics
  - User management with numerical IDs and display names
- **Authentication**: py4web Auth with custom WaddleBot user fields
- **Email Configuration**: 
  - SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD, SMTP_TLS, SMTP_PORT environment variables
  - Automatic fallback to sendmail if SMTP not configured
- **Database Integration**: Uses py4web's auth_user table with custom fields for WaddleBot integration

### String Matching System
- **Pattern Matching**: Supports exact, contains, word boundary, and regex pattern matching
- **Wildcard Support**: Use `"*"` as pattern to match all text (universal trigger)
- **Content Moderation**: Automatic warning and blocking of inappropriate content
- **Auto-Responses**: Trigger commands based on message patterns
- **Webhook Integration**: Send matched content to external webhooks for processing
- **Entity-Based Rules**: Configure different rules per platform/server/channel
- **Priority System**: Lower number = higher priority for rule evaluation
- **Performance Optimized**: Cached compiled regex patterns and rule lookups
- **Usage Tracking**: Monitor rule effectiveness with match counts and timestamps
- **Match Types**:
  - `exact`: Exact string match (case sensitive/insensitive)
  - `contains`: Substring search within message
  - `word`: Word boundary matching (whole words only)
  - `regex`: Full regular expression support with compiled pattern caching
  - `*`: Universal wildcard - matches all text (useful for logging/analytics)
- **Actions**:
  - `warn`: Send warning message to user
  - `block`: Block message and send notification
  - `command`: Execute specified command with optional parameters
  - `webhook`: Send message data to external webhook URL for processing

### Module Response System
- **Response Tracking**: Track responses from interaction modules and webhooks
- **Session Management**: All responses must include session_id for tracking
- **Response Actions**: Support for chat, media, ticker, and form responses
- **Response Types**:
  - `chat`: Text-based chat response back to user
  - `media`: Full-screen media display (video, image, audio) for OBS integration
  - `ticker`: Scrolling text ticker for OBS browser source overlay
  - `form`: Interactive form for user input with field definitions
- **Form Response Structure**:
  - `form_title`: Title of the form
  - `form_description`: Description or instructions
  - `form_fields`: Array of field definitions with name, type, label, required, options
  - `form_submit_url`: URL to submit completed form
  - `form_submit_method`: HTTP method for submission (default: POST)
  - `form_callback_url`: URL to redirect after form submission
  - **Field Types**: text, textarea, select, multiselect, radio, checkbox, number, email, url, date, time
- **OBS Integration**:
  - **Media Response**: Full-screen video/image display in OBS scene
  - **Ticker Response**: Browser source with scrolling text overlay at bottom of screen
  - **Form Response**: Interactive form overlay for user input
  - **Configurable Duration**: Set how long ticker text displays (default: 10 seconds)
- **Success Tracking**: Monitor whether modules executed successfully
- **Performance Metrics**: Track module processing times and response rates
- **Error Handling**: Capture and log module errors for debugging

### Coordination System (Horizontal Scaling)
- **Dynamic Assignment**: Collector containers automatically claim available servers/channels
- **Load Distribution**: Distributes workload across multiple container instances
- **Live Stream Priority**: Prioritizes live streams/channels for higher engagement
- **Configurable Limits**: Each container claims up to configurable number (default: 5)
- **Platform Support**:
  - **Discord/Slack**: Claims servers with multiple channels
  - **Twitch**: Claims individual channels (no servers)
  - **Universal**: Supports any platform with server/channel concept
- **Claim Management**:
  - **Atomic Claims**: Race-condition safe claiming using database locks
  - **Expiration**: Claims expire after 30 minutes without heartbeat
  - **Checkin System**: Containers must checkin every 5 minutes to maintain claims
  - **Timeout**: Claims released if container misses checkin for 6+ minutes (1 minute grace period)
  - **Cleanup**: Automatic cleanup of expired claims and missed checkins
- **Status Tracking**:
  - **Live Status**: Track whether streams/channels are live
  - **Viewer Count**: Monitor audience size for prioritization
  - **Activity**: Track last message/activity timestamp
  - **Error Handling**: Track consecutive errors and mark entities as problematic
- **Horizontal Scaling**:
  - **Auto-Discovery**: New containers automatically find work
  - **Load Balancing**: Prioritizes live channels and high-priority entities
  - **Fault Tolerance**: Failed containers release claims for others to pick up
  - **Resource Optimization**: Containers can adjust claim count based on load
  - **Offline Management**: Containers automatically release offline entities and claim new ones
  - **Continuous Monitoring**: 5-minute checkin cycle ensures active monitoring and claim maintenance

### Message Types and Event Processing
- **Message Types**: All events sent to router must include a message_type field
- **Supported Message Types**:
  - `chatMessage`: User chat messages that may contain commands
  - `subscription`: User subscriptions/follows
  - `follow`: User follows
  - `donation`: User donations/tips
  - `cheer`: Twitch bits/cheers
  - `raid`: Twitch raids
  - `host`: Twitch hosts
  - `subgift`: Subscription gifts
  - `resub`: Subscription renewals
  - `reaction`: Message reactions
  - `member_join`: User joins server/channel
  - `member_leave`: User leaves server/channel
  - `voice_join`: User joins voice channel
  - `voice_leave`: User leaves voice channel
  - `voice_time`: Voice channel time tracking
  - `boost`: Discord server boosts
  - `ban`: User bans
  - `kick`: User kicks
  - `timeout`: User timeouts
  - `warn`: User warnings
  - `file_share`: File uploads
  - `app_mention`: Bot mentions
  - `channel_join`: Channel joins

### Multiple Module Execution
- **Module Matching**: Multiple modules can be triggered by a single message/event
- **Trigger Types**:
  - `command`: Triggered by command prefix (default behavior)
  - `event`: Triggered by specific event types
  - `both`: Triggered by both commands and events
- **Execution Modes**:
  - `sequential`: Execute modules one at a time in priority order
  - `parallel`: Execute modules concurrently using ThreadPoolExecutor
- **Priority System**: Lower numbers = higher priority (executed first)
- **Event Configuration**: Modules can specify which event types trigger them
- **Permission Enforcement**: All modules check entity permissions before execution

### Execution Engine Types
- **Container**: Local container modules for `!` commands (fast, stateful)
- **Lambda**: AWS Lambda functions for `#` commands (serverless, scalable)
- **OpenWhisk**: Apache OpenWhisk functions for `#` commands (open source serverless)
- **Webhook**: Generic HTTP endpoints for `#` commands (flexible integration)

### Marketplace Integration
- **Module Discovery**: Browse, search, and categorize community modules
- **Installation Management**: Install/uninstall modules per entity
- **Permission System**: Entity-based access control
- **Router Sync**: Automatic command registration with router
- **Version Control**: Support for multiple module versions
- **Usage Analytics**: Track module performance and adoption

### Core API Integration
All collectors follow the same pattern:
- **Registration**: Register module with core on startup
- **Heartbeat**: Send periodic health status
- **Server List**: Pull monitored servers/channels from core
- **Context API**: Lookup user identity for reputation tracking
- **Event Forwarding**: Send processed events to router for command processing

## Next Steps

1. **Complete Core Migration**: Migrate gateway from Flask to py4web
2. **Lambda Integration**: Connect action modules to AWS Lambda
3. **Kubernetes Deployment**: Full K8s deployment with monitoring
4. **Additional Collectors**: Matrix, Teams, IRC following established patterns
5. **Golang Migration**: Evaluate performance-critical components for Golang migration

## Security Considerations

- All webhooks must verify signatures (HMAC-SHA256 for Twitch)
- OAuth tokens stored securely with automatic refresh
- Database credentials in Kubernetes secrets
- Non-root containers with read-only filesystems
- Rate limiting on ingress
- HTTPS/TLS termination at ingress level

This context should be referenced for all future development to maintain consistency with the overall WaddleBot architecture and patterns.