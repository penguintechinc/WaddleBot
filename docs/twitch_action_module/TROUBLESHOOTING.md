# Twitch Action Module - Troubleshooting Guide

## Common Errors and Solutions

### Authentication Errors

#### Login authentication failed (IRC)
**Error Message**: `:tmi.twitch.tv NOTICE * :Login authentication failed`

**Causes**:
- OAuth token invalid or expired
- Token refresh failed
- Bot username mismatch

**Solutions**:
```bash
# 1. Check token expiration in database
docker-compose exec infra-postgres psql -U mod_action_twitch -d waddlebot \
  -c "SELECT broadcaster_id, expires_at FROM twitch_action_tokens WHERE broadcaster_id='123456789';"

# 2. Verify token is still valid at Twitch
curl -H "Authorization: Bearer $ACCESS_TOKEN" \
  https://api.twitch.tv/helix/users \
  -H "Client-ID: $TWITCH_CLIENT_ID"

# 3. If token expired, refresh manually
curl -X POST http://localhost:8072/api/v1/tokens/store \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "broadcaster_id": "123456789",
    "access_token": "new_token",
    "refresh_token": "new_refresh",
    "expires_in": 3600
  }'

# 4. Restart IRC connection (module will reconnect on next message)
# Or manually revoke and re-store:
curl -X POST http://localhost:8072/api/v1/tokens/revoke \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -d '{"broadcaster_id": "123456789"}'
```

#### invalid_auth
**Error Message**: `{"error": "Unauthorized", "status": 401}`

**Causes**:
- TWITCH_CLIENT_ID invalid
- TWITCH_CLIENT_SECRET invalid
- Token revoked by broadcaster
- Scopes insufficient

**Solutions**:
```bash
# 1. Verify credentials are correct
echo "Client ID: $TWITCH_CLIENT_ID"
echo "Client Secret: ${TWITCH_CLIENT_SECRET:0:10}..."  # Show first 10 chars only

# 2. Test with OAuth endpoint
curl -X POST https://id.twitch.tv/oauth2/token \
  -d "client_id=$TWITCH_CLIENT_ID" \
  -d "client_secret=$TWITCH_CLIENT_SECRET" \
  -d "grant_type=client_credentials" \
  -d "scope=clips:edit"

# 3. If failed, regenerate at https://dev.twitch.tv/console/apps
# 4. Update environment and restart
export TWITCH_CLIENT_ID=new-id
export TWITCH_CLIENT_SECRET=new-secret
docker-compose restart action-twitch

# 5. Verify credentials are loaded
curl http://localhost:8072/health | jq .
```

#### token_expired
**Error Message**: OAuth token expired, needs refresh

