# Engagement Module — Overview

## Purpose

The Engagement Module is a Python/Quart-based microservice that manages community engagement through polls and forms. It provides granular visibility controls, flexible field types, and comprehensive vote/submission tracking for WaddleBot communities.

**Developer**: Penguin Tech Inc
**Language**: Python 3.13 with Quart async framework
**REST API Port**: 8091 (configurable via `MODULE_PORT`)
**Health Check**: `GET /health`

---

## Key Capabilities

### Polls
- Single-choice and multi-choice polls
- Configurable poll expiration times
- Vote counting and result aggregation
- Prevents duplicate votes per user
- Real-time vote results

### Forms
- Flexible form field types (text, textarea, email, number, select, radio, checkbox, date)
- Field-level validation configuration
- Anonymous submission support
- One submission per user enforcement
- Bulk submission retrieval for administrators

### Visibility Control
Four-tier visibility model applies to both polls and forms:
- **Public**: Accessible to anyone
- **Registered**: Requires login only
- **Community**: Requires community membership
- **Admins**: Administrators only

Each poll/form supports separate `view_visibility` and `submit_visibility` settings for granular access control.

---

## Quick Reference

| Component | Details |
|-----------|---------|
| **Framework** | Quart (async Python web framework) |
| **Database** | PostgreSQL with PyDAL ORM |
| **Authentication** | JWT-based token validation |
| **Port (REST)** | 8091 |
| **Port (gRPC)** | 50061 |
| **Docker Image** | waddlebot/engagement:latest |
| **Configuration File** | `.env` (see CONFIGURATION.md) |
| **Version** | 1.0.0 |

---

## Documentation Index

| Document | Purpose |
|----------|---------|
| [USAGE.md](USAGE.md) | Getting started, Docker deployment, health checks, event tracking, metrics retrieval |
| [API.md](API.md) | Complete endpoint reference, request/response schemas, error codes |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design, event types, scoring logic, module integration patterns |
| [CONFIGURATION.md](CONFIGURATION.md) | Environment variables, required settings, .env examples |
| [TESTING.md](TESTING.md) | Test fixtures, mock data generation, running test suites |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Common issues, debug procedures, performance optimization |
| [RELEASE_NOTES.md](RELEASE_NOTES.md) | Version history and release information |

---

## Core Components

### REST API (Quart)
Asynchronous REST endpoints for poll/form CRUD, voting, submissions, and metrics.

### Database Layer (PyDAL)
Database abstraction with automatic migrations, connection pooling, and transaction management.

### Authentication (JWT)
Token-based authentication for protected endpoints using `Authorization: Bearer <token>` header.

### Visibility Engine
Access control enforcement based on user roles, community membership, and four-tier visibility settings.

---

## Deployment Context

The module is stateless and clusterable, designed to run in Kubernetes or Docker Compose environments. All state is maintained in PostgreSQL, allowing multiple instances to serve requests concurrently.

**Default Deployment**:
```bash
docker run -p 8091:8091 \
  -e MODULE_PORT=8091 \
  -e DATABASE_URL=postgres://... \
  -e JWT_SECRET=... \
  waddlebot/engagement:latest
```

---

## Next Steps

1. **To Deploy**: See [USAGE.md](USAGE.md) for Docker and Kubernetes instructions
2. **To Integrate**: See [API.md](API.md) for endpoint documentation
3. **To Configure**: See [CONFIGURATION.md](CONFIGURATION.md) for environment setup
4. **To Troubleshoot**: See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues

---

## Support

For issues or questions:
- **Documentation**: See related docs in this directory
- **Code Issues**: Check GitHub repository
- **Support**: support@penguintech.io

**Company**: Penguin Tech Inc
**License**: Limited AGPL-3.0
**Last Updated**: 2026-02-16
