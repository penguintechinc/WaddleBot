# Module RTC — Testing Guide

Comprehensive testing guide for Module RTC, including unit tests, integration tests, and real-world signaling flow simulations.

## Test Setup

### Prerequisites

```bash
# Install testing tools
go install github.com/stretchr/testify/assert@latest
go install gotest.tools/gotestsum@latest

# Install LiveKit test server (optional)
docker pull livekit/livekit-server:latest

# Install test dependencies
cd /home/penguin/code/waddlebot/core/module_rtc
go mod download
```

### Test Directory Structure

```
core/module_rtc/
├── internal/
│   ├── api/
│   │   └── handlers_test.go      # HTTP handler tests
│   ├── services/
│   │   ├── room_service_test.go  # Room lifecycle tests
│   │   └── call_features_test.go # Call feature tests
│   └── config/
│       └── config_test.go        # Configuration tests
└── cmd/
    └── server/
        └── main_test.go          # Server startup tests
```

## Unit Tests

### Running Unit Tests

```bash
# Run all unit tests
cd /home/penguin/code/waddlebot/core/module_rtc
go test ./...

# Run with verbose output
go test -v ./...

# Run specific package
go test -v ./internal/services

# Run specific test
go test -v -run TestRaiseHand ./internal/services

# Run with coverage
go test -cover ./...

# Generate coverage report
go test -coverprofile=coverage.out ./...
go tool cover -html=coverage.out
```

### Example Unit Tests

#### Room Service Tests

```go
// internal/services/room_service_test.go
package services

import (
    "context"
    "testing"
    "github.com/stretchr/testify/assert"
)

func TestCreateRoom(t *testing.T) {
    // Setup mock LiveKit client
    service := NewRoomService("localhost:7880", "devkey", "devsecret")

    // Test room creation
    room, err := service.CreateRoom(context.Background(), 1, "test-room", 50)

    // Assertions
    assert.NoError(t, err)
    assert.NotNil(t, room)
    assert.Equal(t, "community_1_test-room", room.RoomName)
    assert.Equal(t, 0, room.Participants)
    assert.False(t, room.IsLocked)
}

func TestJoinRoom(t *testing.T) {
    service := NewRoomService("localhost:7880", "devkey", "devsecret")

    // Test token generation
    token, err := service.JoinRoom(
        context.Background(),
        "test-room",
        "user123",
        "John Doe",
        "host",
    )

    assert.NoError(t, err)
    assert.NotEmpty(t, token.Token)
    assert.Equal(t, "test-room", token.RoomName)
    assert.Equal(t, "user123", token.Identity)
}

func TestMuteParticipant(t *testing.T) {
    service := NewRoomService("localhost:7880", "devkey", "devsecret")

    // Test muting
    err := service.MuteParticipant(
        context.Background(),
        "test-room",
        "user123",
        true,
    )

    assert.NoError(t, err)
}
```

#### Call Features Tests

