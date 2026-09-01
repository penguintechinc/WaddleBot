# YouTube Music Interaction Module - Overview

## Purpose

The **YouTube Music Interaction Module** (`youtube_music_interaction_module`) is an interactive service that enables WaddleBot to integrate with YouTube Music, providing capabilities for music discovery, playback management, and user library interactions within Discord communities.

The module serves as a bridge between WaddleBot's core platform and YouTube Music's API, handling OAuth 2.0 authentication, credential management, and asynchronous music-related operations.

## Core Capabilities

- **OAuth 2.0 Authentication**: Secure user authentication with YouTube Music via OAuth flow
- **Credential Management**: Store and refresh YouTube Music API credentials with database backing
- **Health Monitoring**: Real-time health checks and Prometheus metrics integration
- **Async/Await Support**: Full async/await support via Quart framework
- **Database Integration**: PostgreSQL integration via PyDAL for credential persistence
- **Redis Support**: Optional Redis integration for credential refresh notifications
- **Comprehensive Logging**: AAA-compliant structured logging for audit trails

## Technical Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| **Framework** | Quart | 0.19.0+ |
| **Server** | Hypercorn | 0.16.0+ |
| **HTTP Client** | httpx | 0.27.0 |
| **Database** | PostgreSQL | 12+ (via PyDAL) |
| **Cache/Messaging** | Redis | 6.0+ (optional) |
| **Python** | Python | 3.12 |

## Module Information

| Property | Value |
|----------|-------|
| **Module Name** | `youtube_music_interaction_module` |
| **Current Version** | `2.0.0` |
| **REST Port** | `8025` |
| **gRPC Port** | `50054` |
| **Docker Image Base** | `python:3.12-slim` |
| **Non-Root User** | `waddlebot:waddlebot` |
| **Health Check Path** | `/health`, `/healthz` |
| **Metrics Path** | `/metrics` (Prometheus) |

## Quick Reference

### Starting the Module

**Docker Compose:**
```bash
docker-compose up interactive-youtube-music
```

**Standalone (after `pip install -r requirements.txt`):**
```bash
hypercorn app:app --bind 0.0.0.0:8025 --workers 4
```

### Health Verification

```bash
curl http://localhost:8025/health
curl http://localhost:8025/healthz
```

### API Base URL

```
http://localhost:8025/api/v1
```

## Documentation Index

This documentation suite contains comprehensive guides for all aspects of the YouTube Music Interaction Module:

| Document | Purpose | Audience |
|----------|---------|----------|
| **[OVERVIEW.md](OVERVIEW.md)** | Module purpose, capabilities, tech stack | Everyone |
| **[USAGE.md](USAGE.md)** | Getting started, Docker setup, common workflows | Developers, DevOps |
| **[API.md](API.md)** | Complete endpoint reference, requests/responses | API Consumers, Developers |
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | OAuth flow, component design, data flow | Developers, Architects |
| **[CONFIGURATION.md](CONFIGURATION.md)** | Environment variables, .env setup | DevOps, System Admins |
| **[TESTING.md](TESTING.md)** | Running tests, mocking OAuth, test data | QA, Developers |
| **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** | Common issues, debugging, error solutions | Support, DevOps |
| **[RELEASE_NOTES.md](RELEASE_NOTES.md)** | Version history, changes, upgrades | Everyone |

## Key Files

```
action/interactive/youtube_music_interaction_module/
├── app.py                 # Main Quart application and endpoints
├── config.py             # Configuration management, credential loading
├── requirements.txt      # Python dependencies
├── Dockerfile            # Container image definition
├── test-api.sh          # API integration tests
└── services/
    └── __init__.py       # Service module package
```

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Discord Community                         │
└─────────────┬───────────────────────────────────────────────┘
              │
┌─────────────▼───────────────────────────────────────────────┐
│              WaddleBot Core / Router Service                 │
└─────────────┬───────────────────────────────────────────────┘
              │
              ├──────────────────────────────────────────────┐
              │                                              │
┌─────────────▼────────────────────────┐      ┌─────────────▼─────┐
│ YouTube Music Interaction Module      │      │  Other Modules    │
│ (Port: 8025 REST, 50054 gRPC)         │      │  (twitch, lambda, │
│                                       │      │   etc.)           │
│ ┌─────────────────────────────────┐  │      └───────────────────┘
│ │ Quart Application               │  │
│ │ ├─ /health (healthcheck)        │  │
│ │ ├─ /healthz (k8s probe)         │  │
│ │ ├─ /metrics (Prometheus)        │  │
│ │ └─ /api/v1/* (REST endpoints)   │  │
│ └─────────────────────────────────┘  │
│                                       │
│ ┌──────────────────────────────────┐ │
│ │ Configuration Manager             │ │
│ │ ├─ Credential Loading             │ │
│ │ ├─ Redis Listener (optional)      │ │
│ │ └─ Environment Variables          │ │
│ └──────────────────────────────────┘ │
│                                       │
│ ┌──────────────────────────────────┐ │
│ │ OAuth 2.0 Handler                │ │
│ │ ├─ Token Exchange                 │ │
│ │ ├─ Token Refresh                  │ │
│ │ └─ Scope Management               │ │
│ └──────────────────────────────────┘ │
│                                       │
│ ┌──────────────────────────────────┐ │
│ │ Database Layer (PyDAL)            │ │
│ │ └─ Credential Persistence         │ │
│ └──────────────────────────────────┘ │
└─────────────┬────────────────────────┘
              │
      ┌───────┴────────┬──────────────┐
      │                │              │
┌─────▼──────┐  ┌──────▼──────┐  ┌───▼────────┐
│ PostgreSQL │  │   Redis     │  │  YouTube   │
│ (required) │  │  (optional) │  │   Music    │
│            │  │             │  │   API      │
└────────────┘  └─────────────┘  └────────────┘
```

## Default Configuration

The module uses sensible defaults that can be overridden via environment variables:

- **Module Port**: `8025` (configurable via `MODULE_PORT`)
- **Database**: PostgreSQL at `postgresql://waddlebot:password@localhost:5432/waddlebot`
- **Core API URL**: `http://router-service:8000` (within K8s)
- **Log Level**: `INFO`
- **Workers**: 4 (Hypercorn)

## Security Considerations

- **Non-Root Execution**: Runs as `waddlebot:waddlebot` user (UID isolation)
- **Credential Storage**: Encrypted in PostgreSQL `platform_integrations` table
- **Redis Integration**: Optional Redis channel-based credential refresh notifications
- **AAA Logging**: All actions logged via AAA framework for audit compliance
- **Token Refresh**: Automatic token refresh with background listener support

## Related Resources

- **Router Service**: Handles request routing between modules
- **Flask Core Library**: Shared utilities for health checks, logging, database initialization
- **Platform Integrations Table**: Stores OAuth tokens and credentials
- **Redis Credentials Channel**: `credentials:youtube:bot:refreshed` (optional)

## Getting Help

For detailed guides and troubleshooting:

1. See **[USAGE.md](USAGE.md)** for setup and workflow questions
2. See **[CONFIGURATION.md](CONFIGURATION.md)** for environment variable questions
3. See **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** for error solutions
4. See **[API.md](API.md)** for endpoint reference

---

**Module Version**: 2.0.0  
**Last Updated**: 2026-02-16  
**Maintained by**: Penguin Tech Inc  
**Status**: Production Ready
