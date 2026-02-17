# Module RTC — Troubleshooting Guide

Comprehensive troubleshooting guide for common issues, diagnostics, and resolution steps.

## Common Issues

### 1. Module Fails to Start

**Symptoms**:
- Container exits immediately
- Error: `FATAL: Module startup failed`

**Root Causes**:
- Port already in use
- Configuration missing
- Database connectivity

**Diagnosis**:

```bash
# Check container logs
docker logs module-rtc | tail -50

# Check if ports are in use
lsof -i :8093  # REST API port
lsof -i :50067 # gRPC port

# Test configuration
docker run --rm \
  -e LIVEKIT_HOST=livekit:7880 \
  -e LIVEKIT_API_KEY=test \
  -e LIVEKIT_API_SECRET=test \
  waddlebot/module-rtc:latest
```

**Solutions**:

```bash
# Release port if in use
lsof -i :8093 | grep LISTEN | awk '{print $2}' | xargs kill -9

# Use different port
docker run -p 8094:8093 \
  -e MODULE_PORT=8093 \
  waddlebot/module-rtc:latest

# Check environment variables
docker inspect module-rtc | grep Env | head -20
```

---

### 2. Health Check Failing

**Symptoms**:
- `curl http://localhost:8093/health` returns connection refused
- Kubernetes pods keep restarting

**Root Causes**:
- Module not listening on correct port
- Network connectivity issue
- Module crashed after startup

**Diagnosis**:

```bash
# Check container is running
docker ps | grep module-rtc

# Check listening ports inside container
docker exec module-rtc netstat -tlnp

# Check detailed logs
docker logs module-rtc --tail 100

# Test from inside container
docker exec module-rtc curl -v http://localhost:8093/health
```

**Solutions**:

```bash
# Verify port configuration
docker inspect -f '{{json .Config.ExposedPorts}}' module-rtc

# Increase health check timeout (Kubernetes)
kubectl patch deployment module-rtc -p '
{
  "spec": {
    "template": {
      "spec": {
        "containers": [{
          "name": "module-rtc",
          "livenessProbe": {
            "httpGet": {
              "path": "/health",
              "port": 8093
            },
            "initialDelaySeconds": 30,
            "periodSeconds": 10
          }
        }]
      }
    }
  }
}'

# Restart container
docker restart module-rtc
```

---

### 3. Cannot Connect to LiveKit

**Symptoms**:
```
ERROR: failed to create room: connection refused
ERROR: LiveKit server unreachable
```

**Root Causes**:
- LiveKit server not running
- Incorrect LiveKit host/port
- Network connectivity between containers
- Firewall blocking connection

**Diagnosis**:

```bash
# Check LiveKit container running
docker ps | grep livekit

# Verify LiveKit host:port
echo $LIVEKIT_HOST

# Test connectivity from module-rtc container
docker exec module-rtc \
  curl -v http://livekit:7880/twirp/livekit.RoomService/ListRooms

# Check DNS resolution in container
docker exec module-rtc nslookup livekit

# Check network connectivity
docker exec module-rtc ping livekit -c 3
```

**Solutions**:

```bash
# Start LiveKit if missing
docker run -d \
  --name livekit \
  --network waddlebot \
  livekit/livekit-server:latest \
  --dev --ip=0.0.0.0

# Verify network is shared
docker network ls
docker network inspect waddlebot

# Check LIVEKIT_HOST environment variable
docker exec module-rtc env | grep LIVEKIT_HOST

# Update host if incorrect
docker run -e LIVEKIT_HOST=livekit.example.com:7880 \
  waddlebot/module-rtc:latest

# Test with curl
curl -v http://livekit.example.com:7880/health
```

---

### 4. Room Creation Fails

**Symptoms**:
```bash
curl -X POST http://localhost:8093/api/v1/rooms \
  -d '{"community_id":1,"room_name":"test"}'
# Returns: {"error": "Failed to create room"}
```

