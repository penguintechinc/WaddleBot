# Waddles Shared Patterns

## Introduction

This document describes the shared patterns, architectures, and integration protocols used across all Waddles modules. These patterns ensure consistency, performance, and maintainability across the entire system.

For information on event processing flow and message type handling, see [Event Processing](./event-processing.md).

## Router Architecture

The router module is the core processing component with high-performance features:

### Multi-Threading
- **ThreadPoolExecutor**: Configurable worker count for concurrent operations
- **Parallel Execution**: Process multiple commands simultaneously
- **Async Operations**: Support for async/await patterns with Quart

### Read Replicas
- **Separate Read Connections**: Dedicated connections for command lookups
- **Write to Primary**: All writes go to primary database
- **Load Distribution**: Distribute read load across multiple replicas

### Caching
- **In-Memory Cache**: TTL-based caching for frequently accessed data
- **Command Cache**: Cache command definitions (5 minute TTL)
- **Entity Cache**: Cache entity permissions (10 minute TTL)
- **Redis Integration**: Optional Redis for distributed caching

### Rate Limiting
- **Sliding Window Algorithm**: Track requests over time windows
- **Per-User/Command/Entity**: Granular rate limiting
- **Background Cleanup**: Automatic cleanup of expired rate limit entries
- **Configurable Limits**: Set limits per command, entity, or user role

### Batch Processing
- **Concurrent Event Processing**: Process up to 100 events simultaneously
- **Bulk Operations**: Batch database operations for efficiency
- **Performance Optimization**: Reduce database round trips

### String Matching
- **Pattern Matching**: Support for exact, contains, word boundary, and regex patterns
- **Content Moderation**: Automatic warning and blocking
- **Auto-Responses**: Trigger commands based on message patterns
- **Cached Patterns**: Compiled regex patterns for performance

### Metrics
- **Real-time Monitoring**: Performance metrics and statistics
- **Health Checks**: Database connectivity and service health
- **Usage Analytics**: Command usage, execution times, error rates
- **String Match Statistics**: Pattern match counts and effectiveness

## Router Communication Protocol

### To Interaction Modules

Router sends comprehensive context to all interaction modules:

- **userID**: User's identity in Waddles system
- **community context**: Community ID, platform, server, channel
- **user level**: User's permission level in community (owner, admin, moderator, user)
- **entity information**: Complete entity details for routing

### Module Installation

Rules for module installation and availability:

- **Marketplace modules**: By default NOT added to communities
- **Core interaction modules**: Added to communities by default
- **Community owners**: Can uninstall core interaction modules
- **Community modules**: Can replace core interaction modules
- **Permission-based**: Installation requires entity-level permissions

### Context Passing

All module communications include:

- **Full user context**: Identity, platform, community membership
- **Permission level**: User's role and capabilities in community
- **Entity configuration**: Community-specific module settings
- **Session tracking**: Session ID for response correlation

## Community Portal System

The Hub Module provides web-based community management through Flask/Quart framework.

### Portal Access

Community owners can grant portal access:

```bash
!community portal login add email@domain.com
```

### Native Framework Features

- **Flask-Security-Too**: User authentication and session management
- **Flask-Mailer**: Email sending (SMTP/sendmail support)
- **WTForms**: User input handling with validation
- **Flask-Admin**: Data display and management
- **Flash Messages**: User notifications and alerts
- **Decorators**: Access control and authentication

### Dashboard Features

- **Community Members**: View roles and reputation scores
- **Installed Modules**: Monitor core vs marketplace modules
- **Statistics**: Activity metrics and usage statistics
- **User Management**: Numerical IDs and display names
- **Browser Source URLs**: Unique URLs for OBS integration

### Browser Source Integration

- **Three Source Types**: ticker (scrolling text), media (music display), general (flexible HTML)
- **Unique Token URLs**: Secure token-based URLs per community and source type
- **Copy-to-Clipboard**: Easy OBS integration
- **Recommended Settings**: OBS configuration guidance for each source type
- **Security Notice**: URL privacy warnings and best practices

### Authentication

- **Flask-Security-Too**: Built on Flask's authentication system
- **Custom Fields**: Extended Waddles user fields in user table
- **Session Management**: Secure session handling with expiration
- **Role-Based Access**: Permissions based on community roles

### Email Configuration

Environment variables for email support:

```bash
SMTP_HOST=smtp.company.com
SMTP_USERNAME=hub@company.com
SMTP_PASSWORD=smtp_password
SMTP_TLS=true
SMTP_PORT=587
```

- **Automatic Fallback**: Uses sendmail if SMTP not configured

### Database Integration

- **Flask-Security user table**: Core user authentication
- **Custom Waddles fields**: Additional fields for bot integration
- **Cross-platform linking**: Identity linking across platforms
- **Reputation tracking**: User reputation scores

## String Matching System

The string matching system provides content moderation, auto-responses, and custom actions based on message patterns.

### Pattern Matching

- **Multiple Match Types**: exact, contains, word boundary, regex
- **Case Sensitivity**: Configurable per pattern
- **Compiled Regex**: Cached compiled patterns for performance
- **Priority System**: Lower numbers = higher priority

