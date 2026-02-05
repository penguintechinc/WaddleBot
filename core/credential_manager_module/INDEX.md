# Credential Manager Module - File Index

Complete guide to all files in the credential manager module.

## Quick Navigation

**New to the module?** Start here:
1. [QUICKSTART.md](QUICKSTART.md) - 5-minute setup (2 min read)
2. [README.md](README.md) - Overview and architecture (5 min read)
3. [API.md](API.md) - REST endpoints (3 min read)

**Deploying to production?**
1. [DEPLOYMENT.md](DEPLOYMENT.md) - Complete deployment guide

**Developing/Extending?**
1. [services/oauth_handlers.py](services/oauth_handlers.py) - Adding OAuth providers
2. [services/refresh_service.py](services/refresh_service.py) - Token refresh logic
3. [config.py](config.py) - Configuration system

---

## Core Application Files

### `__init__.py`
- **Purpose**: Module initialization and exports
- **Size**: 25 LOC
- **Key Exports**: RefreshService, Config
- **When to Read**: Understanding module structure

### `config.py`
- **Purpose**: Configuration management from environment variables
- **Size**: 140 LOC
- **Key Classes**: Config
- **Key Methods**: validate(), load_credentials_from_db(), start_credential_listener()
- **When to Read**: Understanding configuration options
- **When to Modify**: Adding new configuration parameters

### `app.py`
- **Purpose**: Quart REST API application
- **Size**: 100 LOC
- **Key Functions**: startup(), shutdown(), health(), credential_status(), force_refresh()
- **Endpoints**:
  - GET /health
  - GET /api/v1/credentials/status
  - POST /api/v1/credentials/refresh-now
- **When to Read**: Understanding REST API
- **When to Modify**: Adding new endpoints

### `requirements.txt`
- **Purpose**: Python package dependencies
- **Size**: 20 LOC
- **Key Packages**:
  - Web: quart, hypercorn
  - Database: asyncpg, psycopg
  - Cache: redis
  - HTTP: httpx
- **When to Read**: Understanding dependencies
- **When to Modify**: Adding new packages

### `Dockerfile`
- **Purpose**: Container image build
- **Size**: 28 LOC
- **Base Image**: python:3.13-slim-bookworm
- **Key Features**:
  - Health check
  - Port 8095 exposure
  - Shared libraries integration
- **When to Read**: Understanding container setup
- **When to Modify**: Changing base image or dependencies

---

## Service Layer

### `services/__init__.py`
- **Purpose**: Service module exports
- **Size**: 40 LOC
- **Key Exports**: RefreshService, all OAuth handlers, get_handler()
- **When to Read**: Understanding service architecture

### `services/oauth_handlers.py`
- **Purpose**: Platform-specific OAuth token refresh implementations
- **Size**: 310 LOC
- **Key Classes**:
  - BaseOAuthHandler (abstract)
  - TwitchOAuthHandler
  - DiscordOAuthHandler
  - SlackOAuthHandler
  - YouTubeOAuthHandler
  - SpotifyOAuthHandler
  - KickOAuthHandler
- **Key Functions**: get_handler(platform)
- **Key Exceptions**: OAuthRefreshError
- **When to Read**: Understanding OAuth implementations
- **When to Modify**: Adding new OAuth provider or fixing refresh logic

### `services/refresh_service.py`
- **Purpose**: Main token refresh polling and database updates
- **Size**: 350 LOC
- **Key Classes**: RefreshService
- **Key Methods**:
  - start() - Initialize service
  - stop() - Shutdown gracefully
  - run_refresh_cycle() - Poll and refresh credentials
  - get_status() - Service status
  - get_credential_stats() - Credential statistics
- **When to Read**: Understanding token refresh workflow
- **When to Modify**: Changing polling logic, retry behavior, or database queries

---

## Documentation

### `README.md`
- **Purpose**: Service overview and architecture
- **Size**: 280 LOC
- **Sections**:
  - Features and architecture
  - Configuration reference
  - Database schema
  - Token refresh flow
  - REST endpoints
  - Docker deployment
  - Error handling
  - Performance tuning
- **Audience**: Developers, DevOps, architects
- **Read Time**: 5 minutes

### `QUICKSTART.md`
- **Purpose**: Fast setup guide
- **Size**: 250 LOC
- **Sections**:
  - Local development setup
  - Docker quick start
  - Configuration quick reference
  - API quick reference
  - Troubleshooting
  - Performance tuning
- **Audience**: New developers, quick setup
- **Read Time**: 2 minutes

### `DEPLOYMENT.md`
- **Purpose**: Complete production deployment guide
- **Size**: 420 LOC
- **Sections**:
  - Prerequisites
  - Docker deployment
  - Docker Compose integration
  - Kubernetes deployment
  - Database setup
  - Environment configuration
  - Health checks
  - Performance tuning
  - Monitoring and logging
  - Troubleshooting
  - Security
  - Updates and upgrades
- **Audience**: DevOps, SRE, infrastructure teams
- **Read Time**: 10 minutes

### `API.md`
- **Purpose**: REST API reference
- **Size**: 380 LOC
- **Sections**:
  - Endpoint specifications
  - Request/response examples
  - Error codes
  - Authentication
  - Rate limiting
  - Redis pub/sub events
  - Usage examples
  - Monitoring guide
  - Security considerations
- **Audience**: API consumers, frontend developers
- **Read Time**: 5 minutes

