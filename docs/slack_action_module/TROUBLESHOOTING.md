# Slack Action Module - Troubleshooting Guide

## Common Errors and Solutions

### Authentication Errors

#### invalid_auth
**Error Message**: `invalid_auth` when sending messages

**Causes**:
- SLACK_BOT_TOKEN expired or revoked
- Bot removed from workspace
- Token has wrong format
- Token for different workspace

**Solutions**:
```bash
# 1. Verify token format (should start with xoxb-)
echo $SLACK_BOT_TOKEN

# 2. Test token validity with Slack API
curl -X POST https://slack.com/api/auth.test \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN"

# Expected response with valid token:
# {"ok": true, "url": "https://workspace.slack.com/", "team": "My Team", ...}

# 3. If invalid, regenerate token
# Go to https://api.slack.com/apps → Your App → OAuth & Permissions
# → Reinstall to Workspace → Copy new Bot User OAuth Token

# 4. Update environment variable
export SLACK_BOT_TOKEN=xoxb-new-token-here

# 5. Restart module
docker-compose restart slack-action-module

# 6. Verify health check
curl http://localhost:8071/health
```

#### token_revoked
**Error Message**: `token_revoked` - Token has been revoked

**Causes**:
- Workspace admin revoked app token
- User uninstalled the app
- Token manually revoked in Slack dashboard

**Solutions**:
```bash
# 1. Reinstall app to workspace
# Go to https://api.slack.com/apps → Your App → OAuth & Permissions
# Click "Reinstall to Workspace"

# 2. Copy new token and set environment variable
export SLACK_BOT_TOKEN=xoxb-new-token

# 3. Restart module
docker-compose restart slack-action-module
```

### Channel Errors

#### channel_not_found
**Error Message**: `channel_not_found` when sending to channel

**Causes**:
- Channel ID format incorrect
- Channel deleted
- Channel ID belongs to different workspace
- Bot in wrong workspace

**Solutions**:
```bash
# 1. Verify channel ID format (starts with C for channels, G for groups)
echo "Channel ID: C01234567" # Correct format for public channel
echo "Channel ID: G01234567" # Correct format for private channel (group)

# 2. Verify channel exists and bot can see it
curl -X POST https://slack.com/api/conversations.list \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" | jq '.channels[] | {id, name}'

# 3. If channel not in list, verify workspace is correct
curl -X POST https://slack.com/api/auth.test \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" | jq '.team_id'

# 4. Use channel name instead if ID unknown
# API will look up channel automatically with #channel-name format
```

#### not_in_channel
**Error Message**: `not_in_channel` - Bot not a member of channel

**Causes**:
- Bot not invited to channel
- Bot removed from channel
- Channel is private and bot not in member list

**Solutions**:
```bash
# 1. Manually invite bot to channel
# In Slack: /invite @WaddleBot in the channel

# 2. Or use Slack API to invite bot
curl -X POST https://slack.com/api/conversations.invite \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d 'channel=C01234567&users=U01234567'

# 3. Verify bot is member
curl -X POST https://slack.com/api/conversations.members \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -d 'channel=C01234567' | jq '.members'

# 4. If still not working, check bot has conversations:read scope
# https://api.slack.com/apps → Your App → OAuth & Permissions
# → Verify scopes include: conversations:read, channels:read
```

#### no_permission
**Error Message**: `no_permission` - Missing required OAuth scope

**Causes**:
- OAuth scope not granted to app
- Using wrong API endpoint
- Scope removed after app installation

**Solutions**:
```bash
# 1. Check granted scopes
curl -X POST https://slack.com/api/auth.test \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" | jq '.response_metadata.scopes'

# Expected scopes for messaging:
# ["chat:write", "chat:write.public", "files:write", ...]

# 2. If scope missing, add it to app
# https://api.slack.com/apps → Your App → OAuth & Permissions
# → Bot Token Scopes → Add the required scope
# → Reinstall app to workspace (if first time)
# → Reauthorize (if already installed)

# 3. Required scopes for all features:
cat << 'EOF'
chat:write - Send messages
chat:write.public - Send to public channels
emoji:read - Read emoji reactions
files:write - Upload files
channels:manage - Create/manage channels
groups:write - Write to private channels
groups:manage - Manage group membership
users:read - Read user information
views:open - Open modals
reactions:write - Add/remove reactions
reactions:read - Read reaction data
EOF

# 4. Restart module after adding scopes
docker-compose restart slack-action-module
```

### Message Errors

#### message_not_found
**Error Message**: `message_not_found` when updating/deleting message

**Causes**:
- Message timestamp (ts) format incorrect
- Message deleted by user/admin
- Message timestamp from different workspace
- Message more than retention period old

**Solutions**:
```bash
# 1. Verify message timestamp format
# Correct: "1234567890.123456" (epoch_seconds.microseconds)
# Incorrect: "1234567890" (missing microseconds)

# 2. Retrieve recent messages to get correct timestamp
curl -X POST https://slack.com/api/conversations.history \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -d 'channel=C01234567&limit=10' | jq '.messages[] | {ts, text}'

# 3. For thread messages, include thread_ts
curl -X POST http://localhost:8071/api/v1/message/C01234567/1234567890.123456 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "community_id": "test",
    "text": "Updated text",
    "thread_ts": "1234567890.123456"
  }'

# 4. If message truly deleted, send new message instead
```

