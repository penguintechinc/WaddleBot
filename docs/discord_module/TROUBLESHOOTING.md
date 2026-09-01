# Discord Module Troubleshooting Guide

## Bot Not Responding

### Symptoms
- Bot appears offline in Discord
- Commands don't get responses
- No events in logs

### Diagnosis

1. **Check bot is online in Discord**
   ```
   Right-click server → Member List
   Find WaddleBot → Should show a green online indicator
   ```

2. **Check logs for connection errors**
   ```bash
   docker-compose logs trigger-discord | grep -i "connection\|connected\|error"
   ```

3. **Verify bot is in the server**
   ```
   Right-click server → Server Settings → Members
   Search for WaddleBot in members list
   ```

### Solutions

**If bot is offline:**
1. Check `DISCORD_BOT_TOKEN` is valid (hasn't been revoked)
2. Restart container: `docker-compose restart trigger-discord`
3. Check Discord status page: https://status.discord.com

**If bot is in wrong server:**
1. Generate OAuth2 URL with correct scopes
2. Go to [Discord Developer Portal](https://discord.com/developers/applications)
3. Select app → OAuth2 → URL Generator
4. Select `bot` and `applications.commands` scopes
5. Select required permissions
6. Copy URL and add bot to correct server

**If logs show repeated errors:**
```
[ERROR] Reconnecting to Discord...
[ERROR] Connection failed
```
This usually means token is invalid. Generate new token in Developer Portal.

## Commands Not Showing Up

### Symptoms
- Type `/` but no WaddleBot commands appear
- Commands were registered before but disappeared
- Some commands visible, others not

### Diagnosis

1. **Check commands are registered**
   ```bash
   curl http://localhost:8003/api/v1/status
   ```
   Should show bot is connected and guilds count > 0

2. **Check Discord API sync status**
   - Slash commands sync globally (can take up to 1 hour)
   - Server-specific commands sync immediately

3. **Check client-side cache**
   - Discord caches command lists locally

### Solutions

**If commands aren't showing after 1 hour:**
1. Force Discord client reload: `Ctrl+Shift+R` (Windows) or `Cmd+Shift+R` (Mac)
2. Log out and log back in to Discord
3. Check bot has correct permissions:
   ```
   Right-click bot → Roles → Edit
   Make sure "Use Slash Commands" permission is enabled
   ```

**To manually re-register commands:**
```bash
docker-compose exec trigger-discord python -m scripts.register_commands --force
```

**If still not showing:**
1. Check logs for registration errors:
   ```bash
   docker logs discord-module | grep -i "register"
   ```
2. Verify `DISCORD_APPLICATION_ID` matches bot in Developer Portal
3. Verify bot token is valid

## Bot Responds Slowly

### Symptoms
- Commands take 10+ seconds to respond
- Frequent "The bot did not respond in time" messages
- High latency shown in `/api/v1/status`

### Diagnosis

1. **Check bot latency**
   ```bash
   curl http://localhost:8003/api/v1/status | jq .latency_ms
   ```
   - < 100ms: Normal
   - 100-300ms: Acceptable
   - > 300ms: Investigate

2. **Check router response times**
   ```bash
   time curl http://router:5000/health
   ```

3. **Check database query times**
   ```bash
   docker-compose logs infra-postgres | grep duration | tail -10
   ```

### Solutions

**High bot latency (> 300ms):**
1. Check Discord API status: https://status.discord.com
2. Move bot to region closer to Discord's data center
3. Check network connectivity from bot to Discord

**Slow router responses:**
1. Check router logs: `docker-compose logs core-router`
2. Scale router replicas if under load
3. Add indexing to frequently queried database columns

**Slow database queries:**
1. Enable query logging: `LOG_LEVEL=DEBUG`
2. Check for missing indexes on credentials table
3. Clear old interaction history:
   ```sql
   DELETE FROM discord_interactions
   WHERE created_at < NOW() - INTERVAL '7 days';
   ```

## Commands Returning Errors

### Error: "The bot did not respond in time"

**Cause**: Router took too long to respond (>3 seconds)

```bash
# Check router timeout
docker-compose logs core-router | grep timeout
```

**Solutions:**
1. Increase `ROUTER_TIMEOUT_SECONDS` in configuration
2. Check router is running: `docker-compose ps core-router`
3. Check router logs for errors: `docker-compose logs core-router`
4. Verify router URL is correct: `echo $ROUTER_API_URL`

### Error: "I don't have permission to do that"

**Cause**: Bot is missing required Discord permissions

**Solutions:**
1. Go to Server Settings → Roles
2. Find bot role
3. Check these permissions are enabled:
   - Send Messages
   - Embed Links
   - Use Slash Commands
   - Use External Emojis
   - Manage Messages (for editing responses)

### Error: "Invalid token"

**Cause**: `DISCORD_BOT_TOKEN` is invalid or expired

**Solutions:**
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Select your app → Bot
3. Click "Reset Token"
4. Copy new token
5. Update `DISCORD_BOT_TOKEN` environment variable
6. Restart container: `docker-compose restart trigger-discord`

### Error: "Unknown slash command"

**Cause**: Command group/name doesn't match registered commands

**Solutions:**
1. Check command is registered: `curl http://localhost:8003/api/v1/status`
2. Reload Discord client: `Ctrl+Shift+R`
3. Re-register commands:
   ```bash
   docker-compose exec trigger-discord python -m scripts.register_commands --force
   ```

## Database Connection Issues

### Symptoms
- Logs show "Cannot connect to database"
- Credentials not being stored
- User profiles not loading

### Diagnosis

```bash
# Check database is running
docker-compose ps infra-postgres

# Test database connection
docker-compose exec infra-postgres psql -U waddlebot_user -d waddlebot -c "SELECT 1"
```

### Solutions

**If database is not running:**
```bash
docker-compose up -d db
```

**If connection times out:**
1. Check database URL: `echo $DATABASE_URL`
   - Format: `postgresql://user:pass@host:5432/dbname`
2. Verify host is reachable: `ping db` (in Docker) or `ping db.example.com`
3. Verify credentials are correct
4. Check database firewall allows connections

**If database is corrupted:**
```bash
# Backup old data
docker-compose exec infra-postgres pg_dump waddlebot > backup.sql

# Reinitialize database
docker-compose exec infra-postgres psql -U postgres -c "DROP DATABASE waddlebot"
docker-compose exec infra-postgres psql -U postgres -c "CREATE DATABASE waddlebot"

# Run migrations
docker-compose exec trigger-discord python -m scripts.migrate_db
```

## Redis Connection Issues

### Symptoms
- Credentials cache not working
- "Cannot connect to Redis" in logs
- Credentials lookup taking long time

### Diagnosis

```bash
# Check Redis is running
docker-compose ps infra-redis

# Test Redis connection
docker-compose exec infra-redis redis-cli ping
# Should respond: PONG
```

### Solutions

**If Redis is not running:**
```bash
docker-compose up -d redis
```

**If Redis connection fails:**
1. Check Redis URL: `echo $REDIS_URL`
2. Format should be: `redis://host:6379/0`
3. Verify host is reachable

**If Redis is running but slow:**
1. Check memory usage: `docker-compose exec infra-redis redis-cli INFO memory`
2. Clear old cache: `docker-compose exec infra-redis redis-cli FLUSHDB`
3. Check disk I/O: `docker stats redis`

## Memory and Resource Issues

### Symptoms
- Bot crashes with "Out of memory"
- Container restarts frequently
- High CPU usage

### Diagnosis

```bash
# Check container stats
docker stats discord-module

# Check memory limits
docker inspect discord-module | grep -i memory

# Check process memory
docker-compose exec trigger-discord ps aux | grep python
```

### Solutions

**If out of memory:**
1. Increase container memory limit in docker-compose.yml:
   ```yaml
   discord-module:
     mem_limit: 512m  # Increase from 256m
   ```
2. Restart container: `docker-compose restart trigger-discord`

**If high CPU usage:**
1. Check if many events are being processed: `docker logs discord-module | grep "Event received"`
2. Enable DEBUG logging to see what's slow: `LOG_LEVEL=DEBUG`
3. Check for infinite loops in event handlers

**If frequent crashes:**
1. Check memory usage trends: `docker stats --no-stream discord-module`
2. Check for memory leaks in logs
3. Increase resource limits
4. Check for large responses from router (should be < 1MB)

## Network and Connectivity Issues

### Symptoms
- "Cannot reach router"
- "Connection refused"
- "Timeout connecting to database"

### Diagnosis

```bash
# Test router connectivity
docker-compose exec trigger-discord curl -v http://router:5000/health

# Test database connectivity
docker-compose exec trigger-discord python -c "import psycopg2; ..."

# Test Redis connectivity
docker-compose exec trigger-discord python -c "import redis; ..."
```

### Solutions

**If using localhost:**
- Use service names in docker-compose: `http://router:5000` (not `localhost:5000`)

**If using custom domain:**
- Ensure DNS resolves: `nslookup router.example.com`
- Ensure firewall allows traffic: `nc -zv router.example.com 5000`
- Check TLS/SSL certificates if using HTTPS

**If Docker network issues:**
```bash
# Check networks
docker network ls

# Inspect network
docker network inspect waddlebot-network

# Restart networking
docker-compose down
docker-compose up -d
```

## Message Not Posting to Discord

### Symptoms
- Bot processes command but message doesn't appear
- No response shown to user
- Command succeeds in logs but no Discord message

### Diagnosis

1. **Check if response was generated**
   ```bash
   docker logs discord-module | grep "Message posted\|response received"
   ```

2. **Check Discord channel permissions**
   - Right-click channel → Permissions
   - Find bot role
   - Ensure "Send Messages" is enabled

3. **Check message content**
   - Response might exceed 2000 char limit
   - Response might have invalid formatting

### Solutions

**If channel is read-only:**
1. Right-click channel → Edit Channel
2. Under Permissions, find bot role
3. Enable "Send Messages"

**If message is too long:**
- Bot automatically splits messages over 2000 characters
- Check that message splitting is enabled: `MESSAGE_SPLIT_ENABLED=true`

**If embed is invalid:**
1. Check embed has title or description
2. Check all field values are not empty
3. Verify color is valid hex: `0xFFD700`

## Command Autocomplete Not Working

### Symptoms
- Type `/balance` and no suggestions appear for parameters
- Autocomplete dropdown empty or missing

### Diagnosis

1. **Check autocomplete is enabled**
   ```bash
   echo $AUTOCOMPLETE_ENABLED
   ```

2. **Check command definition includes options**
   ```bash
   curl http://router:5000/commands | jq '.[] | select(.name == "balance")'
   ```

3. **Check option has autocomplete**
   - Option should have `"autocomplete": true`

### Solutions

**If autocomplete is disabled:**
```bash
export AUTOCOMPLETE_ENABLED=true
docker-compose restart trigger-discord
```

**If command options missing:**
1. Check router is returning command definitions
2. Verify command name matches exactly
3. Re-register commands: `python -m scripts.register_commands --force`

**If suggestions are slow:**
1. Check database query performance
2. Add index on frequently queried column
3. Limit suggestion count (Discord shows max 25)

## Modal Forms Not Appearing

### Symptoms
- Modal support seems enabled but forms don't show
- Click button but no form appears
- "Response not acknowledged" error

### Diagnosis

```bash
# Check modal support is enabled
echo $MODAL_SUPPORT_ENABLED

# Check logs for modal errors
docker logs discord-module | grep -i modal
```

### Solutions

**If modals are disabled:**
```bash
export MODAL_SUPPORT_ENABLED=true
docker-compose restart trigger-discord
```

**If modal submission fails:**
1. Check form has required fields
2. Verify custom_id is unique
3. Check modal response is sent within 3 seconds

## Performance Tuning

### Slow Event Processing

1. **Enable DEBUG logging temporarily**
   ```bash
   LOG_LEVEL=DEBUG docker-compose up trigger-discord
   ```

2. **Identify slow operations**
   - Check logs for database queries
   - Check for many round-trips to router/core

3. **Optimize**
   - Cache frequently accessed data in Redis
   - Batch database queries
   - Add database indexes

### High Memory Usage

1. **Check for memory leaks**
   ```bash
   docker stats --no-stream discord-module
   ```

2. **Limit interaction history**
   - Delete old interactions: `DELETE FROM discord_interactions WHERE created_at < NOW() - INTERVAL '7 days'`

3. **Reduce cache TTL**
   - Decrease `REDIS_CREDENTIAL_TTL` to reduce memory

## Getting Help

### Collect Diagnostic Information

```bash
# System info
docker-compose --version
docker --version

# Service status
docker-compose ps

# Recent logs (last 100 lines)
docker-compose logs trigger-discord --tail 100

# Status check
curl http://localhost:8003/api/v1/status | jq

# Connected guilds
curl http://localhost:8003/api/v1/bot/guilds | jq
```

Save this output when reporting issues.

### Contact Support

- **Email**: support@penguintech.io
- **Status Page**: https://status.penguintech.io
- **Documentation**: https://docs.waddlebot.io

When reporting issues, include:
1. Diagnostic output (see above)
2. Steps to reproduce
3. Expected vs actual behavior
4. Environment (Docker, Kubernetes, etc.)