**Root Causes**:
- LiveKit API credentials invalid
- LiveKit server unreachable
- Database permission issue
- Invalid request parameters

**Diagnosis**:

```bash
# Check logs for specific error
docker logs module-rtc | grep -i "create room"

# Verify LiveKit credentials
echo "API Key: $LIVEKIT_API_KEY"
echo "API Secret: $LIVEKIT_API_SECRET"

# Test LiveKit API directly
curl -X POST http://livekit:7880/twirp/livekit.RoomService/CreateRoom \
  -H "Authorization: Bearer <jwt-token>" \
  -d '{"name":"test-room"}'

# Test with verbose logging
docker run -e LOG_LEVEL=DEBUG \
  -e LIVEKIT_HOST=livekit:7880 \
  -e LIVEKIT_API_KEY=test \
  -e LIVEKIT_API_SECRET=test \
  waddlebot/module-rtc:latest
```

**Solutions**:

```bash
# Verify credentials format
# LiveKit API key and secret should be base64 encoded
echo -n "apikey:apisecret" | base64

# Regenerate credentials if needed (in LiveKit admin)
# Then set in environment
export LIVEKIT_API_KEY=new_key
export LIVEKIT_API_SECRET=new_secret

# Test room creation with detailed response
curl -v -X POST http://localhost:8093/api/v1/rooms \
  -H "Content-Type: application/json" \
  -d '{
    "community_id": 1,
    "room_name": "debug-room",
    "max_participants": 50
  }' 2>&1 | tee /tmp/create_room.log

# Check if it's a database issue
docker logs postgres | tail -20
```

---

### 5. Join Room Returns No Token

**Symptoms**:
```bash
curl -X POST http://localhost:8093/api/v1/rooms/test-room/join \
  -d '{"user_id":"user1","user_name":"Test"}'
# Returns: {"error": "Failed to join room"}
```

**Root Causes**:
- Room doesn't exist
- Invalid user parameters
- Token generation error
- LiveKit API unreachable

**Diagnosis**:

```bash
# Check room exists
curl http://localhost:8093/api/v1/rooms/test-room

# Verify request parameters
curl -v -X POST http://localhost:8093/api/v1/rooms/test-room/join \
  -H "Content-Type: application/json" \
  -d '{"user_id":"user1","user_name":"Test","role":"viewer"}' \
  2>&1

# Check error logs
docker logs module-rtc | grep -i "join room"
```

**Solutions**:

```bash
# Create room first if missing
curl -X POST http://localhost:8093/api/v1/rooms \
  -H "Content-Type: application/json" \
  -d '{"community_id":1,"room_name":"test-room"}'

# Ensure user_id and user_name are provided
curl -X POST http://localhost:8093/api/v1/rooms/community_1_test-room/join \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_unique_123",
    "user_name": "User Name",
    "role": "viewer"
  }'

# Test with valid role
# Valid roles: host, moderator, speaker, viewer
curl -X POST http://localhost:8093/api/v1/rooms/community_1_test-room/join \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "user_name": "Test User",
    "role": "host"
  }' | jq '.token'
```

---

### 6. Raised Hand Not Appearing

**Symptoms**:
```bash
curl -X POST http://localhost:8093/api/v1/rooms/test-room/raise-hand \
  -d '{"user_id":"user1","user_name":"Test"}'
# Returns success, but hand doesn't appear in queue

curl http://localhost:8093/api/v1/rooms/test-room/raised-hands
# Returns empty list
```

**Root Causes**:
- User not in room
- Room name mismatch
- State not persisted across instances
- In-memory state cleared

**Diagnosis**:

```bash
# Check user is in room
curl http://localhost:8093/api/v1/rooms/test-room/participants \
  | jq '.participants[] | select(.identity=="user1")'

# Verify room exists
curl http://localhost:8093/api/v1/rooms/test-room

# Check if instance has the hand (in-memory)
docker logs module-rtc | grep "user1" | grep -i "hand"

# Test on same instance (stateless design issue)
# If using multiple instances, state not synced to Redis yet
```

