# Module RTC — API Reference

Complete REST API reference for Module RTC. All endpoints use JSON request/response format and are prefixed with `/api/v1`.

## Base Configuration

| Item | Value |
|------|-------|
| Base URL | `http://localhost:8093` |
| API Prefix | `/api/v1` |
| Content-Type | `application/json` |
| Authentication | Bearer token (from room join) |

## Room Management Endpoints

### Create Room

**Endpoint**: `POST /api/v1/rooms`

**Description**: Creates a new call room for a community. Returns room metadata and LiveKit integration details.

**Request**:
```json
{
  "community_id": 1,
  "room_name": "general-meeting",
  "max_participants": 100
}
```

**Request Parameters**:
- `community_id` (integer, required): Community ID that owns this room
- `room_name` (string, required): Human-readable room name (alphanumeric, hyphens allowed)
- `max_participants` (integer, optional): Maximum concurrent participants (default: 100)

**Response** (201 Created):
```json
{
  "room_id": "rm_abc123def456",
  "room_name": "community_1_general-meeting",
  "community_id": 1,
  "participants": 0,
  "created_at": "2026-02-16T10:30:00Z",
  "is_locked": false
}
```

**Response Fields**:
- `room_id`: LiveKit room ID (unique identifier)
- `room_name`: Full room name (includes community ID prefix)
- `community_id`: Owner community ID
- `participants`: Current participant count
- `created_at`: Room creation timestamp
- `is_locked`: Current lock status

**Error Responses**:
- `400 Bad Request`: Invalid JSON or missing required fields
- `500 Internal Server Error`: Database or LiveKit connection error

---

### Get Room Details

**Endpoint**: `GET /api/v1/rooms/{roomName}`

**Description**: Retrieves metadata for a specific room.

**Path Parameters**:
- `roomName` (string): Full room name (e.g., `community_1_general-meeting`)

**Response** (200 OK):
```json
{
  "room_id": "rm_abc123def456",
  "room_name": "community_1_general-meeting",
  "community_id": 1,
  "participants": 5,
  "created_at": "2026-02-16T10:30:00Z",
  "is_locked": false
}
```

**Error Responses**:
- `404 Not Found`: Room does not exist
- `500 Internal Server Error`: Database error

---

### Delete Room

**Endpoint**: `DELETE /api/v1/rooms/{roomName}`

**Description**: Permanently deletes a room and removes all participants.

**Path Parameters**:
- `roomName` (string): Full room name

**Response** (200 OK):
```json
{
  "success": true
}
```

**Error Responses**:
- `404 Not Found`: Room does not exist
- `500 Internal Server Error`: LiveKit deletion error

---

## Participant Endpoints

### Join Room

**Endpoint**: `POST /api/v1/rooms/{roomName}/join`

**Description**: Authenticates a user and returns a LiveKit access token for WebRTC connection.

**Path Parameters**:
- `roomName` (string): Full room name

**Request**:
```json
{
  "user_id": "user_alice_123",
  "user_name": "Alice Smith",
  "role": "host"
}
```

**Request Parameters**:
- `user_id` (string, required): Unique user identifier
- `user_name` (string, required): Display name (UTF-8 allowed)
- `role` (string, optional): One of `host`, `moderator`, `speaker`, `viewer` (default: `viewer`)

