# Twitch Module Release Notes

## Version History

All notable changes to the Twitch Module are documented in this file. The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

### Added
- Distributed caching support with Redis fallback
- Viewer activity tracking with join/leave/heartbeat detection
- EventSub webhook signature verification (HMAC-SHA256)
- Message deduplication (last 5000 message IDs)
- Broadcaster-only command enforcement (!! prefix)
- Dynamic channel management with periodic sync (300s default)

### Changed
- Migrated from single HTTP endpoint to dual-ingestion (IRC + EventSub)
- Updated message splitting to include part numbers ([1/3], etc.)
- Improved error handling with retry logic and exponential backoff

### Fixed
- IRC connection drops now trigger automatic reconnection
- EventSub webhooks with duplicate message IDs now properly rejected (409)
- Cache misses gracefully fallback to API calls

### Deprecated
- Legacy single-ingestion mode (IRC only) — now requires EventSub

### Removed
- Old message format (no longer supports deprecated field names)

### Security
- All EventSub webhooks now require HMAC-SHA256 verification
- API keys enforced for service endpoints (/api/v1/bot/send)
- Credentials no longer logged in debug mode

### Performance
- Viewer tracking optimized for 100+ channels
- Cache layer reduces Twitch API calls by ~80%
- Message processing latency reduced to <100ms average

---

## [v1.2.0] - 2025-02-24

### Added
- ViewerTracker service for polling Twitch Chatters API
- Leaderboard integration with Hub API for viewer presence
- Metrics endpoint with Prometheus-format output
- Health check endpoint (`/health` and `/health?type=ready`)
- Detailed status endpoint (`/api/v1/status`)
- Support for EventSub event types:
  - `channel.subscribe` (new subscriptions)
  - `channel.subscription.gift` (gift subscriptions)
  - `channel.raid` (channel raids)
  - `channel.follow` (new followers)
  - `channel.cheer` (bits/cheer donations)
  - `stream.online` (stream started)
  - `stream.offline` (stream ended)

### Changed
- Upgraded TwitchIO to >=2.8.0 for improved IRC stability
- Moved from Flask to Quart for better async/await support
- EventSub webhook handler moved to dedicated endpoint (`/eventsub/webhook`)
- Message format updated to include badges and additional metadata
- API response format standardized across all endpoints

### Fixed
- IRC bot now handles channel membership updates correctly
- Message splitting preserves formatting and special characters
- EventSub webhook retries now properly deduplicated
- Database connection pooling now respects pool size limit

### Deprecated
- Synchronous message handlers (migrate to async handlers)
- Legacy API endpoint format (use new standardized format)

### Removed
- Support for TwitchIO <2.8.0
- Old webhook format (must use new EventSub format)

### Security
- Added HMAC-SHA256 verification for all EventSub webhooks
- Database credentials now encrypted in environment
- API key validation added to all service endpoints

### Performance
- Message processing latency improved from ~200ms to ~50ms
- Viewer tracking reduces API calls by tracking activity between polls
- Cache layer added for channel metadata (reduces API calls)

---

## [v1.1.0] - 2025-01-15

### Added
- Initial support for multiple Twitch channels (dynamic join/leave)
- TwitchBotService with IRC bot capabilities
- EventSubHandler for webhook-based event ingestion
- Message splitting for responses exceeding 500 characters
- Broadcaster-only command support (!! prefix)
- Channel refresh loop (configurable interval)

### Changed
- Moved from single-channel to multi-channel architecture
- Updated to use TwitchIO for IRC bot implementation
- Refactored message routing to support both IRC and EventSub

### Fixed
- IRC connection stability improved
- Message parsing now handles edge cases (empty messages, special chars)
- Rate limiting now properly tracked per-channel

### Security
- Added service API key validation
- OAuth token handling improved (no longer logged)
- Improved error messages (no credential leakage)

### Performance
- Multi-channel support reduces resource usage per channel
- Message queue implementation prevents bottlenecks

---

## [v1.0.0] - 2024-12-01

### Added
- Initial release of Twitch Module
- Basic IRC bot functionality
- Simple message parsing and command routing
- Health check endpoint
- Metrics collection (Prometheus format)
- PostgreSQL database integration for channel list
- Support for message sending to Twitch chat

### Documentation
- Initial API documentation
- Configuration guide
- Usage examples
- Architecture overview

---

## Migration Guides

### Upgrading from v1.1.0 to v1.2.0

**Breaking Changes**: None

**Recommended Actions**:
1. Enable EventSub webhooks in Twitch console
2. Configure `EVENTSUB_SECRET` environment variable
3. Set `EVENTSUB_CALLBACK_URL` to your public endpoint
4. Optional: Enable `VIEWER_TRACKING_ENABLED` for leaderboards

**No code changes required** — existing IRC bot functionality continues to work.

### Upgrading from v1.0.0 to v1.1.0

**Breaking Changes**:
- Message format changed (now includes badges)
- Channel management moved to database

**Migration Steps**:
1. Update database schema (migration script provided)
2. Migrate channel list to database table
3. Update Router API integration to handle new message format
4. Restart service with new configuration

**Migration Script**:
```sql
-- Add channels table if not exists
CREATE TABLE IF NOT EXISTS channels (
    channel_id VARCHAR(32) PRIMARY KEY,
    channel_name VARCHAR(255) UNIQUE NOT NULL,
    community_id VARCHAR(32),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Migrate existing channels from old format
INSERT INTO channels (channel_id, channel_name, is_active)
SELECT id, name, true FROM old_channels_table
ON CONFLICT (channel_id) DO NOTHING;
```

