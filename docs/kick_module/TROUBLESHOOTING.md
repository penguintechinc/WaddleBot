# Kick Module Troubleshooting Guide

## Common Issues & Solutions

### Webhook Signature Verification Failures

**Symptom**: Many requests return 401 Unauthorized with "signature_mismatch" error.

**Root Causes:**

1. **Mismatched webhook secret**
   - The `KICK_WEBHOOK_SECRET` env var doesn't match the secret configured in Kick dashboard
   - **Solution**:
     ```bash
     # Get the secret from Kick dashboard (Integrations → Webhooks)
     # Update .env file
     KICK_WEBHOOK_SECRET=your-actual-webhook-secret-from-kick-console
     # Restart module
     docker restart kick-module
     ```

2. **Secret too short**
   - Kick requires secrets to be at least 32 characters
   - **Solution**:
     ```bash
     # Generate proper secret
     NEW_SECRET=$(openssl rand -base64 32)
     echo "Update KICK_WEBHOOK_SECRET=$NEW_SECRET in your .env"
     ```

3. **Timestamp drift**
   - Module's system clock is out of sync (signature includes timestamp)
   - **Solution**:
     ```bash
     # Synchronize system clock
     ntpdate -s time.nist.gov
     # Or use systemd time sync
     timedatectl set-ntp true
     ```

4. **Request body modified in transit**
   - Proxy/load balancer altering request body
   - **Solution**:
     ```nginx
     # In Nginx config, ensure no body modification
     proxy_pass_request_body on;
     proxy_http_version 1.1;
     ```

**Debugging:**

```bash
# Enable signature logging
echo "KICK_DEBUG_SIGNATURES=true" >> .env
docker restart kick-module

# Watch logs
docker logs -f kick-module | grep -i "signature\|hmac"

# Manual signature test
PAYLOAD='{"event":"chat_message","data":{}}'
SECRET="your-webhook-secret"
EXPECTED=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$SECRET" -hex | cut -d' ' -f2)
echo "Expected: sha256=$EXPECTED"

curl -X POST http://localhost:8007/webhook/kick \
  -H "X-Signature: sha256=$EXPECTED" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD"
```

### WebSocket Connection Issues

**Symptom**: Logs show "WebSocket connection failed" or "Failed to subscribe to chatroom".

**Root Causes:**

1. **Incorrect Pusher credentials**
   - `KICK_PUSHER_KEY` or `KICK_PUSHER_CLUSTER` is wrong
   - **Solution**:
     ```bash
     # Verify Pusher key (usually fixed value)
     KICK_PUSHER_KEY=eb1d5f283081a78b932c  # Standard Kick value
     KICK_PUSHER_CLUSTER=us2                # Standard Kick cluster
     ```

2. **Network connectivity to Pusher**
   - Firewall blocking `pusher.us2.pusher.com:443` or `wss://` protocol
   - **Solution**:
     ```bash
     # Test connectivity
     curl -I https://pusher.us2.pusher.com/
     nc -zv pusher.us2.pusher.com 443  # Or use telnet

     # Check firewall rules
     iptables -L -n | grep pusher
     ufw status | grep 443
     ```

3. **Firewall/NAT blocking WebSocket upgrade**
   - Some proxies don't support WebSocket protocol upgrade
   - **Solution**:
     ```nginx
     # Nginx WebSocket support
     location /pusher {
         proxy_pass https://pusher.us2.pusher.com/;
         proxy_http_version 1.1;
         proxy_set_header Upgrade $http_upgrade;
         proxy_set_header Connection "upgrade";
         proxy_read_timeout 86400;
     }
     ```

4. **Redis connection issue**
   - WebSocket state can't be cached in Redis
   - **Solution**:
     ```bash
     # Test Redis
     redis-cli -u $REDIS_URL ping
     # Expected: PONG

     # Check REDIS_URL format
     # Should be: redis://[:password]@host:port/db
     ```

**Debugging:**

