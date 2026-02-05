# Waddles Module Details - Core Components & Trigger Modules

This document provides comprehensive technical details for Waddles core components and trigger modules. For action/interactive modules, see [module-details-action.md](module-details-action.md). For high-level architecture, see [CLAUDE.md](../CLAUDE.md).

## Module Architecture Overview

Waddles follows a modular, microservices architecture with three primary module categories:

- **Core Components**: Central services handling routing, authentication, identity, and browser source management
- **Trigger Modules (Receivers)**: Platform-specific modules that receive webhooks and events from Twitch, Discord, and Slack
- **Action Modules (Interactive)**: Response modules that process commands and return chat messages, media displays, or data

All modules communicate through the Router Module, which handles command routing, rate limiting, and execution coordination. Modules are deployed as individual Docker containers with Flask/Quart frameworks on Python 3.13.

---

## Core Components

### Router Module (`processing/router_module_flask/`)

**Purpose**: High-performance command router and event processor - the central brain of Waddles

**Key Features**:
- **High-Performance Processing**: Multi-threaded command processing with ThreadPoolExecutor
- **Command Routing**: Parses `!` (local container) and `#` (community Lambda/OpenWhisk) prefixed commands
- **Database Optimization**: Uses read replicas for command lookups, primary for writes
- **Caching Layer**: In-memory caching with TTL for commands and entity permissions
- **Rate Limiting**: Sliding window rate limiter with per-user/command/entity tracking
- **Execution Engine**: Routes to local containers, AWS Lambda, OpenWhisk, or webhook endpoints
- **Metrics & Monitoring**: Real-time performance metrics and health monitoring
- **Batch Processing**: Supports up to 100 concurrent event processing

**Technical Details**:
- Multi-threaded execution with configurable worker pools
- Session management via Redis with TTL
- String matching system for content moderation and auto-responses
- Support for sequential and parallel module execution
- Comprehensive execution audit logging

---

### Marketplace Module (`admin/marketplace_module_flask/`)

**Purpose**: Community module marketplace for browsing, installing, and managing modules

**Key Features**:
- **Module Management**: Browse, search, install, and manage community modules
- **Permission System**: Entity-based permissions for module installation/management
- **Version Control**: Multiple module versions with upgrade/downgrade support
- **Review System**: User reviews and ratings for modules
- **Router Integration**: Automatic command registration/removal with router
- **Usage Analytics**: Track module usage and performance statistics
- **Category System**: Hierarchical module categorization

**Technical Details**:
- Paid subscription system with payment blocking for expired subscriptions
- Automatic synchronization with router for command registration
- Module discovery with search and filtering capabilities

---

### Hub Module (`admin/hub_module/`)

**Purpose**: Community management portal with authentication and direct routing (replaces Kong API Gateway)

**Key Features**:
- **Community Management Portal**: Web-based interface for community administrators
- **Direct Routing**: Replaces Kong API Gateway with direct service routing
- **User Authentication**: Flask-Security-Too for user authentication and session management
- **Role-Based Access Control**: User roles for trigger, action, core, admin, and user permissions
- **Rate Limiting**: Per-service and per-role rate limiting with Redis backend
- **Dashboard**: Community statistics, user management, and module configuration
- **Browser Source Management**: Display unique browser source URLs for OBS integration
- **Email Service**: SMTP/sendmail support for notifications and password resets
- **API Key Management**: Generate and manage API keys for programmatic access
- **Audit Trail**: Comprehensive logging of all administrative actions
- **Service Health Monitoring**: Monitor health status of all Waddles services

**Technical Details**:
- Routes all API traffic to backend services with authentication
- Per-service rate limits (Router: 1000/min, AI: 1000/min, Triggers: 200/min)
- Browser source URL management with copy-to-clipboard functionality
- CORS support for web applications

---

### Identity Core Module (`core/identity_core_module_flask/`)

**Purpose**: Cross-platform identity linking and verification system with comprehensive API key management