**Solutions**:

```bash
# Ensure user is in room first
curl -X POST http://localhost:8093/api/v1/rooms/test-room/join \
  -H "Content-Type: application/json" \
  -d '{"user_id":"user1","user_name":"Test","role":"viewer"}'

# Use exact room name (includes community_id)
# Check room name from GET /rooms
curl http://localhost:8093/api/v1/rooms/community_1_test-room/raise-hand \
  -H "Content-Type: application/json" \
  -d '{"user_id":"user1","user_name":"Test"}'

# For multi-instance, ensure sticky sessions or Redis
# Or make requests to same instance
docker exec module-rtc curl \
  http://localhost:8093/api/v1/rooms/test-room/raised-hands | jq '.raised_hands'

# Check if state was cleared
docker restart module-rtc
# This clears in-memory state - raised hands lost (future: persist to Redis)
```

---

### 7. Room Lock Not Working

**Symptoms**:
- Room can be joined even after lock
- Lock endpoint returns success but doesn't prevent joins

**Root Causes**:
- Lock state is in-memory (lost on restart)
- Check on join not working
- Multiple instances not synced

**Diagnosis**:

```bash
# Check room locked status
docker exec module-rtc curl \
  http://localhost:8093/api/v1/rooms/test-room/locked

# Try to join locked room
curl -X POST http://localhost:8093/api/v1/rooms/test-room/join \
  -H "Content-Type: application/json" \
  -d '{"user_id":"user2","user_name":"Test2"}'

# Check logs
docker logs module-rtc | grep -i "lock"
```

**Solutions**:

```bash
# Lock room
curl -X POST http://localhost:8093/api/v1/rooms/test-room/lock \
  -H "Content-Type: application/json" \
  -d '{"admin_id":"admin1"}'

# Verify lock (should fail with 403)
curl -X POST http://localhost:8093/api/v1/rooms/test-room/join \
  -H "Content-Type: application/json" \
  -d '{"user_id":"user2","user_name":"Test2"}'
# Expected: 403 Forbidden, "Room is locked"

# If still allowing joins:
# 1. Check if requests going to different instance
# 2. Implement sticky sessions in load balancer
# 3. Move lock state to Redis (future feature)
```

---

### 8. Mute/Unmute Not Working

**Symptoms**:
- Participant still publishing audio after mute
- Mute endpoint returns success but no effect

**Root Causes**:
- LiveKit API failure
- Permissions not propagating to client
- WebRTC connection not yet established

**Diagnosis**:

```bash
# Check participant state before mute
curl http://localhost:8093/api/v1/rooms/test-room/participants \
  | jq '.participants[] | {identity, is_muted}'

# Try muting
curl -X POST http://localhost:8093/api/v1/rooms/test-room/mute/user1 \
  -H "Content-Type: application/json" \
  -d '{"moderator_id":"admin1"}'

# Check state after mute
curl http://localhost:8093/api/v1/rooms/test-room/participants \
  | jq '.participants[] | {identity, is_muted}'

# Check LiveKit logs
docker logs livekit | grep -i "user1"
```

**Solutions**:

```bash
# Ensure participant is in room
curl http://localhost:8093/api/v1/rooms/test-room/participants \
  | jq '.participants[].identity'

# Use correct user identity
# Identity is the 'user_id' from join request
curl -X POST http://localhost:8093/api/v1/rooms/test-room/mute/user_id_exact \
  -H "Content-Type: application/json" \
  -d '{"moderator_id":"admin1"}'

# Check LiveKit is running and accessible
curl http://livekit:7880/health

# For WebRTC clients: mute is an option, not a requirement
# Client can unmute locally if not respecting permissions
# This is expected WebRTC behavior (use TURN for enforcement)
```

