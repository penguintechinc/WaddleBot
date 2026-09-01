# Waddles API Reference

## Overview

**Scope note:** this reference covers the pre-v3.0.x per-module API surface (router, marketplace,
identity-core, etc.), which still runs today as legacy Deployments alongside the v3 8-container
pipeline — see [`ARCHITECTURE.md`](../ARCHITECTURE.md#build-status-caveats). For the v3
control-plane API (hub-api: tenancy, marketplace, billing, AI routing, MCP), see
[`hub_api/README.md`](../../hub_api/README.md) and its OpenAPI spec under `hub_api/openapi/`.

All legacy Waddles APIs are routed through the **Hub Module**, which provides centralized routing,
authentication, and rate limiting. There is no Kong or other third-party API gateway in this
repo — routing is direct service-to-service through the Hub Module, and in Kubernetes, external
traffic terminates at Ingress/HTTPRoute before reaching it.

The Hub Module acts as the single entry point for all API requests, handling:
- API key authentication via `X-API-Key` header
- Role-based access control (RBAC) using Flask-Security-Too
- Rate limiting per service and user role
- Request routing to backend microservices
- CORS support for web applications

## Hub Module Services

The following backend services are accessible through the Hub Module:

| Service | Description | Internal URL | Port |
|---------|-------------|--------------|------|
| **router-service** | Core routing and command processing | `http://router-service:8000` | 8000 |
| **ai-interaction** | AI services with multi-provider support | `http://ai-interaction:8005` | 8005 |
| **identity-core** | Cross-platform identity linking and verification | `http://identity-core:8050` | 8050 |
| **twitch-collector** | Twitch platform integration | `http://twitch-collector:8002` | 8002 |
| **discord-collector** | Discord platform integration | `http://discord-collector:8003` | 8003 |
| **slack-collector** | Slack platform integration | `http://slack-collector:8004` | 8004 |
| **youtube-music** | YouTube Music integration | `http://youtube-music:8025` | 8025 |
| **spotify-interaction** | Spotify integration | `http://spotify-interaction:8026` | 8026 |
| **browser-source** | Browser source management for OBS | `http://browser-source:8027` | 8027 |
| **reputation** | Reputation and activity tracking | `http://reputation:8028` | 8028 |
| **community** | Community management service | `http://community:8029` | 8029 |
| **workflow-core** | Visual workflow automation engine (premium) | `http://workflow-core:8070` | 8070 |

## Hub Routes

The Hub Module routes requests to backend services based on URL path:

| Route Pattern | Target Service | Authentication Required |
|---------------|----------------|------------------------|
| `/router/*` | Router API | Yes |
| `/ai/*` | AI Interaction API | Yes |
| `/identity/*` | Identity Core API | Yes |
| `/auth/*` | User Authentication API | Yes |
| `/webhooks/twitch/*` | Twitch webhooks | Yes |
| `/webhooks/discord/*` | Discord webhooks | Yes |
| `/webhooks/slack/*` | Slack webhooks | Yes |
| `/youtube/*` | YouTube Music API | Yes |
| `/spotify/*` | Spotify API | Yes |
| `/browser/*` | Browser Source API | Yes |
| `/reputation/*` | Reputation API | Yes |
| `/community/*` | Community API | Yes |
| `/workflows/*` | Workflow Core API | Yes |
| `/health` | Health checks | No |

## Authentication & Authorization

### API Key Authentication

All API requests (except health checks) require authentication via the `X-API-Key` header:

```http
X-API-Key: your_api_key_here
```

### Role-Based Access Control (RBAC)

Waddles uses Flask-Security-Too for RBAC with the following user roles:

| Role | Description | Access Level |
|------|-------------|--------------|
| `trigger` | Trigger modules (receivers, pollers, cron) | Read/write to router and coordination APIs |
| `action` | Action modules (interactive, pushing, security) | Read router data, write responses |
| `core` | Core platform services | Full access to respective service APIs |
| `admin` | Community administrators | Full administrative access |
| `user` | Regular users | Limited read access and user-specific operations |

### CORS Support

The Hub Module provides CORS support for web applications accessing the API from browsers.

## Rate Limiting

Rate limits are enforced per service and user role to prevent abuse:

| Service/Module Type | Requests per Minute | Requests per Hour |
|---------------------|---------------------|-------------------|
| Router | 1000 | 10000 |
| AI Interaction | 1000 | 10000 |
| Trigger modules | 200 | 2000 |
| Action modules | 500 | 5000 |
| Core modules | 500 | 5000 |

Rate limit headers are included in responses:
- `X-RateLimit-Limit` - Maximum requests allowed in window
- `X-RateLimit-Remaining` - Requests remaining in current window
- `X-RateLimit-Reset` - Unix timestamp when rate limit resets

## Router API Endpoints

The Router is the core component responsible for event processing, command routing, and execution management.

### Event Processing

#### `POST /router/events`
Submit a single event for processing from collectors.

**Request Body:**
```json
{
  "entity_id": "platform:server:channel",
  "message_type": "chatMessage",
  "user_id": "user123",
  "user_name": "username",
  "message_content": "!command args",
  "metadata": {}
}
```

**Response:**
```json
{
  "session_id": "session_uuid",
  "execution_id": "exec_uuid",
  "status": "success"
}
```

#### `POST /router/events/batch`
Submit up to 100 events for concurrent batch processing.

**Request Body:**
```json
{
  "events": [
    {
      "entity_id": "platform:server:channel",
      "message_type": "chatMessage",
      "user_id": "user123",
      "message_content": "!command args"
    }
  ]
}
```

### Command Management

#### `GET /router/commands`
List available commands with optional filtering.

**Query Parameters:**
- `entity_id` - Filter by entity
- `prefix` - Filter by command prefix (! or #)
- `module_type` - Filter by module type
- `is_active` - Filter active/inactive commands

**Response:**
```json
{
  "commands": [
    {
      "id": 1,
      "command": "help",
      "prefix": "!",
      "description": "Show help information",
      "location": "internal",
      "type": "container",
      "is_active": true
    }
  ]
}
```

#### `GET /router/entities`
List registered entities (platform:server:channel combinations).

### String Matching Rules

#### `GET /router/string-rules`
List string matching rules with optional entity filtering.

**Query Parameters:**
- `entity_id` - Filter rules by entity

#### `POST /router/string-rules`
Create a new string matching rule for content moderation or auto-responses.

**Request Body:**
```json
{
  "string": "pattern",
  "match_type": "exact|contains|word|regex",
  "case_sensitive": false,
  "enabled_entity_ids": ["entity1", "entity2"],
  "action": "warn|block|command|webhook",
  "command_to_execute": "!shoutout {user}",
  "priority": 10
}
```

#### `PUT /router/string-rules/<id>`
Update an existing string matching rule.

#### `DELETE /router/string-rules/<id>`
Delete (deactivate) a string matching rule.

### Module Responses

#### `POST /router/responses`
Submit a response from an interaction module or webhook. Requires valid session_id.

**Request Body:**
```json
{
  "session_id": "session_uuid",
  "execution_id": "exec_uuid",
  "module_name": "ai_interaction",
  "success": true,
  "response_action": "chat|media|ticker|general|form",
  "response_data": {},
  "processing_time_ms": 150
}
```

#### `GET /router/responses/<execution_id>`
Get all responses for a specific execution.

#### `GET /router/responses/recent`
Get recent module responses with filtering options.

**Query Parameters:**
- `limit` - Maximum number of responses (default: 50)
- `module_name` - Filter by module
- `entity_id` - Filter by entity
- `success` - Filter by success status

### Monitoring

#### `GET /router/metrics`
Get performance metrics and statistics including string matching stats.

**Response:**
```json
{
  "total_events": 1000000,
  "total_executions": 500000,
  "avg_execution_time_ms": 45,
  "cache_hit_rate": 0.85,
  "string_matches": 10000,
  "rate_limit_hits": 50
}
```

#### `GET /router/health`
Health check endpoint with database connectivity verification.

**Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected",
  "uptime_seconds": 86400
}
```

## Coordination API Endpoints

The Coordination API manages horizontal scaling by dynamically assigning servers/channels to collector containers.

### Entity Management

#### `POST /router/coordination/claim`
Claim available entities for a container to monitor.

**Request Body:**
```json
{
  "container_id": "twitch_container_1",
  "platform": "twitch",
  "max_claims": 5,
  "prioritize_live": true
}
```

**Response:**
```json
{
  "claimed_entities": [
    {
      "entity_id": "twitch:channel1",
      "is_live": true,
      "viewer_count": 1500
    }
  ]
}
```

#### `POST /router/coordination/release`
Release claimed entities back to the pool.

**Request Body:**
```json
{
  "container_id": "twitch_container_1",
  "entity_ids": ["twitch:channel1", "twitch:channel2"]
}
```

#### `POST /router/coordination/release-offline`
Release offline entities and claim new ones in a single atomic operation.

### Container Health

#### `POST /router/coordination/checkin`
Container checkin to maintain claims. Must be called every 5 minutes.

**Request Body:**
```json
{
  "container_id": "twitch_container_1",
  "claimed_entities": ["twitch:channel1", "twitch:channel2"]
}
```

#### `POST /router/coordination/heartbeat`
Send heartbeat and extend claim expiration.

**Request Body:**
```json
{
  "container_id": "twitch_container_1"
}
```

### Entity Status Updates

#### `POST /router/coordination/status`
Update entity status (live state, viewer count, etc.).

**Request Body:**
```json
{
  "entity_id": "twitch:channel1",
  "is_live": true,
  "viewer_count": 1500,
  "live_since": "2025-12-02T10:00:00Z"
}
```

#### `POST /router/coordination/error`
Report error for an entity.

**Request Body:**
```json
{
  "entity_id": "twitch:channel1",
  "error_message": "Connection timeout",
  "error_count": 3
}
```

### Statistics

#### `GET /router/coordination/stats`
Get coordination system statistics.

**Response:**
```json
{
  "total_entities": 1000,
  "claimed_entities": 45,
  "live_entities": 12,
  "active_containers": 9,
  "avg_claims_per_container": 5
}
```

#### `GET /router/coordination/entities`
List entities with filtering options.

**Query Parameters:**
- `platform` - Filter by platform
- `is_live` - Filter live entities
- `claimed` - Filter claimed/unclaimed
- `container_id` - Filter by claiming container

#### `POST /router/coordination/populate`
Populate coordination table from servers table.

## Marketplace API Endpoints

The Marketplace API manages community modules, installation, and configuration.

### Module Discovery

#### `GET /marketplace`
Browse featured and popular modules.

**Response:**
```json
{
  "featured": [],
  "popular": [],
  "recent": []
}
```

#### `GET /marketplace/browse`
Search and filter modules with advanced criteria.

**Query Parameters:**
- `query` - Search term
- `category` - Module category
- `sort` - Sort order (popular, recent, rating)
- `limit` - Results per page

#### `GET /marketplace/module/<id>`
Get detailed module information including versions and reviews.

**Response:**
```json
{
  "id": 123,
  "name": "weather",
  "description": "Weather information commands",
  "versions": [],
  "reviews": [],
  "rating": 4.5,
  "installs": 1000
}
```

### Module Installation

#### `POST /marketplace/install`
Install a module for an entity.

**Request Body:**
```json
{
  "module_id": 123,
  "entity_id": "twitch:channel1",
  "version": "1.0.0"
}
```

#### `POST /marketplace/uninstall`
Remove a module from an entity.

**Request Body:**
```json
{
  "module_id": 123,
  "entity_id": "twitch:channel1"
}
```

### Entity Module Management

#### `GET /marketplace/entity/<id>/modules`
List all installed modules for an entity.

**Response:**
```json
{
  "modules": [
    {
      "module_id": 123,
      "name": "weather",
      "version": "1.0.0",
      "enabled": true,
      "installed_at": "2025-12-01T10:00:00Z"
    }
  ]
}
```

#### `POST /marketplace/entity/<id>/toggle`
Enable or disable a module for an entity.

**Request Body:**
```json
{
  "module_id": 123,
  "enabled": true
}
```

## AI Interaction API Endpoints

The AI Interaction API provides multi-provider AI capabilities (Ollama, OpenAI, MCP).

### Chat & Generation

#### `POST /api/ai/v1/chat/completions`
OpenAI-compatible chat completions endpoint.

**Request Body:**
```json
{
  "model": "llama3.2",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What is the weather?"}
  ],
  "temperature": 0.7,
  "max_tokens": 500
}
```

#### `POST /api/ai/v1/generate`
Simple text generation endpoint.

**Request Body:**
```json
{
  "prompt": "Tell me a joke",
  "temperature": 0.7,
  "max_tokens": 200
}
```

### Model & Provider Management

#### `GET /api/ai/v1/models`
List available AI models from configured providers.

**Response:**
```json
{
  "models": [
    {
      "id": "llama3.2",
      "provider": "ollama",
      "size": "3B parameters"
    }
  ]
}
```

#### `GET /api/ai/v1/providers`
List available AI providers (ollama, openai, mcp).

**Response:**
```json
{
  "providers": [
    {
      "name": "ollama",
      "status": "available",
      "models": ["llama3.2", "mistral"]
    }
  ]
}
```

### Configuration

#### `GET /api/ai/v1/config`
Get current AI configuration.

**Response:**
```json
{
  "provider": "ollama",
  "model": "llama3.2",
  "temperature": 0.7,
  "max_tokens": 500,
  "system_prompt": "You are a helpful assistant."
}
```

#### `PUT /api/ai/v1/config`
Update AI configuration (admin only).

**Request Body:**
```json
{
  "provider": "openai",
  "model": "gpt-3.5-turbo",
  "temperature": 0.8
}
```

### Health Check

#### `GET /api/ai/v1/health`
AI service health check (no authentication required).

**Response:**
```json
{
  "status": "healthy",
  "provider": "ollama",
  "provider_status": "connected"
}
```

## Browser Source API Endpoints

The Browser Source API manages OBS browser sources for communities.

### Display Management

#### `POST /browser/source/display`
Receive display data from router and distribute to browser sources.

**Request Body:**
```json
{
  "community_id": "community123",
  "source_type": "media|ticker|general",
  "content": {},
  "duration": 30,
  "session_id": "session_uuid"
}
```

### Browser Source Display

#### `GET /browser/source/{token}/{source_type}`
Browser source display endpoint for OBS. No authentication required (token-based).

**Parameters:**
- `token` - Unique community browser source token
- `source_type` - Type of source (ticker, media, general)

**Response:** HTML page with WebSocket connection for real-time updates.

#### `WebSocket /ws/{token}/{source_type}`
WebSocket endpoint for real-time browser source updates.

### Token Management

#### `GET /browser/source/admin/tokens`
Get community browser source tokens (admin only).

**Response:**
```json
{
  "tokens": [
    {
      "source_type": "ticker",
      "token": "abc123",
      "url": "https://hub.waddlebot.com/browser/source/abc123/ticker"
    }
  ]
}
```

#### `POST /browser/source/admin/tokens`
Generate new browser source tokens for a community (admin only).

**Request Body:**
```json
{
  "community_id": "community123",
  "source_types": ["ticker", "media", "general"]
}
```

#### `POST /browser/source/admin/tokens/{token}/regenerate`
Regenerate a browser source token (admin only).

#### `DELETE /browser/source/admin/tokens/{token}`
Deactivate a browser source token (admin only).

### Community URLs

#### `GET /browser/source/api/communities/{community_id}/urls`
Get browser source URLs for a specific community.

**Response:**
```json
{
  "ticker_url": "https://hub.waddlebot.com/browser/source/abc123/ticker",
  "media_url": "https://hub.waddlebot.com/browser/source/def456/media",
  "general_url": "https://hub.waddlebot.com/browser/source/ghi789/general"
}
```

### Monitoring

#### `GET /browser/source/stats`
Get browser source statistics and connection info.

**Response:**
```json
{
  "active_connections": 50,
  "total_communities": 100,
  "messages_sent": 10000
}
```

#### `GET /browser/source/health`
Browser source health check (no authentication required).

## Identity Core API Endpoints

The Identity Core API manages cross-platform identity linking and API key management.

### Identity Linking

#### `POST /identity/link`
Initiate cross-platform identity linking with verification.

**Request Body:**
```json
{
  "platform": "twitch|discord|slack",
  "platform_id": "platform_user_id",
  "platform_username": "username"
}
```

**Response:**
```json
{
  "verification_id": "verify_uuid",
  "verification_code": "ABC123",
  "expires_at": "2025-12-02T10:10:00Z"
}
```

#### `POST /identity/verify`
Verify identity with whisper/DM code.

**Request Body:**
```json
{
  "verification_code": "ABC123",
  "platform": "twitch"
}
```

#### `DELETE /identity/unlink`
Unlink a platform identity from user account.

**Request Body:**
```json
{
  "platform": "twitch",
  "platform_id": "platform_user_id"
}
```

### Identity Lookup

#### `GET /identity/user/<user_id>`
Get all linked platform identities for a user.

**Response:**
```json
{
  "user_id": "user123",
  "identities": [
    {
      "platform": "twitch",
      "platform_id": "twitch123",
      "username": "streamer",
      "verified": true,
      "linked_at": "2025-12-01T10:00:00Z"
    }
  ]
}
```

#### `GET /identity/platform/<platform>/<platform_id>`
Get Waddles user for a platform-specific user.

**Response:**
```json
{
  "user_id": "user123",
  "display_name": "UserName",
  "primary_platform": "twitch"
}
```

### Verification Management

#### `GET /identity/pending`
Get pending verification requests for a user.

#### `POST /identity/resend`
Resend verification code to platform via whisper/DM.

**Request Body:**
```json
{
  "verification_id": "verify_uuid"
}
```

### API Key Management

#### `POST /identity/api-keys`
Create user API key for programmatic access.

**Request Body:**
```json
{
  "name": "My API Key",
  "expires_in_days": 365
}
```

**Response:**
```json
{
  "api_key": "waddlebot_xxxxxxxxxx",
  "key_id": "key_uuid",
  "expires_at": "2026-12-02T10:00:00Z"
}
```

#### `GET /identity/api-keys`
List user's active API keys.

#### `DELETE /identity/api-keys/<key_id>`
Revoke user API key.

#### `POST /identity/api-keys/<key_id>/regenerate`
Regenerate user API key (invalidates old key).

### User Authentication

#### `POST /auth/register`
Register new Waddles user account.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "secure_password",
  "username": "username"
}
```

