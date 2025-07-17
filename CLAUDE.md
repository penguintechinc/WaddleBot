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
- **Database**: Default using PostgreSQL db server storing:
  - `servers` table: owner, platform (twitch/discord/slack), channel, configuration
  - Routes to Lambda functions
  - User logins, roles, permissions
  - Module registrations and configurations

### Technology Stack
- **Primary Framework**: py4web on Python 3.12
- **API Gateway**: Kong (open source) with declarative configuration
- **Database**: PyDAL library with a default of PostgreSQL with read replicas
- **Session Management**: Redis for session ID tracking
- **Containerization**: Docker containers
- **Orchestration**: Kubernetes (longer term)
- **Cloud Functions**: AWS Lambda and Apache OpenWHisk (longer term) for actions
- **Authentication**: Kong API Key authentication with consumer groups 
- **Future Migration**: Parts may migrate to Golang later

## Current Implementation

### Core System Components
- **router_module/**: High-performance command router with multi-threading, caching, and read replicas
- **marketplace_module/**: py4web-based community module marketplace and management system
- **portal_module/**: py4web-based community management portal with authentication and user dashboard
- **kong_admin_broker/**: Kong super admin user management service with full audit trail
- **chat/**: Matterbridge-based chat integration
- **gateway/**: Flask-based API gateway (DEPRECATED - migrated to Kong)
- **listener/**: Legacy Twitch authentication and activity listeners
- **libs/**: Shared libraries across modules

### Collector Modules (py4web-based)
- **twitch_module/**: Complete Twitch collector with EventSub webhooks, OAuth, and API integration
- **discord_module/**: Discord collector using py-cord library for bot events and slash commands
- **slack_module/**: Slack collector using Slack SDK for events and slash commands

### Interaction Modules (py4web-based)
- **ai_interaction_module/**: AI-powered interaction module supporting Ollama, OpenAI, and MCP providers for chat responses
- **alias_interaction_module/**: Linux-style alias system for custom commands with variable substitution
- **shoutout_interaction_module/**: Platform-specific user shoutouts with Twitch API integration and auto-shoutout functionality
- **inventory_interaction_module/**: Multi-threaded inventory management system for tracking any item (IRL or in-game) with label support and comprehensive AAA logging
- **youtube_music_interaction_module/**: YouTube Music integration with search, playback control, and media browser source output
- **spotify_interaction_module/**: Spotify integration with OAuth authentication, search, playback control, and media browser source output

### Core System Modules (py4web-based)
- **labels_core_module/**: High-performance multi-threaded label management system for communities, users, modules, and entity groups with user identity verification
- **browser_source_core_module/**: Multi-threaded browser source management system for OBS integration with ticker, media, and general display sources

### Administration Modules (py4web-based)
- **kong_admin_broker/**: Kong super admin user management with automated consumer creation, API key management, and comprehensive audit logging

### Collector Architecture
Each collector module:
- Runs as its own Docker container
- Has its own py4web implementation
- Pulls monitored servers/channels from PostgreSQL `servers` table
- Communicates with core via API when receiving chat/events
- Registers itself with core API
- Designed for handling a 1000+ chat channels at a time
- All configuration comes from environment variables passed through docker

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

### Comprehensive Logging Requirements (ALL MODULES)
All WaddleBot container modules MUST implement comprehensive Authentication, Authorization, and Auditing (AAA) logging:

**Required Logging Outputs:**
- **Console**: All logs output to stdout/stderr for container orchestration
- **File Logging**: Structured logs to `/var/log/waddlebotlog/` with rotation (10MB, 5 backups)
- **Syslog (Optional)**: Configurable syslog support for centralized logging

**Log Categories:**
- `AUTH`: Authentication events (login, logout, token refresh, failures)
- `AUTHZ`: Authorization events (permission checks, access grants/denials)
- `AUDIT`: User actions and system changes (CRUD operations, configuration changes)
- `ERROR`: Error conditions and exceptions
- `SYSTEM`: System events (startup, shutdown, health checks)

**Required Log Structure:**
```
[timestamp] LEVEL module:version EVENT_TYPE community=X user=Y action=Z result=STATUS [additional_fields]
```

**Log Configuration (Environment Variables):**
```bash
LOG_LEVEL=INFO                    # DEBUG, INFO, WARNING, ERROR
LOG_DIR=/var/log/waddlebotlog    # Log directory path
ENABLE_SYSLOG=false              # Enable syslog output
SYSLOG_HOST=localhost            # Syslog server host
SYSLOG_PORT=514                  # Syslog server port
SYSLOG_FACILITY=LOCAL0           # Syslog facility
```

**Implementation Requirements:**
- Use structured logging with consistent field names
- Include execution time for performance monitoring
- Log all user actions with community context
- Implement log rotation and retention policies
- Thread-safe logging for concurrent operations
- Decorator patterns for automatic audit logging
- Comprehensive error context and stack traces

### Performance Considerations
- **Threading**: Utilize ThreadPoolExecutor for concurrent operations when dealing with thousands of entities
  - RBAC service uses 10 worker threads for bulk operations
  - Bulk permission checks, role assignments, and user management operations
  - Concurrent processing for thousands of users/entities simultaneously
- **Database**: Separate each module and router operations into dedicated tables for better locking performance
  - Reduces contention on small number of tables
  - Allows concurrent role assignments without blocking membership operations
- **Bulk Operations**: Implement bulk processing methods for role assignments, permission checks, and user management
  - `check_permissions_bulk()` - Check multiple permissions concurrently
  - `assign_roles_bulk()` - Assign roles to multiple users concurrently
  - `ensure_users_in_global_community_bulk()` - Batch user onboarding
  - `get_user_roles_bulk()` - Retrieve roles for multiple users concurrently
- **Caching**: Use Redis caching for frequently accessed permissions and roles
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
├── ai_interaction_module/  # AI-powered interaction module
│   ├── controllers/    # Main interaction endpoints
│   ├── models.py      # Database models for AI interactions
│   ├── config.py      # AI provider configuration (Ollama/OpenAI/MCP)
│   ├── services/      # AI service providers and router communication
│   │   ├── ai_service.py      # Unified AI service abstraction
│   │   ├── ollama_provider.py # Ollama AI provider implementation
│   │   ├── openai_provider.py # OpenAI API provider implementation
│   │   ├── mcp_provider.py    # Model Context Protocol provider
│   │   └── router_service.py  # Router communication service
│   ├── templates/     # HTML templates
│   ├── Dockerfile     # Container definition
│   └── requirements.txt # Python dependencies including OpenAI
├── alias_interaction_module/  # Linux-style alias system
│   ├── app.py         # Main application with alias management
│   ├── requirements.txt # Python dependencies
│   ├── Dockerfile     # Container definition
│   └── k8s/          # Kubernetes deployment configs
├── shoutout_interaction_module/  # Platform-specific user shoutouts
│   ├── app.py         # Main application with shoutout functionality
│   ├── requirements.txt # Python dependencies
│   ├── Dockerfile     # Container definition
│   └── k8s/          # Kubernetes deployment configs
├── labels_core_module/  # High-performance multi-threaded label management system
│   ├── app.py         # Main application with labels, user verification, and entity groups
│   ├── requirements.txt # Python dependencies (py4web, redis, requests)
│   ├── Dockerfile     # Container definition
│   └── k8s/          # Kubernetes deployment configs
├── inventory_interaction_module/  # Multi-threaded inventory management system
│   ├── app.py        # Main application with inventory CRUD operations
│   ├── models.py     # Database models for inventory items and activity
│   ├── config.py     # Configuration and environment variables
│   ├── logging_config.py # Comprehensive AAA logging system
│   ├── services/     # Inventory services and router communication
│   ├── tests/        # Comprehensive unit tests
│   │   ├── test_inventory_service.py  # Service layer tests
│   │   ├── test_api.py                # API endpoint tests
│   │   └── __init__.py
│   ├── Dockerfile    # Container definition
│   ├── requirements.txt # Python dependencies
│   └── k8s/         # Kubernetes deployment configs
├── youtube_music_interaction_module/  # YouTube Music integration
│   ├── app.py        # Main application with YouTube Music commands
│   ├── models.py     # Database models for now playing, search cache, activity
│   ├── config.py     # YouTube API configuration
│   ├── services/     # YouTube Music service and router communication
│   │   ├── youtube_music_service.py  # YouTube Data API integration
│   │   └── router_service.py         # Router communication service
│   ├── Dockerfile    # Container definition
│   ├── requirements.txt # Python dependencies
│   └── k8s/         # Kubernetes deployment configs
├── spotify_interaction_module/  # Spotify integration
│   ├── app.py        # Main application with Spotify commands and OAuth
│   ├── models.py     # Database models for tokens, now playing, search cache
│   ├── config.py     # Spotify API configuration
│   ├── services/     # Spotify service and router communication
│   │   ├── spotify_service.py        # Spotify Web API integration
│   │   └── router_service.py         # Router communication service
│   ├── Dockerfile    # Container definition
│   ├── requirements.txt # Python dependencies
│   └── k8s/         # Kubernetes deployment configs
├── browser_source_core_module/  # Browser source management system
│   ├── app.py        # Main application with WebSocket and browser source handling
│   ├── models.py     # Database models for tokens, history, access logs
│   ├── config.py     # Browser source configuration
│   ├── services/     # Browser source services
│   │   ├── browser_source_service.py  # Browser source management
│   │   ├── websocket_service.py       # WebSocket handling
│   │   └── router_service.py          # Router communication service
│   ├── templates/    # HTML templates for browser sources
│   │   ├── ticker.html    # Ticker browser source template
│   │   ├── media.html     # Media browser source template
│   │   └── general.html   # General browser source template
│   ├── static/       # CSS and JavaScript for browser sources
│   │   ├── css/      # Styling for different source types
│   │   └── js/       # JavaScript for WebSocket and animations
│   ├── Dockerfile    # Container definition
│   ├── requirements.txt # Python dependencies
│   └── k8s/         # Kubernetes deployment configs
├── kong_admin_broker/  # Kong super admin user management
│   ├── controllers/   # Admin user management endpoints
│   │   └── admin.py   # Broker API endpoints for super admin management
│   ├── models.py     # Database models for users, audit log, backups
│   ├── config.py     # Broker and Kong admin configuration
│   ├── services/     # Kong integration and user management services
│   │   ├── kong_client.py     # Kong Admin API client for consumer management
│   │   └── user_manager.py    # Super admin user management service
│   ├── Dockerfile    # Container definition
│   ├── requirements.txt # Python dependencies
│   └── API.md        # Comprehensive API documentation
├── kong/             # Kong API Gateway configuration
│   ├── docker-compose.yml    # Kong deployment with PostgreSQL
│   ├── kong.yml      # Declarative Kong configuration
│   └── scripts/      # Kong setup and management scripts
├── chat/              # Existing Matterbridge integration
├── gateway/          # Existing Flask gateway (DEPRECATED - migrated to Kong)
├── listener/         # Existing Twitch listeners (LEGACY)
├── libs/            # Shared libraries
└── Premium/         # Premium mobile applications
    ├── LICENSE        # Premium-only license
    ├── Android/       # Native Android app (Kotlin/Jetpack Compose)
    │   ├── app/src/main/java/com/waddlebot/premium/
    │   │   ├── data/models/Models.kt      # Data models with subscription support
    │   │   ├── data/repository/           # Repository layer
    │   │   ├── presentation/              # UI screens and ViewModels
    │   │   │   ├── license/               # License acceptance screens
    │   │   │   ├── subscription/          # Subscription management
    │   │   │   └── common/                # Shared components
    │   │   └── ui/theme/                  # Material 3 theming
    │   ├── build.gradle.kts               # Build configuration
    │   ├── build.sh                       # Build script
    │   ├── WaddleBot-Premium-debug.apk    # Compiled APK
    │   └── .github/workflows/build.yml    # CI/CD pipeline
    └── iOS/           # Native iOS app (Swift/SwiftUI)
        ├── WaddleBotPremium/
        │   ├── Models/Models.swift        # Data models with subscription support
        │   ├── Services/                  # API services
        │   ├── Views/                     # SwiftUI views
        │   │   └── PremiumLicenseView.swift # License acceptance
        │   └── Utils/                     # Utilities and extensions
        └── WaddleBotPremium.xcodeproj     # Xcode project
```

## Integration Points

### Kong API Gateway Integration

All WaddleBot APIs are unified through Kong API Gateway for centralized routing, authentication, and rate limiting:

**Kong Services:**
- **router-service**: Core routing and command processing (`http://router-service:8000`)
- **marketplace-service**: Module marketplace and management (`http://marketplace-service:8001`)
- **ai-interaction**: AI services with multi-provider support (`http://ai-interaction:8005`)
- **kong-admin-broker**: Super admin user management (`http://kong-admin-broker:8000`)
- **twitch-collector**: Twitch platform integration (`http://twitch-collector:8002`)
- **discord-collector**: Discord platform integration (`http://discord-collector:8003`)
- **slack-collector**: Slack platform integration (`http://slack-collector:8004`)
- **youtube-music**: YouTube Music integration (`http://youtube-music:8025`)
- **spotify-interaction**: Spotify integration (`http://spotify-interaction:8026`)
- **browser-source**: Browser source management (`http://browser-source:8027`)

**Kong Routes:**
- `/router/*` → Router API (with authentication)
- `/marketplace/*` → Marketplace API (with authentication)
- `/ai/*` → AI Interaction API (with authentication)
- `/broker/*` → Kong Admin Broker API (broker key authentication)
- `/webhooks/twitch/*` → Twitch webhooks (with authentication)
- `/webhooks/discord/*` → Discord webhooks (with authentication)
- `/webhooks/slack/*` → Slack webhooks (with authentication)
- `/youtube/*` → YouTube Music API (with authentication)
- `/spotify/*` → Spotify API (with authentication)
- `/browser/*` → Browser Source API (with authentication)
- `/health` → Health checks (no authentication)
- `/ai/health` → AI health check (no authentication)
- `/broker/health` → Broker health check (no authentication)
- `/youtube/health` → YouTube Music health check (no authentication)
- `/spotify/health` → Spotify health check (no authentication)
- `/browser/health` → Browser Source health check (no authentication)

**Authentication & Authorization:**
- API Key authentication via `X-API-Key` header
- Broker Key authentication via `X-Broker-Key` header (admin operations)
- Consumer groups: `collectors`, `admins`, `services`, `api-users`, `super-admins`
- Rate limiting per service and consumer group
- CORS support for web applications

**Rate Limiting:**
- Router: 1000/min, 10000/hour
- Marketplace: 500/min, 5000/hour
- AI Interaction: 1000/min, 10000/hour
- Kong Admin Broker: 100/min, 1000/hour
- Collectors: 200/min, 2000/hour

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

### AI Interaction API Endpoints
- `POST /api/ai/v1/chat/completions` - OpenAI-compatible chat completions
- `POST /api/ai/v1/generate` - Simple text generation
- `GET /api/ai/v1/models` - List available AI models
- `GET /api/ai/v1/health` - AI service health check (no auth)
- `GET /api/ai/v1/config` - Get AI configuration
- `PUT /api/ai/v1/config` - Update AI configuration
- `GET /api/ai/v1/providers` - List available AI providers

### Kong Admin Broker API Endpoints
- `POST /api/broker/v1/super-admins` - Create Kong super admin user
- `GET /api/broker/v1/super-admins` - List all super admin users
- `GET /api/broker/v1/super-admins/{username}` - Get specific super admin user
- `PUT /api/broker/v1/super-admins/{username}` - Update super admin user
- `POST /api/broker/v1/super-admins/{username}/deactivate` - Deactivate super admin user
- `POST /api/broker/v1/super-admins/{username}/regenerate-key` - Regenerate API key
- `GET /api/broker/v1/audit-log` - Get comprehensive audit trail
- `POST /api/broker/v1/backup` - Backup all super admin users
- `GET /api/broker/v1/kong/info` - Get Kong server information
- `GET /api/broker/v1/kong/consumers` - List all Kong consumers
- `GET /api/broker/v1/statistics` - Get broker and Kong statistics
- `GET /api/broker/v1/health` - Broker health check (no auth)

### Browser Source API Endpoints
- `POST /browser/source/display` - Receive display data from router and distribute to browser sources
- `GET /browser/source/{token}/{source_type}` - Browser source display endpoint for OBS (no auth)
- `GET /browser/source/admin/tokens` - Get community browser source tokens
- `POST /browser/source/admin/tokens` - Generate new browser source tokens
- `GET /browser/source/api/communities/{community_id}/urls` - Get browser source URLs for community
- `POST /browser/source/admin/tokens/{token}/regenerate` - Regenerate browser source token
- `DELETE /browser/source/admin/tokens/{token}` - Deactivate browser source token
- `GET /browser/source/health` - Browser source health check (no auth)
- `GET /browser/source/stats` - Get browser source statistics and connection info
- `WebSocket /ws/{token}/{source_type}` - WebSocket endpoint for real-time browser source updates

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

#### AI Interaction Module
```bash
# AI Provider Configuration
AI_PROVIDER=ollama  # 'ollama', 'openai', or 'mcp'
AI_HOST=http://ollama:11434
AI_PORT=11434
AI_API_KEY=your_api_key

# Model Configuration
AI_MODEL=llama3.2
AI_TEMPERATURE=0.7
AI_MAX_TOKENS=500

# OpenAI Specific Configuration
OPENAI_API_KEY=sk-your-openai-key
OPENAI_MODEL=gpt-3.5-turbo
OPENAI_BASE_URL=https://api.openai.com/v1

# MCP Configuration
MCP_SERVER_URL=http://mcp-server:8080
MCP_TIMEOUT=30

# System Behavior
SYSTEM_PROMPT="You are a helpful chatbot assistant. Provide friendly, concise, and helpful responses to users in chat."
QUESTION_TRIGGERS=?
RESPONSE_PREFIX="🤖 "
RESPOND_TO_EVENTS=true
EVENT_RESPONSE_TYPES=subscription,follow,donation

# Performance Settings
MAX_CONCURRENT_REQUESTS=10
REQUEST_TIMEOUT=30
ENABLE_CHAT_CONTEXT=true
CONTEXT_HISTORY_LIMIT=5

# Database
DATABASE_URL=postgresql://user:pass@host:5432/waddlebot

# Core API Integration
CORE_API_URL=http://router:8000
ROUTER_API_URL=http://router:8000/router

# Module Info
MODULE_NAME=ai_interaction
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

#### Kong Admin Broker Module
```bash
# Kong Admin API Configuration
KONG_ADMIN_URL=http://kong:8001
KONG_ADMIN_USERNAME=admin
KONG_ADMIN_PASSWORD=admin_password

# Broker Security Configuration
BROKER_SECRET_KEY=waddlebot_broker_secret_key_change_me_in_production
BROKER_API_KEY=wbot_broker_master_key_placeholder
SUPER_ADMIN_GROUP=super-admins
API_KEY_LENGTH=64
REQUIRE_EMAIL_VERIFICATION=false

# Database
DATABASE_URL=postgresql://user:pass@host:5432/waddlebot

# Email Configuration (optional)
SMTP_HOST=smtp.company.com
SMTP_PORT=587
SMTP_USERNAME=broker@company.com
SMTP_PASSWORD=smtp_password
SMTP_TLS=true
FROM_EMAIL=noreply@waddlebot.com

# Performance Settings
MAX_CONCURRENT_REQUESTS=10
REQUEST_TIMEOUT=30
LOG_LEVEL=INFO

# Module Info
MODULE_NAME=kong_admin_broker
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

#### Labels Core Module
```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/waddlebot

# Redis Configuration
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=your_redis_password

# Core API Integration
CORE_API_URL=http://router-service:8000
ROUTER_API_URL=http://router-service:8000/router

# Performance Settings
MAX_WORKERS=20
CACHE_TTL=300
BULK_OPERATION_SIZE=1000
REQUEST_TIMEOUT=30

# Module Info
MODULE_NAME=labels_core
MODULE_VERSION=1.0.0
```

#### Inventory Interaction Module
```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/waddlebot

# Core API Integration
CORE_API_URL=http://router-service:8000
ROUTER_API_URL=http://router-service:8000/router

# Performance Settings
MAX_WORKERS=20
MAX_LABELS_PER_ITEM=5
CACHE_TTL=300
REQUEST_TIMEOUT=30

# AAA Logging Configuration
LOG_LEVEL=INFO
LOG_DIR=/var/log/waddlebotlog
ENABLE_SYSLOG=false
SYSLOG_HOST=localhost
SYSLOG_PORT=514
SYSLOG_FACILITY=LOCAL0

# Module Info
MODULE_NAME=inventory_interaction_module
MODULE_VERSION=1.0.0
MODULE_PORT=8024
```

#### YouTube Music Interaction Module
```bash
# YouTube API Configuration
YOUTUBE_API_KEY=your_youtube_api_key_here
YOUTUBE_API_VERSION=v3
YOUTUBE_MUSIC_CATEGORY_ID=10
YOUTUBE_REGION_CODE=US

# Database
DATABASE_URL=postgresql://user:pass@host:5432/waddlebot

# Core API Integration
CORE_API_URL=http://router-service:8000
ROUTER_API_URL=http://router-service:8000/router

# Browser Source Integration
BROWSER_SOURCE_API_URL=http://browser-source:8027/browser/source

# Performance Settings
MAX_SEARCH_RESULTS=10
CACHE_TTL=300
REQUEST_TIMEOUT=30
MAX_QUEUE_SIZE=50

# Feature Flags
ENABLE_PLAYLISTS=true
ENABLE_QUEUE=true
ENABLE_HISTORY=true
ENABLE_AUTOPLAY=true

# AAA Logging Configuration
LOG_LEVEL=INFO
LOG_DIR=/var/log/waddlebotlog
ENABLE_SYSLOG=false

# Module Info
MODULE_NAME=youtube_music_interaction
MODULE_VERSION=1.0.0
MODULE_PORT=8025
```

#### Spotify Interaction Module
```bash
# Spotify API Configuration
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
SPOTIFY_REDIRECT_URI=http://localhost:8026/spotify/auth/callback
SPOTIFY_SCOPES=user-read-playback-state user-modify-playback-state user-read-currently-playing streaming

# Database
DATABASE_URL=postgresql://user:pass@host:5432/waddlebot

# Core API Integration
CORE_API_URL=http://router-service:8000
ROUTER_API_URL=http://router-service:8000/router

# Browser Source Integration
BROWSER_SOURCE_API_URL=http://browser-source:8027/browser/source

# Performance Settings
MAX_SEARCH_RESULTS=10
CACHE_TTL=300
REQUEST_TIMEOUT=30
TOKEN_REFRESH_BUFFER=300

# Feature Flags
ENABLE_PLAYLISTS=true
ENABLE_QUEUE=true
ENABLE_HISTORY=true
ENABLE_DEVICE_CONTROL=true

# Media Display Settings
MEDIA_DISPLAY_DURATION=30
SHOW_ALBUM_ART=true
SHOW_PROGRESS_BAR=true

# AAA Logging Configuration
LOG_LEVEL=INFO
LOG_DIR=/var/log/waddlebotlog
ENABLE_SYSLOG=false

# Module Info
MODULE_NAME=spotify_interaction
MODULE_VERSION=1.0.0
MODULE_PORT=8026
```

#### Browser Source Core Module
```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/waddlebot

# Core API Integration
CORE_API_URL=http://router-service:8000
ROUTER_API_URL=http://router-service:8000/router

# WebSocket Configuration
WEBSOCKET_HOST=0.0.0.0
WEBSOCKET_PORT=8028
MAX_CONNECTIONS=1000

# Performance Settings
MAX_WORKERS=50
QUEUE_PROCESSING_INTERVAL=1
CLEANUP_INTERVAL=300
TICKER_QUEUE_SIZE=100

# Browser Source Settings
BASE_URL=http://localhost:8027
TOKEN_LENGTH=32
ACCESS_LOG_RETENTION_DAYS=30

# Display Settings
DEFAULT_TICKER_DURATION=10
DEFAULT_MEDIA_DURATION=30
MAX_TICKER_LENGTH=200

# AAA Logging Configuration
LOG_LEVEL=INFO
LOG_DIR=/var/log/waddlebotlog
ENABLE_SYSLOG=false

# Module Info
MODULE_NAME=browser_source_core
MODULE_VERSION=1.0.0
MODULE_PORT=8027
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

### Kong Admin Broker Module (`kong_admin_broker/`) - ADMINISTRATION COMPONENT
- **Super Admin Management**: Complete CRUD operations for Kong super admin users
- **Automated Kong Integration**: Creates Kong consumers, API keys, and ACL group memberships
- **Audit Trail**: Comprehensive logging of all administrative actions with full context
- **API Key Management**: Secure 64-character API key generation and rotation capabilities
- **Backup & Recovery**: Complete backup system for Kong consumer configurations
- **Health Monitoring**: Kong Admin API connectivity and status monitoring
- **Security Features**: Broker-level authentication, rate limiting, and access control
- **Database Schema**: Dedicated tables for users, audit logs, sessions, and backups
- **Kong Consumer Lifecycle**: Full lifecycle management from creation to deactivation
- **Permission System**: Role-based access with super-admin, admin, and service tiers

### Labels Core Module (`labels_core_module/`) - CORE COMPONENT
- **High-Performance Architecture**: Multi-threaded processing with ThreadPoolExecutor (configurable max workers)
- **Redis Caching**: High-performance caching layer with fallback to local cache
- **Bulk Operations**: Support for up to 1000 items per batch operation for high-volume requests
- **Label Management**: Track labels on communities, modules, users, and entityGroups (up to 5 labels per community, 5 per user per community)
- **User Identity Verification**: Time-limited verification codes to link platform identities to bot identities
- **Entity Group Management**: Auto-role assignment in Discord, Slack, and Twitch based on user labels
- **Search Functionality**: Search modules, users, and entities by labels with caching
- **Background Processing**: Asynchronous task queue for long-running operations
- **Performance Monitoring**: Real-time metrics and health monitoring in health endpoint
- **Database Optimization**: Proper indexing and connection pooling for thousands of requests per second

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

### Interaction Modules

#### AI Interaction Module (`ai_interaction_module/`)
- **Multi-Provider Support**: Unified interface supporting Ollama, OpenAI, and MCP (Model Context Protocol) providers
- **Provider Configuration**: Environment variable `AI_PROVIDER` selects between 'ollama', 'openai', or 'mcp'
- **Configurable System Prompt**: Default helpful chatbot assistant prompt, customizable via `SYSTEM_PROMPT` environment variable
- **Conversation Context**: Optional conversation history tracking for contextual responses
- **Event Response Support**: Responds to subscription, follow, donation, and other platform events
- **Question Detection**: Configurable triggers (default: '?') to determine when to respond to chat messages
- **Response Modes**: Supports chat responses with configurable prefix
- **Health Monitoring**: Provider-specific health checks and failover capabilities
- **Dynamic Configuration**: Runtime configuration updates for model, temperature, tokens, and provider settings

**Provider Implementations**:
- **Ollama Provider**: Uses LangChain with Ollama for local LLM hosting
- **OpenAI Provider**: Direct OpenAI API integration with chat completions
- **MCP Provider**: Model Context Protocol for standardized AI model communication

**Configuration**:
```bash
# AI Provider Selection
AI_PROVIDER=ollama  # 'ollama', 'openai', or 'mcp'
AI_HOST=http://ollama:11434
AI_PORT=11434
AI_API_KEY=your_api_key

# Model Configuration
AI_MODEL=llama3.2
AI_TEMPERATURE=0.7
AI_MAX_TOKENS=500

# OpenAI Specific
OPENAI_API_KEY=sk-your-key
OPENAI_MODEL=gpt-3.5-turbo
OPENAI_BASE_URL=https://api.openai.com/v1

# MCP Configuration
MCP_SERVER_URL=http://mcp-server:8080
MCP_TIMEOUT=30

# System Behavior
SYSTEM_PROMPT="You are a helpful chatbot assistant. Provide friendly, concise, and helpful responses to users in chat."
QUESTION_TRIGGERS=?
RESPONSE_PREFIX=> 
RESPOND_TO_EVENTS=true
EVENT_RESPONSE_TYPES=subscription,follow,donation
```

#### Alias Interaction Module (`alias_interaction_module/`)
- **Linux-Style Aliases**: Commands work like Linux bash aliases with `!alias add !user "!so user"`
- **Variable Substitution**: Support for `{user}`, `{args}`, `{arg1}`, `{arg2}`, `{all_args}` placeholders
- **Alias Management**: Add, remove, list aliases with proper permission checking
- **Command Execution**: Routes aliased commands through the router system
- **Usage Statistics**: Track alias usage and performance

**Key Features**:
- `!alias add <alias_name> <command>` - Create new alias
- `!alias remove <alias_name>` - Remove existing alias
- `!alias list` - List all configured aliases
- Variable substitution in commands
- Integration with router for command execution

#### Shoutout Interaction Module (`shoutout_interaction_module/`)
- **Platform Integration**: Twitch API integration for user information and clips
- **Auto-Shoutout**: Automatic shoutouts on follow/subscribe/raid events
- **User Management**: Community managers can configure user-specific settings
- **Twitch Features**: Pulls random clips for full-screen media display
- **Custom Messages**: Personalized shoutout messages with additional links

**Key Features**:
- `!so <username>` or `!shoutout <username>` - Manual shoutout
- Auto-shoutout on platform events with cooldown (1 hour)
- Twitch API integration for user info and last game played
- Random clip selection for full-screen OBS integration
- Custom message and link management per user
- Shoutout history and analytics

**Twitch API Integration**:
- User profile information lookup
- Last game played detection
- Random clip selection from past 7 days
- Full-screen media response for OBS scenes

#### Inventory Interaction Module (`inventory_interaction_module/`)
- **Multi-Threaded Architecture**: ThreadPoolExecutor for concurrent operations (20 workers)
- **Item Management**: Track any item whether IRL or in-game with comprehensive CRUD operations
- **Label System**: Support up to 5 labels per item for categorization and filtering
- **Caching**: High-performance caching with thread-safe operations
- **Comprehensive AAA Logging**: Full Authentication, Authorization, and Auditing logging system

**Key Features**:
- `!inventory add <item_name> <description> [labels]` - Add new item to inventory
- `!inventory checkout <item_name> <username>` - Check out item to user
- `!inventory checkin <item_name>` - Check item back in
- `!inventory delete <item_name>` - Remove item from inventory
- `!inventory list [all|available|checkedout]` - List items with filtering
- `!inventory search <query>` - Search items by name, description, or labels
- `!inventory status <item_name>` - Get item status and checkout information
- `!inventory stats` - Get inventory statistics and metrics
- `!inventory labels <item_name> <add|remove> <label>` - Manage item labels

**Database Schema**:
```sql
inventory_items (
    id, community_id, item_name, description, labels,
    is_checked_out, checked_out_to, checked_out_at, checked_in_at,
    created_by, created_at, updated_at
)

inventory_activity (
    id, community_id, item_id, action, performed_by,
    details, created_at
)
```

**Performance Features**:
- Thread-safe caching with TTL for frequently accessed data
- Bulk operations support for high-volume communities
- Connection pooling for database operations
- Background activity logging for audit trails
- Health monitoring with comprehensive metrics

#### YouTube Music Interaction Module (`youtube_music_interaction_module/`)
- **YouTube Data API v3 Integration**: Direct integration with YouTube API for music search and metadata
- **Search and Playback**: Search YouTube Music tracks and queue for playback
- **Media Browser Source Output**: Sends track information with album art to browser source for OBS
- **Now Playing Tracking**: Stores current playing track information per community
- **Search Result Caching**: Caches search results for quick access via number selection
- **Playlist Management**: Support for community playlists and queue management
- **Activity Logging**: Comprehensive tracking of all music commands and playback

**Key Features**:
- `!ytmusic search <query>` - Search YouTube Music
- `!ytmusic play <url/number>` - Play track or search result
- `!ytmusic current` - Show current playing track with ticker display
- `!ytmusic stop` - Stop playback and clear now playing
- Media browser source integration for OBS with track art and metadata
- Search result numbering for quick selection
- Playback history and analytics

**Database Schema**:
```sql
youtube_now_playing (
    community_id, video_id, title, artist, album, duration,
    thumbnail_url, requested_by, started_at, updated_at
)

youtube_search_cache (
    community_id, user_id, query, results, created_at
)

youtube_activity (
    community_id, user_id, action, details, created_at
)
```

#### Spotify Interaction Module (`spotify_interaction_module/`)
- **Spotify Web API Integration**: OAuth 2.0 authentication with full playback control
- **Real-time Playback Control**: Play, pause, skip, volume control on user's Spotify devices
- **Device Management**: List and control playback on multiple Spotify devices
- **Media Browser Source Output**: Rich media display with album art, progress bars, and track info
- **Token Management**: Automatic token refresh and secure storage
- **Search and Queue**: Advanced search with playlist integration
- **Multi-User Support**: Per-user authentication within communities

**Key Features**:
- `!spotify search <query>` - Search Spotify catalog
- `!spotify play <uri/number>` - Play track on user's Spotify device
- `!spotify current` - Show current playback with progress and device info
- `!spotify pause/resume` - Control playback state
- `!spotify skip` - Skip to next track
- `!spotify devices` - List available Spotify devices
- OAuth authentication flow with secure token management
- Media browser source with real-time progress updates

**Database Schema**:
```sql
spotify_tokens (
    community_id, user_id, access_token, refresh_token,
    expires_at, scope, created_at, updated_at
)

spotify_now_playing (
    community_id, track_uri, track_name, artists, album,
    duration_ms, album_art_url, is_playing, progress_ms,
    requested_by, started_at, updated_at
)

spotify_search_cache (
    community_id, user_id, query, results, created_at
)
```

#### Browser Source Core Module (`browser_source_core_module/`)
- **Multi-threaded Architecture**: ThreadPoolExecutor for handling hundreds of concurrent browser sources
- **WebSocket Communication**: Real-time updates to browser sources via WebSocket connections
- **Three Source Types**: Ticker, Media, and General browser sources for different display needs
- **Unique Community URLs**: Each community gets unique URLs for each source type with secure tokens
- **OBS Integration**: Optimized for OBS Studio browser source plugin with auto-refresh and styling
- **Router Integration**: Receives display data from interaction modules via router
- **Portal Integration**: Community admins can view and manage browser source URLs

**Browser Source Types**:
- **Ticker Source**: Scrolling text messages at bottom of screen for notifications and alerts
- **Media Source**: Rich media display for music, videos, images with metadata and progress
- **General Source**: Custom HTML/CSS content for forms, announcements, and interactive elements

**Key Features**:
- Unique URLs per community: `/browser/source/{token}/ticker`, `/browser/source/{token}/media`, `/browser/source/{token}/general`
- WebSocket real-time updates for immediate display changes
- Queue management for ticker messages with priority and duration
- Media attribution display with artist, song name, album art, and progress bars
- Responsive design that works across different OBS scene sizes
- Access logging and analytics for browser source usage
- Token management with regeneration capabilities

**Database Schema**:
```sql
browser_source_tokens (
    community_id, source_type, token, is_active, created_at
)

browser_source_history (
    community_id, source_type, content, session_id, created_at
)

browser_source_access_log (
    community_id, source_type, ip_address, user_agent, accessed_at
)
```

**Integration Flow**:
1. **Module Response**: Interaction module sends response with browser source data
2. **Router Processing**: Router routes browser source responses to browser source core module
3. **WebSocket Distribution**: Browser source module distributes updates via WebSocket to connected sources
4. **OBS Display**: Browser sources in OBS receive updates and display content in real-time
5. **Portal Management**: Community admins can view URLs and manage settings through portal

**Music Module Browser Source Integration**:
- YouTube Music and Spotify modules send media responses to browser source core
- Media browser source displays track information with album art and attribution
- Real-time progress updates for Spotify playback
- Automatic timeout and cleanup for media displays
- Responsive design for different OBS scene layouts

**Browser Source Implementation Details**:
- **Transparent Backgrounds**: All browser source templates use `background: transparent;` for proper OBS compositing
- **WebSocket Communication**: Real-time bidirectional communication between browser sources and core module
- **Multi-threaded Processing**: ThreadPoolExecutor handles hundreds of concurrent connections
- **Connection Management**: Automatic connection tracking, cleanup, and stale connection removal
- **Queue System**: Priority-based message queuing for ticker with overflow protection
- **Analytics Integration**: Comprehensive tracking of browser source usage and interactions
- **Template System**: Modular HTML/CSS/JS templates for each source type
- **Responsive Design**: Works across different OBS scene sizes and aspect ratios
- **Security**: Token-based authentication with unique URLs per community and source type

**Browser Source Templates**:
- **Ticker Template**: Scrolling text with animations, priority queuing, and style variants
- **Media Template**: Music display with album art, progress bars, and service indicators
- **General Template**: Flexible content display with HTML, forms, announcements, and alerts
- **CSS Framework**: Modern CSS with animations, transitions, and responsive design
- **JavaScript**: WebSocket handling, automatic reconnection, and analytics tracking

**OBS Integration Features**:
- **Transparent Backgrounds**: Proper alpha channel support for overlay compositing
- **Auto-refresh**: Automatic reconnection on connection loss
- **Performance Optimized**: Minimal resource usage with efficient DOM updates
- **Cross-browser**: Compatible with OBS browser source engine
- **Responsive Layouts**: Adapts to different scene sizes and orientations

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
    - **Response Action**: chat, media, ticker, general, or form
    - **Response Data**: Content specific to action type
13. **Browser Source Routing**: Router routes browser source responses to browser source core module:
    - **Media Responses**: Music/video with album art and metadata
    - **Ticker Responses**: Scrolling text with priority and styling
    - **General Responses**: HTML content, forms, announcements, and alerts
    - **WebSocket Distribution**: Browser source core distributes to connected OBS sources
14. **Session Validation**: Router validates session_id matches entity_id
15. **Response Handling**: Return result to collector for user response and OBS integration
16. **Logging**: Record execution, performance metrics, usage stats, string match statistics, and module responses

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
  - `media`: Rich media display for music/video with album art and metadata
  - `ticker`: Scrolling text ticker for notifications and alerts
  - `general`: Flexible content display for HTML, forms, announcements, and alerts
  - `form`: Interactive form for user input with field definitions
- **Form Response Structure**:
  - `form_title`: Title of the form
  - `form_description`: Description or instructions
  - `form_fields`: Array of field definitions with name, type, label, required, options
  - `form_submit_url`: URL to submit completed form
  - `form_submit_method`: HTTP method for submission (default: POST)
  - `form_callback_url`: URL to redirect after form submission
  - **Field Types**: text, textarea, select, multiselect, radio, checkbox, number, email, url, date, time
- **Browser Source Integration**:
  - **Media Response**: Rich media display with album art, track info, and progress bars
  - **Ticker Response**: Scrolling text overlay with priority queuing and animations
  - **General Response**: Flexible content display for HTML, forms, announcements, and alerts
  - **Form Response**: Interactive form overlay with field validation and submission
  - **Transparent Backgrounds**: All browser sources use transparent backgrounds for OBS compositing
  - **WebSocket Updates**: Real-time updates via WebSocket connections
  - **Configurable Duration**: Set display duration for each response type
  - **Responsive Design**: Adapts to different OBS scene sizes and layouts
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
- **Paid Subscription System**: Complete subscription management with payment blocking for expired subscriptions

### Core API Integration
All collectors follow the same pattern:
- **Registration**: Register module with core on startup
- **Heartbeat**: Send periodic health status
- **Server List**: Pull monitored servers/channels from core
- **Context API**: Lookup user identity for reputation tracking
- **Event Forwarding**: Send processed events to router for command processing

## CI/CD and Build System

### GitHub Actions Workflows
WaddleBot uses comprehensive GitHub Actions for automated building, testing, and deployment:

**Main CI/CD Pipeline (`.github/workflows/ci-cd.yml`)**:
- **Multi-Platform Builds**: Docker containers for linux/amd64 and linux/arm64
- **Security Scanning**: Trivy vulnerability scanning and CodeQL analysis
- **Comprehensive Testing**: Unit tests, integration tests, and code coverage reporting
- **Container Registry**: Automated pushing to container registries
- **Quality Gates**: All tests must pass before deployment

**Container-Specific Pipeline (`.github/workflows/containers.yml`)**:
- **Change Detection**: Only builds containers that have been modified
- **Matrix Builds**: Parallel builds for all core, collector, and interaction modules
- **Integration Testing**: Cross-module integration tests
- **Performance Testing**: Load testing for high-volume modules

**Android App Pipeline (`.github/workflows/android.yml`)**:
- **Static Analysis**: Lint checking and code quality analysis
- **Unit Testing**: JUnit tests with coverage reporting
- **Instrumentation Testing**: UI and integration tests on Android emulator
- **Build Artifacts**: APK and AAB generation for distribution
- **Play Store Deployment**: Automated deployment to internal testing track

**Desktop Bridge Pipeline (`.github/workflows/desktop-bridge.yml`)**:
- **Cross-Platform Compilation**: Windows, macOS, and Linux builds
- **Go Testing**: Comprehensive testing including benchmarks
- **Release Management**: Automated release creation with checksums
- **Binary Distribution**: Multi-platform binary artifacts

**Required CI/CD Standards**:
- All modules must have comprehensive unit tests (>90% coverage)
- Integration tests for API endpoints and database operations
- Dockerfile optimization with multi-stage builds and security scanning
- Kubernetes deployment manifests with health checks and resource limits
- Performance benchmarking for high-throughput modules

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