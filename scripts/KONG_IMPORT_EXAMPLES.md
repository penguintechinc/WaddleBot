# Kong Configuration Import - Usage Examples

This document provides practical examples of using the `import-kong-config.py` script.

## Prerequisites

First, install dependencies:

```bash
pip install requests pyyaml
```

Or in a Docker container:

```bash
docker run -it -v /path/to/waddles:/app -w /app python:3.13 bash
pip install requests pyyaml
python3 scripts/import-kong-config.py
```

## Basic Usage

### 1. Import with Default Settings

Assumes Kong is running at `http://localhost:8001` and config is at `config/kong/kong.yml`:

```bash
python3 scripts/import-kong-config.py
```

**Expected Output:**
```
[2025-12-08 10:30:45] INFO: Connected to Kong at http://localhost:8001
[2025-12-08 10:30:45] INFO: Loaded Kong configuration from config/kong/kong.yml
[2025-12-08 10:30:45] INFO: Format version: 3.0
[2025-12-08 10:30:45] INFO: Importing 15 service(s)...
[2025-12-08 10:30:46] INFO: ✓ Service created: hub-service (id: 2d98d0c4-1234-5678-abcd-ef0123456789)
[2025-12-08 10:30:46] INFO: ✓ Service created: router-service (id: 3e19e1d5-2345-6789-bcde-f01234567890)
...
[2025-12-08 10:30:50] INFO: ✓ Consumer created: service-account (id: abc123...)
[2025-12-08 10:30:50] INFO: ✓ Global plugin created: cors
[2025-12-08 10:30:50] INFO: ✓ Global plugin created: rate-limiting
...
[2025-12-08 10:30:52] INFO: ============================================================
[2025-12-08 10:30:52] INFO: IMPORT SUMMARY
[2025-12-08 10:30:52] INFO: ============================================================
[2025-12-08 10:30:52] INFO: Services: 15
[2025-12-08 10:30:52] INFO: Routes: 25
[2025-12-08 10:30:52] INFO: Consumers: 3
[2025-12-08 10:30:52] INFO: Plugins: 40
[2025-12-08 10:30:52] INFO: ============================================================
```

## Docker Compose Integration

### 2. Import Kong Config After docker-compose up

```bash
# Start Kong and dependencies
docker-compose up -d kong

# Wait for Kong to be ready
sleep 5

# Import configuration
docker-compose exec -T kong python3 /app/scripts/import-kong-config.py
```

Or with the Kong image:

```bash
docker run --network host \
  -v /path/to/waddles:/app \
  -w /app \
  kong:latest \
  bash -c "pip install requests pyyaml && \
    python3 scripts/import-kong-config.py --kong-url http://localhost:8001"
```

## Development Environment

### 3. Import with Debug Output

Enable verbose logging to see all API calls:

```bash
python3 scripts/import-kong-config.py --verbose
```

**Output shows:**
- Every service/route/consumer/plugin being created
- HTTP requests and responses
- Debug-level logging information

### 4. Custom Kong URL (Docker Network)

When Kong is running in Docker with custom network:

```bash
python3 scripts/import-kong-config.py --kong-url http://kong:8001
```

Or with Kubernetes:

```bash
python3 scripts/import-kong-config.py --kong-url http://kong-admin.kong.svc.cluster.local:8001
```

## Production Deployment

### 5. Production Environment with HTTPS

```bash
python3 scripts/import-kong-config.py \
  --kong-url https://kong.example.com:8443
```

Note: SSL certificates must be valid. For development:

```bash
python3 scripts/import-kong-config.py \
  --kong-url https://kong.dev.local:8443 \
  --no-verify-ssl
```

## Kubernetes Deployment

### 6. Import as Init Container

In a Kubernetes Job that runs before other services:

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: kong-config-import
spec:
  template:
    spec:
      containers:
      - name: import
        image: python:3.13
        workingDir: /app
        command:
        - sh
        - -c
        - |
          pip install -q requests pyyaml
          python3 scripts/import-kong-config.py \
            --kong-url http://kong-admin:8001 \
            --verbose
        volumeMounts:
        - name: waddlebot
          mountPath: /app
      volumes:
      - name: waddlebot
        configMap:
          name: waddlebot-config
      restartPolicy: Never