#### `POST /auth/login`
Login to Waddles user session.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "password"
}
```

#### `POST /auth/logout`
Logout from Waddles user session.

#### `GET /auth/profile`
Get authenticated user profile information.

#### `PUT /auth/profile`
Update authenticated user profile.

### Monitoring

#### `GET /identity/stats`
Get identity module statistics and metrics.

**Response:**
```json
{
  "total_users": 10000,
  "total_identities": 25000,
  "pending_verifications": 50,
  "active_api_keys": 500
}
```

#### `GET /identity/health`
Identity module health check (no authentication required).

## Legacy Core API Endpoints

These endpoints are maintained for backward compatibility with older modules.

#### `POST /api/modules/register`
Register a module with the core system.

**Request Body:**
```json
{
  "module_name": "twitch",
  "module_version": "1.0.0",
  "platform": "twitch",
  "endpoint_url": "http://twitch-collector:8002",
  "health_check_url": "http://twitch-collector:8002/health"
}
```

#### `POST /api/modules/heartbeat`
Send module heartbeat for health monitoring.

**Request Body:**
```json
{
  "module_name": "twitch",
  "status": "healthy"
}
```

#### `GET /api/servers`
Get monitored servers with filtering.

**Query Parameters:**
- `platform` - Filter by platform (twitch, discord, slack)
- `active` - Filter active servers (true/false)

#### `POST /api/context`
User identity lookup for legacy reputation tracking.

**Request Body:**
```json
{
  "platform": "twitch",
  "platform_user_id": "user123",
  "username": "streamer"
}
```

#### `POST /api/reputation`
Submit activity points for legacy reputation tracking.

**Request Body:**
```json
{
  "user_id": "user123",
  "activity_type": "follow",
  "points": 10,
  "community_id": "community123"
}
```

#### `POST /api/events`
Forward events to router for legacy systems.

#### `POST /api/gateway/activate`
Activate gateway for legacy authentication.

## Workflow API Endpoints

The Workflow API provides comprehensive REST endpoints for managing visual workflow automation. Workflows are premium features requiring valid license keys.

**Base URL**: `/api/v1/workflows` (accessible through Hub Module routing to port 8070)

**Authentication**: All endpoints require `X-API-Key` header or valid JWT token

**License Validation**: Returns HTTP 402 Payment Required if license validation fails

### License Requirements

Workflows are subject to licensing restrictions based on community tier:

| Tier | Workflows per Community | Features | License Key |
|------|------------------------|----------|------------|
| **FREE** | 1 | Basic workflow creation, all operations | Not required |
| **PREMIUM** | Unlimited | All features, advanced integrations | Required (PENG-XXXX-XXXX-XXXX-XXXX-XXXX format) |
| **PRO** | Unlimited | Enterprise features, custom integrations | Required |
| **ENTERPRISE** | Unlimited | Full customization, dedicated support | Required |

#### Workflow Limit Restrictions

- **FREE tier**: Can create up to 1 workflow per community
- **PREMIUM/PRO/ENTERPRISE tiers**: Can create unlimited workflows per community
- When workflow limit is reached, API returns HTTP 402 with message: "Workflow limit reached. Free tier allows 1 workflow per community."

#### License Key Validation

Free tier communities do not require a license key for basic operations. Premium and higher tiers require a valid license key in the format: `PENG-XXXX-XXXX-XXXX-XXXX-XXXX`

### Get Community License Info

#### `GET /api/v1/admin/{communityId}/license-info`

Returns license tier and workflow limits for the community.

**Parameters:**
- `communityId` (required, path): Community ID

**Response (200 OK):**
```json
{
  "success": true,
  "tier": "free|premium|pro|enterprise",
  "maxWorkflows": 1,
  "currentWorkflows": 5,
  "canCreateMore": false,
  "expired": false,
  "expiresAt": "2026-12-31T23:59:59Z"
}
```

**Status Codes:**
- `200 OK`: License information retrieved successfully
- `401 Unauthorized`: Missing or invalid authentication
- `403 Forbidden`: Insufficient permissions (requires admin role)
- `404 Not Found`: Community not found

### HTTP 402 Payment Required

The following scenarios return HTTP 402 Payment Required:

1. **Workflow Limit Exceeded** (FREE tier)
   ```json
   {
     "error": {
       "code": "WORKFLOW_LIMIT_EXCEEDED",
       "message": "Workflow limit reached. Free tier allows 1 workflow per community.",
       "tier": "free",
       "maxWorkflows": 1,
       "currentWorkflows": 1
     }
   }
   ```

2. **Invalid License Key** (PREMIUM+ tier)
   ```json
   {
     "error": {
       "code": "INVALID_LICENSE",
       "message": "License key is invalid or expired.",
       "license_key": "provided_key_format"
     }
   }
   ```

3. **Expired License** (PREMIUM+ tier)
   ```json
   {
     "error": {
       "code": "LICENSE_EXPIRED",
       "message": "License has expired. Please renew to continue using workflows.",
       "expiresAt": "2025-12-01T00:00:00Z"
     }
   }
   ```

**Request Body:**
```json
{
  "name": "My Workflow",
  "description": "Workflow description",
  "community_id": 1,
  "entity_id": 100,
  "trigger_type": "command",
  "trigger_config": {
    "command_pattern": "!hello",
    "platforms": ["twitch", "discord"],
    "cooldown_seconds": 5
  },
  "nodes": {
    "node1": {
      "node_id": "node1",
      "type": "trigger_command",
      "label": "Command Trigger",
      "config": {}
    },
    "node2": {
      "node_id": "node2",
      "type": "action_chat_message",
      "label": "Send Message",
      "config": {
        "message_template": "Hello {user_name}!",
        "destination": "chat"
      }
    }
  },
  "connections": [
    {
      "connection_id": "conn1",
      "from_node_id": "node1",
      "from_port_name": "output",
      "to_node_id": "node2",
      "to_port_name": "input"
    }
  ],
  "global_variables": {},
  "license_key": "PENG-XXXX-XXXX-XXXX-XXXX-ABCD"
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "workflow_id": "550e8400-e29b-41d4-a716-446655440001",
    "name": "My Workflow",
    "status": "draft",
    "community_id": 1,
    "created_at": "2025-12-09T12:00:00Z"
  },
  "message": "Workflow created successfully"
}
```

**Status Codes:**
- `201 Created`: Workflow created successfully
- `400 Bad Request`: Invalid input data
- `401 Unauthorized`: Missing or invalid authentication
- `402 Payment Required`: License validation failed or workflow limit reached
- `500 Internal Server Error`: Server error

#### `GET /api/v1/workflows`
List workflows accessible to the user with pagination and filtering.

**Query Parameters:**
- `entity_id` (required): Entity ID
- `community_id` (optional): Community ID
- `status` (optional): Filter by status (`draft`, `published`, `archived`)
- `search` (optional): Search in name/description
- `page` (optional): Page number (default: 1)
- `per_page` (optional): Items per page (default: 20, max: 100)

**Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "workflow_id": "550e8400-e29b-41d4-a716-446655440001",
      "name": "My Workflow",
      "description": "Workflow description",
      "status": "draft",
      "trigger_type": "command",
      "created_at": "2025-12-09T12:00:00Z",
      "updated_at": "2025-12-09T12:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total_pages": 5,
    "total_items": 100
  }
}
```