**Key Features**:
- **Flask-Security-Too Foundation**: Built on Flask-Security-Too authentication system with extended user fields
- **Cross-Platform Linking**: Secure identity verification between Discord, Twitch, and Slack accounts
- **Whisper/DM Verification**: Platform-specific verification via whispers and direct messages
- **User API Key Management**: Self-service API key generation with same permissions as user identity
- **Comprehensive Security**: SHA-256 hashed API keys, time-limited verification codes, rate limiting
- **Multi-threaded Processing**: ThreadPoolExecutor for concurrent verification operations
- **Redis Caching**: High-performance caching for identity lookups and session management
- **Comprehensive AAA Logging**: Full Authentication, Authorization, and Auditing with structured output

**Identity Linking Flow**:
1. User types `!identity link twitch username`
2. Verification code sent via whisper/DM to platform account
3. User confirms with `!verify CODE` in chat
4. Identity linked across platforms

**Key Features List**:
- **API Key System**: Users can create, regenerate, and revoke their own API keys for programmatic access
- **Session Management**: Flask session-based authentication with configurable expiration
- **Platform Integration**: Communicates with Twitch, Discord, and Slack collectors for whisper/DM delivery
- **Database Schema**: Extended Flask-Security user table with Waddles-specific fields (display_name, primary_platform, reputation_score)
- **Verification Security**: 6-character alphanumeric codes (excluding ambiguous characters) with 10-minute expiration
- **Rate Limiting**: Sliding window rate limiting to prevent spam and abuse
- **Health Monitoring**: Comprehensive health checks for all platform APIs and dependencies

---

### Labels Core Module (`core/labels_core_module_flask/`)

**Purpose**: High-performance multi-threaded label management system for communities, users, modules, and entity groups

**Key Features**:
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

**Technical Details**:
- Label limits: 5 per community, 5 per user per community
- Thread-safe operations with concurrent processing
- Integration with identity system for user verification

---

### Workflow Core Module (`core/workflow_core_module/`)

**Purpose**: Visual workflow automation engine with node-based builder, schedule service, and webhook triggers

**Key Features**:
- **Visual Workflow Builder**: Node-based visual interface for non-technical automation
- **22 Node Types**: Triggers (command, event, webhook, schedule), conditions (if, switch, filter), actions (module, webhook, chat, browser source, delay), data manipulation, loops, and flow control
- **Multiple Trigger Types**: Command-based, event-based, scheduled (cron/interval/one-time), and webhook triggers
- **Execution Engine**: Real-time workflow execution with node-level execution tracking and result capture
- **Schedule Service**: APScheduler-based cron, interval, and one-time scheduling with grace period handling
- **Webhook Integration**: HMAC-SHA256 signature verification, IP allowlist, and rate limiting per webhook
- **License Validation**: Premium feature requiring valid license key (HTTP 402 Payment Required on failure)
- **Permission System**: Entity and community-based access control with audit logging
- **Workflow Templates**: Shareable workflow templates with one-click instantiation
- **Execution Monitoring**: Real-time execution traces, node-level results, and retry support

**Technical Details**:
- **Port**: 8070
- **Framework**: Quart (async Flask) on Python 3.13
- **Database**: AsyncDAL with PostgreSQL (8 tables)
- **Services**:
  - **LicenseService**: Validates workflows against license tier (free: 1 workflow, pro: unlimited)
  - **PermissionService**: Entity-based permission checks for read/write/execute
  - **WorkflowValidationService**: Validates workflow structure, node connections, and configuration
  - **WorkflowService**: CRUD operations and workflow orchestration
  - **WorkflowEngine**: Executes workflows with node-by-node execution and error handling
  - **ScheduleService**: Manages scheduled executions with APScheduler backend

**Node Categories**:

1. **Trigger Nodes** (Entry points):
   - `trigger_command`: Execute on chat command (e.g., `!hello`)
   - `trigger_event`: Execute on platform events (follow, subscribe, raid, etc.)
   - `trigger_webhook`: Execute when webhook receives POST request
   - `trigger_schedule`: Execute on cron schedule, interval, or specific time

2. **Condition Nodes** (Control flow):
   - `condition_if`: Traditional if/else branching with AND logic
   - `condition_switch`: Route to one of multiple outputs based on variable value
   - `condition_filter`: Filter array items based on condition