---

## NAT Traversal & ICE Debugging

### ICE Candidate Issues

**Symptoms**:
- Users can see each other but no audio/video
- Connection established but media not flowing
- Users on same network can connect, but remote users cannot

**Root Causes**:
- STUN server not accessible
- TURN server not configured
- Firewall blocking UDP ports
- NAT not traversable

**Diagnosis**:

```bash
# Check LiveKit STUN/TURN configuration
docker exec livekit cat /etc/livekit.yaml | grep -A 10 "ice:"

# Test STUN server accessibility
# From client browser console:
const pc = new RTCPeerConnection();
pc.onicecandidate = (event) => console.log(event.candidate);

# Monitor WebRTC stats
// In browser
pc.getStats().then(stats => {
  stats.forEach(report => {
    if (report.type === 'inbound-rtp') {
      console.log('ICE State:', report.iceState);
      console.log('Bytes Received:', report.bytesReceived);
    }
  });
});
```

**Solutions**:

```bash
# Configure STUN server in LiveKit
# In livekit.yaml
ice:
  stun_servers:
    - stun:stun.l.google.com:19302
    - stun:stun1.l.google.com:19302

# Add TURN server (required for restrictive firewalls)
# In livekit.yaml
  turn_servers:
    - urls:
        - turn:turn.example.com?transport=udp
        - turn:turn.example.com?transport=tcp
      username: turnuser
      credential: turnpass

# Firewall: Allow UDP port range (WebRTC media)
iptables -A INPUT -p udp --dport 49152:65535 -j ACCEPT

# For Docker: Expose UDP ports
docker run -p 49152-65535:49152-65535/udp \
  livekit/livekit-server:latest
```

---

### Connection Drops

**Symptoms**:
- Participants disconnect randomly
- Connection quality degrades over time
- Reconnect required frequently

**Root Causes**:
- Network timeout configuration
- Load balancer connection reset
- LiveKit SFU overload
- Client-side issues

**Diagnosis**:

```bash
# Check LiveKit logs for timeout
docker logs livekit | grep -i "timeout"

# Monitor connection duration
# From browser:
room.on(RoomEvent.Disconnected, () => {
  console.log('Disconnected, uptime:', Date.now() - connectionTime);
});

# Check network quality
# From browser:
room.on(RoomEvent.MediaDevicesError, (error) => {
  console.log('Network error:', error);
});

# Check module-rtc load
docker stats module-rtc
```

**Solutions**:

```bash
# Increase keepalive timeout in LiveKit
# In livekit.yaml
room:
  timeout: 600  # 10 minutes

# Configure WebSocket timeout
# In browser client config
const room = new Room({
  reconnectPolicy: {
    initialWaitTime: 100,
    maxWaitTime: 30000,
    maxRetries: 5
  }
});

# Reduce module-rtc load if overloaded
# Scale up: add more instances
kubectl scale deployment module-rtc --replicas=5

# Check logs for errors
docker logs module-rtc | grep -i "error" | tail -20
```

---

## Database Issues

### Connection Pool Exhaustion

**Symptoms**:
```
ERROR: connection pool exhausted
ERROR: too many connections
```

**Diagnosis**:

```bash
# Check PostgreSQL active connections
docker exec postgres psql -U waddlebot -d waddlebot -c \
  "SELECT count(*) FROM pg_stat_activity;"

# Check connection limits
docker exec postgres psql -U waddlebot -d waddlebot -c \
  "SHOW max_connections;"
```

**Solutions**:

```bash
# Increase PostgreSQL max_connections
docker run -e POSTGRES_INIT_ARGS="-c max_connections=200" \
  postgres:15-alpine

# Implement connection pooling
# Use PgBouncer or similar
docker run -d \
  --name pgbouncer \
  pgbouncer/pgbouncer
```

---

### Migration Failures

**Symptoms**:
```
ERROR: migration failed
ERROR: table already exists
```

