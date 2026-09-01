# Server Manager Interaction Module - Usage Guide

## Getting Started

This guide covers setup, health checks, and common workflows for the Server Manager Interaction Module.

## Prerequisites

- Python 3.12+
- PostgreSQL 13+ with migration `055_server_manager.sql` applied
- Docker (recommended for containerized deployment)
- Redis (optional, for credential notifications)
- AES-256-GCM encryption key (64-character hex string) — must match the hub backend's `RCON_ENCRYPTION_KEY`

## Local Development Setup

```bash
# Navigate to module directory
cd /home/penguin/code/waddlebot/action/interactive/server_manager_interaction_module/

# Install Python dependencies
pip install -r requirements.txt

# Install shared library
cd /home/penguin/code/waddlebot
pip install -e libs/flask_core

# Apply database migration
psql $DATABASE_URL -f config/postgres/migrations/055_server_manager.sql

# Set required environment variables
export DATABASE_URL="postgresql://waddlebot:password@localhost:5432/waddlebot"
export MODULE_PORT=8098
export RCON_ENCRYPTION_KEY="$(openssl rand -hex 32)"
export SECURITY_CORE_URL="http://localhost:8090"

# Start the module
cd action/interactive/server_manager_interaction_module
python app.py
```

## Docker Setup

### Build the Image

```bash
cd /home/penguin/code/waddlebot

docker build \
  -f action/interactive/server_manager_interaction_module/Dockerfile \
  -t waddlebot/server-manager-interaction:latest \
  .
```

### Run the Container

```bash
docker run -d \
  --name server-manager-interaction \
  -p 8098:8098 \
  -e DATABASE_URL="postgresql://waddlebot:password@db:5432/waddlebot" \
  -e MODULE_PORT=8098 \
  -e RCON_ENCRYPTION_KEY="your-64-char-hex-key-here" \
  -e RCON_CONNECTION_TTL=60 \
  -e SECURITY_CORE_URL="http://security-core:8090" \
  -e LOG_LEVEL=INFO \
  -v /var/log/waddlebotlog:/var/log/waddlebotlog \
  waddlebot/server-manager-interaction:latest
```

### Docker Compose Example

```yaml
version: '3.8'
services:
  server-manager-interaction:
    build:
      context: .
      dockerfile: action/interactive/server_manager_interaction_module/Dockerfile
    container_name: server-manager-interaction
    ports:
      - "8098:8098"
    environment:
      DATABASE_URL: postgresql://waddlebot:password@postgres:5432/waddlebot
      MODULE_PORT: 8098
      RCON_ENCRYPTION_KEY: ${RCON_ENCRYPTION_KEY}
      RCON_CONNECTION_TTL: 60
      SECURITY_CORE_URL: http://security-core:8090
      LOG_LEVEL: INFO
      REDIS_URL: redis://redis:6379/0
    volumes:
      - /var/log/waddlebotlog:/var/log/waddlebotlog
    depends_on:
      - postgres
      - redis
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8098/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

## Health Checks

### GET `/health`

```bash
curl http://localhost:8098/health
```

**Healthy Response:**
```json
{
  "status": "healthy",
  "module": "server_manager_interaction_module",
  "version": "1.0.0",
  "timestamp": "2026-02-24T10:00:00Z",
  "database": "connected",
  "uptime_seconds": 3600
}
```

### GET `/api/v1/status`

```bash
curl http://localhost:8098/api/v1/status
```

```json
{ "status": "operational", "module": "server_manager_interaction_module" }
```

---

## Common Workflows

### Workflow 1: Add a Game Server

Via the hub backend (recommended path for production):

```bash
curl -X POST https://hub.example.com/api/v1/42/rcon/servers \
  -H "Authorization: Bearer <jwt>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Rust Main",
    "server_type": "rcon",
    "game_type": "rust",
    "host": "rust.example.com",
    "port": 28015,
    "rcon_port": 28016,
    "password": "my_rcon_password"
  }'
```

The hub backend encrypts the password before passing it to the Python module. The plaintext password is never stored.

---

### Workflow 2: Test a Connection Before Saving

```bash
curl -X POST http://localhost:8098/api/v1/server-manager/42/connect-test \
  -H "Content-Type: application/json" \
  -d '{
    "server_type": "rcon",
    "game_type": "rust",
    "host": "rust.example.com",
    "port": 28016,
    "password": "my_rcon_password"
  }'
```

**Success response:**
```json
{ "success": true, "latency_ms": 28, "server_info": "Rust 2463 — 8/100 players" }
```

**Failure response:**
```json
{ "success": false, "error": "Authentication failed: wrong password" }
```

---

### Workflow 3: Execute an RCON Command

```bash
curl -X POST http://localhost:8098/api/v1/server-manager/42/command \
  -H "Content-Type: application/json" \
  -d '{
    "server_id": 7,
    "command": "playerlist",
    "executed_by_user_id": 1001
  }'
```

**Response:**
```json
{
  "success": true,
  "response": "Players online: CoolGamer99, AnotherPlayer ...",
  "log_id": 5503
}
```

Every command is written to `rcon_command_log` with the operator, command text, response, and timestamp.

---

### Workflow 4: Kick a Player

```bash
curl -X POST http://localhost:8098/api/v1/server-manager/42/servers/7/kick \
  -H "Content-Type: application/json" \
  -d '{
    "player_identifier": "76561198012345678",
    "reason": "Excessive profanity",
    "actor_user_id": 1001
  }'
