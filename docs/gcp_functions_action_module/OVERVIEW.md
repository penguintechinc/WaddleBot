# GCP Functions Action Module - Overview

## Purpose

The GCP Functions Action Module is a stateless, clusterable microservice that receives task requests from the Waddlebot router via gRPC and invokes Google Cloud Platform (GCP) Cloud Functions. It provides both gRPC and REST interfaces for executing serverless functions, managing invocations, and monitoring function execution.

**Module Name:** gcp_functions_action_module  
**Language:** Python 3.13  
**gRPC Port:** 50061  
**REST Port:** 8081  
**Status:** Production-Ready

## Core Capabilities

The module enables:

- **Function Invocation:** Execute Cloud Functions with JSON payloads
- **Batch Operations:** Invoke multiple functions concurrently
- **HTTP Functions:** Direct HTTP invocation with custom headers
- **Function Management:** List and describe Cloud Functions
- **Execution Monitoring:** Track execution time and results
- **Activity Logging:** Log all invocations to database
- **Service Account Auth:** Automatic GCP credential handling
- **JWT Authentication:** Secure REST API with token-based auth
- **Multi-Protocol Support:** Both gRPC and REST interfaces
- **High Availability:** Horizontal scaling with stateless design
- **Error Handling:** Automatic retries with exponential backoff

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                GCP Functions Action Module                   │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌────────────────┐              ┌────────────────────┐    │
│  │  gRPC Server   │              │   REST API Server   │    │
│  │  (Port 50061)  │              │   (Port 8081)      │    │
│  └────────┬───────┘              └────────┬───────────┘    │
│           │                                │                 │
│           └────────────┬───────────────────┘                 │
│                        │                                      │
│          ┌──────────────▼──────────────┐                     │
│          │  GCP Functions Service      │                     │
│          │  - Cloud Functions API      │                     │
│          │  - Service account auth     │                     │
│          │  - ID token management      │                     │
│          └──────────────┬──────────────┘                     │
│                        │                                      │
│          ┌─────────────┼─────────────┐                       │
│          │             │             │                       │
│          ▼             ▼             ▼                       │
│      ┌────────┐  ┌────────┐  ┌────────────┐                │
│      │ PyDAL  │  │ aiohttp│  │  Logging   │                │
│      │Database│  │Client  │  │  System    │                │
│      └────────┘  └────────┘  └────────────┘                │
│                                                               │
└─────────────────────────────────────────────────────────────┘
         │                          │
         ▼                          ▼
    ┌──────────┐            ┌──────────────────┐
    │PostgreSQL│            │ GCP Cloud        │
    │Database  │            │ Functions API    │
    └──────────┘            └──────────────────┘
```

## Documentation Index

| Document | Purpose | Audience |
|----------|---------|----------|
| USAGE.md | Getting started, GCP setup, first invocations | Developers, DevOps |
| API.md | Complete REST API endpoint reference | API Consumers |
| ARCHITECTURE.md | System design, GCP integration, auth flow | Architects, Contributors |
| CONFIGURATION.md | Environment variables, GCP credentials | DevOps, Operators |
| TESTING.md | Unit/integration tests, mock GCP client | QA Engineers |
| TROUBLESHOOTING.md | Common errors, IAM issues, solutions | Support Engineers |
| RELEASE_NOTES.md | Version history and release information | All |

## Quick Reference

### Health Check
```bash
curl http://localhost:8081/health
```

### Generate Authentication Token
```bash
curl -X POST http://localhost:8081/api/v1/auth/token   -H "Content-Type: application/json"   -d '{"api_key":"your_api_key","service":"my_service"}'
```

### Invoke Cloud Function
```bash
curl -X POST http://localhost:8081/api/v1/functions/invoke   -H "Content-Type: application/json"   -H "Authorization: Bearer YOUR_JWT_TOKEN"   -d '{
    "project": "my-project",
    "region": "us-central1",
    "function_name": "my-function",
    "payload": {"message": "Hello Cloud Function"}
  }'
```

### Invoke HTTP Function
```bash
curl -X POST http://localhost:8081/api/v1/functions/invoke-http   -H "Content-Type: application/json"   -H "Authorization: Bearer YOUR_JWT_TOKEN"   -d '{
    "url": "https://region-project.cloudfunctions.net/function-name",
    "payload": {"data": "test"},
    "method": "POST"
  }'
