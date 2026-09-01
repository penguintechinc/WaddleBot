# Lambda Action Module - Usage Guide

## Getting Started

This guide walks you through setting up and using the Lambda Action Module for the first time.

## Prerequisites

- Docker & Docker Compose
- AWS Account with Lambda permissions
- PostgreSQL database (or Docker container)
- Python 3.13+ (for local development)
- AWS IAM credentials with Lambda invocation permissions

## Quick Start (Docker)

### 1. Clone and Navigate

```bash
cd /home/penguin/code/waddlebot/action/pushing/lambda_action_module/
```

### 2. Configure Environment

Copy the example environment file and edit it:

```bash
cp .env.example .env
```

Edit `.env` with your AWS credentials:

```env
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_REGION=us-east-1
DATABASE_URL=postgres://waddlebot:password@localhost:5432/waddlebot
MODULE_SECRET_KEY=your-64-character-secret-key-here-must-be-64-chars-or-longer
```

### 3. Start with Docker Compose

```bash
docker-compose up -d
```

Verify services are running:

```bash
docker-compose ps
```

Expected output:
```
NAME                       STATUS
lambda_action_module       Up 2 seconds
postgres_lambda            Up 3 seconds (health: healthy)
```

### 4. Verify Module is Running

```bash
curl http://localhost:8080/health
```

Expected response:
```json
{
  "status": "healthy",
  "module": "lambda_action_module",
  "version": "1.0.0",
  "timestamp": "2026-02-16T21:30:45.123456",
  "config": {
    "module_name": "lambda_action_module",
    "module_version": "1.0.0",
    "grpc_port": 50060,
    "rest_port": 8080,
    "database_configured": true,
    "aws_configured": true,
    "aws_region": "us-east-1",
    "max_concurrent_requests": 100,
    "request_timeout": 30,
    "log_level": "INFO",
    "credentials_from_db": false
  }
}
```

## AWS Credentials Setup

### Using Environment Variables (Recommended for Development)

The simplest approach is to set environment variables in your `.env` file:

```env
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1
```

### Using AWS Credentials File (Alternative)

If you have AWS CLI configured on your host machine:

```bash
# Create mount for AWS credentials
docker run -v ~/.aws/credentials:/root/.aws/credentials:ro \
  -e AWS_REGION=us-east-1 \
  lambda_action_module:latest
```

### Using IAM Role (Production)

In production (ECS, EKS), attach an IAM role to your container and remove explicit credentials:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "lambda:InvokeFunction",
        "lambda:ListFunctions",
        "lambda:GetFunction",
        "lambda:GetFunctionConfiguration"
      ],
      "Resource": "arn:aws:lambda:*:*:function/*"
    }
  ]
}
```

## IAM Role Requirements

Your AWS credentials must have the following permissions:

### Minimum Permissions (Principle of Least Privilege)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "LambdaInvoke",
      "Effect": "Allow",
      "Action": "lambda:InvokeFunction",
      "Resource": "arn:aws:lambda:us-east-1:ACCOUNT_ID:function/waddlebot-*"
    }
  ]
}
```

### Full Permissions (Development)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "lambda:InvokeFunction",
        "lambda:ListFunctions",
        "lambda:GetFunction",
        "lambda:GetFunctionConfiguration",
        "lambda:ListAliases",
        "lambda:GetAlias",
        "lambda:PublishVersion"
      ],
      "Resource": "*"
    }
  ]
}
```

### Create IAM User (AWS Console)

1. Go to IAM > Users > Create User
2. Name: `waddlebot-lambda-invoker`
3. Select "Access key - Programmatic access"
4. Attach policy: `AWSLambdaFullAccess` (for development)
5. Copy Access Key ID and Secret Access Key
6. Use credentials in `.env` file

## PostgreSQL Database Setup

### Using Docker Compose (Automatic)

The provided `docker-compose.yml` includes a PostgreSQL service:

```yaml
postgres_lambda:
  image: postgres:15
  environment:
    POSTGRES_USER: waddlebot
    POSTGRES_PASSWORD: password
    POSTGRES_DB: waddlebot
  ports:
    - "5432:5432"
```

### Using External Database

Update `DATABASE_URL` in `.env`:

```env
DATABASE_URL=postgres://user:password@your-db-host:5432/your-database
```

### Create Database Tables Manually

```bash
# Connect to database
psql postgres://waddlebot:password@localhost:5432/waddlebot

# Create lambda_invocations table
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

CREATE INDEX idx_function_name ON lambda_invocations(function_name);
CREATE INDEX idx_invoked_at ON lambda_invocations(invoked_at);
CREATE INDEX idx_success ON lambda_invocations(success);
```

## Module Health Check

The health endpoint returns the module status and configuration:

```bash
curl -X GET http://localhost:8080/health