**Response** (200 OK):
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "room_name": "community_1_general-meeting",
  "identity": "user_alice_123"
}
```

**Response Fields**:
- `token`: LiveKit JWT access token (use with WebRTC client)
- `room_name`: Room name to connect to
- `identity`: User identity in room

**Token Details**:
- **Validity**: 24 hours from issue
- **Grants**: Based on role parameter
- **Format**: JWT with LiveKit-specific claims

**Role Permissions**:
| Role | Can Publish Audio/Video | Can Publish Data | Use Case |
|------|------------------------|--------------------|----------|
| host | Yes | Yes | Call organizer |
| moderator | Yes | Yes | Community moderator |
| speaker | Yes | No | Presenting participant |
| viewer | No | No | Audience member |

**Error Responses**:
- `400 Bad Request`: Invalid request body
- `403 Forbidden`: Room is locked
- `500 Internal Server Error`: Token generation failed

---

### Leave Room

**Endpoint**: `POST /api/v1/rooms/{roomName}/leave`

**Description**: Removes a participant from the room and cleans up their raised hand (if any).

**Path Parameters**:
- `roomName` (string): Full room name

**Request**:
```json
{
  "user_id": "user_alice_123"
}
```

**Response** (200 OK):
```json
{
  "success": true
}
```

**Error Responses**:
- `400 Bad Request`: Invalid request body
- `500 Internal Server Error`: Removal failed

---

### List Participants

**Endpoint**: `GET /api/v1/rooms/{roomName}/participants`

**Description**: Returns all current participants in a room.

**Path Parameters**:
- `roomName` (string): Full room name

**Response** (200 OK):
```json
{
  "participants": [
    {
      "user_id": "sid_abc123",
      "identity": "user_alice_123",
      "role": "host",
      "joined_at": 1707988200,
      "is_muted": false
    },
    {
      "user_id": "sid_def456",
      "identity": "user_bob_456",
      "role": "viewer",
      "joined_at": 1707988250,
      "is_muted": true
    }
  ],
  "count": 2
}
```

**Response Fields**:
- `participants`: Array of participant objects
  - `user_id`: LiveKit participant SID
  - `identity`: User identity
  - `role`: Participant role
  - `joined_at`: Unix timestamp of join time
  - `is_muted`: Audio publication status
- `count`: Total participant count

**Error Responses**:
- `404 Not Found`: Room does not exist
- `500 Internal Server Error`: Database error

---

## Raised Hand Endpoints

### Raise Hand

**Endpoint**: `POST /api/v1/rooms/{roomName}/raise-hand`

**Description**: Adds a participant to the raised hand queue (FIFO order).

**Path Parameters**:
- `roomName` (string): Full room name

**Request**:
```json
{
  "user_id": "user_alice_123",
  "user_name": "Alice Smith"
}
```

**Response** (200 OK):
```json
{
  "success": true
}
```

**Behavior**:
- If user already has hand raised, request is idempotent (returns success)
- Timestamp of raise is recorded
- User appears in raised hands queue in FIFO order

**Error Responses**:
- `400 Bad Request`: Invalid request body
- `500 Internal Server Error`: Queue operation failed

---

### Lower Hand

**Endpoint**: `POST /api/v1/rooms/{roomName}/lower-hand`

**Description**: Removes a participant from the raised hand queue.

**Path Parameters**:
- `roomName` (string): Full room name

**Request**:
```json
{
  "user_id": "user_alice_123"
}
```

**Response** (200 OK):
```json
{
  "success": true
}
```

**Behavior**:
- If user's hand is not raised, returns success (idempotent)
- Acknowledgment status is cleared

**Error Responses**:
- `400 Bad Request`: Invalid request body
- `500 Internal Server Error`: Queue operation failed

---

### Get Raised Hands

**Endpoint**: `GET /api/v1/rooms/{roomName}/raised-hands`

**Description**: Returns all participants with raised hands in FIFO order.

**Path Parameters**:
- `roomName` (string): Full room name

**Response** (200 OK):
```json
{
  "raised_hands": [
    {
      "user_id": "user_alice_123",
      "user_name": "Alice Smith",
      "raised_at": "2026-02-16T10:35:00Z",
      "acknowledged_at": null,
      "acknowledged_by": ""
    },
    {
      "user_id": "user_charlie_789",
      "user_name": "Charlie Jones",
      "raised_at": "2026-02-16T10:36:15Z",
      "acknowledged_at": "2026-02-16T10:36:30Z",
      "acknowledged_by": "user_bob_456"
    }
  ],
  "count": 2
}
```

**Response Fields**:
- `raised_hands`: Array of raised hand objects
  - `user_id`: User identifier
  - `user_name`: User display name
  - `raised_at`: Timestamp when hand was raised
  - `acknowledged_at`: Timestamp of acknowledgment (null if not acknowledged)
  - `acknowledged_by`: Moderator ID who acknowledged (empty if not acknowledged)
- `count`: Total hands raised

**Order**: Returns in FIFO order (oldest raise first)

**Error Responses**:
- `404 Not Found`: Room does not exist
- `500 Internal Server Error`: Database error

---

### Acknowledge Raised Hand

**Endpoint**: `POST /api/v1/rooms/{roomName}/acknowledge-hand/{userId}`

**Description**: Marks a raised hand as acknowledged by a moderator.

**Path Parameters**:
- `roomName` (string): Full room name
- `userId` (string): User ID of the raised hand

**Request**:
```json
{
  "moderator_id": "user_bob_456"
}
```

**Response** (200 OK):
```json
{
  "success": true
}
```

**Behavior**:
- Records acknowledgment timestamp and moderator ID
- Does not automatically lower the hand (user can still speak)
- Multiple acknowledgments update the latest one

**Error Responses**:
- `400 Bad Request`: Invalid request body
- `500 Internal Server Error`: Update failed

---

## Moderator Control Endpoints

### Mute Participant

**Endpoint**: `POST /api/v1/rooms/{roomName}/mute/{userId}`

**Description**: Mutes a specific participant's audio.

**Path Parameters**:
- `roomName` (string): Full room name
- `userId` (string): User identity to mute

**Request**:
```json
{
  "moderator_id": "user_bob_456"
}
```

**Response** (200 OK):
```json
{
  "success": true
}
```

**Behavior**:
- Applies LiveKit permission update
- Participant cannot publish audio but can still listen
- Participant client receives unmute event from server

**Error Responses**:
- `400 Bad Request`: Invalid request body
- `500 Internal Server Error`: LiveKit update failed

---

### Unmute Participant

**Endpoint**: `POST /api/v1/rooms/{roomName}/unmute/{userId}`

**Description**: Unmutes a specific participant's audio.

**Path Parameters**:
- `roomName` (string): Full room name
- `userId` (string): User identity to unmute

**Request**:
```json
{
  "moderator_id": "user_bob_456"
}
```

**Response** (200 OK):
```json
{
  "success": true
}
```

**Error Responses**:
- `400 Bad Request`: Invalid request body
- `500 Internal Server Error`: LiveKit update failed

---

### Mute All Participants

**Endpoint**: `POST /api/v1/rooms/{roomName}/mute-all`

**Description**: Mutes all participants except the moderator executing the command.

**Path Parameters**:
- `roomName` (string): Full room name

**Request**:
```json
{
  "moderator_id": "user_bob_456"
}
```

**Response** (200 OK):
```json
{
  "success": true
}
```

**Behavior**:
- Applies to all participants except the moderator
- New participants joining after this retain their audio capability
- Previously muted participants remain muted

**Error Responses**:
- `400 Bad Request`: Invalid request body
- `500 Internal Server Error`: LiveKit update error

---

### Kick Participant

**Endpoint**: `POST /api/v1/rooms/{roomName}/kick/{userId}`

**Description**: Removes a participant from the room.

**Path Parameters**:
- `roomName` (string): Full room name
- `userId` (string): User identity to remove

**Request**:
```json
{
  "admin_id": "user_bob_456"
}
```

**Response** (200 OK):
```json
{
  "success": true
}
```

**Behavior**:
- Removes participant from LiveKit room
- Automatically lowers their hand if raised
- Participant receives disconnect event

**Error Responses**:
- `400 Bad Request`: Invalid request body
- `500 Internal Server Error`: LiveKit removal failed

---

## Room Control Endpoints

### Lock Room

**Endpoint**: `POST /api/v1/rooms/{roomName}/lock`

**Description**: Prevents new participants from joining the room.

**Path Parameters**:
- `roomName` (string): Full room name

**Request**:
```json
{
  "admin_id": "user_bob_456"
}
```

**Response** (200 OK):
```json
{
  "success": true
}
```

**Behavior**:
- Existing participants can remain
- Join requests after lock receive 403 Forbidden
- Lock state is in-memory (not persisted to database)

**Error Responses**:
- `400 Bad Request`: Invalid request body
- `500 Internal Server Error`: Lock operation failed

---

### Unlock Room

**Endpoint**: `POST /api/v1/rooms/{roomName}/unlock`

**Description**: Allows new participants to join the room again.

**Path Parameters**:
- `roomName` (string): Full room name

**Request**:
```json
{
  "admin_id": "user_bob_456"
}
```

**Response** (200 OK):
```json
{
  "success": true
}
```

**Error Responses**:
- `400 Bad Request`: Invalid request body
- `500 Internal Server Error`: Unlock operation failed

---

## Health Check

### Health Status

**Endpoint**: `GET /health`

**Description**: Returns module health and version information. Used by load balancers and monitoring.

**Response** (200 OK):
```json
{
  "status": "healthy",
  "module": "module_rtc",
  "version": "1.0.0",
  "timestamp": "2026-02-16T10:40:00Z"
}
```

**Fields**:
- `status`: "healthy" (always 200 OK response)
- `module`: Module name identifier
- `version`: Semantic version
- `timestamp`: Current server timestamp (RFC3339)

---

## Error Response Format

All error responses follow this format:

```json
{
  "error": "Human-readable error message"
}
```

### Common HTTP Status Codes

| Status | Meaning | Common Causes |
|--------|---------|---------------|
| 200 | OK | Successful request |
| 201 | Created | Room created successfully |
| 400 | Bad Request | Invalid JSON or missing fields |
| 403 | Forbidden | Room locked or permission denied |
| 404 | Not Found | Room or participant not found |
| 500 | Internal Server Error | Database/LiveKit connectivity issues |

---

## Request/Response Examples

### Complete Example: Host Hosts a Meeting

```bash
# Step 1: Create room
curl -X POST http://localhost:8093/api/v1/rooms \
  -H "Content-Type: application/json" \
  -d '{"community_id":1,"room_name":"standup","max_participants":50}'

