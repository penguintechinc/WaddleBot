# Waddles Application Standards

This document defines local application standards that apply to Waddles development.

## Container Naming Convention

All Docker containers, Kubernetes resources, and internal DNS references MUST follow this naming pattern:

```
<category>-<name>
```

### Categories

| Category | Description | Examples |
|----------|-------------|----------|
| `trigger` | Modules that receive external events (webhooks, IRC, polling) | `trigger-twitch`, `trigger-discord`, `trigger-slack` |
| `action` | Modules that push actions to external platforms | `action-twitch`, `action-discord`, `action-slack` |
| `core` | Core platform services (router, identity, etc.) | `core-router`, `core-identity`, `core-labels` |
| `hub` | Admin/management portal components | `hub-api`, `hub-webui` |
| `infra` | Infrastructure services (databases, caches) | `infra-postgres`, `infra-redis`, `infra-minio` |
| `ai` | AI-related services | `ai-ollama`, `ai-researcher` |

### Examples

| Old Name | New Name | Description |
|----------|----------|-------------|
| `waddlebot-twitch` | `trigger-twitch` | Twitch event collector |
| `waddlebot-twitch-action` | `action-twitch` | Twitch action pusher |
| `waddlebot-router` | `core-router` | Central event router |
| `waddlebot-postgres` | `infra-postgres` | PostgreSQL primary |
| `waddlebot-postgres-replica` | `infra-postgres-replica` | PostgreSQL read replica |
| `waddlebot-hub` | `hub-api` | Hub module API |
| `waddlebot-ollama` | `ai-ollama` | Ollama AI inference |

### Docker Compose Service Names

Service names in `docker-compose.yml` should match the container naming convention:

```yaml
services:
  trigger-twitch:
    container_name: trigger-twitch
    # ...

  action-discord:
    container_name: action-discord
    # ...

  core-router:
    container_name: core-router
    # ...
```

### Internal DNS References

When services communicate internally, use the service name (which follows the same convention):

```python
# Correct
ROUTER_API_URL = "http://core-router:8000"
DATABASE_URL = "postgresql://user:pass@infra-postgres:5432/waddlebot"

# Incorrect (old style)
ROUTER_API_URL = "http://router:8000"
DATABASE_URL = "postgresql://user:pass@postgres:5432/waddlebot"
```

### Kubernetes Resource Names

Kubernetes Deployments, Services, ConfigMaps, etc. should use the same naming convention:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: trigger-twitch
  labels:
    app: trigger-twitch
    category: trigger
```

### Benefits

1. **Clear categorization**: Immediately understand a service's role from its name
2. **Consistent sorting**: Services group naturally in listings (all triggers together, etc.)
3. **Easy filtering**: `docker ps --filter "name=trigger-*"` shows all trigger modules
4. **Self-documenting**: New team members can understand architecture from names alone

### Migration Notes

When renaming containers:
1. Update `docker-compose.yml` service names and container_name
2. Update all internal DNS references (DATABASE_URL, API URLs, etc.)
3. Update Kubernetes manifests in `k8s/` directory
4. Update any hardcoded references in application code
5. Update monitoring/alerting configurations