3. **Action Nodes** (Execute operations):
   - `action_module`: Call Waddles action modules (AI, shoutout, alias, etc.)
   - `action_webhook`: Make HTTP requests to external services with retry support
   - `action_chat_message`: Send message to chat platform (Twitch, Discord, Slack)
   - `action_browser_source`: Update OBS browser source with HTML/text content
   - `action_delay`: Pause workflow execution (static or dynamic delay)

4. **Data Nodes** (Manipulate variables):
   - `data_transform`: Transform data using jq, JavaScript, or Python expressions
   - `data_variable_set`: Set workflow variables (local/workflow/global scope)
   - `data_variable_get`: Retrieve variable from context with default values
   - `data_array_push`: Append items to array variable
   - `data_object_merge`: Merge objects and create composite data structures

5. **Loop Nodes** (Iteration):
   - `loop_foreach`: Iterate over array items with configurable concurrency
   - `loop_while`: Continue looping while condition is true

6. **Flow Control**:
   - `flow_parallel`: Execute multiple nodes in parallel
   - `flow_sequence`: Execute nodes sequentially (default)
   - `flow_noop`: No-operation node for testing and debugging

**Database Tables**:
- `workflow_definitions`: Core workflow metadata and configuration
- `workflow_executions`: Execution records with status and timestamps
- `workflow_node_executions`: Node-level execution details with inputs/outputs
- `workflow_schedules`: Scheduled execution configurations
- `workflow_permissions`: Entity and community-based access control
- `workflow_webhooks`: Webhook configurations with tokens and secrets
- `workflow_audit_log`: Comprehensive audit trail of all operations
- `workflow_templates`: Reusable workflow templates

**API Endpoints** (`/api/v1`):
- **Workflow CRUD**: `POST/GET/PUT/DELETE /workflows`, `GET /workflows/:id`
- **Execution**: `POST /workflows/:id/execute`, `GET /workflows/executions/:execId`, `GET /workflows/:id/executions`
- **Publishing**: `POST /workflows/:id/publish`, `POST /workflows/:id/draft`
- **Validation**: `POST /workflows/:id/validate`, `POST /workflows/validate`
- **Templates**: `GET /templates`, `POST /templates/instantiate`, `GET /templates/:id`
- **Schedules**: `POST /schedules`, `PUT /schedules/:id`, `DELETE /schedules/:id`, `GET /schedules/workflow/:id`
- **Webhooks**: `POST /workflows/:id/webhooks`, `GET /workflows/:id/webhooks`, `DELETE /workflows/:id/webhooks/:id`, `POST /workflows/webhooks/:token`

**Schedule Service**:
- **Cron Scheduling**: Full cron expression support (e.g., "0 12 * * *" for daily at noon)
- **Interval Scheduling**: Repeat every N seconds with optional max execution count
- **One-Time Scheduling**: Execute at specific datetime
- **Grace Period**: Automatically triggers missed executions within configurable window (default: 15 minutes)
- **Concurrent Execution**: APScheduler with configurable max instances and coalescing

**Webhook Features**:
- **HMAC-SHA256 Signature Verification**: Secure token + payload signing with secrets
- **IP Allowlist**: Support for CIDR ranges and individual IPs
- **Rate Limiting**: Sliding window rate limiting per webhook (default: 60 req/min)
- **Secure Token Generation**: 32-character hex tokens and secrets
- **Trigger Stats**: Track trigger count and last triggered timestamp

**Integration**:
- **Router Integration**: Routes action module calls through router-service with version control
- **License Server**: Validates license keys via PenguinTech License Server
- **Identity Core**: User context and permission verification
- **Permission Service**: Community and entity-based access control
- **Audit Logging**: AAA logging for all operations with community/user/action context

**Response Format**:
```json
{
  "success": true,
  "data": {},
  "message": "Operation successful",
  "timestamp": "2025-12-09T12:00:00Z"
}
```

**Error Handling**:
- `400 Bad Request`: Invalid input data
- `401 Unauthorized`: Missing/invalid authentication
- `402 Payment Required`: License validation failed
- `403 Forbidden`: Permission denied
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

---

