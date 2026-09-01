# Video Proxy Module — Troubleshooting Guide

Common issues, debug steps, and solutions for the video_proxy_module.

---

## Table of Contents

1. [Connection Issues](#connection-issues)
2. [Database Problems](#database-problems)
3. [Streaming Issues](#streaming-issues)
4. [Authentication Problems](#authentication-problems)
5. [Configuration Errors](#configuration-errors)
6. [Performance Issues](#performance-issues)
7. [Destination Integration](#destination-integration)
8. [Debug Logging](#debug-logging)
9. [Quick Diagnostic Commands](#quick-diagnostic-commands)

---

## Connection Issues

### Port Already in Use

**Symptom**: `Address already in use` when starting the module

**Root Cause**: Another process is using port 8092 (REST) or 50065 (gRPC)

**Debug Steps**:
```bash
# Check what's using the port
lsof -i :8092      # REST API port
lsof -i :50065     # gRPC port

# Or with netstat
netstat -tlnp | grep 8092
netstat -tlnp | grep 50065
```

**Solutions**:

**Option 1**: Stop conflicting service
```bash
# Find and kill the process
kill -9 $(lsof -t -i :8092)
```

**Option 2**: Use different port
```bash
# Set custom port in environment
export MODULE_PORT=9092
export GRPC_PORT=50066

python3 app.py
```

**Option 3**: Docker/Kubernetes - port mapping
```bash
# Docker with different host port
docker run -p 9092:8092 -p 50066:50065 waddlebot/video-proxy:latest

# Kubernetes - LoadBalancer with different port
apiVersion: v1
kind: Service
metadata:
  name: video-proxy
spec:
  ports:
    - name: rest
      port: 9092
      targetPort: 8092
    - name: grpc
      port: 50066
      targetPort: 50065
```

---

### Connection Refused

**Symptom**: `curl: (7) Failed to connect to localhost port 8092`

**Root Cause**: Module not running or listening on wrong interface

**Debug Steps**:
```bash
# Check if process is running
ps aux | grep "python3 app.py"

# Check if port is open
netstat -tlnp | grep 8092

# Try localhost with -v for verbose
curl -v http://localhost:8092/health

# Check if listening on all interfaces (0.0.0.0)
# If MODULE_HOST=127.0.0.1, can't access from other machines
```

**Solutions**:

**Option 1**: Start the module
```bash
# Make sure environment is set
export DATABASE_URL=postgresql://...
export JWT_SECRET_KEY=...

python3 app.py
```

**Option 2**: Bind to all interfaces
```bash
# Edit .env
MODULE_HOST=0.0.0.0

# Or environment variable
export MODULE_HOST=0.0.0.0
python3 app.py
```

**Option 3**: Check logs for startup errors
```bash
# Run with verbose output
python3 -u app.py 2>&1 | tee app.log
```

---

### Connection Timeout

**Symptom**: `curl: (28) Operation timed out` or `gRPC deadline exceeded`

**Root Cause**: Network issue, firewall, or module is hanging

**Debug Steps**:
```bash
# Check if port is responding
nc -zv localhost 8092
nc -zv localhost 50065

# Check firewall rules
sudo ufw status
sudo iptables -L -n

# Test connectivity to database
python3 -c "from app import db; db.executesql('SELECT 1'); print('DB OK')"

# Test with increased timeout
curl --connect-timeout 10 http://localhost:8092/health

# Check module logs for hangs
docker logs -f video-proxy
```

**Solutions**:

**Option 1**: Allow firewall
```bash
# ufw
sudo ufw allow 8092/tcp
sudo ufw allow 50065/tcp

# iptables
sudo iptables -A INPUT -p tcp --dport 8092 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 50065 -j ACCEPT
```

**Option 2**: Check database connection
```bash
# Test database directly
psql -h localhost -U waddlebot -d waddlebot -c "SELECT 1;"

# If failing, check credentials
echo $DATABASE_URL
```

**Option 3**: Restart module
```bash
# Kill and restart
pkill -f "python3 app.py"
python3 app.py
```

---

## Database Problems

### Database Connection Failed

**Symptom**: `Error: could not connect to server: Connection refused`

**Root Cause**: PostgreSQL not running, wrong credentials, or wrong host

**Debug Steps**:
```bash
# Check if PostgreSQL is running
ps aux | grep postgres

# Test connection
psql -h localhost -U waddlebot -d waddlebot -c "SELECT 1;"

# Parse DATABASE_URL
echo $DATABASE_URL

# Check if database exists
psql -h localhost -U postgres -l | grep waddlebot

# Verify credentials
# Format: postgresql://[user]:[password]@[host]:[port]/[database]
```

**Solutions**:

**Option 1**: Start PostgreSQL
```bash
# macOS (Homebrew)
brew services start postgresql

# Linux (systemd)
sudo systemctl start postgresql

# Docker
docker run -d \
  -e POSTGRES_USER=waddlebot \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=waddlebot \
  -p 5432:5432 \
  postgres:14
```

**Option 2**: Verify credentials
```bash
# Test with different credentials
psql -h localhost -U waddlebot -W -d waddlebot

# Check .env file
cat .env | grep DATABASE_URL

# Correct format in .env:
# DATABASE_URL=postgresql://waddlebot:password@localhost:5432/waddlebot
```

**Option 3**: Fix connection string
```bash
# If using different host/port
export DATABASE_URL=postgresql://waddlebot:password@db.example.com:5432/waddlebot

# If using different database
export DATABASE_URL=postgresql://waddlebot:password@localhost:5432/waddlebot_prod

python3 app.py
```

---

### Database Timeout

**Symptom**: `Error: query timeout` or `connection pool exhausted`

**Root Cause**: Slow queries, connection pool too small, deadlocks

**Debug Steps**:
```bash
# Check active connections
psql -c "SELECT count(*) FROM pg_stat_activity;"

# Find slow queries
psql -c "SELECT query, mean_exec_time FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 5;"

# Check pool settings
python3 -c "from config import Config; c = Config(); print(f'Pool: {c.DB_POOL_SIZE}, Recycle: {c.DB_POOL_RECYCLE}')"

# Check connection string
echo $DATABASE_URL
```

**Solutions**:

**Option 1**: Increase connection pool
```bash
# In .env
DB_POOL_SIZE=20

# Or environment variable
export DB_POOL_SIZE=20

python3 app.py
```

**Option 2**: Recycle connections more frequently
```bash
# In .env
DB_POOL_RECYCLE=1800  # 30 minutes instead of 1 hour

export DB_POOL_RECYCLE=1800
python3 app.py
```

**Option 3**: Add database indexes
```bash
psql -d waddlebot << 'EOF'
CREATE INDEX idx_stream_configs_community_id ON stream_configs(community_id);
CREATE INDEX idx_destinations_config_id ON stream_destinations(config_id);
CREATE INDEX idx_status_config_id ON stream_status(config_id);
EOF
```

---

## Streaming Issues

### Stream Timeout

**Symptom**: Stream disconnects after N minutes or encoder reports "connection lost"

**Root Cause**: Network instability, buffer overrun, or idle connection timeout

**Debug Steps**:
```bash
# Check stream status
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8092/api/v1/stream/status/1

# Monitor real-time bitrate
ffprobe -show_format rtmp://localhost:8092/live/test-key

# Check encoder logs
# (In OBS: View → Logs)

# Monitor module logs
docker logs -f video-proxy

# Check network connectivity
ping -c 5 destination-platform.com

# Check NAT/firewall on encoder side
mtr destination-platform.com
```

**Solutions**:

**Option 1**: Increase timeouts
```bash
# In .env
HTTP_TIMEOUT=60
GRPC_TIMEOUT=60

python3 app.py
```

**Option 2**: Check encoder settings
- Reduce bitrate (less likely to timeout)
- Enable reconnect on error
- Increase retry count

**Option 3**: Network optimization
```bash
# Check bandwidth
iperf3 -c destination-platform.com

# Reduce video quality
# In OBS: decrease resolution or bitrate

# Use TCP instead of UDP if available
```

---

### Destination Not Receiving Stream

**Symptom**: Stream active locally, but destination shows "no data" or "offline"

**Root Cause**: Destination URL invalid, credentials wrong, or proxy not pushing

**Debug Steps**:
```bash
# Get destination details
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8092/api/v1/stream/destinations/1

# Verify destination URL is reachable
curl -I rtmp://live.twitch.tv/app

# Check if proxy can connect to destination
# (add verbose logging to module)

# Test direct RTMP connection
ffmpeg -f lavfi -i testsrc=size=1280x720:duration=10 \
       -f lavfi -i sine=frequency=1000:duration=10 \
       -c:v libx264 -preset ultrafast \
       -f flv "rtmp://live.twitch.tv/app/[stream-key]"

# Check module logs for push errors
docker logs video-proxy | grep -i error
```

**Solutions**:

**Option 1**: Verify destination credentials
```bash
# Get destination from API
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8092/api/v1/stream/destinations/1

# Verify stream key is correct (masked in response)
# Check with platform dashboard directly
```

**Option 2**: Re-add destination with correct URL
```bash
# Delete old destination
curl -X DELETE -H "Authorization: Bearer $TOKEN" \
  http://localhost:8092/api/v1/stream/destinations/1

# Add new destination with verified URL
curl -X POST -H "Authorization: Bearer $TOKEN" \
  http://localhost:8092/api/v1/stream/destinations \
  -d '{
    "config_id": 1,
    "platform": "twitch",
    "rtmp_url": "rtmp://live.twitch.tv/app",
    "stream_key": "verified-stream-key",
    "max_resolution": "1080p"
  }'
```

**Option 3**: Check if force_cut is enabled
```bash
# Get destination details
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8092/api/v1/stream/destinations/1

# If "force_cut": true, toggle it off
curl -X PUT -H "Authorization: Bearer $TOKEN" \
  http://localhost:8092/api/v1/stream/destinations/1/force-cut
```

---

## Authentication Problems

### JWT Invalid Token

**Symptom**: `401 Unauthorized - Invalid or expired token`

**Root Cause**: Token malformed, expired, signed with wrong key, or missing

**Debug Steps**:
```bash
# Check token format
echo $TOKEN | cut -d'.' -f1 | base64 -d | python3 -m json.tool

# Verify token isn't expired
python3 << 'EOF'
import jwt
import json

token = "your-token-here"
decoded = jwt.decode(token, options={"verify_signature": False})
print(json.dumps(decoded, indent=2, default=str))
EOF

# Check JWT_SECRET_KEY
echo $JWT_SECRET_KEY

# Verify request header format
curl -v -H "Authorization: Bearer $TOKEN" http://localhost:8092/health
```

**Solutions**:

**Option 1**: Generate valid token
```bash
python3 << 'EOF'
from datetime import datetime, timedelta
import jwt

payload = {
    'sub': 'admin',
    'exp': datetime.utcnow() + timedelta(hours=1),
    'iat': datetime.utcnow()
}
token = jwt.encode(
    payload,
    'jwt-secret-change-in-production',
    algorithm='HS256'
)
print(token)
EOF
```

**Option 2**: Verify JWT_SECRET_KEY matches
```bash
# In app.py, JWT is signed with:
# jwt.encode(payload, config.JWT_SECRET_KEY, algorithm='HS256')

# Ensure JWT_SECRET_KEY environment variable is set
echo $JWT_SECRET_KEY

# Regenerate token with correct key
python3 << 'EOF'
import os
from datetime import datetime, timedelta
import jwt

secret = os.getenv('JWT_SECRET_KEY', 'jwt-secret-change-in-production')
payload = {
    'sub': 'admin',
    'exp': datetime.utcnow() + timedelta(hours=1)
}
token = jwt.encode(payload, secret, algorithm='HS256')
print(token)
EOF
```

**Option 3**: Check header format
```bash
# Correct format
curl -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  http://localhost:8092/api/v1/stream/config/test

# Incorrect (will fail)
curl -H "Authorization: $TOKEN" ...  # Missing "Bearer " prefix
curl -H "Bearer: $TOKEN" ...         # Wrong header name
```

---

### Missing Authorization Header

**Symptom**: `401 Unauthorized - Missing or invalid Authorization header`

**Root Cause**: Authorization header not included in request

**Debug Steps**:
```bash
# Check request headers with curl -v
curl -v http://localhost:8092/api/v1/stream/config/test

# Should show request headers including Authorization
```

**Solutions**:

**Option 1**: Include Authorization header
```bash
# Generate token
TOKEN=$(python3 -c "import jwt; from datetime import datetime, timedelta; print(jwt.encode({'sub': 'admin', 'exp': datetime.utcnow() + timedelta(hours=1)}, 'jwt-secret-change-in-production', algorithm='HS256'))")

# Make request with header
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8092/api/v1/stream/config/test
```

**Option 2**: Health check (no auth required)
```bash
# This endpoint doesn't require authentication
curl http://localhost:8092/health
```

---

## Configuration Errors

### Missing Required Environment Variable

**Symptom**: `ValueError: DATABASE_URL must be set` or similar at startup

**Root Cause**: Required configuration variable not set

**Debug Steps**:
```bash
# List all critical vars
env | grep -E "DATABASE_URL|JWT_SECRET_KEY|GRPC_PORT|MODULE_PORT"

# Check .env file
cat .env

# Test config loading
python3 << 'EOF'
from config import Config
config = Config()
try:
    config.validate()
    print("Config valid")
except ValueError as e:
    print(f"Config error: {e}")
EOF
```

**Solutions**:

**Option 1**: Set environment variable
```bash
export DATABASE_URL=postgresql://waddlebot:password@localhost:5432/waddlebot
python3 app.py
```

**Option 2**: Use .env file
```bash
# Create .env from example
cp .env.example .env

# Edit .env with your values
nano .env

# Run (loads .env automatically if using python-dotenv)
python3 app.py
```

**Option 3**: Load .env manually
```bash
# In Python
from dotenv import load_dotenv
load_dotenv('.env')

# Then run
python3 app.py
```

---

### Invalid Configuration Value

**Symptom**: `ValueError: Invalid MODULE_PORT: 99999`

**Root Cause**: Configuration value out of valid range

**Debug Steps**:
```bash
# Check current value
echo $MODULE_PORT

# Check validation rules in config.py
python3 << 'EOF'
from config import Config
config = Config()
print(f"MODULE_PORT: {config.MODULE_PORT} (range: 1-65535)")
print(f"GRPC_PORT: {config.GRPC_PORT} (range: 1-65535)")
print(f"DB_POOL_SIZE: {config.DB_POOL_SIZE} (range: 1-50)")
EOF
```

**Solutions**:

**Option 1**: Use valid value
```bash
# Valid port range: 1-65535
export MODULE_PORT=8092

# Valid pool size: 1-50
export DB_POOL_SIZE=10

python3 app.py
```

**Option 2**: Remove custom value (use default)
```bash
unset MODULE_PORT
unset GRPC_PORT
python3 app.py
```

---

## Performance Issues

### High CPU Usage

**Symptom**: Module using 100% CPU, unresponsive

**Root Cause**: Tight loop, infinite recursion, or transcoding CPU-bound

**Debug Steps**:
```bash
# Check CPU usage
top -p $(pgrep -f "python3 app.py")

# Check active threads
python3 << 'EOF'
import threading
print(f"Active threads: {threading.active_count()}")
for thread in threading.enumerate():
    print(f"  - {thread.name}")
EOF

# Check module logs
docker logs video-proxy

# Check if transcoding is active
# (should correlate with CPU usage)
```

**Solutions**:

**Option 1**: Reduce transcoding workload
```bash
# In destinations, lower target resolution
curl -X POST -H "Authorization: Bearer $TOKEN" \
  http://localhost:8092/api/v1/stream/destinations \
  -d '{
    "config_id": 1,
    "platform": "youtube",
    "rtmp_url": "...",
    "stream_key": "...",
    "max_resolution": "720p"  # Instead of 1080p
  }'
```

**Option 2**: Limit concurrent streams
```bash
# Kill least important streams
# Or reduce number of active streams
```

**Option 3**: Use more efficient codec
```bash
# x264 is faster than x265
# AV1 is slowest
# Configure in MarchProxy upstream
```

---

### Memory Leak

**Symptom**: Memory usage increases over time, never freed

**Root Cause**: Circular references, unclosed connections, or cache growth

**Debug Steps**:
```bash
# Monitor memory
watch -n 1 'ps aux | grep python3 | grep -v grep'

# Check for connection leaks
python3 << 'EOF'
from app import db
# Connection pool should be stable
print(f"Pool size: {db.pool.size()}")
EOF

# Generate memory profile
python3 -m memory_profiler app.py
```

**Solutions**:

**Option 1**: Restart module periodically
```bash
# Docker restart policy
docker run --restart=unless-stopped ...

# Kubernetes liveness probe
livenessProbe:
  httpGet:
    path: /health
    port: 8092
  initialDelaySeconds: 30
  periodSeconds: 10
  failureThreshold: 3
```

**Option 2**: Recycle connections
```bash
# In .env
DB_POOL_RECYCLE=1800  # Recycle every 30 minutes

# Force reconnection
python3 << 'EOF'
from app import db
db.close()
db = DAL(config.DATABASE_URL)
EOF
```

---

## Destination Integration

### Twitch Connection Failed

**Symptom**: Destination added but Twitch shows "offline"

**Root Cause**: Invalid stream key, server timeout, or bandwidth limits

**Debug Steps**:
```bash
# Verify stream key from Twitch dashboard
# https://dashboard.twitch.tv/u/[username]/settings/stream

# Test direct RTMP connection
ffmpeg -f lavfi -i testsrc=size=1280x720:duration=10 \
       -c:v libx264 -preset ultrafast \
       -f flv "rtmp://live.twitch.tv/app/[your-stream-key]"

# Check module logs for Twitch errors
docker logs video-proxy | grep -i twitch
```

**Solutions**:
- Verify stream key from Twitch dashboard
- Check internet bandwidth (Twitch requires stable upload)
- Regenerate stream key and re-add destination

---

### YouTube Connection Failed

**Symptom**: "Stream offline" despite active broadcast

**Root Cause**: Wrong RTMP endpoint, stale stream key, or YouTube API limits

**Debug Steps**:
```bash
# Verify from YouTube Studio
# https://studio.youtube.com/

# Check endpoint: should be rtmp://a.rtmp.youtube.com/live2
# (not rtmp://stream.youtube.com/)

# Verify stream key hasn't expired
```

**Solutions**:
- Use correct endpoint: `rtmp://a.rtmp.youtube.com/live2`
- Regenerate stream key from YouTube Studio
- Enable content restrictions if necessary

---

## Debug Logging

### Enable Debug Logging

```bash
# In .env
LOG_LEVEL=DEBUG

# Or environment variable
export LOG_LEVEL=DEBUG

python3 app.py
```

### View Logs in Docker

```bash
# Follow logs in real-time
docker logs -f video-proxy

# Last 100 lines
docker logs --tail 100 video-proxy

# Since specific time
docker logs --since 10m video-proxy
```

### Save Logs to File

```bash
# Redirect stderr and stdout
python3 app.py > app.log 2>&1

# Or with Docker
docker logs video-proxy > logs.txt 2>&1
```

---

## Quick Diagnostic Commands

```bash
# Health check
curl http://localhost:8092/health

# Check database
python3 -c "from app import db; db.executesql('SELECT 1'); print('DB OK')"

# Generate JWT token
python3 -c "import jwt; from datetime import datetime, timedelta; print(jwt.encode({'sub': 'admin', 'exp': datetime.utcnow() + timedelta(hours=1)}, 'jwt-secret-change-in-production', algorithm='HS256'))"

# Check configuration
python3 -c "from config import Config; c = Config(); c.validate(); print('Config OK')"

# List active streams
curl -H "Authorization: Bearer $TOKEN" http://localhost:8092/api/v1/stream/config

# Check gRPC
grpcurl -plaintext localhost:50065 list

# Test RTMP ingest
ffmpeg -f lavfi -i testsrc=size=1280x720:duration=5 \
       -f lavfi -i sine=frequency=1000:duration=5 \
       -c:v libx264 -preset ultrafast \
       -f flv "rtmp://localhost:8092/live/test-key"

# Monitor module
docker stats video-proxy

# Check logs
docker logs video-proxy | tail -50
```

---

**Last Updated**: 2026-02-16
**Repository**: github.com/penguintechinc/waddlebot
