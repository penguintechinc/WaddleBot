# Server Manager Interaction Module - Troubleshooting Guide

## Common Errors & Solutions

---

### Connection Errors

#### Error: "Connection refused" on RCON connect

**Symptom:** `connect-test` returns `"error": "Connection refused"` or `CONNECT_FAILED`

**Cause:** RCON port is closed, host is wrong, or the game server is offline.

**Debug steps:**
```bash
# Test TCP reachability from module container
docker exec server-manager-interaction \
  python3 -c "import socket; s=socket.socket(); s.settimeout(5); s.connect(('rust.example.com', 28016)); print('OK')"

# Check if RCON is enabled in the game server config
# Rust: server.rcon.port, server.rcon.password in server startup args
# Minecraft: rcon.enable=true in server.properties

# Check firewall rules — RCON port must be open to WaddleBot's egress IP
```

**Solutions:**
- Verify the host and RCON port (separate from game port for most games)
- Confirm RCON is enabled in the game server's configuration file
- Check that the game server's firewall allows inbound TCP on the RCON port from the module's IP

---

#### Error: "Authentication failed"

**Symptom:** Connection succeeds but `connect-test` returns `AUTH_FAILED`

**Cause:** Wrong RCON password, or the password was not saved with the correct encryption key.

**Debug steps:**
```bash
# Verify the password manually from outside WaddleBot
# For Minecraft RCON:
mcrcon -H mc.example.com -P 25575 -p "the_password" "list"

# Check the encryption key is the same in hub backend and this module
docker exec hub-backend env | grep RCON_ENCRYPTION_KEY
docker exec server-manager-interaction env | grep RCON_ENCRYPTION_KEY
```

**Solutions:**
- Re-enter the server password via the hub frontend (this re-encrypts with the current key)
- Confirm the RCON password in the game server's configuration matches what was entered

---

#### Error: "SSRF_BLOCKED" — Host resolves to private IP

**Symptom:** `connect-test` returns `SSRF_BLOCKED`

**Cause:** The hostname provided resolves to a private/loopback IP (e.g., `192.168.x.x`, `10.x.x.x`, `127.0.0.1`). The module blocks these to prevent server-side request forgery.

**Solution:** Only public IP addresses or hostnames that resolve to public IPs are permitted for game server connections. If running WaddleBot and the game server in the same private network with a legitimate use case, contact the platform administrator to configure an allowlist.

---

#### Error: "Ice.ConnectionRefused" (Mumble)

**Symptom:** Mumble connect fails with an Ice RPC error

**Debug steps:**
```bash
# Check Mumble server Ice configuration
# In murmur.ini: ice="tcp -h 127.0.0.1 -p 6502"
# The Ice port (default 6502) must be open to the module

# Test connectivity
docker exec server-manager-interaction \
  python3 -c "
import Ice
ic = Ice.initialize()
base = ic.stringToProxy('Meta:tcp -h mumble.example.com -p 6502')
print(base.ice_ping())"
```

**Solutions:**
- Confirm Ice is enabled in `murmur.ini` and the Ice port is open
- Mumble's Ice interface must be accessible from the module container

---

#### Error: TeamSpeak "TS3QueryError: error id=520" (flood ban)

**Symptom:** TeamSpeak operations fail after repeated quick calls

**Cause:** TeamSpeak flood protection triggered by rapid ServerQuery connections.

**Solutions:**
- Add the module's IP to the ServerQuery whitelist in `ts3server.ini`: `query_ip_whitelist=query_ip_whitelist.txt`
- Reduce request frequency if polling for status

---

### Encryption Errors

#### Error: "ENCRYPT_KEY_MISMATCH" — Cannot decrypt credentials

**Symptom:** All RCON operations fail with `ENCRYPT_KEY_MISMATCH` or decryption exception in logs

**Cause:** The `RCON_ENCRYPTION_KEY` in this module does not match the key used by the hub backend to encrypt the credentials.

**Debug steps:**
```bash
# Compare keys (first 8 chars only — do not log full key)
docker exec hub-backend env | grep RCON_ENCRYPTION_KEY | cut -c1-20
docker exec server-manager-interaction env | grep RCON_ENCRYPTION_KEY | cut -c1-20
```

