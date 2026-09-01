# YouTube Music Interaction Module - Usage Guide

## Getting Started

The YouTube Music Interaction Module is a microservice that runs as a separate Docker container. It communicates with the WaddleBot router service and provides YouTube Music integration capabilities.

## Prerequisites

Before running the module, ensure you have:

1. **Docker & Docker Compose** installed
2. **PostgreSQL 12+** running with WaddleBot database
3. **Python 3.12+** (for local development)
4. **YouTube OAuth 2.0 Credentials** (Client ID and Client Secret)
5. **Redis** (optional, for credential refresh notifications)

## Installation & Setup

### Docker Compose (Recommended)

The module is already defined in the main `docker-compose.yml` and `docker-compose.dev.yml`:

```yaml
youtube-music-interaction:
  build:
    context: .
    dockerfile: action/interactive/youtube_music_interaction_module/Dockerfile
  ports:
    - "8025:8025"  # REST API
    - "50054:50054"  # gRPC
  environment:
    - MODULE_PORT=8025
    - DATABASE_URL=postgresql://waddlebot:password@postgres:5432/waddlebot
    - CORE_API_URL=http://router-service:8000
    - ROUTER_API_URL=http://router-service:8000/api/v1/router
    - LOG_LEVEL=INFO
    - SECRET_KEY=${SECRET_KEY}
    - REDIS_URL=${REDIS_URL}
    - YOUTUBE_CLIENT_ID=${YOUTUBE_CLIENT_ID}
    - YOUTUBE_CLIENT_SECRET=${YOUTUBE_CLIENT_SECRET}
  depends_on:
    - postgres
    - router-service
  networks:
    - waddlebot-network
```

### Local Development Setup

1. **Install Dependencies**:
```bash
pip install -r action/interactive/youtube_music_interaction_module/requirements.txt
pip install -r libs/flask_core/requirements.txt
```

2. **Set Environment Variables** (create `.env` file):
```bash
cat > .env << 'ENVEOF'
MODULE_PORT=8025
DATABASE_URL=postgresql://waddlebot:password@localhost:5432/waddlebot
CORE_API_URL=http://localhost:8000
ROUTER_API_URL=http://localhost:8000/api/v1/router
LOG_LEVEL=DEBUG
SECRET_KEY=dev-key-change-in-production
YOUTUBE_CLIENT_ID=your_client_id_here
YOUTUBE_CLIENT_SECRET=your_client_secret_here
REDIS_URL=redis://localhost:6379/0
ENVEOF
```

3. **Start the Module**:
```bash
cd action/interactive/youtube_music_interaction_module
hypercorn app:app --bind 0.0.0.0:8025 --reload
```

## Docker Setup

### Building the Image

```bash
docker build -f action/interactive/youtube_music_interaction_module/Dockerfile \
  -t waddlebot/youtube-music-interaction:latest .
```

### Running with Docker

```bash
docker run -it \
  -p 8025:8025 \
  -p 50054:50054 \
  -e MODULE_PORT=8025 \
  -e DATABASE_URL=postgresql://waddlebot:password@postgres:5432/waddlebot \
  -e CORE_API_URL=http://router-service:8000 \
  -e LOG_LEVEL=INFO \
  --network waddlebot-network \
  waddlebot/youtube-music-interaction:latest
```

### Docker Compose Quick Start

```bash
# Start all services including the YouTube Music module
docker-compose -f docker-compose.yml up -d youtube-music-interaction

# View logs
docker-compose logs -f youtube-music-interaction

# Stop the service
docker-compose down youtube-music-interaction
```

## OAuth 2.0 Setup

The module uses OAuth 2.0 to authenticate users with YouTube Music. Follow these steps:

### Step 1: Create OAuth 2.0 Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the **YouTube Music API** (if available) or **YouTube Data API v3**
4. Go to **Credentials** > **Create Credentials** > **OAuth 2.0 Client ID**
5. Choose **Web Application**
6. Add authorized redirect URIs:
   - Development: `http://localhost:8025/oauth/callback`
   - Production: `https://your-domain.com/oauth/callback`
7. Copy the **Client ID** and **Client Secret**

### Step 2: Store Credentials

Set these environment variables:
```bash
export YOUTUBE_CLIENT_ID="your-client-id-here"
export YOUTUBE_CLIENT_SECRET="your-client-secret-here"
```

