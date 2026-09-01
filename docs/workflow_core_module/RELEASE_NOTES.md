# Workflow Core Module - Release Notes

## Version 1.0.0

**Release Date:** 2025-12-16
**Status:** Production Ready

---

## Overview

The Workflow Core Module v1.0.0 is a production-ready workflow automation engine for Waddles, providing visual workflow creation, advanced control flow, and seamless integration with external systems.

---

## Features

### Workflow Management

✓ **Visual Workflow Builder**
- Drag-and-drop node-based workflow editor
- Real-time validation and error checking
- Version control and workflow templates
- Import/export workflow definitions

✓ **Comprehensive Node Types**
- Trigger Nodes: Commands, Events, Webhooks, Schedules
- Condition Nodes: If/Else, Switch, Filters
- Action Nodes: Modules, Webhooks, Chat Messages, Browser Sources
- Data Nodes: Transformations, Variables
- Loop Nodes: ForEach, While, Break
- Flow Nodes: Merge, Parallel, End

✓ **Advanced Control Flow**
- Conditional branching (if/else, switch/case)
- Loop execution with safety limits
- Parallel execution support
- Dynamic routing based on data

### Execution Engine

✓ **DAG-Based Execution**
- Directed Acyclic Graph construction
- Topological sort for correct execution order
- Cycle detection and prevention
- Dependency resolution

✓ **Parallel Execution**
- ThreadPoolExecutor for concurrent nodes
- Configurable parallelism limits
- Proper synchronization and state management

✓ **Error Handling & Retry**
- Exponential backoff retry logic
- Per-node error handling
- Workflow-level timeout management
- Comprehensive error logging

✓ **State Management**
- Incremental state persistence
- Crash recovery support
- Execution history tracking
- Real-time status queries

### Security & Permissions

✓ **Authentication & Authorization**
- JWT token validation
- Role-Based Access Control (RBAC)
- Permission levels: view, edit, delete, execute
- Community-level isolation

✓ **Webhook Security**
- HMAC-SHA256 signature verification
- IP allowlist support (CIDR notation)
- Per-webhook rate limiting
- Secure token generation

✓ **Code Sandboxing**
- RestrictedPython for data transformations
- Expression engine with restricted globals
- No file system or network access in sandbox
- Safe builtin functions only

### API Capabilities

✓ **REST API**
- Workflow CRUD operations
- Execution triggering and monitoring
- Webhook management
- Schedule management
- Health and status endpoints

✓ **gRPC API**
- High-performance workflow execution
- Streaming execution status
- Service-to-service integration

### Scheduling

✓ **Cron-Based Scheduling**
- Standard cron expression support
- Timezone-aware execution
- APScheduler integration
- Missed run handling (coalesce)
- Schedule management API

### Integration

✓ **Router Module Integration**
- Execute module actions
- Command execution
- Seamless service communication

✓ **License Service Integration**
- Feature-based license validation
- Usage limit enforcement
- Community-level licensing

✓ **External Webhooks**
- HTTP requests to external APIs
- Configurable headers and authentication
- Timeout and retry configuration
- Response data extraction

---

## Technical Specifications

### Technology Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| **Runtime** | Python | 3.13 |
| **Framework** | Quart (async Flask) | 0.20.0+ |
| **Server** | Hypercorn | 0.16.0 |
| **Database** | PostgreSQL + PyDAL | 15+ |
| **Cache** | Redis | 7+ |
| **Scheduler** | APScheduler | 3.10.4 |
| **gRPC** | grpcio | 1.67.0+ |
| **Sandboxing** | RestrictedPython | 8.0+ |

### Performance Characteristics

| Metric | Value | Notes |
|--------|-------|-------|
| **Max Concurrent Workflows** | 10 (configurable) | Default limit |
| **Max Parallel Nodes** | 10 (configurable) | Per workflow |
| **Max Loop Iterations** | 100 (configurable) | Per loop |
| **Max Total Operations** | 1000 (configurable) | Per workflow |
| **Max Loop Depth** | 10 (configurable) | Nested loops |
| **Default Timeout** | 300 seconds | Per workflow |
| **Webhook Rate Limit** | 60/min (configurable) | Per webhook |

### Execution Limits

Safety limits to prevent runaway workflows:

```bash
MAX_CONCURRENT_WORKFLOWS=10
MAX_PARALLEL_NODES=10
WORKFLOW_TIMEOUT_SECONDS=300
MAX_LOOP_ITERATIONS=100
MAX_TOTAL_OPERATIONS=1000
MAX_LOOP_DEPTH=10
```

---

## Database Schema

