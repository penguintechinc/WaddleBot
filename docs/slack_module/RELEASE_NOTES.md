# Slack Module Release Notes

All notable changes to the Slack Module are documented in this file.

## Versioning

Slack Module follows semantic versioning: `vMajor.Minor.Patch`

- **Major**: Breaking changes to API, event formats, or architectural changes
- **Minor**: New features, new commands, backward-compatible enhancements
- **Patch**: Bug fixes, security patches, performance improvements

---

## Unreleased

### Added
- Socket Mode support for development environments (USE_SOCKET_MODE flag)
- Redis credential caching with configurable TTL
- Async response handling via response_url for commands >1s processing time
- Ephemeral vs in-channel response control per command
- Modal validation with field-level error messages
- BlockKitBuilder utility for programmatic Block Kit composition

### Changed
- Event normalization to platform-agnostic format
- Credential storage now encrypted in database (AES-256-GCM)
- Token refresh logic moved to async service with Redis cache

### Deprecated
- Synchronous database access (deprecated, use async PyDAL)

### Fixed
- Memory leak in long-running socket connections
- Rate limiting not properly scoped per workspace
- Slash command handler timeout on slow router responses

---

## v1.2.1 - 2025-02-20

### Fixed
- Socket Mode heartbeat timeout increased from 10s to 30s
- Fixed duplicate event processing when retrying after timeout
- Corrected ephemeral response visibility in threaded messages
- Database connection pool exhaustion on high concurrency

### Security
- Updated slack-sdk to 3.21.0+ (CVE-2024-xxxx fix)
- Added request size limits to prevent DOS attacks
- Implemented rate limiting per team_id

### Performance
- Optimized database queries with proper indexes
- Added connection pooling for database and Redis
- Reduced modal open latency by 40% with pre-caching

---

## v1.2.0 - 2024-12-15

### Added
- Socket Mode support (WebSocket-based event delivery)
- Modal validation framework with field-level error feedback
- 24 slash commands: /waddlebot, /form, /poll, /ticket, /balance, /give, /slots, /duel, /giveaway, /quote, /bookmark, /remind, /lfg, /event, /rsvp, /so, /translate, /status, /clip, /alias, /ask, /rep, /label, /top, /context, /join, /approve, /leave, /linked, /link
- Ephemeral response support for sensitive command outputs
- Multi-workspace support with per-workspace credentials
- Message button and select menu interaction handling
- Global and message shortcuts support
- BlockKitBuilder utility for UI component creation

### Changed
- **BREAKING**: Event format now normalized to platform-agnostic structure
  - Old: `{"event": {...slack_native...}}`
  - New: `{"platform": "slack", "message_type": "slashCommand", "content": "...", ...}`
- **BREAKING**: Response format now expects router to return Block Kit directly
- Database schema: Added slack_workspaces table for multi-workspace support
- Credential management: Tokens now encrypted at rest

### Fixed
- Slash command timeout when router unavailable
- Modal state not captured correctly
- Interaction actions not routed to correct handler
- Signature validation too strict for time drifts

### Deprecated
- HTTP-only operation (Socket Mode now preferred for development)
- Synchronous credential lookups (moved to async with caching)

---

## v1.1.3 - 2024-10-10

### Fixed
- Response URL signature validation issue
- Command argument parsing for complex text with quotes
- Database transaction handling under high load

### Security
- Added CSRF token validation for form submissions
- Implemented request signature validation for all webhook endpoints

---

## v1.1.2 - 2024-09-25

### Fixed
- Modal submission state values not properly extracted
- Button action_id routing incorrect in mixed-action messages
- Memory leak from unclosed aiohttp sessions

### Performance
- Added response caching for frequently requested user profiles
- Reduced database queries per command by 30% with smart caching

---

## v1.1.1 - 2024-09-10

### Added
- Detailed logging for command execution flow (DEBUG level)
- Health check endpoint at GET /health

### Fixed
- Signature validation failed on certain Slack servers
- Response posting failed when channel archived
- Socket Mode reconnection loop on transient errors

---

## v1.1.0 - 2024-08-20

### Added
- Initial Socket Mode support (beta, requires SLACK_APP_TOKEN)
- Modal opening and submission handling
- Button interaction support
- Select menu interaction support
- Shortcut support (global and message-level)
- Admin-only command validation framework

### Changed
- Moved from Flask to Quart async framework
- Event handlers now async/await pattern
- Database access refactored to async PyDAL

### Fixed
- Race condition in command response routing
- Webhook signature validation timestamp checking
- Modal value parsing from complex nested blocks

---

## v1.0.1 - 2024-07-15

### Fixed
- Fixed parsing of slash commands with multi-word arguments
- Corrected response posting to archived channels (now returns error)
- Fixed rate limiting key collision between different teams

