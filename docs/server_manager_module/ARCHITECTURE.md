# Server Manager Interaction Module - Architecture

## System Overview

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Hub Frontend (React)                            │
│   AdminRconServers.jsx (5-tab admin)   GameServers.jsx (member grid)   │
└─────────────────────────────┬──────────────────────────────────────────┘
                              │  JWT-authenticated REST
                              ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   Hub Backend (Node.js / Express)                      │
│                       rconController.js                                │
│  - Validates JWT & community scope                                     │
│  - Encrypts server credentials (AES-256-GCM) before write             │
│  - Proxies requests to Python module at SERVER_MANAGER_URL            │
└─────────────────────────────┬──────────────────────────────────────────┘
                              │  Internal HTTP (httpx)
                              ▼
┌────────────────────────────────────────────────────────────────────────┐
│           Server Manager Interaction Module (Python / Quart)           │
│                          app.py  :8098                                 │
│                                                                        │
│  ┌────────────────────┐  ┌────────────────────┐  ┌──────────────────┐ │
│  │  provider_service  │  │ encryption_service │  │  status_service  │ │
│  │  (route to correct │  │  (AES-256-GCM      │  │  (backward-compat│ │
│  │   protocol handler)│  │   decrypt creds)   │  │   server-status) │ │
│  └────────┬───────────┘  └────────────────────┘  └──────────────────┘ │
│           │                                                            │
│    ┌──────┴──────────────────────────────┐                            │
│    │                                     │                            │
│    ▼                                     ▼                            │
│  ┌──────────────┐  ┌──────────────────────────────────────────────┐  │
│  │ rcon_service │  │ mumble_service  /  teamspeak_service          │  │
│  │  (RCON pool) │  │  (Ice RPC / ServerQuery)                     │  │
│  └──────────────┘  └──────────────────────────────────────────────┘  │
│                                                                        │
│  ┌────────────────────────────────────────────────────────────────┐   │
│  │                   enforcement_service                          │   │
│  │  reputation score fetch → threshold compare → kick/ban        │   │
│  └────────────────────────────────────────────────────────────────┘   │
│                                                                        │
│  ┌────────────────────────────────────────────────────────────────┐   │
│  │                     AsyncDAL (PostgreSQL)                      │   │
│  └────────────────────────────────────────────────────────────────┘   │
└───────┬─────────────────────────────────────────────────┬─────────────┘
        │                                                 │
        ▼                                                 ▼
