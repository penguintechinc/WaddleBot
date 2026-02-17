# YouTube Music Interaction Module - Testing

## Testing Overview

This document describes how to test the YouTube Music Interaction Module, including unit tests, integration tests, and end-to-end testing.

## Test Suite Structure

```
tests/
├── unit/
│   ├── test_config.py          # Configuration loading tests
│   ├── test_app.py             # Application setup tests
│   └── test_oauth.py           # OAuth handler tests
│
├── integration/
│   ├── test_database.py        # Database integration tests
│   ├── test_redis.py           # Redis integration tests
│   └── test_oauth_flow.py      # Full OAuth flow tests
│
├── e2e/
│   ├── test_api_endpoints.py   # All API endpoints
│   └── test_workflows.py       # User workflows
│
└── fixtures/
    ├── conftest.py             # pytest configuration
    ├── mock_youtube_api.py      # Mock YouTube API
    └── test_data.py            # Test data generators
```

## Running Tests

### Run All Tests

```bash
# Using pytest from project root
pytest tests/ -v

# With coverage
pytest tests/ -v --cov=action/interactive/youtube_music_interaction_module

# With specific output format
pytest tests/ -v --tb=short
```

### Run Test Category

```bash
# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v

# End-to-end tests only
pytest tests/e2e/ -v
```

### Run Specific Test

```bash
# Single test file
pytest tests/unit/test_config.py -v

# Single test function
pytest tests/unit/test_config.py::test_load_from_env -v

# Tests matching pattern
pytest -k "oauth" -v
```

### Run with Docker

```bash
# Run tests in container
docker-compose run --rm youtube-music-interaction \
  pytest tests/ -v

# Run with coverage
docker-compose run --rm youtube-music-interaction \
  pytest tests/ -v --cov=. --cov-report=html
```

## Unit Tests

Unit tests verify individual functions and classes in isolation.

### Configuration Tests

Test config.py functionality for loading environment variables and credentials:

```python
# Example test for configuration module
def test_config_from_env():
    # Test loads MODULE_PORT from environment
    # Verify DATABASE_URL parsing
    # Check default values applied
    pass

def test_load_credentials_from_db():
    # Test loading credentials from platform_integrations table
    # Verify client_id and client_secret retrieved
    # Test threading lock for credential safety
    pass

def test_load_credentials_db_fallback():
    # Test fallback to env when DB lookup fails
    # Verify error handling in credential loading
    # Check logging on fallback
    pass

def test_credential_listener_thread():
    # Test Redis listener thread creation
    # Verify daemon thread configuration
    # Check credential reload on notification
    pass
```

### Application Tests

Test app.py startup and endpoints for proper initialization:

```python
# Example tests for application endpoints
def test_app_startup():
    # Verify Quart application creates successfully
    # Check health blueprint registered at /health
    # Verify API blueprint registered at /api/v1
    pass

def test_health_endpoint_returns_json():
    # Test GET /health returns 200 OK
    # Verify JSON structure with status, module, version
    # Check timestamp field present
    pass

def test_healthz_kubernetes_probe():
    # Test GET /healthz Kubernetes probe
    # Verify dependency checks (database, redis)
    # Check status is healthy/degraded appropriately
    pass

def test_metrics_prometheus_format():
    # Test GET /metrics returns Prometheus format
    # Verify module info gauge
    # Check request counter metrics
    pass

def test_api_status_endpoint():
    # Test GET /api/v1/status returns operational
    # Verify response structure
    # Check module name matches configuration
    pass
```

## Integration Tests

Integration tests verify components working together.

### Database Integration

Test database connection and credential storage:

```python
# Database connection tests
def test_database_connection():
    # Test database connection established
    # Execute SELECT 1 to verify connectivity
    # Check connection pooling
    pass

def test_credential_storage():
    # Test storing credentials in database
    # Verify platform_integrations table has data
    # Check retrieved values match stored values
    pass

def test_credential_retrieval_with_filters():
    # Test filtering by community_id
    # Test filtering by is_active status
    # Verify only active credentials returned
    pass

def test_credential_encryption():
    # Verify stored tokens are encrypted
    # Check decryption on retrieval
    # Test token refresh updates encrypted value
    pass
```

### OAuth Flow Simulation

Mock OAuth endpoints and test flow:

```python
# OAuth flow tests
def test_oauth_code_exchange():
    # Mock YouTube OAuth token endpoint
    # Send authorization code to module
    # Verify access_token received
    # Check credentials stored in database
    pass

def test_oauth_token_refresh():
    # Test refresh token flow
    # Mock YouTube refresh endpoint
    # Verify new access_token returned
    # Check database updated with new token
    pass

def test_oauth_invalid_code_handling():
    # Test error handling for invalid code
    # Verify 400 Bad Request returned
    # Check error message provided
    pass

def test_oauth_scope_validation():
    # Test requested scopes validation
    # Verify youtube.readonly scope required
    # Check additional scopes handled
    pass
```

