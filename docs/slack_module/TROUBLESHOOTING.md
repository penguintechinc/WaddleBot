# Slack Module Troubleshooting Guide

## Startup & Connection Issues

### Module won't start

**Error: "SLACK_BOT_TOKEN not configured"**

```bash
# Verify token is set
echo $SLACK_BOT_TOKEN

# If empty, set from .env
source .env
export SLACK_BOT_TOKEN

# Verify format (must start with xoxb-)
echo $SLACK_BOT_TOKEN | grep -E '^xoxb-' && echo "Valid" || echo "Invalid format"
```

**Error: "Failed to connect to database"**

```bash
# Test connection string
psql "$DATABASE_URL" -c "SELECT 1;"

# Check connection string format
echo "DATABASE_URL=$DATABASE_URL"

# Common fixes:
# - Missing password: postgresql://user@host/db → postgresql://user:pass@host/db
# - Wrong host: localhost → container_name (in docker-compose)
# - Missing trailing slash: /waddlebot vs /waddlebot/
```

**Error: "Port 8004 already in use"**

```bash
# Find what's using the port
lsof -i :8004

# Kill existing process
kill -9 <PID>

# Or use different port
export MODULE_PORT=8005
make run-slack-module
```

### Socket Mode connection fails

**Error: "Socket Mode enabled but SLACK_APP_TOKEN not provided"**

```bash
# Get app token from Slack app settings
# Slack App → Socket Mode → Generate Token (xapp-...)

# Set environment variable
export SLACK_APP_TOKEN=xapp-1-...

# Verify format
echo $SLACK_APP_TOKEN | grep -E '^xapp-' && echo "Valid" || echo "Invalid"
```

**Error: "WebSocket connection refused"**

```bash
# Check module logs for connection attempts
docker-compose logs slack-module | grep -i websocket

# Verify network connectivity to Slack
curl -I https://wss-primary.slack.com

# Check if firewall blocks outbound on port 443
telnet wss-primary.slack.com 443

# Try full module restart
docker-compose restart slack-module
```

**Symptom: "Socket Mode enabled: True" but no "connected" message**

```bash
# Enable debug logging to see connection details
export LOG_LEVEL=DEBUG

# Restart and capture logs
docker-compose logs -f slack-module | grep -E "(socket|websocket|connection)"

# Common causes:
# 1. App token expired/revoked - generate new token
# 2. App doesn't have Socket Mode enabled - enable in Slack settings
# 3. Firewall blocks WebSocket - check outbound rules
```

---

## Request & Event Handling Issues

### Slash commands not triggering

**Symptom: User types `/waddlebot` but nothing happens**

```bash
# Step 1: Check if module is receiving requests
docker-compose logs slack-module | grep -i "slash command"

# If no logs, slash command request isn't reaching module:
# - Verify Request URL in Slack app settings
# - For HTTP: https://domain.com/slack/commands
# - For Socket Mode: should be empty

# Step 2: Check module is running
curl http://localhost:8004/health

# Step 3: Test with curl (HTTP mode only)
curl -X POST http://localhost:8004/slack/commands \
  -d "token=test&team_id=T123&channel_id=C456&user_id=U789&command=/waddlebot&text=balance" \
  -H "Content-Type: application/x-www-form-urlencoded"
```

**Symptom: Command shows "loading..." then times out**

```bash
# Check logs for command processing
docker-compose logs slack-module | grep -A5 "slash command"

# Common causes:
# 1. Router API unreachable
docker-compose logs router | grep error

# 2. Command processing takes >3 seconds
# Solution: Use async response via response_url

# 3. Database timeout
docker-compose logs slack-module | grep -i "database\|timeout"
```

**Symptom: Command returns "Internal error" to user**

```bash
# Get full error details from logs
docker-compose logs slack-module | grep -i error | tail -20

# Common errors:
# - "Router service unavailable": docker-compose up router
# - "Database connection error": Check DATABASE_URL
# - "Invalid command": Check slash command routing in code
# - "Signature validation failed": Check SLACK_SIGNING_SECRET matches Slack app
```

### Events not received

**Symptom: Messages and mentions aren't processed**

```bash
# For HTTP mode, verify webhook URL set correctly
# Slack App → Event Subscriptions → Request URL: https://domain.com/slack/events

# Test webhook from Slack (Request URL verification)
# Slack will POST a challenge event - module should respond with challenge value

curl -X POST http://localhost:8004/slack/events \
  -H "X-Slack-Request-Timestamp: $(date +%s)" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "url_verification",
    "challenge": "test123"
  }'

# Expected response:
# {"challenge": "test123"}

# For Socket Mode, check connection status
docker-compose logs slack-module | grep -i "socket mode"
```