# With formatting
curl -X GET http://localhost:8080/health | jq '.'
```

Check these indicators:

- `status`: Should be `healthy`
- `database_configured`: Should be `true`
- `aws_configured`: Should be `true`
- `aws_region`: Should match your region

## First Invocation

### Step 1: Get Authentication Token

```bash
TOKEN=$(curl -s -X POST http://localhost:8080/api/v1/token \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "waddlebot",
    "client_secret": "test-secret"
  }' | jq -r '.token')

echo "Token: $TOKEN"
```

### Step 2: List Available Lambda Functions

```bash
curl -X GET http://localhost:8080/api/v1/functions \
  -H "Authorization: Bearer $TOKEN" | jq '.'
```

### Step 3: Invoke a Function

First, create a test Lambda function in AWS console (simple "Hello World" Python function).

Then invoke it:

```bash
curl -X POST http://localhost:8080/api/v1/invoke \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "function_name": "my-test-function",
    "payload": "{\"name\": \"WaddleBot\"}",
    "invocation_type": "RequestResponse"
  }' | jq '.'
```

Expected response:
```json
{
  "success": true,
  "status_code": 200,
  "payload": "{"message": "Hello from Lambda"}",
  "executed_version": "$LATEST",
  "log_result": "[logs from function]"
}
```

## Local Development Setup

### 1. Create Virtual Environment

```bash
python3.13 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Create .env file

```env
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_REGION=us-east-1
DATABASE_URL=postgres://waddlebot:password@localhost:5432/waddlebot
MODULE_SECRET_KEY=change-me-to-64-character-secret-key-xxxxxxxxxxxxxxxx
GRPC_PORT=50060
REST_PORT=8080
LOG_LEVEL=DEBUG
```

### 4. Run Tests

```bash
pytest tests/ -v
```

### 5. Start Module

```bash
python app.py
```

Expected output:
```
[2026-02-16 21:30:00] INFO root:app.py:100 - Starting lambda_action_module v1.0.0
[2026-02-16 21:30:00] INFO services.lambda_service:lambda_service.py:50 - Lambda service initialized
[2026-02-16 21:30:01] INFO app.py:250 - Starting gRPC server on 0.0.0.0:50060
[2026-02-16 21:30:01] INFO app.py:280 - Starting REST API server on 0.0.0.0:8080
```

## Troubleshooting Common Issues

### AWS Credentials Not Found

Error:
```
Configuration errors: ['AWS_ACCESS_KEY_ID is required', 'AWS_SECRET_ACCESS_KEY is required']
```

Solution:
1. Check `.env` file has credentials
2. Ensure credentials have Lambda permissions
3. Test with AWS CLI: `aws lambda list-functions`

### Database Connection Failed

Error:
```
Failed to connect to PostgreSQL: could not connect to server
```

Solution:
1. Ensure PostgreSQL is running: `docker-compose ps`
2. Check DATABASE_URL format in `.env`
3. Test connection: `psql <DATABASE_URL>`

### JWT Token Invalid

Error:
```
{"error": "Invalid token"}
```

Solution:
1. Generate new token
2. Ensure token hasn't expired (default: 1 hour)
3. Check MODULE_SECRET_KEY hasn't changed

### Lambda Function Not Found

Error:
```
{"success": false, "error": "Function not found"}
```

Solution:
1. Verify function exists in AWS console
2. Check function name spelling
3. Verify AWS region is correct
4. Ensure IAM credentials have lambda:InvokeFunction permission

## Stopping the Module

```bash
# Stop Docker containers
docker-compose down

# Stop and remove volumes
docker-compose down -v

# Stop local Python process
# Press Ctrl+C in terminal
```

## Environment Variables Summary

| Variable | Default | Purpose | Required |
|----------|---------|---------|----------|
| AWS_ACCESS_KEY_ID | - | AWS access key | Yes |
| AWS_SECRET_ACCESS_KEY | - | AWS secret key | Yes |
| AWS_REGION | us-east-1 | AWS region | No |
| DATABASE_URL | - | PostgreSQL connection | Yes |
| GRPC_PORT | 50060 | gRPC server port | No |
| REST_PORT | 8080 | REST API port | No |
| MODULE_SECRET_KEY | - | JWT signing key (64+ chars) | Yes |
| JWT_EXPIRATION_SECONDS | 3600 | Token lifetime | No |
| MAX_CONCURRENT_REQUESTS | 100 | Max concurrent calls | No |
| REQUEST_TIMEOUT | 30 | Request timeout (seconds) | No |
| LAMBDA_TIMEOUT | 300 | Lambda timeout (seconds) | No |
| LOG_LEVEL | INFO | Logging level | No |
| LOG_DIR | /var/log/waddlebotlog | Log file location | No |

See [CONFIGURATION.md](CONFIGURATION.md) for complete details.

## Next Steps

- [API Reference](API.md) - Learn all available endpoints
- [Architecture](ARCHITECTURE.md) - Understand system design
- [Testing Guide](TESTING.md) - Run tests with moto
- [Troubleshooting](TROUBLESHOOTING.md) - Common errors and solutions
