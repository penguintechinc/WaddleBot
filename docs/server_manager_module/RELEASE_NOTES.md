# Server Manager Interaction Module - Release Notes

## v1.0.0 — Initial Release

*Released: 2026-02-24*

### Overview

First release of the **Server Manager Interaction Module** — WaddleBot's unified game and voice server management system. This release absorbs and replaces the `server_status_interaction_module`, fully preserving all existing API routes under `/api/v1/server-status/*` while introducing a comprehensive new surface under `/api/v1/server-manager/`.

---

### New Features

#### Game Server Management (RCON)

- **Multi-game RCON support**: Rust, Minecraft (Java + Bedrock), CS2, ARK: Survival Evolved, Valheim, and any Source Engine RCON–compatible server
- **Connection pooling**: Persistent authenticated RCON connections per `(community_id, server_id)` with configurable TTL (`RCON_CONNECTION_TTL`, default 60 s)
- **Command execution**: Send arbitrary RCON commands and receive structured responses with full audit logging to `rcon_command_log`
- **Player management**: List connected players with Steam ID / UUID resolution, kick, and ban operations
- **Connection testing**: `POST /<community_id>/connect-test` validates credentials and reachability without persisting data

#### Voice Server Management

- **Mumble (Ice RPC)**: Channel listing, user move between channels, server-wide message broadcast via `zeroc-ice`
- **TeamSpeak (ServerQuery)**: Channel listing, client move, server-wide message broadcast via `ts3`
- **Unified API surface**: Mumble and TeamSpeak share identical endpoint signatures — callers need no knowledge of the underlying protocol

#### AES-256-GCM Credential Encryption

- Server credentials are encrypted by the hub backend (Node.js `rconController.js`) using `RCON_ENCRYPTION_KEY` before being stored
- This module decrypts credentials in memory only for the duration of a connection attempt; plaintext is never persisted
- SSRF protection blocks connections to private/loopback IP addresses

#### Reputation-Driven Auto-Moderation

- **FICO-style scoring**: Reputation scores on a 300–850 scale sourced from the `reputation_module`
- **Per-server policies**: Configurable `reputation_kick_threshold` and `reputation_ban_threshold` stored in `server_access_policies`
- **Automatic enforcement**: `enforcement_service.py` evaluates all connected players on server join and on manual trigger
- **Manual enforcement**: `POST /<community_id>/servers/<id>/enforce` triggers an immediate scan of all connected players

#### Cross-Platform Moderation Sync

- Bans can be propagated to all other servers in a community in a single request (`sync_to_all_servers: true`)
- Ban events are forwarded to `security_core_module` for global enforcement (`notify_security_core: true`, default)
- `server_ban_sync` table tracks propagation status per target server

#### Comprehensive Audit Logging

- **RCON command log** (`rcon_command_log`): Every command, operator, raw response, success flag, and timestamp
- **Access log** (`server_access_log`): Every kick/ban with actor, target player, reason, auto_enforced flag, and reputation score at time of action
- **Ban sync log** (`server_ban_sync`): Per-server sync status and timestamp

#### Hub Backend Integration

- `rconController.js` added to the hub backend, proxying all frontend requests after JWT validation and community scoping
- Admin routes: full CRUD for servers, command execution, kick/ban, channels, move, message, policy, enforce, logs
- Member routes: read-only server info, live status, player list (no credentials exposed)

#### Frontend Components

- **`AdminRconServers.jsx`**: 5-tab admin interface (Servers, Commands, Players, Voice, Policy)
- **`GameServers.jsx`**: Member-facing card grid showing server status and live player counts

---

### Backward Compatibility

All endpoints previously served by `server_status_interaction_module` are preserved:

```
/api/v1/server-status/*   →   All existing routes continue to work unchanged
```

No migration is required for existing integrations. The old module's tables are extended in-place by migration `055_server_manager.sql`.

---

### Database Changes

**Migration**: `config/postgres/migrations/055_server_manager.sql`

**Changes to existing tables:**

