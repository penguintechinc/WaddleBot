# Engagement Module — Usage Guide

## Getting Started

The Engagement Module provides REST APIs for managing community polls and forms. This guide covers deployment, configuration, health checks, and common workflows.

---

## Prerequisites

- Docker 20.10+ (for containerized deployment) or Python 3.13+
- PostgreSQL 12+ database
- JWT secrets configured
- Network access to module port (default: 8091)

---

## Docker Deployment

### Quick Start

```bash
# Build the Docker image
docker build -t waddlebot/engagement:latest \
  /path/to/engagement_module

# Run with environment variables
docker run \
  --name engagement-module \
  -p 8091:8091 \
  -e MODULE_PORT=8091 \
  -e DATABASE_URL=postgres://user:pass@db-host:5432/waddlebot \
  -e JWT_SECRET=your-secret-key-here \
  -e MODULE_SECRET_KEY=your-module-secret-key \
  -e ENVIRONMENT=development \
  waddlebot/engagement:latest
```

### Docker Compose Setup

```yaml
version: '3.8'
services:
  engagement:
    image: waddlebot/engagement:latest
    ports:
      - "8091:8091"
      - "50061:50061"
    environment:
      MODULE_PORT: 8091
      DATABASE_URL: postgresql://waddlebot:password@postgres:5432/waddlebot
      JWT_SECRET: your-jwt-secret-key
      MODULE_SECRET_KEY: your-module-secret-key
      LOG_LEVEL: INFO
      ENVIRONMENT: development
    depends_on:
      - postgres
    networks:
      - waddlebot-network

  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: waddlebot
      POSTGRES_USER: waddlebot
      POSTGRES_PASSWORD: password
    volumes:
      - postgres-data:/var/lib/postgresql/data
    networks:
      - waddlebot-network

networks:
  waddlebot-network:

volumes:
  postgres-data:
```

### Running with Custom Configuration

```bash
# Create .env file
cat > .env << EOF
MODULE_PORT=8091
DATABASE_URL=postgresql://waddlebot:password@localhost:5432/waddlebot
JWT_SECRET=your-jwt-secret-key
MODULE_SECRET_KEY=your-module-secret-key
LOG_LEVEL=DEBUG
ENVIRONMENT=development
EOF

# Run container with env file
docker run \
  --name engagement-module \
  -p 8091:8091 \
  --env-file .env \
  waddlebot/engagement:latest
```

---

## Health Check

### HTTP Health Check

```bash
curl -X GET http://localhost:8091/health
```

**Success Response (200)**:
```json
{
  "status": "healthy",
  "module": "engagement_module",
  "version": "1.0.0",
  "timestamp": "2026-02-16T10:30:45.123456"
}
```

**Failure Response (503)**:
```json
{
  "status": "unhealthy",
  "error": "Connection refused"
}
```

### Docker Health Check

```bash
# Add healthcheck to docker run
docker run \
  --health-cmd='curl -f http://localhost:8091/health || exit 1' \
  --health-interval=10s \
  --health-timeout=5s \
  --health-retries=3 \
  waddlebot/engagement:latest
```

### Kubernetes Health Check

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: engagement-module
spec:
  containers:
  - name: engagement
    image: waddlebot/engagement:latest
    ports:
    - containerPort: 8091
      name: http
    livenessProbe:
      httpGet:
        path: /health
        port: 8091
      initialDelaySeconds: 10
      periodSeconds: 10
    readinessProbe:
      httpGet:
        path: /health
        port: 8091
      initialDelaySeconds: 5
      periodSeconds: 5
```

---

## Tracking Engagement Events

### Creating a Poll

```bash
curl -X POST http://localhost:8091/api/v1/polls \
  -H "Authorization: Bearer <JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "community_id": 1,
    "title": "What is your favorite programming language?",
    "description": "Vote for your preferred language",
    "options": ["Python", "JavaScript", "Go", "Rust"],
    "view_visibility": "community",
    "submit_visibility": "community",
    "allow_multiple_choices": false,
    "expires_at": "2026-02-28T23:59:59Z"
  }'
```

**Response (201)**:
```json
{
  "success": true,
  "poll": {
    "id": 42,
    "community_id": 1,
    "title": "What is your favorite programming language?",
    "description": "Vote for your preferred language",
    "options": [
      {"id": 1, "text": "Python"},
      {"id": 2, "text": "JavaScript"},
      {"id": 3, "text": "Go"},
      {"id": 4, "text": "Rust"}
    ],
    "view_visibility": "community",
    "submit_visibility": "community",
    "allow_multiple_choices": false,
    "max_choices": 1,
    "expires_at": "2026-02-28T23:59:59",
    "is_active": true,
    "created_at": "2026-02-16T10:30:45"
  }
}
```

### Voting on a Poll

```bash
curl -X POST http://localhost:8091/api/v1/polls/42/vote \
  -H "Authorization: Bearer <JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "option_ids": [2]
  }'
```

**Response (200)**:
```json
{
  "success": true,
  "message": "Vote recorded"
}
```

### Creating a Form

```bash
curl -X POST http://localhost:8091/api/v1/forms \
  -H "Authorization: Bearer <JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "community_id": 1,
    "title": "Community Feedback Survey",
    "description": "Help us improve our community",
    "fields": [
      {
        "type": "text",
        "label": "Name",
        "placeholder": "Your full name",
        "required": true
      },
      {
        "type": "email",
        "label": "Email",
        "required": true
      },
      {
        "type": "textarea",
        "label": "Feedback",
        "placeholder": "Tell us what you think",
        "required": true
      },
      {
        "type": "select",
        "label": "Overall satisfaction",
        "options": ["Very satisfied", "Satisfied", "Neutral", "Dissatisfied"],
        "required": false
      }
    ],
    "view_visibility": "community",
    "submit_visibility": "community",
    "allow_anonymous": false,
    "submit_once_per_user": true
  }'