**Solutions:**
1. Ensure both services have the same `RCON_ENCRYPTION_KEY` value
2. After fixing the key, re-save all server credentials via the hub frontend (the old ciphertext cannot be decrypted)

---

#### Error: "Invalid key length" on startup

**Symptom:** Module crashes at startup with key length error

**Cause:** `RCON_ENCRYPTION_KEY` is not exactly 64 hexadecimal characters.

**Solution:**
```bash
# Generate a valid key
openssl rand -hex 32
# Verify length
echo -n "$RCON_ENCRYPTION_KEY" | wc -c   # Must be 64
```

---

### Database Errors

#### Error: "Connection refused" to PostgreSQL

**Symptom:** Module fails to start, logs show `psycopg2.OperationalError: connection refused`

**Debug steps:**
```bash
# Check PostgreSQL is running
docker ps | grep postgres

# Test connection directly
docker exec server-manager-interaction \
  python3 -c "import psycopg2; psycopg2.connect('$DATABASE_URL'); print('OK')"

# Verify DATABASE_URL is set
docker exec server-manager-interaction env | grep DATABASE_URL
```

**Solutions:**
- Confirm PostgreSQL is running: `docker restart waddlebot-postgres`
- Verify `DATABASE_URL` hostname resolves from the module container

---

#### Error: "relation server_ban_sync does not exist"

**Symptom:** Server manager operations fail with missing table errors

**Cause:** Migration `055_server_manager.sql` has not been applied.

**Solution:**
```bash
psql $DATABASE_URL -f /home/penguin/code/waddlebot/config/postgres/migrations/055_server_manager.sql

# Verify tables exist
psql $DATABASE_URL -c "\dt server_ban_sync"
psql $DATABASE_URL -c "\dt rcon_command_log"
psql $DATABASE_URL -c "\dt server_access_policies"
psql $DATABASE_URL -c "\dt server_access_log"
```

---

### Module Startup Issues

#### Error: Module exits immediately

**Symptom:** Container starts and immediately exits (exit code 1)

**Debug steps:**
```bash
docker logs server-manager-interaction

# Common causes visible in logs:
# - Missing RCON_ENCRYPTION_KEY
# - DATABASE_URL not reachable
# - Port already in use
```

**Solution (port conflict):**
```bash
lsof -i :8098     # Find conflicting process
# Or change MODULE_PORT if needed
```

---

#### Error: Health check fails

**Symptom:** `curl http://localhost:8098/health` returns 502 or connection refused

**Debug steps:**
```bash
# Is the container running?
docker ps | grep server-manager

# Is Hypercorn listening?
docker exec server-manager-interaction ss -tlnp | grep 8098

# View recent logs
docker logs --tail 50 server-manager-interaction
```

**Solution:** Restart the container and check logs:
```bash
docker restart server-manager-interaction
docker logs -f server-manager-interaction
```

---

### Enforcement & Policy Issues

#### Problem: Players not being kicked despite low reputation scores

**Symptom:** Enforcement pass reports 0 kicked even for known low-reputation players

**Debug steps:**
```bash
# Check that a policy exists for the server
curl http://localhost:8098/api/v1/server-manager/42/servers/7/policy

# Check the thresholds — default kick threshold is 400
# A player with score 390 should be kicked

# Manually trigger enforcement and review output
curl -X POST http://localhost:8098/api/v1/server-manager/42/servers/7/enforce \
  -d '{"actor_user_id": 1}'

# Check the access log for enforcement actions
curl "http://localhost:8098/api/v1/server-manager/42/servers/7/access-log?limit=20"
```

**Solutions:**
- Verify the policy exists and thresholds are set (`PUT .../policy`)
- Confirm the player's reputation score is actually being returned (check reputation_module connectivity)
- Enable DEBUG logging to see per-player score evaluations

---

#### Problem: Ban sync not propagating to other servers

**Symptom:** `synced_servers` in ban response is empty or missing servers

