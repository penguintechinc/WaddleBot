# YouTube Action Module - Troubleshooting Guide

## Common Errors

### OAuth Errors

#### invalidCredentials / Unauthorized (401)
**Error**: OAuth token invalid or expired

**Causes**:
- Token expired (3600 seconds)
- Token revoked by user
- Client ID/secret mismatch
- Scopes insufficient

**Solutions**:
```bash
# 1. Check token expiry in database
docker-compose exec infra-postgres psql -U mod_action_youtube -d waddlebot \
  -c "SELECT channel_id, expires_at FROM youtube_oauth_credentials WHERE channel_id='UCxxxxx';"

# 2. Refresh token manually if expired
# Module should auto-refresh before expiry
# If manual refresh needed:
curl -X POST https://oauth2.googleapis.com/token \
  -d "client_id=$YOUTUBE_CLIENT_ID" \
  -d "client_secret=$YOUTUBE_CLIENT_SECRET" \
  -d "grant_type=refresh_token" \
  -d "refresh_token=$REFRESH_TOKEN"

# 3. Verify scopes in database
docker-compose exec infra-postgres psql -U mod_action_youtube -d waddlebot \
  -c "SELECT scopes FROM youtube_oauth_credentials WHERE channel_id='UCxxxxx';"

# 4. If needed, revoke and re-authorize
curl -X DELETE http://localhost:8073/oauth/revoke/UCxxxxx \
  -H "Authorization: Bearer $JWT_TOKEN"
```

#### accessDenied
**Error**: User denied access permissions

**Causes**:
- User didn't grant scopes
- Revoked app permissions
- OAuth flow incomplete

**Solutions**:
```bash
# 1. Remove existing credentials
docker-compose exec infra-postgres psql -U mod_action_youtube -d waddlebot \
  -c "DELETE FROM youtube_oauth_credentials WHERE channel_id='UCxxxxx';"

# 2. Initiate new OAuth flow
curl -G http://localhost:8073/oauth/authorize -d "state=UCxxxxx"

# 3. User must grant all requested scopes
```

### API Errors

#### quotaExceeded (403)
**Error**: YouTube API quota exceeded

**Causes**:
- Exceeded daily quota (1,000,000 units)
- Too many requests in short time
- Quota allocation exceeded

**Solutions**:
```bash
# 1. Check what caused quota usage
docker-compose logs action-youtube | grep quota

# 2. Wait until next day (quota resets at midnight PT)
# Module will auto-retry after waiting

# 3. Reduce request frequency
# Instead of sending messages constantly, batch them

# 4. Check quota usage on Google Cloud Console
# https://console.cloud.google.com → APIs & Services → YouTube Data API v3

# 5. Request quota increase if needed
# https://console.cloud.google.com → APIs & Services → Quotas
```

#### liveChatNotFound (404)
**Error**: Live chat ID not found

**Causes**:
- Channel not currently live
- Live chat disabled
- Chat ID incorrect
- Stream ended

**Solutions**:
```bash
# 1. Verify channel is live
# https://youtube.com/@channel_name/live

# 2. Verify live chat ID format
# Should be 17-20 character string starting with "AimF"

# 3. Check if live chat is enabled in channel settings
# Settings → Advanced settings → Chat → Enable live chat

# 4. Get correct live chat ID from broadcast details
# Using YouTube API or checking in StreamYard/OBS

# 5. Retry when stream is live
```

#### forbidden (403)
**Error**: Action not allowed

**Causes**:
- Insufficient permissions
- Not channel owner/manager
- Action disabled
- Resource doesn't exist

**Solutions**:
```bash
# 1. Verify user has required permissions
# Only channel owner/managers can post chat messages

# 2. Check feature flags
echo "ENABLE_CHAT_ACTIONS=$ENABLE_CHAT_ACTIONS"
echo "ENABLE_VIDEO_ACTIONS=$ENABLE_VIDEO_ACTIONS"

# 3. Verify channel_id and user_id
docker-compose exec infra-postgres psql -U mod_action_youtube -d waddlebot \
  -c "SELECT channel_id, is_active FROM youtube_oauth_credentials WHERE channel_id='UCxxxxx';"

# 4. Check if actions are disabled in config
# See CONFIGURATION.md for feature flags
```

