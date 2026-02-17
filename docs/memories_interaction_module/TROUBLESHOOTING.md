# Memories Interaction Module - Troubleshooting

## Common Issues and Solutions

### 1. Module Fails to Start

#### Error: "Failed to connect to database"

**Symptoms**:
```
ConnectionError: could not translate host name "postgres" to address
ERROR: Failed to initialize database connection
```

**Causes**:
- PostgreSQL server not running
- DATABASE_URL is incorrect
- Network connectivity issue

**Solutions**:

1. Verify PostgreSQL is running:
```bash
# Docker
docker ps | grep postgres

# Local
pg_isready -h localhost -p 5432
```

2. Test database connection:
```bash
psql postgresql://user:pass@localhost:5432/waddlebot
```

3. Check DATABASE_URL environment variable:
```bash
echo $DATABASE_URL
# Should output: postgresql://user:pass@host:5432/dbname
```

4. Fix DATABASE_URL if needed:
```bash
# Docker Compose - use service name
DATABASE_URL=postgresql://waddlebot:password@postgres:5432/waddlebot

# Local - use localhost
DATABASE_URL=postgresql://waddlebot:password@localhost:5432/waddlebot
```

#### Error: "Port 8031 already in use"

**Symptoms**:
```
OSError: [Errno 48] Address already in use
```

**Solutions**:

1. Find process using port:
```bash
netstat -tulpn | grep 8031
lsof -i :8031
```

2. Kill process:
```bash
kill -9 <PID>
```

3. Or use different port:
```bash
export MODULE_PORT=8032
```

#### Error: "Module tables not found"

**Symptoms**:
```
ProgrammingError: relation "memories_quotes" does not exist
```

**Solutions**:

1. Verify schema exists in database:
```bash
psql -d waddlebot -c "\dt memories*"
```

2. Run migrations if needed:
```bash
# Using migration tool
psql -d waddlebot < migrations/create_memories_schema.sql
```

3. Check if database is correct:
```bash
# List all tables
psql -d waddlebot -c "\dt"
```

---

### 2. API Request Failures

#### Error: "400 Validation Error"

**Symptoms**:
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Validation failed for QuoteCreateRequest"
  }
}
```

**Common causes and fixes**:

| Field | Issue | Fix |
|-------|-------|-----|
| community_id | Not an integer or ≤0 | Use positive integer |
| quote_text | Empty, too long (>5000), or whitespace | Provide 1-5000 character text |
| created_by_username | Empty or whitespace | Provide valid username |
| url (bookmark) | Invalid URL format | Use valid URL starting with http:// or https:// |
| remind_in | Invalid format | Use "5m", "2h", "1d", "3w" or ISO timestamp |
| vote_type | Not "up" or "down" | Use exact values: "up" or "down" |

**Debug validation errors**:

```bash
# Check request JSON syntax
curl -X POST http://localhost:8031/api/v1/memories/quotes \
  -H "Content-Type: application/json" \
  -d '{"invalid json"}'  # Missing closing brace

# Verbose response
curl -v -X POST http://localhost:8031/api/v1/memories/quotes \
  -H "Content-Type: application/json" \
  -d '{...}' | jq .
```

#### Error: "404 Not Found"

**Symptoms**:
```json
{
  "success": false,
  "error": {
    "code": "NOT_FOUND",
    "message": "Quote not found"
  }
}
```

**Causes**:
- Resource ID doesn't exist
- Wrong community_id
- Resource was deleted

**Solutions**:

1. Verify resource exists:
```bash
# Search for quotes in community
curl http://localhost:8031/api/v1/memories/quotes/1

# Get stats
curl http://localhost:8031/api/v1/memories/quotes/1/stats
```

2. Check community_id is correct:
```bash
# List communities if available
curl http://localhost:8000/api/v1/communities
```

#### Error: "403 Forbidden"

**Symptoms**:
```json
{
  "success": false,
  "error": {
    "code": "FORBIDDEN",
    "message": "Unauthorized or not found"
  }
}
```

**Causes**:
- User trying to delete someone else's content
- User_id in request doesn't match creator

**Solutions**:

1. Verify you're the creator:
```bash
# Get quote details
curl http://localhost:8031/api/v1/memories/quotes/1/5