**Symptom: Correct events showing in logs but not processing**

```bash
# Check event routing
docker-compose logs slack-module | grep -E "(message_event|app_mention|event_type)"

# Verify event handler registered
grep -r "on_event(" src/ | grep message

# Check if event is filtered/ignored
docker-compose logs slack-module | grep -i "ignoring\|skipping\|filtering"

# Common causes:
# - Message from bot itself (filtered by design)
# - Message in thread (check if handler processes threads)
# - Permission issues accessing thread details
```

### Interaction (button/select) not working

**Symptom: User clicks button but nothing happens**

```bash
# Check if interaction event received
docker-compose logs slack-module | grep "block_actions"

# If not received:
# - Verify Interactivity enabled in Slack app
# - Verify Request URL set: https://domain.com/slack/actions
# - Check button action_id is set in message

# If received but not processed:
docker-compose logs slack-module | grep -i "action\|button"

# Test interaction manually
curl -X POST http://localhost:8004/slack/actions \
  -H "Content-Type: application/json" \
  -d '{
    "type": "block_actions",
    "user": {"id": "U123", "name": "test"},
    "team": {"id": "T123"},
    "channel": {"id": "C123"},
    "actions": [{"type": "button", "action_id": "test_button", "value": "test"}],
    "trigger_id": "123.456.abc"
  }'
```

---

## Response & Posting Issues

### Responses not appearing in Slack

**Symptom: Module processes command but no response shown**

```bash
# Check response posting in logs
docker-compose logs slack-module | grep -E "(chat_postMessage|updating|posting)"

# Common causes:

# 1. Response type mismatch
# Expected: ephemeral only visible to user
# Check logs for response_type
docker-compose logs slack-module | grep "response_type"

# 2. Missing bot permission
# Required: chat:write, chat:write.public
# Verify in Slack App → OAuth & Permissions → Bot Token Scopes

# 3. Channel archive or deleted
# Module tries to post to invalid channel
docker-compose logs slack-module | grep -E "channel.*not_found|archive_error"

# 4. Router returned empty response
# Check router logs
docker-compose logs router | grep -E "empty|null|undefined"
```

**Symptom: Ephemeral responses appear to everyone**

```bash
# Check response_type is set correctly
docker-compose logs slack-module | grep "response_type"

# Should show: "response_type": "ephemeral"

# If showing "in_channel", check:
# 1. Command handler returns correct response_type
# 2. Router returns correct response_type
# 3. BlockKitBuilder not overwriting response_type

grep -r "response_type" src/ | grep -v ephemeral | head -10
```

**Symptom: Modal doesn't open**

```bash
# Check modal opening call
docker-compose logs slack-module | grep -E "(views_open|modal)"

# Common causes:
# 1. Invalid trigger_id (expires after 3 seconds)
# 2. Missing required fields in modal
# 3. User doesn't have modal interaction permission

# Test modal directly with valid trigger_id
# Get from recent interaction logs
docker-compose logs slack-module | grep "trigger_id" | tail -1

# Extract trigger_id and test
curl -X POST https://slack.com/api/views.open \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "trigger_id": "TRIGGER_ID_HERE",
    "view": {...}
  }'
```

### Response message formatting issues

**Symptom: Block Kit blocks not rendering correctly**

```bash
# Check block JSON validity
docker-compose logs slack-module | grep -A20 "blocks.*:" | head -50

# Use Slack Block Kit validator
# Go to: https://app.slack.com/block-kit-builder

# Common issues:
# - Missing required fields (type, text.type, etc.)
# - Invalid text type for block (mrkdwn vs plain_text)
# - Unescaped JSON in strings
# - Circular references in selects

# Example: Valid section with button
{
  "type": "section",
  "text": {
    "type": "mrkdwn",  # or "plain_text"
    "text": "Some text"
  },
  "accessory": {
    "type": "button",
    "action_id": "my_button",
    "text": {
      "type": "plain_text",  # buttons always plain_text
      "text": "Click me"
    }
  }
}
```

---

## Modal & Form Issues

### Modal submission validation not working

**Symptom: Invalid inputs accepted in modal**

```bash
# Check validation logic runs
docker-compose logs slack-module | grep -i validation

# If no validation logs:
# 1. Modal handler not triggered
docker-compose logs slack-module | grep "view_submission"

# 2. Validation function not called
grep -r "def.*validate" src/

# 3. Validation errors not returned
docker-compose logs slack-module | grep "response_action.*errors"

# Test validation with missing required field
curl -X POST http://localhost:8004/slack/actions \
  -H "Content-Type: application/json" \
  -d '{
    "type": "view_submission",
    "view": {
      "id": "V123",
      "state": {
        "values": {
          "block_1": {"field_1": {"value": null}}
        }
      }
    }
  }'
```