#### `GET /api/v1/workflows/:id`
Get a specific workflow definition.

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "workflow_id": "550e8400-e29b-41d4-a716-446655440001",
    "name": "My Workflow",
    "nodes": {},
    "connections": [],
    "status": "draft",
    "trigger_type": "command",
    "trigger_config": {},
    "global_variables": {}
  }
}
```

#### `PUT /api/v1/workflows/:id`
Update an existing workflow.

**Request Body:**
```json
{
  "name": "Updated Workflow",
  "description": "New description",
  "nodes": {},
  "connections": [],
  "global_variables": {}
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "workflow_id": "550e8400-e29b-41d4-a716-446655440001",
    "updated_at": "2025-12-09T12:01:00Z"
  }
}
```

#### `DELETE /api/v1/workflows/:id`
Archive (soft delete) a workflow.

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Workflow archived successfully"
}
```

### Workflow Publishing

#### `POST /api/v1/workflows/:id/publish`
Publish a workflow to make it active.

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "workflow_id": "550e8400-e29b-41d4-a716-446655440001",
    "status": "published",
    "published_at": "2025-12-09T12:02:00Z"
  }
}
```

#### `POST /api/v1/workflows/:id/draft`
Return a published workflow to draft status.

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "workflow_id": "550e8400-e29b-41d4-a716-446655440001",
    "status": "draft"
  }
}
```

