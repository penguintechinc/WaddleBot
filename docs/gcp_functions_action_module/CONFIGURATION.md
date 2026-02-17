# GCP Functions Action Module - Configuration

## Overview

The GCP Functions Action Module uses environment variables for configuration, with optional fallback to database-stored credentials. All settings are centralized in the `config.py` file and loaded at startup.

## Environment Variables

### GCP Configuration

#### GCP_PROJECT_ID
**Type:** String  
**Required:** Yes (for production)  
**Default:** "" (empty)  
**Description:** GCP project ID containing Cloud Functions

```bash
export GCP_PROJECT_ID="my-gcp-project"
```

Get from GCP Console or using gcloud:
```bash
gcloud config get-value project
```

#### GCP_REGION
**Type:** String  
**Default:** "us-central1"  
**Description:** Default GCP region for Cloud Functions

```bash
export GCP_REGION="us-central1"
```

Valid regions: us-central1, us-east1, us-east4, us-west1, etc.

#### GCP_SERVICE_ACCOUNT_KEY
**Type:** String (path or JSON)  
**Required:** Yes (for production)  
**Default:** "" (empty)  
**Description:** Service account credentials (JSON key or file path)

**Option 1: File path**
```bash
export GCP_SERVICE_ACCOUNT_KEY="/path/to/service-account-key.json"
```

**Option 2: Inline JSON**
```bash
export GCP_SERVICE_ACCOUNT_KEY='{"type":"service_account","project_id":"...","private_key":"..."}'
```

Generate using gcloud:
```bash
gcloud iam service-accounts keys create service-account-key.json \
  --iam-account=waddlebot@PROJECT_ID.iam.gserviceaccount.com
```

#### GCP_SERVICE_ACCOUNT_EMAIL
**Type:** String  
**Default:** "" (empty)  
**Description:** Service account email address

```bash
export GCP_SERVICE_ACCOUNT_EMAIL="waddlebot@my-project.iam.gserviceaccount.com"
```

Format: `account@project.iam.gserviceaccount.com`

#### GCP_API_TIMEOUT
**Type:** Integer (seconds)  
**Default:** 30  
**Description:** Timeout for GCP API calls

```bash
export GCP_API_TIMEOUT="30"
```

Increase if Cloud Functions are slow or in distant regions.

### Database Configuration

#### DATABASE_URL
**Type:** String  
**Required:** Yes  
**Default:** "postgres://waddlebot:password@localhost:5432/waddlebot"  
**Description:** PostgreSQL connection string

```bash
# Format: postgres://username:password@host:port/database
export DATABASE_URL="postgres://waddlebot:password@postgres:5432/waddlebot"
```

Supports:
- Standard PostgreSQL URLs
- Unix socket connections
- Connection parameters (sslmode=require, etc.)

#### REDIS_URL
**Type:** String  
**Default:** "" (empty, optional)  
**Description:** Redis connection for credential refresh

```bash
export REDIS_URL="redis://localhost:6379/0"
```

If set, module listens for credential updates on channel:
`credentials:gcp:bot:refreshed`

### Server Configuration

#### HOST
**Type:** String  
**Default:** "0.0.0.0"  
**Description:** Server bind address

```bash
export HOST="0.0.0.0"  # Listen on all interfaces
```

#### GRPC_PORT
**Type:** Integer  
**Default:** 50061  
**Valid Range:** 1-65535  
**Description:** gRPC server port

```bash
export GRPC_PORT="50061"
```

Used for processor/router communication.

#### REST_PORT
**Type:** Integer  
**Default:** 8081  
**Valid Range:** 1-65535  
**Description:** REST API server port

```bash
export REST_PORT="8081"
```

Used for third-party integrations.

#### MODULE_PORT
**Type:** Integer  
**Default:** 8081  
**Description:** Alias for REST_PORT

```bash
export MODULE_PORT="8081"
```

### Security Configuration

#### MODULE_SECRET_KEY
**Type:** String  
**Required:** Yes (for production)  
**Minimum Length:** 64 characters  
**Default:** "waddlebot_gcp_functions_action_secret_change_me_in_production"  
**Description:** Secret key for JWT signing

```bash
# Generate secure 64+ character key
export MODULE_SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
```

WARNING: Change this in production! Use strong, random key.

#### JWT_ALGORITHM
**Type:** String  
**Default:** "HS256"  
**Description:** JWT signing algorithm

```bash
export JWT_ALGORITHM="HS256"
```

