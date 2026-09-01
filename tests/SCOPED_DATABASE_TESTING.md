# Scoped Database Implementation Testing Guide

This document covers the three critical integration test suites for validating the scoped database implementation with Row-Level Security (RLS) and module credential isolation.

## Test Scripts Overview

### 1. RLS Policy Enforcement Tests
**File**: `tests/integration/rls_policies_test.sh`

Tests that Row-Level Security (RLS) policies correctly isolate platform credentials between modules.

#### What It Tests
- **Module Platform Isolation**: Verifies each module user can only SELECT credentials for their assigned platform
- **RLS Blocking**: Confirms RLS blocks access to platforms not assigned to the module
- **Hub Admin Full Access**: Validates hub_admin role has unrestricted access to all platforms
- **Analytics Read-Only**: Ensures analytics user can query all platforms but cannot modify data
- **Column-Level Security**: Verifies sensitive columns (like password_hash) are protected

#### Test Cases
1. `twitch_action` can SELECT `test-twitch` credentials only
2. `twitch_action` cannot SELECT `test-discord` or `test-slack` credentials
3. `discord_action` can SELECT `test-discord` credentials only
4. `discord_action` cannot SELECT other platform credentials
5. `slack_action` can SELECT `test-slack` credentials only
6. `hub_admin` can SELECT all platform credentials (no RLS restrictions)
7. `analytics` can SELECT all platforms (read-only access)

#### Usage
```bash
# Prerequisites: PostgreSQL running with migrations applied
./tests/integration/rls_policies_test.sh

# With custom database connection
DB_HOST=prod-postgres DB_PORT=5432 DB_NAME=waddlebot ./tests/integration/rls_policies_test.sh

# Environment variables
export DB_HOST="localhost"          # PostgreSQL host
export DB_PORT="5432"               # PostgreSQL port
export DB_NAME="waddlebot"          # Database name
export DB_SUPERUSER="postgres"      # Superuser for setup/cleanup
export DB_SUPERUSER_PASSWORD="pw"   # Superuser password
```

#### Success Criteria
- All 7+ test cases pass
- Color-coded output shows green checkmarks
- TAP (Test Anything Protocol) output written to `/tmp/rls_policies_test.tap`
- Exit code 0

#### What It Validates
- **Security**: Module users cannot access other modules' credentials
- **Compliance**: RLS policies enforce credential isolation at database layer
- **Admin Access**: Hub admin has necessary access for management tasks
- **Audit Ready**: Tests confirm isolation is enforced for audit requirements

---

### 2. Credential Refresh Integration Tests
**File**: `tests/integration/credential_refresh_test.sh`

Verifies the credential manager service can refresh tokens and notify modules via Redis.

#### What It Tests
- **Token Expiry Detection**: Identifies credentials approaching expiration
- **Credential Manager Write Access**: Validates credential-manager can UPDATE platform_integrations
- **Redis Pub/Sub Ready**: Confirms Redis is available for notifications
- **Token Update Verification**: Confirms tokens are properly refreshed
- **Audit Logging**: Validates credential access is tracked (optional)

#### Test Cases
1. Insert credential with 2-minute expiry
2. Verify credential inserted successfully
3. Test credential_manager SELECT access
4. Detect tokens within 5-minute expiration window
5. credential_manager can UPDATE platform_integrations
6. Verify token was updated to new value
7. Redis pub/sub is accessible
8. Audit log table is queryable (optional)

#### Usage
```bash
# Prerequisites: PostgreSQL + Redis running with migrations applied
./tests/integration/credential_refresh_test.sh

# With custom database/Redis connection
DB_HOST=postgres.local REDIS_HOST=cache.local ./tests/integration/credential_refresh_test.sh

# Environment variables
export DB_HOST="localhost"                    # PostgreSQL host
export DB_PORT="5432"                         # PostgreSQL port
export DB_NAME="waddlebot"                    # Database name
export DB_SUPERUSER="postgres"                # Setup/cleanup user
export DB_SUPERUSER_PASSWORD="password"       # Superuser password
export REDIS_HOST="localhost"                 # Redis host
export REDIS_PORT="6379"                      # Redis port
```

#### Success Criteria
- All 8 test cases pass
- Token expiry detection working
- credential_manager UPDATE access confirmed
- Redis connectivity verified
- Exit code 0

#### What It Validates
- **Token Management**: Credential refresh service can detect and update expiring tokens
- **Service Communication**: credential_manager microservice has correct database permissions
- **Notification Ready**: Redis pub/sub channel is available for real-time updates
- **Audit Trail**: Credential access is logged for compliance

---

### 3. Module Database Access Smoke Tests
**File**: `tests/smoke/module_db_access_test.sh`

Quick validation that all module users can connect with their scoped credentials.