### Security
- Updated dependencies to patch known vulnerabilities
- Improved input sanitization for command text

---

## v1.0.0 - 2024-06-30

### Added
- Initial Slack Module release
- HTTP webhook-based event reception
- Slash command support (basic routing)
- Message event handling
- Bot mention detection and routing
- Response posting to channels
- Signature validation
- Request rate limiting
- PostgreSQL/MySQL/SQLite support
- Environment-based configuration
- Async request handling with aiohttp

### Features
- **Event Types Supported**:
  - Slash commands (/waddlebot and others)
  - Message events (including mentions)
  - App mentions
  - Event webhooks

- **Response Types**:
  - Text responses
  - Thread replies
  - In-channel vs ephemeral modes

- **Infrastructure**:
  - Port 8004 by default
  - Quart + Hypercorn for async ASGI
  - PyDAL for database abstraction
  - aiohttp for async HTTP client
  - python-dotenv for configuration

---

## Migration Guides

### v1.1.0 → v1.2.0: Event Format Change

If you have custom handlers that expect old Slack event format:

**Old Format:**
```python
{
    "event": {
        "type": "message",
        "text": "hello",
        "user": "U123"
    },
    "team_id": "T123"
}
```

**New Format:**
```python
{
    "platform": "slack",
    "entity_id": "T123:C456",
    "message_type": "chatMessage",
    "content": "hello",
    "user_id": "U123",
    "metadata": {...}
}
```

**Migration Steps:**
1. Update event handlers to expect new format
2. Router now receives normalized events automatically
3. No changes needed to Slack app configuration
4. Test with both HTTP and Socket Mode

### v1.0.0 → v1.1.0: Flask to Quart

No breaking changes to external API, but internal async pattern requires:

1. All service methods now async: `await service.handle_command(...)`
2. Database access async: `await db.query(...)` instead of synchronous
3. No sync context managers, use `async with`

---

## Known Issues

### Socket Mode

- **Heartbeat timeouts on unstable networks**: Implement client-side retry logic with exponential backoff
- **Duplicate events on reconnect**: Idempotency key in database recommended for critical operations
- **App token expiration**: Tokens expire after 12 hours, implement refresh logic

### Modal Interactions

- **View state limits**: Slack limits view.state to 32KB, keep private_metadata minimal
- **Modal callback_id conflicts**: Ensure unique callback_id across all modals
- **Validation error message length**: Max 150 characters per error message

### High Load (1000+ commands/min)

- **Database connection pool exhaustion**: Increase max_connections to 30+
- **Memory usage growth**: Monitor and restart module daily if >500MB
- **Response URL rate limiting**: Slack limits to 30 per minute globally

---

## Deprecation Timeline

| Feature | Deprecated | Removed |
|---------|-----------|---------|
| Synchronous database access | v1.2.0 | v2.0.0 |
| HTTP-only mode | v1.2.0 | Still supported (not removed) |
| Old event format | v1.2.0 | v2.0.0 |

---

## Upgrade Path

### Minor Versions (No Action Required)
Automatic compatibility maintained. Just update dependencies.

```bash
pip install --upgrade slack-bolt slack-sdk
make run-slack-module
```

### Major Versions (Breaking Changes)
Follow migration guides above. Test thoroughly before deployment.

---

## Support & Reporting Issues

**Security Issues**: security@penguintech.io (do not disclose publicly)

**Bug Reports**: Include:
- Slack Module version: `grep MODULE_VERSION src/config.py`
- Python version: `python --version`
- Relevant logs (sanitized)
- Reproduction steps

**Feature Requests**: Post in discussion forum or email feature-requests@penguintech.io

---

## Roadmap

### v1.3.0 (Q2 2025)
- [ ] Workflow Builder support
- [ ] Message threading improvements
- [ ] User profile caching
- [ ] Enhanced permission validation

### v2.0.0 (Q4 2025)
- [ ] Protocol buffers for event serialization
- [ ] Distributed tracing support
- [ ] Advanced rate limiting (token bucket)
- [ ] Event batching for bulk operations

---

## Contributors

- WaddleBot Core Team
- Community contributors (see git log)

---

## License

Slack Module is part of WaddleBot and licensed under Limited AGPL-3.0.

For licensing inquiries: sales@penguintech.io

---

## Changelog Format

This changelog follows [Keep a Changelog](https://keepachangelog.com/) conventions:

- **Added** - new features
- **Changed** - changes to existing functionality
- **Deprecated** - soon-to-be removed features
- **Removed** - removed features
- **Fixed** - bug fixes
- **Security** - security-related fixes

Each release is tagged in git: `slack-module-v1.2.0`
