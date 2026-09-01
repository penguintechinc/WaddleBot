# Kong Configuration Import Script

This script imports the declarative Kong configuration from `config/kong/kong.yml` into the Kong Admin API.

## Overview

The `import-kong-config.py` script automates importing Kong configuration by:
1. Reading the YAML configuration file
2. Creating **services** (backend microservices)
3. Creating **routes** (API path mappings to services)
4. Creating **consumers** (API consumers for auth)
5. Creating **plugins** (global, service-level, and route-level)

## Prerequisites

Install required Python packages:

```bash
pip install requests pyyaml
```

Or using requirements file (if available):

```bash
pip install -r requirements.txt
```

## Usage

### Basic usage (defaults)

```bash
python3 scripts/import-kong-config.py
```

This assumes:
- Kong Admin API is running at `http://localhost:8001`
- Configuration file is at `config/kong/kong.yml`

### Custom Kong Admin URL

```bash
python3 scripts/import-kong-config.py --kong-url http://kong-admin:8001
```

### Custom configuration file

```bash
python3 scripts/import-kong-config.py --config-file /path/to/kong.yml
```

### Enable debug logging

```bash
python3 scripts/import-kong-config.py --verbose
```

### Disable SSL certificate verification

```bash
python3 scripts/import-kong-config.py --no-verify-ssl
```

### Full example

```bash
python3 scripts/import-kong-config.py \
  --kong-url https://kong-admin.example.com:8443 \
  --config-file config/kong/kong.yml \
  --verbose
```

## Command-line Options

| Option | Default | Description |
|--------|---------|-------------|
| `--config-file` | `config/kong/kong.yml` | Path to Kong YAML configuration file |
| `--kong-url` | `http://localhost:8001` | Kong Admin API base URL |
| `--no-verify-ssl` | (disabled) | Disable SSL certificate verification |
| `--verbose`, `-v` | (disabled) | Enable debug-level logging |
| `-h`, `--help` | - | Show help message and exit |

## Configuration File Format

The configuration file (`config/kong/kong.yml`) follows Kong's declarative format:

### Services

```yaml
services:
  - name: api-service
    url: http://api-backend:8000
    connect_timeout: 5000
    read_timeout: 30000
    tags:
      - waddlebot
      - core
```

### Routes

```yaml
routes:
  - name: api-route
    service: api-service
    paths:
      - /api/v1/service
    strip_path: false
    protocols:
      - http
      - https
```

### Consumers

```yaml
consumers:
  - username: service-account
    custom_id: service-account
    tags:
      - service
```

### Plugins

#### Global Plugin

```yaml
plugins:
  - name: cors
    config:
      origins:
        - "https://example.com"
      methods:
        - GET
        - POST
```

#### Service-level Plugin

```yaml
plugins:
  - name: rate-limiting
    service: api-service
    config:
      minute: 100
```

#### Route-level Plugin

```yaml
plugins:
  - name: jwt
    route: api-route
    config:
      header_names:
        - Authorization
```

## Output

The script provides progress logging with:
- Service creation status
- Route creation status
- Consumer creation status
- Plugin creation status
- Final summary of imported objects

Example output:

```
[2025-12-08 10:30:45] INFO: Connected to Kong at http://localhost:8001
[2025-12-08 10:30:45] INFO: Loaded Kong configuration from config/kong/kong.yml
[2025-12-08 10:30:45] INFO: Format version: 3.0
[2025-12-08 10:30:45] INFO: Importing 15 service(s)...
[2025-12-08 10:30:46] INFO: ✓ Service created: hub-service (id: abc123...)
[2025-12-08 10:30:46] INFO: ✓ Service created: router-service (id: def456...)
...
[2025-12-08 10:30:50] INFO: ============================================================
[2025-12-08 10:30:50] INFO: IMPORT SUMMARY
[2025-12-08 10:30:50] INFO: ============================================================
[2025-12-08 10:30:50] INFO: Services: 15
[2025-12-08 10:30:50] INFO: Routes: 25
[2025-12-08 10:30:50] INFO: Consumers: 3
[2025-12-08 10:30:50] INFO: Plugins: 40
[2025-12-08 10:30:50] INFO: ============================================================
```

## Error Handling

The script handles common errors gracefully:

| Error | Handling |
|-------|----------|
| Connection refused | Displays error message and suggests checking Kong is running |
| Invalid YAML | Displays parsing error |
| Missing service reference | Skips dependent route/plugin with warning |
| 409 Conflict (resource exists) | Logs warning and continues (idempotent) |
| Network timeout | Retries or logs error |
| HTTP errors | Logs response status and body |

## Idempotent Operation

The script is **idempotent** - running it multiple times is safe:
- Attempts to create resources that already exist return HTTP 409 Conflict
- The script logs these as warnings but continues successfully
- This allows the script to be run multiple times for updates

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Failed to import (connection error, file not found, etc.) |

## Docker Usage

Run from Docker container:

```bash
docker run -v /path/to/WaddleBot:/app -w /app python:3.13 \
  bash -c "pip install requests pyyaml && python3 scripts/import-kong-config.py"
```

Or with custom settings:

```bash
docker run -v /path/to/WaddleBot:/app -w /app python:3.13 \
  bash -c "pip install requests pyyaml && python3 scripts/import-kong-config.py \
    --kong-url http://kong:8001 --verbose"
```

## Troubleshooting

### Kong Admin API not reachable

```
ERROR: Cannot connect to Kong: Connection refused
```

**Solution**: Ensure Kong is running and Admin API is accessible:

```bash
curl http://localhost:8001/status
```

### YAML parsing error

```
ERROR: Failed to parse YAML: ...
```

**Solution**: Validate YAML syntax:

```bash
python3 -m yaml config/kong/kong.yml
```

### Service not found for route

```
WARNING: Cannot find service ID for api-service, skipping route api-route
```

**Solution**: Ensure service is defined in YAML before routes that reference it.

### 409 Conflict errors

```
WARNING: Resource already exists (409): /services
```

**Solution**: This is normal and expected. The script is idempotent and will continue. To force re-import, delete existing resources in Kong Admin API first.

## Waddles Configuration

The Waddles Kong configuration includes:

- **Services**: 15 microservices (hub, router, AI, identity, labels, etc.)
- **Routes**: 25+ API endpoints with path-based routing
- **Consumers**: 3 standard consumers (anonymous, authenticated-user, service-account)
- **Plugins**: 40+ plugins for:
  - CORS (Cross-Origin Resource Sharing)
  - Rate limiting
  - Authentication (JWT, API Key)
  - Request tracking (Correlation ID)
  - Security (Request size limiting)

## References

- Kong Documentation: https://docs.konghq.com/
- Kong Admin API: https://docs.konghq.com/gateway/latest/admin-api/
- Waddles Architecture: `/home/penguin/code/waddlebot/CLAUDE.md`