**Symptom: Validation error appears but form doesn't reopen**

```bash
# Modal should stay open on validation error
# User fills form again and submits

# If modal closes instead:
# - Check response doesn't have "response_action": "clear"
# - Verify validation error response format

# Correct format:
{
  "response_action": "errors",
  "errors": {
    "block_id": "Error message"
  }
}

# Incorrect (closes modal):
{
  "response_action": "clear"
}
```

### Modal values not captured

**Symptom: Form fields empty or null when submitted**

```bash
# Check state.values structure in logs
docker-compose logs slack-module | grep -A30 "state.*values"

# Verify block_id and action_id match in submission
# block_id comes from block definition
# action_id comes from the input element

# Example correct structure:
{
  "state": {
    "values": {
      "email_block": {          # block_id
        "email_action": {       # action_id
          "type": "plain_text_input",
          "value": "user@example.com"
        }
      }
    }
  }
}

# If values are empty:
# 1. User hasn't filled field
# 2. field element doesn't have action_id
# 3. block doesn't have block_id
```

---

## Database & Credential Issues

### Token validation fails

**Error: "Invalid bot token" after adding workspace**

```bash
# Verify token format
echo $SLACK_BOT_TOKEN | grep -E '^xoxb-' && echo "Format OK"

# Check if token is active in Slack
curl -X POST https://slack.com/api/auth.test \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN"

# If token revoked/expired:
# 1. Generate new token in Slack App → OAuth & Permissions
# 2. Update DATABASE_URL or environment
# 3. Restart module

# Check stored token in database
psql $DATABASE_URL -c "
  SELECT team_id, created_at, updated_at FROM slack_workspaces LIMIT 5;
"
```

**Error: "Signature validation failed"**

```bash
# SLACK_SIGNING_SECRET must match Slack app setting
# Slack App → Basic Information → Signing Secret

# Verify locally
echo $SLACK_SIGNING_SECRET

# Should be 32 characters, hex format
echo -n $SLACK_SIGNING_SECRET | wc -c  # should print 32

# If mismatch:
# 1. Copy correct secret from Slack app
# 2. Update .env or environment variable
# 3. Restart module

# Test signature validation
docker-compose logs slack-module | grep -E "(signature|validation)" | tail -5
```

### Credential refresh issues

**Symptom: "Token refresh failed" errors in logs**

```bash
# Check if Redis is available (if enabled)
redis-cli ping
# Should respond: PONG

# If Redis not available:
export REDIS_URL=redis://localhost:6379/0
docker-compose up -d redis

# Check token in database directly
psql $DATABASE_URL << SQL
  SELECT
    team_id,
    created_at,
    extract(epoch from (NOW() - updated_at)) as seconds_since_update
  FROM slack_workspaces
  WHERE team_id = 'T123456';
SQL

# If token needs refresh:
# 1. Generate new token in Slack
# 2. Update database manually:
psql $DATABASE_URL -c "
  UPDATE slack_workspaces
  SET bot_token = 'xoxb-...'
  WHERE team_id = 'T123456';
"
# 3. Restart module

# Monitor refresh attempts
docker-compose logs slack-module | grep -i refresh | tail -10
```

### Database transaction failures

**Error: "Database transaction deadlock"**

```bash
# Check if many commands happening simultaneously
docker-compose logs slack-module | grep -c "transaction\|deadlock"

# Solutions:
# 1. Increase connection pool size
export DATABASE_MAX_CONNECTIONS=20

# 2. Retry with exponential backoff (should be automatic)
docker-compose logs slack-module | grep -i retry

# 3. Check for long-running queries blocking others
psql $DATABASE_URL -c "
  SELECT pid, usename, application_name, state, query
  FROM pg_stat_activity
  WHERE state != 'idle';
"
```

---

## Performance & Scaling Issues

### Slow command responses

**Symptom: Commands take 1-2 seconds to respond**

```bash
# Check router latency
docker-compose logs router | grep -E "(duration|ms|time)" | tail -5

# Check database query performance
psql $DATABASE_URL -c "
  SELECT
    query,
    calls,
    total_time,
    mean_time
  FROM pg_stat_statements
  ORDER BY mean_time DESC
  LIMIT 10;
"

# Optimize slow queries with indexes
psql $DATABASE_URL -c "
  CREATE INDEX idx_workspace_team_id ON slack_workspaces(team_id);
  CREATE INDEX idx_user_roles_user_id ON user_roles(user_id);
"

# Check connection pool isn't exhausted
# Look for "pool exhausted" errors in logs
docker-compose logs slack-module | grep -i "pool\|connection"
```

