# Shoutout Interaction Module — Release Notes

## v2.0.0 — Current Version

**Released:** 2026-02-16

### New Features

#### Video Shoutout Support (!vso)
- New `/api/v1/video-shoutout` endpoint for video shoutouts
- Fetches Twitch clips as primary source
- YouTube fallback via cross-platform identity resolution
- Displays video + channel information in overlay widget
- Configurable widget position and duration

#### Auto-Shoutout Functionality
- Automatic shoutouts on configurable community events
- Support for triggers: first_message, raid, host
- Per-community creator list for auto-shoutout eligibility
- Auto-shoutout eligibility checking endpoint
- Per-creator custom trigger configuration

#### Multi-Level Permission System
- Permission levels: admin_only, mod, vip, subscriber, everyone
- Separate permissions for text (!so) vs video (!vso) shoutouts
- Role-based access control (admin, mod, vip, subscriber)
- Per-community permission configuration

#### Community Type Validation
- Shoutouts limited to creator and gaming communities
- Prevents misconfiguration in incompatible community types
- Explicit community eligibility checking

#### Cooldown Management
- Per-user cooldown (prevents spam from single user)
- Per-target cooldown (prevents target from being shoutout'd too frequently)
- Configurable cooldown duration per community
- Separate cooldowns for text and video shoutouts

#### Database Credential Loading
- Load Twitch/YouTube credentials from platform_integrations table
- Fallback to environment variables if database unavailable
- Runtime credential updates without restart (with Redis support)
- Threadsafe credential management with locking

### Breaking Changes

None. Version 2.0.0 maintains backward compatibility with v0.1.0 text shoutout API.

### Architecture Changes

- Added VideoService for multi-platform video retrieval
- Added IdentityService for cross-platform identity resolution
- Added VideoShoutoutService for complex video shoutout orchestration
- Separated responsibilities: TwitchService (user data), VideoService (clips), ShoutoutService (text generation)
- Introduced asyncpg connection pool for video shoutout operations
- Circuit breaker pattern for resilience

### Database Migrations

New tables:
- `video_shoutout_config` - Community-level video shoutout configuration
- `video_shoutout_history` - Video shoutout execution history
- `auto_shoutout_creators` - Creator list for auto-shoutout triggers

Modified tables:
- `shoutout_history` - Added `shoutout_type` column (manual/auto)

### API Additions

Text Shoutouts (existing, unchanged):
- POST `/api/v1/shoutout`
- GET `/api/v1/history/{community_id}`
- GET `/api/v1/stats/{community_id}`
- POST `/api/v1/template`
- GET `/api/v1/twitch/user/{username}`
- GET `/api/v1/circuit-breaker/metrics`

Video Shoutouts (new):
- POST `/api/v1/video-shoutout` - Execute video shoutout
- POST `/api/v1/video-shoutout/auto-check` - Check eligibility for auto-trigger
- GET `/api/v1/video-shoutout/config/{community_id}` - Get configuration
- PUT `/api/v1/video-shoutout/config/{community_id}` - Update configuration
- GET `/api/v1/video-shoutout/creators/{community_id}` - List auto-shoutout creators
- POST `/api/v1/video-shoutout/creators/{community_id}` - Add creator
- DELETE `/api/v1/video-shoutout/creators/{community_id}/{platform}/{user_id}` - Remove creator
- GET `/api/v1/video-shoutout/history/{community_id}` - Get history
- GET `/api/v1/video-shoutout/video/{platform}/{username}` - Get video content (test)

### Environment Variables

New:
- `YOUTUBE_API_KEY` - For YouTube video fallback
- `VIDEO_SHOUTOUT_DEFAULT_DURATION` - Widget display duration
- `VIDEO_SHOUTOUT_DEFAULT_COOLDOWN` - Default cooldown minutes

Modified:
- `DATABASE_URL` - Now requires asyncpg, PostgreSQL only (not other databases)

### Documentation

- Comprehensive OVERVIEW.md with architecture overview
- USAGE.md with 10 common workflows and examples
- API.md with complete endpoint documentation
- ARCHITECTURE.md with service breakdown and data flows
- CONFIGURATION.md with all environment variables
- TESTING.md with unit, integration, and E2E test examples
- TROUBLESHOOTING.md with 30+ common issues and fixes
- RELEASE_NOTES.md (this file)

### Performance Improvements

- Circuit breaker prevents cascading failures
- Retry logic with exponential backoff
- Timeout management (10s for APIs, 30s for database)
- Connection pooling (asyncpg pool for video operations)
- Caching of OAuth tokens

### Security Improvements

- Input validation on all API endpoints
- Permission checking enforced in VideoShoutoutService
- Sensitive data (tokens, exact errors) not exposed in responses
- Timeout protection prevents hanging connections
- Database secrets can be loaded from secure storage
- Redis listener for credential refresh notifications

### Known Limitations

- Only Twitch and YouTube supported currently (Discord/Slack shoutout text only)
- Video shoutout requires user to have public Twitch clips or linked YouTube
- Circuit breaker requires 60 second recovery window after 5 failures
- No built-in analytics dashboard (history accessible via API)

### Migration Guide from v0.1.0

If upgrading from the hypothetical v0.1.0:

1. **Database:**
```bash
# Run new migrations
psql waddlebot < config/postgres/migrations/036_calendar_appointments.sql
psql waddlebot < config/postgres/migrations/037_fix_community_schema.sql
```

2. **Configuration:**
```bash
# Update .env with new variables
echo "YOUTUBE_API_KEY=..." >> .env
echo "VIDEO_SHOUTOUT_DEFAULT_DURATION=30" >> .env
echo "VIDEO_SHOUTOUT_DEFAULT_COOLDOWN=60" >> .env
```

3. **Existing API:**
   - All existing text shoutout endpoints unchanged
   - Existing templates continue to work
   - History and stats endpoints unchanged

4. **New Configuration:**
   - Default video shoutout config created automatically for each community
   - Empty creator list by default (no auto-shoutouts until configured)

### Bug Fixes

- Circuit breaker now properly tracks state transitions
- Token refresh handles concurrent requests correctly
- Cooldown check includes both manual and auto shoutouts
- Video lookup respects clip creation timestamp ordering

### Testing

- Unit tests for all services
- Integration tests for workflows
- E2E tests for API endpoints
- Mock Twitch/YouTube API responses
- 80%+ code coverage

---

## v0.1.0 — Initial Documentation Release

**Released:** 2026-02-16

### Initial Features

- Text shoutout generation (!so command)
- Twitch Helix API integration (user, channel, stream data)
- Customizable shoutout templates per community
- Platform-specific formatting (Twitch, Discord, Slack)
- Shoutout history tracking
- Community statistics
- Twitch API circuit breaker for resilience

### Architecture

- Single TwitchService for API integration
- ShoutoutService for template-based generation
- Database persistence in PostgreSQL
- Async/await pattern with Quart framework
- AAA logging framework integration

### API Endpoints

- POST `/api/v1/shoutout` - Generate text shoutout
- GET `/api/v1/history/{community_id}` - Retrieve history
- GET `/api/v1/stats/{community_id}` - Get statistics
- POST `/api/v1/template` - Save custom template
- GET `/api/v1/twitch/user/{username}` - Get user data (debug)
- GET `/api/v1/circuit-breaker/metrics` - Monitor resilience

### Environment Configuration

- TWITCH_CLIENT_ID
- TWITCH_CLIENT_SECRET
- DATABASE_URL
- MODULE_PORT
- LOG_LEVEL
- IDENTITY_URL
- CORE_API_URL
- ROUTER_API_URL

### Documentation

- Basic API documentation
- Configuration guide
- Troubleshooting sections
- Example requests and responses

---

## Changelog Format

Each release documents:

- **New Features**: Major functionality additions
- **Breaking Changes**: API changes requiring updates
- **Architecture Changes**: Internal refactoring
- **Database Migrations**: Schema updates
- **API Additions**: New endpoints
- **Environment Variables**: New config options
- **Bug Fixes**: Issues resolved
- **Performance**: Speed/efficiency improvements
- **Security**: Security-related enhancements
- **Testing**: Coverage improvements
- **Documentation**: Docs additions

## Version Format

Follows semantic versioning: `vMajor.Minor.Patch`

- **Major**: Breaking changes, API changes
- **Minor**: New features (backward compatible)
- **Patch**: Bug fixes, documentation

Current version: **v2.0.0**

## Support

For issues or questions about this release:
- Email: support@penguintech.io
- Docs: [Shoutout Module Docs](../)
- GitHub: [Waddlebot Repository](https://github.com/penguintechinc/waddlebot)