## Trigger Modules (Receivers)

### Twitch Module (`trigger/receiver/twitch_module/`)

**Purpose**: Twitch IRC bot with prefix commands and EventSub webhook receiver

**Key Features**:
- **IRC Bot (TwitchIO)**: Persistent IRC connection for `!prefix` commands in chat
- **EventSub Webhooks**: Handles follow, subscribe, cheer, raid, gift subscription, stream online/offline events
- **Channel Management**: Dynamic channel join/leave with database-driven refresh
- **OAuth Integration**: Complete OAuth flow with token management and refresh
- **Viewer Tracking**: Optional viewer activity tracking for leaderboards
- **Activity Points**: follow=10, sub=50, bits=variable, raid=30, subgift=60, ban=-10

**Command Support**:
| Type | Format | Example |
|------|--------|---------|
| Prefix | `!command` | `!help`, `!so streamer` |

**Technical Details**:
- TwitchIO 2.8+ for IRC bot functionality
- Webhook signature verification (HMAC-SHA256) for EventSub
- Automatic token refresh and management
- Mod/subscriber/VIP badge detection
- Coordination system for horizontal scaling across multiple containers

---

### Discord Module (`trigger/receiver/discord_module/`)

**Purpose**: Discord bot with py-cord integration for slash commands, prefix commands, modals, and buttons

**Key Features**:
- **py-cord Integration**: Uses py-cord 2.4+ library for full Discord bot functionality
- **Slash Commands**: Native Discord slash commands with autocomplete support
- **Prefix Commands**: Traditional `!command` support via message listener
- **Modals**: Interactive form dialogs for user input (e.g., feedback forms)
- **Buttons**: Interactive button components with custom handlers
- **Select Menus**: Dropdown selection components
- **Event Handling**: Messages, reactions, member joins, voice states, server boosts
- **Voice Tracking**: Tracks voice channel participation with time-based points
- **Activity Points**: message=5, reaction=2, member_join=10, voice_join=8, voice_time=1/min, boost=100

**Command Support**:
| Type | Format | Example |
|------|--------|---------|
| Slash | `/command` | `/help`, `/shoutout user` |
| Prefix | `!command` | `!help`, `!so user` |

**Technical Details**:
- Native Discord bot with persistent gateway connections
- Interaction handler for modals, buttons, and select menus
- Redis caching for interaction context storage
- Voice channel time tracking with point accumulation
- Server boost event handling
- Deferred responses for long-running commands

---

### Slack Module (`trigger/receiver/slack_module/`)

**Purpose**: Slack app with Slack Bolt integration for slash commands, prefix commands, modals, and buttons

**Key Features**:
- **Slack Bolt Framework**: Uses slack-bolt 1.18+ for event-driven architecture
- **Slash Commands**: Custom `/waddlebot` command with subcommand routing
- **Prefix Commands**: Traditional `!command` support via message events
- **Modals**: Interactive form dialogs using Block Kit
- **Buttons**: Interactive button components with action handlers
- **Block Kit**: Full Block Kit support for rich message formatting
- **Event API**: Handles messages, reactions, file shares, channel joins, app mentions
- **Socket Mode**: Optional Socket Mode for development without public URLs
- **Activity Points**: message=5, file_share=15, reaction=3, member_join=10, app_mention=8

**Command Support**:
| Type | Format | Example |
|------|--------|---------|
| Slash | `/waddlebot command` | `/waddlebot help`, `/waddlebot shoutout @user` |
| Prefix | `!command` | `!help`, `!so @user` |

**Technical Details**:
- Slack Bolt async handlers for all event types
- Block Kit builder for dynamic UI generation
- Signature verification for webhook security
- Socket Mode support for real-time events (development)
- HTTP mode for production webhook endpoints
- User information caching for performance

---

## Related Documentation

- [module-details-action.md](module-details-action.md) - Action/interactive module details
- [CLAUDE.md](../CLAUDE.md) - Project overview and architecture
- [API Documentation](api-reference.md) - Complete API endpoint reference
- [Environment Variables](environment-variables.md) - Configuration reference
- [Deployment Guide](deployment.md) - Docker and Kubernetes deployment