**Debug steps:**
```sql
-- Check server_ban_sync table
SELECT * FROM server_ban_sync
WHERE community_id = 42
ORDER BY created_at DESC
LIMIT 10;

-- Look for rows with synced = false (sync attempted but failed)
SELECT * FROM server_ban_sync WHERE synced = false;
```

**Solutions:**
- Verify all target servers are online and reachable
- Check `rcon_command_log` for ban command failures on target servers
- Ensure `sync_to_all_servers: true` was included in the ban request

---

### Performance Issues

#### Problem: RCON commands are slow (>500 ms)

**Symptom:** Commands consistently take 500ms+

**Cause:** Connection pool miss — cold connections on every request.

**Debug:**
```bash
# Enable DEBUG logging to see connection pool hits/misses
docker run -e LOG_LEVEL=DEBUG ...

# Look for log lines like:
# "Pool miss for server_id=7 — opening new connection"
```

**Solutions:**
- Increase `RCON_CONNECTION_TTL` to keep connections alive longer
- Ensure servers are reachable with low latency (same region preferred)

---

#### Problem: Module memory growing over time

**Symptom:** `docker stats` shows memory increasing steadily

**Cause:** RCON connection objects not being released (pool leak) or Ice communicators not torn down.

**Solutions:**
```bash
# Restart to clear pool
docker restart server-manager-interaction

# Monitor after restart
docker stats server-manager-interaction --no-stream
```

---

## Debugging Techniques

### View Live Logs

```bash
# Follow logs
docker logs -f server-manager-interaction

# Last 100 lines
docker logs --tail 100 server-manager-interaction

# Filter for errors only
docker logs server-manager-interaction 2>&1 | grep -i error
```

### Enable Debug Logging

```bash
docker run -e LOG_LEVEL=DEBUG ... waddlebot/server-manager-interaction:latest
```

Debug mode logs:
- All RCON commands and raw responses
- Connection pool hit/miss events
- Encryption/decryption operations (no key or plaintext values)
- Enforcement score evaluations

### Inspect Container Environment

```bash
docker exec server-manager-interaction env | grep -E "^(DATABASE|MODULE|RCON|SECURITY)"
```

### Test Connectivity from Inside the Container

```bash
docker exec -it server-manager-interaction /bin/bash

# Test TCP to a game server
python3 -c "import socket; s=socket.socket(); s.settimeout(5); s.connect(('rust.example.com', 28016)); print('OK')"

# Test database
python3 -c "import psycopg2; c=psycopg2.connect('$DATABASE_URL'); print('DB OK')"
```

### Check Database Tables

```bash
psql $DATABASE_URL -c "SELECT COUNT(*) FROM rcon_command_log WHERE created_at > NOW() - INTERVAL '1 hour';"
psql $DATABASE_URL -c "SELECT * FROM server_access_log ORDER BY created_at DESC LIMIT 5;"
psql $DATABASE_URL -c "SELECT server_id, synced, COUNT(*) FROM server_ban_sync GROUP BY 1,2;"
```

---

## Log Locations

| Context | Path |
|---------|------|
| Inside container | `/var/log/waddlebotlog/server_manager_interaction_module.log` |
| Docker volume (host) | `/var/log/waddlebotlog/server_manager_interaction_module.log` |
| Docker stdout | `docker logs server-manager-interaction` |

---

## Quick Diagnostics Checklist

```bash
# 1. Is the module running?
docker ps | grep server-manager

# 2. Is it healthy?
curl -s http://localhost:8098/health | python3 -m json.tool

# 3. Is the database reachable?
docker exec server-manager-interaction \
  python3 -c "import psycopg2; psycopg2.connect('$DATABASE_URL'); print('DB OK')"

# 4. Is the encryption key set and 64 chars?
docker exec server-manager-interaction \
  sh -c 'echo -n $RCON_ENCRYPTION_KEY | wc -c'

# 5. Is the migration applied?
psql $DATABASE_URL -c "\dt rcon_command_log"

# 6. Can the module reach the security core?
docker exec server-manager-interaction \
  python3 -c "import httpx; r=httpx.get('$SECURITY_CORE_URL/health'); print(r.status_code)"
```

---

**Module**: server_manager_interaction_module
**Version**: 1.0.0
**Last Updated**: 2026-02-24
