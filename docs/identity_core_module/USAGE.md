# Identity Core Module - Usage Guide

## Overview

This guide provides comprehensive documentation on using the Identity Core Module for cross-platform identity management, user authentication, and platform linking in Waddles.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Cross-Platform Identity Features](#cross-platform-identity-features)
3. [User Authentication](#user-authentication)
4. [Platform Linking](#platform-linking)
5. [Identity Lookups](#identity-lookups)
6. [API Key Management](#api-key-management)
7. [WebUI Usage](#webui-usage)
8. [gRPC Client Usage](#grpc-client-usage)
9. [Common Workflows](#common-workflows)
10. [Best Practices](#best-practices)

---

## Getting Started

### Prerequisites

- Waddles system running
- Identity Core Module deployed (REST API + gRPC)
- Database migrations applied
- Valid API key or user session

### Quick Start

**1. Check Service Health:**
```bash
curl http://localhost:8050/health
```

**Response:**
```json
{
  "status": "healthy",
  "module": "identity_core_module",
  "version": "2.0.0"
}
```

**2. Obtain Authentication:**

Option A - Login:
```bash
curl -X POST http://localhost:8050/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "YourPassword123!"
  }'
```

Option B - Use API Key:
```bash
# Set in header
X-API-Key: your-api-key-here
```

---

## Cross-Platform Identity Features

### Supported Platforms

The Identity Core Module supports linking identities from:

| Platform | Code | Identity Fields |
|----------|------|----------------|
| Twitch | `twitch` | user_id, username, email |
| Discord | `discord` | user_id, username#discriminator |
| YouTube | `youtube` | channel_id, channel_name |
| Kick | `kick` | user_id, username |
| TikTok | `tiktok` | user_id, username |

### Platform Identity Structure

Each platform identity contains:

```json
{
  "platform": "twitch",
  "platform_user_id": "123456789",
  "platform_username": "streamername",
  "platform_email": "user@example.com",
  "avatar_url": "https://cdn.example.com/avatar.png",
  "linked_at": "2025-01-01T00:00:00Z",
  "last_used": "2025-12-16T10:30:00Z",
  "is_primary": true
}
```

### Identity Graph

Users can link multiple platform identities to a single hub account:

```
Hub User: waddle_user (ID: 42)
├── Twitch: streamername (ID: 123456789) [PRIMARY]
├── Discord: username#1234 (ID: 987654321)
├── YouTube: My Channel (ID: UCxxx...)
└── Kick: kickstreamer (ID: 456789)
```

---

## User Authentication

### Register New Account

**Endpoint:** `POST /auth/register`

```bash
curl -X POST http://localhost:8050/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@example.com",
    "password": "SecurePassword123!",
    "username": "newusername"
  }'
```

**Response:**
```json
{
  "user_id": 42,
  "email": "newuser@example.com",
  "username": "newusername",
  "created_at": "2025-12-16T10:30:00Z",
  "message": "Account created successfully"
}
```

**Password Requirements:**
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one number
- At least one special character

---

### Login

**Endpoint:** `POST /auth/login`

```bash
curl -X POST http://localhost:8050/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePassword123!"
  }'
```

**Response:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user_id": 42,
  "username": "waddle_user",
  "expires_at": "2025-12-17T10:30:00Z"
}
```

**Using the Token:**
```bash
# Include in subsequent requests
curl -X GET http://localhost:8050/auth/profile \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

### View Profile

**Endpoint:** `GET /auth/profile`

```bash
curl -X GET http://localhost:8050/auth/profile \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "user_id": 42,
  "email": "user@example.com",
  "username": "waddle_user",
  "display_name": "Waddle User",
  "avatar_url": "https://cdn.example.com/avatar.png",
  "email_verified": true,
  "created_at": "2025-01-01T00:00:00Z",
  "last_login": "2025-12-16T10:30:00Z",
  "linked_platforms": ["twitch", "discord", "youtube"]
}
```

---

### Update Profile

**Endpoint:** `PUT /auth/profile`

```bash
curl -X PUT http://localhost:8050/auth/profile \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "display_name": "New Display Name",
    "bio": "I am a Waddles user",
    "website_url": "https://mywebsite.com",
    "location": "San Francisco, CA"
  }'
```

**Response:**
```json
{
  "success": true,
  "user_id": 42,
  "display_name": "New Display Name",
  "updated_at": "2025-12-16T10:45:00Z"
}
```

---

### Logout

**Endpoint:** `POST /auth/logout`

```bash
curl -X POST http://localhost:8050/auth/logout \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "success": true,
  "message": "Logged out successfully"
}
```

---

## Platform Linking

### Link Platform Identity

**Step 1: Initiate Link**

**Endpoint:** `POST /identity/link`

```bash
curl -X POST http://localhost:8050/identity/link \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "twitch",
    "platform_id": "123456789",
    "platform_username": "streamername"
  }'
```

**Response:**
```json
{
  "verification_id": "ver_abc123xyz",
  "verification_code": "WXYZ-1234",
  "expires_at": "2025-12-16T11:30:00Z",
  "message": "Verification code generated. Please verify within 1 hour."
}
```

**Step 2: Verify with Code**

The user will receive the verification code via the platform (e.g., Twitch chat command, Discord DM).

**Endpoint:** `POST /identity/verify`

```bash
curl -X POST http://localhost:8050/identity/verify \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "verification_code": "WXYZ-1234",
    "platform": "twitch"
  }'
```

**Response:**
```json
{
  "success": true,
  "user_id": 42,
  "platform": "twitch",
  "platform_user_id": "123456789",
  "platform_username": "streamername",
  "linked_at": "2025-12-16T10:45:00Z",
  "message": "Platform identity linked successfully"
}
```

---

### View Pending Verifications

**Endpoint:** `GET /identity/pending`

```bash
curl -X GET http://localhost:8050/identity/pending \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "pending_verifications": [
    {
      "verification_id": "ver_abc123",
      "platform": "youtube",
      "platform_username": "My Channel",
      "created_at": "2025-12-16T10:30:00Z",
      "expires_at": "2025-12-16T11:30:00Z",
      "status": "pending"
    }
  ]
}
```

---

### Resend Verification Code

**Endpoint:** `POST /identity/resend`

```bash
curl -X POST http://localhost:8050/identity/resend \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "verification_id": "ver_abc123"
  }'
```

**Response:**
```json
{
  "success": true,
  "verification_code": "ABCD-5678",
  "expires_at": "2025-12-16T11:45:00Z",
  "message": "Verification code resent"
}
```

---

### Unlink Platform Identity

**Endpoint:** `DELETE /identity/unlink`

```bash
curl -X DELETE http://localhost:8050/identity/unlink \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "twitch",
    "platform_id": "123456789"
  }'
```

**Response:**
```json
{
  "success": true,
  "message": "Platform identity unlinked successfully",
  "platform": "twitch",
  "unlinked_at": "2025-12-16T10:50:00Z"
}
```

---

## Identity Lookups

### Lookup by Hub User ID

**Endpoint:** `GET /identity/user/{user_id}`

```bash
curl -X GET http://localhost:8050/identity/user/42 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "user_id": 42,
  "username": "waddle_user",
  "display_name": "Waddle User",
  "identities": [
    {
      "platform": "twitch",
      "platform_user_id": "123456789",
      "platform_username": "streamername",
      "avatar_url": "https://cdn.twitch.tv/avatar.png",
      "linked_at": "2025-01-01T00:00:00Z",
      "last_used": "2025-12-16T10:30:00Z",
      "is_primary": true
    },
    {
      "platform": "discord",
      "platform_user_id": "987654321",
      "platform_username": "username#1234",
      "avatar_url": "https://cdn.discord.com/avatar.png",
      "linked_at": "2025-01-02T00:00:00Z",
      "last_used": "2025-12-15T14:20:00Z",
      "is_primary": false
    }
  ]
}
```

---

### Lookup by Platform Identity

**Endpoint:** `GET /identity/platform/{platform}/{platform_id}`

```bash
curl -X GET http://localhost:8050/identity/platform/twitch/123456789 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "user_id": 42,
  "username": "waddle_user",
  "display_name": "Waddle User",
  "platform": "twitch",
  "platform_user_id": "123456789",
  "platform_username": "streamername",
  "linked_at": "2025-01-01T00:00:00Z",
  "last_used": "2025-12-16T10:30:00Z"
}
```

**Use Case:** Find hub user from a platform message/event

```python
# Example: Incoming Twitch message
twitch_user_id = "123456789"

# Lookup hub user
response = requests.get(
    f"http://localhost:8050/identity/platform/twitch/{twitch_user_id}",
    headers={"Authorization": f"Bearer {token}"}
)

hub_user_id = response.json()["user_id"]
```

---

## API Key Management

### Create API Key

**Endpoint:** `POST /identity/api-keys`

```bash
curl -X POST http://localhost:8050/identity/api-keys \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production Bot Key",
    "expires_in_days": 365
  }'
```

**Response:**
```json
{
  "api_key": "wbt_1234567890abcdef1234567890abcdef",
  "key_id": "key_xyz789",
  "name": "Production Bot Key",
  "created_at": "2025-12-16T10:30:00Z",
  "expires_at": "2026-12-16T10:30:00Z",
  "message": "Store this key securely. It will not be shown again."
}
```

**Important:** Save the `api_key` immediately. It cannot be retrieved later.

---

### List API Keys

**Endpoint:** `GET /identity/api-keys`

```bash
curl -X GET http://localhost:8050/identity/api-keys \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "api_keys": [
    {
      "key_id": "key_xyz789",
      "name": "Production Bot Key",
      "created_at": "2025-12-16T10:30:00Z",
      "expires_at": "2026-12-16T10:30:00Z",
      "last_used": "2025-12-16T10:45:00Z",
      "last_used_ip": "192.168.1.100"
    },
    {
      "key_id": "key_abc456",
      "name": "Development Key",
      "created_at": "2025-12-01T00:00:00Z",
      "expires_at": "2025-12-31T23:59:59Z",
      "last_used": null,
      "last_used_ip": null
    }
  ]
}
```

---

### Regenerate API Key

**Endpoint:** `POST /identity/api-keys/{key_id}/regenerate`

```bash
curl -X POST http://localhost:8050/identity/api-keys/key_xyz789/regenerate \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "api_key": "wbt_newkey9876543210fedcba9876543210",
  "key_id": "key_xyz789",
  "name": "Production Bot Key",
  "regenerated_at": "2025-12-16T11:00:00Z",
  "expires_at": "2026-12-16T11:00:00Z",
  "message": "Old key is now invalid. Store new key securely."
}
```

---

### Revoke API Key

**Endpoint:** `DELETE /identity/api-keys/{key_id}`

```bash
curl -X DELETE http://localhost:8050/identity/api-keys/key_xyz789 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "success": true,
  "message": "API key revoked successfully",
  "key_id": "key_xyz789",
  "revoked_at": "2025-12-16T11:05:00Z"
}
```

---

## WebUI Usage

### Admin Hub - Identity Management

Access the Identity Management section in the Waddles Admin Hub:

**URL:** `https://your-waddlebot-instance/admin/identity`

#### Viewing Linked Identities

1. Navigate to **Settings** > **Identity Management**
2. View all linked platform accounts
3. See connection status, last used date

**Screenshot View:**
```
┌─────────────────────────────────────────────────┐
│ Identity Management                              │
├─────────────────────────────────────────────────┤
│                                                  │
│ Linked Platforms:                                │
│                                                  │
│ ✓ Twitch                                        │
│   streamername (ID: 123456789)                  │
│   Last used: Dec 16, 2025 10:30 AM              │
│   [Unlink] [Refresh]                            │
│                                                  │
│ ✓ Discord                                       │
│   username#1234 (ID: 987654321)                 │
│   Last used: Dec 15, 2025 2:20 PM               │
│   [Unlink] [Refresh]                            │
│                                                  │
│ + Link New Platform                             │
│   [Twitch] [Discord] [YouTube] [Kick]           │
│                                                  │
└─────────────────────────────────────────────────┘
```

---

#### Linking New Platform (WebUI)

1. Click **"Link New Platform"**
2. Select platform (e.g., YouTube)
3. Click **"Connect YouTube Account"**
4. Redirected to YouTube OAuth
5. Authorize Waddles
6. Redirected back with success message

**OAuth Flow:**
```
[Waddles] → [Platform OAuth] → [User Authorizes] → [Callback] → [Linked!]
```

---

#### Managing API Keys (WebUI)

1. Navigate to **Settings** > **API Keys**
2. View all active API keys
3. Create new keys
4. Regenerate or revoke keys

**API Keys View:**
```
┌─────────────────────────────────────────────────┐
│ API Keys                                         │
├─────────────────────────────────────────────────┤
│                                                  │
│ Active Keys:                                     │
│                                                  │
│ Production Bot Key                               │
│ Created: Dec 16, 2025                           │
│ Expires: Dec 16, 2026                           │
│ Last used: 2 minutes ago                        │
│ [Regenerate] [Revoke]                           │
│                                                  │
│ Development Key                                  │
│ Created: Dec 1, 2025                            │
│ Expires: Dec 31, 2025                           │
│ Never used                                       │
│ [Regenerate] [Revoke]                           │
│                                                  │
│ [+ Create New API Key]                          │
│                                                  │
└─────────────────────────────────────────────────┘
```

---

## gRPC Client Usage

### Python Client

**Install Dependencies:**
```bash
pip install grpcio grpcio-tools
```

**Generate Client Stubs:**
```bash
cd /home/penguin/code/Waddles
python -m grpc_tools.protoc \
  -I./libs/grpc_protos \
  --python_out=. \
  --grpc_python_out=. \
  ./libs/grpc_protos/identity.proto \
  ./libs/grpc_protos/common.proto
```

**Client Code:**
```python
import grpc
import identity_pb2
import identity_pb2_grpc

# Create channel
channel = grpc.insecure_channel('localhost:50030')
stub = identity_pb2_grpc.IdentityServiceStub(channel)

# Lookup identity
request = identity_pb2.LookupIdentityRequest(
    token='your-auth-token',
    platform='twitch',
    platform_user_id='123456789'
)

response = stub.LookupIdentity(request)

if response.success:
    print(f"Hub User ID: {response.hub_user_id}")
    print(f"Username: {response.username}")
    print(f"Linked Platforms: {len(response.linked_platforms)}")

    for platform in response.linked_platforms:
        print(f"  - {platform.platform}: {platform.platform_username}")
else:
    print(f"Error: {response.error.message}")
```

---

### Go Client

**Install Dependencies:**
```bash
go get google.golang.org/grpc
go get google.golang.org/protobuf
```

**Generate Client Stubs:**
```bash
protoc \
  -I /home/penguin/code/Waddles/libs/grpc_protos \
  --go_out=. \
  --go-grpc_out=. \
  identity.proto common.proto
```

**Client Code:**
```go
package main

import (
    "context"
    "log"

    "google.golang.org/grpc"
    pb "your/package/path/identity"
)

func main() {
    // Connect to server
    conn, err := grpc.Dial("localhost:50030", grpc.WithInsecure())
    if err != nil {
        log.Fatalf("Failed to connect: %v", err)
    }
    defer conn.Close()

    client := pb.NewIdentityServiceClient(conn)

    // Lookup identity
    req := &pb.LookupIdentityRequest{
        Token:          "your-auth-token",
        Platform:       "twitch",
        PlatformUserId: "123456789",
    }

    resp, err := client.LookupIdentity(context.Background(), req)
    if err != nil {
        log.Fatalf("Error: %v", err)
    }

    if resp.Success {
        log.Printf("Hub User ID: %d", resp.HubUserId)
        log.Printf("Username: %s", resp.Username)
        log.Printf("Linked Platforms: %d", len(resp.LinkedPlatforms))
    } else {
        log.Printf("Error: %s", resp.Error.Message)
    }
}
```

---

### Node.js Client

**Install Dependencies:**
```bash
npm install @grpc/grpc-js @grpc/proto-loader
```

**Client Code:**
```javascript
const grpc = require('@grpc/grpc-js');
const protoLoader = require('@grpc/proto-loader');
const path = require('path');

// Load proto file
const PROTO_PATH = path.join(__dirname, 'libs/grpc_protos/identity.proto');
const packageDefinition = protoLoader.loadSync(PROTO_PATH, {
  keepCase: true,
  longs: String,
  enums: String,
  defaults: true,
  oneofs: true
});

const identityProto = grpc.loadPackageDefinition(packageDefinition).waddlebot.identity;

// Create client
const client = new identityProto.IdentityService(
  'localhost:50030',
  grpc.credentials.createInsecure()
);

// Lookup identity
const request = {
  token: 'your-auth-token',
  platform: 'twitch',
  platform_user_id: '123456789'
};

client.LookupIdentity(request, (error, response) => {
  if (error) {
    console.error('Error:', error);
    return;
  }

  if (response.success) {
    console.log('Hub User ID:', response.hub_user_id);
    console.log('Username:', response.username);
    console.log('Linked Platforms:', response.linked_platforms.length);

    response.linked_platforms.forEach(platform => {
      console.log(`  - ${platform.platform}: ${platform.platform_username}`);
    });
  } else {
    console.error('Error:', response.error.message);
  }
});
```

---

## Common Workflows

### Workflow 1: New User Registration with Platform Link

```bash
# 1. Register account
TOKEN=$(curl -s -X POST http://localhost:8050/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@example.com",
    "password": "SecurePass123!",
    "username": "newuser"
  }' | jq -r '.token')

# 2. Link Twitch account
VERIFY_CODE=$(curl -s -X POST http://localhost:8050/identity/link \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "twitch",
    "platform_id": "123456789",
    "platform_username": "twitchuser"
  }' | jq -r '.verification_code')

echo "Verification code: $VERIFY_CODE"

# 3. User verifies in Twitch chat: !verify WXYZ-1234

# 4. Complete verification
curl -X POST http://localhost:8050/identity/verify \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"verification_code\": \"$VERIFY_CODE\",
    \"platform\": \"twitch\"
  }"
```

---

### Workflow 2: Cross-Platform User Lookup

```python
import requests

# Incoming message from Twitch
twitch_user_id = "123456789"
message = "!points"

# 1. Lookup hub user from Twitch ID
response = requests.get(
    f"http://localhost:8050/identity/platform/twitch/{twitch_user_id}",
    headers={"X-API-Key": API_KEY}
)

hub_user_id = response.json()["user_id"]

# 2. Get all linked identities
response = requests.get(
    f"http://localhost:8050/identity/user/{hub_user_id}",
    headers={"X-API-Key": API_KEY}
)

identities = response.json()["identities"]

# 3. Check if user is also on Discord
discord_identity = next(
    (i for i in identities if i["platform"] == "discord"),
    None
)

if discord_identity:
    print(f"User is also on Discord: {discord_identity['platform_username']}")
    # Can send notifications to both platforms
```

---

### Workflow 3: Multi-Platform Notification

```python
# User earned achievement - notify on all platforms

def notify_achievement(hub_user_id, achievement):
    # Get all linked platforms
    response = requests.get(
        f"http://localhost:8050/identity/user/{hub_user_id}",
        headers={"X-API-Key": API_KEY}
    )

    identities = response.json()["identities"]

    # Send notification to each platform
    for identity in identities:
        platform = identity["platform"]
        platform_user_id = identity["platform_user_id"]

        if platform == "twitch":
            send_twitch_message(platform_user_id, f"Achievement unlocked: {achievement}!")
        elif platform == "discord":
            send_discord_dm(platform_user_id, f"🏆 Achievement: {achievement}")
        elif platform == "youtube":
            send_youtube_community_post(platform_user_id, achievement)
```

---

## Best Practices

### Security Best Practices

1. **Token Storage**
   - Never store tokens in client-side JavaScript
   - Use secure HTTP-only cookies for web apps
   - Store API keys in environment variables
   - Rotate keys regularly

2. **Authentication**
   - Always use HTTPS in production
   - Implement token refresh before expiry
   - Logout on sensitive operations
   - Monitor for unusual authentication patterns

3. **Platform Linking**
   - Verify platform ownership before linking
   - Use time-limited verification codes
   - Allow users to unlink platforms
   - Audit link/unlink events

---

### Performance Best Practices

1. **Caching**
   - Cache identity lookups client-side (5 min TTL)
   - Batch identity lookups when possible
   - Use gRPC for high-frequency lookups

2. **API Usage**
   - Use gRPC for service-to-service calls
   - Use REST for user-facing operations
   - Implement exponential backoff for retries
   - Respect rate limits

---

### Integration Best Practices

1. **Error Handling**
   ```python
   try:
       response = requests.get(identity_endpoint)
       response.raise_for_status()
       data = response.json()
   except requests.exceptions.HTTPError as e:
       if e.response.status_code == 404:
           # Identity not found - handle gracefully
           logger.info(f"Identity not found for {platform_user_id}")
       else:
           # Other error - retry or alert
           logger.error(f"Identity lookup failed: {e}")
   except requests.exceptions.Timeout:
       # Timeout - retry with backoff
       logger.warning("Identity service timeout - retrying")
   ```

2. **Validation**
   - Validate platform IDs before lookup
   - Check token expiry before using
   - Verify platform is supported
   - Sanitize user input

3. **Logging**
   - Log all identity operations
   - Include user_id and platform in logs
   - Monitor failed verifications
   - Track link/unlink events

---

## Troubleshooting

### Common Issues

**Issue:** "Token expired"
```json
{"error": {"code": "UNAUTHORIZED", "message": "Token expired"}}
```
**Solution:** Refresh token or re-login

**Issue:** "Platform identity already linked"
```json
{"error": {"code": "CONFLICT", "message": "Identity already linked to another account"}}
```
**Solution:** User must unlink from other account first

**Issue:** "Verification code expired"
```json
{"error": {"code": "NOT_FOUND", "message": "Verification not found or expired"}}
```
**Solution:** Request new verification code

---

## Additional Resources

- [API Reference](API.md)
- [Configuration Guide](CONFIGURATION.md)
- [Architecture Documentation](ARCHITECTURE.md)
- [Testing Guide](TESTING.md)
- [gRPC Integration Guide](/home/penguin/code/Waddles/core/identity_core_module/GRPC_INTEGRATION.md)