| Table | Change |
|-------|--------|
| `server_status_configs` | Added columns: `server_type`, `game_type`, `encrypted_password`, `rcon_port` |

**New tables:**

| Table | Purpose |
|-------|---------|
| `rcon_command_log` | Immutable RCON command audit trail |
| `server_ban_sync` | Cross-server ban propagation tracking |
| `server_access_policies` | Per-server reputation thresholds and access rules |
| `server_access_log` | Kick/ban action audit trail |

---

### New API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/server-manager/<cid>/connect-test` | Test server credentials without saving |
| `POST` | `/api/v1/server-manager/<cid>/command` | Execute RCON command |
| `GET` | `/api/v1/server-manager/<cid>/servers/<id>/status` | Live server status |
| `GET` | `/api/v1/server-manager/<cid>/servers/<id>/players` | Current player list |
| `POST` | `/api/v1/server-manager/<cid>/servers/<id>/kick` | Kick a player |
| `POST` | `/api/v1/server-manager/<cid>/servers/<id>/ban` | Ban a player |
| `GET` | `/api/v1/server-manager/<cid>/servers/<id>/channels` | List voice channels |
| `POST` | `/api/v1/server-manager/<cid>/servers/<id>/move` | Move voice user |
| `POST` | `/api/v1/server-manager/<cid>/servers/<id>/message` | Broadcast voice message |
| `GET` | `/api/v1/server-manager/<cid>/servers/<id>/policy` | Get access policy |
| `PUT` | `/api/v1/server-manager/<cid>/servers/<id>/policy` | Set access policy |
| `POST` | `/api/v1/server-manager/<cid>/servers/<id>/enforce` | Run enforcement pass |
| `GET` | `/api/v1/server-manager/<cid>/servers/<id>/access-log` | Access audit log |

---

### New Services

| Service | Purpose |
|---------|---------|
| `rcon_service.py` | RCON connection pool and command dispatch |
| `mumble_service.py` | Mumble Ice RPC integration |
| `teamspeak_service.py` | TeamSpeak ServerQuery integration |
| `encryption_service.py` | AES-256-GCM credential decryption |
| `enforcement_service.py` | Reputation threshold enforcement |
| `provider_service.py` | Protocol routing (rcon / mumble / teamspeak) |
| `status_service.py` | Backward-compat status polling (absorbed from old module) |

---

### New Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `RCON_ENCRYPTION_KEY` | Yes | — | 64-char hex AES-256-GCM key |
| `RCON_CONNECTION_TTL` | No | `60` | Pool idle TTL in seconds |
| `SECURITY_CORE_URL` | Recommended | `http://security-core:8090` | Ban sync target |
| `SERVER_MANAGER_URL` | No (hub only) | `http://server-manager-interaction:8098` | Set in hub backend |

---

### Technology Stack

| Component | Version |
|-----------|---------|
| Python | 3.12 |
| Quart | 0.19.0+ |
| Hypercorn | 0.16.0+ |
| PostgreSQL | 13+ |
| rcon | 2.4.0+ |
| ts3 | 2.0.0+ |
| zeroc-ice | 3.7+ |
| cryptography | 42.0+ |
| httpx | 0.27.0+ |

---

### Documentation

Complete documentation bundle created at `docs/server_manager_module/`:

| File | Description |
|------|-------------|
| `OVERVIEW.md` | Module purpose, capabilities, quick reference |
| `API.md` | All Python module and hub backend proxy endpoints |
| `USAGE.md` | Setup, Docker, health checks, common workflows |
| `CONFIGURATION.md` | All environment variables with examples |
| `ARCHITECTURE.md` | System diagram, data flows, DB schema |
| `TESTING.md` | Test strategy, data setup, validation procedures |
| `TROUBLESHOOTING.md` | Common errors, debug steps, log locations |
| `RELEASE_NOTES.md` | This file |

---

**Module**: server_manager_interaction_module
**Version**: 1.0.0
**Port**: 8098
**Replaces**: server_status_interaction_module
**Release Date**: 2026-02-24
**Status**: Initial Release