```

### Batch Invoke Functions
```bash
curl -X POST http://localhost:8081/api/v1/functions/batch   -H "Content-Type: application/json"   -H "Authorization: Bearer YOUR_JWT_TOKEN"   -d '{
    "invocations": [
      {
        "function_name": "function-1",
        "payload": {"id": 1}
      },
      {
        "function_name": "function-2",
        "payload": {"id": 2}
      }
    ]
  }'
```

### List Cloud Functions
```bash
curl "http://localhost:8081/api/v1/functions/list?project=my-project&region=us-central1"   -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Key Features by Category

### Function Invocation
- Synchronous Cloud Function execution
- HTTP-triggered function invocation
- Custom payload with JSON
- Custom request headers
- Configurable timeouts

### Batch Operations
- Concurrent invocation of multiple functions
- Parallel execution
- Individual result tracking
- Success/failure counts
- Configurable batch size (max 100)

### Function Management
- List all Cloud Functions in project
- Get function details and metadata
- Region-based filtering
- Display function endpoints

### Execution Tracking
- Unique execution IDs
- Execution time tracking
- Response capture and logging
- Error message logging
- Database activity audit trail

### Integration
- gRPC interface for processor communication
- REST API for third-party integrations
- JWT authentication for all API access
- Database logging of all invocations

## Dependencies

**Python Libraries:**
- quart - Async ASGI web framework
- grpc - gRPC framework
- pydal - Database abstraction layer
- aiohttp - Async HTTP client
- google-auth - GCP authentication
- google-cloud-functions - GCP Cloud Functions client
- pyjwt - JWT token generation/verification
- hypercorn - ASGI server

**External Services:**
- PostgreSQL (or compatible database)
- GCP Cloud Functions enabled
- GCP Service Account with appropriate permissions

## Performance Characteristics

- **Max Workers:** 20 concurrent executors
- **Request Timeout:** 30 seconds
- **Function Timeout:** 60 seconds per invocation
- **Max Batch Size:** 100 functions per request
- **Max Retries:** 3 with exponential backoff
- **Retry Delay:** 1 second initial

## GCP Requirements

**GCP Project Setup:**
- Cloud Functions API enabled
- Service Account with Cloud Functions Invoker role
- Valid service account JSON key or credentials

**Required Permissions:**
```
cloudfunctions.functions.call
cloudfunctions.functions.list
cloudfunctions.functions.get
```

## Source Code Location

All source code is located in:
```
/home/penguin/code/waddlebot/action/pushing/gcp_functions_action_module/
```

Key files:
- app.py - Main application with REST endpoints
- config.py - Configuration management
- services/gcp_functions_service.py - GCP Cloud Functions operations
- services/auth_service.py - JWT authentication
- services/grpc_handler.py - gRPC service implementation
- grpc_proto/ - Protocol buffer definitions

## Deployment

The module runs as a standalone Docker container with horizontal scaling support. See USAGE.md for Docker Compose setup and CONFIGURATION.md for credential setup.

Default deployment:
```bash
docker-compose up -d
```

The module automatically connects to PostgreSQL and GCP Cloud Functions API. See CONFIGURATION.md for GCP credentials.

## Security

- **Authentication:** JWT tokens with configurable expiration
- **Credentials:** Support for service account JSON keys
- **ID Tokens:** Automatic ID token generation for function auth
- **Input Validation:** All function parameters validated
- **Logging:** All invocations logged for audit trail
- **Error Handling:** Secure error messages without sensitive data

## GCP Integration

The module uses Google Cloud client libraries for:
- Service account authentication
- ID token generation
- Cloud Functions API v2 calls
- Automatic credential discovery

Supports both:
- Explicit credentials (JSON key file)
- Default credentials (GCE/GKE environment)

## Version Information

**Current Version:** 1.0.0  
**Released:** 2025-01-27  
**Last Updated:** 2026-02-16

## Testing

Includes mock GCP client for isolated testing without actual Cloud Function invocations. See TESTING.md for test patterns and setup.
