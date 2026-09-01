# OpenWhisk Action Module - Troubleshooting Guide

## Common Issues

### Authentication & Credentials

#### Issue: "Invalid API key"

**Symptoms**:
```json
{"error": "Unauthorized"}
```

**Causes**:
- Wrong API key format
- Expired API key
- Invalid namespace

**Solutions**:

1. **Verify API key format** (namespace:key):
```bash
echo $OPENWHISK_AUTH_KEY
# Should be: waddlebot@example.com_dev:abc123...
```

2. **Get correct API key**:
```bash
# IBM Cloud
ibmcloud fn property get --auth

# Local
wsk property get --auth
```

3. **Test API key**:
```bash
curl -u YOUR_NAMESPACE:This15TotallyAnExampleKey! https://openwhisk.example.com/api/v1/namespaces
```

#### Issue: "Cannot connect to OpenWhisk"

**Symptoms**:
```
Connection refused or timeout
```

**Causes**:
- Wrong API host URL
- OpenWhisk not running
- Network unreachable

**Solutions**:

1. **Verify API host**:
```bash
echo $OPENWHISK_API_HOST
curl -X GET $OPENWHISK_API_HOST/api/v1/namespaces
```

2. **Check OpenWhisk is running**:
```bash
# Docker
docker ps | grep openwhisk

# IBM Cloud
ibmcloud fn status
```

3. **Test network**:
```bash
ping openwhisk.example.com
curl https://openwhisk.example.com
```

### Database Issues

#### Issue: "relation "openwhisk_action_executions" does not exist"

**Symptoms**:
```
ProgrammingError: relation "openwhisk_action_executions" does not exist
```

**Solutions**:

1. **Create table**:
```sql
CREATE TABLE openwhisk_action_executions (
    id SERIAL PRIMARY KEY,
    execution_id VARCHAR(255) UNIQUE,
    namespace VARCHAR(255),
    action_name VARCHAR(255),
    action_type VARCHAR(50),
    payload TEXT,
    blocking BOOLEAN,
    timeout INTEGER,
    activation_id VARCHAR(255),
    result TEXT,
    duration_ms INTEGER,
    status VARCHAR(50),
    success BOOLEAN,
    error TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);
```

### Action Invocation Issues

#### Issue: "Action not found"

**Symptoms**:
```json
{"error": "The action does not exist"}
```

**Solutions**:

1. **Verify action exists**:
```bash
wsk action list
```

2. **Create test action**:
```bash
echo 'function main(params) { return {hello: "world"}; }' > test.js
wsk action create test test.js
```

3. **Check namespace**:
```bash
# Ensure correct namespace in request
curl -X POST http://localhost:8082/api/v1/actions/invoke \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"action_name":"test","namespace":"guest"}'
```

#### Issue: "Timeout during action execution"

**Solutions**:

1. **Increase timeout**:
```env
REQUEST_TIMEOUT=60
DEFAULT_ACTION_TIMEOUT=120000
```

2. **Check action performance**:
```bash
wsk action invoke test --result --blocking
```

3. **Increase action memory** (if supported):
```bash
wsk action update test --memory 512
```

### REST API Issues

#### Issue: "Invalid or expired token"

**Symptoms**:
```json
{"error": "Invalid or expired token"}
```

**Solutions**:

1. **Generate new token**:
```bash
curl -X POST http://localhost:8082/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"api_key":"your-key"}'
```

2. **Extend token lifetime**:
```env
JWT_EXPIRATION_SECONDS=7200
```

### Configuration Issues

#### Issue: "TESTING_MODE validation error in production"

**Symptoms**:
```
ValueError: MODULE_SECRET_KEY must be set to a secure value
```

**Solutions**:

1. **Set production MODE_SECRET_KEY**:
```bash
# Generate secure key
openssl rand -base64 48
```

2. **Disable testing mode**:
```env
TESTING_MODE=false
MODULE_SECRET_KEY=your-actual-secure-key
```

## Health Diagnostics

### Check Module Health

```bash
curl -X GET http://localhost:8082/health | jq '.'
```

### Verify Components

```bash
#!/bin/bash

echo "1. Checking database..."
psql $DATABASE_URL -c "SELECT 1" && echo "✓ Database OK"

echo "2. Checking OpenWhisk..."
curl -u YOUR_NAMESPACE:This15TotallyAnExampleKey! $OPENWHISK_API_HOST/api/v1/namespaces && echo "✓ OpenWhisk OK"

echo "3. Checking REST API..."
curl -s http://localhost:8082/health | jq '.status' && echo "✓ REST API OK"

echo "4. Checking gRPC..."
grpcurl -plaintext localhost:50062 list && echo "✓ gRPC OK"
```

## Getting Help

1. Check logs (this module is not currently wired into `docker-compose.yml` as its own service —
   run it directly and check its log file/stdout):
```bash
tail -f /var/log/waddlebotlog/openwhisk_action_module.log
```

2. Run tests:
```bash
pytest tests/ -v
```

3. Check configuration:
```bash
curl http://localhost:8082/health | jq '.config'
```

See [CONFIGURATION.md](CONFIGURATION.md) and [API.md](API.md) for reference.
