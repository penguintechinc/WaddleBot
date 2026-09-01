# GCP Functions Action Module - Troubleshooting Guide

## Common Issues and Solutions

### Module Startup Issues

#### 1. Module Won't Start - GCP Credentials Error

**Error Message:**
```
ERROR Failed to load GCP credentials: Permission denied
ERROR No GCP credentials available - running in degraded mode
```

**Causes:**
- GCP_SERVICE_ACCOUNT_KEY not set
- Service account JSON invalid
- Service account key file not found

**Solutions:**

Verify credentials exist:
```bash
# Check environment variable
echo $GCP_SERVICE_ACCOUNT_KEY

# If file path, verify file exists
ls -la /path/to/service-account-key.json
```

Validate JSON format:
```bash
# If using inline JSON, validate it
echo $GCP_SERVICE_ACCOUNT_KEY | python3 -m json.tool
```

Check file permissions:
```bash
# Service account key must be readable by application
chmod 600 /path/to/service-account-key.json
```

Use correct JSON key:
```bash
# Download fresh key from GCP Console
gcloud iam service-accounts keys create gcp-key.json \
  --iam-account=waddlebot@PROJECT.iam.gserviceaccount.com

# Set as environment variable
export GCP_SERVICE_ACCOUNT_KEY="/path/to/gcp-key.json"
```

#### 2. Module Won't Start - Database Connection Error

**Error Message:**
```
ERROR Configuration errors: DATABASE_URL is required
ERROR Failed to connect to database: connection refused
```

**Solutions:**

Check PostgreSQL running:
```bash
docker-compose ps
# Should show 'postgres' as 'Up'
```

Start database if not running:
```bash
docker-compose up -d postgres
```

Verify DATABASE_URL:
```bash
# Format: postgres://user:password@host:port/database
psql $DATABASE_URL -c "SELECT 1"
```

Check port accessible:
```bash
netstat -tuln | grep 5432
```

#### 3. Module Won't Start - GCP Project Not Configured

**Error Message:**
```
ValueError: GCP_PROJECT_ID is required
```

**Solution:**

Set GCP project ID:
```bash
export GCP_PROJECT_ID="my-gcp-project"

# Or get from gcloud
export GCP_PROJECT_ID=$(gcloud config get-value project)

# Verify
echo $GCP_PROJECT_ID
```

---

### API Request Issues

#### 1. Health Check Returns Unhealthy

**Response:**
```json
{
  "status": "unhealthy",
  "error": "Failed to connect to GCP"
}
```

**Check:**
1. GCP credentials: `echo $GCP_SERVICE_ACCOUNT_KEY`
2. GCP project: `echo $GCP_PROJECT_ID`
3. Database connectivity: `psql $DATABASE_URL -c "SELECT 1"`
4. Logs: `docker-compose logs gcp_functions_action_module`

**Solutions:**

Restart with valid credentials:
```bash
export GCP_SERVICE_ACCOUNT_KEY="/path/to/key.json"
export GCP_PROJECT_ID="my-project"
docker-compose restart gcp_functions_action_module
```

#### 2. Authentication Failures

**Error Response:**
```json
{
  "error": "Missing or invalid Authorization header"
}
```

**Cause:**
- Missing Authorization header
- Invalid JWT token
- Token expired

**Solution - Get new token:**
```bash
curl -X POST http://localhost:8081/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"api_key":"test","service":"test"}' | jq -r '.token'
```

Use token in requests:
```bash
TOKEN="your_jwt_token_here"
curl http://localhost:8081/api/v1/functions/list \
  -H "Authorization: Bearer $TOKEN"
```

#### 3. Missing Authorization Header Format

**Error Response:**
```json
{
  "error": "Missing or invalid Authorization header"
}
```

**Correct Format:**
```bash
curl http://localhost:8081/api/v1/functions/invoke \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"project":"test","region":"us-central1","function_name":"fn","payload":{}}'
```

**Invalid Formats:**
```bash
# WRONG - no Bearer prefix
-H "Authorization: YOUR_TOKEN"

# WRONG - wrong header name
-H "Auth: Bearer TOKEN"

# WRONG - token without header
-d '{"token": "YOUR_TOKEN"}'
```

---

### GCP API Issues

#### 1. Function Invocation Returns 403 Unauthorized

**Error Message:**
```json
{
  "success": false,
  "error": "403 Forbidden - Permission denied"
}
```