Do not change unless you need different algorithm.

#### JWT_EXPIRATION_SECONDS
**Type:** Integer  
**Default:** 3600 (1 hour)  
**Description:** JWT token expiration time

```bash
export JWT_EXPIRATION_SECONDS="3600"
```

### Performance Settings

#### MAX_WORKERS
**Type:** Integer  
**Default:** 20  
**Description:** Maximum concurrent function executions

```bash
export MAX_WORKERS="20"
```

Adjust based on available resources and GCP quotas.

#### REQUEST_TIMEOUT
**Type:** Integer (seconds)  
**Default:** 30  
**Description:** HTTP request timeout for GCP API

```bash
export REQUEST_TIMEOUT="30"
```

#### MAX_BATCH_SIZE
**Type:** Integer  
**Default:** 100  
**Description:** Maximum functions per batch request

```bash
export MAX_BATCH_SIZE="100"
```

### Function Invocation Settings

#### FUNCTION_TIMEOUT
**Type:** Integer (seconds)  
**Default:** 60  
**Description:** Per-function execution timeout

```bash
export FUNCTION_TIMEOUT="60"
```

Increase if functions take longer to execute.

#### MAX_RETRIES
**Type:** Integer  
**Default:** 3  
**Description:** Maximum retry attempts

```bash
export MAX_RETRIES="3"
```

#### RETRY_DELAY
**Type:** Integer (seconds)  
**Default:** 1  
**Description:** Initial retry delay

```bash
export RETRY_DELAY="1"
```

Delay multiplied by (attempt + 1) for exponential backoff.

### Logging Configuration

#### LOG_LEVEL
**Type:** String  
**Default:** "INFO"  
**Valid Values:** DEBUG, INFO, WARNING, ERROR, CRITICAL  
**Description:** Logging level

```bash
export LOG_LEVEL="INFO"
```

Set to DEBUG for verbose logging during development.

#### LOG_DIR
**Type:** String (path)  
**Default:** "/var/log/waddlebotlog"  
**Description:** Directory for log files

```bash
export LOG_DIR="/var/log/waddlebotlog"
```

Directory must be writable by application.

#### ENABLE_SYSLOG
**Type:** Boolean  
**Default:** "false"  
**Valid Values:** "true", "false"  
**Description:** Enable syslog logging

```bash
export ENABLE_SYSLOG="false"  # or "true"
```

#### SYSLOG_HOST
**Type:** String  
**Default:** "localhost"  
**Description:** Syslog server hostname

```bash
export SYSLOG_HOST="localhost"
```

#### SYSLOG_PORT
**Type:** Integer  
**Default:** 514  
**Description:** Syslog server port

```bash
export SYSLOG_PORT="514"
```

#### SYSLOG_FACILITY
**Type:** String  
**Default:** "LOCAL0"  
**Valid Values:** LOCAL0-LOCAL7, USER, DAEMON, etc.  
**Description:** Syslog facility

```bash
export SYSLOG_FACILITY="LOCAL0"
```

### Module Information

#### MODULE_NAME
**Type:** String  
**Default:** "gcp_functions_action_module"  
**Description:** Module identifier

```bash
export MODULE_NAME="gcp_functions_action_module"
```

#### MODULE_VERSION
**Type:** String  
**Default:** "1.0.0"  
**Description:** Module version

```bash
export MODULE_VERSION="1.0.0"
```

### Testing/Development

#### TESTING_MODE
**Type:** Boolean  
**Default:** "true"  
**Valid Values:** "true", "false"  
**Description:** Skip strict validation for testing

```bash
export TESTING_MODE="true"
```

In production, set to "false" for strict validation.

## Example .env File

Create a `.env` file with all settings:

```bash
# GCP Configuration
GCP_PROJECT_ID=my-gcp-project
GCP_REGION=us-central1
GCP_SERVICE_ACCOUNT_KEY=/app/gcp-key.json
GCP_SERVICE_ACCOUNT_EMAIL=waddlebot@my-gcp-project.iam.gserviceaccount.com
GCP_API_TIMEOUT=30

# Database
DATABASE_URL=postgres://waddlebot:secure_password@postgres:5432/waddlebot

# Server
HOST=0.0.0.0
GRPC_PORT=50061
REST_PORT=8081
MODULE_PORT=8081

# Security
MODULE_SECRET_KEY=your_secure_64_char_key_here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_SECONDS=3600

# Performance
MAX_WORKERS=20
REQUEST_TIMEOUT=30
MAX_BATCH_SIZE=100

# Function Settings
FUNCTION_TIMEOUT=60
MAX_RETRIES=3
RETRY_DELAY=1

# Logging
LOG_LEVEL=INFO
LOG_DIR=/var/log/waddlebotlog
ENABLE_SYSLOG=false

# Module Info
MODULE_VERSION=1.0.0

# Testing
TESTING_MODE=false
```