```go
// internal/services/call_features_test.go
package services

import (
    "context"
    "testing"
    "time"
    "github.com/stretchr/testify/assert"
)

func TestRaiseHand(t *testing.T) {
    roomService := NewRoomService("localhost:7880", "devkey", "devsecret")
    features := NewCallFeaturesService(roomService)

    // User raises hand
    err := features.RaiseHand(context.Background(), "room1", "user1", "Alice")
    assert.NoError(t, err)

    // Get raised hands
    hands, err := features.GetRaisedHands(context.Background(), "room1")
    assert.NoError(t, err)
    assert.Len(t, hands, 1)
    assert.Equal(t, "user1", hands[0].UserID)
    assert.Equal(t, "Alice", hands[0].UserName)
}

func TestRaiseHandIdempotent(t *testing.T) {
    roomService := NewRoomService("localhost:7880", "devkey", "devsecret")
    features := NewCallFeaturesService(roomService)

    // Raise hand twice
    err1 := features.RaiseHand(context.Background(), "room1", "user1", "Alice")
    err2 := features.RaiseHand(context.Background(), "room1", "user1", "Alice")

    assert.NoError(t, err1)
    assert.NoError(t, err2)

    hands, _ := features.GetRaisedHands(context.Background(), "room1")
    assert.Len(t, hands, 1) // Only one entry
}

func TestLowerHand(t *testing.T) {
    roomService := NewRoomService("localhost:7880", "devkey", "devsecret")
    features := NewCallFeaturesService(roomService)

    // Raise then lower
    features.RaiseHand(context.Background(), "room1", "user1", "Alice")
    err := features.LowerHand(context.Background(), "room1", "user1")
    assert.NoError(t, err)

    hands, _ := features.GetRaisedHands(context.Background(), "room1")
    assert.Len(t, hands, 0)
}

func TestAcknowledgeHand(t *testing.T) {
    roomService := NewRoomService("localhost:7880", "devkey", "devsecret")
    features := NewCallFeaturesService(roomService)

    // Setup
    features.RaiseHand(context.Background(), "room1", "user1", "Alice")

    // Acknowledge
    err := features.AcknowledgeHand(context.Background(), "room1", "user1", "moderator1")
    assert.NoError(t, err)

    hands, _ := features.GetRaisedHands(context.Background(), "room1")
    assert.NotNil(t, hands[0].AcknowledgedAt)
    assert.Equal(t, "moderator1", hands[0].AcknowledgedBy)
}

func TestLockRoom(t *testing.T) {
    roomService := NewRoomService("localhost:7880", "devkey", "devsecret")
    features := NewCallFeaturesService(roomService)

    // Lock room
    err := features.LockRoom(context.Background(), "room1", "admin1")
    assert.NoError(t, err)

    // Check locked status
    assert.True(t, features.IsRoomLocked(context.Background(), "room1"))
}

func TestRaisedHandsOrder(t *testing.T) {
    roomService := NewRoomService("localhost:7880", "devkey", "devsecret")
    features := NewCallFeaturesService(roomService)

    // Raise hands in order
    features.RaiseHand(context.Background(), "room1", "user1", "Alice")
    time.Sleep(10 * time.Millisecond)
    features.RaiseHand(context.Background(), "room1", "user2", "Bob")
    time.Sleep(10 * time.Millisecond)
    features.RaiseHand(context.Background(), "room1", "user3", "Charlie")

    // Get raised hands
    hands, _ := features.GetRaisedHands(context.Background(), "room1")

    // Verify FIFO order
    assert.Len(t, hands, 3)
    assert.Equal(t, "user1", hands[0].UserID) // First raised
    assert.Equal(t, "user2", hands[1].UserID) // Second
    assert.Equal(t, "user3", hands[2].UserID) // Third
}
```

## Integration Tests

### Docker Compose Test Environment

Create `docker-compose.test.yml`:

```yaml
version: '3.8'

services:
  module-rtc:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8093:8093"
      - "50067:50067"
    environment:
      LIVEKIT_HOST: livekit:7880
      LIVEKIT_API_KEY: test-key
      LIVEKIT_API_SECRET: test-secret
      DATABASE_URL: postgres://test:test@postgres:5432/module_rtc_test
      LOG_LEVEL: DEBUG
    depends_on:
      - postgres
      - livekit
    networks:
      - test

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: test
      POSTGRES_PASSWORD: test
      POSTGRES_DB: module_rtc_test
    networks:
      - test

  livekit:
    image: livekit/livekit-server:latest
    command: --dev --ip=0.0.0.0
    ports:
      - "7880:7880"
    networks:
      - test

networks:
  test:
    driver: bridge
```

Start test environment:

```bash
docker-compose -f docker-compose.test.yml up -d

# Wait for services to be ready
sleep 10

# Run tests
go test -v -tags=integration ./...

# Cleanup
docker-compose -f docker-compose.test.yml down
```

### Integration Test Example

