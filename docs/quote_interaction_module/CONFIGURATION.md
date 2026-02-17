# Quote Interaction Module - Configuration

## Environment Variables

### Required Variables

#### DATABASE_URL

PostgreSQL connection string for the quotes database.

```bash
DATABASE_URL="postgresql://user:password@localhost:5432/waddlebot"
```

**Format:** `postgresql://[user]:[password]@[host]:[port]/[database]`

**Examples:**
```bash
# Local development
DATABASE_URL="postgresql://waddlebot:waddlebot@localhost:5432/waddlebot"

# Docker Compose
DATABASE_URL="postgresql://waddlebot:waddlebot@postgres:5432/waddlebot"

# Production (with SSL)
DATABASE_URL="postgresql://user:pass@prod.db.host:5432/waddlebot?sslmode=require"
```

**Note:** Must have access to the `quotes` table created by migration 015.

---

### Optional Variables

#### QUOTE_MODULE_PORT

The port on which the module listens for HTTP requests.

```bash
QUOTE_MODULE_PORT=5012
```

- **Default:** `5012`
- **Type:** integer
- **Range:** 1024-65535 (non-root ports)
- **Production:** May be overridden by container orchestration

---

#### QUOTE_MODULE_NAME

Module identifier used in logging and status endpoints.

```bash
QUOTE_MODULE_NAME="quote_interaction_module"
```

- **Default:** `quote_interaction_module`
- **Type:** string
- **Usage:** Appears in health checks and metrics

---

#### QUOTE_MODULE_VERSION

Module version string.

```bash
QUOTE_MODULE_VERSION="1.0.0"
```

- **Default:** `1.0.0`
- **Type:** string (semver format)
- **Usage:** Version reporting in status endpoints

---

#### READ_REPLICA_URL

Optional PostgreSQL read replica for scaling read-heavy queries.

```bash
READ_REPLICA_URL="postgresql://user:password@read-replica.db.host:5432/waddlebot"
```

- **Default:** Not set (uses DATABASE_URL for all queries)
- **Type:** string
- **Purpose:** Offload SELECT queries to read replica
- **Note:** Write operations still use primary DATABASE_URL

---

#### REDIS_URL

Redis connection for credential refresh notifications.

```bash
REDIS_URL="redis://localhost:6379/0"
```

- **Default:** Not set (credential updates disabled)
- **Type:** string
- **Format:** `redis://[host]:[port]/[db]`
- **Purpose:** Listen for credential refresh events on channel `credentials:quote_interaction:bot:refreshed`
- **Note:** Optional but recommended for multi-instance deployments

---

#### DB_POOL_SIZE

Number of concurrent database connections to maintain.

```bash
DB_POOL_SIZE=10
```

- **Default:** `10`
- **Type:** integer
- **Range:** 5-100
- **Tuning:** Increase for high-concurrency environments
  - Light traffic: 5-10
  - Medium traffic: 10-20
  - High traffic: 20-50
- **Note:** Each connection consumes PostgreSQL server resources

---

#### API_TIMEOUT

Request timeout in seconds for API operations.

```bash
API_TIMEOUT=30
```

- **Default:** `30`
- **Type:** integer
- **Unit:** seconds
- **Impact:** Maximum time a single request waits for database response
- **Typical Values:**
  - Development: 30
  - Production: 10-20

---

#### MAX_PAGE_SIZE

Maximum number of results per page (pagination limit).

```bash
MAX_PAGE_SIZE=100
```

- **Default:** `100`
- **Type:** integer
- **Purpose:** Prevents clients from requesting excessively large result sets
- **Trade-off:** Larger limit = more memory, but better for bulk operations
- **Typical Values:** 50-200

---

#### DEFAULT_PAGE_SIZE

Default page size when client doesn't specify limit.

```bash
DEFAULT_PAGE_SIZE=50
```

- **Default:** `50`
- **Type:** integer
- **Must be:** <= MAX_PAGE_SIZE
- **Purpose:** Reasonable default for list queries
- **Typical Values:** 20-100

---

#### AUTO_APPROVE_QUOTES

Auto-approve new quotes or require manual review.

```bash
AUTO_APPROVE_QUOTES=true
```

- **Default:** `true`
- **Type:** boolean (case-insensitive: "true"/"false")
- **Values:**
  - `true` or `yes` or `1` - New quotes approved immediately
  - `false` or `no` or `0` - New quotes require approval
