# Scoped Database Integration Test Guide

Quick reference for integrating and running the three critical test scripts for validating the scoped database implementation.

## Files Created

```
tests/
├── integration/
│   ├── rls_policies_test.sh          (243 lines, 7.7 KB)
│   ├── credential_refresh_test.sh    (258 lines, 8.1 KB)
│   └── [existing test files]
├── smoke/
│   ├── module_db_access_test.sh      (184 lines, 7.2 KB)
│   └── [existing test files]
├── SCOPED_DATABASE_TESTING.md        (447 lines, 15 KB) - Full documentation
└── INTEGRATION_GUIDE.md              (this file)
```

## Quick Start

### Prerequisites
- PostgreSQL running with migrations applied
- Redis running (for credential refresh test)
- Network access to both services
- Bash 4.0+ available

### Running Tests

```bash
# Individual tests
./tests/integration/rls_policies_test.sh
./tests/integration/credential_refresh_test.sh
./tests/smoke/module_db_access_test.sh

# All tests in sequence
bash -c 'set -e && \
  ./tests/integration/rls_policies_test.sh && \
  ./tests/integration/credential_refresh_test.sh && \
  ./tests/smoke/module_db_access_test.sh && \
  echo "All scoped database tests PASSED"'

# With custom database
DB_HOST=prod-db DB_PORT=5432 ./tests/integration/rls_policies_test.sh
```

## Test Script Reference

### 1. RLS Policy Tests (`tests/integration/rls_policies_test.sh`)

**What it does**: Validates Row-Level Security policies enforce credential isolation

**Key assertions**:
- Module users can access only their assigned platform
- RLS blocks cross-platform access
- Hub admin has full access
- Analytics has read-only access

**Typical output**:
```
✓ PASS: twitch_action can SELECT twitch platform
✓ PASS: twitch_action cannot SELECT discord platform (RLS blocks)
✓ PASS: discord_action can SELECT discord platform
✓ PASS: hub_admin can SELECT all platforms
```

**Execution time**: 10-15 seconds

**TAP output**: `/tmp/rls_policies_test.tap`

### 2. Credential Refresh Tests (`tests/integration/credential_refresh_test.sh`)

**What it does**: Validates token refresh mechanism and Redis pub/sub

**Key assertions**:
- Expiring tokens are detected
- Credential manager can update tokens
- Token updates are verified
- Redis pub/sub is accessible

**Typical output**:
```
✓ PASS: Credential inserted successfully
✓ PASS: credential_manager can query platform_integrations
✓ PASS: Expiring tokens detected within 5-minute window
✓ PASS: credential_manager can update platform_integrations
```

**Execution time**: 15-20 seconds

**TAP output**: `/tmp/credential_refresh_test.tap`

### 3. Module Access Tests (`tests/smoke/module_db_access_test.sh`)

**What it does**: Quick validation that all 34+ modules can connect with scoped credentials

**Key assertions**:
- Admin users can connect
- 12+ core modules can connect
- 5 trigger modules can connect
- 6 action modules can connect
- 10 interactive modules can connect

**Typical output**:
```
✓ PASS: Hub Admin (hub_admin)
✓ PASS: Router (mod_router)
✓ PASS: Twitch Trigger (twitch_trigger)
✓ PASS: Twitch Action (twitch_action)
... (34+ tests total)
```

**Execution time**: 25-30 seconds

**TAP output**: `/tmp/module_db_access_test.tap`

## Environment Variables

All scripts support these environment variables (with defaults):

```bash
# Database configuration
DB_HOST=localhost              # PostgreSQL hostname
DB_PORT=5432                   # PostgreSQL port
DB_NAME=waddlebot              # Database name
DB_SUPERUSER=postgres          # Superuser for setup/teardown
DB_SUPERUSER_PASSWORD=postgres # Superuser password

# Redis configuration (credential_refresh_test only)
REDIS_HOST=localhost           # Redis hostname
REDIS_PORT=6379               # Redis port

# TAP output location
TAP_OUTPUT=/tmp/test.tap       # TAP output file (optional)
```

## Docker Compose Integration

### Start Services
```bash
# Terminal 1: Start PostgreSQL and Redis
docker-compose up postgres redis

# Wait for services to be ready
sleep 5

# Terminal 2: Run tests
./tests/integration/rls_policies_test.sh
./tests/integration/credential_refresh_test.sh
./tests/smoke/module_db_access_test.sh

# Cleanup
docker-compose down
```

### Using Services in docker-compose.yml
```yaml
# In docker-compose.yml or docker-compose.test.yml
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: waddlebot
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
```

## GitHub Actions Integration

Add to `.github/workflows/ci-cd.yml`:

```yaml
name: Database Tests

on: [push, pull_request]

jobs:
  database-tests:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: waddlebot
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v3

      - name: Run migrations
        run: |
          apt-get update && apt-get install -y postgresql-client
          psql -h localhost -U postgres -d waddlebot \
            -f config/postgres/init.sql
          for f in config/postgres/migrations/*.sql; do
            psql -h localhost -U postgres -d waddlebot -f "$f"
          done
        env:
          PGPASSWORD: postgres

      - name: Test RLS Policies
        run: ./tests/integration/rls_policies_test.sh
        env:
          DB_HOST: localhost
          DB_SUPERUSER_PASSWORD: postgres

      - name: Test Credential Refresh
        run: ./tests/integration/credential_refresh_test.sh
        env:
          DB_HOST: localhost
          REDIS_HOST: localhost
          DB_SUPERUSER_PASSWORD: postgres

      - name: Test Module Access
        run: ./tests/smoke/module_db_access_test.sh
        env:
          DB_HOST: localhost
          DB_SUPERUSER_PASSWORD: postgres

      - name: Upload TAP results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: tap-results
          path: /tmp/*.tap
```

