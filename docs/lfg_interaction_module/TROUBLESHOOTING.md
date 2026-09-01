# LFG Interaction Module - Troubleshooting Guide

## Quick Diagnostics

### Step 1: Check Module Health
```bash
curl -s http://localhost:8096/health | jq .
```

**Healthy Response**:
```json
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected",
  "uptime_seconds": 3600
}
```

**Unhealthy Responses**:
```json
{
  "status": "unhealthy",
  "database": "disconnected",
  "reason": "Failed to connect to PostgreSQL"
}
```

### Step 2: Check Logs
```bash
# Docker Compose
docker-compose logs -f interactive-lfg

# Kubernetes
kubectl logs -f deployment/lfg-module -n waddlebot

# Direct
tail -f /var/log/waddlebot/lfg-module.log
```

### Step 3: Test API Connectivity
```bash
curl -v http://localhost:8096/api/v1/lfg/posts \
  -H "Authorization: Bearer test-token" 2>&1 | head -20
```

---

## Common Issues & Solutions

### Issue 1: Module Won't Start - Port Already in Use

**Error**:
```
ERROR: Port 8096 is already in use
```

**Solution**:
```bash
# Find process using port
lsof -i :8096
# or
netstat -tlnp | grep 8096

# Kill the process
kill -9 <PID>

# Or use different port
export MODULE_PORT=8097
docker-compose up interactive-lfg
```

**Prevention**:
- Use high-numbered ports (8000+) to avoid system port conflicts
- In Kubernetes, Services handle port allocation automatically

---

### Issue 2: Database Connection Failed

**Error**:
```
ERROR: Failed to connect to postgresql://localhost:5432/waddlebot
could not connect to server: Connection refused
```

**Diagnosis**:
```bash
# Check if PostgreSQL is running
docker ps | grep postgres
ps aux | grep postgres

# Test connection directly
psql postgresql://postgres:password@localhost:5432/waddlebot -c "SELECT 1;"
```

**Solutions**:
1. **Start PostgreSQL**:
   ```bash
   docker-compose up -d postgres
   ```

2. **Verify connection string**:
   ```bash
   # Should be: postgresql://[user]:[password]@[host]:[port]/[db]
   echo $DATABASE_URL
   ```

3. **Check credentials**:
   ```bash
   # Verify user exists and has permissions
   docker exec -it postgres psql -U postgres -c "\du"
   ```

4. **Wait for PostgreSQL to be ready**:
   ```bash
   # May need to wait 10-30 seconds after starting
   docker-compose up -d postgres
   sleep 30
   docker-compose up interactive-lfg
   ```

5. **Check network (Kubernetes)**:
   ```bash
   kubectl get svc postgres -n waddlebot
   kubectl exec -it lfg-module-pod -- nc -zv postgres.waddlebot.svc.cluster.local 5432
   ```

---

### Issue 3: Migrations Failed

**Error**:
```
ERROR: Migration 001_create_tables.sql failed
Relation "lfg_posts" already exists
```

**Solution**:
```bash
# Option 1: Drop existing tables (development only)
docker-compose exec infra-postgres psql -U postgres -d waddlebot -c "
  DROP TABLE IF EXISTS lfg_joins CASCADE;
  DROP TABLE IF EXISTS lfg_posts CASCADE;
"

# Option 2: Disable auto-migration and run manually
export AUTO_MIGRATE=false
docker-compose up interactive-lfg

# Run migrations manually
psql $DATABASE_URL < migrations/001_create_tables.sql
```

**Prevention**:
- Use version-controlled migration files
- Always test migrations in staging first
- Keep idempotent migration scripts (use `CREATE TABLE IF NOT EXISTS`)

---

### Issue 4: Authentication/Authorization Failed

**Error**:
```json
{
  "status": "error",
  "error": "UNAUTHORIZED",
  "message": "Invalid token"
}
```

**Diagnosis**:
```bash
# 1. Check if token is present
curl -i http://localhost:8096/api/v1/lfg/posts

# Should return 401 without Authorization header

# 2. Verify token format
# Should be: Authorization: Bearer <token>
curl -H "Authorization: Bearer mytoken123" ...
```

**Solutions**:
1. **Obtain valid token**:
   ```bash
   # From Core API
   curl -X POST http://core-api:5000/auth/login \
     -d '{"email": "user@example.com", "password": "..."}' \
     | jq '.token'
   ```

2. **Verify Core API is accessible**:
   ```bash
   curl -s http://core-api:5000/health
   ```

3. **Check SECRET_KEY in both services**:
   ```bash
   # Must match between Core API and LFG Module
   echo $SECRET_KEY
   ```

4. **Check token expiry**:
   - Tokens expire after time
   - Obtain fresh token if needed

---

### Issue 5: Posts Not Appearing in List

**Symptoms**:
- Created post successfully (201)
- But `GET /lfg/posts/{community_id}` returns empty