### Workflow Execution

#### `POST /api/v1/workflows/:id/execute`
Execute a workflow immediately.

**Request Body:**
```json
{
  "trigger_type": "manual",
  "trigger_data": {
    "user_id": 123,
    "user_name": "streamer",
    "custom_data": {}
  }
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "execution_id": "550e8400-e29b-41d4-a716-446655440000",
    "workflow_id": "550e8400-e29b-41d4-a716-446655440001",
    "status": "running"
  }
}
```

#### `GET /api/v1/workflows/executions/:execId`
Get detailed execution information including node-by-node results.

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "execution_id": "550e8400-e29b-41d4-a716-446655440000",
    "workflow_id": "550e8400-e29b-41d4-a716-446655440001",
    "status": "success",
    "started_at": "2025-12-09T12:00:00Z",
    "completed_at": "2025-12-09T12:00:05Z",
    "duration_ms": 5000,
    "node_executions": [
      {
        "node_execution_id": "node-exec-1",
        "node_id": "node1",
        "node_type": "trigger_command",
        "status": "success",
        "output_variables": {}
      }
    ],
    "output_variables": {}
  }
}
```

#### `POST /api/v1/workflows/executions/:execId/cancel`
Cancel a running workflow execution.

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Execution cancelled successfully"
}
```

