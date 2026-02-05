# Waddles Event Processing

## Introduction

Waddles uses an event-driven architecture where trigger modules (receivers, pollers, cron) send events to the processing layer (router), which then routes to appropriate action modules (interactive, pushing, security) based on commands, patterns, and event types. This document describes the event processing flow, command architecture, and message type handling.

For information on router architecture, communication protocols, and integration patterns, see [Shared Patterns](./shared-patterns.md).

## Event Processing Flow

The complete event processing flow from message reception to response delivery:

1. **Message Reception**: Collector receives message/event from platform (Twitch, Discord, Slack)
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

## Command Architecture

Waddles supports multiple command input methods across platforms:

### Command Support Matrix

| Platform | Slash Commands | Prefix Commands | Modals | Buttons | Autocomplete |
|----------|---------------|-----------------|--------|---------|--------------|
| Discord  | `/command`    | `!command`      | Yes    | Yes     | Yes          |
| Slack    | `/waddlebot`  | `!command`      | Yes    | Yes     | No           |
| Twitch   | N/A           | `!command`      | N/A    | N/A     | N/A          |

### Slash Commands (`/`)

Platform-native slash commands with rich UI support:

- **Discord**: Native `/command` with options, autocomplete, and ephemeral responses
- **Slack**: `/waddlebot command` with Block Kit responses and modals
- **Rich Interactions**: Modals, buttons, select menus, and forms
- **Deferred Responses**: Support for long-running operations (15 min timeout)

### Prefix Commands (`!` and `#`)

Traditional text-based commands in chat messages:

#### `!` (Local Container Modules)

Interaction modules running in local Docker containers:

- **Fast execution**: Container-to-container communication
- **Full control**: Complete control over execution environment
- **Stateful**: Can maintain state and persistent connections
- **Examples**: `!help`, `!stats`, `!admin`, `!so`, `!alias`, `!inventory`

#### `#` (Community Modules)

Marketplace modules running in Lambda/OpenWhisk:

- **Serverless execution**: Automatic scaling for high demand
- **Community-contributed**: Marketplace-managed modules
- **Stateless**: Functions with cold start considerations
- **Examples**: `#weather`, `#translate`, `#game`

### Interactions (Modals, Buttons, Selects)

Interactive UI components for Discord and Slack:

- **Modals**: Form dialogs for collecting user input
- **Buttons**: Clickable action buttons with custom IDs
- **Select Menus**: Dropdown selections (single or multi-select)
- **Custom ID Format**: `module:action:context` (e.g., `inventory:buy:item_123`)

## Activity Processing Flow (Legacy)

The legacy activity processing flow for reputation tracking:

1. **Event Reception**: Platform-specific webhook/event handler
2. **Event Logging**: Store raw event in `{platform}_events` table
3. **Activity Extraction**: Determine activity type and point value
4. **Context Lookup**: Get user identity from core via `identity_name`
5. **Reputation Submission**: Send activity to core reputation API
6. **Activity Logging**: Store processed activity in `{platform}_activities` table

**Activity Point Values**:
- Twitch: follow=10, sub=50, bits=variable, raid=30, subgift=60, ban=-10
- Discord: message=5, reaction=2, member_join=10, voice_join=8, voice_time=1/min, boost=100
- Slack: message=5, file_share=15, reaction=3, member_join=10, app_mention=8

## Message Types and Event Processing

All events sent to router must include a message_type field to determine processing path.

### Supported Message Types

#### Command Types
- **chatMessage**: User chat messages that may contain `!` or `#` prefix commands
- **slashCommand**: Platform slash commands (`/command` on Discord, `/waddlebot` on Slack)

#### Interaction Types
- **interaction**: Generic interaction event (button, modal, select)
- **modal_submit**: Modal form submission with user input
- **button_click**: Button interaction click
- **select_menu**: Select menu option selection

#### Subscription/Monetization Events
- **subscription**: User subscriptions
- **gift_subscription**: Gift subscriptions
- **follow**: User follows
- **donation**: User donations/tips
- **cheer**: Twitch bits/cheers
- **resub**: Subscription renewals

#### Stream Events
- **raid**: Twitch raids
- **host**: Twitch hosts
- **stream_online**: Stream goes live
- **stream_offline**: Stream ends