### Wildcard Support

- **Universal Trigger**: Use `"*"` as pattern to match all text
- **Logging**: Useful for analytics and message logging
- **Debugging**: Capture all messages for troubleshooting

### Content Moderation

- **Automatic Warning**: Send warning messages to users
- **Message Blocking**: Block inappropriate content
- **Notification**: Alert moderators of blocked content
- **Usage Tracking**: Monitor rule effectiveness

### Auto-Responses

- **Command Triggers**: Execute commands based on message patterns
- **Parameter Passing**: Pass matched content to commands
- **Custom Actions**: Community-specific automated responses

### Webhook Integration

- **External Processing**: Send matched content to external webhooks
- **HTTP POST**: POST request with message data and context
- **Custom Integration**: Connect to external systems and services

### Entity-Based Rules

- **Per-Entity Configuration**: Different rules per platform/server/channel
- **Enabled Entity IDs**: Specify which entities use each rule
- **Override Support**: Entity-specific rule overrides

### Match Types

- **exact**: Exact string match (case sensitive/insensitive)
- **contains**: Substring search within message
- **word**: Word boundary matching (whole words only)
- **regex**: Full regular expression support with compiled pattern caching
- **`*`**: Universal wildcard - matches all text (useful for logging/analytics)

### Actions

- **warn**: Send warning message to user
- **block**: Block message and send notification
- **command**: Execute specified command with optional parameters
- **webhook**: Send message data to external webhook URL for processing

## Module Response System

The module response system tracks responses from interaction modules and webhooks, supporting multiple response types for different display contexts.

### Response Tracking

- **Execution Correlation**: Link responses to specific command executions
- **Module Attribution**: Track which module generated each response
- **Success Monitoring**: Monitor module execution success rates
- **Error Logging**: Capture and log module errors for debugging

### Session Management

- **Required Session ID**: All responses must include session_id for tracking
- **Session Validation**: Router validates session_id matches entity_id
- **Timeout Handling**: Sessions expire after configurable timeout
- **Redis Storage**: Session data stored in Redis with TTL

### Response Actions

Support for multiple response types:

- **chat**: Text-based chat response back to user
- **media**: Rich media display for music/video with album art and metadata
- **ticker**: Scrolling text ticker for notifications and alerts
- **general**: Flexible content display for HTML, forms, announcements, and alerts
- **form**: Interactive form for user input with field definitions

### Response Type Examples

#### Chat Response
```json
{
  "response_action": "chat",
  "chat_message": "Response text to user"
}
```

#### Media Response
```json
{
  "response_action": "media",
  "media_type": "music",
  "media_url": "https://youtube.com/watch?v=...",
  "response_data": {
    "title": "Song Title",
    "artist": "Artist Name",
    "album": "Album Name",
    "duration": "3:45",
    "thumbnail_url": "https://...",
    "service": "youtube"
  }
}
```

#### Ticker Response
```json
{
  "response_action": "ticker",
  "ticker_text": "Scrolling message text",
  "ticker_duration": 10,
  "response_data": {
    "priority": "high",
    "style": "info"
  }
}
```

### Browser Source Integration

#### Media Response
- Rich media display with album art, track info, and progress bars
- Real-time progress updates for Spotify playback
- Service indicators (YouTube, Spotify, etc.)
- Automatic timeout and cleanup

#### Ticker Response
- Scrolling text overlay with priority queuing and animations
- Configurable duration and styling
- Multiple priority levels (high, normal, low)
- Queue management with overflow protection

#### Display Features
- **Transparent Backgrounds**: All browser sources use transparent backgrounds for OBS compositing
- **WebSocket Updates**: Real-time updates via WebSocket connections
- **Configurable Duration**: Set display duration for each response type
- **Responsive Design**: Adapts to different OBS scene sizes and layouts

## Coordination System (Horizontal Scaling)

The coordination system enables horizontal scaling by dynamically distributing workload across multiple collector container instances.

### Dynamic Assignment

- **Automatic Claiming**: Containers automatically claim available servers/channels
- **Race-Condition Safe**: Atomic claiming using database locks
- **Load Balancing**: Distributes workload evenly across containers
- **Auto-Discovery**: New containers automatically find work

### Load Distribution

- **Configurable Limits**: Each container claims up to configurable number (default: 5)
- **Priority-Based**: Prioritizes high-value entities (live streams, high activity)
- **Even Distribution**: Ensures workload is distributed evenly
- **Resource Optimization**: Containers can adjust claim count based on load

### Live Stream Priority

- **Live Status Tracking**: Track whether streams/channels are live
- **Viewer Count**: Monitor audience size for prioritization
- **Activity Levels**: Track message/activity frequency
- **Dynamic Prioritization**: Prioritize live and active entities

### Configurable Limits

- **MAX_CLAIMS**: Maximum entities per container (default: 5)
- **HEARTBEAT_INTERVAL**: Checkin interval in seconds (default: 300)
- **CLAIM_TIMEOUT**: Claim expiration timeout (default: 360 seconds)
- **GRACE_PERIOD**: Grace period before claim release (default: 60 seconds)

