# Waddles Comprehensive Test Suite Guide

## Overview

The `test-all.sh` script is a comprehensive test runner that executes build tests, API tests, and WebUI load tests in parallel. All test output is logged to `/tmp` for detailed analysis.

## Quick Start

```bash
# Run all tests (default settings)
./test-all.sh

# Run with custom timeout (default: 300s)
TIMEOUT=120 ./test-all.sh

# Run with more parallel jobs (default: 8)
PARALLEL_JOBS=16 ./test-all.sh

# Combine options
TIMEOUT=180 PARALLEL_JOBS=12 ./test-all.sh
```

## Test Categories

### 1. Build Tests (Syntax & Compilation)
- **What:** Python syntax validation using `py_compile`
- **Scope:** All Python modules across the project
- **Fast:** Runs in < 5 seconds
- **Output:** `/tmp/waddlebot-tests-*/builds/`

### 2. API Tests (REST & gRPC)
- **What:** API endpoint health checks and functional tests
- **Scope:** 36 modules across core, action, trigger, processing, and admin
- **Requires:** Services must be running (docker-compose)
- **Output:** `/tmp/waddlebot-tests-*/api-tests/`

### 3. WebUI Tests (Page Load)
- **What:** Frontend page accessibility tests
- **Scope:** Hub module SPA routes and static assets
- **Requires:** Hub module running on localhost:8060
- **Output:** `/tmp/waddlebot-tests-*/webui-tests/`

## Understanding Test Results

### Exit Codes
- `0` - All tests passed
- `1` - Some tests failed

### Test Output
- **Console:** Real-time pass/fail indicators with colors
  - ✓ (green) - Test passed
  - ✗ (red) - Test failed
  - ⊘ (yellow) - Test skipped

- **Logs:** Detailed output in `/tmp/waddlebot-tests-<timestamp>/`
  - `SUMMARY.txt` - Overall results summary
  - `ANALYSIS.md` - Detailed analysis (if generated)
  - `builds/*.log` - Individual build test logs
  - `api-tests/*.log` - Individual API test logs
  - `webui-tests/*.log` - Individual WebUI test logs

## Common Scenarios

### Scenario 1: First Run (Services Not Started)

```bash
./test-all.sh
```

**Expected Results:**
- ✅ Build tests: 100% pass (all modules compile)
- ⚠️ API tests: ~30% pass (only Hub module running)
- ✅ WebUI tests: 100% pass (Hub frontend accessible)

**Action:** Start services with `docker-compose up -d`

### Scenario 2: Full Environment Running

```bash
# Start all services
docker-compose up -d

# Wait for services to be healthy
sleep 30

# Run tests
./test-all.sh
```

**Expected Results:**
- ✅ Build tests: 100% pass
- ✅ API tests: 90%+ pass (all services responding)
- ✅ WebUI tests: 100% pass

### Scenario 3: Quick Syntax Check Only

```bash
# Run syntax checks (no service requirements)
# Modify test-all.sh or run individual syntax tests
python3 -m py_compile $(find . -name "*.py" -path "*/action/*" -o -path "*/core/*" -o -path "*/libs/*")
```

## Analyzing Failed Tests

### Step 1: Check the Summary

```bash
# View latest test run summary
ls -td /tmp/waddlebot-tests-* | head -1 | xargs -I {} cat {}/SUMMARY.txt
```

### Step 2: Examine Individual Logs

```bash
# View specific test log
cat /tmp/waddlebot-tests-<timestamp>/api-tests/<module-name>.log
```

### Step 3: Common Failure Patterns

#### Pattern 1: Connection Refused
```
Cannot connect to router at http://localhost:8000
```
**Cause:** Service not running
**Fix:** Start service with docker-compose

#### Pattern 2: CSRF Token Error
```
CSRF token missing or invalid
```
**Cause:** Test script doesn't handle CSRF tokens
**Fix:** Update test script to fetch and include CSRF token

#### Pattern 3: Timeout
```
Status: TIMEOUT (120s)
```
**Cause:** Test took longer than timeout limit
**Fix:** Increase timeout with `TIMEOUT=300 ./test-all.sh`

## Log Retention

Test logs are stored in `/tmp` with timestamps. They will be automatically cleaned up by the system, typically after reboot or by tmpfs cleanup policies.

To preserve test results:

```bash
# Copy logs to project directory
cp -r /tmp/waddlebot-tests-<timestamp> ./test-results/

# Archive logs
tar -czf test-results-$(date +%Y%m%d).tar.gz /tmp/waddlebot-tests-<timestamp>
```

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Comprehensive Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Start services
        run: docker-compose up -d

      - name: Wait for services
        run: sleep 30

      - name: Run test suite
        run: ./test-all.sh

      - name: Archive test logs
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: test-logs
          path: /tmp/waddlebot-tests-*
```

## Performance Tuning

### Parallel Execution

The test suite uses background jobs to run tests in parallel. Adjust based on your system:

```bash
# Low-end systems (2-4 cores)
PARALLEL_JOBS=4 ./test-all.sh

# Medium systems (4-8 cores)
PARALLEL_JOBS=8 ./test-all.sh  # Default

# High-end systems (8+ cores)
PARALLEL_JOBS=16 ./test-all.sh
```

### Timeout Configuration

Adjust timeout based on your environment:

```bash
# Fast local environment
TIMEOUT=60 ./test-all.sh

# Standard environment
TIMEOUT=120 ./test-all.sh  # Default

# Slow CI environment
TIMEOUT=300 ./test-all.sh
```

## Troubleshooting

### Problem: Tests hang indefinitely

**Solution:** Kill stuck background jobs
```bash
# Find and kill background jobs
jobs -p | xargs kill -9

# Or use Ctrl+C (script handles gracefully)
```

### Problem: Permission denied on /tmp

**Solution:** Ensure /tmp is writable
```bash
# Check permissions
ls -ld /tmp

# Should show: drwxrwxrwt (sticky bit set)
```

### Problem: Logs not being created

**Solution:** Check disk space
```bash
df -h /tmp
```

## Advanced Usage

### Run Specific Test Categories

Currently, the script runs all test categories. To run specific categories, you can:

1. **Comment out sections** in `test-all.sh`:
   ```bash
   # Comment out unwanted test categories
   # run_build_tests
   run_api_tests
   # run_webui_tests
   ```

2. **Run individual test scripts** directly:
   ```bash
   # Run single module test
   bash action/interactive/ai_interaction_module/test-api.sh
   ```

### Custom Log Directory

Modify the script to change log location:

```bash
# Edit test-all.sh
LOG_DIR="/my/custom/path/waddlebot-tests-${TIMESTAMP}"
```

## Best Practices

1. **Always check build tests first** - If syntax tests fail, fix those before running API tests
2. **Start services before API tests** - Save time by ensuring services are running
3. **Archive important test runs** - Copy logs out of /tmp for critical test runs
4. **Review logs after failures** - Don't just re-run; understand why tests failed
5. **Use CI/CD integration** - Automate test runs on every commit

## Related Documentation

- [API Test Scripts](./api-testing.md) - Individual module API test documentation
- [WebUI Testing](./webui-testing.md) - Frontend testing guide
- [Docker Compose](../deployment/docker-compose.md) - Service orchestration
- [CI/CD Setup](../ci-cd/github-actions.md) - Automation guide

---
**Last Updated:** 2025-12-19
**Script Version:** 1.0.0
**Maintained by:** Waddles Engineering Team
