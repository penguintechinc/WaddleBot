# WaddleBot Usage Guide

This guide covers how to build, configure, and run WaddleBot's various Docker containers and applications.

## Overview

WaddleBot uses a microservices architecture with multiple Docker containers:

- **Core Services**: Router, Identity, Portal, Marketplace
- **Collector Modules**: Twitch, Discord, Slack platform integrations
- **Interaction Modules**: AI, Alias, Shoutout, Inventory, Calendar, Memories
- **Media Modules**: YouTube Music, Spotify, Browser Source
- **Infrastructure**: Kong Gateway, PostgreSQL, Redis

### Prerequisites

- Docker and Docker Compose
- PostgreSQL database
- Redis server
- Platform API credentials (Twitch, Discord, Slack)

### Quick Start

1. **Copy environment template:**
```bash
cp .env.example .env
```

2. **Configure your `.env` file** with your database credentials, API keys, and platform tokens

3. **Start the core services:**
```bash
docker-compose up -d db redis kong
```

4. **Deploy your desired modules:**
```bash
docker-compose up -d router identity-core twitch-collector discord-collector
```

## Environment Configuration

### Database Configuration
```bash
# PostgreSQL settings
POSTGRES_USER=waddlebot
POSTGRES_PASSWORD=your_secure_password_here
POSTGRES_DB=waddlebot
DATABASE_URL=postgresql://waddlebot:your_secure_password_here@db:5432/waddlebot
READ_REPLICA_URL=postgresql://waddlebot:your_secure_password_here@db-read:5432/waddlebot
```

### Redis Configuration
```bash
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=optional_redis_password
```

### Core API URLs
```bash
CORE_API_URL=http://router:8000
ROUTER_API_URL=http://router:8000/router
CONTEXT_API_URL=http://router:8000/api/context
REPUTATION_API_URL=http://router:8000/api/reputation
```

## Build Options

### Universal Build Arguments

All Docker containers support these common build arguments:

```dockerfile
ARG PYTHON_VERSION=3.12
ARG PY4WEB_VERSION=latest
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION
```

### Build Commands

Build individual modules:
```bash
docker build -t waddlebot/router:latest ./router_module
docker build -t waddlebot/twitch:latest ./twitch_module
docker build -t waddlebot/discord:latest ./discord_module
```

Build with custom Python version:
```bash
docker build --build-arg PYTHON_VERSION=3.11 -t waddlebot/router:3.11 ./router_module
```

## Core Services

## Router Module

**Purpose**: Central command routing and execution engine

**Build Options:**
```bash
docker build -t waddlebot/router ./router_module
```

**Environment Variables:**
```bash
# Module Configuration
MODULE_NAME=router
MODULE_VERSION=1.0.0
MODULE_PORT=8000

# Performance Settings
ROUTER_MAX_WORKERS=20              # Thread pool size
ROUTER_MAX_CONCURRENT=100          # Max concurrent requests
ROUTER_REQUEST_TIMEOUT=30          # Request timeout in seconds
ROUTER_DEFAULT_RATE_LIMIT=60       # Default rate limit per minute

# Caching
ROUTER_COMMAND_CACHE_TTL=300       # Command cache TTL (seconds)
ROUTER_ENTITY_CACHE_TTL=600        # Entity cache TTL (seconds)

# Database
DATABASE_URL=postgresql://user:pass@db:5432/waddlebot
READ_REPLICA_URL=postgresql://user:pass@db-read:5432/waddlebot

# Session Management
REDIS_HOST=redis
SESSION_TTL=3600                   # Session expiry (seconds)

# Execution Engines
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
LAMBDA_FUNCTION_PREFIX=waddlebot-

OPENWHISK_API_HOST=openwhisk.example.com
OPENWHISK_AUTH_KEY=your_auth_key
OPENWHISK_NAMESPACE=waddlebot
```

**Key Features:**
- Multi-threaded command processing
- Database read replicas for performance
- Redis session management
- Rate limiting with sliding windows
- AWS Lambda and OpenWhisk integration

## Identity Core Module

**Purpose**: Cross-platform identity linking and user authentication

**Build Options:**
```bash
docker build -t waddlebot/identity-core ./identity_core_module
```