- **Override:** Clients can override via `is_approved` parameter when creating quotes
- **Use Cases:**
  - `true`: Trusted communities with no moderation needed
  - `false`: Communities requiring quote review

---

#### LOG_LEVEL

Logging verbosity level.

```bash
LOG_LEVEL=INFO
```

- **Default:** `INFO`
- **Valid Values:**
  - `DEBUG` - Detailed debugging information
  - `INFO` - General informational messages
  - `WARNING` - Warning messages
  - `ERROR` - Error messages only
  - `CRITICAL` - Critical errors only
- **Development:** `DEBUG`
- **Production:** `INFO` or `WARNING`

---

## Configuration Examples

### Development Configuration

```bash
# .env.dev
QUOTE_MODULE_PORT=5012
QUOTE_MODULE_NAME=quote_interaction_module
QUOTE_MODULE_VERSION=1.0.0
DATABASE_URL=postgresql://waddlebot:waddlebot@localhost:5432/waddlebot
DB_POOL_SIZE=5
API_TIMEOUT=30
MAX_PAGE_SIZE=100
DEFAULT_PAGE_SIZE=50
AUTO_APPROVE_QUOTES=true
LOG_LEVEL=DEBUG
```

### Docker Compose Configuration

```yaml
services:
  quote_interaction_module:
    image: waddlebot/quote-interaction:latest
    environment:
      QUOTE_MODULE_PORT: 5012
      QUOTE_MODULE_NAME: quote_interaction_module
      QUOTE_MODULE_VERSION: 1.0.0
      DATABASE_URL: postgresql://waddlebot:waddlebot@postgres:5432/waddlebot
      DB_POOL_SIZE: 10
      API_TIMEOUT: 30
      MAX_PAGE_SIZE: 100
      DEFAULT_PAGE_SIZE: 50
      AUTO_APPROVE_QUOTES: 'true'
      LOG_LEVEL: INFO
      REDIS_URL: redis://redis:6379/0
    ports:
      - "5012:5012"
    depends_on:
      - postgres
      - redis
```

### Production Configuration

```bash
# .env.prod
QUOTE_MODULE_PORT=5012
QUOTE_MODULE_NAME=quote_interaction_module
QUOTE_MODULE_VERSION=1.0.0
DATABASE_URL=postgresql://quote_user:${DB_PASSWORD}@prod-db.internal:5432/waddlebot?sslmode=require
READ_REPLICA_URL=postgresql://quote_user:${DB_PASSWORD}@prod-replica.internal:5432/waddlebot?sslmode=require
DB_POOL_SIZE=20
API_TIMEOUT=15
MAX_PAGE_SIZE=100
DEFAULT_PAGE_SIZE=50
AUTO_APPROVE_QUOTES=false
LOG_LEVEL=WARNING
REDIS_URL=redis://:${REDIS_PASSWORD}@prod-redis.internal:6379/0
```

### Kubernetes Configuration

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: quote-module-config
data:
  QUOTE_MODULE_PORT: "5012"
  QUOTE_MODULE_NAME: "quote_interaction_module"
  LOG_LEVEL: "INFO"
  MAX_PAGE_SIZE: "100"
  DEFAULT_PAGE_SIZE: "50"
  AUTO_APPROVE_QUOTES: "true"
  DB_POOL_SIZE: "15"
  API_TIMEOUT: "20"
---
apiVersion: v1
kind: Secret
metadata:
  name: quote-module-secrets
type: Opaque
stringData:
  DATABASE_URL: "postgresql://quote_user:password@postgres:5432/waddlebot"
  READ_REPLICA_URL: "postgresql://quote_user:password@postgres-replica:5432/waddlebot"
  REDIS_URL: "redis://redis:6379/0"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: quote-interaction-module
spec:
  containers:
  - name: quote-module
    image: waddlebot/quote-interaction:latest
    ports:
    - containerPort: 5012
    envFrom:
    - configMapRef:
        name: quote-module-config
    - secretRef:
        name: quote-module-secrets
    livenessProbe:
      httpGet:
        path: /health
        port: 5012
      initialDelaySeconds: 30
      periodSeconds: 10
    readinessProbe:
      httpGet:
        path: /health
        port: 5012
      initialDelaySeconds: 10
      periodSeconds: 5
```

## Configuration File (.env)

Create a `.env` file in the project root for local development:

```bash
# Quote Module Configuration
QUOTE_MODULE_PORT=5012
QUOTE_MODULE_NAME=quote_interaction_module
QUOTE_MODULE_VERSION=1.0.0

