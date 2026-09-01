# Discord Module Release Notes

## Version 0.3.0 (Current)

**Release Date**: 2026-02-24

### New Features

- **Dynamic Slash Command Autocomplete**: Commands now provide intelligent parameter suggestions based on database state
- **Modal Form Support**: Interactive Discord modal forms for multi-field input collection
- **Rich Button Interactions**: Enhanced button styling (primary, secondary, success, danger, link)
- **Select Menu Components**: Dropdown menus with option groups and dynamic options
- **Message Splitting**: Automatic split and link of responses exceeding 2000 character limit
- **Admin Context Commands**: `/context switch` and `/link` for admin guild management
- **Credential Management**: Secure per-user-per-guild credential storage with Redis caching

### Improvements

- Improved error handling with user-friendly messages
- Enhanced logging with DEBUG level support
- Better performance with async credential caching
- Optimized database queries with strategic indexing
- Comprehensive Prometheus metrics for monitoring
- Support for up to 25 options in select menus

### Bug Fixes

- Fixed interaction timeout issues on slow networks
- Corrected embed color formatting (0xFFD700 format)
- Resolved button custom_id length validation
- Fixed modal field validation and error messages
- Improved rate limit handling with exponential backoff

### Breaking Changes

None

### Database Migrations

**Migration 047**: Added `discord_credentials` table with encrypted storage
**Migration 048**: Added `discord_interactions` history tracking
**Migration 049**: Added command metadata storage

To apply:
```bash
docker-compose exec trigger-discord python -m scripts.migrate_db
```

### Dependencies Updated

- py-cord: 2.4.1 → 2.5.0
- httpx: 0.24.0 → 0.25.0
- redis: 5.0.0 (new)
- cryptography: 41.0.0 (new, for credential encryption)

### Configuration Changes

**New Environment Variables**:
- `MODAL_SUPPORT_ENABLED` (default: true)
- `BUTTON_SUPPORT_ENABLED` (default: true)
- `SELECT_SUPPORT_ENABLED` (default: true)
- `REDIS_CREDENTIAL_TTL` (default: 3600 seconds)
- `INTERACTION_TIMEOUT_SECONDS` (default: 900)

**Changed Defaults**:
- `MESSAGE_SPLIT_ENABLED` now defaults to true

### Deprecations

- Prefix command support (deprecated in favor of slash commands)
  - Will be removed in v1.0.0
  - Still supported but not recommended

### Known Issues

- Modal submission sometimes fails on slow networks (timeout workaround in progress)
- Select menu with 25+ options may cause Discord rendering issues
- Button interactions occasionally lose context after 15 minutes (Redis TTL related)

### Upgrade Path from v0.2.0

1. **Backup database**
   ```bash
   docker-compose exec infra-postgres pg_dump waddlebot > backup_v0.2.0.sql
   ```

2. **Update image**
   ```bash
   docker-compose pull discord-module
   ```

3. **Apply migrations**
   ```bash
   docker-compose exec trigger-discord python -m scripts.migrate_db
   ```

4. **Restart service**
   ```bash
   docker-compose up -d discord-module
   ```

5. **Verify**
   ```bash
   curl http://localhost:8003/health
   ```

### Testing

All features tested with:
- Unit tests: 95% coverage
- Integration tests: Router interaction
- E2E tests: Full Discord workflow
- Load tests: 1000 events/second

---

## Version 0.2.0

**Release Date**: 2026-01-15

### New Features

- **Slash Command Groups**: Organized commands into 20+ groups (/form, /poll, /ticket, etc.)
- **Embed Support**: Rich Discord embeds with colors, fields, footers
- **Guild Management**: Track connected guilds and their configurations
- **Comprehensive Logging**: Info, warning, and error level logging
- **Health Check Endpoints**: `/health` and `/metrics` for monitoring

### Improvements

- Faster command registration (parallel processing)
- Better error messages for invalid commands
- Optimized event forwarding to router

### Bug Fixes

- Fixed slash command group ordering
- Resolved guild join event handling
- Corrected interaction token validation

### Breaking Changes

None

---

## Version 0.1.0

**Release Date**: 2025-12-01

### Initial Release

- **Core Functionality**: py-cord bot integration with WaddleBot router
- **Event Normalization**: Standard event format for all interactions
- **Basic Commands**: Support for slash commands and text commands
- **Message Responses**: Simple text responses to Discord events
- **Status Endpoint**: `/api/v1/status` for health monitoring
- **Discord Integration**: Full WebSocket connectivity to Discord