---

## Known Issues

### Current Release (v1.2.0)

**Minor**:
- EventSub webhook registration may show "pending" for 30-60 seconds before "enabled"
  - Workaround: Refresh Twitch console, or wait 5 minutes for automatic retry

- Viewer tracking may be delayed 60+ seconds during peak load
  - Impact: Leaderboard updates slightly delayed
  - Mitigation: Increase `VIEWER_POLL_INTERVAL` if needed

**Limitation**:
- Maximum 5000 EventSub subscriptions per application
  - Each channel needs ~5 subscriptions (subscribe, raid, follow, cheer, stream.online/offline)
  - Supports up to ~1000 channels per application
  - Workaround: Create multiple Twitch applications for scaling

---

## Deprecation Timeline

### v1.3.0 (Planned)
- `DEPRECATED`: Synchronous message handlers (migrate to async)
- `DEPRECATED`: Old event format in EventSub webhooks
- `DEPRECATED`: Database v1 schema (plan migration to v2)

### v2.0.0 (Future)
- `REMOVE`: Support for TwitchIO <2.8.0
- `REMOVE`: Synchronous message handlers
- `REMOVE`: Legacy event format
- `BREAKING`: Database schema v1 (v2 required)

---

## Performance Benchmarks

### v1.2.0

**Latency** (50th percentile):
```
IRC message → Router: 45ms
EventSub webhook → handler: 20ms
Viewer poll: 500ms
API call (cached): <1ms
API call (miss): 100ms
```

**Throughput** (per single instance):
```
Messages: ~500 msgs/sec (IRC limit: ~20/30s per channel)
EventSub events: ~100 events/sec (Twitch limit: varies)
Viewer polls: 1 poll/60s per channel (configurable)
Channels supported: ~100-200 (depends on activity)
```

**Resource Usage** (single instance, 50 channels, 5k viewers/channel):
```
Memory: ~500MB (with Redis cache)
CPU: ~15% average
Network: ~10 Mbps average
```

### Scaling Characteristics

**Vertical Scaling** (more resources per instance):
- +50 channels: +~200MB memory, +~5% CPU
- +1000 channels: +~4GB memory, +~50% CPU

**Horizontal Scaling** (multiple instances):
- 2 instances: Linear throughput increase, shared Redis cache
- 4 instances: Minor diminishing returns (Twitch API rate limits)
- 8+ instances: Diminishing returns, consider multiple apps

---

## Platform Support

### Twitch API Versions
- Helix API: Latest (no specific version lock)
- EventSub: v1
- IRC: Latest (Twitch TMI)

### Python Versions
- Supported: 3.12+
- Not supported: <3.12

### Databases
- PostgreSQL: 12+
- Other: Not supported (PyDAL abstraction, but not tested)

### Deployment
- Docker: Supported (Python 3.12 slim base)
- Kubernetes: Supported (Helm chart available)
- Bare metal: Supported with standard Python 3.12 installation

---

## Dependencies

### Production Dependencies
```
quart>=0.19.0        # ASGI web framework
hypercorn>=0.15.0    # ASGI server
twitchio>=2.8.0      # Twitch IRC bot library
httpx>=0.24.0        # Async HTTP client
pydal>=20230101.0    # Database abstraction
python-dotenv>=1.0.0 # Environment file support
flask_core>=0.1.0    # Shared Flask utilities
platform_receiver>=1.0.0  # Platform integration
```

### Development Dependencies
```
pytest>=7.0.0
pytest-asyncio>=0.21.0
pytest-cov>=4.0.0
black>=22.0.0
isort>=5.0.0
flake8>=4.0.0
mypy>=0.990
```

---

## Contributors

**v1.2.0**:
- Initial implementation: Twitch Module Core Team
- EventSub integration: Platform Integration Team
- Viewer tracking: Leaderboard Team

**v1.1.0**:
- Multi-channel support: Engineering Team

**v1.0.0**:
- Initial prototype: Platform Team

---

## License

Copyright (c) 2024-2025 Penguin Tech Inc. All rights reserved.

This project is licensed under the Limited AGPL-3.0 license with commercial use restrictions. See [LICENSE.md](../../LICENSE.md) for details.

---

## Support & Feedback

- **Issues**: Report bugs at https://github.com/penguintechinc/waddlebot/issues
- **Discussions**: Community discussions at https://github.com/penguintechinc/waddlebot/discussions
- **Security**: Report security issues to security@penguintech.io
- **Documentation**: See [docs/twitch_module/](.) for comprehensive guides

---

## Roadmap

### Short Term (v1.3.0)
- Redis Sentinel support for high availability
- EventSub subscription automatic recovery
- Enhanced metrics (histograms, summaries)

### Medium Term (v2.0.0)
- Database schema v2 with better indexing
- Async database driver (PostgreSQL native)
- WebSocket support for real-time updates
- Custom command handlers

### Long Term
- Machine learning for bot activity optimization
- Advanced leaderboard analytics
- Integration with other streaming platforms
- Multi-region support with database replication

---

## Changelog Format

This changelog follows the [Keep a Changelog](https://keepachangelog.com/) format:

- **Added**: New features
- **Changed**: Changes to existing functionality
- **Deprecated**: Soon-to-be removed features
- **Removed**: Removed features
- **Fixed**: Bug fixes
- **Security**: Security updates
- **Performance**: Performance improvements

Versions are formatted as `vMajor.Minor.Patch` (Semantic Versioning).

---

**Last Updated**: 2025-02-24
**Maintained by**: Penguin Tech Inc
**Repository**: https://github.com/penguintechinc/waddlebot