```

**Response (201)**:
```json
{
  "success": true,
  "form": {
    "id": 12,
    "community_id": 1,
    "title": "Community Feedback Survey",
    "description": "Help us improve our community",
    "view_visibility": "community",
    "submit_visibility": "community",
    "allow_anonymous": false,
    "submit_once_per_user": true,
    "is_active": true,
    "created_at": "2026-02-16T10:30:45"
  }
}
```

### Submitting a Form

```bash
curl -X POST http://localhost:8091/api/v1/forms/12/submit \
  -H "Authorization: Bearer <JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "values": {
      "1": "Jane Doe",
      "2": "jane@example.com",
      "3": "Great community! Keep up the good work.",
      "4": "Very satisfied"
    }
  }'
```

**Response (201)**:
```json
{
  "success": true,
  "submission_id": 95
}
```

---

## Retrieving Engagement Metrics

### Get Poll Details with Results

```bash
curl -X GET http://localhost:8091/api/v1/polls/42 \
  -H "Authorization: Bearer <JWT_TOKEN>"
```

**Response (200)**:
```json
{
  "success": true,
  "poll": {
    "id": 42,
    "community_id": 1,
    "title": "What is your favorite programming language?",
    "options": [
      {"id": 1, "text": "Python"},
      {"id": 2, "text": "JavaScript"},
      {"id": 3, "text": "Go"},
      {"id": 4, "text": "Rust"}
    ],
    "vote_counts": {
      "1": 15,
      "2": 23,
      "3": 8,
      "4": 12
    ],
    "view_visibility": "community",
    "submit_visibility": "community",
    "is_active": true,
    "created_at": "2026-02-16T10:30:45"
  }
}
```

### List All Polls for a Community

```bash
curl -X GET http://localhost:8091/api/v1/polls/community/1 \
  -H "Authorization: Bearer <JWT_TOKEN>"
```

**Response (200)**:
```json
{
  "success": true,
  "count": 3,
  "polls": [
    {
      "id": 42,
      "title": "What is your favorite programming language?",
      "community_id": 1,
      "created_at": "2026-02-16T10:30:45"
    },
    {
      "id": 41,
      "title": "Should we add a new feature?",
      "community_id": 1,
      "created_at": "2026-02-15T08:15:20"
    }
  ]
}
```

### Get Form Submissions

```bash
curl -X GET http://localhost:8091/api/v1/forms/12/submissions \
  -H "Authorization: Bearer <JWT_TOKEN>"
```

**Response (200)**:
```json
{
  "success": true,
  "count": 42,
  "submissions": [
    {
      "id": 95,
      "user_id": 128,
      "submitted_at": "2026-02-16T14:22:15",
      "values": {
        "1": "Jane Doe",
        "2": "jane@example.com",
        "3": "Great community! Keep up the good work.",
        "4": "Very satisfied"
      }
    },
    {
      "id": 94,
      "user_id": 127,
      "submitted_at": "2026-02-16T12:08:43",
      "values": {
        "1": "John Smith",
        "2": "john@example.com",
        "3": "Good but could improve moderation",
        "4": "Satisfied"
      }
    }
  ]
}
```

### List All Forms for a Community

```bash
curl -X GET http://localhost:8091/api/v1/forms/community/1 \
  -H "Authorization: Bearer <JWT_TOKEN>"
```

**Response (200)**:
```json
{
  "success": true,
  "count": 5,
  "forms": [
    {
      "id": 12,
      "title": "Community Feedback Survey",
      "community_id": 1,
      "created_at": "2026-02-16T10:30:45"
    }
  ]
}
```

---

## Logging and Debugging

### View Module Logs

```bash
# Docker logs
docker logs engagement-module

# With tail (last 100 lines)
docker logs --tail 100 engagement-module

# Follow logs in real-time
docker logs -f engagement-module
```

### Enable Debug Logging

Set `LOG_LEVEL=DEBUG` in environment:

```bash
docker run \
  -e LOG_LEVEL=DEBUG \
  waddlebot/engagement:latest
```

### Check Log Format

Logs follow this format:
```
[2026-02-16 10:30:45,123] INFO engagement_module:verify_jwt_token:187 Token verification successful
[2026-02-16 10:30:46,456] ERROR engagement_module:create_poll:328 Create poll failed: Invalid poll options
```

---

## Best Practices

1. **Always use HTTPS in production** for JWT token transmission
2. **Rotate JWT secrets regularly** to improve security
3. **Monitor health check endpoint** for early failure detection
4. **Use database backups** before major polls/forms to preserve results
5. **Set appropriate poll expiration times** to manage engagement metrics
6. **Test visibility controls** with different user roles before deployment
7. **Monitor module performance** for connection pool saturation

---

## Troubleshooting Quick Links

- Connection issues: See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) — Database Connection Errors
- JWT validation failures: See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) — JWT Token Validation
- Missing submissions: See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) — Missing Form Data
- Performance problems: See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) — Performance Optimization

---

## Next Steps

- Review [API.md](API.md) for complete endpoint documentation
- Check [CONFIGURATION.md](CONFIGURATION.md) for all environment options
- Run [TESTING.md](TESTING.md) test fixtures for local validation

**Company**: Penguin Tech Inc
**License**: Limited AGPL-3.0
**Last Updated**: 2026-02-16