### Platform Support

#### Discord/Slack
- **Server-Based**: Claims servers with multiple channels
- **Channel Monitoring**: Monitors all channels within claimed servers
- **Hierarchical**: Server → Channel relationship

#### Twitch
- **Channel-Based**: Claims individual channels (no servers)
- **Direct Monitoring**: Each channel monitored independently
- **Flat Structure**: No hierarchical relationship

### Claim Management

#### Atomic Claims
- **Database Locks**: Race-condition safe claiming
- **Transaction Support**: All claims in database transactions
- **Conflict Resolution**: Handle simultaneous claim attempts

#### Checkin System
- **5-Minute Interval**: Containers must checkin every 5 minutes
- **Claim Maintenance**: Checkin extends claim expiration
- **Activity Reporting**: Report entity status during checkin

#### Timeout and Cleanup
- **6-Minute Threshold**: Claims released if container misses checkin for 6+ minutes
- **1-Minute Grace**: 1 minute grace period before release
- **Automatic Cleanup**: Background cleanup of expired claims and missed checkins

### Horizontal Scaling Features

- **Auto-Discovery**: New containers automatically find work
- **Load Balancing**: Prioritize live channels and high-priority entities
- **Fault Tolerance**: Failed containers release claims for others to pick up
- **Resource Optimization**: Containers can adjust claim count based on load
- **Offline Management**: Containers automatically release offline entities and claim new ones
- **Continuous Monitoring**: 5-minute checkin cycle ensures active monitoring and claim maintenance

## Marketplace Integration

The marketplace system enables community-contributed modules with installation, versioning, and subscription management.

### Module Discovery

- **Browse Featured**: Featured and popular modules
- **Search and Filter**: Search by name, category, tags
- **Categorization**: Hierarchical module categorization
- **Ratings and Reviews**: User reviews and ratings

### Installation Management

- **Install Modules**: Install modules per entity
- **Uninstall Modules**: Remove modules from entity
- **Enable/Disable**: Toggle modules without uninstalling
- **Bulk Operations**: Install/uninstall multiple modules

### Permission System

- **Entity-Based Access**: Installation permissions per entity
- **Role-Based**: Permissions based on community roles
- **Owner Override**: Community owners can always install/uninstall

### Router Sync

- **Automatic Registration**: Modules auto-register commands with router
- **Automatic Removal**: Commands removed when module uninstalled
- **Configuration Sync**: Module settings sync to router
- **Real-time Updates**: Changes reflected immediately

### Version Control

- **Multiple Versions**: Support for multiple module versions
- **Upgrade/Downgrade**: Upgrade or downgrade module versions
- **Version History**: Track version changes and updates
- **Rollback Support**: Rollback to previous version if needed

### Usage Analytics

- **Performance Tracking**: Track module performance metrics
- **Adoption Rates**: Monitor module installation and usage
- **Error Tracking**: Track module errors and failures
- **User Feedback**: Collect user feedback and ratings

### Paid Subscription System

- **Subscription Management**: Complete subscription lifecycle management
- **Payment Integration**: Integration with payment processors
- **Trial Periods**: Support for free trial periods
- **Expiration Handling**: Block access for expired subscriptions
- **Renewal Reminders**: Automatic renewal reminders

## Core API Integration

All collector modules follow the same integration pattern with core APIs.

### Registration

- **Module Registration**: Register module with core on startup
- **Module Information**: Name, version, platform, endpoints
- **Health Check URL**: Endpoint for health monitoring
- **Configuration**: Module-specific configuration

### Heartbeat

- **Periodic Health Status**: Send health status every 5 minutes
- **Uptime Reporting**: Report module uptime and statistics
- **Performance Metrics**: Report performance metrics
- **Error Reporting**: Report errors and issues

### Server List

- **Pull Monitored Servers**: Get list of servers/channels to monitor
- **Platform Filter**: Filter by platform (Twitch, Discord, Slack)
- **Active Filter**: Filter by active status
- **Configuration**: Get server-specific configuration

### Context API

- **User Identity Lookup**: Look up user identity for reputation tracking
- **Cross-Platform**: Link identities across platforms
- **Verification**: Verify user identities with codes
- **Session Management**: Manage user sessions

### Event Forwarding

- **Send Processed Events**: Forward events to router for command processing
- **Batch Support**: Send multiple events in batch
- **Session Tracking**: Include session ID for response tracking
- **Error Handling**: Handle forwarding errors gracefully

---

## Summary

Waddles's shared patterns provide a consistent, high-performance architecture across all modules. These patterns enable horizontal scaling, content moderation, rich response types, and comprehensive integration with external systems.

Key features:
- High-performance router with multi-threading and caching
- String matching for content moderation and auto-responses
- Comprehensive module response system with multiple response types
- Horizontal scaling with dynamic workload distribution
- Marketplace integration with version control and subscriptions
- Consistent Core API integration patterns across all modules

For detailed information on event processing flow and message type handling, see [Event Processing](./event-processing.md).