```bash
# Check WebSocket connection in status
curl http://localhost:8007/api/v1/status | jq '.components.websocket'

# View reconnection attempts in logs
docker logs kick-module | grep -i "websocket\|reconnect\|pusher"

# Enable debug logging
LOG_LEVEL=DEBUG docker run ... kick-module
```

### Router API Integration Failures

**Symptom**: Events received but not forwarded to Router. Logs show "POST /api/v1/events failed".

**Root Causes:**

1. **Router API unreachable**
   - `ROUTER_API_URL` is incorrect or Router service is down
   - **Solution**:
     ```bash
     # Test connectivity
     curl -I $ROUTER_API_URL/health

     # Verify URL format (no trailing slash)
     ROUTER_API_URL=http://router-api:8001
     echo $ROUTER_API_URL

     # Check DNS resolution
     nslookup router-api
     ```

2. **Router service not running**
   - **Solution**:
     ```bash
     # Check service status
     systemctl status waddlebot-router
     docker ps | grep router

     # Restart if needed
     systemctl restart waddlebot-router
     # or
     docker restart router-container
     ```

3. **Router API authentication required**
   - Router might require API key in Authorization header
   - **Solution**:
     ```bash
     # Check router documentation
     # Add to code if needed:
     headers = {
         'Authorization': f'Bearer {ROUTER_API_KEY}',
         'Content-Type': 'application/json'
     }
     ```

4. **Event payload format mismatch**
   - Router expects different event schema
   - **Solution**:
     ```bash
     # View actual event being sent
     docker logs kick-module | grep "forwarding_event" | tail -1

     # Compare with Router API documentation
     # Fix event mapping in src/models/events.py
     ```

**Debugging:**

```bash
# Monitor router failures in real-time
docker logs -f kick-module | grep -i "router\|forward"

# Test router endpoint manually
PAYLOAD='{
  "platform": "kick",
  "event_type": "chat",
  "channel_id": "12345",
  "user": {"id": "123", "username": "test"},
  "content": "test message",
  "metadata": {}
}'

curl -X POST http://$ROUTER_API_URL/api/v1/events \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD"

# Check router queue/logs
docker logs router | tail -20
```

### Database Connection Errors

**Symptom**: "PostgreSQL connection failed" or "DATABASE_URL invalid".

**Root Causes:**

1. **Invalid DATABASE_URL format**
   - Must be: `postgresql://user:password@host:port/dbname`
   - **Solution**:
     ```bash
     # Correct format
     DATABASE_URL=postgresql://waddlebot:secure_pass@postgres:5432/waddlebot

     # With special chars, URL-encode password
     PASSWORD='p@$$w0rd'
     ENCODED=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$PASSWORD'))")
     DATABASE_URL=postgresql://waddlebot:$ENCODED@postgres:5432/waddlebot
     ```

2. **PostgreSQL server not running or unreachable**
   - **Solution**:
     ```bash
     # Test connection
     psql $DATABASE_URL -c "SELECT 1;"

     # If connection fails:
     # 1. Check if service running
     systemctl status postgresql
     # 2. Verify network reachability
     nc -zv postgres 5432
     # 3. Check firewall
     ufw allow 5432
     ```

3. **Database doesn't exist**
   - **Solution**:
     ```bash
     # Create database
     psql postgresql://postgres:postgres@localhost/postgres \
       -c "CREATE DATABASE waddlebot;"

     # Or in Kubernetes:
     kubectl exec -it postgres-0 -- psql -U postgres \
       -c "CREATE DATABASE waddlebot;"
     ```

4. **Connection pool exhausted**
   - Too many concurrent connections from Kick module
   - **Solution**:
     ```bash
     # Check current connections
     psql $DATABASE_URL -c "SELECT count(*) FROM pg_stat_activity;"

     # Increase pool size in .env
     DB_POOL_SIZE=30
     DB_POOL_OVERFLOW=15

     # Or increase PostgreSQL limit
     psql -c "ALTER SYSTEM SET max_connections = 500;"
     # Then restart PostgreSQL
     ```

**Debugging:**