#### What It Tests
- **Admin User Connectivity**: hub_admin, analytics, credential_manager can connect
- **Core Module Access**: 13 core modules can establish database connections
- **Trigger Module Access**: 5 trigger modules can authenticate
- **Action Module Access**: 6 action modules can authenticate
- **Interactive Module Access**: 10 interactive modules can authenticate

#### Test Organization
- **Admin Users**: Hub admin, analytics, credential manager
- **Core Modules**: Router, labels, browser source, identity, AI researcher, workflow, community, reputation, security, video proxy, engagement, RTC
- **Trigger Modules**: Twitch, Discord, Slack, YouTube, Kick
- **Action Modules**: Twitch, Discord, Slack, YouTube, Lambda, GCP
- **Interactive Modules**: AI, Alias, Shoutout, Inventory, Calendar, Memories, YouTube Music, Spotify, Loyalty, Quote

#### Usage
```bash
# Quick smoke test (< 30 seconds)
./tests/smoke/module_db_access_test.sh

# With custom connection settings
DB_HOST=infra-postgres DB_PORT=5432 ./tests/smoke/module_db_access_test.sh

# Environment variables
export DB_HOST="localhost"              # PostgreSQL host
export DB_PORT="5432"                   # PostgreSQL port
export DB_NAME="waddlebot"              # Database name
export DB_SUPERUSER="postgres"          # Validation user
export DB_SUPERUSER_PASSWORD="password" # Validation password
```

#### Success Criteria
- All 34+ module connections succeed
- Green checkmarks for all tests
- Completes in under 30 seconds
- TAP output written to `/tmp/module_db_access_test.tap`
- Exit code 0

#### What It Validates
- **Deployment Health**: All modules can connect to database
- **Credential Distribution**: Scoped credentials properly provisioned to all modules
- **Pre-Deployment Check**: Fast validation before deploying to production
- **Rapid Feedback**: Smoke test provides quick go/no-go decision

---

## Running All Tests

### Sequential Execution
```bash
# Run all three test suites in order
./tests/integration/rls_policies_test.sh && \
  ./tests/integration/credential_refresh_test.sh && \
  ./tests/smoke/module_db_access_test.sh

echo "All scoped database tests passed!"
```

### In CI/CD Pipeline
Add to `.github/workflows/ci-cd.yml`:
```yaml
- name: Test RLS Policies
  run: ./tests/integration/rls_policies_test.sh

- name: Test Credential Refresh
  run: ./tests/integration/credential_refresh_test.sh

- name: Smoke Test Module Access
  run: ./tests/smoke/module_db_access_test.sh
```

### With Docker Compose
```bash
# Start services in background
docker-compose up -d postgres redis

# Wait for services to be ready
sleep 5

# Run all tests
./tests/integration/rls_policies_test.sh
./tests/integration/credential_refresh_test.sh
./tests/smoke/module_db_access_test.sh

# Cleanup
docker-compose down
```

---

## Test Output Formats

### Console Output
All tests provide color-coded console output:
- **Green checkmark (✓)**: Test passed
- **Red X (✗)**: Test failed
- **Blue section headers**: Test category
- **Summary table**: Test count and results

Example:
```
✓ PASS: twitch_action can SELECT twitch platform
✗ FAIL: twitch_action cannot SELECT discord platform
✓ PASS: discord_action can SELECT discord platform
```

### TAP Output
TAP (Test Anything Protocol) compatible output for CI/CD integration:
```
1..42
ok 1 - twitch_action can SELECT twitch platform
not ok 2 - twitch_action cannot SELECT discord platform
ok 3 - discord_action can SELECT discord platform
...
```

Files:
- RLS Tests: `/tmp/rls_policies_test.tap`
- Credential Tests: `/tmp/credential_refresh_test.tap`
- Module Tests: `/tmp/module_db_access_test.tap`

### Exit Codes
- **0**: All tests passed - safe to proceed
- **1**: One or more tests failed - requires investigation

---

## Troubleshooting

### Database Connection Failed
```
ERROR: Cannot connect to PostgreSQL
Database: localhost:5432/waddlebot
User: postgres
```

**Solutions**:
1. Verify PostgreSQL is running: `docker-compose ps postgres`
2. Check connection settings: `DB_HOST=<ip> ./test.sh`
3. Verify migrations applied: `docker-compose exec postgres psql -U postgres -d waddlebot -c '\dt'`

### RLS Tests Fail with Permission Denied
```
not ok 1 - twitch_action can SELECT twitch platform
```

**Solutions**:
1. Verify RLS policies exist: Check migrations have run
2. Verify scoped users exist: `docker-compose exec postgres psql -U postgres -l`
3. Verify table permissions: `GRANT SELECT ON platform_integrations TO twitch_action;`

### Credential Refresh Tests Fail
```
not ok 5 - credential_manager can update platform_integrations
```

