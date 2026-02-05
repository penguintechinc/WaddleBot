# Waddles Database Schema Reference

## Overview

Waddles uses PostgreSQL as its primary database with read replica support for high-performance query operations. The architecture separates read operations (command lookups, permission checks) to read replicas while write operations (executions, logging) use the primary database.

**Database Configuration:**
- Primary database for writes and critical operations
- Read replicas for command lookups and high-frequency queries
- Connection pooling for concurrent operations
- Per-module table separation for reduced lock contention

## Key Shared Tables

### Servers Table
The `servers` table is shared across all collector modules and tracks monitored platform channels:

```sql
servers (
    id,
    owner,
    platform,           -- 'twitch', 'discord', 'slack'
    channel,
    server_id,
    is_active,
    webhook_url,
    config,             -- JSON configuration
    last_activity,
    created_at,
    updated_at
)
```

### Collector Modules Table
Tracks registered collector modules and their health status:

```sql
collector_modules (
    module_name,
    module_version,
    platform,           -- 'twitch', 'discord', 'slack'
    endpoint_url,
    health_check_url,
    status,             -- 'active', 'inactive', 'error'
    last_heartbeat,
    config,             -- JSON configuration
    created_at,
    updated_at
)
```

## Router Database Schema

### Commands Table
Core command registration and routing configuration:

```sql
commands (
    id,
    command,            -- Command name (e.g., 'help', 'stats')
    prefix,             -- '!' for local, '#' for community
    description,
    location_url,       -- URL for module endpoint
    location,           -- 'internal' for !, 'community' for #
    type,               -- 'container', 'lambda', 'openwhisk', 'webhook'
    method,             -- HTTP method (GET, POST, etc.)
    timeout,            -- Request timeout in seconds
    headers,            -- JSON headers for requests
    auth_required,      -- Boolean flag
    rate_limit,         -- Requests per minute
    is_active,
    module_type,        -- 'trigger', 'action', 'core'
    module_id,
    version,
    trigger_type,       -- 'command', 'event', 'both'
    event_types,        -- JSON array of event types
    priority,           -- Lower = higher priority
    execution_mode      -- 'sequential', 'parallel'
)
```

### Entities Table
Maps platform identifiers to Waddles entities:

```sql
entities (
    id,
    entity_id,          -- Unique Waddles entity identifier
    platform,           -- 'twitch', 'discord', 'slack'
    server_id,          -- Platform server/guild ID
    channel_id,         -- Platform channel ID
    owner,              -- Owner user ID
    is_active,
    config              -- JSON configuration
)
```

### Command Permissions Table
Entity-specific command permissions and configuration:

```sql
command_permissions (
    id,
    command_id,         -- Foreign key to commands table
    entity_id,          -- Foreign key to entities table
    is_enabled,         -- Boolean flag
    config,             -- JSON entity-specific configuration
    permissions,        -- JSON permission settings
    usage_count,        -- Number of times command used
    last_used           -- Timestamp of last usage
)
```

### Command Executions Table
Audit log for all command executions:

```sql
command_executions (
    id,
    execution_id,       -- Unique execution identifier
    command_id,         -- Foreign key to commands table
    entity_id,          -- Foreign key to entities table
    user_id,            -- Platform user ID
    message_content,    -- Original message text
    parameters,         -- JSON parsed parameters
    location_url,       -- Module endpoint URL
    request_payload,    -- JSON request sent to module
    response_status,    -- HTTP status code
    response_data,      -- JSON response from module
    execution_time_ms,  -- Execution duration
    error_message,      -- Error details if failed
    retry_count,        -- Number of retries attempted
    status              -- 'pending', 'success', 'failed'
)
```

### Rate Limits Table
Tracks rate limiting per command/entity/user:

```sql
rate_limits (
    id,
    command_id,         -- Foreign key to commands table
    entity_id,          -- Foreign key to entities table
    user_id,            -- Platform user ID
    window_start,       -- Timestamp of rate limit window start
    request_count       -- Number of requests in window
)
```

### String Match Table
Content moderation and auto-response pattern matching:

```sql
stringmatch (
    id,
    string,             -- Pattern to match (or "*" for wildcard)
    match_type,         -- 'exact', 'contains', 'word', 'regex'
    case_sensitive,     -- Boolean flag
    enabled_entity_ids, -- JSON array of entity IDs
    action,             -- 'warn', 'block', 'command', 'webhook'
    command_to_execute, -- Command to run on match
    command_parameters, -- JSON parameters for command
    webhook_url,        -- URL for webhook action
    warning_message,    -- Message for warn action
    block_message,      -- Message for block action
    priority,           -- Lower = higher priority
    is_active,
    match_count,        -- Number of times matched
    last_matched,       -- Timestamp of last match
    created_by          -- User who created rule
)
```

### Module Responses Table
Tracks responses from interaction modules and webhooks:

```sql
module_responses (
    id,
    execution_id,       -- Foreign key to command_executions
    module_name,        -- Name of responding module
    success,            -- Boolean success flag
    response_action,    -- 'chat', 'media', 'ticker', 'general', 'form'
    response_data,      -- JSON response content
    media_type,         -- 'music', 'video', 'image'
    media_url,          -- URL for media content
    ticker_text,        -- Text for ticker display
    ticker_duration,    -- Duration in seconds
    chat_message,       -- Chat message to send
    error_message,      -- Error details if failed
    processing_time_ms, -- Module processing time
    created_at          -- Timestamp
)
```

### Coordination Table
Dynamic server/channel assignment for horizontal scaling:

```sql
coordination (
    id,
    platform,           -- 'twitch', 'discord', 'slack'
    server_id,          -- Platform server/guild ID (null for Twitch)
    channel_id,         -- Platform channel ID
    entity_id,          -- Waddles entity identifier
    claimed_by,         -- Container ID that claimed this entity
    claimed_at,         -- Timestamp of claim
    status,             -- 'available', 'claimed', 'offline', 'error'
    is_live,            -- Boolean live status
    live_since,         -- Timestamp when went live
    viewer_count,       -- Current viewer count
    last_activity,      -- Timestamp of last message/event
    last_check,         -- Timestamp of last status check
    last_checkin,       -- Timestamp of last container checkin
    claim_expires,      -- Timestamp when claim expires
    heartbeat_interval, -- Seconds between heartbeats
    error_count,        -- Consecutive error count
    metadata,           -- JSON additional data
    priority,           -- Priority for claim selection
    max_containers,     -- Max containers that can claim
    config,             -- JSON configuration
    created_at,
    updated_at
)
```

## Collector Database Schemas

### Platform-Specific Patterns

Each collector (Twitch, Discord, Slack) follows similar schema patterns:

#### Platform Tokens
```sql
{platform}_tokens (
    team_id,            -- Discord: guild_id, Slack: team_id, Twitch: user_id
    access_token,
    refresh_token,
    expires_at,
    token_type,
    scope,
    created_at,
    updated_at
)
```

#### Platform Entities
```sql
-- Discord/Slack: servers/teams with multiple channels
{platform}_guilds (
    guild_id,
    name,
    owner_id,
    config,             -- JSON configuration
    is_active,
    created_at,
    updated_at
)

-- Twitch: individual channels
twitch_channels (
    channel_id,
    broadcaster_id,
    broadcaster_name,
    config,             -- JSON configuration
    is_active,
    created_at,
    updated_at
)
```

#### Event Logging
```sql
{platform}_events (
    event_id,
    event_type,         -- 'message', 'subscription', 'follow', etc.
    platform_ids,       -- JSON with server/channel/user IDs
    event_data,         -- JSON event payload
    processed,          -- Boolean flag
    created_at
)
```

#### Activity Tracking
```sql
{platform}_activities (
    event_id,           -- Foreign key to events table
    activity_type,      -- 'follow', 'sub', 'cheer', 'raid', etc.
    user_id,            -- Platform user ID
    username,
    amount,             -- Points or quantity
    context_sent,       -- Boolean flag if sent to context API
    reputation_sent,    -- Boolean flag if sent to reputation API
    created_at
)
```

## Module-Specific Schemas

### Memories Module