#### `GET /api/v1/workflows/:id/executions`
List paginated executions for a specific workflow.

**Query Parameters:**
- `status` (optional): Filter by status (`pending`, `running`, `success`, `failed`, `cancelled`)
- `page` (optional): Page number (default: 1)
- `per_page` (optional): Items per page (default: 20, max: 100)

**Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "execution_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "success",
      "duration_ms": 5000,
      "created_at": "2025-12-09T12:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total_items": 150
  }
}
```

### Workflow Validation

#### `POST /api/v1/workflows/:id/validate`
Validate workflow structure and configuration.

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "is_valid": true,
    "errors": [],
    "warnings": []
  }
}
```

#### `POST /api/v1/workflows/validate`
Validate a workflow without saving it.

**Request Body:**
```json
{
  "nodes": {},
  "connections": [],
  "trigger_config": {}
}
```

### Scheduled Execution

#### `POST /api/v1/schedules`
Create a schedule for automated workflow execution.

**Request Body:**
```json
{
  "workflow_id": "550e8400-e29b-41d4-a716-446655440001",
  "schedule_type": "cron",
  "cron_expression": "0 12 * * *",
  "timezone": "UTC",
  "context_data": {}
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "schedule_id": "550e8400-e29b-41d4-a716-446655440002",
    "next_execution_at": "2025-12-10T12:00:00Z"
  }
}
```

