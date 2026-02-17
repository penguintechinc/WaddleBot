# Video Proxy Module — API Reference

Complete specification for all REST API endpoints and gRPC methods supported by the video_proxy_module.

---

## Table of Contents

1. [REST API Overview](#rest-api-overview)
2. [Authentication](#authentication)
3. [Stream Configuration Endpoints](#stream-configuration-endpoints)
4. [Stream Destination Endpoints](#stream-destination-endpoints)
5. [Stream Status Endpoints](#stream-status-endpoints)
6. [gRPC Service Reference](#grpc-service-reference)
7. [Error Codes](#error-codes)
8. [Stream URL Formats](#stream-url-formats)

---

## REST API Overview

**Base URL**: `http://localhost:8092/api/v1`

**Authentication**: Bearer token in `Authorization` header

**Content-Type**: `application/json`

**Response Format**: JSON

---

## Authentication

### Bearer Token

All REST endpoints require JWT authentication via the `Authorization` header:

```
Authorization: Bearer <jwt-token>
```

### JWT Token Generation

**Endpoint**: Custom (application-specific)

Example JWT payload:
```json
{
  "sub": "admin",
  "exp": 1708103445,
  "iat": 1708099845
}
```

Generated with:
- Algorithm: HS256
- Secret: `JWT_SECRET_KEY` from configuration
- Default expiration: 3600 seconds (1 hour)

---

## Stream Configuration Endpoints

### Create Stream Configuration

**Method**: `POST`
**Path**: `/stream/config`
**Auth**: Required

Create a new stream configuration for a community.

**Request Body**:
```json
{
  "community_id": "string (required, max 255 chars, must be unique)"
}
```

**Response** (201 Created):
```json
{
  "success": true,
  "config": {
    "id": 1,
    "community_id": "community-123",
    "stream_key": "secure-random-token-urlsafe-32-chars",
    "ingest_url": "rtmp://localhost:8092/live/secure-random-token-urlsafe-32-chars",
    "is_active": true,
    "created_at": "2026-02-16T10:30:45.123456",
    "updated_at": "2026-02-16T10:30:45.123456"
  }
}
```

**Status Codes**:
- `201`: Configuration created successfully
- `400`: Missing required field `community_id`
- `409`: Configuration already exists for this community
- `500`: Server error

**Notes**:
- Stream key is cryptographically secure (32-byte URL-safe random token)
- Ingest URL format: `rtmp://{MODULE_HOST}:{MODULE_PORT}/live/{stream_key}`
- Configuration creates associated stream status record

---

### Get Stream Configuration

**Method**: `GET`
**Path**: `/stream/config/<community_id>`
**Auth**: Required

Retrieve stream configuration by community ID.

**Path Parameters**:
- `community_id` (string): Community identifier

**Response** (200 OK):
```json
{
  "success": true,
  "config": {
    "id": 1,
    "community_id": "community-123",
    "stream_key": "secure-token-here",
    "ingest_url": "rtmp://localhost:8092/live/secure-token-here",
    "is_active": true,
    "created_at": "2026-02-16T10:30:45.123456",
    "updated_at": "2026-02-16T10:30:45.123456"
  }
}
```

**Status Codes**:
- `200`: Configuration retrieved
- `404`: Configuration not found
- `500`: Server error

---

### Regenerate Stream Key

**Method**: `POST`
**Path**: `/stream/key/regenerate/<community_id>`
**Auth**: Required

Generate a new stream key for a community. Invalidates the previous key.

**Path Parameters**:
- `community_id` (string): Community identifier

**Response** (200 OK):
```json
{
  "success": true,
  "config": {
    "id": 1,
    "community_id": "community-123",
    "stream_key": "new-secure-token-urlsafe-32-chars",
    "ingest_url": "rtmp://localhost:8092/live/new-secure-token-urlsafe-32-chars",
    "is_active": true,
    "created_at": "2026-02-16T10:30:45.123456",
    "updated_at": "2026-02-16T10:35:22.654321"
  }
}
```

**Status Codes**:
- `200`: Key regenerated
- `404`: Configuration not found
- `500`: Server error

**Notes**:
- Old key immediately becomes invalid
- Encoder must be updated with new key
- All active streams using old key will be interrupted

---

## Stream Destination Endpoints

### List Destinations

**Method**: `GET`
**Path**: `/stream/destinations/<config_id>`
**Auth**: Required

List all destinations for a stream configuration.

**Path Parameters**:
- `config_id` (integer): Stream configuration ID

**Response** (200 OK):
```json
{
  "success": true,
  "count": 2,
  "destinations": [
    {
      "id": 1,
      "config_id": 1,
      "platform": "twitch",
      "rtmp_url": "rtmp://live.twitch.tv/app",
      "stream_key": "twitch-ke...",
      "is_active": true,
      "force_cut": false,
      "max_resolution": "1080p",
      "created_at": "2026-02-16T10:30:45.123456",
      "updated_at": "2026-02-16T10:30:45.123456"
    },
    {
      "id": 2,
      "config_id": 1,
      "platform": "youtube",
      "rtmp_url": "rtmp://a.rtmp.youtube.com/live2",
      "stream_key": "youtube-...",
      "is_active": true,
      "force_cut": false,
      "max_resolution": "1080p",
      "created_at": "2026-02-16T10:35:10.234567",
      "updated_at": "2026-02-16T10:35:10.234567"
    }
  ]
}
```

**Status Codes**:
- `200`: Destinations listed
- `404`: Configuration not found
- `500`: Server error

**Notes**:
- Stream keys are masked (first 8 chars shown, then `...`)
- Empty array returned if no destinations exist
- Count field indicates total destinations for this config

---

### Add Destination

**Method**: `POST`
**Path**: `/stream/destinations`
**Auth**: Required

Add a new streaming destination to a configuration.

**Request Body**:
```json
{
  "config_id": 1,
  "platform": "twitch",
  "rtmp_url": "rtmp://live.twitch.tv/app",
  "stream_key": "your-twitch-stream-key",
  "max_resolution": "1080p"
}
```

**Request Fields**:
- `config_id` (integer, required): Configuration ID
- `platform` (string, required): Platform name (twitch, youtube, kick, custom)
- `rtmp_url` (string, required): RTMP endpoint URL (max 512 chars)
- `stream_key` (string, required): Stream key for this platform (max 255 chars)
- `max_resolution` (string, optional): Default `1080p`. Options: 480p, 720p, 1080p, 2K, 4K

**Response** (201 Created):
```json
{
  "success": true,
  "destination": {
    "id": 3,
    "config_id": 1,
    "platform": "kick",
    "rtmp_url": "rtmp://ingest.kick.com",
    "stream_key": "kick-ke...",
    "is_active": true,
    "force_cut": false,
    "max_resolution": "1080p",
    "created_at": "2026-02-16T10:40:15.456789",
    "updated_at": "2026-02-16T10:40:15.456789"
  }
}
```

**Status Codes**:
- `201`: Destination added
- `400`: Missing required fields
- `403`: Maximum destinations reached (free tier: 3)
- `404`: Configuration not found
- `500`: Server error

**Free Tier Limits**:
- Maximum 3 destinations per stream
- Maximum 1 destination at 2K+ resolution
- Enforced via `FREE_MAX_DESTINATIONS` and `FREE_MAX_2K_DESTINATIONS` config

---

### Remove Destination

**Method**: `DELETE`
**Path**: `/stream/destinations/<destination_id>`
**Auth**: Required

Delete a streaming destination.

**Path Parameters**:
- `destination_id` (integer): Destination ID

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Destination removed successfully"
}
```

**Status Codes**:
- `200`: Destination deleted
- `404`: Destination not found
- `500`: Server error

**Notes**:
- Immediate effect: stream is no longer proxied to this platform
- If stream is active, output to this destination stops immediately

---

### Toggle Force Cut

**Method**: `PUT`
**Path**: `/stream/destinations/<destination_id>/force-cut`
**Auth**: Required

Toggle the force-cut flag for a destination. When enabled, the proxy immediately disconnects from that platform.

**Path Parameters**:
- `destination_id` (integer): Destination ID

**Response** (200 OK):
```json
{
  "success": true,
  "destination": {
    "id": 2,
    "config_id": 1,
    "platform": "youtube",
    "rtmp_url": "rtmp://a.rtmp.youtube.com/live2",
    "stream_key": "youtube-...",
    "is_active": true,
    "force_cut": true,
    "max_resolution": "1080p",
    "created_at": "2026-02-16T10:35:10.234567",
    "updated_at": "2026-02-16T10:42:33.789012"
  }
}
```

**Status Codes**:
- `200`: Force-cut toggled
- `404`: Destination not found
- `500`: Server error

**Behavior**:
- `force_cut: false` → proxy actively sends to destination
- `force_cut: true` → proxy closes connection, no data sent
- Toggle is reversible (send same request to turn off)

---

## Stream Status Endpoints

### Get Stream Status

**Method**: `GET`
**Path**: `/stream/status/<config_id>`
**Auth**: Required

Retrieve real-time streaming status for a configuration.

**Path Parameters**:
- `config_id` (integer): Stream configuration ID

**Response** (200 OK):
```json
{
  "success": true,
  "status": {
    "config_id": 1,
    "is_streaming": true,
    "viewer_count": 452,
    "bitrate_kbps": 5000,
    "start_time": "2026-02-16T10:35:00.000000",
    "last_update": "2026-02-16T10:42:45.123456"
  }
}
```

**Status Codes**:
- `200`: Status retrieved
- `404`: Stream status not found
- `500`: Server error

**Fields**:
- `is_streaming` (boolean): Is an active stream currently being proxied?
- `viewer_count` (integer): Aggregate viewer count across destinations
- `bitrate_kbps` (integer): Current bitrate in kilobits per second
- `start_time` (ISO 8601): When the stream session began (null if not streaming)
- `last_update` (ISO 8601): Timestamp of last status update

---

### Health Check

**Method**: `GET`
**Path**: `/health`
**Auth**: Not required

Check overall module health and database connectivity.

**Response** (200 OK):
```json
{
  "status": "healthy",
  "module": "video_proxy_module",
  "version": "1.0.0",
  "timestamp": "2026-02-16T10:45:30.234567",
  "database": "connected"
}
```

**Response** (503 Service Unavailable):
```json
{
  "status": "unhealthy",
  "error": "Connection refused to PostgreSQL"
}
```

---

## gRPC Service Reference

**Service Name**: `video_proxy.VideoProxyService`
**Port**: 50065
**Protocol**: gRPC (protobuf3)

### RPC Methods

#### GetStreamConfig
Retrieve stream configuration via gRPC.

**Request**:
```protobuf
message GetStreamConfigRequest {
  string stream_id = 1;
}
```

**Response**:
```protobuf
message StreamConfig {
  string stream_id = 1;
  StreamKey primary_key = 2;
  repeated StreamKey backup_keys = 3;
  repeated Destination destinations = 4;
}
```

---

#### CreateStreamKey
Create a new stream key.

**Request**:
```protobuf
message CreateStreamKeyRequest {
  string stream_id = 1;
}
```

**Response**:
```protobuf
message StreamKey {
  string id = 1;
  string stream_id = 2;
  string key = 3;
  int64 created_at = 4;
}
```

---

#### AddDestination
Add a streaming destination via gRPC.

**Request**:
```protobuf
message AddDestinationRequest {
  string stream_id = 1;
  string platform = 2;
  string url = 3;
  string name = 4;
}
```

**Response**:
```protobuf
message Destination {
  string id = 1;
  string stream_id = 2;
  string platform = 3;
  string url = 4;
  string name = 5;
  int64 created_at = 6;
}
```

---

#### GetStreamStatus
Get stream status via gRPC.

**Request**:
```protobuf
message GetStreamStatusRequest {
  string stream_id = 1;
}
```

**Response**:
```protobuf
message StreamStatus {
  string stream_id = 1;
  bool is_active = 2;
  int64 connected_at = 3;
  int64 bytes_sent = 4;
  repeated DestinationStatus destinations = 5;
}

message DestinationStatus {
  string destination_id = 1;
  string platform = 2;
  bool connected = 3;
  int64 bytes_sent = 4;
  string last_error = 5;
}
```

---

## Error Codes

| Code | Meaning | Common Cause |
|------|---------|--------------|
| 400 | Bad Request | Missing/invalid required fields |
| 401 | Unauthorized | Missing/invalid JWT token |
| 403 | Forbidden | Feature limit exceeded (free tier) |
| 404 | Not Found | Resource (config/destination) not found |
| 409 | Conflict | Resource already exists (duplicate community_id) |
| 500 | Server Error | Database error, unhandled exception |
| 503 | Service Unavailable | Database connection failed |

---

## Stream URL Formats

### Twitch

**RTMP URL**: `rtmp://live.twitch.tv/app`
**Stream Key**: (from Twitch dashboard)
**Full Ingest**: `rtmp://live.twitch.tv/app/[stream-key]`

### YouTube

**RTMP URL**: `rtmp://a.rtmp.youtube.com/live2`
**Stream Key**: (from YouTube Studio)
**Full Ingest**: `rtmp://a.rtmp.youtube.com/live2/[stream-key]`

### Kick

**RTMP URL**: `rtmp://ingest.kick.com`
**Stream Key**: (from Kick channel settings)
**Full Ingest**: `rtmp://ingest.kick.com/[stream-key]`

### Custom RTMP

**RTMP URL**: Any valid RTMP server
**Stream Key**: Server-specific key
**Full Ingest**: `[RTMP URL]/[stream-key]`

### Module Ingest (OBS/Encoder)

**URL Format**: `rtmp://[MODULE_HOST]:[MODULE_PORT]/live/[STREAM_KEY]`

**Example**:
```
rtmp://waddlebot.penguintech.io:8092/live/secure-token-here
```

---

**Last Updated**: 2026-02-16
**Repository**: github.com/penguintechinc/waddlebot