┌──────────────────────────┐               ┌─────────────────────────────┐
│  Game Servers (RCON)     │               │  security_core_module       │
│  Rust / Minecraft /      │               │  (ban sync on ban events)   │
│  CS2 / ARK / Valheim     │               └─────────────────────────────┘
├──────────────────────────┤
│  Voice Servers           │
│  Mumble (Ice RPC)        │
│  TeamSpeak (ServerQuery) │
└──────────────────────────┘
```

---

## Component Descriptions

### app.py
- Quart async web application entry point
- Registers blueprints: health/metrics, `/api/v1/server-manager`, `/api/v1/server-status` (backward compat)
- Bootstraps encryption key from `RCON_ENCRYPTION_KEY` on startup
- Initializes AsyncDAL connection pool
- Starts Hypercorn with 4 workers on `MODULE_PORT`

### encryption_service.py
- Decrypts AES-256-GCM–encrypted credentials stored in `server_status_configs.encrypted_password`
- Encryption is performed by the hub backend (Node.js) using the shared `RCON_ENCRYPTION_KEY`
- This service only decrypts; never encrypts
- Decrypted credentials are held in memory only for the duration of the connection attempt

### provider_service.py
- Inspects `server_type` and `game_type` fields to route requests to the correct service
- Maps: `rcon` → `rcon_service`, `mumble` → `mumble_service`, `teamspeak` → `teamspeak_service`
- Abstracts the caller from protocol differences

### rcon_service.py
- Maintains a connection pool of authenticated RCON connections keyed by `(community_id, server_id)`
- Drops connections idle beyond `RCON_CONNECTION_TTL` seconds
- Sends commands and parses responses
- Implements `kick` and `ban` by issuing the appropriate RCON command for each game type
- Fetches player list via game-specific RCON commands

### mumble_service.py
- Connects via Ice RPC (`zeroc-ice`) to the Mumble server daemon
- Provides: `list_channels()`, `move_user()`, `send_message()`
- Maintains one Ice communicator per `(community_id, server_id)` with TTL-based teardown

### teamspeak_service.py
- Connects via ServerQuery TCP (`ts3`) to the TeamSpeak server
- Provides: `list_channels()`, `move_client()`, `send_message()`
- Handles login/logout lifecycle per request (ServerQuery does not support long-lived pools well)

### enforcement_service.py
- Fetches current player list from `rcon_service` or `mumble/teamspeak_service`
- Retrieves reputation scores for each player from the database or via API call to `reputation_module`
- Compares scores against the server's `server_access_policies` thresholds
- Calls `kick` or `ban` for players below the respective threshold
- Writes all actions to `server_access_log` with `auto_enforced = true`

### status_service.py
- Backward-compatible polling logic absorbed from the old `server_status_interaction_module`
- Exposes `/api/v1/server-status/*` routes unchanged
- Internally delegates to `provider_service` and `rcon_service`

---

## Data Flow Diagrams

### RCON Command Execution

```
Admin (Hub UI)
    │
    │  POST /:communityId/rcon/servers/:id/command
    ▼
rconController.js (Hub Backend)
    │  Verify JWT, extract community scope
    │  POST /api/v1/server-manager/:communityId/command
    ▼
app.py (Python Module)
    │
    ▼
provider_service → rcon_service
    │
    ├── Check connection pool for (community_id, server_id)
    │    ├── HIT:  reuse existing RCON connection
    │    └── MISS: decrypt credentials via encryption_service
    │              → open new RCON connection → add to pool
    │
    ├── Send command string over RCON socket
    │
    ├── Receive response string
    │
    ├── Write to rcon_command_log (async, non-blocking)
    │
    └── Return { success, response, log_id }
```

### Reputation Enforcement Cycle

```
Trigger: player join event (RCON webhook) OR manual enforce call
    │
    ▼
enforcement_service.enforce_server(community_id, server_id)
    │
    ├── Fetch player list from rcon_service / voice service
    │
    ├── For each player:
    │    ├── Lookup reputation score (DB cache or reputation_module API)
    │    ├── Fetch server policy from server_access_policies
    │    │
    │    ├── score < ban_threshold ?
    │    │    └── rcon_service.ban(player) → write access_log (auto_enforced=true)
    │    │        → optionally call security_core_module /api/v1/bans
    │    │
    │    └── score < kick_threshold ?
    │         └── rcon_service.kick(player) → write access_log (auto_enforced=true)
    │
    └── Return { players_evaluated, players_kicked, players_banned, actions[] }
```

### Cross-Platform Ban Sync

```
Ban action (manual or auto-enforced)
    │
    ▼
enforcement_service / rcon_service
    │
    ├── Write ban to origin server (RCON ban command)
    │
    ├── Write to rcon_command_log
    │
    ├── Write to server_access_log
    │
    ├── sync_to_all_servers = true ?
    │    └── For each other server in community:
    │         └── rcon_service.ban(player) on target server
    │             Write to server_ban_sync (synced=true)
    │
    └── notify_security_core = true ?
         └── POST SECURITY_CORE_URL/api/v1/bans
             { community_id, player_identifier, reason }
```

---

## Database Schema

### server_status_configs (extended by migration 055)

```sql
-- Existing columns remain; migration adds:
ALTER TABLE server_status_configs ADD COLUMN IF NOT EXISTS
    server_type VARCHAR(20) DEFAULT 'rcon',
    game_type VARCHAR(50),
    encrypted_password TEXT,  -- AES-256-GCM ciphertext (base64)
    rcon_port INTEGER;
```

### rcon_command_log

```sql
CREATE TABLE rcon_command_log (
    id              SERIAL PRIMARY KEY,
    community_id    INTEGER NOT NULL,
    server_id       INTEGER NOT NULL REFERENCES server_status_configs(id),
    executed_by_user_id INTEGER,
    command         TEXT NOT NULL,
    response        TEXT,
    success         BOOLEAN DEFAULT TRUE,
    executed_at     TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_rcon_command_log_server ON rcon_command_log(server_id, executed_at DESC);
CREATE INDEX idx_rcon_command_log_user   ON rcon_command_log(executed_by_user_id);
CREATE INDEX idx_rcon_command_log_community ON rcon_command_log(community_id, executed_at DESC);
```

### server_ban_sync

```sql
CREATE TABLE server_ban_sync (
    id                   SERIAL PRIMARY KEY,
    community_id         INTEGER NOT NULL,
    source_server_id     INTEGER NOT NULL REFERENCES server_status_configs(id),
    target_server_id     INTEGER NOT NULL REFERENCES server_status_configs(id),
    player_identifier    VARCHAR(128) NOT NULL,
    reason               TEXT,
    synced               BOOLEAN DEFAULT FALSE,
    synced_at            TIMESTAMP,
    created_at           TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_server_ban_sync_community ON server_ban_sync(community_id);
CREATE INDEX idx_server_ban_sync_player    ON server_ban_sync(player_identifier);
```

### server_access_policies

```sql
CREATE TABLE server_access_policies (
    id                          SERIAL PRIMARY KEY,
    community_id                INTEGER NOT NULL,
    server_id                   INTEGER NOT NULL REFERENCES server_status_configs(id),
    policy_type                 VARCHAR(50) NOT NULL DEFAULT 'reputation_threshold',
    reputation_kick_threshold   INTEGER DEFAULT 400,
    reputation_ban_threshold    INTEGER DEFAULT 320,
    policy_data                 JSONB DEFAULT '{}',
    created_at                  TIMESTAMP DEFAULT NOW(),
    updated_at                  TIMESTAMP DEFAULT NOW(),
    UNIQUE(community_id, server_id)
);

CREATE INDEX idx_server_access_policies_server ON server_access_policies(server_id);
```

### server_access_log

```sql
CREATE TABLE server_access_log (
    id                       SERIAL PRIMARY KEY,
    community_id             INTEGER NOT NULL,
    server_id                INTEGER NOT NULL REFERENCES server_status_configs(id),
    actor_user_id            INTEGER,
    target_player_identifier VARCHAR(128) NOT NULL,
    action                   VARCHAR(20) NOT NULL,  -- 'kick', 'ban', 'unban'
    reason                   TEXT,
    auto_enforced            BOOLEAN DEFAULT FALSE,
    reputation_score         INTEGER,
    created_at               TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_server_access_log_server ON server_access_log(server_id, created_at DESC);
CREATE INDEX idx_server_access_log_player ON server_access_log(target_player_identifier);
CREATE INDEX idx_server_access_log_community ON server_access_log(community_id, created_at DESC);
```

---

## Integration Points

### Hub Backend (`rconController.js`)

The hub backend is the sole entry point for frontend requests. It:
1. Validates the user's JWT and community membership
2. For write operations (add/update server), encrypts the raw password with AES-256-GCM using `RCON_ENCRYPTION_KEY`
3. Proxies the request to `SERVER_MANAGER_URL` (this module)
4. Strips the encrypted password field from read responses before returning to the frontend

The Python module never receives or stores plaintext passwords.

### security_core_module

When a ban is applied with `notify_security_core: true` (the default), the enforcement service POSTs to:

```
POST SECURITY_CORE_URL/api/v1/bans
{
  "community_id": 42,
  "player_identifier": "76561198012345678",
  "reason": "Cheating",
  "source": "server_manager"
}
```

This allows the security_core to apply the ban globally and notify other modules.

### reputation_module

The enforcement service queries reputation scores either:
- From a local cache table (if populated by the reputation_module via pub/sub)
- By calling the reputation_module API directly: `GET /api/v1/reputation/:communityId/score/:userId`

---

## Async/Await Pattern

All database and network operations are non-blocking:

```python
async def handle_command(community_id, server_id, command, user_id):
    # All awaited — never blocks the event loop
    config = await get_server_config(community_id, server_id)
    creds = await encryption_service.decrypt(config['encrypted_password'])
    response = await rcon_service.send_command(config, creds, command)
    log_id = await write_command_log(community_id, server_id, user_id, command, response)
    return {"success": True, "response": response, "log_id": log_id}
```

---

## Performance Characteristics

| Operation | Typical Latency | Notes |
|-----------|----------------|-------|
| RCON command (pooled) | 20–80 ms | Connection already established |
| RCON command (cold) | 200–800 ms | Includes connect + auth |
| Mumble channel list | 30–100 ms | Ice RPC round trip |
| TeamSpeak channel list | 50–150 ms | ServerQuery TCP |
| Enforcement pass (14 players) | 500–2000 ms | Depends on player count and game type |
| DB log write | 5–15 ms | Async, non-blocking |

---

**Architecture Version**: 1.0.0
**Last Updated**: 2026-02-24