### Known Limitations

- Only text responses (no embeds)
- Limited to basic command routing
- No credential management
- No advanced UI components

---

## Compatibility Matrix

| Discord Module | py-cord | Python | Node | Status |
|---|---|---|---|---|
| 0.3.0 | 2.5.0+ | 3.12+ | - | Current |
| 0.2.0 | 2.4.1 | 3.11+ | - | Supported |
| 0.1.0 | 2.3.0 | 3.11+ | - | EOL (2026-01-15) |

### End of Life Schedule

- **0.1.0**: Ended 2026-01-15
- **0.2.0**: Ends 2026-06-15 (EOL date)
- **0.3.0**: Current (support until next major version)

---

## Migration Guides

### From v0.1.0 to v0.2.0

Key changes:
- Command group structure introduced
- Embed support requires response format changes
- Guild configuration table added

Steps:
1. Update environment variables
2. Apply database migration
3. Update command handlers to use new response format
4. Test all commands

### From v0.2.0 to v0.3.0

Key changes:
- Modal support added
- Credential management introduced
- Redis caching optional (recommended for production)

Steps:
1. (Optional) Set up Redis server
2. Apply database migrations
3. Update command handlers to use new UI components
4. Configure new environment variables
5. Test modal and credential workflows

---

## Roadmap

### Planned for v0.4.0 (Q2 2026)

- [ ] Advanced embed formatting with images
- [ ] Message reactions support
- [ ] Thread support for conversations
- [ ] Webhook integration for cross-server messages
- [ ] Message command context menu
- [ ] User command context menu

### Planned for v1.0.0 (Q3 2026)

- [ ] Remove prefix command support
- [ ] Enterprise authentication
- [ ] Advanced permission management
- [ ] Multi-language support
- [ ] Custom emoji handling
- [ ] Voice channel integration

### Planned for v2.0.0 (2027)

- [ ] Multiple Discord bot instances per module
- [ ] Distributed message cache
- [ ] Advanced sharding support
- [ ] Machine learning-based moderation
- [ ] Community tier system

---

## Support and Feedback

### Report Issues

- **GitHub Issues**: github.com/penguintechinc/waddlebot/issues
- **Email**: support@penguintech.io
- **Discord Server**: https://discord.gg/waddlebot

### Request Features

1. Check [existing issues](github.com/penguintechinc/waddlebot/issues)
2. Create GitHub issue with detailed use case
3. Vote on popular features
4. Discuss in [Discord community](https://discord.gg/waddlebot)

### Security Vulnerabilities

Report security issues privately:
- **Email**: security@penguintech.io
- **Do not** open public GitHub issues for security vulnerabilities

---

## Version Numbering

This project follows Semantic Versioning (SemVer):

- **Major (X.0.0)**: Breaking changes, removed features
- **Minor (0.X.0)**: New features, backward compatible
- **Patch (0.0.X)**: Bug fixes, security patches

### Build Metadata

Versions may include build timestamp:
- `0.3.0.1708688130` - v0.3.0 built at epoch 1708688130
- `.1708688130` is automatically appended by CI/CD

---

## Changelog Structure

Each release includes:

1. **Version and Date** - Clear version number and release date
2. **New Features** - Major additions
3. **Improvements** - Performance, UX, code quality
4. **Bug Fixes** - Issues resolved
5. **Breaking Changes** - Backward-incompatible changes
6. **Database Migrations** - Schema changes
7. **Dependencies** - Updated packages
8. **Configuration** - New/changed environment variables
9. **Deprecations** - Features being phased out
10. **Known Issues** - Outstanding problems
11. **Testing** - QA coverage
12. **Upgrade Path** - How to upgrade from previous version

---

## Getting the Latest Version

### Check Current Version

```bash
curl http://localhost:8003/api/v1/status | jq .version
```

### Update to Latest

```bash
# Pull latest image
docker-compose pull discord-module

# Restart service
docker-compose up -d discord-module

# Verify
curl http://localhost:8003/health
```

### Pin to Specific Version

```yaml
services:
  discord-module:
    image: waddlebot/discord-module:0.3.0
    # Instead of 'latest'
```

---

## Contributing

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for:
- Code style guidelines
- Testing requirements
- Pull request process
- Development setup
- Release procedures