**Causes:**
- Service account lacks Cloud Functions Invoker role
- Service account doesn't have access to function

**Solutions:**

Check service account has required roles:
```bash
# Should have roles/cloudfunctions.invoker
gcloud projects get-iam-policy MY_PROJECT_ID \
  --flatten="bindings[].members" \
  --format='table(bindings.role)' \
  --filter="bindings.members:serviceAccount:waddlebot@*"
```

Grant required role:
```bash
gcloud projects add-iam-policy-binding MY_PROJECT_ID \
  --member="serviceAccount:waddlebot@MY_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/cloudfunctions.invoker"
```

Also grant viewer role for listing:
```bash
gcloud projects add-iam-policy-binding MY_PROJECT_ID \
  --member="serviceAccount:waddlebot@MY_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/cloudfunctions.viewer"
```

#### 2. Function Invocation Returns 404 Not Found

**Error Message:**
```json
{
  "success": false,
  "error": "404 Not Found"
}
```

**Causes:**
- Function doesn't exist
- Wrong region specified
- Function name misspelled

**Solutions:**

List available functions:
```bash
curl http://localhost:8081/api/v1/functions/list \
  -H "Authorization: Bearer TOKEN" | jq '.functions'
```

Verify function exists in GCP:
```bash
gcloud functions list --region=us-central1
```

Check function name spelling:
```bash
# Function names are case-sensitive
gcloud functions describe my-function --region=us-central1
```

Use correct region:
```bash
# Default region is us-central1, can override in request
curl -X POST http://localhost:8081/api/v1/functions/invoke \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project": "my-project",
    "region": "us-west1",
    "function_name": "my-function",
    "payload": {}
  }'
```

#### 3. Function Invocation Times Out

**Error Message:**
```json
{
  "success": false,
  "error": "Function execution timeout"
}
```

**Causes:**
- Function takes longer than FUNCTION_TIMEOUT
- Network connectivity issues
- GCP overloaded

**Solutions:**

Increase function timeout:
```bash
export FUNCTION_TIMEOUT=120  # 120 seconds
docker-compose restart gcp_functions_action_module
```

Check GCP function performance:
```bash
# Monitor function execution logs
gcloud functions logs read my-function --region=us-central1 --limit=50
```

Check network connectivity to GCP:
```bash
# Test connectivity
ping -c 5 cloudfunctions.googleapis.com

# Test HTTPS
curl -I https://cloudfunctions.googleapis.com
```

#### 4. Batch Operations Fail Partially

**Response:**
```json
{
  "responses": [
    {"success": true, "status_code": 200},
    {"success": false, "error": "Function not found"},
    {"success": true, "status_code": 200}
  ],
  "total_count": 3,
  "success_count": 2,
  "failure_count": 1
}
```

**Solution:**

Check failed invocation details. Errors are typically:
- Function not found: Verify function exists
- Permission denied: Check IAM roles
- Timeout: Increase FUNCTION_TIMEOUT
- Invalid payload: Validate JSON

#### 5. Batch Size Exceeded Error

**Error Response:**
```json
{
  "error": "Batch size exceeds maximum of 100"
}
```

**Solution:**

Reduce invocations to <= 100:
```bash
# Instead of 150 functions, split into 2 batch requests
# Batch 1: 100 functions
# Batch 2: 50 functions

# Or increase limit
export MAX_BATCH_SIZE=200
docker-compose restart gcp_functions_action_module
```

#### 6. GCP Cloud Functions API Not Enabled

**Error Message:**
```
403 Forbidden: Cloud Functions API is not enabled
```

**Solution:**

Enable API:
```bash
gcloud services enable cloudfunctions.googleapis.com

# Verify
gcloud services list --enabled | grep functions
```

---

### Performance Issues

#### 1. Function Invocations Are Very Slow

**Symptom:**
- Function invocation takes >10 seconds
- Batch operations timeout

**Causes:**
- GCP Functions themselves slow
- Network latency
- High concurrency with low quota

**Solutions:**

Check GCP function performance:
```bash
gcloud functions logs read my-function --region=us-central1

# Look for execution times in logs
```

Check GCP status:
```bash
# https://status.cloud.google.com/
curl https://www.google.com/appsstatus/dashboard/incidents
```

Reduce concurrency:
```bash
export MAX_WORKERS=5
docker-compose restart gcp_functions_action_module
```

