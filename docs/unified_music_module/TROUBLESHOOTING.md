# Unified Music Module Troubleshooting Guide

**Module**: `unified_music_module`
**Version**: 1.0.0

---

## Table of Contents

1. [Common Issues](#common-issues)
2. [OAuth Authentication Issues](#oauth-authentication-issues)
3. [Playback Problems](#playback-problems)
4. [Provider Errors](#provider-errors)
5. [Queue Issues](#queue-issues)
6. [Radio Streaming Issues](#radio-streaming-issues)
7. [Performance Issues](#performance-issues)
8. [Debugging Tools](#debugging-tools)
9. [Error Codes Reference](#error-codes-reference)

---

## Common Issues

### Service Won't Start

**Symptoms**: Service fails to start or crashes immediately

**Possible Causes**:
1. Missing environment variables
2. Redis connection failure
3. Port already in use
4. Missing dependencies

**Solutions**:

```bash
# Check environment variables
env | grep -E '(SPOTIFY|YOUTUBE|SOUNDCLOUD|REDIS)'

# Verify required variables are set
if [ -z "$REDIS_URL" ]; then
    echo "ERROR: REDIS_URL not set"
fi

# Check port availability
lsof -i :8051
# If in use, kill process or change port

# Install dependencies
pip install -r requirements.txt

# Check Redis connection
redis-cli -u $REDIS_URL ping
# Should return: PONG

# View service logs
docker logs unified-music-module -f
```

---

### Health Check Fails

**Symptoms**: `/health` endpoint returns 503 or times out

**Possible Causes**:
1. Provider authentication failures
2. Redis disconnected
3. Service overloaded

**Solutions**:

```bash
# Check detailed health
curl http://localhost:8051/healthz | jq

# Expected output:
{
  "status": "healthy",
  "checks": {
    "redis": {"status": "healthy", "latency_ms": 2},
    "spotify": {"status": "healthy", "authenticated": true},
    "youtube": {"status": "healthy", "authenticated": true}
  }
}

# If Redis unhealthy:
docker restart redis
# Or check Redis logs:
docker logs redis -f

# If provider unhealthy, re-authenticate:
# See OAuth Authentication Issues section
```

---

## OAuth Authentication Issues

### Spotify Authentication Failed

**Symptoms**:
- "Not authenticated" errors
- 401 responses from Spotify API
- Token refresh failures

**Error Messages**:
```
SpotifyAuthError: Failed to exchange code
SpotifyAuthError: Failed to refresh token
SpotifyAuthError: Not authenticated. Call authenticate() first.
```

**Solutions**:

**1. Verify Credentials**
```bash
# Check environment variables
echo $SPOTIFY_CLIENT_ID
echo $SPOTIFY_CLIENT_SECRET
echo $SPOTIFY_REDIRECT_URI

# Ensure redirect URI matches exactly in Spotify app settings
# https://developer.spotify.com/dashboard
```

**2. Re-authenticate**
```python
from providers.spotify_provider import SpotifyProvider

spotify = SpotifyProvider()

# Get new auth URL
auth_url = spotify.get_auth_url(state="random_state_123")
print(f"Visit: {auth_url}")

# After user authorizes, exchange code
await spotify.authenticate({"code": "authorization_code_from_callback"})
```

**3. Check Token Expiration**
```python
# Tokens are auto-refreshed 5 minutes before expiry
# If refresh fails, re-authenticate

is_auth = await spotify.is_authenticated()
if not is_auth:
    # Re-authenticate
    pass
```

**4. Verify Scopes**
```python
# Ensure all required scopes are granted
SCOPES = [
    "user-read-playback-state",
    "user-modify-playback-state",
    "user-read-currently-playing",
    "playlist-read-private",
    "playlist-read-collaborative",
    "user-library-read",
]
```

---

### YouTube API Quota Exceeded

**Symptoms**:
- Search fails with 403 error
- "Quota exceeded" error message

**Error Messages**:
```
YouTubeAPIError: YouTube API error: 403 - quotaExceeded
```

**Solutions**:

**1. Check Quota Usage**
- Visit [Google Cloud Console](https://console.cloud.google.com/)
- Navigate to: APIs & Services → YouTube Data API v3 → Quotas
- Default quota: 10,000 units/day
- Search costs: 100 units per request

**2. Request Quota Increase**
- Go to quota page
- Click "Request quota increase"
- Justify usage (e.g., "Music bot for 1000 users")

**3. Reduce API Calls**
```python
# Cache search results
# Use larger limits to reduce total requests
results = await youtube.search(query, limit=50)  # Get 50 at once

# Implement rate limiting
import asyncio
await asyncio.sleep(1)  # 1 second between searches
```

**4. Use Alternative Provider**
```python
# Fallback to SoundCloud or Spotify
try:
    results = await youtube.search(query)
except YouTubeAPIError:
    # Fallback to Spotify
    results = await spotify.search(query)
```

---

### SoundCloud OAuth Issues

**Symptoms**:
- Authentication fails
- "Invalid client" error
- Token not persisting

**Solutions**:

**1. Verify App Registration**
```bash
# Check credentials
echo $SOUNDCLOUD_CLIENT_ID
echo $SOUNDCLOUD_CLIENT_SECRET

# Ensure app is approved by SoundCloud
# Some features require app approval
```

**2. Use Non-Expiring Tokens**
```python
# SoundCloud supports non-expiring tokens with 'non-expiring' scope
SCOPES = ["non-expiring"]

# Token may not have refresh_token
# That's normal for non-expiring tokens
```

---

## Playback Problems

### Spotify: No Active Device

**Symptoms**:
- "No active device found" error
- Playback commands fail with 404

**Error Messages**:
```
SpotifyAPIError: API request failed: No active device found
```

**Solutions**:

**1. List Available Devices**
```python
devices = await spotify.get_devices()
for device in devices:
    print(f"{device['name']} - Active: {device['is_active']}")
```

**2. Set Active Device**
```python
# Option 1: Set via API
if devices:
    device_id = devices[0]['id']
    await spotify.set_device(device_id)

# Option 2: Open Spotify app manually
# Start playing any song to activate device
```

**3. Transfer Playback**
```python
# Transfer to specific device
await spotify.set_device(device_id)
# Then start playback
await spotify.play(track_id)
```

---

### YouTube Playback Not Working

**Symptoms**:
- Track shows as playing but no audio
- Browser source not loading

**Solutions**:

**YouTube uses browser source for playback, not direct API control**

**1. Verify Browser Source Integration**
```bash
# Check browser source URL is set
echo $BROWSER_SOURCE_URL

# Test browser source endpoint
curl http://browser-source:8050/health
```

**2. Check Browser Source Logs**
```bash
docker logs browser-source -f
# Look for now-playing updates
```

**3. Manual Browser Source Test**
```html
<!-- Test iframe embed -->
<iframe
  width="560"
  height="315"
  src="https://www.youtube.com/embed/dQw4w9WgXcQ?autoplay=1"
  frameborder="0"
  allow="autoplay; encrypted-media"
  allowfullscreen>
</iframe>
```

---

### Track Skips Immediately

**Symptoms**:
- Track marked as playing but skips instantly
- Provider play() returns false

**Solutions**:

**1. Check Provider Health**
```python
healthy = await provider.health_check()
if not healthy:
    print("Provider unhealthy!")
```

**2. Verify Track Exists**
```python
track = await provider.get_track(track_id)
if not track:
    print("Track not found or unavailable")
```

**3. Check Queue Status**
```python
# Ensure track is in queue
queue_items = await queue.get_queue(community_id)
if not queue_items:
    print("Queue is empty!")
```

---

## Provider Errors

### Spotify Rate Limiting

**Symptoms**:
- 429 (Too Many Requests) errors
- Requests slow down significantly

**Solutions**:

```python
# Implement exponential backoff
import asyncio

async def retry_with_backoff(func, max_retries=3):
    for i in range(max_retries):
        try:
            return await func()
        except SpotifyAPIError as e:
            if '429' in str(e):
                wait_time = 2 ** i
                await asyncio.sleep(wait_time)
            else:
                raise
    raise Exception("Max retries exceeded")

# Use:
result = await retry_with_backoff(
    lambda: spotify.search(query)
)
```

---

### YouTube API Errors

**Common Error Codes**:

| Code | Error | Solution |
|------|-------|----------|
| 400 | Bad Request | Check query parameters |
| 403 | Forbidden / Quota Exceeded | Request quota increase |
| 404 | Not Found | Video deleted or private |
| 500 | Server Error | Retry after delay |

**Solutions**:

```python
try:
    track = await youtube.get_track(video_id)
except YouTubeAPIError as e:
    if '403' in str(e):
        # Quota exceeded
        print("Quota exceeded, try tomorrow")
    elif '404' in str(e):
        # Video not found
        print("Video deleted or private")
    else:
        # Other error
        print(f"Error: {e}")
```

---

### SoundCloud Stream URL Expired

**Symptoms**:
- Playback fails after some time
- "Stream URL invalid" error

**Solutions**:

```python
# Re-fetch stream URL before playback
async def play_soundcloud_track(track_id, soundcloud):
    # Get fresh stream URL
    stream_url = await soundcloud.get_stream_url(track_id)

    if not stream_url:
        # Fallback: re-authenticate
        await soundcloud.refresh_access_token()
        stream_url = await soundcloud.get_stream_url(track_id)

    return stream_url
```

---

## Queue Issues

### Queue Not Persisting

**Symptoms**:
- Queue cleared after restart
- Items disappear after adding

**Solutions**:

**1. Verify Redis Connection**
```bash
# Check Redis is running
redis-cli ping

# Check connection from service
redis-cli -u $REDIS_URL ping
```

**2. Check TTL Settings**
```bash
# View queue TTL
redis-cli -u $REDIS_URL TTL music_queue:1:queue

# If -1, key has no expiry
# If -2, key doesn't exist
# Otherwise, seconds until expiry
```

**3. Check Fallback Mode**
```python
# If Redis unavailable, uses in-memory fallback
# Data lost on restart
queue = UnifiedQueue(
    redis_url=redis_url,
    enable_fallback=True  # Fallback enabled
)

# Check connection status
if queue._fallback_enabled:
    print("WARNING: Using in-memory fallback!")
```

---

### Votes Not Working

**Symptoms**:
- Vote count doesn't change
- Queue doesn't reorder

**Solutions**:

**1. Check User Already Voted**
```python
# Users can only vote once per track
# Check voters list
item = queue_items[0]
if user_id in item.voters:
    print("User already voted!")
```

**2. Manually Reorder Queue**
```python
# Votes update item, but queue position doesn't auto-reorder
# Call reorder_by_votes() to apply vote ordering
await queue.reorder_by_votes(community_id)
```

---

### Queue Position Wrong

**Symptoms**:
- Track position doesn't match expected order
- Gaps in position numbers

**Solutions**:

```python
# Positions are 0-indexed and auto-managed
# After removal, positions are recalculated

# Manually reposition if needed
await queue._reposition_queue(community_id)
```

---

## Radio Streaming Issues

### Icecast Stream Not Playing

**Symptoms**:
- Radio plays but no audio
- Metadata not updating

**Solutions**:

**1. Verify Stream URL**
```bash
# Test stream URL directly
curl -I https://stream.example.com/radio.mp3

# Should return:
# Content-Type: audio/mpeg (or audio/aac)
# icy-metaint: 16000 (for metadata)
```

**2. Check Metadata Support**
```python
# Some streams don't support metadata
# Use API-based providers instead

# For Icecast, verify ICY-MetaInt header
async with httpx.AsyncClient() as client:
    response = await client.get(
        stream_url,
        headers={"Icy-MetaData": "1"}
    )
    meta_int = response.headers.get("icy-metaint")
    if not meta_int:
        print("Stream doesn't support metadata")
```

---

### Radio Metadata Not Updating

**Symptoms**:
- Now-playing shows old track
- Metadata stuck

**Solutions**:

**1. Check Refresh Interval**
```python
# Metadata refreshes every 30 seconds
# Force refresh by fetching without cache
now_playing = await radio.get_now_playing(
    community_id,
    use_cache=False  # Bypass cache
)
```

**2. Verify Provider API**
```bash
# For Pretzel/Epidemic/etc., check API directly
curl https://api.pretzel.rocks/v1/current \
  -H "Authorization: Bearer $API_KEY"
```

---

## Performance Issues

### Slow API Responses

**Symptoms**:
- Requests take >5 seconds
- Timeouts

**Solutions**:

**1. Check Redis Latency**
```bash
# Redis latency test
redis-cli --latency -u $REDIS_URL

# Should be <10ms
```

**2. Check Provider API Latency**
```bash
# Test provider APIs
time curl https://api.spotify.com/v1/search?q=test&type=track \
  -H "Authorization: Bearer $TOKEN"
```

**3. Enable Connection Pooling**
```python
# Reuse HTTP client
client = httpx.AsyncClient(
    limits=httpx.Limits(
        max_connections=100,
        max_keepalive_connections=20
    )
)
```

---

### High Memory Usage

**Symptoms**:
- Memory usage >500MB
- Out of memory errors

**Solutions**:

**1. Check Active Communities**
```python
# Memory ~50MB per 1000 communities with active queues
active_states = player.get_all_playback_states()
print(f"Active communities: {len(active_states)}")
```

**2. Clear Old Queue Data**
```bash
# Clean up old Redis keys
redis-cli --scan --pattern 'music_queue:*' | \
  xargs redis-cli DEL
```

**3. Reduce Queue TTL**
```bash
# Lower TTL to expire items sooner
export REDIS_QUEUE_TTL=3600  # 1 hour instead of 24
```

---

## Debugging Tools

### Enable Debug Logging

```python
import logging

# Set log level
logging.basicConfig(level=logging.DEBUG)

# Or via environment
export LOG_LEVEL=DEBUG
```

### Inspect Queue State

```bash
# View raw queue data in Redis
redis-cli -u $REDIS_URL GET music_queue:1:queue | jq
```

### Monitor HTTP Requests

```python
# Log all HTTP requests
import httpx

async def log_request(request):
    print(f"Request: {request.method} {request.url}")

client = httpx.AsyncClient()
client.event_hooks = {'request': [log_request]}
```

### Check Provider Token

```python
# Check Spotify token expiry
print(f"Token expires at: {spotify.token_expires_at}")
print(f"Time until expiry: {spotify.token_expires_at - datetime.now()}")
```

---

## Error Codes Reference

### HTTP Status Codes

| Code | Error | Meaning | Solution |
|------|-------|---------|----------|
| 400 | Bad Request | Invalid input | Check request payload |
| 401 | Unauthorized | Auth failed | Re-authenticate |
| 403 | Forbidden | No permission | Check scopes/quota |
| 404 | Not Found | Resource missing | Verify ID/URL |
| 409 | Conflict | State conflict | Retry operation |
| 429 | Too Many Requests | Rate limited | Wait and retry |
| 500 | Server Error | Internal error | Check logs |
| 502 | Bad Gateway | Provider error | Provider down |
| 503 | Service Unavailable | Service down | Check health |

### Provider-Specific Errors

**Spotify**:
- `NO_ACTIVE_DEVICE` - No Spotify device available
- `PREMIUM_REQUIRED` - Feature requires Spotify Premium
- `MARKET_NOT_AVAILABLE` - Content not available in region

**YouTube**:
- `quotaExceeded` - API quota exceeded
- `videoNotFound` - Video deleted/private
- `forbidden` - Geographic restriction

**SoundCloud**:
- `401 Unauthorized` - Invalid or expired token
- `404 Not Found` - Track deleted or private

---

## Getting Help

**1. Check Logs**
```bash
# Service logs
docker logs unified-music-module -f

# Provider-specific logs
# Look for ERROR or WARNING level messages
```

**2. Run Health Check**
```bash
curl http://localhost:8051/healthz | jq
```

**3. Test Individual Components**
```bash
# Test Redis
redis-cli -u $REDIS_URL ping

# Test Spotify
curl https://api.spotify.com/v1/me \
  -H "Authorization: Bearer $SPOTIFY_TOKEN"

# Test YouTube
curl "https://www.googleapis.com/youtube/v3/videos?id=dQw4w9WgXcQ&key=$YOUTUBE_API_KEY&part=snippet"
```

**4. Contact Support**
- GitHub Issues: https://github.com/waddlebot/waddlebot/issues
- Discord: https://discord.gg/waddlebot
- Documentation: `/docs/unified_music_module/`

---

**Last Updated**: 2025-12-16
**Version**: 1.0.0
**Maintainer**: Waddles Development Team