## Loading Configuration

### Priority Order

1. Environment variables (highest priority)
2. .env file in working directory
3. Default values in config.py (lowest priority)

### Docker Compose

Pass variables via docker-compose.yml:

```yaml
services:
  gcp_functions_action_module:
    environment:
      - GCP_PROJECT_ID=${GCP_PROJECT_ID}
      - GCP_SERVICE_ACCOUNT_KEY=${GCP_SERVICE_ACCOUNT_KEY}
      - DATABASE_URL=${DATABASE_URL}
      - MODULE_SECRET_KEY=${MODULE_SECRET_KEY}
```

### Kubernetes

Use Secrets for sensitive values:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: gcp-secrets
type: Opaque
stringData:
  GCP_PROJECT_ID: my-project
  GCP_SERVICE_ACCOUNT_KEY: |
    {"type":"service_account",...}
  DATABASE_URL: postgres://...
  MODULE_SECRET_KEY: secure_key_here
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: gcp-functions-action-module
spec:
  template:
    spec:
      containers:
      - name: gcp-functions-action-module
        env:
        - name: GCP_PROJECT_ID
          valueFrom:
            secretKeyRef:
              name: gcp-secrets
              key: GCP_PROJECT_ID
```

## GCP Credentials Setup

### Step 1: Create Service Account

```bash
gcloud iam service-accounts create waddlebot-functions \
  --display-name "WaddleBot Cloud Functions"
```

### Step 2: Grant Permissions

```bash
gcloud projects add-iam-policy-binding MY_PROJECT_ID \
  --member "serviceAccount:waddlebot-functions@MY_PROJECT_ID.iam.gserviceaccount.com" \
  --role "roles/cloudfunctions.invoker"
```

### Step 3: Create Key

```bash
gcloud iam service-accounts keys create gcp-key.json \
  --iam-account=waddlebot-functions@MY_PROJECT_ID.iam.gserviceaccount.com
```

### Step 4: Set Configuration

```bash
export GCP_SERVICE_ACCOUNT_KEY="/path/to/gcp-key.json"
export GCP_PROJECT_ID="my-gcp-project"
```

## Validation

Configuration is validated on startup. In production mode (TESTING_MODE=false):

**Required:**
- GCP_PROJECT_ID
- GCP_SERVICE_ACCOUNT_KEY
- DATABASE_URL
- MODULE_SECRET_KEY (and must be changed from default)

**Errors stop application:**
```bash
docker-compose logs gcp_functions_action_module
# Configuration error: GCP_PROJECT_ID is required
```

**Warnings logged but don't stop application:**
```
WARNING: TESTING_MODE is true - this is not recommended for production
```

Run validation manually:

```python
from config import Config
try:
    Config.validate()
    print("Configuration valid")
except ValueError as e:
    print(f"Configuration error: {e}")
```

## Configuration Summary Endpoint

Get current configuration (without secrets):

```bash
curl http://localhost:8081/health | jq '.stats'
```

Returns:

```json
{
  "module": "gcp_functions_action_module",
  "version": "1.0.0",
  "gcp_project": "my-project",
  "gcp_region": "us-central1",
  "grpc_port": 50061,
  "rest_port": 8081,
  "max_workers": 20,
  "max_batch_size": 100,
  "log_level": "INFO"
}
```

## Troubleshooting Configuration

**Module won't start:**
- Check GCP_PROJECT_ID is set
- Check GCP_SERVICE_ACCOUNT_KEY path/content
- Check DATABASE_URL is valid: `psql $DATABASE_URL`
- Check logs for validation errors

**API calls fail with 500:**
- Check GCP credentials are valid
- Check GCP project has Cloud Functions API enabled
- Check service account has correct IAM roles

**Function invocations timeout:**
- Increase FUNCTION_TIMEOUT
- Check GCP Cloud Functions are responsive
- Check network connectivity to GCP

**Batch operations slow:**
- Increase MAX_WORKERS
- Check GCP quotas and limits
- Monitor GCP API usage

See TROUBLESHOOTING.md for more solutions.