### Tables

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `workflows` | Workflow definitions | workflow_id, name, nodes, connections |
| `workflow_executions` | Execution history | execution_id, workflow_id, status, node_states |
| `workflow_webhooks` | Webhook configurations | webhook_id, workflow_id, token, secret |
| `workflow_permissions` | Access control | workflow_id, user_id, can_view, can_edit, can_execute |
| `workflow_schedules` | Scheduled executions | schedule_id, workflow_id, cron_expression |

### Indexes

Optimized indexes for common queries:
- Workflows by entity_id, community_id, status
- Executions by workflow_id, status, start_time
- Permissions by user_id, workflow_id
- Schedules by next_run_at (for active schedules)

---

## API Endpoints

### Workflow Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/workflows` | POST | Create workflow |
| `/api/v1/workflows` | GET | List workflows |
| `/api/v1/workflows/:id` | GET | Get workflow |
| `/api/v1/workflows/:id` | PUT | Update workflow |
| `/api/v1/workflows/:id` | DELETE | Archive workflow |
| `/api/v1/workflows/:id/publish` | POST | Publish workflow |
| `/api/v1/workflows/:id/validate` | POST | Validate workflow |

### Execution

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/workflows/:id/execute` | POST | Execute workflow |
| `/api/v1/workflows/:id/test` | POST | Test workflow (dry-run) |
| `/api/v1/workflows/executions/:execId` | GET | Get execution details |
| `/api/v1/workflows/executions/:execId/cancel` | POST | Cancel execution |
| `/api/v1/workflows/:id/executions` | GET | List executions |

### Webhooks

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/workflows/webhooks/:token` | POST | Trigger webhook (public) |
| `/api/v1/workflows/:id/webhooks` | GET | List webhooks |
| `/api/v1/workflows/:id/webhooks` | POST | Create webhook |
| `/api/v1/workflows/:id/webhooks/:webhookId` | DELETE | Delete webhook |

### Health & Status

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/v1/status` | GET | Module status |

---

## Configuration

### Environment Variables

Key configuration options:

```bash
# Module Ports
MODULE_PORT=8070
GRPC_PORT=50070

# Database
DATABASE_URI=postgresql://waddlebot:password@localhost:5432/waddlebot
READ_REPLICA_URIS=postgresql://...

# Redis
REDIS_URL=redis://localhost:6379/0

# Services
ROUTER_URL=http://router-service:8000
LICENSE_SERVER_URL=https://license.penguintech.io

# Security
SECRET_KEY=change-me-in-production
API_KEY=change-me-in-production

# Feature Flags
RELEASE_MODE=false
FEATURE_WORKFLOWS_ENABLED=true

# Execution Limits
MAX_CONCURRENT_WORKFLOWS=10
WORKFLOW_TIMEOUT_SECONDS=300
MAX_LOOP_ITERATIONS=100
MAX_TOTAL_OPERATIONS=1000
MAX_LOOP_DEPTH=10
MAX_PARALLEL_NODES=10