#### message_metadata_invalid
**Error Message**: `message_metadata_invalid` - Block Kit structure error

**Causes**:
- Malformed Block Kit JSON
- Block type not recognized
- Missing required fields in block
- Too many blocks (max 100)

**Solutions**:
```bash
# 1. Validate Block Kit structure
# Use Slack Block Kit Builder: https://app.slack.com/block-kit-builder

# 2. Check common issues:
# - Missing "type" field
# - Misspelled block types (section not "Section")
# - Incorrect text object structure
# - Elements with invalid types

# 3. Example correct block structure:
{
  "blocks": [
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "*Bold* text"
      }
    },
    {
      "type": "actions",
      "elements": [
        {
          "type": "button",
          "text": {
            "type": "plain_text",
            "text": "Click me",
            "emoji": true
          },
          "value": "click_me_123"
        }
      ]
    }
  ]
}

# 4. Validate before sending with jq
cat message.json | jq . || echo "Invalid JSON"
```

### Rate Limiting

#### rate_limited
**Error Message**: `rate_limited` - Too many requests

**Causes**:
- Exceeded Slack API rate limits
- Too many concurrent requests
- Burst of messages in short time

**Slack API Rate Limits**:
- 1 message per second per channel
- 50 API requests per second per app
- File uploads: 20 per second per workspace

**Solutions**:
```bash
# 1. Check rate limiting in response headers
curl -v http://localhost:8071/api/v1/message \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"community_id": "test", "channel_id": "C123", "text": "msg"}' 2>&1 | grep -i rate

# 2. Implement exponential backoff in client
# Retry-After header indicates seconds to wait
# Example: Retry-After: 60

# 3. Reduce concurrent request rate
# If sending many messages, add delay between requests
for channel in C123 C456 C789; do
  curl -X POST http://localhost:8071/api/v1/message \
    -H "Authorization: Bearer $TOKEN" \
    -d "{\"community_id\": \"test\", \"channel_id\": \"$channel\", \"text\": \"msg\"}"
  sleep 1  # 1 second delay between requests
done

# 4. Batch operations where possible
# Group updates to same channel before sending
```

### File Upload Errors

#### file_not_uploaded
**Error Message**: `file_not_uploaded` - File upload failed

**Causes**:
- File size exceeds limit (20MB)
- Invalid base64 encoding
- Channel full or storage quota exceeded
- Unsupported file type

**Solutions**:
```bash
# 1. Check file size
ls -lh /path/to/file
# File must be under 20MB

# 2. Verify base64 encoding
base64 -w0 /path/to/file > /tmp/encoded.txt
wc -c /tmp/encoded.txt  # Should be < 25MB

# 3. Encode file correctly for API
FILE_CONTENT=$(base64 -w0 < /path/to/file)
curl -X POST http://localhost:8071/api/v1/file \
  -H "Authorization: Bearer $TOKEN" \
  -d "{
    \"community_id\": \"test\",
    \"channel_id\": \"C123\",
    \"file_content_base64\": \"$FILE_CONTENT\",
    \"filename\": \"file.pdf\"
  }"

# 4. For large files, use Slack's file API directly
# Instead of base64, use multipart/form-data upload
```

### Database Errors

#### database_connection_failed
**Error Message**: Health check shows `unhealthy` with database error

**Causes**:
- PostgreSQL server down
- Connection string invalid
- Network unreachable
- Wrong credentials

**Solutions**:
```bash
# 1. Check database connection string
echo $DATABASE_URL
# Should be: postgresql://user:password@host:5432/dbname

# 2. Test PostgreSQL connection
psql $DATABASE_URL -c "SELECT 1"

# 3. Check database is running
docker-compose ps postgres

# 4. Check logs for connection errors
docker-compose logs postgres

# 5. Verify credentials
# In PostgreSQL shell:
psql -U mod_action_slack -h localhost -d waddlebot

# 6. If database down, start it
docker-compose up -d postgres

# 7. Wait for database to be ready
docker-compose exec postgres pg_isready -U mod_action_slack

# 8. Health check should pass after restart
curl http://localhost:8071/health
```

### JWT Authentication Errors

#### Missing Authorization Header
**Error Message**: `401 Unauthorized` - No authorization header

**Causes**:
- Client forgot to include Authorization header
- Header name misspelled
- Token not provided

**Solutions**:
```bash
# 1. Verify header format
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8071/api/v1/history/test

# 2. Generate token if missing
TOKEN=$(curl -s -X POST http://localhost:8071/api/v1/token \
  -H "Content-Type: application/json" \
  -d '{"api_key": "'$MODULE_SECRET_KEY'", "client_id": "test"}' | jq -r '.token')

echo "Token: $TOKEN"

# 3. Use token in request
curl -H "Authorization: Bearer $TOKEN" http://localhost:8071/api/v1/history/test
```

#### Invalid Token
**Error Message**: `401 Unauthorized` - Invalid or expired token

