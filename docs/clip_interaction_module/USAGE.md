# Clip Interaction Module - Usage Guide

Common workflows and integration patterns for using the Clip Interaction Module.

## Table of Contents

1. [Authentication Setup](#authentication-setup)
2. [Basic Clip Workflows](#basic-clip-workflows)
3. [Highlight Management](#highlight-management)
4. [Reel Creation](#reel-creation)
5. [OBS Integration](#obs-integration)
6. [Error Handling](#error-handling)
7. [Best Practices](#best-practices)

## Authentication Setup

All requests require a valid JWT token from the core-api module.

### Getting a Token

```bash
# Get token via core-api login endpoint
curl -X POST http://core-api:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "streamer@example.com",
    "password": "secure_password"
  }' | jq -r '.token'
```

### Using Token in Requests

```bash
# Store token for reuse
TOKEN=$(curl -s -X POST http://core-api:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "streamer@example.com",
    "password": "secure_password"
  }' | jq -r '.token')

# Use in subsequent requests
curl http://localhost:8098/api/v1/clips/community-123 \
  -H "Authorization: Bearer $TOKEN"
```

### Token Expiration

Tokens expire after 24 hours. Refresh tokens are available via:

```bash
curl -X POST http://core-api:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "your-refresh-token"}'
```

## Basic Clip Workflows

### Creating a Clip via Twitch Proxy

The module proxies clip creation to the action-twitch service. This workflow assumes you have a Twitch broadcast ID.

```bash
COMMUNITY_ID="550e8400-e29b-41d4-a716-446655440000"
BROADCAST_ID="twitch_broadcast_12345"

curl -X POST http://localhost:8098/api/v1/clips/$COMMUNITY_ID/create \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "broadcast_id": "'$BROADCAST_ID'",
    "title": "Incredible Rampage!",
    "language": "en",
    "has_delay": false
  }'
```

**Response:**

```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "status": "created",
  "clip_id": "SomeClip123",
  "clip_url": "https://twitch.tv/clip/SomeClip123",
  "title": "Incredible Rampage!",
  "created_at": "2026-02-24T14:30:00Z"
}
```

### Bookmarking a Clip

Save a clip to your community's collection:

```bash
COMMUNITY_ID="550e8400-e29b-41d4-a716-446655440000"

curl -X POST http://localhost:8098/api/v1/clips/$COMMUNITY_ID/bookmark \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "clip_id": "SomeClip123",
    "clip_url": "https://twitch.tv/clip/SomeClip123",
    "title": "Incredible Rampage!",
    "game": "Valorant",
    "tags": ["ace", "highlight", "5k"]
  }'
```

**Response:**

```json
{
  "id": "770e8400-e29b-41d4-a716-446655440002",
  "community_id": "550e8400-e29b-41d4-a716-446655440000",
  "clip_id": "SomeClip123",
  "clip_url": "https://twitch.tv/clip/SomeClip123",
  "title": "Incredible Rampage!",
  "game": "Valorant",
  "tags": ["ace", "highlight", "5k"],
  "bookmarked_by": "880e8400-e29b-41d4-a716-446655440003",
  "is_highlight": false,
  "created_at": "2026-02-24T14:32:00Z"
}
```

### Listing Bookmarked Clips

Retrieve all clips for a community with optional filtering:

```bash
COMMUNITY_ID="550e8400-e29b-41d4-a716-446655440000"

# Get all clips
curl http://localhost:8098/api/v1/clips/$COMMUNITY_ID \
  -H "Authorization: Bearer $TOKEN"

# Filter by game
curl "http://localhost:8098/api/v1/clips/$COMMUNITY_ID?game=Valorant&limit=10" \
  -H "Authorization: Bearer $TOKEN"

# Filter by tag
curl "http://localhost:8098/api/v1/clips/$COMMUNITY_ID?tag=clutch&limit=20" \
  -H "Authorization: Bearer $TOKEN"

# Paginate results
curl "http://localhost:8098/api/v1/clips/$COMMUNITY_ID?limit=50&offset=50" \
  -H "Authorization: Bearer $TOKEN"
```

## Highlight Management

### Marking a Clip as Highlight

Flag a clip for inclusion in highlight reels:

```bash
COMMUNITY_ID="550e8400-e29b-41d4-a716-446655440000"
CLIP_ID="770e8400-e29b-41d4-a716-446655440002"

curl -X POST http://localhost:8098/api/v1/clips/$COMMUNITY_ID/$CLIP_ID/highlight \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Response:**

```json
{
  "id": "770e8400-e29b-41d4-a716-446655440002",
  "is_highlight": true,
  "updated_at": "2026-02-24T14:35:00Z"
}
```

### Getting Only Highlights

```bash
COMMUNITY_ID="550e8400-e29b-41d4-a716-446655440000"

curl "http://localhost:8098/api/v1/clips/$COMMUNITY_ID?highlights_only=true&limit=20" \
  -H "Authorization: Bearer $TOKEN"
```

## Reel Creation

### Creating a Highlight Reel

Combine multiple highlighted clips into a reel:

```bash
COMMUNITY_ID="550e8400-e29b-41d4-a716-446655440000"

curl -X POST http://localhost:8098/api/v1/reels/$COMMUNITY_ID \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Best Plays - Week 1",
    "description": "Top highlights from week 1 of the tournament",
    "clip_ids": [
      "770e8400-e29b-41d4-a716-446655440002",
      "880e8400-e29b-41d4-a716-446655440004",
      "990e8400-e29b-41d4-a716-446655440006"
    ]
  }'
```

**Response:**

```json
{
  "id": "aa0e8400-e29b-41d4-a716-446655440008",
  "community_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Best Plays - Week 1",
  "description": "Top highlights from week 1 of the tournament",
  "clip_ids": [
    "770e8400-e29b-41d4-a716-446655440002",
    "880e8400-e29b-41d4-a716-446655440004",
    "990e8400-e29b-41d4-a716-446655440006"
  ],
  "created_by": "880e8400-e29b-41d4-a716-446655440003",
  "is_published": false,
  "created_at": "2026-02-24T15:00:00Z"
}
```

### Retrieving a Reel

Get reel details with full clip metadata:

```bash
COMMUNITY_ID="550e8400-e29b-41d4-a716-446655440000"
REEL_ID="aa0e8400-e29b-41d4-a716-446655440008"

curl http://localhost:8098/api/v1/reels/$COMMUNITY_ID/$REEL_ID \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**

```json
{
  "id": "aa0e8400-e29b-41d4-a716-446655440008",
  "community_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Best Plays - Week 1",
  "description": "Top highlights from week 1 of the tournament",
  "clips": [
    {
      "id": "770e8400-e29b-41d4-a716-446655440002",
      "clip_id": "SomeClip123",
      "title": "Incredible Rampage!",
      "clip_url": "https://twitch.tv/clip/SomeClip123"
    }
  ],
  "created_by": "880e8400-e29b-41d4-a716-446655440003",
  "is_published": false,
  "created_at": "2026-02-24T15:00:00Z"
}
```

### Publishing a Reel

Mark a reel as published for sharing:

```bash
COMMUNITY_ID="550e8400-e29b-41d4-a716-446655440000"
REEL_ID="aa0e8400-e29b-41d4-a716-446655440008"

curl -X PUT http://localhost:8098/api/v1/reels/$COMMUNITY_ID/$REEL_ID/publish \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```

## OBS Integration

### Fetching Overlay Data

Get the 5 most recent highlighted clips for OBS display:

```bash
COMMUNITY_ID="550e8400-e29b-41d4-a716-446655440000"

curl http://localhost:8098/api/v1/overlay/$COMMUNITY_ID \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**

```json
{
  "community_id": "550e8400-e29b-41d4-a716-446655440000",
  "highlights": [
    {
      "id": "770e8400-e29b-41d4-a716-446655440002",
      "title": "Incredible Rampage!",
      "clip_url": "https://twitch.tv/clip/SomeClip123",
      "created_at": "2026-02-24T14:32:00Z"
    },
    {
      "id": "880e8400-e29b-41d4-a716-446655440004",
      "title": "Clutch Defuse",
      "clip_url": "https://twitch.tv/clip/AnotherClip456",
      "created_at": "2026-02-24T14:15:00Z"
    }
  ],
  "total": 12,
  "last_updated": "2026-02-24T15:10:00Z"
}
```

### Integration with OBS

Use this endpoint in OBS's Browser Source for live overlay:

1. Open OBS → Add Source → Browser
2. Configure Browser Source:
   - **Width**: 1920
   - **Height**: 1080
   - **URL**: Set to a custom overlay HTML page
3. In your overlay HTML, fetch and safely render clip data:

```javascript
// Safe overlay integration example
function updateOverlay() {
  const COMMUNITY_ID = "YOUR_COMMUNITY_ID";
  const TOKEN = "YOUR_TOKEN";

  fetch(`http://localhost:8098/api/v1/overlay/${COMMUNITY_ID}`, {
    headers: { 'Authorization': `Bearer ${TOKEN}` }
  })
  .then(r => r.json())
  .then(data => {
    if (data.highlights && data.highlights.length > 0) {
      const latest = data.highlights[0];
      const titleElement = document.getElementById('clip-title');
      // Use textContent to safely set text without HTML parsing
      titleElement.textContent = latest.title;
    }
  });
}

// Update every 5 seconds
setInterval(updateOverlay, 5000);
```

## Error Handling

### Handling Common Errors

**Duplicate Bookmark (409 Conflict)**

```bash
curl -X POST http://localhost:8098/api/v1/clips/$COMMUNITY_ID/bookmark \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "clip_id": "DuplicateClip",
    "clip_url": "...",
    "title": "..."
  }'
# Returns 409 if this clip is already bookmarked
```

**Solution**: Check if clip exists before bookmarking:

```bash
curl "http://localhost:8098/api/v1/clips/$COMMUNITY_ID?highlights_only=false" \
  -H "Authorization: Bearer $TOKEN" | jq '.clips[] | select(.clip_id == "DuplicateClip")'
```

**Missing Authorization (401 Unauthorized)**

Always include the Authorization header with a valid token:

```bash
curl http://localhost:8098/api/v1/clips/$COMMUNITY_ID \
  -H "Authorization: Bearer $TOKEN"  # Required!
```

**Invalid Community (404 Not Found)**

Ensure the community ID is correct and the user has access:

```bash
# Verify community exists
curl http://core-api:8000/api/v1/communities/$COMMUNITY_ID \
  -H "Authorization: Bearer $TOKEN"
```

## Best Practices

### 1. Cache Token Locally

Store tokens with expiration time to avoid repeated auth calls:

```bash
#!/bin/bash
TOKEN_FILE="/tmp/clip_module_token"
TOKEN_EXPIRY_FILE="/tmp/clip_module_token_expiry"

get_token() {
  if [[ -f $TOKEN_FILE && -f $TOKEN_EXPIRY_FILE ]]; then
    EXPIRY=$(cat $TOKEN_EXPIRY_FILE)
    NOW=$(date +%s)
    if [[ $NOW -lt $EXPIRY ]]; then
      cat $TOKEN_FILE
      return
    fi
  fi

  TOKEN=$(curl -s -X POST http://core-api:8000/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"user@example.com","password":"pass"}' | jq -r '.token')

  echo $TOKEN > $TOKEN_FILE
  echo $(($(date +%s) + 86400)) > $TOKEN_EXPIRY_FILE
  echo $TOKEN
}

TOKEN=$(get_token)
```

### 2. Batch Operations for Reels

When creating reels with many clips, verify all clip IDs first:

```bash
# Validate all clips exist before reel creation
for CLIP_ID in "${CLIP_IDS[@]}"; do
  curl "http://localhost:8098/api/v1/clips/$COMMUNITY_ID" \
    -H "Authorization: Bearer $TOKEN" | jq --arg cid "$CLIP_ID" \
    '.clips[] | select(.id == $cid) | .id' || echo "Missing: $CLIP_ID"
done
```

### 3. Use Filtering for Large Collections

For communities with hundreds of clips, always use pagination:

```bash
COMMUNITY_ID="550e8400-e29b-41d4-a716-446655440000"
LIMIT=50
OFFSET=0

while true; do
  curl "http://localhost:8098/api/v1/clips/$COMMUNITY_ID?limit=$LIMIT&offset=$OFFSET" \
    -H "Authorization: Bearer $TOKEN" | jq '.clips[]' || break

  OFFSET=$((OFFSET + LIMIT))
  # Add your processing logic here
done
```

### 4. Handle Transient Failures

Implement retry logic for external service calls:

```bash
retry_curl() {
  local max_attempts=3
  local attempt=1

  while [[ $attempt -le $max_attempts ]]; do
    if curl "$@"; then
      return 0
    fi
    echo "Attempt $attempt failed, retrying..."
    sleep $((attempt * 2))
    ((attempt++))
  done

  return 1
}

retry_curl http://localhost:8098/api/v1/clips/$COMMUNITY_ID \
  -H "Authorization: Bearer $TOKEN"
```

### 5. Tag Naming Convention

Use consistent tag naming for searchability:

```
- Lowercase only
- Use hyphens for multi-word tags
- Examples: "1v5-clutch", "eco-round", "post-plant", "site-execute"
```

### 6. Reel Organization Strategy

Structure reels by timeframe and theme:

```
- "Month-Year" reels (e.g., "February-2026")
- Game-specific reels (e.g., "Valorant-Highlights")
- Tournament reels (e.g., "LAN-2026-Grand-Finals")
```
