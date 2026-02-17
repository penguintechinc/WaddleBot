# Hub Module

> Central web portal and API gateway providing administration, community management, real-time communication, and unified access to all Waddles microservices through an integrated web interface.

## Purpose

The Hub Module is the primary administrative portal and unified interface for Waddles. It provides a full-stack application with a Node.js/Express backend and React-based frontend SPA that enables administrators and community managers to configure, monitor, and manage communities, users, and integrated modules. The module acts as an API gateway, proxying requests to downstream Waddles microservices while providing its own management capabilities.

The Hub Module handles authentication across multiple platforms (OAuth2 with Twitch, Discord, YouTube, etc.), session management, user administration, community configuration, module discovery and management, real-time updates via WebSockets, analytics, and broadcast capabilities. It serves both public-facing pages (community directory, statistics) and admin dashboards with role-based access control.

The module is central to the Waddles architecture, sitting at the intersection of user authentication (via Identity Core Module), community management (via Community Module), and all downstream feature modules, coordinating their configuration and providing a unified management experience.

## Key Capabilities

- Multi-platform OAuth2 authentication (Twitch, Discord, YouTube, and more)
- Community creation and management interface
- User and role management with granular permissions
- Module discovery, registration, and configuration
- Real-time updates and notifications via WebSocket
- Broadcast and announcement system
- Analytics and statistics dashboard
- Kong API Gateway integration and management
- Admin panel for super-admins and community moderators
- Public community directory and search
- Chat system with real-time messaging
- Ticketing and calendar integration
- Leaderboard and loyalty program configuration

## Documentation Index

| Document | Description |
|---|---|
| [USAGE.md](USAGE.md) | Getting started, accessing dashboards, common workflows |
| [API.md](API.md) | Backend REST endpoints, WebSocket events, formats |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Frontend/backend design, data flows, components |
| [CONFIGURATION.md](CONFIGURATION.md) | Environment variables, OAuth setup, service discovery |
| [TESTING.md](TESTING.md) | Test strategy, API testing, WebUI testing |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Common issues, debug steps, FAQ |
| [RELEASE_NOTES.md](RELEASE_NOTES.md) | Version history, breaking changes, migrations |

## Quick Reference

| Item | Value |
|---|---|
| Source | `admin/hub_module/` |
| Backend Language | Node.js 20+ (Express) |
| Frontend Language | JavaScript/React 18 |
| Backend Port | 8060 |
| Real-time | WebSocket (Socket.io) |
| Database | PostgreSQL |
| Maintained by | Penguin Tech Inc |