**Environment Variables:**
```bash
# Module Configuration
MODULE_NAME=identity_core_module
MODULE_VERSION=1.0.0
MODULE_PORT=8050

# Security
SECRET_KEY=waddlebot_identity_secret_key_change_me_in_production
SESSION_TTL=3600

# API Keys
VALID_API_KEYS=system_key1,system_key2
MAX_API_KEYS_PER_USER=5
API_KEY_DEFAULT_EXPIRY_DAYS=365

# Verification Settings
VERIFICATION_CODE_LENGTH=6
VERIFICATION_TIMEOUT_MINUTES=10
RESEND_COOLDOWN_SECONDS=60
MAX_VERIFICATION_ATTEMPTS=5

# Platform APIs (for whisper/DM functionality)
TWITCH_API_URL=http://twitch-collector:8002
DISCORD_API_URL=http://discord-collector:8003
SLACK_API_URL=http://slack-collector:8004

# Email Configuration (py4web Mailer)
SMTP_HOST=smtp.company.com
SMTP_PORT=587
SMTP_USERNAME=identity@company.com
SMTP_PASSWORD=smtp_password
SMTP_TLS=true
FROM_EMAIL=noreply@waddlebot.com

# Performance
MAX_WORKERS=20
CACHE_TTL=300
REQUEST_TIMEOUT=30
BULK_OPERATION_SIZE=100

# Rate Limiting
RATE_LIMIT_REQUESTS=60
RATE_LIMIT_WINDOW=60

# Feature Flags
ENABLE_EMAIL_VERIFICATION=false
ENABLE_TWO_FACTOR=false
ENABLE_OAUTH_PROVIDERS=false
```

**Key Features:**
- py4web Auth foundation with extended user fields
- Cross-platform identity verification via whispers/DMs
- Self-service API key management
- Multi-threaded processing with Redis caching

## Portal Module

**Purpose**: Web-based community management interface

**Build Options:**
```bash
docker build -t waddlebot/portal ./portal_module
```

**Environment Variables:**
```bash
# Module Configuration
MODULE_NAME=portal
MODULE_VERSION=1.0.0
MODULE_PORT=8000

# Portal Configuration
PORTAL_URL=http://localhost:8000
APP_NAME=WaddleBot Community Portal

# Email Configuration (py4web Mailer)
SMTP_HOST=smtp.company.com
SMTP_PORT=587
SMTP_USERNAME=portal@company.com
SMTP_PASSWORD=smtp_password
SMTP_TLS=true
FROM_EMAIL=noreply@waddlebot.com

# Browser Source Integration
BROWSER_SOURCE_BASE_URL=http://browser-source-core:8027

# Database
DATABASE_URL=postgresql://user:pass@db:5432/waddlebot
```

**Key Features:**
- py4web-based community management portal
- User authentication and role management
- Browser source URL management
- Email integration for notifications

## Collector Modules

## Twitch Module

**Purpose**: Twitch platform integration with EventSub webhooks

**Build Options:**
```bash
docker build -t waddlebot/twitch ./twitch_module
```

**Environment Variables:**
```bash
# Module Configuration
MODULE_NAME=twitch
MODULE_VERSION=1.0.0
MODULE_PORT=8002

# Twitch API Configuration
TWITCH_APP_ID=your_twitch_app_id
TWITCH_APP_SECRET=your_twitch_app_secret
TWITCH_CLIENT_ID=your_twitch_client_id
TWITCH_CLIENT_SECRET=your_twitch_client_secret
TWITCH_ACCESS_TOKEN=your_twitch_access_token

# Webhook Configuration
TWITCH_WEBHOOK_SECRET=your_webhook_secret
TWITCH_WEBHOOK_CALLBACK_URL=https://yourdomain.com/twitch/webhook
TWITCH_REDIRECT_URI=https://yourdomain.com/twitch/auth/callback

# Coordination System
MAX_CLAIMS=5                       # Max channels per container
HEARTBEAT_INTERVAL=300             # Heartbeat interval (seconds)
CONTAINER_ID=twitch_container_1    # Unique container identifier

# Core API Integration
CORE_API_URL=http://router:8000
CONTEXT_API_URL=http://router:8000/api/context
REPUTATION_API_URL=http://router:8000/api/reputation
GATEWAY_ACTIVATE_URL=http://router:8000/api/gateway/activate

# Database
DATABASE_URL=postgresql://user:pass@db:5432/waddlebot
```