**Diagnosis**:
```bash
# 1. Check post was actually created
curl -s "http://localhost:8096/api/v1/lfg/posts/community-uuid" \
  -H "Authorization: Bearer $TOKEN" | jq '.data.posts | length'

# 2. Check database directly
docker-compose exec infra-postgres psql -U postgres -d waddlebot -c "
  SELECT id, community_id, status, created_at FROM lfg_posts LIMIT 5;
"

# 3. Check filters being applied
curl -s "http://localhost:8096/api/v1/lfg/posts/community-uuid?status=open" \
  -H "Authorization: Bearer $TOKEN" | jq '.data'
```

**Solutions**:
1. **Check post status**:
   - Default is 'open' — if querying `?status=filled`, open posts won't appear
   - Use `?status=all` to see all posts

2. **Verify community_id**:
   - Must exactly match post's community_id
   - Check for UUID format issues

3. **Check expiry**:
   - Posts expire after LFG_DEFAULT_EXPIRY_MINUTES (default 120 min)
   - Expired posts won't appear unless `?status=expired`

4. **Flush cache**:
   ```bash
   # If Redis is used
   redis-cli FLUSHDB
   ```

---

### Issue 6: Join Post Returns "Already Joined"

**Error**:
```json
{
  "status": "error",
  "error": "ALREADY_JOINED",
  "message": "User already joined this post"
}
```

**Solutions**:
1. **User already in this post**:
   - Check if user_id already exists in lfg_joins for this post
   - User must leave before rejoining

2. **Different user?**:
   - Verify correct user_id is being sent
   - Check token belongs to correct user

3. **Database corruption**:
   ```bash
   # Check join records
   docker-compose exec infra-postgres psql -U postgres -d waddlebot -c "
     SELECT post_id, user_id, joined_at FROM lfg_joins
     WHERE post_id = 'post-uuid';
   "

   # Remove stale join if needed (admin only)
   DELETE FROM lfg_joins WHERE post_id='...' AND user_id='...';
   ```

---

### Issue 7: Post Marked as "Filled" Incorrectly

**Symptoms**:
- Only 2/4 players joined but post is marked "filled"
- Or exactly 4/4 but showing as "open"

**Diagnosis**:
```bash
# Check post details
curl -s "http://localhost:8096/api/v1/lfg/posts/community-uuid" \
  -H "Authorization: Bearer $TOKEN" | jq '.data.posts[] | select(.id=="post-uuid")'

# Check join count in database
docker-compose exec infra-postgres psql -U postgres -d waddlebot -c "
  SELECT COUNT(*) FROM lfg_joins WHERE post_id='post-uuid';
"

# Compare with player_count_needed
docker-compose exec infra-postgres psql -U postgres -d waddlebot -c "
  SELECT player_count_needed, status FROM lfg_posts WHERE id='post-uuid';
"
```

**Solutions**:
1. **Race condition during join**:
   - May occur under high concurrency
   - Try leaving and rejoining (should correct status)

2. **Manual status fix** (admin only):
   ```bash
   docker-compose exec infra-postgres psql -U postgres -d waddlebot -c "
     UPDATE lfg_posts
     SET status = CASE
       WHEN (SELECT COUNT(*) FROM lfg_joins WHERE post_id='post-uuid') >= player_count_needed
       THEN 'filled'
       ELSE 'open'
     END
     WHERE id='post-uuid';
   "
   ```

3. **Clear cache**:
   ```bash
   redis-cli DEL "lfg:post:post-uuid"
   ```

---

### Issue 8: Cron Expiry Job Not Running

**Symptoms**:
- Old posts (> 2 hours) still show as "open"
- No log messages about expiry

**Diagnosis**:
```bash
# Check when expire endpoint was last called
docker-compose logs interactive-lfg | grep "expire"

# Check if scheduler is configured
echo $LFG_DEFAULT_EXPIRY_MINUTES
```

**Solutions**:
1. **Set up external scheduler**:
   ```bash
   # Cron job (runs hourly)
   0 * * * * curl -X POST http://localhost:8096/api/v1/lfg/expire \
     -H "Content-Type: application/json" \
     -d '{"cron_token": "secret-token"}' 2>&1 | logger
   ```

2. **Kubernetes CronJob**:
   ```yaml
   apiVersion: batch/v1
   kind: CronJob
   metadata:
     name: lfg-expire
     namespace: waddlebot
   spec:
     schedule: "0 * * * *"  # Hourly
     jobTemplate:
       spec:
         template:
           spec:
             containers:
             - name: curl
               image: curlimages/curl:latest
               command:
               - /bin/sh
               - -c
               - |
                 curl -X POST http://lfg-module:8096/api/v1/lfg/expire \
                   -H "Content-Type: application/json" \
                   -d '{"cron_token":"'$CRON_TOKEN'"}'
               env:
               - name: CRON_TOKEN
                 valueFrom:
                   secretKeyRef:
                     name: lfg-secrets
                     key: CRON_TOKEN
             restartPolicy: OnFailure
   ```

3. **Manual expiry**:
   ```bash
   curl -X POST http://localhost:8096/api/v1/lfg/expire \
     -H "Content-Type: application/json" \
     -d '{"cron_token": "your-secret-token"}'
   ```