#### Memories Table
```sql
memories (
    id,
    community_id,
    entity_id,
    memory_type,        -- 'quote', 'url', 'note'
    title,              -- Title for URLs and notes
    content,            -- Quote text or note content
    url,                -- URL for url type
    author,             -- Author for quotes
    context,            -- Additional context
    tags,               -- JSON array of tags
    created_by,         -- User ID who created
    created_by_name,    -- Username who created
    created_at,
    updated_at,
    is_active,
    usage_count,        -- Number of times accessed
    last_used           -- Timestamp of last access
)
```

#### Reminders Table
```sql
reminders (
    id,
    memory_id,          -- Foreign key to memories table
    community_id,
    entity_id,
    user_id,            -- User to remind
    user_name,
    reminder_text,      -- Reminder message
    remind_at,          -- Timestamp to send reminder
    created_at,
    is_sent,            -- Boolean flag
    sent_at,            -- Timestamp when sent
    is_recurring,       -- Boolean flag
    recurring_pattern,  -- 'daily', 'weekly', 'monthly'
    recurring_end       -- End date for recurring reminders
)
```

#### Memory Reactions Table
```sql
memory_reactions (
    id,
    memory_id,          -- Foreign key to memories table
    user_id,            -- User who reacted
    reaction_type,      -- 'like', 'love', 'helpful', etc.
    created_at
)
```

#### Memory Categories Table
```sql
memory_categories (
    id,
    community_id,
    name,               -- Category name
    description,        -- Category description
    color,              -- Display color
    icon,               -- Display icon
    created_by,         -- User who created category
    created_at
)
```

### Calendar Module

#### Events Table
```sql
events (
    id,
    community_id,
    entity_id,
    title,              -- Event title
    description,        -- Event description
    event_date,         -- Start date/time
    end_date,           -- End date/time
    location,           -- Event location
    max_attendees,      -- Maximum attendee limit
    created_by,         -- User who created event
    created_by_name,    -- Username
    status,             -- 'pending', 'approved', 'rejected', 'cancelled'
    approved_by,        -- User who approved
    approved_by_name,   -- Username of approver
    approved_at,        -- Approval timestamp
    rejection_reason,   -- Reason if rejected
    attendees,          -- JSON array of attendee IDs
    tags,               -- JSON array of tags
    is_recurring,       -- Boolean flag
    recurring_pattern,  -- 'daily', 'weekly', 'monthly', 'yearly'
    recurring_end_date, -- End date for recurring events
    notification_sent,  -- Boolean flag for reminders
    created_at,
    updated_at
)
```

#### Event Attendees Table
```sql
event_attendees (
    id,
    event_id,           -- Foreign key to events table
    user_id,            -- Platform user ID
    user_name,          -- Username
    status,             -- 'attending', 'maybe', 'declined'
    joined_at           -- Timestamp when joined
)
```

#### Event Reminders Table
```sql
event_reminders (
    id,
    event_id,           -- Foreign key to events table
    reminder_time,      -- Timestamp to send reminder
    reminder_type,      -- '1day', '1hour', '15min'
    message,            -- Reminder message
    sent,               -- Boolean flag
    created_at
)
```

### Inventory Module

#### Inventory Items Table
```sql
inventory_items (
    id,
    community_id,
    item_name,          -- Unique item name
    description,        -- Item description
    labels,             -- JSON array of labels (max 5)
    is_checked_out,     -- Boolean checkout status
    checked_out_to,     -- User ID if checked out
    checked_out_at,     -- Checkout timestamp
    checked_in_at,      -- Last checkin timestamp
    created_by,         -- User who added item
    created_at,
    updated_at
)
```

#### Inventory Activity Table
```sql
inventory_activity (
    id,
    community_id,
    item_id,            -- Foreign key to inventory_items
    action,             -- 'add', 'checkout', 'checkin', 'delete', 'update'
    performed_by,       -- User who performed action
    details,            -- JSON action details
    created_at
)
```

### YouTube Music Module

#### YouTube Now Playing Table
```sql
youtube_now_playing (
    community_id,       -- Primary key
    video_id,           -- YouTube video ID
    title,              -- Track title
    artist,             -- Artist name
    album,              -- Album name
    duration,           -- Duration in seconds
    thumbnail_url,      -- Thumbnail image URL
    requested_by,       -- User who requested
    started_at,         -- Playback start timestamp
    updated_at
)
```