**Key Features:**
- Twitch EventSub webhook integration
- OAuth flow with token refresh
- Horizontal scaling with coordination system
- Activity point tracking (follow=10, sub=50, bits=variable, raid=30, subgift=60, ban=-10)

## Discord Module

**Purpose**: Discord bot integration with py-cord

**Build Options:**
```bash
docker build -t waddlebot/discord ./discord_module
```

**Environment Variables:**
```bash
# Module Configuration
MODULE_NAME=discord
MODULE_VERSION=1.0.0
MODULE_PORT=8003

# Discord Bot Configuration
DISCORD_BOT_TOKEN=your_discord_bot_token
DISCORD_APPLICATION_ID=your_discord_app_id
DISCORD_PUBLIC_KEY=your_discord_public_key
DISCORD_COMMAND_PREFIX=!

# Coordination System
MAX_CLAIMS=5
HEARTBEAT_INTERVAL=300
CONTAINER_ID=discord_container_1

# Core API Integration
CORE_API_URL=http://router:8000
CONTEXT_API_URL=http://router:8000/api/context
REPUTATION_API_URL=http://router:8000/api/reputation

# Database
DATABASE_URL=postgresql://user:pass@db:5432/waddlebot
```

**Key Features:**
- py-cord library integration
- Slash commands support
- Event handling (messages, reactions, member joins, voice states, server boosts)
- Activity points (message=5, reaction=2, member_join=10, voice_join=8, voice_time=1/min, boost=100)

## Slack Module

**Purpose**: Slack workspace integration

**Build Options:**
```bash
docker build -t waddlebot/slack ./slack_module
```

**Environment Variables:**
```bash
# Module Configuration
MODULE_NAME=slack
MODULE_VERSION=1.0.0
MODULE_PORT=8004

# Slack App Configuration
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token
SLACK_CLIENT_ID=your_slack_client_id
SLACK_CLIENT_SECRET=your_slack_client_secret
SLACK_SIGNING_SECRET=your_slack_signing_secret
SLACK_OAUTH_REDIRECT_URI=https://yourdomain.com/slack/oauth/callback
SLACK_SOCKET_MODE=false

# Coordination System
MAX_CLAIMS=5
HEARTBEAT_INTERVAL=300
CONTAINER_ID=slack_container_1

# Core API Integration
CORE_API_URL=http://router:8000
CONTEXT_API_URL=http://router:8000/api/context
REPUTATION_API_URL=http://router:8000/api/reputation

# Database
DATABASE_URL=postgresql://user:pass@db:5432/waddlebot
```

**Key Features:**
- Slack SDK integration
- Event API handling
- Custom slash commands
- Activity points (message=5, file_share=15, reaction=3, member_join=10, app_mention=8)

## Interaction Modules

## AI Interaction Module

**Purpose**: AI-powered chat responses with multi-provider support

**Build Options:**
```bash
docker build -t waddlebot/ai-interaction ./ai_interaction_module
```

**Environment Variables:**
```bash
# Module Configuration
MODULE_NAME=ai_interaction
MODULE_VERSION=1.0.0
MODULE_PORT=8005

# AI Provider Configuration
AI_PROVIDER=ollama                 # Options: 'ollama', 'openai', 'mcp'
AI_HOST=http://ollama:11434
AI_PORT=11434
AI_API_KEY=your_api_key

# Model Configuration
AI_MODEL=llama3.2
AI_TEMPERATURE=0.7                 # Response creativity (0.0-1.0)
AI_MAX_TOKENS=500                  # Max response length

# OpenAI Configuration (if using OpenAI provider)
OPENAI_API_KEY=sk-your-openai-key
OPENAI_MODEL=gpt-3.5-turbo
OPENAI_BASE_URL=https://api.openai.com/v1

# MCP Configuration (if using MCP provider)
MCP_SERVER_URL=http://mcp-server:8080
MCP_TIMEOUT=30

# System Behavior
SYSTEM_PROMPT="You are a helpful chatbot assistant. Provide friendly, concise, and helpful responses to users in chat."
QUESTION_TRIGGERS=?                # Characters that trigger AI response
RESPONSE_PREFIX="🤖 "             # Prefix for AI responses
RESPOND_TO_EVENTS=true             # Respond to platform events
EVENT_RESPONSE_TYPES=subscription,follow,donation

# Performance Settings
MAX_CONCURRENT_REQUESTS=10
REQUEST_TIMEOUT=30
ENABLE_CHAT_CONTEXT=true           # Track conversation history
CONTEXT_HISTORY_LIMIT=5            # Messages to remember

# Core API Integration
CORE_API_URL=http://router:8000
ROUTER_API_URL=http://router:8000/router

# Database
DATABASE_URL=postgresql://user:pass@db:5432/waddlebot
```

