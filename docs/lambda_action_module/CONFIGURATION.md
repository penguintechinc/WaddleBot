# Lambda Action Module - Configuration Reference

## Overview

The Lambda Action Module uses environment variables for configuration. All variables have sensible defaults except those marked REQUIRED.

## Environment Variables

### AWS Configuration

| Variable | Default | Required | Purpose |
|----------|---------|----------|---------|
| `AWS_ACCESS_KEY_ID` | - | YES | AWS IAM access key for Lambda invocations |
| `AWS_SECRET_ACCESS_KEY` | - | YES | AWS IAM secret key |
| `AWS_REGION` | us-east-1 | NO | AWS region for Lambda functions |
| `AWS_LAMBDA_ROLE_ARN` | - | NO | IAM role ARN for Lambda functions (informational) |

**Example**:
```env
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_REGION=us-west-2
AWS_LAMBDA_ROLE_ARN=arn:aws:iam::123456789:role/lambda-execution-role
```

### Database Configuration

| Variable | Default | Required | Purpose |
|----------|---------|----------|---------|
| `DATABASE_URL` | postgres://user:pass@localhost:5432/waddlebot | YES | PostgreSQL connection URL |

**Format**:
```
postgres://username:password@host:port/database
```

**Examples**:
```env
# Local PostgreSQL
DATABASE_URL=postgres://waddlebot:password@localhost:5432/waddlebot

# Docker network
DATABASE_URL=postgres://waddlebot:password@postgres:5432/waddlebot

# RDS (AWS)
DATABASE_URL=postgres://waddlebot:password@mydb.123456789.us-east-1.rds.amazonaws.com:5432/waddlebot

# With SSL
DATABASE_URL=postgres://waddlebot:password@host:5432/waddlebot?sslmode=require
```

**Note**: PyDAL expects `postgres://` not `postgresql://`. The module automatically converts.

### Server Configuration

| Variable | Default | Required | Purpose |
|----------|---------|----------|---------|
| `HOST` | 0.0.0.0 | NO | Bind address for servers |
| `GRPC_PORT` | 50060 | NO | gRPC server port |
| `REST_PORT` | 8080 | NO | REST API server port |

**Example**:
```env
HOST=0.0.0.0
GRPC_PORT=50060
REST_PORT=8080
```

**Port Requirements**:
- gRPC port (50060): Used by processor/router
- REST port (8080): Used by HTTP clients
- Both must be unique on the same host

### Security Configuration