# Check created_by_username matches your user
```

2. Use correct user_id in deletion request:
```bash
curl -X DELETE http://localhost:8031/api/v1/memories/quotes/1/5 \
  -d '{"user_id": YOUR_USER_ID}'
```

#### Error: "500 Internal Server Error"

**Symptoms**:
```json
{
  "success": false,
  "error": {
    "code": "INTERNAL_ERROR",
    "message": "Internal server error"
  }
}
```

**Debug steps**:

1. Check module logs:
```bash
docker logs memories-module
# Look for traceback and error details
```

2. Check database connectivity:
```bash
psql $DATABASE_URL -c "SELECT 1"
```

3. Check for recent code changes:
```bash
git log --oneline -10
git diff HEAD~1
```

4. Enable debug logging:
```bash
export LOG_LEVEL=DEBUG
docker restart memories-module
docker logs memories-module
```

---

### 3. Search Functionality Issues

#### Problem: Full-text search returns no results

**Symptoms**:
```bash
curl "http://localhost:8031/api/v1/memories/quotes/1?q=innovation"
# Returns empty results even though quote exists
```

**Causes**:
- search_vector not populated
- PostgreSQL full-text search not configured
- Stop words filtering out query terms

**Solutions**:

1. Verify search_vector is populated:
```bash
psql -d waddlebot -c "SELECT id, quote_text, search_vector FROM memories_quotes LIMIT 5;"
```

2. Rebuild search vectors if needed:
```bash
psql -d waddlebot -c "
  UPDATE memories_quotes SET search_vector = 
    to_tsvector('english', coalesce(quote_text, ''))
  WHERE search_vector IS NULL;
"
```

3. Test search query directly:
```bash
psql -d waddlebot -c "
  SELECT * FROM memories_quotes 
  WHERE search_vector @@ plainto_tsquery('english', 'innovation')
  LIMIT 5;
"
```

---

### 4. Reminder Issues

#### Problem: Reminders not firing at scheduled time

**Symptoms**:
- Created reminder but it wasn't sent
- No pending reminders in /reminders/pending

**Causes**:
- No reminder processor running
- Timezone mismatch (UTC vs local)
- Reminder time in past

**Solutions**:

1. Verify reminder was created:
```bash
curl http://localhost:8031/api/v1/memories/reminders/1/user/101
```

2. Check remind_at timestamp:
```bash
psql -d waddlebot -c "
  SELECT id, username, remind_at, is_sent 
  FROM memories_reminders 
  WHERE user_id = 101 
  ORDER BY remind_at DESC
  LIMIT 5;
"
```

3. Get pending reminders:
```bash
curl http://localhost:8031/api/v1/memories/reminders/pending
```

4. Check if time is in future (UTC):
```bash
psql -d waddlebot -c "SELECT NOW() AT TIME ZONE 'UTC';"
```

5. Ensure reminder processor is running:
```bash
# Check if reminder processor service is active
docker ps | grep reminder-processor
# Or manually mark reminder as sent for testing
curl -X POST http://localhost:8031/api/v1/memories/reminders/1/sent \
  -d '{"schedule_next": true}'
```

#### Problem: Recurring reminders not rescheduling

**Symptoms**:
- Marked reminder as sent but no next reminder created
- recurring_rule seems valid but not scheduling

**Causes**:
- Invalid RRULE format
- schedule_next=false in mark-sent request
- Next occurrence already in past

**Solutions**:

1. Validate RRULE format:
```bash
# Should start with FREQ=
# Example: "FREQ=DAILY;INTERVAL=1;BYDAY=MO,TU,WE,TH,FR"

# Test RRULE:
python3 << 'EOF'
from dateutil.rrule import rrulestr
from datetime import datetime

rule_str = "FREQ=DAILY;INTERVAL=1"
rule = rrulestr(rule_str, dtstart=datetime.utcnow())
next_occ = rule.after(datetime.utcnow())
print(f"Next occurrence: {next_occ}")
EOF
```

2. Check recurring reminders in database:
```bash
psql -d waddlebot -c "
  SELECT id, username, remind_at, recurring_rule 
  FROM memories_reminders 
  WHERE recurring_rule IS NOT NULL
  LIMIT 5;