**Key Features:**
- Multi-provider AI support (Ollama, OpenAI, MCP)
- Configurable system prompts and triggers
- Conversation context tracking
- Event-based responses

## Inventory Interaction Module

**Purpose**: Multi-threaded inventory management system

**Build Options:**
```bash
docker build -t waddlebot/inventory ./inventory_interaction_module
```

**Environment Variables:**
```bash
# Module Configuration
MODULE_NAME=inventory_interaction_module
MODULE_VERSION=1.0.0
MODULE_PORT=8024

# Performance Settings
MAX_WORKERS=20                     # Thread pool size
MAX_LABELS_PER_ITEM=5             # Max labels per inventory item
CACHE_TTL=300                     # Cache expiration (seconds)
REQUEST_TIMEOUT=30

# AAA Logging Configuration
LOG_LEVEL=INFO
LOG_DIR=/var/log/waddlebotlog
ENABLE_SYSLOG=false
SYSLOG_HOST=localhost
SYSLOG_PORT=514
SYSLOG_FACILITY=LOCAL0

# Core API Integration
CORE_API_URL=http://router:8000
ROUTER_API_URL=http://router:8000/router

# Database
DATABASE_URL=postgresql://user:pass@db:5432/waddlebot
```

**Key Features:**
- Thread-safe inventory management
- Label-based categorization
- Comprehensive AAA logging
- Real-time inventory tracking

## YouTube Music Interaction Module

**Purpose**: YouTube Music integration with browser source output

**Build Options:**
```bash
docker build -t waddlebot/youtube-music ./youtube_music_interaction_module
```

**Environment Variables:**
```bash
# Module Configuration
MODULE_NAME=youtube_music_interaction
MODULE_VERSION=1.0.0
MODULE_PORT=8025

# YouTube API Configuration
YOUTUBE_API_KEY=your_youtube_api_key
YOUTUBE_API_VERSION=v3
YOUTUBE_MUSIC_CATEGORY_ID=10       # Music category
YOUTUBE_REGION_CODE=US

# Browser Source Integration
BROWSER_SOURCE_API_URL=http://browser-source:8027/browser/source

# Performance Settings
MAX_SEARCH_RESULTS=10              # Search result limit
CACHE_TTL=300                      # Search cache TTL
REQUEST_TIMEOUT=30
MAX_QUEUE_SIZE=50                  # Music queue limit

# Feature Flags
ENABLE_PLAYLISTS=true
ENABLE_QUEUE=true
ENABLE_HISTORY=true
ENABLE_AUTOPLAY=true

# AAA Logging
LOG_LEVEL=INFO
LOG_DIR=/var/log/waddlebotlog
ENABLE_SYSLOG=false

# Core API Integration
CORE_API_URL=http://router:8000
ROUTER_API_URL=http://router:8000/router

# Database
DATABASE_URL=postgresql://user:pass@db:5432/waddlebot
```

**Key Features:**
- YouTube Data API integration
- Search result caching
- Browser source media display
- Queue management

## Spotify Interaction Module

**Purpose**: Spotify integration with OAuth and playback control

**Build Options:**
```bash
docker build -t waddlebot/spotify ./spotify_interaction_module
```

