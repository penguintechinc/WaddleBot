# Module RTC — Overview

**Module RTC** is a scalable, stateless real-time communication module built with Go and powered by LiveKit WebRTC server. It manages video/audio call rooms for Waddlebot communities with advanced features like participant role management, hand raising queues, moderator controls, and room locking.

## Purpose

Module RTC provides a complete WebRTC signaling and room management layer that:

- Creates and manages LiveKit-based video call rooms for communities
- Handles participant authentication and role-based permissions (host, moderator, speaker, viewer)
- Manages raised hand queues with FIFO ordering and acknowledgment
- Provides moderator controls (mute, kick, lock room) for call management
- Scales to 1000+ concurrent participants per call with stateless architecture
- Integrates with PostgreSQL for persistence and Redis for distributed state

## Capabilities

| Capability | Details |
|-----------|---------|
| **Room Management** | Create, list, delete, lock/unlock rooms with max participant limits |
| **Participant Control** | Role-based access, mute/unmute, kick, permission grants |
| **Hand Raising** | FIFO queue system, acknowledgment by moderators, automatic cleanup on leave |
| **Room Security** | Room locking, permission-based joins, role validation |
| **Scalability** | Stateless HTTP servers, Redis-backed distributed state, LiveKit SFU |
| **Media Handling** | WebRTC audio/video streaming, screen sharing capability |
| **Monitoring** | Health checks, participant tracking, room state visibility |

## Technical Stack

- **Language**: Go 1.24+
- **WebRTC**: LiveKit Server SDK (github.com/livekit/server-sdk-go)
- **HTTP Router**: Gorilla Mux
- **Database**: PostgreSQL (via environment config)
- **Cache/State**: Redis
- **Ports**: REST API 8093, gRPC 50067

## Key Components

### Room Service
Manages room lifecycle and participant access:
- Room creation with max participant limits
- Token generation for LiveKit authentication
- Participant listing and muting
- Room info and deletion

### Call Features Service
Implements call-specific functionality:
- Hand raising queue management (FIFO)
- Moderator acknowledgment of raised hands
- Mute/unmute controls (individual and all)
- Room locking/unlocking
- Participant kick with cleanup

### API Handlers
REST API layer exposing all functionality:
- POST/GET/DELETE room operations
- Participant join/leave and controls
- Raised hand queue operations
- Moderator action endpoints

## Documentation Index

| Document | Purpose |
|----------|---------|
| [OVERVIEW.md](OVERVIEW.md) | Module purpose, capabilities, architecture overview |
| [USAGE.md](USAGE.md) | Getting started, Docker setup, health checks, client connection flows |
| [API.md](API.md) | Complete REST endpoint reference, request/response schemas, error codes |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design, peer connection lifecycle, ICE/STUN/TURN, data flows |
| [CONFIGURATION.md](CONFIGURATION.md) | Environment variables, required/optional settings, example .env |
| [TESTING.md](TESTING.md) | Test scenarios, peer connection simulation, signaling test flows |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Common issues, NAT traversal, ICE debugging, connection diagnostics |
| [RELEASE_NOTES.md](RELEASE_NOTES.md) | Version history and changes |

## Quick Reference

### Starting the Module

```bash
# With Docker
docker run -p 8093:8093 -p 50067:50067 \
  -e LIVEKIT_HOST=livekit.example.com:7880 \
  -e LIVEKIT_API_KEY=your-key \
  -e LIVEKIT_API_SECRET=your-secret \
  waddlebot/module-rtc:latest

# Or from source
go run ./cmd/server/main.go
```

### Health Check

```bash
curl http://localhost:8093/health
# Response: {"status":"healthy","module":"module_rtc","version":"1.0.0",...}
```

### Creating a Room

```bash
curl -X POST http://localhost:8093/api/v1/rooms \
  -H "Content-Type: application/json" \
  -d '{
    "community_id": 1,
    "room_name": "general-call",
    "max_participants": 100
  }'
```

### Joining a Room

```bash
curl -X POST http://localhost:8093/api/v1/rooms/general-call/join \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "user_name": "John Doe",
    "role": "host"
  }'
# Response includes LiveKit access token
```

## Participant Roles

| Role | Permissions | Use Case |
|------|-------------|----------|
| **host** | Full control, promote/demote, create rooms | Call organizer, community owner |
| **moderator** | Mute, kick, acknowledge hands | Community moderators |
| **speaker** | Unmute self, share screen, publish media | Presenting participants |
| **viewer** | Listen/watch only, raise hand | General audience |

## Database Schema

Three main tables (created during deployment):

- **community_call_rooms**: Room metadata with LiveKit room IDs
- **community_call_participants**: Participant tracking with roles and state
- **call_raised_hands**: Hand raising queue entries

## Scaling Architecture

Module RTC scales horizontally through:

1. **Stateless HTTP Servers**: Multiple container replicas behind load balancer
2. **Redis Coordination**: Distributed hand raising queues and room state
3. **LiveKit SFU**: Handles media routing and peer connections at scale
4. **PostgreSQL**: Persistent storage for community/participant data

Target capacity: **1000+ concurrent users per call** across multiple communities.

## Integration Points

- **LiveKit Server**: External SFU for WebRTC media handling
- **PostgreSQL**: Participant and room persistence
- **Redis**: Distributed state (hands queue, room locks)
- **Hub API**: Event notifications and community metadata

## Source Location

```
/home/penguin/code/waddlebot/core/module_rtc/
├── cmd/server/main.go              # Application entry point
├── internal/api/handlers.go         # REST endpoint handlers
├── internal/services/               # Business logic
│   ├── room_service.go              # Room lifecycle management
│   └── call_features.go             # Call features (hands, mute, lock)
├── internal/config/config.go        # Configuration loading
├── go.mod                           # Go module definition
└── Dockerfile                       # Container image
```

## Version

- **Current Version**: 1.0.0
- **Module Name**: module_rtc
- **Language**: Go
- **License**: Limited AGPL-3.0 with Penguin Tech exceptions

## Support

For issues, questions, or contributions:
- Documentation: See related guides in `/docs/module_rtc/`
- Source: `/home/penguin/code/waddlebot/core/module_rtc/`
- Company: Penguin Tech Inc