```

### 7. Import as Init Container in Pod

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: api-gateway
spec:
  initContainers:
  - name: init-kong-config
    image: python:3.13
    workingDir: /app
    command:
    - sh
    - -c
    - |
      pip install -q requests pyyaml
      python3 scripts/import-kong-config.py \
        --kong-url http://kong-admin:8001
    volumeMounts:
    - name: code
      mountPath: /app
  containers:
  - name: kong
    image: kong:latest
    ports:
    - containerPort: 8000
    - containerPort: 8443
    - containerPort: 8001
  volumes:
  - name: code
    configMap:
      name: waddlebot-code
```

## CI/CD Pipeline Integration

### 8. GitHub Actions Example

```yaml
name: Deploy Kong Configuration for Waddles

on:
  push:
    branches: [main]
    paths:
      - 'config/kong/kong.yml'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.13'
      
      - name: Install dependencies
        run: pip install requests pyyaml
      
      - name: Import Kong configuration
        env:
          KONG_URL: ${{ secrets.KONG_ADMIN_URL }}
        run: |
          python3 scripts/import-kong-config.py \
            --kong-url $KONG_URL \
            --verbose
```

### 9. GitLab CI Example

```yaml
deploy_kong_config:
  stage: deploy
  image: python:3.13
  script:
    - pip install requests pyyaml
    - python3 scripts/import-kong-config.py
        --kong-url $KONG_ADMIN_URL
        --verbose
  only:
    - main
  variables:
    KONG_ADMIN_URL: "https://kong.example.com:8443"
```

## Idempotent Operations

### 10. Safe Re-import

The script is idempotent and can be run multiple times safely:

```bash
# First run - creates all resources
python3 scripts/import-kong-config.py

# Second run - skips existing resources with warnings
python3 scripts/import-kong-config.py

# Output will show:
# [2025-12-08 10:35:00] WARNING: Resource already exists (409): /services/hub-service
# [2025-12-08 10:35:00] WARNING: Resource already exists (409): /services/hub-service/routes
```

This is safe because Kong Admin API returns 409 Conflict for existing resources, and the script treats this as expected behavior.

## Error Recovery

### 11. Import with Custom Config File

If you have a different configuration:

```bash
python3 scripts/import-kong-config.py --config-file custom-kong.yml
```

### 12. Partial Import (Manual Testing)

Create a minimal test config:

```yaml
# test-kong.yml
_format_version: "3.0"

services:
  - name: test-service
    url: http://test-backend:8000

routes:
  - name: test-route
    service: test-service
    paths:
      - /api/test
```

Then import:

```bash
python3 scripts/import-kong-config.py --config-file test-kong.yml
```

## Verification After Import

### 13. Verify Import Success

Check Kong Admin API for created resources:

```bash
# Check services
curl http://localhost:8001/services | jq '.data | length'

# Check routes
curl http://localhost:8001/routes | jq '.data | length'

# Check consumers
curl http://localhost:8001/consumers | jq '.data | length'

# Check plugins
curl http://localhost:8001/plugins | jq '.data | length'
```

### 14. Check Specific Resource

```bash
# Get hub-service details
curl http://localhost:8001/services/hub-service | jq .

# Get hub-user route
curl http://localhost:8001/routes/hub-user | jq .

# Get JWT plugin for hub-user route
curl http://localhost:8001/routes/hub-user/plugins | jq '.data[] | select(.name=="jwt")'
```

## Troubleshooting

### 15. Connection Issues

If Kong is unreachable:

```bash
# Test connectivity
curl http://localhost:8001/status

# If behind firewall/proxy, use verbose mode to debug
python3 scripts/import-kong-config.py --verbose

# Check if running in Docker
docker exec kong curl localhost:8001/status
```

### 16. YAML Validation

Validate config file before import:

```bash
python3 -c "import yaml; yaml.safe_load(open('config/kong/kong.yml'))" && \
  echo "YAML is valid"
```

### 17. Test with Small Config

Create a minimal config for testing:

```bash
cat > test-minimal.yml << 'EOF'
_format_version: "3.0"

services:
  - name: test-svc
    url: http://localhost:8000

routes:
  - name: test-route
    service: test-svc
    paths: [/test]