```go
// internal/api/handlers_integration_test.go
// +build integration

package api

import (
    "bytes"
    "encoding/json"
    "net/http"
    "net/http/httptest"
    "testing"
    "github.com/gorilla/mux"
    "github.com/stretchr/testify/assert"
)

func TestCreateRoomIntegration(t *testing.T) {
    // Setup
    router := mux.NewRouter()
    handlers := NewHandlers(roomService, featuresService)
    handlers.RegisterRoutes(router)

    // Prepare request
    body := map[string]interface{}{
        "community_id":     1,
        "room_name":        "integration-test",
        "max_participants": 50,
    }
    jsonBody, _ := json.Marshal(body)

    // Make request
    req := httptest.NewRequest("POST", "/api/v1/rooms", bytes.NewReader(jsonBody))
    w := httptest.NewRecorder()

    router.ServeHTTP(w, req)

    // Verify response
    assert.Equal(t, http.StatusCreated, w.Code)

    var response map[string]interface{}
    json.Unmarshal(w.Body.Bytes(), &response)
    assert.NotNil(t, response["room_id"])
}

func TestJoinRoomFlow(t *testing.T) {
    // Create room first
    roomResponse := createTestRoom(t)
    roomName := roomResponse["room_name"].(string)

    // Now join room
    joinBody := map[string]interface{}{
        "user_id":   "user_test_123",
        "user_name": "Test User",
        "role":      "host",
    }
    jsonBody, _ := json.Marshal(joinBody)

    req := httptest.NewRequest(
        "POST",
        "/api/v1/rooms/"+roomName+"/join",
        bytes.NewReader(jsonBody),
    )
    w := httptest.NewRecorder()

    router.ServeHTTP(w, req)

    assert.Equal(t, http.StatusOK, w.Code)

    var token map[string]interface{}
    json.Unmarshal(w.Body.Bytes(), &token)
    assert.NotEmpty(t, token["token"])
}

func TestRaiseHandFlow(t *testing.T) {
    // Create room and user joins
    setupTestRoom(t)

    // Raise hand
    raiseBody := map[string]interface{}{
        "user_id":   "user_test_123",
        "user_name": "Test User",
    }
    jsonBody, _ := json.Marshal(raiseBody)

    req := httptest.NewRequest(
        "POST",
        "/api/v1/rooms/test_room/raise-hand",
        bytes.NewReader(jsonBody),
    )
    w := httptest.NewRecorder()

    router.ServeHTTP(w, req)
    assert.Equal(t, http.StatusOK, w.Code)

    // Get raised hands
    req = httptest.NewRequest("GET", "/api/v1/rooms/test_room/raised-hands", nil)
    w = httptest.NewRecorder()

    router.ServeHTTP(w, req)
    assert.Equal(t, http.StatusOK, w.Code)

    var response map[string]interface{}
    json.Unmarshal(w.Body.Bytes(), &response)
    hands := response["raised_hands"].([]interface{})
    assert.Len(t, hands, 1)
}
```

## Signaling Flow Simulation Tests

### Test Scenario: Complete Call Workflow