## Mock Objects

### Mock YouTube API

Create mock YouTube API responses:

```
# fixtures/mock_youtube_api.py
MockYouTubeAPI provides:
- mock_token_response(): OAuth token response
- mock_search_response(): Search API response
- mock_httpx_post(): Async HTTP POST mock
```

Sample token response:
```json
{
  "access_token": "ya29.test_token",
  "refresh_token": "1//test_refresh",
  "expires_in": 3600,
  "token_type": "Bearer"
}
```

### Mock Redis

Mock Redis for credential updates:

```
# fixtures/mock_redis.py
MockRedis provides:
- publish(): Send message to channel
- pubsub(): Mock pubsub interface
- listen(): Iterate over messages
```

## Test Data

### Sample OAuth Credentials

Test credentials used throughout test suite:

```
TEST_OAUTH_CODE: "4/0AdY47_bXxxxxxxxxxxx"

TEST_OAUTH_RESPONSE:
- access_token: "ya29.a0AfH6SMBxxxxxxxxxxxxxx"
- refresh_token: "1//0gF6xxxxxxxxxxxxxx"
- expires_in: 3600

TEST_CREDENTIALS:
- client_id: "123456789.apps.googleusercontent.com"
- client_secret: "GOCSPX-xxxxxxxxxxxx"

TEST_COMMUNITY_ID: "discord_community_123456"
TEST_USER_ID: "discord_user_987654"
```

## Testing OAuth Flow Locally

### Step 1: Start Module in Test Mode

```bash
# Set test environment
export MODULE_PORT=8025
export DATABASE_URL=postgresql://test:test@localhost/test_youtube_music
export YOUTUBE_CLIENT_ID=test_client_id
export YOUTUBE_CLIENT_SECRET=test_client_secret
export LOG_LEVEL=DEBUG

# Start module
hypercorn app:app --bind 0.0.0.0:8025
```

### Step 2: Initiate OAuth

```bash
# Generate authorization URL
curl -X POST http://localhost:8025/api/v1/oauth/authorize \
  -H "Content-Type: application/json" \
  -d '{
    "redirect_uri": "http://localhost:8025/oauth/callback",
    "scopes": ["youtube.readonly"],
    "state": "random_state_value"
  }'
```

### Step 3: Exchange Code

After user grants permission:

```bash
curl -X POST http://localhost:8025/api/v1/oauth/token \
  -H "Content-Type: application/json" \
  -d '{
    "code": "4/0AdY47_bXxxx...",
    "redirect_uri": "http://localhost:8025/oauth/callback"
  }'
```

## API Integration Test Script

The module includes test-api.sh for comprehensive endpoint testing:

```bash
# Run all tests
./action/interactive/youtube_music_interaction_module/test-api.sh

# Test specific URL
./action/interactive/youtube_music_interaction_module/test-api.sh --url http://localhost:8025

# View test output
./action/interactive/youtube_music_interaction_module/test-api.sh --help
```

This script tests:
- Health check endpoints
- Kubernetes health probe
- Prometheus metrics
- API status endpoint
- Error handling (404, 405)
- Response headers
- Service availability
- Response time

## Test Coverage Goals

Target minimum test coverage:

- **Unit Tests**: >85% coverage
- **Integration Tests**: >70% coverage
- **Critical Paths**: >95% coverage

Check coverage:

```bash
pytest tests/ \
  --cov=action/interactive/youtube_music_interaction_module \
  --cov-report=html
open htmlcov/index.html
```

## Performance Testing

### Load Testing with Locust

Locustfile example:

```
# tests/performance/locustfile.py

YouTubeMusicUser class:
- health_check task: GET /health
- status_endpoint task: GET /api/v1/status (weighted 3x)
- wait_time: 1-3 seconds between requests
```

Run load test:

```bash
locust -f tests/performance/locustfile.py --host=http://localhost:8025
```

## Security Testing

### Scan for Vulnerabilities

```bash
# Check for known vulnerabilities in dependencies
pip install safety
safety check

# Scan code with bandit for security issues
pip install bandit
bandit -r action/interactive/youtube_music_interaction_module/
```

### OAuth Security Tests

- Test CSRF protection with state parameter
- Verify redirect_uri validation
- Check token expiration enforcement
- Verify scope restrictions
- Test refresh token rotation

## CI/CD Integration

The module runs tests in GitHub Actions on every commit:

1. Test Job Creates Services (PostgreSQL, Redis)
2. Installs Dependencies
3. Runs Unit Tests
4. Runs Integration Tests
5. Generates Coverage Report
6. Uploads Coverage to Codecov

---

**Last Updated**: 2026-02-16