**Diagnosis**:

```bash
# Check applied migrations
docker exec postgres psql -U waddlebot -d waddlebot -c \
  "SELECT * FROM schema_migrations;"

# Check table structure
docker exec postgres psql -U waddlebot -d waddlebot -c \
  "\\d community_call_rooms;"
```

**Solutions**:

```bash
# Reapply migrations
docker-compose down -v  # Remove volume
docker-compose up

# Or manually apply from migration files
docker exec postgres psql -U waddlebot -d waddlebot < \
  config/postgres/migrations/001_initial.sql
```

---

## Performance Issues

### High CPU Usage

**Symptoms**:
- Module-rtc using 100% CPU
- Response times slow
- System becomes unresponsive

**Diagnosis**:

```bash
# Check CPU usage
docker stats module-rtc

# Profile CPU
go tool pprof http://localhost:6060/debug/pprof/profile

# Check for goroutine leaks
curl http://localhost:6060/debug/pprof/goroutine

# Monitor locks
curl http://localhost:6060/debug/pprof/mutex
```

**Solutions**:

```bash
# Reduce logging level (DEBUG is expensive)
export LOG_LEVEL=WARN

# Scale horizontally
# Disable debug features in production:
# - Remove verbose logging
# - Optimize database queries

# Check for infinite loops in logs
docker logs module-rtc | grep -v "INFO" | head -20
```

---

### High Memory Usage

**Symptoms**:
```
ERROR: OOMKilled
Container exited with code 137
```

**Diagnosis**:

```bash
# Check memory usage
docker stats module-rtc

# Check goroutines (potential leak)
curl http://localhost:6060/debug/pprof/goroutine | wc -l

# Check heap allocation
go tool pprof http://localhost:6060/debug/pprof/heap
```

**Solutions**:

```bash
# Increase memory limit
docker run -m 1g --memory-reservation 512m \
  waddlebot/module-rtc:latest

# Reduce maximum hand queue size
# Implement automatic cleanup of old hands:
# - Timeout raised hands after 1 hour
# - Limit queue to 1000 entries

# Clear state periodically
# Add cleanup job to restart service

# Check for memory leaks
# Profile heap over time
go tool pprof -alloc_space http://localhost:6060/debug/pprof/heap
go tool pprof -inuse_space http://localhost:6060/debug/pprof/heap
```

---

## Logging & Debugging

### Enable Debug Logging

```bash
# Start with debug logs
export LOG_LEVEL=DEBUG
go run ./cmd/server/main.go

# Docker
docker run -e LOG_LEVEL=DEBUG \
  waddlebot/module-rtc:latest

# Kubernetes
kubectl set env deployment/module-rtc LOG_LEVEL=DEBUG
```

### Trace Requests

```bash
# Enable request logging with proxy
docker run -p 8094:8093 \
  -e LOG_LEVEL=DEBUG \
  waddlebot/module-rtc:latest

# Use tcpdump to capture traffic
tcpdump -i any -A 'tcp port 8093'

# Use mitmproxy
mitmproxy -p 8094 --mode reverse:http://localhost:8093
```

### Check Dependencies

```bash
# Verify all dependencies are running
docker-compose ps

# Check network connectivity between services
docker exec module-rtc \
  curl -v http://livekit:7880/health

docker exec module-rtc \
  psql -h postgres -U waddlebot -d waddlebot -c "SELECT 1;"
```

---

## Getting Help

If you encounter issues not covered above:

1. **Check logs**: `docker logs module-rtc -f`
2. **Enable debug mode**: `LOG_LEVEL=DEBUG`
3. **Test dependencies**: LiveKit, PostgreSQL, Redis
4. **Review configuration**: Verify all environment variables
5. **Test endpoints**: Use curl to isolate the issue
6. **Community**: Check documentation at `/docs/module_rtc/`

For enterprise support: support@penguintech.io
