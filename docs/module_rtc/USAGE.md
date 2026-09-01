# Module RTC — Usage Guide

This guide covers getting started with Module RTC, including local setup, Docker deployment, connecting clients, and common workflows.

## Prerequisites

- Go 1.24+ (for building from source)
- Docker & Docker Compose (for containerized deployment)
- LiveKit server (separate deployment)
- PostgreSQL 13+ (for persistence)
- Redis 6+ (for distributed state)

## Building from Source

Clone and build the module:

```bash
cd /home/penguin/code/waddlebot/core/module_rtc

# Install dependencies
go mod download
go mod verify

# Build binary
go build -o module-rtc ./cmd/server/main.go

# Run server
./module-rtc
```

Output:
```
2026-02-16T10:23:45Z Starting module_rtc v1.0.0
2026-02-16T10:23:45Z HTTP server starting on port 8093
```

## Docker Deployment

### Build Container Image

```bash
cd /home/penguin/code/waddlebot/core/module_rtc

# Build with docker-compose
docker build -t waddlebot/module-rtc:latest .

# Tag for registry
docker tag waddlebot/module-rtc:latest \
  registry.example.com/waddlebot/module-rtc:latest
```

### Run with Docker

```bash
# Development setup
docker run -d \
  --name module-rtc \
  -p 8093:8093 \
  -p 50067:50067 \
  -e MODULE_PORT=8093 \
  -e GRPC_PORT=50067 \
  -e LIVEKIT_HOST=livekit.example.com:7880 \
  -e LIVEKIT_API_KEY=devkey123 \
  -e LIVEKIT_API_SECRET=devsecret456 \
  -e DATABASE_URL="postgres://waddlebot:password@postgres:5432/waddlebot" \
  -e LOG_LEVEL=DEBUG \
  waddlebot/module-rtc:latest

# Check logs
docker logs -f module-rtc
```

### Run with Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  module-rtc:
    image: waddlebot/module-rtc:latest
    ports:
      - "8093:8093"
      - "50067:50067"
    environment:
      MODULE_PORT: 8093
      GRPC_PORT: 50067
      LIVEKIT_HOST: livekit:7880
      LIVEKIT_API_KEY: ${LIVEKIT_API_KEY}
      LIVEKIT_API_SECRET: ${LIVEKIT_API_SECRET}
      DATABASE_URL: postgres://waddlebot:password@postgres:5432/waddlebot
      LOG_LEVEL: INFO
    depends_on:
      - postgres
      - redis
      - livekit
    networks:
      - waddlebot

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: waddlebot
      POSTGRES_PASSWORD: password
      POSTGRES_DB: waddlebot
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - waddlebot

  redis:
    image: redis:7-alpine
    networks:
      - waddlebot

  livekit:
    image: livekit/livekit-server:latest
    command: --dev --ip=0.0.0.0
    ports:
      - "7880:7880"
      - "7881:7881"
      - "7882:7882/udp"
    networks:
      - waddlebot

volumes:
  postgres_data:

networks:
  waddlebot:
    driver: bridge
```

Start all services:

```bash
# Create .env file with LiveKit credentials
echo "LIVEKIT_API_KEY=devkey123" > .env
echo "LIVEKIT_API_SECRET=devsecret456" >> .env

# Start stack
docker-compose up -d

# Check health
docker-compose logs -f core-module-rtc
```

## Health Check

Module RTC exposes a health check endpoint for load balancers and monitoring:

```bash
curl http://localhost:8093/health

# Response:
# {
#   "status": "healthy",
#   "module": "module_rtc",
#   "version": "1.0.0",
#   "timestamp": "2026-02-16T10:25:30Z"
# }
```

### Health Check in Docker Compose

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8093/health"]
  interval: 10s
  timeout: 3s
  retries: 3
  start_period: 5s
```

## Connecting Clients

### Step 1: Create a Room

Before users can join, create a room:

```bash
curl -X POST http://localhost:8093/api/v1/rooms \
  -H "Content-Type: application/json" \
  -d '{
    "community_id": 1,
    "room_name": "weekly-meeting",
    "max_participants": 100
  }'

# Response:
# {
#   "room_id": "rm_abc123def456",
#   "room_name": "community_1_weekly-meeting",
#   "community_id": 1,
#   "participants": 0,
#   "created_at": "2026-02-16T10:26:00Z",
#   "is_locked": false
# }
```

### Step 2: User Joins Room

User requests access token:

```bash
curl -X POST http://localhost:8093/api/v1/rooms/community_1_weekly-meeting/join \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_alice_123",
    "user_name": "Alice Smith",
    "role": "host"
  }'

# Response:
# {
#   "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
#   "room_name": "community_1_weekly-meeting",
#   "identity": "user_alice_123"
# }
```

### Step 3: Client Connects to LiveKit

Client uses the token to connect to LiveKit:

```javascript
// JavaScript/Browser example
import { Room, RoomEvent, Participant } from 'livekit-client';

const room = new Room();

// Connect with token from step 2
await room.connect('wss://livekit.example.com', token);

// Listen for participant events
room.on(RoomEvent.ParticipantConnected, (participant) => {
  console.log(`${participant.name} joined`);
});

// Subscribe to audio/video tracks
const videoTrack = await navigator.mediaDevices.getUserMedia({
  video: true,
  audio: true
});

// Publish tracks
await room.localParticipant.publishTrack(videoTrack);
```

### Step 4: User Raises Hand

```bash
curl -X POST http://localhost:8093/api/v1/rooms/community_1_weekly-meeting/raise-hand \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_alice_123",
    "user_name": "Alice Smith"
  }'

# Response: {"success": true}
```

### Step 5: Moderator Views Raised Hands

```bash
curl http://localhost:8093/api/v1/rooms/community_1_weekly-meeting/raised-hands

# Response:
# {
#   "raised_hands": [
#     {
#       "user_id": "user_alice_123",
#       "user_name": "Alice Smith",
#       "raised_at": "2026-02-16T10:27:00Z",
#       "acknowledged_at": null,
#       "acknowledged_by": ""
#     }
#   ],
#   "count": 1
# }
```

### Step 6: Moderator Acknowledges Hand

```bash
curl -X POST \
  http://localhost:8093/api/v1/rooms/community_1_weekly-meeting/acknowledge-hand/user_alice_123 \
  -H "Content-Type: application/json" \
  -d '{
    "moderator_id": "user_bob_456"
  }'

# Response: {"success": true}
```

### Step 7: User Leaves Room

```bash
curl -X POST http://localhost:8093/api/v1/rooms/community_1_weekly-meeting/leave \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_alice_123"
  }'

# Response: {"success": true}
```

## Common Workflows

### Moderating a Call

```bash
# Get all participants
curl http://localhost:8093/api/v1/rooms/community_1_weekly-meeting/participants

# Mute a specific user
curl -X POST \
  http://localhost:8093/api/v1/rooms/community_1_weekly-meeting/mute/user_alice_123 \
  -H "Content-Type: application/json" \
  -d '{"moderator_id": "user_bob_456"}'

# Mute everyone except yourself
curl -X POST \
  http://localhost:8093/api/v1/rooms/community_1_weekly-meeting/mute-all \
  -H "Content-Type: application/json" \
  -d '{"moderator_id": "user_bob_456"}'

# Kick a disruptive participant
curl -X POST \
  http://localhost:8093/api/v1/rooms/community_1_weekly-meeting/kick/user_charlie_789 \
  -H "Content-Type: application/json" \
  -d '{"admin_id": "user_bob_456"}'
```

### Securing a Call

```bash
# Lock room to prevent new participants
curl -X POST \
  http://localhost:8093/api/v1/rooms/community_1_weekly-meeting/lock \
  -H "Content-Type: application/json" \
  -d '{"admin_id": "user_bob_456"}'

# Unlock when ready for more participants
curl -X POST \
  http://localhost:8093/api/v1/rooms/community_1_weekly-meeting/unlock \
  -H "Content-Type: application/json" \
  -d '{"admin_id": "user_bob_456"}'
```

### Cleaning Up

```bash
# Delete a room (removes all participants)
curl -X DELETE \
  http://localhost:8093/api/v1/rooms/community_1_weekly-meeting
```

## Debugging

### Enable Debug Logging

```bash
# Start with debug logs
docker run -e LOG_LEVEL=DEBUG waddlebot/module-rtc:latest

# In local development
export LOG_LEVEL=DEBUG
go run ./cmd/server/main.go
```

### Check Container Logs

```bash
docker logs module-rtc

# Follow logs in real-time
docker logs -f module-rtc

# Last 100 lines
docker logs --tail 100 module-rtc
```

### Test Connectivity

```bash
# Check if module is running
curl -v http://localhost:8093/health

# Test database connectivity (via module logs)
docker logs module-rtc | grep -i "database"

# Test LiveKit connectivity
docker logs module-rtc | grep -i "livekit"
```

## Performance Considerations

- **Max Participants**: Configured per room (default 100)
- **Concurrent Rooms**: Limited by database and Redis capacity
- **Concurrent Users**: Target 1000+ with stateless scaling
- **Hand Raising**: In-memory with Redis backup for distributed state
- **Token TTL**: 24 hours (configurable in room_service.go)

## Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for:
- Connection failures
- Hand raising issues
- Moderator control failures
- Database connectivity problems
- LiveKit integration issues

## Next Steps

- Review [API.md](API.md) for complete endpoint reference
- Study [ARCHITECTURE.md](ARCHITECTURE.md) for system design
- Configure for production in [CONFIGURATION.md](CONFIGURATION.md)
- Run tests in [TESTING.md](TESTING.md)