### `INDEX.md` (this file)
- **Purpose**: Navigation guide
- **Size**: 250 LOC
- **Sections**: This file
- **Audience**: Anyone learning the codebase
- **Read Time**: 3 minutes

---

## Testing

### `test_credential_manager.py`
- **Purpose**: Unit and integration tests
- **Size**: 200 LOC
- **Test Classes**:
  - TestOAuthHandlers - Handler instantiation
  - TestConfiguration - Config management
  - TestErrorHandling - Error classes
  - TestDataStructures - Data validation
  - TestIntegration - Integration tests
- **Test Framework**: pytest
- **When to Run**: `pytest test_credential_manager.py -v`
- **When to Modify**: Adding new features or fixing bugs

---

## File Dependency Graph

```
app.py
├── config.py
├── services/refresh_service.py
│   ├── services/oauth_handlers.py
│   └── services/__init__.py

services/__init__.py
├── services/refresh_service.py
└── services/oauth_handlers.py

test_credential_manager.py
├── services/oauth_handlers.py
└── config.py
```

---

## Decision Tree: What to Read?

```
1. First time?
   → QUICKSTART.md (2 min)
   → README.md (5 min)

2. Need API info?
   → API.md (5 min)

3. Deploying to production?
   → DEPLOYMENT.md (10 min)

4. Adding new platform?
   → services/oauth_handlers.py
   → README.md (architecture section)
   → test_credential_manager.py (testing section)

5. Understanding token refresh?
   → README.md (token refresh flow)
   → services/refresh_service.py (code)

6. Troubleshooting?
   → README.md (error handling)
   → DEPLOYMENT.md (troubleshooting)
   → QUICKSTART.md (troubleshooting)

7. Modifying config?
   → config.py
   → DEPLOYMENT.md (environment variables)

8. Understanding security?
   → README.md (security section)
   → DEPLOYMENT.md (security section)
   → API.md (security section)
```

---

## File Sizes and Complexity

| File | Size | Complexity | Priority |
|------|------|-----------|----------|
| oauth_handlers.py | 310 LOC | Medium | High (platform support) |
| refresh_service.py | 350 LOC | Medium | High (core logic) |
| DEPLOYMENT.md | 420 LOC | Low | High (production) |
| API.md | 380 LOC | Low | Medium (API consumers) |
| README.md | 280 LOC | Low | Medium (overview) |
| config.py | 140 LOC | Low | Medium (configuration) |
| test_credential_manager.py | 200 LOC | Medium | Low (testing) |
| QUICKSTART.md | 250 LOC | Low | Low (setup) |
| app.py | 100 LOC | Low | Low (REST API) |
| Dockerfile | 28 LOC | Low | Low (container) |
| __init__.py | 25 LOC | Low | Low (module) |
| requirements.txt | 20 LOC | Low | Low (dependencies) |

---

## Reading Path by Role

### Backend Developer
1. QUICKSTART.md - Local setup
2. README.md - Architecture
3. services/oauth_handlers.py - OAuth implementations
4. services/refresh_service.py - Token refresh
5. test_credential_manager.py - Testing

### DevOps Engineer
1. README.md - Overview
2. DEPLOYMENT.md - Production setup
3. Dockerfile - Container build
4. QUICKSTART.md - Quick reference

### Frontend Developer
1. QUICKSTART.md - Quick setup
2. API.md - Endpoint specifications
3. README.md - Architecture section

### QA/Tester
1. QUICKSTART.md - Setup
2. API.md - Endpoints to test
3. test_credential_manager.py - Test examples
4. README.md - Error handling

### Architect/Tech Lead
1. README.md - Architecture and design
2. API.md - API contract
3. DEPLOYMENT.md - Production requirements
4. config.py - Configuration strategy

---

## Common Tasks and Which Files to Check

| Task | Files to Check |
|------|-----------------|
| Add new OAuth platform | oauth_handlers.py, test_credential_manager.py |
| Change refresh interval | config.py, DEPLOYMENT.md |
| Fix token refresh bug | refresh_service.py, test_credential_manager.py |
| Add new API endpoint | app.py, API.md |
| Deploy to production | DEPLOYMENT.md, Dockerfile |
| Understand health check | app.py, API.md, README.md |
| Configure logging | config.py, DEPLOYMENT.md |
| Performance tuning | README.md, DEPLOYMENT.md |
| Implement monitoring | API.md, DEPLOYMENT.md |
| Add authentication | app.py, API.md, DEPLOYMENT.md |

---

## Version Information

- **Module Version**: 1.0.0
- **Python Version**: 3.13+
- **Framework**: Quart (async/await)
- **Database**: PostgreSQL 13+
- **Cache**: Redis 6.0+
- **Last Updated**: 2025-02-05

---

## Support and Links

- **Main Waddlebot Docs**: ../../docs/
- **Architecture**: ../../docs/ARCHITECTURE.md
- **Database Schema**: ../../docs/architecture/database-schema.md
- **Security Policy**: ../../docs/SECURITY.md
- **API Reference**: ../../docs/reference/api-reference.md

---

## Quick Commands

```bash
# View directory structure
tree core/credential_manager_module/

# Run tests
pytest core/credential_manager_module/test_credential_manager.py -v

# Check code syntax
python3 -m py_compile core/credential_manager_module/*.py

# Build Docker image
docker build -f core/credential_manager_module/Dockerfile -t credential-manager .

# View file line counts
wc -l core/credential_manager_module/*.py core/credential_manager_module/*.md
```

---

**Navigation Helper**: Use this file to understand the module structure and navigate to the right file for your task.