---

### Issue 9: High Memory Usage

**Symptoms**:
- Container/process using 500MB+ memory
- OOMKilled in Kubernetes

**Diagnosis**:
```bash
# Check memory usage
docker stats lfg-module

# Check for memory leaks
docker-compose exec interactive-lfg ps aux | grep python
```

**Solutions**:
1. **Disable in-memory caching**:
   - Use Redis instead: `REDIS_URL=redis://...`
   - In-memory cache grows unbounded without Redis

2. **Reduce connection pool**:
   ```bash
   DB_POOL_MAX=5  # Was 20
   ```

3. **Lower worker count**:
   ```bash
   WORKER_COUNT=2  # Was 4
   ```

4. **Increase container memory limit**:
   ```yaml
   resources:
     limits:
       memory: 512Mi  # Was 256Mi
   ```

5. **Use profiler to find leaks**:
   ```bash
   # Python memory profiler
   pip install memory-profiler
   python -m memory_profiler app.py
   ```

---

### Issue 10: Slow API Responses

**Symptoms**:
- List endpoints taking 5+ seconds
- Create/join endpoints slow under load

**Diagnosis**:
```bash
# Measure response time
time curl -s "http://localhost:8096/api/v1/lfg/posts/community-uuid" \
  -H "Authorization: Bearer $TOKEN" > /dev/null

# Check database query time
docker-compose exec infra-postgres psql -U postgres -d waddlebot -c "
  EXPLAIN ANALYZE
  SELECT * FROM lfg_posts WHERE community_id='...' AND status='open'
  ORDER BY created_at DESC LIMIT 50;
"

# Check slow query log
docker-compose exec infra-postgres psql -U postgres -d waddlebot -c "
  SELECT * FROM pg_stat_statements
  ORDER BY mean_time DESC LIMIT 10;
"
```

**Solutions**:
1. **Add missing indexes**:
   ```bash
   docker-compose exec infra-postgres psql -U postgres -d waddlebot -c "
     CREATE INDEX IF NOT EXISTS idx_community_status
     ON lfg_posts(community_id, status);
   "
   ```

2. **Enable Redis caching**:
   ```bash
   REDIS_URL=redis://localhost:6379/0
   # Restart module
   ```

3. **Reduce result limit**:
   - Default limit: 50
   - Max limit: 200
   - Use pagination

4. **Increase worker count**:
   ```bash
   WORKER_COUNT=8  # Was 4
   ```

5. **Check database performance**:
   - CPU usage high? Scale up PostgreSQL
   - Disk I/O high? Check connection pool size
   - Memory high? Check index effectiveness

---

### Issue 11: Race Condition - Users Rejoining Filled Groups

**Symptoms**:
- User leaves → post status should revert to 'open'
- But another user can't join
- Or post stays 'filled' with empty slots

**Root Cause**:
- Concurrent reads of join count can miss updates
- Status not atomically updated with join

**Mitigation**:
```python
# In service layer, wrap in transaction
with db.transaction():
    # Delete join
    db.delete(join_record)

    # Recount
    current_count = db.query(LfgJoin).filter_by(post_id=post_id).count()

    # Update status atomically
    if current_count < post.player_count_needed:
        db.update(LfgPost, status='open', id=post_id)
```

---

### Issue 12: Redis Connection Issues

**Error**:
```
ERROR: Failed to connect to Redis at redis://localhost:6379/0
```

**Diagnosis**:
```bash
# Check if Redis is running
docker ps | grep redis

# Test Redis connection
redis-cli ping
```

**Solutions**:
1. **Start Redis**:
   ```bash
   docker-compose up -d redis
   ```

2. **Verify connection string**:
   ```bash
   echo $REDIS_URL
   # Should be: redis://[:password]@[host]:[port]/[db]
   ```

3. **Test connection**:
   ```bash
   redis-cli -u $REDIS_URL ping
   ```

4. **Make Redis optional**:
   - Unset REDIS_URL to fall back to in-memory cache
   - Performance will be worse but service will work

---

## Performance Tuning Checklist

- [ ] Indexes created on community_id, status, expires_at
- [ ] Redis configured and healthy
- [ ] Connection pool sized appropriately (min 5, max 20+)
- [ ] Worker count matches CPU cores (or 2x)
- [ ] Rate limiting enabled for production
- [ ] Log level set to INFO (not DEBUG)
- [ ] Cron expiry job running hourly
- [ ] Metrics endpoint enabled for monitoring
- [ ] Health checks passing consistently

## Support & Escalation

**Level 1**: Check logs, restart service
```bash
docker-compose restart interactive-lfg
```

**Level 2**: Check database and Redis
```bash
docker-compose logs infra-postgres redis
```

**Level 3**: Clear state and reinitialize
```bash
docker-compose down -v
docker-compose up -d
```

**Level 4**: Contact Waddlebot support with logs
- Full `docker-compose logs` output
- Environment variables (redact secrets)
- Error messages and timestamps
