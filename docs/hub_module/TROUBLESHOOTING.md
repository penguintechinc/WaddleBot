# Hub Module Troubleshooting Guide

## Overview

This guide helps diagnose and resolve common issues with the Waddles Hub Module.

**Version:** 1.0.1

---

## Table of Contents

- [Quick Diagnostics](#quick-diagnostics)
- [Login & Authentication Issues](#login--authentication-issues)
- [Database Connection Issues](#database-connection-issues)
- [API Errors](#api-errors)
- [WebSocket Issues](#websocket-issues)
- [Module Installation Issues](#module-installation-issues)
- [Performance Issues](#performance-issues)
- [OAuth Integration Issues](#oauth-integration-issues)
- [Frontend Issues](#frontend-issues)
- [Docker Deployment Issues](#docker-deployment-issues)
- [Security Issues](#security-issues)
- [Common Error Codes](#common-error-codes)

---

## Quick Diagnostics

### Health Check

**Step 1: Check service health**

```bash
curl http://localhost:8060/health | jq
```

**Expected response:**
```json
{
  "module": "hub_module",
  "version": "1.0.0",
  "status": "healthy",
  "timestamp": "2024-03-15T10:00:00Z",
  "database": "connected"
}
```

**If unhealthy:**
- Check database connection
- Check service logs
- Verify environment variables

---

### View Logs

```bash
# Docker logs
docker logs hub-module

# File logs (if configured)
tail -f /var/log/waddlebotlog/hub-*.log

# System logs
journalctl -u hub-module -f
```

---

### Check Metrics

```bash
curl http://localhost:8060/metrics | jq
```

Look for:
- Database pool health
- Memory usage
- Uptime

---

## Login & Authentication Issues

### Issue: "Invalid email or password"

**Symptoms:**
- Login fails with valid credentials
- Error message: "Invalid email or password"

**Causes:**
1. Wrong credentials
2. User doesn't exist
3. Password hash mismatch
4. Database connection issue

**Solutions:**

**1. Verify user exists:**
```sql
SELECT id, email, username, is_active
FROM hub_users
WHERE email = 'admin@localhost';
```

**2. Reset admin password:**
```sql
-- Generate new bcrypt hash (use Node.js bcrypt)
-- node -e "console.log(require('bcrypt').hashSync('newpassword', 12))"

UPDATE hub_users
SET password_hash = '$2b$12$NEW_HASH_HERE'
WHERE email = 'admin@localhost';
```

**3. Check if account is active:**
```sql
UPDATE hub_users
SET is_active = true
WHERE email = 'admin@localhost';
```

**4. Verify email is verified (if required):**
```sql
UPDATE hub_users
SET email_verified = true
WHERE email = 'admin@localhost';
```

---

### Issue: "Authentication token required"

**Symptoms:**
- API returns 401 Unauthorized
- Error: "Authentication token required"

**Causes:**
1. No JWT token in request
2. Token expired
3. Token invalid

**Solutions:**

**1. Check token in request:**
```bash
# Verify Authorization header is set
curl http://localhost:8060/api/v1/auth/me \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -v
```

**2. Login to get new token:**
```bash
TOKEN=$(curl -s -X POST http://localhost:8060/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@localhost","password":"admin123"}' \
  | jq -r '.token')

echo $TOKEN
```

**3. Check JWT_SECRET is configured:**
```bash
echo $JWT_SECRET

# If empty or using default:
# Set in .env file
JWT_SECRET=your-strong-secret-64-characters-minimum
```

---

### Issue: JWT token expired

**Symptoms:**
- Token works initially, then stops after 1 hour
- 401 Unauthorized after some time

**Solution:**

**Use refresh token:**
```bash
curl -X POST http://localhost:8060/api/v1/auth/refresh \
  -H "Cookie: refreshToken=YOUR_REFRESH_TOKEN" | jq
```

**Or re-login:**
```bash
curl -X POST http://localhost:8060/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@localhost","password":"admin123"}' | jq
```

---

### Issue: CSRF token mismatch

**Symptoms:**
- POST/PUT/DELETE requests fail with 403 Forbidden
- Error: "CSRF token mismatch"

**Solution:**

**Frontend (automatic):**
The CSRF token is automatically handled by cookies. Ensure:
- `credentials: 'include'` in Axios config
- Cookies are enabled

**Testing with curl:**
```bash
# 1. Get CSRF token (set in cookie)
CSRF_TOKEN=$(curl -s -c cookies.txt http://localhost:8060/health \
  | grep -o 'csrfToken=[^;]*' | cut -d= -f2)

# 2. Use token in request
curl -X POST http://localhost:8060/api/v1/auth/login \
  -b cookies.txt \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@localhost","password":"admin123"}'
```

---

## Database Connection Issues

### Issue: "Client has encountered a connection error"

**Symptoms:**
- API returns 500 Internal Server Error
- Logs show: "Client has encountered a connection error"

**Causes:**
1. PostgreSQL not running
2. Wrong connection string
3. Database doesn't exist
4. Connection pool exhausted

**Solutions:**

**1. Check PostgreSQL is running:**
```bash
# Check status
sudo systemctl status postgresql

# Start if stopped
sudo systemctl start postgresql
```

**2. Verify connection string:**
```bash
echo $DATABASE_URL
# Should be: postgresql://user:password@host:port/database

# Test connection
psql $DATABASE_URL -c "SELECT 1"
```

**3. Create database if missing:**
```bash
createdb waddlebot

# Or via SQL
psql -U postgres -c "CREATE DATABASE waddlebot;"
```

**4. Check connection pool:**
```bash
curl http://localhost:8060/metrics | jq '.database.pool'

# If all connections used:
# Increase DATABASE_POOL_SIZE in .env
DATABASE_POOL_SIZE=20
```

**5. Check firewall:**
```bash
# PostgreSQL default port
sudo ufw allow 5432/tcp

# Or check iptables
sudo iptables -L -n | grep 5432
```

---

### Issue: "Database connection timeout"

**Symptoms:**
- Slow queries
- Timeouts on database operations
- Error: "Connection timeout"

**Solutions:**

**1. Check database performance:**
```sql
-- Check active queries
SELECT pid, now() - pg_stat_activity.query_start AS duration, query
FROM pg_stat_activity
WHERE state = 'active'
ORDER BY duration DESC;

-- Kill long-running queries
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE pid <> pg_backend_pid()
  AND state = 'active'
  AND now() - pg_stat_activity.query_start > interval '5 minutes';
```

**2. Add indexes:**
```sql
-- Check missing indexes
SELECT schemaname, tablename, attname
FROM pg_stats
WHERE schemaname = 'public'
  AND n_distinct > 100;

-- Add indexes for common queries
CREATE INDEX idx_community_members_user ON community_members(user_id);
CREATE INDEX idx_hub_chat_messages_community ON hub_chat_messages(community_id, created_at DESC);
```

**3. Optimize connection pool:**
```env
# .env
DATABASE_POOL_SIZE=10
DATABASE_CONNECTION_TIMEOUT=5000
DATABASE_IDLE_TIMEOUT=30000
```

---

## API Errors

### Issue: Rate limit exceeded (429)

**Symptoms:**
- API returns 429 Too Many Requests
- Error: "Too many requests"

**Causes:**
- Exceeded 100 requests per minute limit
- Automated script hitting API

**Solutions:**

**1. Check rate limit settings:**
```env
# .env
RATE_LIMIT_WINDOW_MS=60000
RATE_LIMIT_MAX_REQUESTS=100
```

**2. Increase limits (production):**
```env
RATE_LIMIT_WINDOW_MS=60000
RATE_LIMIT_MAX_REQUESTS=500
```

**3. Implement backoff in client:**
```javascript
async function apiCallWithRetry(url, options, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      const response = await fetch(url, options);
      if (response.status === 429) {
        const retryAfter = response.headers.get('Retry-After') || 60;
        await new Promise(resolve => setTimeout(resolve, retryAfter * 1000));
        continue;
      }
      return response;
    } catch (error) {
      if (i === maxRetries - 1) throw error;
    }
  }
}
```

---

### Issue: CORS errors

**Symptoms:**
- Browser console: "CORS policy: No 'Access-Control-Allow-Origin' header"
- API calls fail from frontend

**Causes:**
- Frontend URL not in CORS_ORIGIN
- Missing credentials: 'include'

**Solutions:**

**1. Add frontend URL to CORS:**
```env
# .env
CORS_ORIGIN=http://localhost:5173,http://localhost:3000,https://hub.example.com
```

**2. Restart backend:**
```bash
npm run dev
```

**3. Check Axios config:**
```javascript
// frontend/src/services/api.js
import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '',
  withCredentials: true, // Important for CORS with cookies
});
```

---

### Issue: 404 Not Found on API route

**Symptoms:**
- API endpoint returns 404
- Route exists in code

**Causes:**
1. Typo in URL
2. Route not registered
3. Middleware blocking route

**Solutions:**

**1. Check route registration:**
```javascript
// backend/src/routes/index.js
import adminRoutes from './admin.js';

router.use('/admin', adminRoutes); // Must be registered
```

**2. Verify route path:**
```bash
# Check if route exists
curl http://localhost:8060/api/v1/admin/1/settings -v

# Expected: 401 (auth required) or 200 (if authenticated)
# Not: 404
```

**3. Check middleware:**
```javascript
// Ensure middleware doesn't consume request
router.use(requireAuth); // ✓ Good - calls next()
router.get('/settings', handler); // ✓ Route registered after middleware
```

---

## WebSocket Issues

### Issue: WebSocket connection fails

**Symptoms:**
- Chat doesn't work
- Real-time updates missing
- Console error: "WebSocket connection failed"

**Causes:**
1. Backend WebSocket server not running
2. Firewall blocking WebSocket
3. Invalid JWT token
4. CORS issues

**Solutions:**

**1. Check WebSocket server:**
```bash
# Check logs for "WebSocket server initialized"
docker logs hub-module | grep WebSocket

# Should see:
# WebSocket server initialized
```

**2. Test WebSocket connection:**
```javascript
// browser console
const io = require('socket.io-client');
const socket = io('http://localhost:8060', {
  auth: { token: 'YOUR_JWT_TOKEN' }
});

socket.on('connect', () => console.log('✓ Connected'));
socket.on('connect_error', (err) => console.error('✗ Error:', err));
```

**3. Check firewall:**
```bash
# Allow WebSocket port
sudo ufw allow 8060/tcp

# Or check if blocked
sudo ufw status | grep 8060
```

**4. Verify token is valid:**
```bash
# Get fresh token
curl -X POST http://localhost:8060/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@localhost","password":"admin123"}' | jq -r '.token'
```

---

### Issue: WebSocket disconnects frequently

**Symptoms:**
- Chat connection drops
- Reconnects often
- Console: "WebSocket disconnected"

**Causes:**
1. Network instability
2. Timeout settings too aggressive
3. Load balancer issues (production)

**Solutions:**

**1. Increase timeout settings:**
```javascript
// backend/src/websocket/index.js
const io = new Server(httpServer, {
  pingTimeout: 60000,     // Increase from 5000
  pingInterval: 25000,    // Increase from 10000
});
```

**2. Configure client reconnection:**
```javascript
// frontend
const socket = io('http://localhost:8060', {
  auth: { token: localStorage.getItem('token') },
  reconnection: true,
  reconnectionAttempts: 5,
  reconnectionDelay: 1000,
  reconnectionDelayMax: 5000,
});
```

**3. Use sticky sessions (production):**
```nginx
# nginx.conf
upstream hub_backend {
  ip_hash; # Sticky sessions
  server hub1:8060;
  server hub2:8060;
}
```

---

## Module Installation Issues

### Issue: Module installation fails

**Symptoms:**
- "Install Module" button doesn't work
- Error: "Failed to install module"

**Causes:**
1. Module not published
2. Database error
3. Missing permissions

**Solutions:**

**1. Check module is published:**
```sql
SELECT id, name, is_published
FROM hub_modules
WHERE name = 'loyalty';

-- If not published (SuperAdmin only):
UPDATE hub_modules
SET is_published = true
WHERE name = 'loyalty';
```

**2. Check for duplicate installation:**
```sql
SELECT *
FROM hub_module_installations
WHERE community_id = 1 AND module_id = 1;

-- If exists, delete and retry:
DELETE FROM hub_module_installations
WHERE community_id = 1 AND module_id = 1;
```

**3. Verify user is admin:**
```sql
SELECT role
FROM community_members
WHERE community_id = 1 AND user_id = 1;

-- Should be 'admin'
-- If not:
UPDATE community_members
SET role = 'admin'
WHERE community_id = 1 AND user_id = 1;
```

---

### Issue: Module config not saving

**Symptoms:**
- Config changes don't persist
- Returns to default after refresh

**Causes:**
1. Invalid JSON in config
2. Schema validation failure
3. Database write error

**Solutions:**

**1. Validate JSON:**
```bash
# Test JSON validity
echo '{"enabled": true, "setting": "value"}' | jq

# Should output formatted JSON
# If error, fix JSON syntax
```

**2. Check config schema:**
```sql
SELECT config_schema
FROM hub_modules
WHERE id = 1;

-- Ensure your config matches schema
```

**3. Check database logs:**
```bash
# Enable query logging
DATABASE_LOG=true npm run dev

# Check for UPDATE errors
```

---

## Performance Issues

### Issue: Slow page loads

**Symptoms:**
- Pages take >3 seconds to load
- High CPU usage
- Database queries slow

**Causes:**
1. Missing database indexes
2. N+1 query problem
3. Large dataset loading
4. Slow API calls

**Solutions:**

**1. Add database indexes:**
```sql
-- Check slow queries
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Add indexes
CREATE INDEX idx_communities_name ON communities(name);
CREATE INDEX idx_community_members_lookup ON community_members(community_id, user_id);
```

**2. Optimize queries (avoid N+1):**
```javascript
// Bad: N+1 query
for (const member of members) {
  member.user = await query('SELECT * FROM hub_users WHERE id = $1', [member.user_id]);
}

// Good: Single query with JOIN
const members = await query(`
  SELECT cm.*, u.username, u.avatar_url
  FROM community_members cm
  LEFT JOIN hub_users u ON cm.user_id = u.id
  WHERE cm.community_id = $1
`, [communityId]);
```

**3. Implement pagination:**
```javascript
// Always paginate large lists
router.get('/members', async (req, res) => {
  const page = parseInt(req.query.page) || 1;
  const limit = parseInt(req.query.limit) || 50;
  const offset = (page - 1) * limit;

  const members = await query(
    'SELECT * FROM community_members WHERE community_id = $1 LIMIT $2 OFFSET $3',
    [communityId, limit, offset]
  );

  res.json({ data: members, page, limit });
});
```

**4. Enable caching:**
```javascript
// Cache community data
const cache = new Map();

async function getCommunity(id) {
  if (cache.has(id)) {
    return cache.get(id);
  }

  const community = await query('SELECT * FROM communities WHERE id = $1', [id]);
  cache.set(id, community);
  setTimeout(() => cache.delete(id), 60000); // 1 min TTL

  return community;
}
```

---

### Issue: High memory usage

**Symptoms:**
- Memory usage >1GB
- Out of memory errors
- Slow performance

**Causes:**
1. Memory leaks
2. Large datasets in memory
3. WebSocket connections not cleaned up

**Solutions:**

**1. Check memory usage:**
```bash
curl http://localhost:8060/metrics | jq '.memory'

# Shows:
# - rss (resident set size)
# - heapTotal
# - heapUsed
```

**2. Reduce connection pool:**
```env
DATABASE_POOL_SIZE=5  # Reduce if high memory
```

**3. Clean up WebSocket connections:**
```javascript
// Ensure disconnect handler is called
socket.on('disconnect', () => {
  // Clean up resources
  socket.rooms.clear();
  socket.removeAllListeners();
});
```

**4. Use streams for large data:**
```javascript
// Bad: Load all data into memory
const messages = await query('SELECT * FROM hub_chat_messages');

// Good: Stream data
const stream = client.query('SELECT * FROM hub_chat_messages');
stream.on('data', (row) => {
  res.write(JSON.stringify(row) + '\n');
});
stream.on('end', () => res.end());
```

---

## OAuth Integration Issues

### Issue: OAuth login fails

**Symptoms:**
- "OAuth provider not configured" error
- Redirect fails
- No token returned

**Causes:**
1. OAuth credentials not set (SuperAdmin)
2. Redirect URI mismatch
3. Platform API down

**Solutions:**

**1. Configure OAuth (SuperAdmin):**
```bash
# Login as SuperAdmin
# Go to /superadmin/platform-config
# Select platform (Discord, Twitch, etc.)
# Enter Client ID and Client Secret
# Save and enable
```

**2. Verify redirect URI:**
```bash
# Redirect URI must match exactly:
http://localhost:8060/api/v1/auth/oauth/discord/callback

# Or for production:
https://hub.example.com/api/v1/auth/oauth/discord/callback

# Check in Discord Developer Portal:
# https://discord.com/developers/applications
# OAuth2 → Redirects → Add redirect URI
```

**3. Test OAuth flow:**
```bash
# 1. Get OAuth URL
curl http://localhost:8060/api/v1/auth/oauth/discord | jq '.url'

# 2. Open URL in browser
# 3. Authorize
# 4. Should redirect back with code
# 5. Backend exchanges code for token
```

**4. Check platform status:**
- Discord: https://discordstatus.com
- Twitch: https://status.twitch.tv
- YouTube: https://www.google.com/appsstatus

---

### Issue: OAuth account linking fails

**Symptoms:**
- "Failed to link account" error
- Account already linked to another user

**Causes:**
1. Platform account already linked
2. User not authenticated
3. Database constraint violation

**Solutions:**

**1. Check if account is linked:**
```sql
SELECT hub_user_id, platform, platform_user_id
FROM hub_user_identities
WHERE platform = 'discord' AND platform_user_id = '123456789';

-- If linked to different user:
-- User must unlink from other account first
```

**2. Unlink account:**
```sql
DELETE FROM hub_user_identities
WHERE platform = 'discord' AND platform_user_id = '123456789';
```

**3. Verify user is authenticated:**
```bash
# Ensure valid JWT token
curl http://localhost:8060/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN" | jq
```

---

## Frontend Issues

### Issue: White screen / blank page

**Symptoms:**
- Page shows blank screen
- No errors in console
- React app not loading

**Causes:**
1. Build error
2. JavaScript error
3. API unreachable
4. CORS issue

**Solutions:**

**1. Check browser console:**
```
F12 → Console tab
Look for errors (red messages)
```

**2. Rebuild frontend:**
```bash
cd frontend
rm -rf node_modules dist
npm install
npm run build
```

**3. Check API is running:**
```bash
curl http://localhost:8060/health
```

**4. Check Vite dev server:**
```bash
cd frontend
npm run dev

# Should start on http://localhost:3000
```

---

### Issue: "Failed to fetch" errors

**Symptoms:**
- API calls fail
- Console: "Failed to fetch"
- Network errors

**Causes:**
1. Backend not running
2. Wrong API URL
3. CORS issue
4. Network connectivity

**Solutions:**

**1. Verify backend is running:**
```bash
curl http://localhost:8060/health
```

**2. Check API URL in frontend:**
```javascript
// frontend/src/services/api.js
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '',
  // Empty string = same origin
  // Or set: baseURL: 'http://localhost:8060'
});
```

**3. Check CORS:**
```env
# backend/.env
CORS_ORIGIN=http://localhost:3000,http://localhost:5173
```

---

## Docker Deployment Issues

### Issue: Container won't start

**Symptoms:**
- Docker container exits immediately
- `docker ps` shows no hub container
- Exit code 1

**Causes:**
1. Environment variables missing
2. Database unreachable
3. Build error

**Solutions:**

**1. Check container logs:**
```bash
docker logs hub-module
```

**2. Verify environment variables:**
```bash
docker exec hub-module env | grep DATABASE_URL
docker exec hub-module env | grep JWT_SECRET
```

**3. Check database connection:**
```bash
# Test from container
docker exec hub-module pg_isready -h postgres -p 5432
```

**4. Rebuild container:**
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

---

### Issue: "EADDRINUSE: address already in use"

**Symptoms:**
- Container fails to start
- Error: "address already in use :::8060"

**Cause:**
Another process is using port 8060

**Solutions:**

**1. Find process using port:**
```bash
lsof -i :8060
# Or
netstat -tulpn | grep 8060
```

**2. Kill process:**
```bash
kill -9 <PID>
```

**3. Use different port:**
```yaml
# docker-compose.yml
services:
  hub:
    ports:
      - "8061:8060"  # External:Internal
```

---

## Security Issues

### Issue: "JWT_SECRET must be set"

**Symptoms:**
- Server won't start in production
- Error: "FATAL: JWT_SECRET must be set to a strong secret in production"

**Cause:**
Using default/weak JWT_SECRET in production

**Solution:**

**Generate strong secret:**
```bash
# Generate 64-character random string
openssl rand -hex 32

# Set in .env
JWT_SECRET=your_64_character_random_string_here
```

---

### Issue: XSS vulnerability detected

**Symptoms:**
- Security scan reports XSS
- User input not sanitized

**Solution:**

XSS sanitization is automatic via middleware. Verify:

```javascript
// backend/src/index.js
app.use(sanitizeBody); // ✓ Should be enabled

// Manual sanitization if needed:
import xss from 'xss';
const cleanInput = xss(userInput);
```

---

## Common Error Codes

### HTTP Status Codes

| Code | Meaning | Common Cause |
|------|---------|--------------|
| 400 | Bad Request | Invalid request body/params |
| 401 | Unauthorized | Missing/invalid JWT token |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Invalid endpoint or resource |
| 409 | Conflict | Resource already exists (duplicate) |
| 422 | Unprocessable Entity | Validation failed |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server-side error (check logs) |
| 503 | Service Unavailable | Database/service down |

---

### Application Error Codes

| Code | Description | Solution |
|------|-------------|----------|
| `VALIDATION_ERROR` | Input validation failed | Check request body |
| `UNAUTHORIZED` | Authentication required | Login and get token |
| `FORBIDDEN` | Permission denied | Check user role |
| `NOT_FOUND` | Resource not found | Verify resource ID |
| `CONFLICT` | Resource already exists | Use different name/ID |
| `RATE_LIMITED` | Too many requests | Wait and retry |
| `INTERNAL_ERROR` | Server error | Check logs, contact admin |

---

## Getting Help

### Before Contacting Support

1. **Check logs:**
   ```bash
   docker logs hub-module --tail 100
   ```

2. **Check health:**
   ```bash
   curl http://localhost:8060/health | jq
   ```

3. **Check metrics:**
   ```bash
   curl http://localhost:8060/metrics | jq
   ```

4. **Try test scripts:**
   ```bash
   ./test-api.sh
   ./test-webui.sh
   ```

5. **Search documentation:**
   - API.md
   - CONFIGURATION.md
   - ARCHITECTURE.md

---

### Provide These Details

When reporting an issue:

1. **Version:** 1.0.1
2. **Environment:** Development/Production
3. **Error message:** Full error text
4. **Logs:** Last 50 lines
5. **Steps to reproduce:** What you did
6. **Expected behavior:** What should happen
7. **Actual behavior:** What actually happened

---

### Support Channels

- **Documentation:** `/docs/hub_module/`
- **GitHub Issues:** https://github.com/yourusername/Waddles/issues
- **Community Discord:** https://discord.gg/waddlebot
- **Email:** support@waddlebot.io

---

## Preventive Maintenance

### Regular Checks

**Weekly:**
- [ ] Check disk space
- [ ] Review error logs
- [ ] Monitor database size
- [ ] Check backup integrity

**Monthly:**
- [ ] Update dependencies (security patches)
- [ ] Review database indexes
- [ ] Analyze slow queries
- [ ] Test disaster recovery

**Quarterly:**
- [ ] Security audit
- [ ] Performance review
- [ ] Capacity planning
- [ ] Documentation updates

---

### Monitoring Setup

**Recommended tools:**
- **Uptime:** UptimeRobot, Pingdom
- **Logs:** ELK Stack, Grafana Loki
- **Metrics:** Prometheus + Grafana
- **Errors:** Sentry, Rollbar
- **Database:** pgAdmin, DataDog

---

### Backup Strategy

**Database backups:**
```bash
# Daily backup
pg_dump $DATABASE_URL > backup-$(date +%Y%m%d).sql

# Automated backup (cron)
0 2 * * * pg_dump $DATABASE_URL | gzip > /backups/hub-$(date +\%Y\%m\%d).sql.gz

# Restore from backup
psql $DATABASE_URL < backup-20240315.sql
```

---

## Conclusion

Most issues can be resolved by:
1. Checking logs
2. Verifying configuration
3. Testing with provided scripts
4. Consulting documentation

For persistent issues, contact support with detailed information.