# Scheduler
SCHEDULER_TIMEZONE=UTC
SCHEDULER_JOB_DEFAULTS_MAX_INSTANCES=3
```

---

## Breaking Changes

### From Pre-Release Versions

N/A - This is the initial production release.

### Migration Guide

For users migrating from development/beta versions:

1. **Database Migration**
   ```bash
   # Backup existing data
   pg_dump waddlebot > backup.sql

   # Run migration scripts
   python scripts/migrate_to_v1.py
   ```

2. **Configuration Updates**
   - Rename `WORKFLOW_PORT` → `MODULE_PORT`
   - Add `GRPC_PORT` (default: 50070)
   - Update `SECRET_KEY` and `API_KEY` (required)

3. **API Changes**
   - Execution endpoint now returns `202 Accepted` instead of `200 OK`
   - Webhook trigger moved to `/api/v1/workflows/webhooks/:token`
   - Permission system now uses explicit `can_view`, `can_edit`, `can_execute`

---

## Known Issues

### Issue #1: Large Workflow Performance

**Description:** Workflows with >100 nodes may experience slower validation times.

**Workaround:** Break large workflows into smaller sub-workflows.

**Status:** Optimization planned for v1.1.0

### Issue #2: Webhook Signature Verification with Binary Data

**Description:** HMAC signature verification may fail with binary webhook payloads.

**Workaround:** Use JSON payloads only.

**Status:** Fix planned for v1.0.1

### Issue #3: Nested Loop Execution Context

**Description:** Variables in nested loops (depth > 5) may not resolve correctly.

**Workaround:** Limit loop nesting to 5 levels or use intermediate variables.

**Status:** Under investigation

---

## Deprecations

None in this release.

---

## Security Advisories

### SA-2025-001: Webhook Token Exposure

**Severity:** Low
**Description:** Webhook tokens are included in API responses when listing webhooks.
**Mitigation:** Tokens are public by design; use signature verification for security.
**Status:** Not applicable (working as intended)

### SA-2025-002: Expression Engine Sandbox Escape

**Severity:** Critical (Resolved)
**Description:** Potential sandbox escape via `__import__` in expression engine.
**Mitigation:** RestrictedPython updated to v8.0 with hardened globals.
**Status:** Resolved in v1.0.0

---

## Dependencies

### Python Dependencies

```
quart>=0.20.0
hypercorn==0.16.0
grpcio>=1.67.0
grpcio-tools>=1.67.0
aiohttp>=3.12.14,<4.0.0
pydal>=20240906.1,<20250101
RestrictedPython>=8.0
croniter==2.0.1
APScheduler==3.10.4
redis==5.0.1
python-jose[cryptography]>=3.4.0
cryptography==43.0.3
python-dotenv>=1.0.0
pytest>=7.4.0
pytest-asyncio>=0.23.0
pytest-cov>=4.1.0
```

### System Dependencies

- PostgreSQL 15+
- Redis 7+
- Python 3.13+

---

## Upgrade Instructions

### From Development Version

1. **Stop the service**
   ```bash
   docker-compose down core-workflow
   ```

2. **Backup database**
   ```bash
   pg_dump waddlebot > backup_$(date +%Y%m%d).sql
   ```

3. **Update code**
   ```bash
   git pull origin main
   ```

4. **Run migrations**
   ```bash
   python scripts/migrate.py
   ```

5. **Update configuration**
   ```bash
   # Review and update .env file
   cp .env.example .env
   # Edit .env with your settings
   ```

6. **Rebuild and start**
   ```bash
   docker-compose build core-workflow
   docker-compose up -d workflow-core
   ```

7. **Verify health**
   ```bash
   curl http://localhost:8070/health
   ```

---

## Testing

### Test Coverage

- **Overall Coverage:** 87%
- **Service Layer:** 88%
- **Models:** 95%
- **Controllers:** 75%

### Test Commands

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest services/test_node_executor.py
```

---

## Documentation

### Available Documentation

1. **API.md** - Complete API reference with examples
2. **CONFIGURATION.md** - Configuration guide and environment variables
3. **ARCHITECTURE.md** - System architecture and design
4. **USAGE.md** - User guide and tutorials
5. **TESTING.md** - Testing procedures and test documentation
6. **TROUBLESHOOTING.md** - Common issues and solutions

### Online Resources

- GitHub Repository: https://github.com/your-org/waddlebot
- Issue Tracker: https://github.com/your-org/waddlebot/issues
- Documentation: https://docs.waddlebot.io/workflow-core

---

## Contributors

- Waddles Development Team
- Community Contributors

---

## License

Copyright © 2025 Waddles Team. All rights reserved.

---

## Roadmap

### Planned for v1.1.0

- [ ] WebUI workflow builder enhancements
- [ ] Workflow templates marketplace
- [ ] Advanced debugging tools (breakpoints, step-through)
- [ ] Workflow versioning and rollback
- [ ] Sub-workflow support (call workflows from workflows)
- [ ] Improved error messages and validation feedback

### Planned for v1.2.0

- [ ] GraphQL API support
- [ ] Workflow analytics and metrics dashboard
- [ ] A/B testing workflows
- [ ] Workflow collaboration (multi-user editing)
- [ ] Import from third-party workflow engines

### Future Considerations

- Machine learning node types
- Natural language workflow creation
- Mobile workflow builder app
- Workflow marketplace integration
- Advanced analytics and insights

---

## Changelog

### [1.0.0] - 2025-12-16

#### Added
- Initial production release
- Complete workflow management API
- Workflow execution engine with DAG support
- 18 node types across 6 categories
- gRPC API for high-performance integration
- Webhook support with HMAC signature verification
- Cron-based scheduling with APScheduler
- Permission system with RBAC
- License service integration
- RestrictedPython sandbox for transformations
- Comprehensive AAA logging
- Health check and monitoring endpoints
- Docker support with multi-stage builds
- Complete documentation suite

#### Fixed
- Expression engine sandbox escape vulnerability (SA-2025-002)
- Database connection pool exhaustion under high load
- Race condition in parallel node execution
- Memory leak in long-running scheduled workflows

#### Changed
- Migrated from Flask to Quart for async support
- Updated to Python 3.13
- Improved error messages in validation service
- Optimized DAG construction algorithm

---

## Support

For support, please:
1. Check the troubleshooting guide (TROUBLESHOOTING.md)
2. Search existing issues on GitHub
3. Create a new issue with detailed information
4. Contact the development team

---

## Acknowledgments

Special thanks to:
- The Waddles community for testing and feedback
- Contributors who helped shape the workflow engine design
- Open source projects we depend on (Quart, APScheduler, RestrictedPython)