**Solutions**:
1. Verify credential_manager has UPDATE permission
2. Check schema: `SELECT * FROM platform_integrations LIMIT 1;`
3. Test UPDATE directly: `UPDATE platform_integrations SET updated_at = NOW() LIMIT 1;`

### Redis Connection Failed
```
not ok 7 - Redis is accessible for pub/sub notifications
```

**Solutions**:
1. Verify Redis running: `docker-compose ps redis`
2. Test connectivity: `redis-cli -h <host> -p <port> PING`
3. Check network: `docker-compose logs redis`

---

## Integration with CI/CD

### GitHub Actions
```yaml
test-scoped-database:
  runs-on: ubuntu-latest
  services:
    postgres:
      image: postgres:15
      env:
        POSTGRES_PASSWORD: postgres
      options: >-
        --health-cmd pg_isready
        --health-interval 10s
        --health-timeout 5s
        --health-retries 5
    redis:
      image: redis:7
      options: >-
        --health-cmd "redis-cli ping"
        --health-interval 10s
        --health-timeout 5s
        --health-retries 5
  steps:
    - uses: actions/checkout@v3
    - name: Run migrations
      run: ./scripts/migrate.sh
    - name: Run RLS tests
      run: ./tests/integration/rls_policies_test.sh
    - name: Run credential refresh tests
      run: ./tests/integration/credential_refresh_test.sh
    - name: Run module access tests
      run: ./tests/smoke/module_db_access_test.sh
```

### Pre-Commit Hook
Add to `.git/hooks/pre-commit`:
```bash
#!/bin/bash
set -e

# Quick smoke test before commit
./tests/smoke/module_db_access_test.sh

# If making DB changes, run integration tests
if git diff --cached --name-only | grep -q "config/postgres/migrations"; then
    ./tests/integration/rls_policies_test.sh
    ./tests/integration/credential_refresh_test.sh
fi
```

---

## Test Maintenance

### Adding New Modules
When adding a new module to the system:

1. **Add scoped user** in `config/postgres/migrations/`
2. **Add database user creation** in migration
3. **Update module_db_access_test.sh** to test new module:
   ```bash
   test_connection "new_module" "mod_new_module_dev_changeme" "New Module"
   ```
4. **Run smoke tests** to verify connectivity

### Adding New Platforms
When adding a new platform integration (Twitch, Discord, etc.):

1. **Test RLS isolation** by adding test case to rls_policies_test.sh
2. **Verify credential manager** can refresh tokens for new platform
3. **Update module_db_access_test.sh** for platform-specific action modules

### Updating Scoped Credentials
When rotating or updating credentials:

1. **Run credential_refresh_test.sh** to verify update mechanism
2. **Verify RLS policies** still enforce isolation
3. **Check audit logs** for credential access events

---

## Performance Characteristics

### Test Execution Times
- **rls_policies_test.sh**: ~10-15 seconds
- **credential_refresh_test.sh**: ~15-20 seconds
- **module_db_access_test.sh**: ~25-30 seconds
- **Total suite**: ~50-65 seconds

### Database Impact
- Temporary test data created and cleaned up
- Minimal database load (mostly SELECT operations)
- Safe to run in production-like environments
- RLS policies tested, not modified

### Resource Requirements
- PostgreSQL: ~50MB RAM for test operations
- Redis: ~10MB RAM for pub/sub test
- Network: ~1MB data transfer
- CPU: Minimal (I/O bound)

---

## Security Notes

### Credential Handling
- Test scripts do NOT log passwords to stdout
- Environment variables used for sensitive data
- TAP output contains no sensitive information
- Temporary test data cleaned up after each run

### RLS Enforcement
- Tests verify RLS blocks unauthorized access
- No test data persists after execution
- Superuser only used for setup/cleanup
- Module users only have scoped access

### Audit Trail
- All credential access logged (when implemented)
- Test activities tracked in credential_access_log
- Audit logs provide compliance evidence

---

## Troubleshooting Checklist

Before filing an issue:

- [ ] PostgreSQL is running and accessible
- [ ] Redis is running and accessible
- [ ] Database migrations have been applied
- [ ] Scoped users have been created
- [ ] RLS policies are in place
- [ ] Network connectivity is working
- [ ] Environment variables are set correctly
- [ ] No firewall blocking database/Redis ports

---

## Next Steps

After all tests pass:

1. **Deploy to staging** with confidence in scoped database implementation
2. **Monitor audit logs** for credential access patterns
3. **Verify module functionality** with real platform credentials
4. **Schedule rotation** of scoped credentials periodically
5. **Run tests before production deploy** as mandatory check

---

## References

- [PostgreSQL RLS Documentation](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- [TAP Specification](https://testanything.org/)
- [Redis Pub/Sub](https://redis.io/topics/pubsub)
- [SCOPED_CREDENTIALS.md](../../docs/SCOPED_CREDENTIALS.md)