#### YouTube Search Cache Table
```sql
youtube_search_cache (
    community_id,
    user_id,            -- User who searched
    query,              -- Search query
    results,            -- JSON array of search results
    created_at
)
```

#### YouTube Activity Table
```sql
youtube_activity (
    community_id,
    user_id,            -- User who performed action
    action,             -- 'search', 'play', 'stop'
    details,            -- JSON action details
    created_at
)
```

### Spotify Module

#### Spotify Tokens Table
```sql
spotify_tokens (
    community_id,
    user_id,            -- User who authenticated
    access_token,       -- OAuth access token
    refresh_token,      -- OAuth refresh token
    expires_at,         -- Token expiration timestamp
    scope,              -- OAuth scopes granted
    created_at,
    updated_at
)
```

#### Spotify Now Playing Table
```sql
spotify_now_playing (
    community_id,       -- Primary key
    track_uri,          -- Spotify track URI
    track_name,         -- Track name
    artists,            -- JSON array of artists
    album,              -- Album name
    duration_ms,        -- Duration in milliseconds
    album_art_url,      -- Album art image URL
    is_playing,         -- Boolean playback state
    progress_ms,        -- Current playback position
    requested_by,       -- User who requested
    started_at,         -- Playback start timestamp
    updated_at
)
```

#### Spotify Search Cache Table
```sql
spotify_search_cache (
    community_id,
    user_id,            -- User who searched
    query,              -- Search query
    results,            -- JSON array of search results
    created_at
)
```

### Browser Source Module

#### Browser Source Tokens Table
```sql
browser_source_tokens (
    community_id,
    source_type,        -- 'ticker', 'media', 'general'
    token,              -- Unique token for URL
    is_active,          -- Boolean active status
    created_at
)
```

#### Browser Source History Table
```sql
browser_source_history (
    community_id,
    source_type,        -- 'ticker', 'media', 'general'
    content,            -- JSON content displayed
    session_id,         -- Router session ID
    created_at
)
```

#### Browser Source Access Log Table
```sql
browser_source_access_log (
    community_id,
    source_type,        -- 'ticker', 'media', 'general'
    ip_address,         -- Accessing IP address
    user_agent,         -- Browser user agent
    accessed_at
)
```

## Workflow Core Module Database Schema

### Workflows Table
Core workflow definitions and metadata:

```sql
workflow_definitions (
    workflow_id UUID PRIMARY KEY,
    community_id INTEGER NOT NULL,
    entity_id INTEGER NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'draft',        -- 'draft', 'published', 'archived'
    trigger_type VARCHAR(50) NOT NULL,         -- 'command', 'event', 'webhook', 'schedule'
    trigger_config JSONB NOT NULL,             -- Trigger-specific configuration
    nodes JSONB NOT NULL,                      -- Node definitions (key -> node config)
    connections JSONB NOT NULL,                -- Array of connections between nodes
    global_variables JSONB DEFAULT '{}',       -- Workflow-level variables
    settings JSONB DEFAULT '{}',               -- Workflow settings (timeouts, retries)
    created_by INTEGER NOT NULL,
    updated_by INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    FOREIGN KEY (community_id) REFERENCES communities(id),
    FOREIGN KEY (entity_id) REFERENCES entities(entity_id),
    INDEX idx_workflow_community (community_id),
    INDEX idx_workflow_entity (entity_id),
    INDEX idx_workflow_status (status)
)
```

### Workflow Executions Table
Execution records for workflow runs:

```sql
workflow_executions (
    execution_id UUID PRIMARY KEY,
    workflow_id UUID NOT NULL,
    community_id INTEGER NOT NULL,
    entity_id INTEGER NOT NULL,
    trigger_type VARCHAR(50) NOT NULL,        -- How execution was triggered
    trigger_data JSONB,                        -- Data from trigger (webhook payload, command args, etc.)
    status VARCHAR(50) DEFAULT 'pending',     -- 'pending', 'running', 'success', 'failed', 'cancelled'
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_ms INTEGER,                       -- Execution duration in milliseconds
    error_message TEXT,                        -- Error details if failed
    output_variables JSONB DEFAULT '{}',       -- Final output from workflow
    retry_count INTEGER DEFAULT 0,
    is_test_run BOOLEAN DEFAULT false,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    FOREIGN KEY (workflow_id) REFERENCES workflow_definitions(workflow_id),
    FOREIGN KEY (community_id) REFERENCES communities(id),
    FOREIGN KEY (entity_id) REFERENCES entities(entity_id),
    INDEX idx_execution_workflow (workflow_id),
    INDEX idx_execution_community (community_id),
    INDEX idx_execution_status (status),
    INDEX idx_execution_created (created_at)
)
```

### Workflow Node Executions Table
Node-level execution tracking for each node in a workflow:

```sql
workflow_node_executions (
    node_execution_id UUID PRIMARY KEY,
    execution_id UUID NOT NULL,
    workflow_id UUID NOT NULL,
    node_id VARCHAR(255) NOT NULL,             -- Node identifier within workflow
    node_type VARCHAR(50) NOT NULL,            -- e.g., 'trigger_command', 'action_module', 'condition_if'
    status VARCHAR(50) DEFAULT 'pending',     -- 'pending', 'running', 'success', 'failed', 'skipped'
    input_variables JSONB DEFAULT '{}',        -- Variables passed to node
    output_variables JSONB DEFAULT '{}',       -- Variables produced by node
    output_port VARCHAR(50),                   -- Which output port was taken (for conditionals)
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_ms INTEGER,
    error_message TEXT,
    result_data JSONB,                         -- Node-specific result data
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),

    FOREIGN KEY (execution_id) REFERENCES workflow_executions(execution_id),
    FOREIGN KEY (workflow_id) REFERENCES workflow_definitions(workflow_id),
    INDEX idx_node_execution (execution_id),
    INDEX idx_node_execution_workflow (workflow_id),
    INDEX idx_node_execution_node (node_id)
)
```

### Workflow Schedules Table
Scheduled execution configurations:

```sql
workflow_schedules (
    schedule_id UUID PRIMARY KEY,
    workflow_id UUID NOT NULL,
    community_id INTEGER NOT NULL,
    entity_id INTEGER NOT NULL,
    schedule_type VARCHAR(50) NOT NULL,        -- 'cron', 'interval', 'one_time'
    cron_expression VARCHAR(255),              -- Cron format (e.g., "0 12 * * *")
    interval_seconds INTEGER,                  -- For interval-based schedules
    timezone VARCHAR(50) DEFAULT 'UTC',
    next_execution_at TIMESTAMP,
    last_execution_at TIMESTAMP,
    execution_count INTEGER DEFAULT 0,
    max_executions INTEGER,                    -- NULL = unlimited
    is_active BOOLEAN DEFAULT true,
    context_data JSONB DEFAULT '{}',           -- Data passed to workflow on execution
    created_by INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    FOREIGN KEY (workflow_id) REFERENCES workflow_definitions(workflow_id),
    FOREIGN KEY (community_id) REFERENCES communities(id),
    FOREIGN KEY (entity_id) REFERENCES entities(entity_id),
    INDEX idx_schedule_workflow (workflow_id),
    INDEX idx_schedule_active (is_active),
    INDEX idx_schedule_next_exec (next_execution_at)
)
```

### Workflow Permissions Table
Entity and community-based access control:

```sql
workflow_permissions (
    permission_id UUID PRIMARY KEY,
    workflow_id UUID NOT NULL,
    entity_id INTEGER NOT NULL,
    community_id INTEGER NOT NULL,
    user_id INTEGER,                           -- NULL for community-level permissions
    permission_type VARCHAR(50) NOT NULL,     -- 'can_view', 'can_edit', 'can_execute', 'can_delete'
    granted_by INTEGER NOT NULL,
    granted_at TIMESTAMP NOT NULL DEFAULT NOW(),

    FOREIGN KEY (workflow_id) REFERENCES workflow_definitions(workflow_id),
    FOREIGN KEY (entity_id) REFERENCES entities(entity_id),
    FOREIGN KEY (community_id) REFERENCES communities(id),
    UNIQUE KEY unique_permission (workflow_id, entity_id, permission_type),
    INDEX idx_permission_workflow (workflow_id),
    INDEX idx_permission_entity (entity_id)
)
```