```

---

### Workflow 5: Ban a Player and Sync Across All Servers

```bash
curl -X POST http://localhost:8098/api/v1/server-manager/42/servers/7/ban \
  -H "Content-Type: application/json" \
  -d '{
    "player_identifier": "76561198012345678",
    "reason": "Cheating",
    "actor_user_id": 1001,
    "sync_to_all_servers": true,
    "notify_security_core": true
  }'
```

**Response:**
```json
{
  "success": true,
  "log_id": 893,
  "synced_servers": [7, 9, 11]
}
```

---

### Workflow 6: Manage Mumble Channels

**List channels:**
```bash
curl http://localhost:8098/api/v1/server-manager/42/servers/12/channels
```

**Move a user:**
```bash
curl -X POST http://localhost:8098/api/v1/server-manager/42/servers/12/move \
  -H "Content-Type: application/json" \
  -d '{
    "user_identifier": "CoolGamer99",
    "target_channel_id": 3,
    "actor_user_id": 1001
  }'
```

**Broadcast a message:**
```bash
curl -X POST http://localhost:8098/api/v1/server-manager/42/servers/12/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Game night starts in 10 minutes — join the Gaming channel!",
    "actor_user_id": 1001
  }'
```

---

### Workflow 7: Set Up a Reputation-Based Access Policy

```bash
# Create or update the policy
curl -X PUT http://localhost:8098/api/v1/server-manager/42/servers/7/policy \
  -H "Content-Type: application/json" \
  -d '{
    "policy_type": "reputation_threshold",
    "reputation_kick_threshold": 420,
    "reputation_ban_threshold": 340
  }'
```

Once set, any player whose reputation score is below 420 will be auto-kicked on join. Players below 340 are auto-banned.

---

### Workflow 8: Trigger Manual Enforcement

Force an immediate scan of all connected players against the policy:

```bash
curl -X POST http://localhost:8098/api/v1/server-manager/42/servers/7/enforce \
  -H "Content-Type: application/json" \
  -d '{ "actor_user_id": 1001 }'
```

**Response:**
```json
{
  "success": true,
  "players_evaluated": 14,
  "players_kicked": 1,
  "players_banned": 0,
  "actions": [
    { "player": "ToxicUser123", "action": "kick", "reputation_score": 385 }
  ]
}
```

---

### Workflow 9: Review Access Log

```bash
curl "http://localhost:8098/api/v1/server-manager/42/servers/7/access-log?limit=20"
```

**Response:**
```json
{
  "server_id": 7,
  "total": 48,
  "entries": [
    {
      "id": 893,
      "actor_user_id": 1001,
      "target_player_identifier": "76561198012345678",
      "action": "ban",
      "reason": "Cheating",
      "auto_enforced": false,
      "reputation_score": null,
      "created_at": "2026-02-24T09:14:00Z"
    }
  ]
}
```

---

## Error Handling

All endpoints return structured error responses:

```json
{ "error": "Connection refused: host unreachable", "code": "CONNECT_FAILED" }
```

### Common Error Scenarios

| Error | Cause | Resolution |
|-------|-------|-----------|
| `CONNECT_FAILED` | Server host unreachable | Verify host/port; check firewall rules |
| `AUTH_FAILED` | Wrong RCON password | Re-check credentials; re-save with correct password |
| `SSRF_BLOCKED` | Host resolves to private IP | Only public IPs are permitted for RCON hosts |
| `ENCRYPT_KEY_MISMATCH` | Hub and module use different keys | Ensure `RCON_ENCRYPTION_KEY` is identical in both services |
| `SERVER_NOT_FOUND` | Invalid `server_id` for community | Verify server belongs to the community |
| `POLICY_NOT_FOUND` | No policy set for server | Create a policy first with `PUT .../policy` |

---

## Environment Variables Quick Reference

```bash
# Required
DATABASE_URL=postgresql://waddlebot:password@localhost:5432/waddlebot
MODULE_PORT=8098
RCON_ENCRYPTION_KEY=<64-char hex>   # Must match hub backend

# Recommended
SECURITY_CORE_URL=http://security-core:8090
RCON_CONNECTION_TTL=60              # Seconds; idle connections are dropped
LOG_LEVEL=INFO

# Optional
REDIS_URL=redis://localhost:6379/0
```

See [CONFIGURATION.md](CONFIGURATION.md) for the complete list with defaults.

---

## Best Practices

1. **Always test before saving**: Use `connect-test` before persisting server credentials
2. **Use the hub backend routes**: They handle JWT auth and credential encryption automatically
3. **Set reputation policies**: Even a permissive threshold (e.g., ban below 300) deters the worst actors
4. **Monitor access logs**: Review daily for unexpected auto-enforcement actions
5. **Rotate the encryption key carefully**: Existing encrypted passwords become unreadable after rotation — re-save all server credentials after a key rotation
6. **Separate RCON port**: Always use a dedicated RCON port, not the game port

---

## Next Steps

- Review [API.md](API.md) for complete endpoint documentation
- Check [ARCHITECTURE.md](ARCHITECTURE.md) for internal design
- See [CONFIGURATION.md](CONFIGURATION.md) for all environment variables
- Consult [TROUBLESHOOTING.md](TROUBLESHOOTING.md) if issues arise

---

**Module**: server_manager_interaction_module
**Port**: 8098
**Language**: Python 3.12
**Framework**: Quart
