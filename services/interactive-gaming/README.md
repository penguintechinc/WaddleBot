# Interactive Gaming Service

Combined microservice that merges 4 gaming interaction modules into a single Quart application on port 8104.

## Modules Included

1. **LFG (Looking for Group) Module** (port 8104 → `/api/v1/lfg`)
   - Player matchmaking and party formation
   - Group availability and interest matching
   - LFG request management and filtering

2. **Inventory Module** (port 8104 → `/api/v1/inventory`)
   - Player item management and storage
   - Inventory state tracking
   - Item usage and distribution

3. **Server Manager Module** (port 8104 → `/api/v1/server-manager`, `/api/v1/server-status`)
   - RCON (Remote Console) command execution
   - Server enforcement and policy management
   - Server parameter configuration
   - gRPC service on port 50051

4. **Server Status Module** (port 8104 → `/api/v1/server-status`)
   - Real-time server health monitoring
   - Player count and performance metrics
   - Server availability and uptime tracking

## Architecture

```
/app/
  app.py                        # Combined Quart entry point
  config.py                     # Unified configuration
  requirements.txt              # Merged dependencies
  Dockerfile                    # Multi-stage build
  lfg_interaction_module/       # LFG service code
  inventory_interaction_module/ # Inventory service code
  server_manager_interaction_module/  # Server manager service code
  server_status_interaction_module/   # Server status service code
  libs/                         # Shared Flask/Quart utilities
```

## API Endpoints

### Health & Status
- `GET /healthz` - Liveness probe
- `GET /health` - Health with timestamp
- `GET /api/v1/status` - Unified service status

### LFG (Looking for Group)
- `POST /api/v1/lfg/groups` - Create LFG group
- `GET /api/v1/lfg/groups` - List available groups
- `GET /api/v1/lfg/groups/<group_id>` - Get group details
- `POST /api/v1/lfg/groups/<group_id>/join` - Join a group
- `DELETE /api/v1/lfg/groups/<group_id>/leave` - Leave a group
- `POST /api/v1/lfg/match` - Find matching groups
- `GET /api/v1/lfg/availability` - Get player availability

### Inventory
- `POST /api/v1/inventory` - Create inventory
- `GET /api/v1/inventory/<user_id>` - Get user inventory
- `POST /api/v1/inventory/<user_id>/items` - Add item to inventory
- `DELETE /api/v1/inventory/<user_id>/items/<item_id>` - Remove item from inventory
- `PUT /api/v1/inventory/<user_id>/items/<item_id>` - Update item quantity
- `GET /api/v1/inventory/status` - Inventory service status

### Server Manager (RCON & Enforcement)
- `POST /api/v1/server-manager/command` - Execute RCON command
- `POST /api/v1/server-manager/ban` - Ban player from server
- `POST /api/v1/server-manager/kick` - Kick player from server
- `PUT /api/v1/server-manager/config` - Update server configuration
- `GET /api/v1/server-manager/config` - Get current server config
- `POST /api/v1/server-manager/enforce` - Apply enforcement rules

### Server Status (Health & Monitoring)
- `GET /api/v1/server-status/<server_id>` - Get server status
- `GET /api/v1/server-status/<server_id>/metrics` - Get server metrics
- `GET /api/v1/server-status/<server_id>/players` - Get active players
- `GET /api/v1/server-status` - List all server statuses
- `POST /api/v1/internal/events` - Receive status events

## Environment Variables

```bash
# Service
MODULE_NAME=interactive-gaming
MODULE_VERSION=0.0.1
MODULE_PORT=8104
MODULE_HOST=0.0.0.0

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/waddlebot
DB_POOL_SIZE=10

# Security
SERVICE_API_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret
JWT_ALGORITHM=HS256

# RCON (Server Manager)
RCON_HOST=server.example.com
RCON_PORT=27015
RCON_PASSWORD=rcon-password
RCON_TIMEOUT=10
RCON_RETRIES=3

# gRPC (Server Manager)
GRPC_PORT=50051

# Logging
LOG_LEVEL=INFO

# Server Status Polling
SERVER_STATUS_POLLING_INTERVAL=30
SERVER_HEALTH_CHECK_TIMEOUT=5
```

## Building

### Local Build
```bash
docker build -t interactive-gaming:latest .
```

### Run Locally
```bash
docker run -d \
  -p 8104:8104 \
  -p 50051:50051 \
  -e DATABASE_URL=postgresql://user:pass@localhost:5432/waddlebot \
  -e SERVICE_API_KEY=secret-key \
  -e JWT_SECRET_KEY=jwt-secret \
  -e RCON_HOST=server.example.com \
  -e RCON_PASSWORD=rcon-password \
  interactive-gaming:latest
```

## Ports

- **8104** - HTTP REST API (all 4 modules)
- **50051** - gRPC service (Server Manager module only)

## Service Key Authentication

All non-health endpoints require the `X-Service-Key` header:

```bash
curl -H "X-Service-Key: your-secret-key" http://localhost:8104/api/v1/status
```

Health endpoints are exempt:
```bash
curl http://localhost:8104/healthz
curl http://localhost:8104/health
```

## Database Schema

The service initializes database tables for all 4 modules:

- LFG: groups, players, party_members, availability
- Inventory: inventories, items, item_instances
- Server Manager: servers, bans, kicks, config, enforcement_rules
- Server Status: server_metrics, player_status, health_events

All use PyDAL with `migrate=False` (schema via Alembic only).

## Logging

Uses `flask_core.setup_aaa_logging()` with structured JSON logging:
- All startup/shutdown events logged
- Service key violations logged
- RCON command execution logged (with security masking)
- Per-module initialization status tracked