#### Member Events
- **member_join**: User joins server/channel
- **member_leave**: User leaves server/channel
- **voice_join**: User joins voice channel
- **voice_leave**: User leaves voice channel
- **voice_time**: Voice channel time tracking
- **boost**: Discord server boosts
- **channel_join**: Channel joins

#### Moderation Events
- **ban**: User bans
- **kick**: User kicks
- **timeout**: User timeouts
- **warn**: User warnings

#### Other Events
- **reaction**: Message reactions
- **file_share**: File uploads
- **app_mention**: Bot mentions

### Processing Behavior

- **chatMessage**: Full command processing with `!`/`#` prefix detection and string matching
- **slashCommand**: Route to command processor, translate to `!command` format for module execution
- **interaction**: Route based on `custom_id` format (`module:action:context`)
- **Stream events**: Activity tracking and event-triggered module execution
- **Non-chat events**: Direct reputation processing and event-triggered modules
- **Event-specific modules**: Modules configured to respond to specific event types
- **Reputation tracking**: All events can contribute to reputation scores

## Multiple Module Execution

Multiple modules can be triggered by a single message or event, supporting both sequential and parallel execution.

### Module Matching

- **Command Matching**: Multiple modules can register the same command
- **Event Matching**: Multiple modules can register for the same event types
- **Pattern Matching**: String patterns can trigger multiple modules
- **Priority-Based**: Execute in priority order (lower number = higher priority)

### Trigger Types

- **command**: Triggered by command prefix (default behavior)
- **event**: Triggered by specific event types
- **both**: Triggered by both commands and events

### Execution Modes

- **sequential**: Execute modules one at a time in priority order
- **parallel**: Execute modules concurrently using ThreadPoolExecutor

### Priority System

- **Lower Numbers = Higher Priority**: Priority field determines execution order
- **Sequential Execution**: Lower priority modules wait for higher priority completion
- **Parallel Execution**: All modules execute simultaneously regardless of priority

### Event Configuration

Modules specify which event types trigger them:

```json
{
  "trigger_type": "event",
  "event_types": ["subscription", "follow", "donation"],
  "execution_mode": "parallel"
}
```

### Permission Enforcement

- **All modules check permissions**: Every module verifies entity permissions before execution
- **Individual enablement**: Each module can be enabled/disabled per entity
- **Permission inheritance**: Modules inherit entity-level permission settings

## Execution Engine Types

Router supports four execution engine types for routing commands to different execution environments.

### Container

- **Local Container Modules**: `!` prefixed commands
- **Fast Execution**: Container-to-container communication
- **Stateful**: Can maintain state and persistent connections
- **Examples**: AI interaction, alias, shoutout, inventory

### Lambda

- **AWS Lambda Functions**: `#` prefixed community modules
- **Serverless**: Automatic scaling for high demand
- **Stateless**: Functions with cold start considerations
- **Region-Based**: Deploy in multiple AWS regions

### OpenWhisk

- **Apache OpenWhisk Functions**: `#` prefixed community modules
- **Open Source Serverless**: Self-hosted serverless platform
- **Stateless**: Functions with cold start considerations
- **Custom Deployment**: Deploy on your own infrastructure

### Webhook

- **Generic HTTP Endpoints**: `#` prefixed community modules
- **Flexible Integration**: Connect to any HTTP service
- **Custom Authentication**: Support for API keys, OAuth, etc.
- **External Services**: Integrate with third-party services

---

## Summary

Waddles's event processing system provides a comprehensive, scalable architecture for handling events from multiple platforms, routing them through a high-performance processing layer, and executing appropriate actions through interaction modules. The system supports horizontal scaling, multiple execution environments, content moderation, and rich response types including browser source integration for OBS.

Key features:
- Event-driven architecture with 16-step processing flow
- Dual command prefix system (`!` local, `#` community)
- Support for multiple message types and event processing
- Multiple module execution with sequential and parallel modes
- Four execution engine types (container, Lambda, OpenWhisk, webhook)
- Comprehensive permission enforcement and rate limiting

For detailed information on router architecture, string matching, module responses, coordination systems, and integration patterns, see [Shared Patterns](./shared-patterns.md).