#### 2. Too Many Concurrent Executions

**Error:**
```
Quota exceeded for quota metric 'cloudfunctions.googleapis.com/gen2_api_call_count'
```

**Solutions:**

Check GCP quotas:
```bash
gcloud compute project-info describe MY_PROJECT_ID \
  --format="value(quotas)"
```

Reduce concurrent workers:
```bash
export MAX_WORKERS=5
docker-compose restart gcp_functions_action_module
```

Implement client-side rate limiting:
```python
# Add delays between batch requests
import time
for batch in batches:
    invoke_batch(batch)
    time.sleep(1)
```

Request quota increase:
```
GCP Console -> Quotas -> Cloud Functions API
Request higher limits
```

---

### Logging and Debugging

#### 1. Check Module Logs

View real-time logs:
```bash
docker-compose logs -f gcp_functions_action_module
```

View with timestamps:
```bash
docker-compose logs -f --timestamps gcp_functions_action_module
```

Filter by log level:
```bash
docker-compose logs gcp_functions_action_module | grep ERROR
docker-compose logs gcp_functions_action_module | grep WARNING
```

#### 2. Enable Debug Logging

Set debug level:
```bash
export LOG_LEVEL=DEBUG
docker-compose restart gcp_functions_action_module
```

View detailed logs:
```bash
docker-compose logs gcp_functions_action_module | head -100
```

#### 3. Check Execution Logs

Query database for execution history:
```bash
docker-compose exec postgres psql -U waddlebot -d waddlebot << 'SQL'
SELECT function_name, status_code, success, execution_time_ms, created_at
FROM gcp_function_invocations
ORDER BY created_at DESC
LIMIT 10;
SQL
```

Check specific function:
```bash
docker-compose exec postgres psql -U waddlebot -d waddlebot << 'SQL'
SELECT *
FROM gcp_function_invocations
WHERE function_name = 'my-function'
ORDER BY created_at DESC
LIMIT 5;
SQL
```

---

### Docker Issues

#### 1. Container Won't Start

**Check status:**
```bash
docker-compose ps
```

**View logs:**
```bash
docker-compose logs gcp_functions_action_module
```

**Rebuild:**
```bash
docker-compose build --no-cache gcp_functions_action_module
docker-compose up -d gcp_functions_action_module
```

#### 2. Port Already in Use

**Error:**
```
Error response from daemon: driver failed programming external connectivity
```

**Find what's using port:**
```bash
lsof -i :8081
```

**Use different port:**
```bash
export REST_PORT=8082
docker-compose up -d
```

#### 3. Disk Space Full

**Error:**
```
no space left on device
```

**Check space:**
```bash
df -h
```

**Clean up:**
```bash
docker system prune -a
```

---

## Quick Reference - Common Fixes

| Problem | Quick Fix |
|---------|-----------|
| Module won't start | Check GCP_SERVICE_ACCOUNT_KEY and GCP_PROJECT_ID |
| Health check fails | Verify database and GCP credentials |
| API returns 401 | Generate new JWT token via /api/v1/auth/token |
| GCP returns 403 | Check service account has cloudfunctions.invoker role |
| GCP returns 404 | Verify function exists in region with gcloud functions list |
| Invocation timeout | Increase FUNCTION_TIMEOUT environment variable |
| Batch size exceeded | Reduce to <= 100 functions or increase MAX_BATCH_SIZE |
| Slow invocations | Check GCP function performance, reduce concurrency |
| Port in use | Change REST_PORT or GRPC_PORT |
| Container won't start | Check logs: docker-compose logs gcp_functions_action_module |
| Disk full | Run docker system prune -a |

## Getting Help

If you can't resolve the issue:

1. **Gather diagnostic info:**
   ```bash
   docker-compose logs gcp_functions_action_module > logs.txt
   curl http://localhost:8081/health | jq . > health.json
   env | grep -E "GCP|DATABASE|JWT" > env.txt
   ```

2. **Check documentation:**
   - CONFIGURATION.md - All environment variables
   - API.md - Endpoint reference
   - ARCHITECTURE.md - System design

3. **Verify prerequisites:**
   - GCP project has Cloud Functions API enabled
   - Service account has correct IAM roles
   - Database is accessible
   - Network connectivity to GCP

4. **Contact support:**
   - Include logs with sensitive data removed
   - Include error messages and stack traces
   - Include module version
   - Describe what you were trying to do