**Causes**:
- Token not refreshed before expiry
- Refresh token also expired (shouldn't happen)
- Broadcaster revoked access

**Solutions**:
```bash
# 1. Module auto-refreshes 5 minutes before expiry (default)
# If error occurs, token refresh failed

# 2. Check refresh token validity
docker-compose exec infra-postgres psql -U mod_action_twitch -d waddlebot \
  -c "SELECT broadcaster_id, refresh_token FROM twitch_action_tokens WHERE broadcaster_id='123456789';"

# 3. Try manual refresh
curl -X POST https://id.twitch.tv/oauth2/token \
  -d "client_id=$TWITCH_CLIENT_ID" \
  -d "client_secret=$TWITCH_CLIENT_SECRET" \
  -d "grant_type=refresh_token" \
  -d "refresh_token=$REFRESH_TOKEN"

# 4. If refresh fails, broadcaster must re-authorize
# Revoke current token and re-store with new one
curl -X POST http://localhost:8072/api/v1/tokens/revoke \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -d '{"broadcaster_id": "123456789"}'
```

### IRC Connection Errors

#### Connection refused
**Error Message**: `ConnectionRefusedError: [Errno 111] Connection refused`

**Causes**:
- irc.chat.twitch.tv unreachable
- Network connectivity issue
- Firewall blocking IRC port 6667

**Solutions**:
```bash
# 1. Check network connectivity
docker-compose exec action-twitch ping irc.chat.twitch.tv

# 2. Check firewall rules (if using UFW)
sudo ufw allow 6667

# 3. Test IRC connection manually
telnet irc.chat.twitch.tv 6667

# 4. Check Twitch status page
# https://status.twitch.tv/

# 5. Retry connection (module auto-retries with backoff)
# Enable debug logging to see retry attempts
export LOG_LEVEL=DEBUG
docker-compose restart action-twitch
```

#### ERR_NOTREGISTERED
**Error Message**: `ERR_NOTREGISTERED: You have not registered`

**Causes**:
- Authentication not sent before sending commands
- Authentication failed silently
- IRC protocol sequence error

**Solutions**:
```bash
# 1. Check logs for authentication error
docker-compose logs -f action-twitch | grep -i auth

# 2. Verify token being used is valid
# Token should start with "oauth:" in IRC

# 3. Enable detailed IRC logging
export LOG_LEVEL=DEBUG
docker-compose restart action-twitch

# 4. Test IRC authentication manually
# telnet irc.chat.twitch.tv 6667
# CAP REQ :twitch.tv/tags twitch.tv/commands
# PASS oauth:ACCESS_TOKEN_HERE
# NICK waddlebot
# [Should receive :tmi.twitch.tv NOTICE * :Login successful]
```

#### Connection timeout
**Error Message**: `TimeoutError: IRC connection timed out after 30s`

**Causes**:
- IRC server not responding
- Network latency high
- Firewall dropping packets

**Solutions**:
```bash
# 1. Check network latency to Twitch
docker-compose exec action-twitch ping -c 5 irc.chat.twitch.tv

# 2. Increase timeout if network is slow
export REQUEST_TIMEOUT=60
docker-compose restart action-twitch

# 3. Check if IRC server is overloaded
# Monitor CPU and memory on Twitch infrastructure

# 4. Use different IRC server endpoint (if available)
# Currently only one: irc.chat.twitch.tv:6667
```

### Token Errors

#### token_not_found
**Error Message**: `broadcaster_id not found in token database`

**Causes**:
- Token was never stored for broadcaster
- Token was revoked
- Wrong broadcaster_id used

**Solutions**:
```bash
# 1. Check if token exists in database
docker-compose exec infra-postgres psql -U mod_action_twitch -d waddlebot \
  -c "SELECT broadcaster_id FROM twitch_action_tokens WHERE broadcaster_id='123456789';"

# 2. Store token if missing
curl -X POST http://localhost:8072/api/v1/tokens/store \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -d '{
    "broadcaster_id": "123456789",
    "access_token": "...",
    "refresh_token": "...",
    "expires_in": 3600
  }'

# 3. Verify broadcaster_id format
# Should be numeric Twitch user ID
# Get from: https://api.twitch.tv/helix/users?login=username

# 4. List all stored tokens
docker-compose exec infra-postgres psql -U mod_action_twitch -d waddlebot \
  -c "SELECT broadcaster_id, broadcaster_login FROM twitch_action_tokens ORDER BY created_at DESC LIMIT 10;"
```

#### insufficient_permissions
**Error Message**: `Missing required scope: clips:edit`

**Causes**:
- OAuth token doesn't have required scope
- Broadcaster didn't grant permission
- Scope requirements changed

**Solutions**:
```bash
# 1. Check granted scopes
curl -H "Authorization: Bearer $ACCESS_TOKEN" \
  https://api.twitch.tv/helix/users \
  -H "Client-ID: $TWITCH_CLIENT_ID" \
  | jq .

# 2. Revoke current token and request new one with all scopes
curl -X POST http://localhost:8072/api/v1/tokens/revoke \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -d '{"broadcaster_id": "123456789"}'

# 3. Request reauthorization with all scopes
# Redirect broadcaster to:
# https://id.twitch.tv/oauth2/authorize \
#   ?client_id=$TWITCH_CLIENT_ID \
#   &redirect_uri=http://localhost:8072/oauth/callback \
#   &response_type=code \
#   &scope=chat:edit+chat:read+clips:edit+moderator:manage:chat_settings

# 4. Required scopes for all features
cat << 'EOF'
chat:edit - Send chat messages
chat:read - Read chat messages
clips:edit - Create clips
moderator:manage:chat_settings - Manage chat settings
EOF
```

### API Errors

#### rate_limited
**Error Message**: `{"error": "rate_limited", "retry_after": 60}`

**Causes**:
- Too many messages in short time
- Twitch rate limit exceeded (50 req/sec)
- IRC rate limit (1 msg/sec per channel)

**Solutions**:
```bash
# 1. Implement exponential backoff in client
# Wait 60 seconds before retrying

# 2. Reduce message throughput
# Spread messages over time:
# Instead of 100 msgs in 1 sec, send 1/sec

# 3. Use batch operations efficiently
# Group messages for same broadcaster

# 4. Check module logs
docker-compose logs action-twitch | grep -i rate

# 5. Increase token refresh buffer to reduce token refresh rate
export TOKEN_REFRESH_BUFFER=600
docker-compose restart action-twitch
```

#### invalid_batch_size
**Error Message**: `Batch size 150 exceeds maximum of 100`

**Causes**:
- Too many actions in single batch
- Exceeded MAX_BATCH_SIZE setting

**Solutions**:
```bash
# 1. Split batch into smaller chunks
# Instead of 150 actions, send 2 batches of 75

# 2. Increase MAX_BATCH_SIZE if needed
export MAX_BATCH_SIZE=200
docker-compose restart action-twitch

# 3. Example correct batch size
# {"actions": [...100 items max...]}
```

### Database Errors

#### database_connection_failed
**Error Message**: Health check shows database unreachable

**Causes**:
- PostgreSQL server down
- Connection string invalid
- Network unreachable

**Solutions**:
```bash
# 1. Check database is running
docker-compose ps infra-postgres

# 2. Test connection manually
docker-compose exec infra-postgres psql -U mod_action_twitch -d waddlebot -c "SELECT 1;"

# 3. Check connection string
echo $DATABASE_URL

# 4. Verify credentials
psql -U mod_action_twitch -h localhost -d waddlebot

# 5. Start database if down
docker-compose up -d postgres

# 6. Wait for database to be ready
docker-compose exec infra-postgres pg_isready -U mod_action_twitch

# 7. Health check should now pass
curl http://localhost:8072/health
```

### JWT Authentication Errors

#### Missing Authorization Header
**Error Message**: `401 Unauthorized - No authorization header`

**Causes**:
- Client forgot to include Authorization header
- Header name misspelled
- Bearer token missing

**Solutions**:
```bash
# 1. Verify header format
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8072/api/v1/stats

# 2. Generate token if missing
TOKEN=$(curl -s -X POST http://localhost:8072/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"api_key": "'$MODULE_SECRET_KEY'"}' | jq -r '.token')

# 3. Use token in request
curl -H "Authorization: Bearer $TOKEN" http://localhost:8072/api/v1/stats
```

#### Invalid or Expired Token
**Error Message**: `401 Unauthorized - Invalid or expired token`

**Causes**:
- Token signature invalid
- Token expired (default 1 hour)
- MODULE_SECRET_KEY changed
- Token corrupted

**Solutions**:
```bash
# 1. Generate fresh token
TOKEN=$(curl -s -X POST http://localhost:8072/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"api_key": "'$MODULE_SECRET_KEY'"}' | jq -r '.token')

# 2. Check token expiration
echo $TOKEN | cut -d'.' -f2 | base64 -d | jq .

# 3. Increase token expiry if needed (in source code)
# JWT_EXPIRATION_SECONDS = 86400  # 24 hours
```

### Module Startup Errors

#### Configuration Error: TWITCH_CLIENT_ID Not Configured
**This is normal** in development. Module will start but fail on actions.

**Solution**:
```bash
export TWITCH_CLIENT_ID=your-id
export TWITCH_CLIENT_SECRET=your-secret
docker-compose up action-twitch
```

#### Configuration Error: DATABASE_URL Required
**This prevents startup** and requires immediate fix.

**Solution**:
```bash
export DATABASE_URL=postgresql://user:pass@postgres:5432/waddlebot
docker-compose up action-twitch
```

## Debugging and Monitoring

### Enable Debug Logging
```bash
export LOG_LEVEL=DEBUG
docker-compose restart action-twitch

# Watch logs in real-time
docker-compose logs -f action-twitch
```

### Check Health Status
```bash
# Regular check
curl http://localhost:8072/health | jq .

# Continuous monitoring
watch -n 5 'curl -s http://localhost:8072/health | jq .'
```

### Monitor Logs

```bash
# Real-time logs
docker-compose logs -f action-twitch

# Last 50 lines
docker-compose logs --tail=50 twitch-action-module

# Filter for errors
docker-compose logs action-twitch | grep ERROR

# Filter for IRC logs
docker-compose logs action-twitch | grep IRC
```

### Check Token Status

```bash
# List all tokens
docker-compose exec infra-postgres psql -U mod_action_twitch -d waddlebot \
  -c "SELECT broadcaster_id, expires_at, is_active FROM twitch_action_tokens ORDER BY created_at DESC;"

# Check specific token
docker-compose exec infra-postgres psql -U mod_action_twitch -d waddlebot \
  -c "SELECT * FROM twitch_action_tokens WHERE broadcaster_id='123456789';"

# Check tokens expiring soon
docker-compose exec infra-postgres psql -U mod_action_twitch -d waddlebot \
  -c "SELECT broadcaster_id, expires_at FROM twitch_action_tokens WHERE expires_at < NOW() + INTERVAL '1 hour';"
```

### Performance Issues

#### High Memory Usage
```bash
# Check memory
docker-compose stats twitch-action-module

# Restart to clear
docker-compose restart action-twitch

# Reduce concurrent workers
export MAX_WORKERS=10
docker-compose restart action-twitch
```

#### Slow Response Times
```bash
# Check if rate limited
docker-compose logs action-twitch | grep rate

# Check Twitch status
curl https://status.twitch.tv/api/v2/status.json | jq .

# Increase timeout
export REQUEST_TIMEOUT=60
docker-compose restart action-twitch
```

## Getting Help

1. Check logs: `docker-compose logs -f action-twitch`
2. Enable debug: `export LOG_LEVEL=DEBUG`
3. Verify configuration: `docker-compose exec action-twitch env | grep TWITCH`
4. Test connectivity: `docker-compose exec action-twitch ping irc.chat.twitch.tv`
5. Review this guide: Search for your error message
6. Contact support: support@penguintech.io