```bash
# Test connection directly
psql $DATABASE_URL -c "SELECT version();"

# Check connection string parsing
python3 << 'EOF'
import urllib.parse
url = 'postgresql://user:pass@host:5432/db'
parsed = urllib.parse.urlparse(url)
print(f"Host: {parsed.hostname}, Port: {parsed.port}, DB: {parsed.path}")
EOF

# Monitor active queries
psql $DATABASE_URL -c "SELECT pid, usename, state, query FROM pg_stat_activity;"
```

### High Latency or Slow Event Processing

**Symptom**: Events taking >1 second to reach Router, or status shows high latency.

**Root Causes:**

1. **Router API is slow**
   - Router under load or network latency
   - **Solution**:
     ```bash
     # Increase timeout
     ROUTER_TIMEOUT=30  # seconds

     # Check Router health
     time curl $ROUTER_API_URL/health

     # Monitor Router CPU/memory
     docker stats router-container
     ```

2. **Database queries too slow**
   - User enrichment or event logging queries slow
   - **Solution**:
     ```bash
     # Check slow query log
     psql $DATABASE_URL -c "SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 5;"

     # Add indexes if missing
     psql $DATABASE_URL -c "CREATE INDEX idx_kick_events_channel ON kick_events(channel_id);"
     ```

3. **Batching delay**
   - Events collected in batches (up to 50ms)
   - **Solution** (if latency critical):
     ```bash
     # Reduce batch timeout in config
     BATCH_TIMEOUT=0.01  # 10ms instead of 50ms
     MAX_BATCH_SIZE=10   # Smaller batches
     ```

4. **Too many WebSocket connections**
   - Pusher reconnections consuming CPU
   - **Solution**:
     ```bash
     # Monitor connections
     curl http://localhost:8007/api/v1/status | jq '.stats.websocket_connections'

     # If high, check for reconnect loops
     docker logs kick-module | grep -i "reconnect" | wc -l
     ```

**Profiling:**

```bash
# Add latency metrics to logs
LOG_LEVEL=DEBUG docker run ... kick-module

# Parse logs for slow operations
docker logs kick-module | grep '"duration_ms":' | \
  awk -F'duration_ms":' '{print $2}' | \
  awk -F',' '{print $1}' | \
  sort -n | tail -10
```

### Memory Leaks or Growing Memory Usage

**Symptom**: Module memory usage steadily increases over time.

**Root Causes:**

1. **Unclosed event objects in queue**
   - Events not properly released after processing
   - **Solution**:
     ```bash
     # Check queue depth
     curl http://localhost:8007/api/v1/status | jq '.stats'

     # If queue growing, restart module
     docker restart kick-module

     # Fix in code: ensure proper cleanup
     # In event handler:
     try:
         process_event(event)
     finally:
         del event  # Explicit cleanup
     ```

2. **WebSocket connection leak**
   - Connections not closing on disconnect
   - **Solution**:
     ```bash
     # Monitor websocket_connections metric
     curl http://localhost:8007/metrics | grep websocket_connections_active

     # Should be stable; if growing, check reconnect logic
     docker logs kick-module | grep -E "disconnect|cleanup"
     ```

3. **Cache accumulation**
   - Redis or in-memory cache growing without eviction
   - **Solution**:
     ```bash
     # Check Redis memory
     redis-cli -u $REDIS_URL info memory

     # Set cache expiration
     CACHE_TTL=3600  # 1 hour

     # Or use Redis eviction policy
     redis-cli CONFIG SET maxmemory-policy allkeys-lru
     ```

4. **Circular references in dataclasses**
   - Python objects not garbage collected
   - **Solution**:
     ```bash
     # Restart module periodically (if needed)
     # In Docker: add restart policy
     --restart=on-failure:3

     # Or use memory profiler to find leaks
     pip install memory-profiler
     python -m memory_profiler app.py
     ```

### Module Won't Start

**Symptom**: Container fails to start or crashes immediately.

**Root Causes:**

