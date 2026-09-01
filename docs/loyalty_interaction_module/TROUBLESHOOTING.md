# Loyalty Interaction Module — Troubleshooting Guide

Solutions to common issues, error messages, and operational problems.

## Table of Contents

1. [Startup Issues](#startup-issues)
2. [Database Errors](#database-errors)
3. [Economic Issues](#economic-issues)
4. [Game & Duel Problems](#game--duel-problems)
5. [Giveaway Issues](#giveaway-issues)
6. [Performance Problems](#performance-problems)
7. [Authentication & Security](#authentication--security)
8. [Common Error Messages](#common-error-messages)

## Startup Issues

### Module Fails to Start

**Problem:** Container exits immediately with error

**Solution:**
1. Check logs: `docker logs loyalty-module`
2. Verify DATABASE_URL is set and valid
3. Ensure PostgreSQL is running and accessible
4. Check port 8032 is not already in use

```bash
# Test PostgreSQL connection
psql postgresql://user:pass@host:5432/db

# Check if port is in use
lsof -i :8032

# Start with debug logging
LOG_LEVEL=DEBUG python app.py
```

### Module Starts but Health Check Fails

**Problem:** `curl http://localhost:8032/health` returns 500 or timeout

**Solution:**
1. Verify database migration tables exist:
```sql
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name LIKE 'loyalty%';
```

2. If tables missing, initialize schema:
```bash
# Manual initialization
python -c "from app import app, startup; asyncio.run(startup())"
```

3. Check database connectivity from container:
```bash
docker exec loyalty-module psql -h postgres -U waddlebot -d waddlebot -c "SELECT 1"
```

### Memory Usage Excessive

**Problem:** Container uses >1GB RAM on startup

**Solution:**
1. Check Redis is enabled (uses memory):
```bash
docker exec loyalty-module redis-cli INFO memory
```

2. Disable Redis if not needed:
```bash
# Remove REDIS_URL from environment
docker run ... -e REDIS_URL="" ...
```

3. Set memory limits:
```yaml
services:
  loyalty:
    mem_limit: 512m
    memswap_limit: 512m
```

## Database Errors

### "PostgreSQL Connection Refused"

**Error:**
```
psycopg2.OperationalError: could not connect to server: Connection refused
```

**Solution:**
1. Verify PostgreSQL is running:
```bash
docker ps | grep postgres
docker logs postgres-container
```

2. Check DATABASE_URL format:
```bash
# Correct format
postgresql://user:password@host:5432/database

# Wrong format (missing ://)
postgressql://...  ❌
postgresql://...   ✓
```

3. Test connection manually:
```bash
psql "postgresql://waddlebot:secret@localhost:5432/waddlebot"
```

4. Check firewall (if remote database):
```bash
nc -zv postgres.example.com 5432
```

### "Relation loyalty_balances Does Not Exist"

**Error:**
```
psycopg2.ProgrammingError: relation "loyalty_balances" does not exist
```

**Solution:**
1. Check if tables exist:
```sql
\dt loyalty*
```

2. If missing, create schema (run migrations):
```bash
# Connect to database
psql postgresql://user:pass@host/db

# Create tables
CREATE TABLE loyalty_balances (
  id SERIAL PRIMARY KEY,
  community_id INTEGER NOT NULL,
  platform VARCHAR(50) NOT NULL,
  platform_user_id VARCHAR(255) NOT NULL,
  balance INTEGER NOT NULL DEFAULT 0,
  lifetime_earned INTEGER NOT NULL DEFAULT 0,
  lifetime_spent INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(community_id, platform, platform_user_id)
);

-- Add other tables...
```

3. Or use initialization script:
```bash
python scripts/init_db.py
```

### "Too Many Connections"

**Error:**
```
psycopg2.OperationalError: too many connections for role "waddlebot"
```

**Solution:**
1. Close existing connections:
```bash
# View connections
SELECT * FROM pg_stat_activity WHERE datname = 'waddlebot';

# Kill idle connections
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE state = 'idle'
AND datname = 'waddlebot'
AND query_start < now() - interval '10 minutes';
```

2. Reduce connection pool size:
```bash
# In config.py or environment
# Add pool size limit
asyncpg.create_pool(..., max_size=10)
```

3. Increase PostgreSQL max_connections:
```sql
ALTER SYSTEM SET max_connections = 200;
SELECT pg_reload_conf();
```

### "Deadlock Detected"

**Error:**
```
psycopg2.errors.InFailedSqlTransaction: current transaction is aborted
```

**Solution:**
1. Occurs when concurrent updates conflict
2. Review transaction isolation:
```python
# In services, use explicit transactions
async with transaction:
    await update_balance(...)
    await insert_transaction(...)
```

3. Check for long-running queries:
```sql
SELECT * FROM pg_stat_activity
WHERE state = 'active'
ORDER BY query_start;
```

4. Increase lock timeout:
```sql
SET lock_timeout = '10s';  -- Kill queries holding locks >10s
```

## Economic Issues

### Duplicate Points / Double Charging

**Problem:** User earned/charged twice for single action

**Causes:**
1. Webhook called twice (router issue)
2. Race condition in concurrent requests
3. Transaction rollback retry

**Solution:**
1. Add idempotency key to requests:
```python
# In app.py, add idempotency check
@app.before_request
async def check_idempotency():
    if request.method == 'POST':
        idempotency_key = request.headers.get('Idempotency-Key')
        if idempotency_key:
            # Check if already processed
            cached = await redis.get(f"idempotency:{idempotency_key}")
            if cached:
                return cached  # Return previous result
```

2. Database constraints prevent duplicates:
```sql
-- Prevent duplicate transactions
CREATE UNIQUE INDEX idx_transaction_idempotency
  ON loyalty_transactions(community_id, idempotency_key)
  WHERE idempotency_key IS NOT NULL;
```

3. Check transaction logs:
```sql
SELECT * FROM loyalty_transactions
WHERE user_id = 'user123'
AND created_at > now() - interval '1 minute'
ORDER BY created_at DESC;
```

### Balance Mismatch

**Problem:** Reported balance doesn't match transaction sum

**Symptoms:**
- `SELECT balance FROM loyalty_balances` ≠ `SELECT SUM(amount) FROM loyalty_transactions`

**Solution:**
1. Audit transaction history:
```sql
SELECT user_id, SUM(amount) as total_earned
FROM loyalty_transactions
WHERE type = 'earn'
GROUP BY user_id;
```

2. Recalculate from transactions (careful!):
```sql
WITH calculated AS (
  SELECT
    community_id,
    platform,
    platform_user_id,
    SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as earned,
    SUM(CASE WHEN amount < 0 THEN -amount ELSE 0 END) as spent,
    SUM(amount) as balance
  FROM loyalty_transactions
  GROUP BY community_id, platform, platform_user_id
)
UPDATE loyalty_balances b
SET
  balance = c.balance,
  lifetime_earned = c.earned,
  lifetime_spent = c.spent
FROM calculated c
WHERE b.community_id = c.community_id
  AND b.platform = c.platform
  AND b.platform_user_id = c.platform_user_id;
```

3. Check for negative balances:
```sql
-- Users below zero (shouldn't happen)
SELECT * FROM loyalty_balances WHERE balance < 0;
```

### Inflation / Points Too Plentiful

**Problem:** Economy has too many points in circulation

**Solution:**
1. Reduce earning rates:
```bash
export DEFAULT_EARN_CHAT=0              # Disable chat earning
export DEFAULT_EARN_SUB_T2=500          # Cut subscription bonus
export DEFAULT_EARN_CHAT_COOLDOWN=300  # 5 min cooldown
```

2. Increase minimum bet:
```bash
export MIN_BET=100   # Force higher stakes
```

3. Temporary wipe (last resort):
```bash
# Wipe all points (DANGEROUS!)
curl -X DELETE http://localhost:8032/api/v1/loyalty/currency/1/wipe \
  -H "Authorization: Bearer admin-token"
```

4. Monitor inflation:
```sql
-- Check daily earning volume
SELECT DATE(created_at), COUNT(*), SUM(amount)
FROM loyalty_transactions
WHERE type = 'earn'
AND community_id = 1
GROUP BY DATE(created_at)
ORDER BY created_at DESC;
```

### Deflation / Points Too Scarce

**Problem:** Users can't earn enough points to gamble/shop

**Solution:**
1. Increase earning rates:
```bash
export DEFAULT_EARN_CHAT=3
export DEFAULT_EARN_WATCH_TIME=5
export DEFAULT_EARN_SUB_T2=2000
```

2. Lower bet minimums:
```bash
export MIN_BET=5
```

3. Run bonus event:
```bash
# 2x multiplier weekend
export EARNING_MULTIPLIER=2.0
```

4. Grant starting balance:
```sql
-- Give new users starting balance
INSERT INTO loyalty_balances (community_id, platform, platform_user_id, balance, lifetime_earned)
VALUES (1, 'twitch', 'newuser', 500, 500)
ON CONFLICT DO NOTHING;
```

## Game & Duel Problems

### Duel Challenge Never Resolves

**Problem:** Duel stays in "pending" state forever

**Cause:** Opponent didn't accept before timeout

**Solution:**
1. Check duel status:
```sql
SELECT * FROM loyalty_duels WHERE status = 'pending'
AND created_at < now() - interval '10 minutes';
```

2. Auto-decline expired duels:
```sql
UPDATE loyalty_duels
SET status = 'declined'
WHERE status = 'pending'
AND expires_at < now();
```

3. Refund expired challenge (if not already):
```sql
WITH expired_duels AS (
  SELECT challenger_id, wager FROM loyalty_duels
  WHERE status = 'pending' AND expires_at < now()
)
UPDATE loyalty_balances
SET balance = balance + (SELECT wager FROM expired_duels LIMIT 1)
WHERE platform_user_id = (SELECT challenger_id FROM expired_duels LIMIT 1);
```

### Duel Winner/Loser Wrong

**Problem:** Wrong player won the duel

**Cause:** RNG algorithm or stat calculation bug

**Solution:**
1. Check equipped gear of both players:
```sql
SELECT u.user_id, i.item_id, g.name, g.stat_bonus
FROM loyalty_gear_inventory i
JOIN loyalty_gear_items g ON i.item_id = g.id
JOIN loyalty_duels d ON i.user_id = d.challenger_id OR i.user_id = d.opponent_id
WHERE d.id = 99;  -- Replace with duel ID
```

2. Review win probability calculation (in code):
```python
# In duel_service.py, check stat weighting
challenger_stats = calculate_stats(challenger_gear)
opponent_stats = calculate_stats(opponent_gear)
challenger_odds = challenger_stats / (challenger_stats + opponent_stats)
```

3. If consistently wrong, manual override:
```sql
-- Fix specific duel result
UPDATE loyalty_duels
SET winner_id = 'correct_player'
WHERE id = 99;

-- Re-process rewards
UPDATE loyalty_balances
SET balance = balance + 200
WHERE platform_user_id = 'correct_player';

UPDATE loyalty_balances
SET balance = balance - 200
WHERE platform_user_id = 'wrong_player';

-- Log correction
INSERT INTO loyalty_transactions (user_id, amount, reason)
VALUES ('correct_player', 200, 'Duel correction - dispute resolved');
```

### Game Never Responds

**Problem:** Slots/Coinflip/Roulette takes >10 seconds to respond

**Cause:** Database slow, RNG hanging, external API call

**Solution:**
1. Check database performance:
```bash
# Monitor slow queries
docker exec postgres psql -U waddlebot -d waddlebot -c "
  SELECT query, mean_time FROM pg_stat_statements
  ORDER BY mean_time DESC LIMIT 10;
"
```

2. Enable query logging:
```sql
ALTER DATABASE waddlebot SET log_min_duration_statement = 1000;  -- Log queries >1s
```

3. Increase timeout:
```python
# In config.py
QUERY_TIMEOUT = 30  # seconds
```

4. Check system resources:
```bash
# High CPU?
top

# Disk I/O slow?
iostat -x 1

# Memory pressure?
free -h
```

## Giveaway Issues

### Giveaway Won't Accept Entries

**Problem:** Entry button returns 409 Conflict

**Error:**
```json
{
  "error": "Giveaway not active or max entries reached",
  "error_code": "CONFLICT"
}
```

**Solution:**
1. Check giveaway status:
```sql
SELECT id, status, entry_count, max_entries, ends_at
FROM loyalty_giveaways
WHERE id = 42;
```

2. Verify not expired:
```sql
UPDATE loyalty_giveaways
SET status = 'ended'
WHERE ends_at < now()
AND status = 'active';
```

3. Check entry limit:
```sql
SELECT COUNT(*) FROM loyalty_giveaway_entries WHERE giveaway_id = 42;
-- If count >= max_entries, increase max_entries
UPDATE loyalty_giveaways SET max_entries = 1000 WHERE id = 42;
```

### Winner Not Drawing

**Problem:** Draw returns success but no winner selected

**Cause:** No entries in giveaway

**Solution:**
1. Check for entries:
```sql
SELECT COUNT(*) FROM loyalty_giveaway_entries WHERE giveaway_id = 42;
```

2. If zero entries:
   - Wait for users to enter
   - Manually add entries (testing only):
```sql
INSERT INTO loyalty_giveaway_entries (giveaway_id, platform, user_id)
VALUES (42, 'twitch', 'test_user');
```

3. Check winner drawing code (in giveaway_service.py)
```python
# Ensure RNG is working
import random
winner = random.choice(entries)
```

### Reputation Weighting Not Working

**Problem:** Giveaway ignores reputation_weighted flag

**Cause:** Reputation API not configured or unreachable

**Solution:**
1. Verify REPUTATION_API_URL set:
```bash
echo $REPUTATION_API_URL
# Should output: http://reputation:8021
```

2. Test reputation API:
```bash
curl http://reputation:8021/api/v1/reputation/1/user123
# Should return { "reputation": 750 }
```

3. If API unreachable, fallback to uniform random:
```python
# In giveaway_service.py
try:
    reputation = await get_reputation(user_id)
    weight = get_reputation_weight(reputation)
except:
    weight = 1.0  # Fall back to equal odds
```

4. Enable detailed logging:
```python
logger.debug(f"Drawing with reputation_weighted={reputation_weighted}")
logger.debug(f"User {winner_id} weight: {weight}")
```

## Performance Problems

### API Response Slow (>500ms)

**Problem:** Endpoint takes long time to respond

**Diagnosis:**
1. Check database query time:
```bash
# Enable query logging
docker exec postgres psql -U waddlebot -d waddlebot -c "
  SET log_min_duration_statement = 500;
"
```

2. Profile endpoint:
```python
# Add timing
import time
@app.route('/api/v1/loyalty/currency/...')
async def endpoint():
    start = time.time()
    result = await service.operation()
    duration = time.time() - start
    logger.info(f"Operation took {duration:.2f}s")
    return result
```

3. Check for N+1 queries:
```sql
-- Multiple similar queries?
SELECT query, calls FROM pg_stat_statements
WHERE query LIKE '%loyalty%'
ORDER BY calls DESC;
```

**Solutions:**
1. Add indexes:
```sql
CREATE INDEX idx_loyalty_balances_community_balance
  ON loyalty_balances(community_id, balance DESC);
```

2. Enable Redis caching:
```bash
export REDIS_URL=redis://redis:6379
```

3. Use connection pooling (asyncpg auto-pools)

4. Optimize queries:
```python
# Bad: Multiple queries
for user in users:
    await get_balance(user)

# Good: Batch query
await get_balances_batch(users)
```

### High Memory Usage

**Problem:** Container memory grows over time (memory leak)

**Solution:**
1. Check for unclosed connections:
```bash
# Monitor connection count
watch "psql -U waddlebot -d waddlebot -c 'SELECT count(*) FROM pg_stat_activity;'"
```

2. Force garbage collection:
```python
# In background task
import gc
gc.collect()
```

3. Limit Redis memory:
```bash
docker run ... redis redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
```

### Database CPU Maxed Out

**Problem:** PostgreSQL CPU 100% constantly

**Solution:**
1. Find expensive queries:
```sql
SELECT query, calls, mean_time
FROM pg_stat_statements
ORDER BY total_time DESC LIMIT 10;
```

2. Check for missing indexes:
```sql
-- Unused indexes
SELECT schemaname, tablename, indexname
FROM pg_indexes
WHERE idx_scan = 0;

-- Missing indexes (from query analysis)
CREATE INDEX idx_missing ON loyalty_balances(community_id, balance DESC);
```

3. Analyze/vacuum:
```sql
ANALYZE;  -- Update statistics
VACUUM;   -- Clean up
```

## Authentication & Security

### "Unauthorized" on Admin Endpoints

**Problem:** Admin endpoint returns 401 Unauthorized

**Solution:**
1. Verify auth token provided:
```bash
curl -H "Authorization: Bearer token123" http://localhost:8032/api/v1/loyalty/currency/1/add
```

2. Check token validity:
```python
# In auth_required decorator
def verify_token(token):
    try:
        payload = jwt.decode(token, SECRET_KEY)
        return payload
    except:
        return None
```

3. Use test token:
```bash
# Generate test token
python -c "
import jwt
token = jwt.encode({'user': 'admin'}, 'secret', algorithm='HS256')
print(token)
"
```

### Service-to-Service Auth Failing

**Problem:** Router can't call loyalty endpoints

**Solution:**
1. Verify SERVICE_API_KEY set:
```bash
echo $SERVICE_API_KEY
```

2. Add key to request header:
```bash
curl -H "X-API-Key: sk_loyalty_xxx" http://localhost:8032/api/v1/loyalty/...
```

3. Update router to send key:
```python
# In router
headers = {'X-API-Key': SERVICE_API_KEY}
async with httpx.AsyncClient() as client:
    response = await client.post(
        'http://loyalty:8032/api/v1/loyalty/...',
        headers=headers
    )
```

## Common Error Messages

### "Insufficient balance to place bet"

**Cause:** User balance < bet amount
**Fix:**
- User needs to earn/purchase more points
- Or reduce bet amount
- Or admin can add currency

### "Bet outside allowed range"

**Cause:** Bet < MIN_BET or > MAX_BET
**Fix:**
```bash
# Check current limits
MIN_BET=10 MAX_BET=10000

# Adjust bet within range
```

### "Giveaway not found"

**Cause:** Giveaway ID doesn't exist for community
**Fix:**
```sql
SELECT id FROM loyalty_giveaways WHERE community_id = 1;
```

### "Cannot transfer to yourself"

**Cause:** from_user_id == to_user_id
**Fix:** Specify different recipient

### "User not found"

**Cause:** User doesn't have any points/record yet
**Fix:**
```sql
INSERT INTO loyalty_balances (community_id, platform, platform_user_id, balance)
VALUES (1, 'twitch', 'user123', 0);
```

### "Duel timeout expired"

**Cause:** Opponent didn't respond within DUEL_TIMEOUT_MINUTES
**Fix:**
- Challenge expired, can create new challenge
- Or check DUEL_TIMEOUT_MINUTES setting (default 5 min)

---

**Last Updated:** 2026-02-16