### Workflow Webhooks Table
Webhook configurations for triggering workflows:

```sql
workflow_webhooks (
    webhook_id UUID PRIMARY KEY,
    workflow_id UUID NOT NULL,
    token VARCHAR(255) UNIQUE NOT NULL,        -- Public token (32-char hex)
    secret VARCHAR(255) NOT NULL,              -- Private secret (32-char hex)
    name VARCHAR(255) NOT NULL,
    description TEXT,
    url TEXT NOT NULL,                         -- Full public URL for webhook
    enabled BOOLEAN DEFAULT true,
    require_signature BOOLEAN DEFAULT true,    -- Require HMAC-SHA256 signature
    ip_allowlist TEXT[] DEFAULT '{}',          -- Array of allowed CIDR/IPs
    rate_limit_max INTEGER DEFAULT 60,         -- Max requests per window
    rate_limit_window INTEGER DEFAULT 60,      -- Rate limit window in seconds
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_triggered_at TIMESTAMP,
    last_execution_id UUID,
    trigger_count INTEGER DEFAULT 0,

    FOREIGN KEY (workflow_id) REFERENCES workflow_definitions(workflow_id),
    UNIQUE KEY unique_token (token),
    INDEX idx_webhook_workflow (workflow_id),
    INDEX idx_webhook_token (token)
)
```

### Workflow Audit Log Table
Comprehensive audit trail for all operations:

```sql
workflow_audit_log (
    audit_id UUID PRIMARY KEY,
    workflow_id UUID,
    community_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    action VARCHAR(100) NOT NULL,              -- 'create', 'update', 'publish', 'execute', 'delete'
    resource_type VARCHAR(50) NOT NULL,        -- 'workflow', 'schedule', 'webhook', 'execution'
    resource_id VARCHAR(255),
    old_values JSONB,                          -- Previous values for updates
    new_values JSONB,                          -- New values for updates
    result VARCHAR(50) DEFAULT 'success',      -- 'success', 'failure'
    error_message TEXT,
    details JSONB DEFAULT '{}',                -- Additional context
    ip_address INET,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),

    FOREIGN KEY (workflow_id) REFERENCES workflow_definitions(workflow_id),
    FOREIGN KEY (community_id) REFERENCES communities(id),
    INDEX idx_audit_workflow (workflow_id),
    INDEX idx_audit_community (community_id),
    INDEX idx_audit_user (user_id),
    INDEX idx_audit_action (action),
    INDEX idx_audit_created (created_at)
)
```

### Workflow Templates Table
Reusable workflow templates:

```sql
workflow_templates (
    template_id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),                     -- e.g., 'notifications', 'moderation', 'gamification'
    template_workflow JSONB NOT NULL,          -- Complete workflow definition
    preview_image_url TEXT,
    download_count INTEGER DEFAULT 0,
    rating DECIMAL(3,2),                       -- Average user rating (0-5)
    tags TEXT[],                               -- Array of searchable tags
    is_public BOOLEAN DEFAULT true,
    created_by INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    UNIQUE KEY unique_template_name (name),
    INDEX idx_template_category (category),
    INDEX idx_template_public (is_public)
)
```

## Database Optimization Strategies

### Indexing
- Primary keys on all `id` columns
- Foreign key indexes for joins
- Composite indexes on frequently queried columns (community_id, entity_id, user_id)
- Index on `is_active` flags for filtering

### Connection Pooling
- Separate connection pools for read and write operations
- ThreadPoolExecutor for concurrent database operations
- Configurable pool sizes based on module load

### Caching
- Redis caching for frequently accessed data (commands, permissions)
- TTL-based cache invalidation
- Thread-safe local caching with fallback

### Table Separation
- Per-module tables reduce lock contention
- Separate activity/audit tables from operational tables
- Historical data archival strategies

### Performance Tuning
- Read replicas for high-frequency queries
- Bulk operation support for mass updates
- Prepared statements for repeated queries
- Query optimization with EXPLAIN analysis