# Database
DATABASE_URL=postgresql://waddlebot:waddlebot@localhost:5432/waddlebot
READ_REPLICA_URL=

# Redis (optional)
REDIS_URL=

# Connection Pool
DB_POOL_SIZE=10

# API Settings
API_TIMEOUT=30
MAX_PAGE_SIZE=100
DEFAULT_PAGE_SIZE=50

# Moderation
AUTO_APPROVE_QUOTES=true

# Logging
LOG_LEVEL=INFO
```

Load in Python:
```python
from dotenv import load_dotenv
import os

load_dotenv()
database_url = os.getenv('DATABASE_URL')
```

## Database Setup

### Migration 015 - Create Quotes Table

The module requires migration 015 to be applied:

```bash
# Run migrations
python3 -c "from config.postgres.migrations import run_migrations; run_migrations()"

# Verify table exists
psql $DATABASE_URL -c "\dt quotes"

# Check indices
psql $DATABASE_URL -c "\di" | grep quotes
```

### Manual Table Creation

If migrations haven't been applied:

```sql
CREATE TABLE quotes (
    id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL,
    quote_text TEXT NOT NULL,
    quoted_user_id INTEGER,
    quoted_username VARCHAR(255),
    added_by_user_id INTEGER,
    platform VARCHAR(50),
    context TEXT,
    tags TEXT[],
    is_approved BOOLEAN DEFAULT TRUE,
    search_vector TSVECTOR GENERATED ALWAYS AS 
        (to_tsvector('english', quote_text)) STORED,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMP
);

CREATE INDEX idx_quotes_community_id 
    ON quotes(community_id, deleted_at);
CREATE INDEX idx_quotes_approved 
    ON quotes(community_id, is_approved) 
    WHERE deleted_at IS NULL;
CREATE INDEX idx_quotes_author 
    ON quotes(community_id, quoted_username) 
    WHERE deleted_at IS NULL;
CREATE INDEX idx_quotes_search_vector 
    ON quotes USING GIN(search_vector);
CREATE INDEX idx_quotes_random 
    ON quotes(community_id, is_approved, created_at) 
    WHERE deleted_at IS NULL;

ALTER TABLE quotes 
    ADD CONSTRAINT fk_quotes_community 
    FOREIGN KEY (community_id) REFERENCES communities(id);
```

## Configuration Validation

### Check Configuration

```bash
# Verify environment variables are set
python3 << 'EOF'
import os
from config import Config

print(f"Module: {Config.MODULE_NAME} v{Config.MODULE_VERSION}")
print(f"Port: {Config.MODULE_PORT}")
print(f"Database Pool Size: {Config.DB_POOL_SIZE}")
print(f"Auto Approve: {Config.AUTO_APPROVE_QUOTES}")
print(f"Max Page Size: {Config.MAX_PAGE_SIZE}")
print(f"Log Level: {Config.LOG_LEVEL}")
EOF
```

### Test Database Connection

```bash
# Verify PostgreSQL connection
psql $DATABASE_URL -c "SELECT version();"

# Check quotes table
psql $DATABASE_URL -c "SELECT COUNT(*) as count FROM quotes;"
```

## Troubleshooting Configuration Issues

### Common Issues

**Issue:** Module fails to start with "database connection error"

**Solution:**
1. Verify DATABASE_URL is correctly formatted
2. Ensure PostgreSQL server is running and accessible
3. Check database credentials
4. Verify network connectivity to database host

```bash
# Test connection
psql $DATABASE_URL -c "SELECT 1;"
```

**Issue:** "relation quotes does not exist"

**Solution:** Run database migrations to create tables

```bash
python3 -c "from config.postgres.migrations import run_migrations; run_migrations()"
```

**Issue:** Search queries returning no results

**Solution:** Verify search_vector column exists and is populated

```bash
psql $DATABASE_URL -c "SELECT id, quote_text, search_vector FROM quotes LIMIT 5;"
```

## Performance Tuning

### For High-Concurrency Environments

```bash
DB_POOL_SIZE=25
API_TIMEOUT=20
```

### For Memory-Constrained Environments

```bash
DB_POOL_SIZE=5
MAX_PAGE_SIZE=50
DEFAULT_PAGE_SIZE=25
```

### For Search-Heavy Workloads

```bash
# Enable read replica for queries
READ_REPLICA_URL=postgresql://...

# Increase pool size
DB_POOL_SIZE=15
```