"
```

3. Verify schedule_next=true:
```bash
curl -X POST http://localhost:8031/api/v1/memories/reminders/5/sent \
  -d '{"schedule_next": true}'  # Must be true
```

---

### 5. Performance Issues

#### Problem: Search queries are slow

**Symptoms**:
```bash
# Slow response on search endpoint
curl "http://localhost:8031/api/v1/memories/quotes/1?q=test"
# Takes > 1 second to respond
```

**Causes**:
- Missing indexes
- Large dataset
- Database under load

**Solutions**:

1. Check if indexes exist:
```bash
psql -d waddlebot -c "
  SELECT indexname FROM pg_indexes 
  WHERE tablename = 'memories_quotes'
  ORDER BY indexname;
"
```

2. Create missing indexes:
```bash
psql -d waddlebot -c "
  CREATE INDEX IF NOT EXISTS idx_quotes_search 
  ON memories_quotes USING GIN(search_vector);
  
  CREATE INDEX IF NOT EXISTS idx_quotes_community 
  ON memories_quotes(community_id);
"
```

3. Vacuum and analyze:
```bash
psql -d waddlebot -c "VACUUM ANALYZE memories_quotes;"
```

4. Check query plan:
```bash
psql -d waddlebot -c "
  EXPLAIN ANALYZE
  SELECT * FROM memories_quotes 
  WHERE search_vector @@ plainto_tsquery('english', 'test')
  LIMIT 50;
"
```

---

### 6. Bookmark Metadata Issues

#### Problem: Auto-fetch metadata fails

**Symptoms**:
```json
{
  "id": 1,
  "url": "https://example.com",
  "title": "https://example.com",  // Should be page title
  "description": ""  // Should have content
}
```

**Causes**:
- Website doesn't allow scraping
- Network timeout
- HTML structure not standard

**Solutions**:

1. Enable debug logging:
```bash
export LOG_LEVEL=DEBUG
```

2. Check logs for metadata fetch errors:
```bash
docker logs memories-module | grep "metadata"
```

3. Test URL manually:
```bash
curl -I https://example.com
# Check if returns 200 OK and has title/meta tags
```

4. Provide explicit metadata:
```bash
curl -X POST http://localhost:8031/api/v1/memories/bookmarks \
  -d '{
    "community_id": 1,
    "url": "https://example.com",
    "title": "Custom Title",
    "description": "Custom Description",
    "auto_fetch_metadata": false
  }'
```

---

### 7. Database Connection Pool Issues

#### Problem: "Too many connections" error

**Symptoms**:
```
ERROR: FATAL: remaining connection slots are reserved for non-replication superuser connections
```

**Causes**:
- Connection pool exhausted
- Long-running queries holding connections
- Memory leak in connection handling

**Solutions**:

1. Check active connections:
```bash
psql -d waddlebot -c "
  SELECT count(*) 
  FROM pg_stat_activity;
"
```

2. Kill idle connections:
```bash
psql -d waddlebot -c "
  SELECT pg_terminate_backend(pid) 
  FROM pg_stat_activity 
  WHERE state = 'idle'
  AND query_start < NOW() - INTERVAL '10 minutes';
"
```

3. Increase connection limit:
```bash
# In postgresql.conf
max_connections = 200

# Restart PostgreSQL
sudo systemctl restart postgresql
```

4. Increase module pool size in code if needed

---

## Getting Help

If you still have issues:

1. **Check logs**:
```bash
docker logs -f memories-module
```

2. **Check database**:
```bash
psql $DATABASE_URL -c "SELECT 1"
```

3. **Run diagnostics**:
```bash
curl http://localhost:8031/health
curl http://localhost:8031/metrics
```

4. **Review configuration**:
```bash
env | grep -E "(DATABASE|MODULE|LOG|SECRET)"
```

---

Last Updated: February 16, 2026
Module Version: 2.0.0