1. **Missing required environment variables**
   - **Solution**:
     ```bash
     # Check logs
     docker logs kick-module 2>&1 | head -20

     # Verify all required vars
     docker run -it kick-module env | grep -E "SECRET_KEY|WEBHOOK|DATABASE"

     # Add missing vars to .env or Dockerfile
     ```

2. **Python dependency missing**
   - **Solution**:
     ```bash
     # Check for import errors
     docker run --rm kick-module python -c "import quart, pysher, pydal"

     # Rebuild image if dependencies changed
     docker build --no-cache -t kick-module .
     ```

3. **Port already in use**
   - Another service using port 8007
   - **Solution**:
     ```bash
     # Find process using port
     lsof -i :8007
     # or
     netstat -tulnp | grep 8007

     # Kill or change Kick module port
     MODULE_PORT=8008 docker run ... kick-module
     ```

4. **Database migration failed**
   - **Solution**:
     ```bash
     # Check migration status
     psql $DATABASE_URL -c "\d"

     # Run migrations manually
     docker run --rm kick-module flask db upgrade
     ```

**Debugging Startup:**

```bash
# Run with verbose logging
docker run -it \
  -e LOG_LEVEL=DEBUG \
  -e DEBUG=true \
  kick-module

# Check Python syntax
python -m py_compile src/**/*.py

# Test imports
python -c "from src import app; print('OK')"
```

## Performance Tuning Guide

### For High-Volume Streams (&gt;100 msgs/sec)

```bash
# Increase database pool
DB_POOL_SIZE=30
DB_POOL_OVERFLOW=20

# Larger batches
MAX_BATCH_SIZE=200
BATCH_TIMEOUT=0.2

# More HTTP connections
MAX_CONNECTIONS=100

# Increase timeouts
ROUTER_TIMEOUT=20
API_REQUEST_TIMEOUT=15

# More Quart workers (if using hypercorn)
hypercorn -b 0.0.0.0:8007 -w 8 app:app
```

### For Low-Latency Requirements (&lt;200ms p99)

```bash
# Reduce batch wait
MAX_BATCH_SIZE=10
BATCH_TIMEOUT=0.01  # 10ms

# Faster reconnects
WEBSOCKET_BACKOFF_MAX=10  # seconds

# Persistent connections
DB_POOL_RECYCLE=3600

# Connection pooling
MAX_CONNECTIONS=200
```

## Monitoring Checklist

**Daily:**
- [ ] Module health check: `curl http://localhost:8007/health`
- [ ] Event processing rate: `curl .../metrics | grep kick_event_processed_total`
- [ ] Error rate: `docker logs kick-module | grep ERROR | wc -l`

**Weekly:**
- [ ] Database size: `psql $DATABASE_URL -c "SELECT pg_size_pretty(pg_database_size('waddlebot'));"`
- [ ] WebSocket connection stability: Check reconnect counts
- [ ] Router API latency: Check metrics p99

**Monthly:**
- [ ] Slow query analysis: Enable and review slow logs
- [ ] Memory usage trend: Graph memory metrics
- [ ] Dependency updates: Check for security patches

## Support & Escalation

If issues persist after troubleshooting:

1. **Collect diagnostic bundle:**
   ```bash
   mkdir -p kick-module-diagnostics
   docker logs kick-module > kick-module-diagnostics/logs.txt
   curl http://localhost:8007/api/v1/status > kick-module-diagnostics/status.json
   curl http://localhost:8007/metrics > kick-module-diagnostics/metrics.txt
   env | grep -E "KICK|DATABASE|ROUTER" > kick-module-diagnostics/config.txt
   ```

2. **Contact support with:**
   - Diagnostic bundle (above)
   - Exact error message from logs
   - Steps to reproduce
   - Expected vs actual behavior

3. **Support channels:**
   - Email: support@penguintech.io
   - Slack: #waddlebot-support
   - Status: https://status.penguintech.io

## See Also

- [API Documentation](API.md)
- [Configuration Guide](CONFIGURATION.md)
- [Usage Guide](USAGE.md)
- [Architecture Details](ARCHITECTURE.md)