### High CPU usage

**Symptom: Module consuming 80%+ CPU**

```bash
# Check number of concurrent connections
docker stats slack-module

# If too many:
# 1. Reduce HYPERCORN_WORKERS
export WORKERS=2

# 2. Check for infinite loops in event handlers
docker-compose logs slack-module | grep -E "(CPU|loop)" | head -10

# 3. Check blocking I/O not happening
# All operations should be async
grep -r "\.sleep\|sleep\(" src/ | grep -v "asyncio"
```

### Memory leaks

**Symptom: Memory usage increases over time**

```bash
# Monitor memory
watch -n 5 'docker stats slack-module | grep slack'

# Check for unclosed connections
docker-compose logs slack-module | grep -i "connection\|leak\|open" | tail -20

# Verify sessions are properly closed
grep -r "async with" src/ | wc -l  # Should have context managers

# Restart module to confirm memory resets
docker-compose restart slack-module
docker-compose logs slack-module | grep "Memory\|Uptime"
```

---

## Socket Mode Specific Issues

### Socket Mode heartbeat failures

**Error: "Heartbeat missed" in logs**

```bash
# Check network connectivity
ping -c 5 slack.com

# Monitor Socket Mode connection
docker-compose logs slack-module | grep -E "(heartbeat|ping|pong)" | tail -10

# If repeated failures:
# 1. Network is unstable - may need retry logic
# 2. Firewall dropping packets - check firewall rules
# 3. Slack having issues - check status.slack.com

# Force reconnect
docker-compose restart slack-module
```

### Duplicate events in Socket Mode

**Symptom: Event processed twice (both ack and response)**

```bash
# Check if events are being retried
docker-compose logs slack-module | grep -E "(envelope_id|retry|duplicate)" | tail -20

# Socket Mode requires:
# 1. Immediate ack with envelope_id
# 2. Optional response with envelope_id

# If skipping ack, Slack retries event
# Solution: Always call ack() first in handler

# Verify ack is sent
grep -A5 "handle_message_event\|handle_slash_command" src/ | grep ack
```

---

## Debugging Commands

### Enable verbose logging

```bash
# Set DEBUG level
export LOG_LEVEL=DEBUG

# Restart module
docker-compose restart slack-module

# Watch logs in real-time
docker-compose logs -f slack-module | grep -i "debug\|error"
```

### Capture request/response payloads

```bash
# Use tcpdump to capture Slack webhooks
sudo tcpdump -i any -n "tcp port 8004" -w /tmp/slack.pcap

# Or in Python, add logging:
import logging
logging.basicConfig(level=logging.DEBUG)

# View captured packets
tcpdump -r /tmp/slack.pcap -A | less
```

### Manual testing with curl

```bash
# Test /slack/events endpoint
curl -X POST http://localhost:8004/slack/events \
  -H "X-Slack-Request-Timestamp: $(date +%s)" \
  -H "X-Slack-Signature: v0=fake_signature" \
  -H "Content-Type: application/json" \
  -d '{"type": "url_verification", "challenge": "test"}'

# Test /slack/commands endpoint
curl -X POST http://localhost:8004/slack/commands \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "token=test&team_id=T123&command=/waddlebot&text=balance&user_id=U123&channel_id=C123"

# Test health endpoint
curl http://localhost:8004/health | jq .
```

### Connect to database for inspection

```bash
# Connect to PostgreSQL
psql $DATABASE_URL

# List tables
\dt

# Inspect slack_workspaces table
SELECT team_id, bot_name, created_at, updated_at FROM slack_workspaces;

# Check recent command executions
SELECT * FROM slack_command_log ORDER BY created_at DESC LIMIT 10;

# Inspect user roles
SELECT * FROM user_roles WHERE user_id = 'U123';
```

---

## Getting Help

If issues persist after troubleshooting:

1. **Collect logs:**
   ```bash
   docker-compose logs slack-module > /tmp/slack-module.log 2>&1
   docker-compose logs router > /tmp/router.log 2>&1
   docker-compose logs postgres > /tmp/postgres.log 2>&1
   ```

2. **Capture configuration (no secrets):**
   ```bash
   env | grep -v TOKEN | grep -v SECRET | grep -v PASSWORD > /tmp/env.log
   ```

3. **Test health:**
   ```bash
   curl http://localhost:8004/health > /tmp/health.json
   ```

4. **Contact support with logs and error details:**
   - support@penguintech.io
   - Include reproduction steps
   - Include relevant log snippets (sanitized of secrets)