**Environment Variables:**
```bash
# Module Configuration
MODULE_NAME=spotify_interaction
MODULE_VERSION=1.0.0
MODULE_PORT=8026

# Spotify API Configuration
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
SPOTIFY_REDIRECT_URI=http://localhost:8026/spotify/auth/callback
SPOTIFY_SCOPES=user-read-playback-state user-modify-playback-state user-read-currently-playing streaming

# Browser Source Integration
BROWSER_SOURCE_API_URL=http://browser-source:8027/browser/source

# Performance Settings
MAX_SEARCH_RESULTS=10
CACHE_TTL=300
REQUEST_TIMEOUT=30
TOKEN_REFRESH_BUFFER=300           # Token refresh buffer (seconds)

# Feature Flags
ENABLE_PLAYLISTS=true
ENABLE_QUEUE=true
ENABLE_HISTORY=true
ENABLE_DEVICE_CONTROL=true

# Media Display Settings
MEDIA_DISPLAY_DURATION=30          # Browser source display time
SHOW_ALBUM_ART=true
SHOW_PROGRESS_BAR=true

# AAA Logging
LOG_LEVEL=INFO
LOG_DIR=/var/log/waddlebotlog
ENABLE_SYSLOG=false

# Core API Integration
CORE_API_URL=http://router:8000
ROUTER_API_URL=http://router:8000/router

# Database
DATABASE_URL=postgresql://user:pass@db:5432/waddlebot
```

**Key Features:**
- Spotify Web API OAuth integration
- Real-time playback control
- Multi-device support
- Rich media browser source output

## Browser Source Core Module

**Purpose**: Browser source management for OBS integration

**Build Options:**
```bash
docker build -t waddlebot/browser-source ./browser_source_core_module
```

**Environment Variables:**
```bash
# Module Configuration
MODULE_NAME=browser_source_core
MODULE_VERSION=1.0.0
MODULE_PORT=8027

# WebSocket Configuration
WEBSOCKET_HOST=0.0.0.0
WEBSOCKET_PORT=8028
MAX_CONNECTIONS=1000               # Max concurrent WebSocket connections

# Performance Settings
MAX_WORKERS=50                     # Thread pool size
QUEUE_PROCESSING_INTERVAL=1        # Queue processing interval (seconds)
CLEANUP_INTERVAL=300              # Cleanup interval (seconds)
TICKER_QUEUE_SIZE=100             # Max ticker messages in queue

# Browser Source Settings
BASE_URL=http://localhost:8027
TOKEN_LENGTH=32                   # Token length for URLs
ACCESS_LOG_RETENTION_DAYS=30      # Access log retention

# Display Settings
DEFAULT_TICKER_DURATION=10        # Default ticker display time
DEFAULT_MEDIA_DURATION=30         # Default media display time
MAX_TICKER_LENGTH=200             # Max ticker message length

# AAA Logging
LOG_LEVEL=INFO
LOG_DIR=/var/log/waddlebotlog
ENABLE_SYSLOG=false

# Core API Integration
CORE_API_URL=http://router:8000
ROUTER_API_URL=http://router:8000/router

# Database
DATABASE_URL=postgresql://user:pass@db:5432/waddlebot
```

**Key Features:**
- Multi-threaded WebSocket handling
- Three browser source types (ticker, media, general)
- Real-time OBS integration
- Token-based security

## Infrastructure Services

## Kong Admin Broker

**Purpose**: Kong API Gateway super admin user management

**Build Options:**
```bash
docker build -t waddlebot/kong-broker ./kong_admin_broker
```

**Environment Variables:**
```bash
# Module Configuration
MODULE_NAME=kong_admin_broker
MODULE_VERSION=1.0.0
MODULE_PORT=8000

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

# Database
DATABASE_URL=postgresql://user:pass@db:5432/waddlebot
```

**Key Features:**
- Kong consumer lifecycle management
- Automated API key generation
- Comprehensive audit logging
- Backup and recovery system

## Labels Core Module

**Purpose**: High-performance multi-threaded label management

**Build Options:**
```bash
docker build -t waddlebot/labels-core ./labels_core_module
```