```bash
#!/bin/bash
# scripts/test_signaling_flow.sh

HOST="http://localhost:8093"
COMMUNITY_ID=1
ROOM_NAME="test-call-$(date +%s)"

echo "=== Module RTC Signaling Flow Test ==="
echo ""

# Step 1: Create room
echo "1. Creating room: $ROOM_NAME"
ROOM_RESPONSE=$(curl -s -X POST $HOST/api/v1/rooms \
  -H "Content-Type: application/json" \
  -d "{\"community_id\": $COMMUNITY_ID, \"room_name\": \"$ROOM_NAME\", \"max_participants\": 10}")

FULL_ROOM_NAME=$(echo $ROOM_RESPONSE | jq -r '.room_name')
echo "   Created: $FULL_ROOM_NAME"
echo ""

# Step 2: Host joins
echo "2. Host joining room"
HOST_TOKEN=$(curl -s -X POST $HOST/api/v1/rooms/$FULL_ROOM_NAME/join \
  -H "Content-Type: application/json" \
  -d '{"user_id": "host_user_1", "user_name": "Host", "role": "host"}' | jq -r '.token')
echo "   Host token obtained: ${HOST_TOKEN:0:30}..."
echo ""

# Step 3: Participant joins
echo "3. Participant joining room"
PARTICIPANT_TOKEN=$(curl -s -X POST $HOST/api/v1/rooms/$FULL_ROOM_NAME/join \
  -H "Content-Type: application/json" \
  -d '{"user_id": "participant_1", "user_name": "Participant", "role": "viewer"}' | jq -r '.token')
echo "   Participant token obtained: ${PARTICIPANT_TOKEN:0:30}..."
echo ""

# Step 4: List participants
echo "4. Listing participants"
curl -s -X GET $HOST/api/v1/rooms/$FULL_ROOM_NAME/participants | jq '.participants[] | {identity, role, is_muted}'
echo ""

# Step 5: Participant raises hand
echo "5. Participant raising hand"
curl -s -X POST $HOST/api/v1/rooms/$FULL_ROOM_NAME/raise-hand \
  -H "Content-Type: application/json" \
  -d '{"user_id": "participant_1", "user_name": "Participant"}' | jq '.'
echo ""

# Step 6: Get raised hands
echo "6. Host viewing raised hands"
curl -s -X GET $HOST/api/v1/rooms/$FULL_ROOM_NAME/raised-hands | jq '.raised_hands'
echo ""

# Step 7: Acknowledge hand
echo "7. Host acknowledging hand"
curl -s -X POST $HOST/api/v1/rooms/$FULL_ROOM_NAME/acknowledge-hand/participant_1 \
  -H "Content-Type: application/json" \
  -d '{"moderator_id": "host_user_1"}' | jq '.'
echo ""

# Step 8: Unmute participant
echo "8. Host unmuting participant"
curl -s -X POST $HOST/api/v1/rooms/$FULL_ROOM_NAME/unmute/participant_1 \
  -H "Content-Type: application/json" \
  -d '{"moderator_id": "host_user_1"}' | jq '.'
echo ""

# Step 9: Lock room
echo "9. Host locking room (preventing new joins)"
curl -s -X POST $HOST/api/v1/rooms/$FULL_ROOM_NAME/lock \
  -H "Content-Type: application/json" \
  -d '{"admin_id": "host_user_1"}' | jq '.'
echo ""

# Step 10: Try to join when locked
echo "10. Attempting to join locked room (should fail)"
curl -s -X POST $HOST/api/v1/rooms/$FULL_ROOM_NAME/join \
  -H "Content-Type: application/json" \
  -d '{"user_id": "new_user", "user_name": "New User", "role": "viewer"}' | jq '.'
echo ""

# Step 11: Unlock room
echo "11. Host unlocking room"
curl -s -X POST $HOST/api/v1/rooms/$FULL_ROOM_NAME/unlock \
  -H "Content-Type: application/json" \
  -d '{"admin_id": "host_user_1"}' | jq '.'
echo ""

# Step 12: Participant leaves
echo "12. Participant leaving"
curl -s -X POST $HOST/api/v1/rooms/$FULL_ROOM_NAME/leave \
  -H "Content-Type: application/json" \
  -d '{"user_id": "participant_1"}' | jq '.'
echo ""

# Step 13: Delete room
echo "13. Host deleting room"
curl -s -X DELETE $HOST/api/v1/rooms/$FULL_ROOM_NAME | jq '.'
echo ""

echo "=== Test Complete ==="
```

Run the test:

```bash
chmod +x scripts/test_signaling_flow.sh
./scripts/test_signaling_flow.sh
```

### Load Testing with Apache Bench