**Schedule Types:**
- `cron`: Cron expression (e.g., "0 12 * * *" for daily at noon)
- `interval`: Repeat every N seconds
- `one_time`: Execute at specific datetime

#### `PUT /api/v1/schedules/:id`
Update an existing schedule.

**Request Body:**
```json
{
  "cron_expression": "0 9 * * *",
  "timezone": "America/New_York"
}
```

#### `DELETE /api/v1/schedules/:id`
Remove a schedule.

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Schedule deleted successfully"
}
```

#### `GET /api/v1/schedules/workflow/:id`
List all schedules for a workflow.

**Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "schedule_id": "550e8400-e29b-41d4-a716-446655440002",
      "schedule_type": "cron",
      "next_execution_at": "2025-12-10T12:00:00Z",
      "is_active": true
    }
  ]
}
```

### Webhook Triggers

#### `POST /api/v1/workflows/:id/webhooks`
Create a webhook for triggering a workflow via HTTP.

**Request Body:**
```json
{
  "name": "My Webhook",
  "description": "Optional description",
  "require_signature": true,
  "ip_allowlist": ["192.168.1.0/24"],
  "rate_limit_max": 60,
  "rate_limit_window": 60
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "webhook_id": "550e8400-e29b-41d4-a716-446655440003",
    "token": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
    "secret": "b1c2d3e4f5g6h7i8j9k0l1m2n3o4p5q6",
    "url": "https://api.example.com/api/v1/workflows/webhooks/a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
  }
}
```

