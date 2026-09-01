# Lambda Action Module - Troubleshooting Guide

## Common Issues and Solutions

### Authentication & Credentials

#### Issue: "AWS_ACCESS_KEY_ID is required"

**Symptoms**:
```
Configuration errors: ['AWS_ACCESS_KEY_ID is required', 'AWS_SECRET_ACCESS_KEY is required']
```

**Causes**:
- Environment variables not set
- .env file not loaded
- Credentials not in database

**Solutions**:

1. **Check .env file exists and has credentials**:
```bash
cat .env | grep AWS_ACCESS_KEY_ID
```

2. **Load .env file explicitly**:
```bash
source .env
python app.py
```

3. **Test with AWS CLI**:
```bash
aws lambda list-functions
```

4. **Verify credentials in environment**:
```bash
echo $AWS_ACCESS_KEY_ID
echo $AWS_SECRET_ACCESS_KEY
```

5. **Check if database integration is working**:
```sql
SELECT * FROM platform_integrations 
WHERE platform='aws_lambda' AND is_active=TRUE;
```

#### Issue: "The provided AWS credentials are not valid"

**Symptoms**:
```
ClientError: An error occurred (InvalidSignatureException) when calling the 
Invoke operation: The provided AWS credentials are not valid
```

**Causes**:
- Credentials are expired
- Wrong access key or secret key
- Credentials revoked
- AWS account suspended

**Solutions**:

1. **Generate new credentials in AWS console**:
   - IAM > Users > Select user > Security Credentials > Create Access Key

2. **Test credentials locally**:
```bash
aws sts get-caller-identity --profile waddlebot
```

3. **Verify credentials have Lambda permissions**:
```bash
aws iam get-user-policy --user-name waddlebot --policy-name lambda-policy
```

4. **Check AWS account status**:
   - Log into AWS console and verify account is in good standing

#### Issue: "User is not authorized to perform: lambda:InvokeFunction"

**Symptoms**:
```
ClientError: An error occurred (AccessDeniedException) when calling the Invoke 
operation: User is not authorized to perform: lambda:InvokeFunction
```

**Causes**:
- IAM user/role lacks Lambda invocation permissions
- Lambda function's resource policy blocks access
- Regional restrictions

**Solutions**:

1. **Attach Lambda full access** (development only):
```bash
aws iam attach-user-policy \
  --user-name waddlebot \
  --policy-arn arn:aws:iam::aws:policy/AWSLambdaFullAccess
```

2. **Create custom IAM policy**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "lambda:InvokeFunction",
      "Resource": "arn:aws:lambda:*:*:function/*"
    }
  ]
}
```

3. **Verify policy is attached**:
```bash
aws iam list-user-policies --user-name waddlebot
aws iam list-attached-user-policies --user-name waddlebot
```

4. **Test with mock**:
```python
from moto import mock_lambda
@mock_lambda
def test():
    # Should work with moto even without real credentials
    pass
```

### Database Issues

#### Issue: "could not connect to server: Connection refused"

**Symptoms**:
```
psycopg2.OperationalError: could not connect to server: Connection refused
Is the server running on host "localhost" (127.0.0.1) and accepting
TCP/IP connections on port 5432?
```

**Causes**:
- PostgreSQL not running
- Wrong host/port in DATABASE_URL
- Database doesn't exist
- Firewall blocking connection

**Solutions**:

1. **Check PostgreSQL is running**:
```bash
docker-compose ps
# or
sudo systemctl status postgresql
```

2. **Start PostgreSQL**:
```bash
docker-compose up -d postgres_lambda
# or
brew services start postgresql
```

3. **Test connection**:
```bash
psql "postgres://waddlebot:password@localhost:5432/waddlebot"
```

4. **Verify DATABASE_URL**:
```bash
echo $DATABASE_URL
# Should be: postgres://user:pass@host:port/database
```

5. **Create database if missing**:
```bash
createdb -U waddlebot waddlebot
```

6. **Check firewall**:
```bash
telnet localhost 5432
nc -zv localhost 5432
```

#### Issue: "relation "lambda_invocations" does not exist"

**Symptoms**:
```
ProgrammingError: relation "lambda_invocations" does not exist
LINE 1: INSERT INTO lambda_invocations (...)
```

**Causes**:
- Table not created in database
- Wrong database selected
- Table name typo

**Solutions**:

1. **Create table manually**:
```sql
CREATE TABLE lambda_invocations (
    id SERIAL PRIMARY KEY,
    function_name VARCHAR(255) NOT NULL,
    invocation_type VARCHAR(50) NOT NULL,
    payload TEXT,
    alias VARCHAR(255),
    version VARCHAR(50),
    status_code INTEGER,
    response_payload TEXT,
    function_error VARCHAR(255),
    executed_version VARCHAR(50),
    request_id VARCHAR(255),
    success BOOLEAN,
    error_message TEXT,
    invoked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);