| Variable | Default | Required | Purpose |
|----------|---------|----------|---------|
| `MODULE_SECRET_KEY` | change_me... | YES | JWT signing secret (64+ characters) |
| `JWT_ALGORITHM` | HS256 | NO | JWT algorithm (don't change) |
| `JWT_EXPIRATION_SECONDS` | 3600 | NO | Token lifetime in seconds |

**Example**:
```env
MODULE_SECRET_KEY=your-super-secret-64-character-key-that-must-be-changed-in-production-xxxxxxxxxx
JWT_ALGORITHM=HS256
JWT_EXPIRATION_SECONDS=3600
```

**Generating Secret Key**:
```bash
# Linux/macOS
openssl rand -base64 48

# Python
python3 -c "import secrets; print(secrets.token_urlsafe(48))"

# Result should be 64+ characters
```

### Module Information

| Variable | Default | Required | Purpose |
|----------|---------|----------|---------|
| `MODULE_NAME` | lambda_action_module | NO | Module identifier |
| `MODULE_VERSION` | 1.0.0 | NO | Module version |

### Performance Settings

| Variable | Default | Required | Purpose |
|----------|---------|----------|---------|
| `MAX_CONCURRENT_REQUESTS` | 100 | NO | Max concurrent Lambda invocations |
| `REQUEST_TIMEOUT` | 30 | NO | Request timeout in seconds |
| `LAMBDA_TIMEOUT` | 300 | NO | Lambda function timeout in seconds |
| `LAMBDA_MEMORY_SIZE` | 512 | NO | Lambda default memory in MB |
| `LAMBDA_MAX_RETRIES` | 3 | NO | Max retries for failed invocations |
| `MAX_RETRIES` | 3 | NO | General retry count |
| `RETRY_DELAY` | 1.0 | NO | Delay between retries in seconds |

**Example**:
```env
MAX_CONCURRENT_REQUESTS=100
REQUEST_TIMEOUT=30
LAMBDA_TIMEOUT=300
LAMBDA_MEMORY_SIZE=512
LAMBDA_MAX_RETRIES=3
```

**Tuning Recommendations**:
- Increase `MAX_CONCURRENT_REQUESTS` for high throughput (monitor AWS account limits)
- Increase `REQUEST_TIMEOUT` for long-running functions
- Adjust `LAMBDA_TIMEOUT` based on expected function runtime

### Lambda-Specific Configuration

| Variable | Default | Required | Purpose |
|----------|---------|----------|---------|
| `LAMBDA_FUNCTION_PREFIX` | waddlebot- | NO | Prefix for Lambda function names |

**Example**:
```env
LAMBDA_FUNCTION_PREFIX=waddlebot-
```

Functions named `waddlebot-process`, `waddlebot-notify`, etc. will be invoked.

### Logging Configuration

| Variable | Default | Required | Purpose |
|----------|---------|----------|---------|
| `LOG_LEVEL` | INFO | NO | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `LOG_DIR` | /var/log/waddlebotlog | NO | Log file directory |
| `ENABLE_SYSLOG` | false | NO | Enable syslog output |
| `SYSLOG_HOST` | localhost | NO | Syslog server host |
| `SYSLOG_PORT` | 514 | NO | Syslog server port |
| `SYSLOG_FACILITY` | LOCAL0 | NO | Syslog facility code |

**Example**:
```env
LOG_LEVEL=INFO
LOG_DIR=/var/log/waddlebotlog
ENABLE_SYSLOG=false
SYSLOG_HOST=localhost
SYSLOG_PORT=514
SYSLOG_FACILITY=LOCAL0
```

**Log Levels**:
- `DEBUG`: Detailed execution flow (not recommended for production)
- `INFO`: Key operations (default, recommended)
- `WARNING`: Configuration issues, credential problems
- `ERROR`: Failures and exceptions

**Syslog Facilities**:
- LOCAL0 through LOCAL7 (typically LOCAL0-LOCAL3 for applications)

### Redis Configuration (Optional)

| Variable | Default | Required | Purpose |
|----------|---------|----------|---------|
| `REDIS_URL` | - | NO | Redis connection URL for credential updates |

**Format**:
```
redis://host:port/db
```

**Example**:
```env
REDIS_URL=redis://localhost:6379/0
```

If `REDIS_URL` is empty, Redis credential listening is disabled.

## Example .env File

### Development

```env
# AWS Configuration
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_REGION=us-east-1

# Database
DATABASE_URL=postgres://waddlebot:password@localhost:5432/waddlebot

# Server
HOST=0.0.0.0
GRPC_PORT=50060
REST_PORT=8080

# Security
MODULE_SECRET_KEY=change_me_in_production_64_char_key_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Performance
MAX_CONCURRENT_REQUESTS=100
REQUEST_TIMEOUT=30
LAMBDA_TIMEOUT=300

# Logging
LOG_LEVEL=DEBUG
LOG_DIR=/var/log/waddlebotlog

# Redis (optional)
REDIS_URL=
```

### Production

```env
# AWS Configuration (use IAM role in production)
AWS_REGION=us-east-1

# Database (RDS)
DATABASE_URL=postgres://waddlebot:SECURE_PASSWORD@mydb.rds.amazonaws.com:5432/waddlebot

# Server
HOST=0.0.0.0
GRPC_PORT=50060
REST_PORT=8080

# Security (MUST be changed)
MODULE_SECRET_KEY=your-actual-secure-64-character-key-from-secure-generation-process

# Performance
MAX_CONCURRENT_REQUESTS=200
REQUEST_TIMEOUT=30
LAMBDA_TIMEOUT=300

# Logging
LOG_LEVEL=INFO
LOG_DIR=/var/log/waddlebotlog
ENABLE_SYSLOG=true
SYSLOG_HOST=syslog.example.com
SYSLOG_PORT=514

# Redis (for credential updates)
REDIS_URL=redis://redis.example.com:6379/0
```

### Docker Compose

```env
# AWS Configuration
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_REGION=us-east-1

# Database (Docker network)
DATABASE_URL=postgres://waddlebot:password@postgres_lambda:5432/waddlebot

# Server
HOST=0.0.0.0
GRPC_PORT=50060
REST_PORT=8080

# Security
MODULE_SECRET_KEY=docker-compose-dev-key-must-be-64-characters-long-xxxxxxxxxxxxxxxxx

# Logging
LOG_LEVEL=INFO
LOG_DIR=/var/log/waddlebotlog
```

## Configuration Validation

The module validates configuration on startup:

```python
errors = Config.validate()
if errors:
    # Exit with error
    print("Configuration errors:", errors)
    sys.exit(1)
```

### Validation Rules

- `AWS_ACCESS_KEY_ID` must be set
- `AWS_SECRET_ACCESS_KEY` must be set
- `AWS_REGION` must be set
- `DATABASE_URL` must be set
- `MODULE_SECRET_KEY` must be 64+ characters
- `GRPC_PORT` must be 1-65535
- `REST_PORT` must be 1-65535

## Configuration Priority

The module loads configuration in this order:

1. **Environment Variables** (highest priority)
   - Set in shell, .env file, or container
2. **Python Defaults** (lowest priority)
   - Hard-coded in config.py

To override a default, set the environment variable.

## Database Integration (Optional)

Instead of using environment variables, credentials can be stored in the database:

### Setup Database Integration

1. Create credentials in database:

```sql
INSERT INTO platform_integrations (
  platform,
  integration_type,
  client_id,
  client_secret,
  config_data,
  is_active
) VALUES (
  'aws_lambda',
  'bot',
  'AKIAIOSFODNN7EXAMPLE',
  'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',
  '{
    "region": "us-east-1",
    "role_arn": "arn:aws:iam::123456789:role/lambda-role"
  }',
  true
);
```

2. Call `Config.load_credentials_from_db(db)` in app startup

3. Optionally, listen for credential updates:

```python
listener_thread = Config.start_credential_listener(redis_client)
```

## Secrets Management Best Practices

### AWS Credentials

- **Development**: Store in .env (gitignore enabled)
- **Docker**: Use environment file
- **Kubernetes**: Use Secrets resource
- **Production**: Use IAM role (no explicit credentials)

### JWT Secret

- **Development**: Use provided default (for dev only)
- **Production**: Generate secure random 64+ character string
- **Rotation**: Regenerate periodically, update all instances

### Database Password

- **Development**: Simple password fine
- **Production**: Use strong password + encryption in transit

## Validation Checklist

Before deploying to production:

- [ ] `AWS_ACCESS_KEY_ID` is set and valid
- [ ] `AWS_SECRET_ACCESS_KEY` is set and valid
- [ ] `AWS_REGION` matches your Lambda region
- [ ] `DATABASE_URL` is correct and tested
- [ ] `MODULE_SECRET_KEY` is 64+ characters and secure
- [ ] All passwords are strong
- [ ] Database has required tables
- [ ] Log directory exists and is writable
- [ ] Ports 50060 and 8080 are available
- [ ] AWS IAM role has Lambda permissions

## Environment-Specific Configurations

### Local Development

```bash
export AWS_PROFILE=default  # Use AWS CLI credentials
export LOG_LEVEL=DEBUG
export ENABLE_SYSLOG=false
```

### Docker Container

```dockerfile
FROM python:3.13
ENV LOG_LEVEL=INFO
ENV ENABLE_SYSLOG=true
```

### Kubernetes

```yaml
env:
- name: AWS_REGION
  value: "us-east-1"
- name: LOG_LEVEL
  value: "INFO"
- name: AWS_ACCESS_KEY_ID
  valueFrom:
    secretKeyRef:
      name: aws-credentials
      key: access-key-id
```

## Configuration Examples

### AWS Region Override

```env
AWS_REGION=eu-west-1
```

Invokes Lambda functions in Ireland instead of N. Virginia.

### High Throughput Setup

```env
MAX_CONCURRENT_REQUESTS=500
LAMBDA_TIMEOUT=600
REQUEST_TIMEOUT=60
```

Suitable for bulk processing workloads.

### Debug Mode

```env
LOG_LEVEL=DEBUG
ENABLE_SYSLOG=false
REQUEST_TIMEOUT=60
```

Useful for troubleshooting issues.

## Summary

For quick reference:

**Required (must set)**:
- AWS_ACCESS_KEY_ID
- AWS_SECRET_ACCESS_KEY
- DATABASE_URL
- MODULE_SECRET_KEY (64+ chars)

**Strongly Recommended**:
- AWS_REGION (if not us-east-1)
- LOG_LEVEL=INFO (production)
- Enable SYSLOG (production)

**Optional**:
- REDIS_URL (for credential updates)
- Performance tuning variables

See [USAGE.md](USAGE.md) for setup instructions and [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues.