## Makefile Integration

Add to `Makefile`:

```makefile
.PHONY: test-rls
test-rls:
	@echo "Running RLS policy tests..."
	@./tests/integration/rls_policies_test.sh

.PHONY: test-credentials
test-credentials:
	@echo "Running credential refresh tests..."
	@./tests/integration/credential_refresh_test.sh

.PHONY: test-modules
test-modules:
	@echo "Running module access smoke tests..."
	@./tests/smoke/module_db_access_test.sh

.PHONY: test-scoped-db
test-scoped-db: test-rls test-credentials test-modules
	@echo ""
	@echo "All scoped database tests PASSED"

.PHONY: test-all
test-all: test-unit test-integration test-scoped-db
	@echo "All tests PASSED"
```

Usage:
```bash
make test-scoped-db          # Run all three tests
make test-rls                # Run RLS tests only
make test-credentials        # Run credential tests only
make test-modules            # Run module access tests only
```

## Pre-Commit Hook

Add to `.git/hooks/pre-commit`:

```bash
#!/bin/bash

set -e

echo "Running scoped database smoke tests..."

# Always run quick smoke test
./tests/smoke/module_db_access_test.sh || {
    echo "Module access test failed. Commit blocked."
    exit 1
}

# Run integration tests if DB changes
if git diff --cached --name-only | grep -q "config/postgres"; then
    echo "Database changes detected. Running integration tests..."
    ./tests/integration/rls_policies_test.sh || {
        echo "RLS tests failed. Commit blocked."
        exit 1
    }
    ./tests/integration/credential_refresh_test.sh || {
        echo "Credential refresh tests failed. Commit blocked."
        exit 1
    }
fi

echo "All tests passed. Proceeding with commit."
exit 0
```

Make executable:
```bash
chmod +x .git/hooks/pre-commit
```

## Troubleshooting

### Tests Fail with "Cannot connect to PostgreSQL"

```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# Verify migrations are applied
docker-compose exec postgres psql -U postgres -d waddlebot -c '\dt'

# Test with explicit host
DB_HOST=127.0.0.1 ./tests/integration/rls_policies_test.sh
```

### RLS Tests Show Permission Denied

```bash
# Check if scoped users exist
docker-compose exec postgres psql -U postgres -c '\du' | grep mod_

# Check if table permissions are set
docker-compose exec postgres psql -U postgres -d waddlebot -c '\z platform_integrations'

# Verify RLS policies exist
docker-compose exec postgres psql -U postgres -d waddlebot -c \
  'SELECT * FROM pg_policies WHERE tablename = ''platform_integrations'';'
```

### Credential Refresh Tests Fail with "credential_manager cannot update"

```bash
# Check credential_manager user exists
docker-compose exec postgres psql -U postgres -d waddlebot -c \
  'SELECT * FROM pg_roles WHERE rolname = ''credential_manager'';'

# Grant UPDATE permission
docker-compose exec postgres psql -U postgres -d waddlebot -c \
  'GRANT UPDATE ON platform_integrations TO credential_manager;'

# Test UPDATE directly
docker-compose exec postgres psql -U credential_manager -d waddlebot -c \
  'UPDATE platform_integrations SET updated_at = NOW() WHERE id = 1;'
```

### Redis Connection Failed

```bash
# Check if Redis is running
docker-compose ps redis

# Test connection
redis-cli -h localhost -p 6379 PING

# With Docker
docker-compose exec redis redis-cli PING
```

## Continuous Monitoring

### Parse TAP Output in CI/CD

```bash
# Count passed/failed
grep "^ok" /tmp/rls_policies_test.tap | wc -l     # Passed
grep "^not ok" /tmp/rls_policies_test.tap | wc -l # Failed
```

### Set Alerts for Failures

```bash
# Monitor test results in GitHub Actions
# Add workflow status to Slack, email, or monitoring system

# Example: Slack notification on failure
if [ $(grep -c "^not ok" /tmp/*.tap) -gt 0 ]; then
    curl -X POST $SLACK_WEBHOOK \
        -d '{"text": "Scoped database tests FAILED"}'
fi
```

## Performance Baseline

Expected execution times on standard hardware:

| Test | Time | Notes |
|------|------|-------|
| RLS Policies | 10-15s | 7+ assertions |
| Credential Refresh | 15-20s | Includes Redis + cleanup |
| Module Access | 25-30s | 34+ module connections |
| **Total** | **50-65s** | Full suite |

Optimize by running in parallel for CI/CD:

```bash
# Parallel execution (bash jobs)
./tests/integration/rls_policies_test.sh &
./tests/smoke/module_db_access_test.sh &
wait

# Then run credential test (requires database in clean state)
./tests/integration/credential_refresh_test.sh
```

## Next Steps

1. **Run tests locally** to verify setup works
2. **Add to CI/CD pipeline** for automated validation
3. **Configure pre-commit hooks** for developer workflow
4. **Monitor results** in production deployments
5. **Update tests** when adding new modules or platforms

See `tests/SCOPED_DATABASE_TESTING.md` for comprehensive documentation.