```bash
# Test room creation rate
ab -n 100 -c 10 -p /tmp/create_room.json \
  -T application/json \
  http://localhost:8093/api/v1/rooms

# Test health check
ab -n 1000 -c 50 http://localhost:8093/health

# Test join room requests
ab -n 100 -c 5 -p /tmp/join_room.json \
  -T application/json \
  http://localhost:8093/api/v1/rooms/test_room/join
```

### Load Testing with K6

```javascript
// tests/load_test.js
import http from 'k6/http';
import { check, sleep } from 'k6';

export let options = {
  vus: 50,      // 50 virtual users
  duration: '2m' // 2 minutes
};

export default function () {
  // Create room
  let createRoomRes = http.post('http://localhost:8093/api/v1/rooms', {
    community_id: 1,
    room_name: 'load-test-' + __VU + '-' + __ITER,
    max_participants: 100
  }, {
    headers: { 'Content-Type': 'application/json' }
  });

  check(createRoomRes, {
    'room created': (r) => r.status === 201
  });

  let roomName = JSON.parse(createRoomRes.body).room_name;

  // Join room
  let joinRes = http.post(`http://localhost:8093/api/v1/rooms/${roomName}/join`, {
    user_id: 'user-' + __VU + '-' + __ITER,
    user_name: 'User ' + __VU,
    role: 'viewer'
  }, {
    headers: { 'Content-Type': 'application/json' }
  });

  check(joinRes, {
    'room joined': (r) => r.status === 200
  });

  // Raise hand
  http.post(`http://localhost:8093/api/v1/rooms/${roomName}/raise-hand`, {
    user_id: 'user-' + __VU + '-' + __ITER,
    user_name: 'User ' + __VU
  }, {
    headers: { 'Content-Type': 'application/json' }
  });

  sleep(1);
}
```

Run load test:

```bash
k6 run tests/load_test.js
```

## Health Check Testing

```bash
# Simple health check
curl http://localhost:8093/health

# Verify all fields
curl -s http://localhost:8093/health | jq '.status'

# Monitor health (every 5 seconds)
watch -n 5 'curl -s http://localhost:8093/health | jq'
```

## Manual Testing Checklist

### Pre-Deployment Testing

- [ ] Health check returns 200 OK
- [ ] Create room with valid params returns 201 Created
- [ ] Create room with missing params returns 400 Bad Request
- [ ] Join room with valid token generates JWT
- [ ] Join locked room returns 403 Forbidden
- [ ] Raise hand works for multiple users
- [ ] Get raised hands returns FIFO order
- [ ] Acknowledge hand marks timestamp
- [ ] Mute participant succeeds
- [ ] Unmute participant succeeds
- [ ] Mute all excludes moderator
- [ ] Kick participant removes from room
- [ ] Lock room prevents joins
- [ ] Unlock room allows joins
- [ ] Delete room removes all participants

### Concurrency Testing

- [ ] 10 simultaneous joins to same room
- [ ] 10 simultaneous hand raises
- [ ] Concurrent mute and unmute operations
- [ ] Lock/unlock while users joining

### Error Handling

- [ ] Invalid JSON returns 400
- [ ] Missing required fields returns 400
- [ ] Non-existent room returns 404
- [ ] Database connection loss returns 500
- [ ] LiveKit connection loss returns 500

## Continuous Integration

### GitHub Actions Test Workflow

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test
          POSTGRES_DB: module_rtc_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      livekit:
        image: livekit/livekit-server:latest
        options: --cmd "--dev --ip=0.0.0.0"

    steps:
      - uses: actions/checkout@v3

      - uses: actions/setup-go@v4
        with:
          go-version: '1.24'

      - run: go test -v -race -coverprofile=coverage.out ./...

      - run: go tool cover -func=coverage.out

      - uses: codecov/codecov-action@v3
```

## Coverage Goals

- **Minimum Coverage**: 80%
- **Critical Paths**: 95% (room creation, token generation, muting)
- **Error Handling**: 100%

View coverage:

```bash
go test -coverprofile=coverage.out ./...
go tool cover -html=coverage.out -o coverage.html
open coverage.html
```