#### resourceNotFound (404)
**Error**: Video, playlist, or comment not found

**Causes**:
- Video ID incorrect
- Video deleted
- Playlist removed
- Comment deleted

**Solutions**:
```bash
# 1. Verify resource exists
# For videos: https://youtube.com/watch?v=VIDEO_ID
# For playlists: https://youtube.com/playlist?list=PLAYLIST_ID

# 2. Check resource ID format
# Video ID: 11 alphanumeric characters
# Playlist ID: Starts with "PL" + 32 characters
# Comment ID: Long alphanumeric string

# 3. Verify ownership
# Channel must own resource to modify it
```

### Module Errors

#### Database Connection Failed
**Error**: PostgreSQL connection error

**Causes**:
- Database server down
- Connection string invalid
- Network issue

**Solutions**:
```bash
# 1. Check database status
docker-compose ps infra-postgres

# 2. Test connection
docker-compose exec infra-postgres psql -U mod_action_youtube -d waddlebot -c "SELECT 1;"

# 3. Check connection string
echo $DATABASE_URL

# 4. Start database
docker-compose up -d postgres

# 5. Wait for database ready
docker-compose exec infra-postgres pg_isready -U mod_action_youtube
```

#### Configuration Error: YOUTUBE_CLIENT_ID Not Configured
**This is normal** in development.

**Solution**:
```bash
export YOUTUBE_CLIENT_ID=your-id
export YOUTUBE_CLIENT_SECRET=your-secret
docker-compose up action-youtube
```

#### Configuration Error: DATABASE_URL Required
**This prevents startup** and requires immediate fix.

**Solution**:
```bash
export DATABASE_URL=postgresql://user:pass@postgres:5432/waddlebot
docker-compose up action-youtube
```

## Debugging

### Enable Debug Logging
```bash
export LOG_LEVEL=DEBUG
docker-compose restart action-youtube

# Watch logs
docker-compose logs -f action-youtube
```

### Check Health Status
```bash
# Regular check
curl http://localhost:8073/health | jq .

# Continuous monitoring
watch -n 5 'curl -s http://localhost:8073/health | jq .'
```

### Monitor Logs
```bash
# Real-time
docker-compose logs -f action-youtube

# Last 50 lines
docker-compose logs --tail=50 youtube-action-module

# Filter for errors
docker-compose logs action-youtube | grep ERROR

# Filter for quota messages
docker-compose logs action-youtube | grep -i quota
```

### Check Credentials
```bash
# List all credentials
docker-compose exec infra-postgres psql -U mod_action_youtube -d waddlebot \
  -c "SELECT channel_id, expires_at, is_active FROM youtube_oauth_credentials;"

# Check specific channel
docker-compose exec infra-postgres psql -U mod_action_youtube -d waddlebot \
  -c "SELECT * FROM youtube_oauth_credentials WHERE channel_id='UCxxxxx';"

# Check expiring soon
docker-compose exec infra-postgres psql -U mod_action_youtube -d waddlebot \
  -c "SELECT channel_id, expires_at FROM youtube_oauth_credentials WHERE expires_at < NOW() + INTERVAL '1 hour';"
```

## Performance Issues

### High Memory Usage
```bash
# Check memory
docker-compose stats youtube-action-module

# Reduce workers
export MAX_WORKERS=10
docker-compose restart action-youtube

# Clear memory (restart)
docker-compose restart action-youtube
```

### Slow Response Times
```bash
# Check if quota limited
docker-compose logs action-youtube | grep quota

# Check Google Cloud status
curl https://status.cloud.google.com/

# Increase timeout
export REQUEST_TIMEOUT=60
docker-compose restart action-youtube

# Reduce rate limits
export RATE_LIMIT_REQUESTS=50
export RATE_LIMIT_WINDOW=60
docker-compose restart action-youtube
```

## Getting Help

1. Check logs: `docker-compose logs -f action-youtube`
2. Enable debug: `export LOG_LEVEL=DEBUG`
3. Verify config: `docker-compose exec action-youtube env | grep YOUTUBE`
4. Test OAuth: Visit https://console.cloud.google.com → OAuth client
5. Review this guide: Search for your error
6. Contact support: support@penguintech.io
