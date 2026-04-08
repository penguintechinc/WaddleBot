# Core Community Service

Combined Quart microservice merging 4 modules into a single unified application on port 8020.

## Modules Merged

1. **community_module** (port 8020) - Community management
   - Endpoints: `/api/v1/community/*`
   - Lightweight core functionality

2. **workflow_core_module** - Workflow automation with gRPC
   - Endpoints: `/api/v1/workflow/*`
   - Includes WorkflowService, WorkflowEngine, PermissionService, LicenseService
   - Optional gRPC support for service-to-service communication

3. **browser_source_core_module** - OBS browser source integration
   - Endpoints: `/api/v1/browser-source/*`
   - Overlay routes: `/overlay/*`
   - WebSocket: `/ws/captions/<community_id>`
   - OverlayService for caption streaming and OBS integration

4. **video_proxy_module** - Video stream proxying
   - Endpoints: `/api/v1/stream/*`
   - Stream configuration, destination management, status tracking

## Note: Module RTC

The `module_rtc` (real-time communication) module was not found in the repository and was not included in this merge. If it needs to be added later, additional endpoints can be integrated following the same pattern.

## Architecture

- **Single Quart app** - All modules registered on port 8020
- **Shared database** - One PyDAL instance (`dal`) shared across all modules
- **Unified startup/shutdown** - Coordinated initialization and cleanup
- **Service namespacing** - URL prefixes keep endpoints organized:
  - `/api/v1/community/*` - community endpoints
  - `/api/v1/workflow/*` - workflow endpoints
  - `/api/v1/browser-source/*` - browser source endpoints
  - `/api/v1/stream/*` - video proxy endpoints
  - `/overlay/*` - overlay serving
  - `/ws/*` - websocket endpoints

## Dependencies

Combined from all 4 modules:
- Quart >= 0.19.5, Hypercorn >= 0.17.3
- gRPC, PyDAL, Redis, APScheduler
- JWT/cryptography for auth
- See `requirements.txt` for full list

## Running

```bash
# Development
python3 app.py

# Production (with Hypercorn)
hypercorn app:app --bind 0.0.0.0:8020 --workers 4

# Docker
docker build -t core-community:latest .
docker run -p 8020:8020 \
  -e DATABASE_URL="postgresql://user:pass@db:5432/waddlebot" \
  -e MODULE_PORT=8020 \
  core-community:latest
```

## Health Check

```bash
curl http://localhost:8020/healthz
curl http://localhost:8020/api/v1/status
```

## Integration Notes

1. **Database tables**: All 4 modules' tables are expected in the shared database
2. **Configuration**: Single `Config` class handles all modules
3. **Logging**: Unified logging via `flask_core.setup_aaa_logging()`
4. **Optional services**: Services that fail to initialize log warnings but don't block startup (e.g., LicenseService, WorkflowService)

## Future: Module RTC

When module_rtc is available, add:
- RTC-specific endpoints under `/api/v1/rtc/*`
- WebRTC signaling, peer connection management
- Integration with other modules' websocket infrastructure