**Environment Variables:**
```bash
# Module Configuration
MODULE_NAME=labels_core
MODULE_VERSION=1.0.0
MODULE_PORT=8025

# Redis Configuration
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=your_redis_password

# Performance Settings
MAX_WORKERS=20                     # Thread pool size
CACHE_TTL=300                      # Cache expiration
BULK_OPERATION_SIZE=1000           # Max bulk operations
REQUEST_TIMEOUT=30

# Core API Integration
CORE_API_URL=http://router:8000
ROUTER_API_URL=http://router:8000/router

# Database
DATABASE_URL=postgresql://user:pass@db:5432/waddlebot
```

**Key Features:**
- Multi-threaded label operations
- Redis caching with fallback
- Bulk operation support
- User identity verification

## Docker Compose Deployment

### Development Environment
```bash
# Start core services only
docker-compose up -d db redis kong

# Start with specific modules
docker-compose up -d db redis kong router identity-core twitch-collector

# View logs
docker-compose logs -f router

# Scale collectors
docker-compose up -d --scale twitch-collector=3
```

### Production Deployment
```bash
# Use production compose file
docker-compose -f docker-compose.prod.yml up -d

# Update specific service
docker-compose pull router
docker-compose up -d --no-deps router

# Health checks
docker-compose ps
```

### Kubernetes Deployment

Each module includes Kubernetes manifests in `k8s/` directory:

```bash
# Deploy router
kubectl apply -f router_module/k8s/

# Deploy with custom namespace
kubectl apply -f router_module/k8s/ -n waddlebot

# Scale deployment
kubectl scale deployment router --replicas=3
```

## Monitoring and Health Checks

All modules expose health endpoints:

- `GET /health` - Basic health check
- `GET /metrics` - Performance metrics (if enabled)
- `GET /ready` - Readiness check for Kubernetes

Health check URLs:
- Router: `http://localhost:8000/health`
- Identity Core: `http://localhost:8050/identity/health`
- Twitch Collector: `http://localhost:8002/health`
- AI Interaction: `http://localhost:8005/ai/health`

## Troubleshooting

### Common Issues

1. **Database Connection Issues**
   ```bash
   # Check database connectivity
   docker-compose exec router python -c "import psycopg2; print('DB OK')"
   
   # View database logs
   docker-compose logs db
   ```

2. **Redis Connection Issues**
   ```bash
   # Test Redis connection
   docker-compose exec redis redis-cli ping
   
   # Clear Redis cache
   docker-compose exec redis redis-cli FLUSHALL
   ```

3. **API Credential Issues**
   ```bash
   # Verify environment variables
   docker-compose exec twitch-collector printenv | grep TWITCH
   
   # Test API credentials
   docker-compose exec twitch-collector python -c "from config import Config; print(Config.TWITCH_CLIENT_ID)"
   ```

4. **Module Communication Issues**
   ```bash
   # Check inter-service connectivity
   docker-compose exec twitch-collector curl -f http://router:8000/health
   
   # View network configuration
   docker-compose exec twitch-collector cat /etc/resolv.conf
   ```

### Logging

View logs for specific services:
```bash
# Router logs
docker-compose logs -f router

# All AI module logs
docker-compose logs -f ai-interaction

# Follow logs with timestamps
docker-compose logs -f -t router twitch-collector discord-collector
```

Configure logging levels:
```bash
# Enable debug logging
LOG_LEVEL=DEBUG docker-compose up -d router

# Enable syslog output
ENABLE_SYSLOG=true SYSLOG_HOST=syslog-server docker-compose up -d
```

## Performance Tuning

### Database Optimization
```bash
# Use read replicas
READ_REPLICA_URL=postgresql://user:pass@db-read:5432/waddlebot

# Connection pooling
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10
```

### Redis Optimization
```bash
# Increase cache TTL for stable data
CACHE_TTL=3600

# Use Redis clustering
REDIS_CLUSTER_ENABLED=true
REDIS_CLUSTER_NODES=redis-1:6379,redis-2:6379,redis-3:6379
```

### Application Tuning
```bash
# Increase worker threads
MAX_WORKERS=50

# Adjust request timeouts
REQUEST_TIMEOUT=60

# Enable bulk operations
BULK_OPERATION_SIZE=5000
```

This comprehensive guide covers all major components of the WaddleBot system. Each module can be deployed independently or as part of the full system depending on your requirements. 