Or store in `.env` file:
```env
YOUTUBE_CLIENT_ID=your-client-id-here
YOUTUBE_CLIENT_SECRET=your-client-secret-here
```

### Step 3: Configure Redirect URI

Ensure the OAuth callback endpoint is configured in the application.

## Health Checks

The module provides multiple health check endpoints for monitoring and orchestration:

### Application Health Endpoint

```bash
curl http://localhost:8025/health
```

Response:
```json
{
  "status": "healthy",
  "module": "youtube_music_interaction_module",
  "version": "2.0.0",
  "timestamp": "2026-02-16T12:34:56Z"
}
```

### Kubernetes Readiness/Liveness Probe

```bash
curl http://localhost:8025/healthz
```

Response (when healthy):
```json
{
  "status": "healthy",
  "module": "youtube_music_interaction_module",
  "version": "2.0.0",
  "checks": {
    "database": "connected",
    "redis": "connected"
  }
}
```

Or when degraded (503):
```json
{
  "status": "degraded",
  "module": "youtube_music_interaction_module",
  "version": "2.0.0",
  "checks": {
    "database": "connected",
    "redis": "disconnected"
  }
}
```

### Configure in Kubernetes

Add to your Deployment spec:
```yaml
livenessProbe:
  httpGet:
    path: /healthz
    port: 8025
  initialDelaySeconds: 10
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /healthz
    port: 8025
  initialDelaySeconds: 5
  periodSeconds: 5
```

## Metrics & Monitoring

The module exposes Prometheus metrics at `/metrics`:

```bash
curl http://localhost:8025/metrics
```

Key metrics:
- `waddlebot_info`: Module information
- `waddlebot_requests_total`: Total HTTP requests
- `waddlebot_request_duration_seconds`: Request latency
- `youtube_music_interaction_module_*`: Module-specific metrics

## Common Workflows

### Verify Module is Running

```bash
# Check if service responds
curl -v http://localhost:8025/health

# Check metrics
curl http://localhost:8025/metrics | grep youtube_music

# View container logs
docker-compose logs youtube-music-interaction
```

### Test API Endpoints

The module includes a comprehensive test script:

```bash
# Run all tests
./action/interactive/youtube_music_interaction_module/test-api.sh

# Test specific base URL
./action/interactive/youtube_music_interaction_module/test-api.sh --url http://localhost:8025

# Help
./action/interactive/youtube_music_interaction_module/test-api.sh --help
```

### Update OAuth Credentials

1. Update environment variables or `.env` file
2. Restart the container:
```bash
docker-compose restart youtube-music-interaction
```

3. Verify with health check:
```bash
curl http://localhost:8025/health
```

### View Logs

**Docker Compose:**
```bash
# Real-time logs
docker-compose logs -f youtube-music-interaction

# Last 100 lines
docker-compose logs --tail=100 youtube-music-interaction

# Specific time range
docker-compose logs --since 2026-02-16T12:00:00 youtube-music-interaction
```

**Kubernetes:**
```bash
# Get logs
kubectl logs -n waddlebot deployment/youtube-music-interaction

# Real-time logs
kubectl logs -n waddlebot -f deployment/youtube-music-interaction

# Previous pod logs
kubectl logs -n waddlebot deployment/youtube-music-interaction --previous
```

### Check Database Connection

The module automatically initializes the database connection on startup. To verify:

```bash
# Check logs for startup messages
docker-compose logs youtube-music-interaction | grep "database"

# Connect to PostgreSQL directly
psql postgresql://waddlebot:password@localhost:5432/waddlebot

# Verify platform_integrations table
SELECT * FROM platform_integrations WHERE platform = 'youtube';
```

## Troubleshooting

### Port Already in Use

If port 8025 is already in use:

```bash
# Find process using port
lsof -i :8025

# Change port in environment
export MODULE_PORT=8026
```

### Database Connection Failures

Check your `DATABASE_URL`:
```bash
# Verify connection string format
psql "postgresql://waddlebot:password@localhost:5432/waddlebot"

# Check PostgreSQL is running
docker ps | grep postgres
```

### OAuth Credential Errors

Ensure credentials are set:
```bash
# Check environment variables
env | grep YOUTUBE_

# Check inside container
docker-compose exec youtube-music-interaction env | grep YOUTUBE_
```

For detailed troubleshooting, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

---

**Last Updated**: 2026-02-16
