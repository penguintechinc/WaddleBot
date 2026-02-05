# Health Check Standardization

## Overview

All Waddles containers now use a standardized Python-based health check system that doesn't require curl or any external dependencies.

## Standard Endpoints

Every Waddles module provides three standard endpoints:

### 1. `/health` - Basic Health Check
Simple health check endpoint that returns module name, version, and status.

**Response:**
```json
{
  "status": "healthy",
  "module": "module_name",
  "version": "1.0.0",
  "timestamp": "2025-12-08T14:49:58.899744"
}
```

### 2. `/healthz` - Kubernetes Probe
Kubernetes-compatible liveness/readiness probe endpoint with detailed checks.

**Response:**
```json
{
  "status": "healthy",
  "module": "module_name",
  "version": "1.0.0",
  "timestamp": "2025-12-08T14:49:58.899744",
  "checks": {
    "cpu": "ok",
    "memory": "ok"
  }
}
```

**Use in Kubernetes:**
```yaml
livenessProbe:
  httpGet:
    path: /healthz
    port: 8032
  initialDelaySeconds: 5
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /healthz
    port: 8032
  initialDelaySeconds: 3
  periodSeconds: 5
```

### 3. `/metrics` - Prometheus Metrics
Prometheus-compatible metrics endpoint in text exposition format.

**Metrics Provided:**
- `waddlebot_info` - Module information (gauge)
- `waddlebot_requests_total` - Total requests counter
- `waddlebot_requests_success_total` - Successful requests counter
- `waddlebot_requests_error_total` - Failed requests counter
- `waddlebot_request_duration_seconds` - Average request duration (gauge)
- `waddlebot_memory_bytes` - Memory usage (RSS and VMS)
- `waddlebot_cpu_percent` - CPU usage percentage
- `waddlebot_open_files` - Number of open file descriptors
- `waddlebot_threads` - Number of threads

**Response Format:**
```
# HELP waddlebot_info Module information
# TYPE waddlebot_info gauge
waddlebot_info{module="loyalty_interaction_module",version="1.0.0"} 1

# HELP waddlebot_requests_total Total number of requests
# TYPE waddlebot_requests_total counter
waddlebot_requests_total{module="loyalty_interaction_module"} 42

# HELP waddlebot_memory_bytes Memory usage in bytes
# TYPE waddlebot_memory_bytes gauge
waddlebot_memory_bytes{module="loyalty_interaction_module",type="rss"} 73379840
```

**Prometheus Scrape Config:**
```yaml
scrape_configs:
  - job_name: 'waddlebot'
    static_configs:
      - targets:
        - 'router:8000'
        - 'hub:8060'
        - 'loyalty-interaction:8032'
        - 'reputation:8021'
    metrics_path: '/metrics'
```

## Standardized Health Check Script

All containers include `/usr/local/bin/healthcheck.py` - a Python script that checks health endpoints without requiring curl.

### Usage

**In Container:**
```bash
python3 /usr/local/bin/healthcheck.py http://localhost:8032/healthz
```

**From Another Container:**
```bash
docker exec container-name python3 /usr/local/bin/healthcheck.py http://service:8032/healthz
```

**Exit Codes:**
- `0` - Health check passed
- `1` - Health check failed

### Script Features
- No external dependencies (uses urllib from stdlib)
- Configurable timeout (default: 5 seconds)
- Clear success/failure output
- Works with all three endpoint types

## Dockerfile Integration

### Standard Pattern

All Waddles Dockerfiles follow this pattern:

```dockerfile
FROM python:3.13-slim

WORKDIR /app

# Copy and install shared library
COPY libs/flask_core /app/libs/flask_core
RUN pip install --no-cache-dir /app/libs/flask_core

# Install module dependencies
COPY module/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY module /app/

# Copy standard healthcheck script
COPY scripts/healthcheck.py /usr/local/bin/healthcheck.py
RUN chmod 755 /usr/local/bin/healthcheck.py

# Create non-root user
RUN useradd -m -u 1000 waddlebot && chown -R waddlebot:waddlebot /app
USER waddlebot

EXPOSE 8032

# Health check (using /healthz for Kubernetes compatibility)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 /usr/local/bin/healthcheck.py http://localhost:8032/healthz

CMD ["hypercorn", "app:app", "--bind", "0.0.0.0:8032"]
```

### Key Points
1. **healthcheck.py copied before USER switch** - Ensures proper permissions
2. **chmod 755** - Makes script readable/executable by all users
3. **Uses /healthz endpoint** - Kubernetes-compatible standard
4. **Consistent intervals** - 30s interval, 10s timeout, 5s start period, 3 retries

## Testing

### Test Health Endpoint
```bash
docker exec container python3 /usr/local/bin/healthcheck.py http://localhost:PORT/health
```

### Test Healthz Endpoint
```bash
docker exec container python3 /usr/local/bin/healthcheck.py http://localhost:PORT/healthz
```

### Test Metrics Endpoint
```bash
docker exec container python3 -c "import urllib.request; print(urllib.request.urlopen('http://localhost:PORT/metrics').read().decode())"
```

### Verify Docker Health
```bash
docker ps --format "table {{.Names}}\t{{.Status}}"
```

## Implementation Details

### Flask Core Library

The `create_health_blueprint()` function in `libs/flask_core/flask_core/api_utils.py` provides all three endpoints:

```python
from flask_core import create_health_blueprint

# Create blueprint with all standard endpoints
health_bp = create_health_blueprint(MODULE_NAME, MODULE_VERSION)
app.register_blueprint(health_bp)
```

This automatically adds:
- `GET /health` - Basic health check
- `GET /healthz` - Kubernetes probe with system checks
- `GET /metrics` - Prometheus metrics

### Metrics Collection

The flask_core library automatically tracks:
- Request counts (total, success, error)
- Request durations
- Memory usage (RSS, VMS)
- CPU usage
- File descriptors
- Thread count

No additional code needed in modules.

## Migration

To update existing Dockerfiles to use the standardized health check:

```bash
# Run the bulk update script
bash scripts/update-dockerfiles-healthcheck.sh
```

This script:
1. Finds all Dockerfiles with urllib-based health checks
2. Adds the standardized healthcheck.py script
3. Updates HEALTHCHECK commands to use /healthz
4. Sets proper permissions

## Benefits

### 1. No External Dependencies
- Uses Python stdlib only (urllib, sys)
- No need for curl, wget, or other tools
- Smaller container images

### 2. Standardization
- Consistent health check behavior across all modules
- Same endpoints, same format, same metrics
- Easier to maintain and debug

### 3. Kubernetes Native
- `/healthz` follows Kubernetes conventions
- Ready for liveness and readiness probes
- No additional configuration needed

### 4. Observability
- Prometheus metrics out of the box
- Detailed system metrics (CPU, memory, threads)
- Request tracking and duration
- Easy integration with monitoring stacks

### 5. Security
- Runs as non-root user
- Minimal permissions required
- No shell commands or curl vulnerabilities

## Future Enhancements

Potential improvements:
1. Add dependency checks to /healthz (database, redis, etc.)
2. Custom metrics per module
3. Health check timeout configuration via environment variable
4. Alerting integration
5. Trace ID support for distributed tracing

---

**See Also:**
- [API Reference](api-reference.md)
- [Kubernetes Deployment](../k8s/README.md)
- [Development Rules](development-rules.md)