**Causes**:
- Token signature invalid
- Token expired (default 1 hour)
- MODULE_SECRET_KEY changed
- Token corrupted in transmission

**Solutions**:
```bash
# 1. Generate new token
TOKEN=$(curl -s -X POST http://localhost:8071/api/v1/token \
  -H "Content-Type: application/json" \
  -d '{"api_key": "'$MODULE_SECRET_KEY'", "client_id": "test"}' | jq -r '.token')

# 2. Decode token to check expiration
echo $TOKEN | cut -d'.' -f2 | base64 -d | jq .

# Expected output shows "exp" timestamp (unix time)
# If exp < current time, token is expired

# 3. Verify MODULE_SECRET_KEY hasn't changed
# Token was signed with old key, but server using new key
# Must regenerate token with correct key

# 4. Increase token expiry if needed (in source code)
# JWT_EXPIRY_SECONDS = 3600  # 1 hour - change to 86400 for 24 hours
```

### Module Startup Errors

#### Configuration Error: SLACK_BOT_TOKEN Not Configured
**Error**: `WARNING: SLACK_BOT_TOKEN not configured - awaiting admin configuration via hub`

**This is normal** in development. Module will start but fail to send messages.

**Solution**:
```bash
# Set environment variable before starting
export SLACK_BOT_TOKEN=xoxb-your-token
docker-compose up slack-action-module

# Or add to .env file
echo "SLACK_BOT_TOKEN=xoxb-your-token" >> .env
```

#### Configuration Error: DATABASE_URL Required
**Error**: `CRITICAL: DATABASE_URL is required` → Module exits

**This prevents module startup** and requires immediate fix.

**Solution**:
```bash
# Set DATABASE_URL
export DATABASE_URL=postgresql://user:pass@postgres:5432/waddlebot
docker-compose up slack-action-module
```

### Logging and Debugging

#### Enable Debug Logging
```bash
# Set log level to DEBUG
export LOG_LEVEL=DEBUG
docker-compose restart slack-action-module

# View logs
docker-compose logs -f slack-action-module

# Expected debug output:
# [2024-01-15 10:30:00] DEBUG slack_service:send_message:123 Sending message to C01234567
# [2024-01-15 10:30:00] DEBUG slack_service:send_message:124 Message response: {'ok': True, 'ts': '...'}
```

#### Check Health Status
```bash
# Regular health check
curl http://localhost:8071/health | jq .

# Continuous monitoring
watch -n 5 'curl -s http://localhost:8071/health | jq .'
```

#### Monitor Container Logs
```bash
# Real-time logs
docker-compose logs -f slack-action-module

# Last 50 lines
docker-compose logs --tail=50 slack-action-module

# Filter for errors
docker-compose logs slack-action-module | grep ERROR

# Follow specific log file
docker-compose exec slack-action-module tail -f /var/log/waddlebotlog/slack_action.log
```

### Performance Issues

#### High Memory Usage
**Symptoms**: Container memory usage growing continuously

**Causes**:
- Database connection leak
- Slack SDK memory leak
- Large action history in memory

**Solutions**:
```bash
# 1. Check memory usage
docker-compose stats slack-action-module

# 2. Restart container to clear memory
docker-compose restart slack-action-module

# 3. Check for connection leaks in logs
docker-compose logs slack-action-module | grep -i leak

# 4. Reduce MAX_CONCURRENT_REQUESTS
export MAX_CONCURRENT_REQUESTS=50
docker-compose restart slack-action-module

# 5. Set memory limit in docker-compose.yml
deploy:
  resources:
    limits:
      memory: 512M
```

#### Slow Response Times
**Symptoms**: Requests taking >5 seconds to complete

**Causes**:
- Slack API is slow
- Database queries slow
- Network latency
- Rate limiting applied

**Solutions**:
```bash
# 1. Check Slack API status
curl https://status.slack.com/api/v2.0/status

# 2. Test database query performance
docker-compose exec postgres \
  psql -U mod_action_slack -d waddlebot \
  -c "SELECT COUNT(*) FROM action_history;"

# 3. Check network latency
docker-compose exec slack-action-module ping -c 5 slack.com

# 4. Increase REQUEST_TIMEOUT if needed
export REQUEST_TIMEOUT=60
docker-compose restart slack-action-module
```

## Health Checks and Monitoring

### Kubernetes Readiness Probe
```yaml
readinessProbe:
  httpGet:
    path: /health
    port: 8071
  initialDelaySeconds: 10
  periodSeconds: 10
  timeoutSeconds: 5
```

### Kubernetes Liveness Probe
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8071
  initialDelaySeconds: 30
  periodSeconds: 30
  timeoutSeconds: 5
```

## Getting Help

If issues persist:

1. **Check logs**: `docker-compose logs -f slack-action-module`
2. **Verify configuration**: `docker-compose exec slack-action-module env | grep SLACK`
3. **Test Slack token**: `curl -H "Authorization: Bearer $SLACK_BOT_TOKEN" https://slack.com/api/auth.test`
4. **Review this guide**: Search for the error message
5. **Contact support**: support@penguintech.io