**Note**: The secret is only returned on creation and cannot be retrieved later.

#### `GET /api/v1/workflows/:id/webhooks`
List webhooks for a workflow.

**Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "webhook_id": "550e8400-e29b-41d4-a716-446655440003",
      "token": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
      "name": "My Webhook",
      "enabled": true,
      "trigger_count": 42
    }
  ]
}
```

#### `DELETE /api/v1/workflows/:id/webhooks/:id`
Delete a webhook.

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Webhook deleted successfully"
}
```

#### `POST /api/v1/workflows/webhooks/:token`
Trigger a workflow via webhook (no authentication required, signature-based).

**Request Body** (any JSON):
```json
{
  "event": "user.created",
  "user_id": 12345,
  "custom_data": {}
}
```

**Headers**:
- `X-Webhook-Signature: sha256=<hmac-sha256-hex>` (if require_signature=true)

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "execution_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

**Error Responses:**
- `404 Webhook Not Found`: Token doesn't exist
- `403 Webhook Disabled`: Webhook is disabled
- `403 IP Not Allowed`: IP not in allowlist
- `403 Signature Invalid`: Signature verification failed
- `429 Rate Limit Exceeded`: Too many requests

### Workflow Templates

#### `GET /api/v1/templates`
List available workflow templates.

**Query Parameters:**
- `category` (optional): Filter by category
- `search` (optional): Search by name/description
- `page` (optional): Page number (default: 1)
- `per_page` (optional): Items per page (default: 20)

**Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "template_id": "550e8400-e29b-41d4-a716-446655440004",
      "name": "Welcome Message",
      "category": "notifications",
      "description": "Send welcome message to new followers",
      "download_count": 1234
    }
  ]
}
```

#### `GET /api/v1/templates/:id`
Get a specific template.

#### `POST /api/v1/templates/instantiate`
Create a workflow from a template.

**Request Body:**
```json
{
  "template_id": "550e8400-e29b-41d4-a716-446655440004",
  "name": "My Welcome Message",
  "community_id": 1,
  "entity_id": 100
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "workflow_id": "550e8400-e29b-41d4-a716-446655440001",
    "name": "My Welcome Message",
    "status": "draft"
  }
}
```

## Error Responses

All API endpoints return consistent error responses:

```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Detailed error message",
    "details": {}
  }
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_REQUEST` | 400 | Malformed request or invalid parameters |
| `UNAUTHORIZED` | 401 | Missing or invalid API key |
| `FORBIDDEN` | 403 | Insufficient permissions for operation |
| `NOT_FOUND` | 404 | Resource not found |
| `RATE_LIMIT_EXCEEDED` | 429 | Rate limit exceeded |
| `INTERNAL_ERROR` | 500 | Internal server error |
| `SERVICE_UNAVAILABLE` | 503 | Backend service unavailable |

## Pagination

List endpoints support pagination with the following query parameters:

- `page` - Page number (default: 1)
- `per_page` - Items per page (default: 50, max: 100)

Paginated responses include metadata:

```json
{
  "data": [],
  "pagination": {
    "page": 1,
    "per_page": 50,
    "total_pages": 10,
    "total_items": 500
  }
}
```

## Webhooks

Some endpoints support webhook callbacks for asynchronous processing:

```json
{
  "webhook_url": "https://your-server.com/webhook",
  "webhook_secret": "signing_secret"
}
```

Webhook payloads are signed with HMAC-SHA256 using the webhook secret in the `X-Webhook-Signature` header.

## API Versioning

The Waddles API follows semantic versioning. The version is included in the URL path for breaking changes:

- `/api/v1/*` - Version 1 (current)
- `/api/v2/*` - Version 2 (future)

Non-breaking changes are added to existing versions without URL changes.