```

2. **Verify table exists**:
```sql
\dt lambda_invocations
SELECT * FROM information_schema.tables 
WHERE table_name='lambda_invocations';
```

3. **Check database selection**:
```bash
psql -d waddlebot -c "\dt"
```

### Lambda Invocation Issues

#### Issue: "Function not found"

**Symptoms**:
```json
{
  "success": false,
  "error": "Function not found",
  "status_code": 0
}
```

**Causes**:
- Lambda function doesn't exist in AWS
- Wrong function name
- Function in different region
- Function was deleted

**Solutions**:

1. **List available functions**:
```bash
curl -X GET http://localhost:8080/api/v1/functions \
  -H "Authorization: Bearer $TOKEN"
```

2. **Check function exists in AWS console**:
   - AWS > Lambda > Functions > Look for your function name

3. **Verify function name**:
```bash
aws lambda list-functions --region us-east-1 | jq '.Functions[].FunctionName'
```

4. **Check region**:
```bash
# Ensure AWS_REGION matches function region
echo $AWS_REGION
```

5. **Create test function** (if missing):
```bash
aws lambda create-function \
  --function-name my-test-function \
  --runtime python3.11 \
  --role arn:aws:iam::ACCOUNT:role/lambda-role \
  --handler index.handler \
  --zip-file fileb://lambda_function.zip
```

#### Issue: "RequestId not available"

**Symptoms**:
```json
{
  "success": false,
  "error": "RequestId not available",
  "status_code": 0
}
```

**Causes**:
- Invalid payload format
- Lambda service error
- Timeout during invocation

**Solutions**:

1. **Verify payload is valid JSON**:
```bash
curl -X POST http://localhost:8080/api/v1/invoke \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "function_name": "test",
    "payload": "{\"valid\": \"json\"}"
  }'
```

2. **Check payload size**:
```bash
# Max 6MB
echo -n 'PAYLOAD' | wc -c
```

3. **Increase timeout**:
```env
REQUEST_TIMEOUT=60
LAMBDA_TIMEOUT=600
```

4. **Check AWS service status**:
   - https://status.aws.amazon.com/

#### Issue: Lambda invocation times out

**Symptoms**:
```
Timeout waiting for response
or
connection timed out
```

**Causes**:
- Lambda function taking too long
- REQUEST_TIMEOUT too short
- Network latency
- Lambda cold start

**Solutions**:

1. **Increase timeout**:
```env
REQUEST_TIMEOUT=60        # 60 seconds
LAMBDA_TIMEOUT=600        # 10 minutes
```

2. **Check Lambda function performance**:
```bash
aws lambda get-function-concurrency \
  --function-name my-function
```

3. **Enable Lambda insights**:
   - AWS Console > Lambda > Select function > Monitoring > Enable insights

4. **Test function locally**:
```python
# Test that function completes quickly
import time
start = time.time()
# Run function logic
duration = time.time() - start
assert duration < 30  # Seconds
```

5. **Increase Lambda memory** (improves speed):
```bash
aws lambda update-function-configuration \
  --function-name my-function \
  --memory-size 1024  # Increase from default 512
```

#### Issue: "Throttling" error

**Symptoms**:
```json
{
  "success": false,
  "error": "ThrottlingException",
  "status_code": 0
}
```

**Causes**:
- Exceeding concurrent Lambda limit (1000 by default)
- Rate limit exceeded
- Account throttled

**Solutions**:

1. **Check concurrent limit**:
```bash
aws lambda get-account-settings --query 'AccountUsage'
```

2. **Increase concurrent limit** (AWS Support):
   - Contact AWS Support to increase limit

3. **Implement retry logic**:
```env
LAMBDA_MAX_RETRIES=3
RETRY_DELAY=1.0
```

4. **Reduce concurrent requests**:
```env
MAX_CONCURRENT_REQUESTS=50  # Reduce from 100
```

### REST API Issues

#### Issue: "Invalid or expired token"

**Symptoms**:
```json
{
  "error": "Invalid or expired token"
}
```

**Status**: 401 Unauthorized

**Causes**:
- Token expired (older than JWT_EXPIRATION_SECONDS)
- Token modified
- Wrong MODULE_SECRET_KEY

**Solutions**:

1. **Generate new token**:
```bash
curl -X POST http://localhost:8080/api/v1/token \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "waddlebot",
    "client_secret": "secret"
  }'
```

2. **Extend token lifetime**:
```env
JWT_EXPIRATION_SECONDS=7200  # 2 hours instead of 1
```

3. **Verify MODULE_SECRET_KEY hasn't changed**:
```bash
# If changed, all existing tokens become invalid
echo $MODULE_SECRET_KEY
```

#### Issue: "Missing or invalid Authorization header"

**Symptoms**:
```json
{
  "error": "Missing or invalid Authorization header"
}
```

**Status**: 401 Unauthorized

**Causes**:
- No Authorization header sent
- Wrong header format
- Bearer token missing

**Solutions**:

1. **Include Authorization header**:
```bash
curl -X GET http://localhost:8080/api/v1/functions \
  -H "Authorization: Bearer $TOKEN"
```

2. **Verify header format**:
```bash
# Correct: Bearer <token>
# Wrong: Token <token>
# Wrong: <token>
```

3. **Get valid token**:
```bash
TOKEN=$(curl -s -X POST http://localhost:8080/api/v1/token \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "test",
    "client_secret": "secret"
  }' | jq -r '.token')