# Step 2: Host joins as host
curl -X POST http://localhost:8093/api/v1/rooms/community_1_standup/join \
  -H "Content-Type: application/json" \
  -d '{"user_id":"host1","user_name":"Alice","role":"host"}'

# Step 3: Get token from response, connect to LiveKit with it

# Step 4: Participant joins as viewer
curl -X POST http://localhost:8093/api/v1/rooms/community_1_standup/join \
  -H "Content-Type: application/json" \
  -d '{"user_id":"participant1","user_name":"Bob","role":"viewer"}'

# Step 5: Viewer raises hand
curl -X POST http://localhost:8093/api/v1/rooms/community_1_standup/raise-hand \
  -H "Content-Type: application/json" \
  -d '{"user_id":"participant1","user_name":"Bob"}'

# Step 6: Host sees raised hands
curl http://localhost:8093/api/v1/rooms/community_1_standup/raised-hands

# Step 7: Host acknowledges
curl -X POST http://localhost:8093/api/v1/rooms/community_1_standup/acknowledge-hand/participant1 \
  -H "Content-Type: application/json" \
  -d '{"moderator_id":"host1"}'

# Step 8: Host unmutes participant
curl -X POST http://localhost:8093/api/v1/rooms/community_1_standup/unmute/participant1 \
  -H "Content-Type: application/json" \
  -d '{"moderator_id":"host1"}'
```

---

## Rate Limiting

Module RTC does not implement built-in rate limiting. Deploy behind a reverse proxy (nginx, HAProxy) for production rate limiting.

## CORS

Module RTC does not set CORS headers. Configure CORS at the reverse proxy level.

## Authentication

- REST API is open (no per-endpoint auth required)
- Access control enforced via role-based permissions in LiveKit tokens
- Moderator/admin verification relies on request parameters (implement token validation at API gateway level)
