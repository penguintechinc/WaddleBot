# Credential Manager - Quick Start Guide

Fast-track guide to get the credential manager running locally or in production.

## Local Development (5 minutes)

### 1. Prerequisites

```bash
# Python 3.13+ and pip
python3 --version

# PostgreSQL running with waddlebot database
psql -U postgres -d waddlebot -c "SELECT 1"

# Redis running
redis-cli ping
```

### 2. Install Dependencies

```bash
cd core/credential_manager_module
pip install -r requirements.txt
```

### 3. Set Environment Variables

```bash
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/waddlebot"
export REDIS_URL="redis://localhost:6379/0"
export LOG_LEVEL="DEBUG"
```

### 4. Run Service

```bash
python -m quart --app app:app run --host 0.0.0.0 --port 8095
```

### 5. Test Service

```bash
# Health check
curl http://localhost:8095/health

# Credential status
curl http://localhost:8095/api/v1/credentials/status

# Force refresh
curl -X POST http://localhost:8095/api/v1/credentials/refresh-now
```

## Docker Quick Start (3 minutes)

### Build

```bash
docker build -f core/credential_manager_module/Dockerfile -t credential-manager .
```

### Run

```bash
docker run -it --rm \
  -e DATABASE_URL="postgresql://postgres:postgres@host.docker.internal:5432/waddlebot" \
  -e REDIS_URL="redis://host.docker.internal:6379/0" \
  -p 8095:8095 \
  credential-manager
```

### With Docker Compose

```bash
# Add to docker-compose.yml, then:
docker-compose up credential-manager
```

## Configuration Quick Reference

| Variable | Default | Notes |
|----------|---------|-------|
| DATABASE_URL | (required) | PostgreSQL connection string |
| REDIS_URL | redis://localhost:6379/0 | Redis connection |
| TOKEN_REFRESH_BUFFER | 300 | Refresh 5 min before expiry |
| POLL_INTERVAL | 60 | Check every 60 seconds |
| MODULE_PORT | 8095 | REST API port |
| LOG_LEVEL | INFO | DEBUG, INFO, WARNING, ERROR |

## API Quick Reference

```bash
# Health check (use in probes)
curl http://localhost:8095/health

# Get credential status
curl http://localhost:8095/api/v1/credentials/status | jq .

# Force refresh now
curl -X POST http://localhost:8095/api/v1/credentials/refresh-now
```

## Troubleshooting

### Service won't start

**Check database connection:**
```bash
psql postgresql://user:pass@localhost:5432/waddlebot -c "SELECT 1"
```

**Check Redis connection:**
```bash
redis-cli -u redis://localhost:6379/0 ping
```

### Tokens not refreshing

**Check if service is running:**
```bash
curl http://localhost:8095/health
```

**Check if credentials exist:**
```sql
SELECT COUNT(*) FROM platform_integrations
WHERE is_active=true AND expires_at IS NOT NULL;
```

**Check logs:**
```bash
docker logs credential-manager  # Docker
```

### Connection pool exhausted

Reduce:
1. POLL_INTERVAL (less frequent checks)
2. Concurrent connections from other services

## File Structure

```
core/credential_manager_module/
├── __init__.py              # Module exports
├── config.py                # Configuration
├── app.py                   # REST API
├── requirements.txt         # Dependencies
├── Dockerfile               # Container image
├── services/
│   ├── __init__.py          # Service exports
│   ├── oauth_handlers.py    # Platform-specific OAuth
│   └── refresh_service.py   # Token refresh logic
└── README.md, API.md, DEPLOYMENT.md  # Documentation
```

## Next Steps

1. **See [README.md](README.md)** for architecture overview
2. **See [DEPLOYMENT.md](DEPLOYMENT.md)** for production setup
3. **See [API.md](API.md)** for endpoint reference
4. **Check [services/oauth_handlers.py](services/oauth_handlers.py)** for supported platforms

## Common Tasks

### Monitor in Real-Time

```bash
watch -n 5 'curl -s http://localhost:8095/health | jq .'
```

### Check Refresh Stats

```bash
curl http://localhost:8095/api/v1/credentials/status | \
  jq '.stats[] | {platform, total, expiring_soon, expired}'
```

### View Logs with Filtering

```bash
docker logs -f credential-manager | grep "ERROR\|FAILED"
```

### Test Specific Platform Handler

```python
from services.oauth_handlers import get_handler

handler = get_handler("twitch")
print(f"Twitch handler: {handler.TOKEN_URL}")
```

## Performance Tuning

### For High Volume (1000+ credentials)

```bash
# Increase polling frequency
export POLL_INTERVAL=30

# Increase database pool
# (modify code: min_size=10, max_size=20)
```

### For Low Latency (real-time refresh)

```bash
# Decrease refresh buffer
export TOKEN_REFRESH_BUFFER=60

# Decrease poll interval
export POLL_INTERVAL=10
```

### For Low Resources

```bash
# Increase poll interval
export POLL_INTERVAL=300

# Increase refresh buffer
export TOKEN_REFRESH_BUFFER=600
```

## Production Checklist

- [ ] Database user created and granted permissions
- [ ] Redis cluster configured and replicated
- [ ] Environment variables set securely (Kubernetes Secrets, etc.)
- [ ] Health check configured (liveness/readiness probes)
- [ ] Logging configured (ELK, CloudWatch, etc.)
- [ ] Monitoring configured (Prometheus, Datadog, etc.)
- [ ] Alerting configured (PagerDuty, Slack, etc.)
- [ ] Backup strategy for database
- [ ] Disaster recovery plan

## Support

- **Issues**: Check troubleshooting in [README.md](README.md)
- **Deployment**: See [DEPLOYMENT.md](DEPLOYMENT.md)
- **API Reference**: See [API.md](API.md)
- **Architecture**: See [docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md)

## Key Files to Know

| File | When to Read |
|------|--------------|
| README.md | Overview of service |
| DEPLOYMENT.md | Setting up in production |
| API.md | Understanding REST endpoints |
| config.py | Configuration options |
| services/oauth_handlers.py | Adding new OAuth provider |
| services/refresh_service.py | Understanding token refresh logic |

---

**Version**: 1.0.0
**Last Updated**: 2025-02-05
**Status**: Production Ready