echo $TOKEN
```

### Configuration Issues

#### Issue: "MODULE_SECRET_KEY must be at least 64 characters"

**Causes**:
- Secret key too short
- Not set at all

**Solution**:

1. **Generate 64+ character key**:
```bash
# Linux/macOS
openssl rand -base64 48

# Python
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

2. **Set in .env**:
```env
MODULE_SECRET_KEY=your-generated-64-plus-character-key-here
```

3. **Verify length**:
```bash
echo -n "YOUR_KEY" | wc -c
# Should be >= 64
```

#### Issue: "GRPC_PORT must be between 1 and 65535"

**Causes**:
- Port out of valid range
- Port already in use

**Solutions**:

1. **Use valid port** (1-65535):
```env
GRPC_PORT=50060
REST_PORT=8080
```

2. **Check port is available**:
```bash
lsof -i :50060
netstat -tuln | grep 50060
```

3. **Kill process using port**:
```bash
kill -9 $(lsof -t -i :50060)
```

### Docker Issues

#### Issue: "docker-compose up" fails

**Symptoms**:
```
ERROR: docker-compose command not found
or
Cannot connect to Docker daemon
```

**Solutions**:

1. **Install Docker Compose**:
```bash
pip install docker-compose
# or
brew install docker-compose
```

2. **Start Docker daemon**:
```bash
# macOS
open -a Docker

# Linux
sudo systemctl start docker
```

3. **Check Docker running**:
```bash
docker ps
docker --version
```

#### Issue: "Port 8080 is already allocated"

**Causes**:
- Another service using port
- Previous container still running

**Solutions**:

1. **Stop existing containers**:
```bash
docker-compose down
```

2. **Use different port**:
```bash
docker run -p 8090:8080 lambda_action_module:latest
```

3. **Find process using port**:
```bash
lsof -i :8080
kill -9 <PID>
```

### Performance Issues

#### Issue: Module responding slowly

**Symptoms**:
- Requests taking 10+ seconds
- High CPU usage
- Database connections maxed out

**Solutions**:

1. **Check database connection pool**:
```sql
SELECT datname, usename, state, count(*) 
FROM pg_stat_activity 
GROUP BY datname, usename, state;
```

2. **Increase pool size**:
```python
# In app.py
db = DAL(Config.DATABASE_URL, folder=None, pool_size=20)  # Increase from 10
```

3. **Reduce MAX_CONCURRENT_REQUESTS**:
```env
MAX_CONCURRENT_REQUESTS=50  # Reduce load
```

4. **Enable query logging**:
```env
LOG_LEVEL=DEBUG
```

5. **Monitor AWS Lambda limits**:
```bash
aws lambda get-account-settings \
  --query 'AccountUsage.ConcurrentExecutions'
```

### Logging Issues

#### Issue: "Log file not written"

**Symptoms**:
- No log files in `/var/log/waddlebotlog/`

**Causes**:
- Directory doesn't exist
- Permission denied
- Wrong LOG_DIR

**Solutions**:

1. **Create log directory**:
```bash
mkdir -p /var/log/waddlebotlog
chmod 777 /var/log/waddlebotlog
```

2. **Verify LOG_DIR**:
```bash
echo $LOG_DIR
ls -la /var/log/waddlebotlog/
```

3. **Check permissions**:
```bash
stat /var/log/waddlebotlog/
# Should be writable by container user
```

4. **Use stdout logging** (Docker):
```env
LOG_LEVEL=INFO
# Logs to stdout, captured by docker logs
```

## Health Diagnostics

### Check Module Health

```bash
# Health endpoint
curl -X GET http://localhost:8080/health | jq '.'

# Expected response
{
  "status": "healthy",
  "module": "lambda_action_module",
  "version": "1.0.0",
  "config": {
    "database_configured": true,
    "aws_configured": true
  }
}
```

### Verify All Components

```bash
#!/bin/bash

echo "1. Checking database..."
psql $DATABASE_URL -c "SELECT 1" && echo "✓ Database OK"

echo "2. Checking AWS credentials..."
aws sts get-caller-identity && echo "✓ AWS OK"

echo "3. Checking Lambda access..."
aws lambda list-functions --max-items 1 && echo "✓ Lambda OK"

echo "4. Checking REST API..."
curl -s http://localhost:8080/health | jq '.status' && echo "✓ REST API OK"

echo "5. Checking gRPC..."
grpcurl -plaintext localhost:50060 list && echo "✓ gRPC OK"
```

## Getting Help

If issues persist:

1. **Check logs**:
```bash
docker-compose logs -f lambda_action_module
```

2. **Run tests**:
```bash
pytest tests/ -v
```

3. **Check configuration**:
```bash
curl -X GET http://localhost:8080/health | jq '.config'
```

4. **Contact support**:
   - Check DEVELOPMENT.md in main repository
   - Review similar module documentation
   - Examine source code in services/

See [CONFIGURATION.md](CONFIGURATION.md) and [API.md](API.md) for additional reference.
