# Router Module Testing Guide

## Overview

Comprehensive testing guide for the Router Module, including unit tests, integration tests, and API testing.

**Version:** 2.0.0

---

## Table of Contents

1. [Test Infrastructure](#test-infrastructure)
2. [API Testing](#api-testing)
3. [Unit Testing](#unit-testing)
4. [Integration Testing](#integration-testing)
5. [Performance Testing](#performance-testing)
6. [Test Data](#test-data)

---

## Test Infrastructure

### Test Dependencies

```txt
# requirements.txt
pytest>=7.4.0
pytest-asyncio>=0.23.0
pytest-cov>=4.1.0
aiohttp>=3.12.14
```

### Install Test Dependencies

```bash
cd /home/penguin/code/WaddleBot/processing/router_module
pip install -r requirements.txt
```

---

## API Testing

### Using test-api.sh

The module includes a comprehensive API test script located at `/processing/router_module/test-api.sh`.

#### Basic Usage

```bash
# Test local instance
./test-api.sh

# Test remote instance
ROUTER_URL=http://router.example.com:8000 ./test-api.sh

# Test with API key
API_KEY=your-key-here ./test-api.sh

# Verbose mode
./test-api.sh --verbose
```

#### Test Coverage

The script tests all endpoints:

| Test | Endpoint | Description |
|------|----------|-------------|
| Health Check | `GET /health` | Basic health check |
| Kubernetes Probe | `GET /healthz` | Health probe with component checks |
| Metrics | `GET /metrics` | Prometheus metrics |
| Admin Status | `GET /api/v1/admin/status` | Admin status endpoint |
| List Commands | `GET /api/v1/router/commands` | Command listing |
| Router Metrics | `GET /api/v1/router/metrics` | Performance metrics |
| Process Event | `POST /api/v1/router/events` | Single event processing |
| Batch Processing | `POST /api/v1/router/events/batch` | Batch event processing |
| Submit Response | `POST /api/v1/router/responses` | Module response submission |
| 404 Handling | `GET /api/v1/invalid` | Error handling |
| Malformed JSON | `POST /api/v1/router/events` | Validation error handling |

#### Sample Output

```
========================================
Waddles Router Module API Tests
========================================
Router URL: http://localhost:8000
API Key: [set]
Verbose: 0

========================================
Connectivity Check
========================================
✓ Router is accessible

========================================
Health & Status Endpoints
========================================
[TEST] GET /health - Basic health check
[PASS] GET /health - Health check working
[TEST] GET /healthz - Kubernetes health probe
[PASS] GET /healthz - Health probe working
[TEST] GET /metrics - Prometheus metrics
[PASS] GET /metrics - Metrics endpoint working
[TEST] GET /api/v1/admin/status - Admin status check
[PASS] GET /api/v1/admin/status - Status endpoint working

========================================
Router Endpoints
========================================
[TEST] GET /api/v1/router/commands - List available commands
[PASS] GET /api/v1/router/commands - List commands working
[TEST] GET /api/v1/router/metrics - Router performance metrics
[PASS] GET /api/v1/router/metrics - Router metrics working
[TEST] POST /api/v1/router/events - Process single event
[PASS] POST /api/v1/router/events - Process event working
[TEST] POST /api/v1/router/events/batch - Process batch of events
[PASS] POST /api/v1/router/events/batch - Batch processing working
[TEST] POST /api/v1/router/responses - Submit module response
[PASS] POST /api/v1/router/responses - Submit response working

========================================
Error Handling
========================================
[TEST] GET /api/v1/invalid - Test 404 handling
[PASS] GET /api/v1/invalid - 404 handling working
[TEST] POST /api/v1/router/events - Test malformed JSON handling
[PASS] POST /api/v1/router/events - Handles malformed JSON

========================================
Test Summary
========================================

Total Tests:  11
Passed:       11
Failed:       0
Skipped:      0

Success Rate: 100.0%

✓ All tests passed
```

#### Environment Variables

```bash
# test-api.sh environment variables
ROUTER_URL=http://localhost:8000  # Base URL
API_KEY=your-api-key               # Optional API key
VERBOSE=1                          # Verbose output (0 or 1)
```

#### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All tests passed |
| 1 | One or more tests failed |

---

## Unit Testing

### Validation Model Tests

**File:** `/processing/router_module/test_validation.py`

Tests Pydantic validation models for API requests.

#### Run Unit Tests

```bash
cd /home/penguin/code/WaddleBot/processing/router_module
pytest test_validation.py -v
```

#### Test Structure

```python
import pytest
from pydantic import ValidationError
from validation_models import RouterEventRequest, RouterBatchRequest, RouterResponseRequest


class TestRouterEventRequest:
    """Test RouterEventRequest validation."""

    def test_valid_event(self):
        """Test valid event request."""
        event = RouterEventRequest(
            platform="twitch",
            channel_id="12345",
            user_id="67890",
            username="test_user",
            message="!help"
        )
        assert event.platform == "twitch"
        assert event.message == "!help"

    def test_invalid_platform(self):
        """Test invalid platform rejection."""
        with pytest.raises(ValidationError) as exc:
            RouterEventRequest(
                platform="invalid",
                channel_id="12345",
                user_id="67890",
                username="test_user",
                message="!help"
            )
        assert "platform" in str(exc.value)

    def test_empty_message(self):
        """Test empty message rejection."""
        with pytest.raises(ValidationError) as exc:
            RouterEventRequest(
                platform="twitch",
                channel_id="12345",
                user_id="67890",
                username="test_user",
                message=""
            )
        assert "message" in str(exc.value)

    def test_message_too_long(self):
        """Test message length limit."""
        with pytest.raises(ValidationError) as exc:
            RouterEventRequest(
                platform="twitch",
                channel_id="12345",
                user_id="67890",
                username="test_user",
                message="x" * 5001  # Max is 5000
            )
        assert "message" in str(exc.value)


class TestRouterBatchRequest:
    """Test RouterBatchRequest validation."""

    def test_valid_batch(self):
        """Test valid batch request."""
        batch = RouterBatchRequest(
            events=[
                RouterEventRequest(
                    platform="twitch",
                    channel_id="12345",
                    user_id="67890",
                    username="user1",
                    message="!help"
                ),
                RouterEventRequest(
                    platform="discord",
                    channel_id="98765",
                    user_id="43210",
                    username="user2",
                    message="!stats"
                )
            ]
        )
        assert len(batch.events) == 2

    def test_empty_batch(self):
        """Test empty batch rejection."""
        with pytest.raises(ValidationError) as exc:
            RouterBatchRequest(events=[])
        assert "events" in str(exc.value)

    def test_batch_too_large(self):
        """Test batch size limit (max 100)."""
        events = [
            RouterEventRequest(
                platform="twitch",
                channel_id="12345",
                user_id=f"user_{i}",
                username=f"user_{i}",
                message="!help"
            )
            for i in range(101)  # Max is 100
        ]

        with pytest.raises(ValidationError) as exc:
            RouterBatchRequest(events=events)
        assert "events" in str(exc.value)


class TestRouterResponseRequest:
    """Test RouterResponseRequest validation."""

    def test_valid_response(self):
        """Test valid response request."""
        response = RouterResponseRequest(
            event_id="evt_abc123",
            response="Command executed successfully",
            platform="twitch",
            channel_id="12345"
        )
        assert response.event_id == "evt_abc123"
        assert response.platform == "twitch"

    def test_empty_response(self):
        """Test empty response rejection."""
        with pytest.raises(ValidationError) as exc:
            RouterResponseRequest(
                event_id="evt_abc123",
                response="",
                platform="twitch",
                channel_id="12345"
            )
        assert "response" in str(exc.value)
```

#### Run Tests with Coverage

```bash
pytest test_validation.py --cov=validation_models --cov-report=html
```

**Coverage Report:** `htmlcov/index.html`

---

## Integration Testing

### Service Integration Tests

Create integration tests for service interactions:

```python
# test_integration.py
import pytest
import asyncio
from services.command_processor import CommandProcessor
from services.command_registry import CommandRegistry
from services.cache_manager import CacheManager
from services.rate_limiter import RateLimiter
from services.session_manager import SessionManager


@pytest.fixture
async def command_processor():
    """Create CommandProcessor instance for testing."""
    # Mock dependencies
    dal = MockDAL()
    cache = CacheManager()
    rate_limiter = RateLimiter()
    session_manager = SessionManager()
    registry = CommandRegistry(dal, cache)

    processor = CommandProcessor(
        dal, cache, rate_limiter, session_manager, registry
    )
    return processor


@pytest.mark.asyncio
async def test_process_chat_message(command_processor):
    """Test processing a chat message."""
    event = {
        "platform": "twitch",
        "channel_id": "12345",
        "user_id": "67890",
        "username": "test_user",
        "message": "Hello world",
        "message_type": "chatMessage"
    }

    result = await command_processor.process_event(event)

    assert result["success"] is True
    assert "session_id" in result


@pytest.mark.asyncio
async def test_process_command(command_processor):
    """Test processing a command."""
    event = {
        "platform": "twitch",
        "channel_id": "12345",
        "user_id": "67890",
        "username": "test_user",
        "message": "!help",
        "message_type": "chatMessage"
    }

    result = await command_processor.process_event(event)

    assert result["success"] is True
    assert result["command"] == "!help"


@pytest.mark.asyncio
async def test_rate_limiting(command_processor):
    """Test rate limiting."""
    event = {
        "platform": "twitch",
        "channel_id": "12345",
        "user_id": "67890",
        "username": "test_user",
        "message": "!balance",
        "message_type": "chatMessage"
    }

    # Send 65 requests (limit is 60)
    results = []
    for i in range(65):
        result = await command_processor.process_event(event)
        results.append(result)

    # Count successes and rate limit errors
    successes = sum(1 for r in results if r.get("success"))
    rate_limited = sum(1 for r in results if "rate limit" in r.get("error", "").lower())

    assert successes == 60
    assert rate_limited == 5


@pytest.mark.asyncio
async def test_translation_service():
    """Test translation service."""
    from services.translation_service import TranslationService

    dal = MockDAL()
    cache = CacheManager()
    service = TranslationService(dal, cache)

    config = {
        "enabled": True,
        "default_language": "en",
        "min_words": 2,
        "confidence_threshold": 0.7
    }

    result = await service.translate(
        text="Hola mundo",
        target_lang="en",
        community_id=123,
        config=config
    )

    assert result is not None
    assert result["translated_text"] == "Hello world"
    assert result["detected_lang"] == "es"


@pytest.mark.asyncio
async def test_command_registry():
    """Test command registry."""
    from services.command_registry import CommandRegistry

    dal = MockDAL()
    cache = CacheManager()
    registry = CommandRegistry(dal, cache)

    # Register command
    success = await registry.register_command(
        command="!test",
        module_name="test_module",
        module_url="http://test:8000",
        description="Test command",
        category="testing",
        cooldown_seconds=5
    )

    assert success is True

    # Retrieve command
    cmd = await registry.get_command("!test")
    assert cmd is not None
    assert cmd.command == "!test"
    assert cmd.cooldown_seconds == 5
```

#### Run Integration Tests

```bash
pytest test_integration.py -v
```

---

## Performance Testing

### Load Testing with Locust

Create load tests using Locust:

```python
# locustfile.py
from locust import HttpUser, task, between


class RouterUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        """Set up headers."""
        self.headers = {
            "Content-Type": "application/json",
            "X-Service-Key": "test-api-key"
        }

    @task(5)
    def process_chat_message(self):
        """Process a chat message (most common)."""
        event = {
            "platform": "twitch",
            "channel_id": "12345",
            "user_id": "67890",
            "username": "load_test_user",
            "message": "Hello world"
        }
        self.client.post(
            "/api/v1/router/events",
            json=event,
            headers=self.headers
        )

    @task(3)
    def process_command(self):
        """Process a command."""
        event = {
            "platform": "twitch",
            "channel_id": "12345",
            "user_id": "67890",
            "username": "load_test_user",
            "message": "!help"
        }
        self.client.post(
            "/api/v1/router/events",
            json=event,
            headers=self.headers
        )

    @task(1)
    def list_commands(self):
        """List commands."""
        self.client.get("/api/v1/router/commands")

    @task(1)
    def health_check(self):
        """Health check."""
        self.client.get("/health")
```

#### Run Load Test

```bash
# Install locust
pip install locust

# Run load test
locust -f locustfile.py --host=http://localhost:8000

# Or headless mode
locust -f locustfile.py --host=http://localhost:8000 \
  --users 100 --spawn-rate 10 --run-time 60s --headless
```

### Benchmark Results (Expected)

| Operation | Throughput | P50 Latency | P95 Latency | P99 Latency |
|-----------|------------|-------------|-------------|-------------|
| Chat message (cached) | 10,000 req/s | 5ms | 15ms | 30ms |
| Chat message (uncached) | 2,000 req/s | 50ms | 150ms | 300ms |
| Command execution | 1,000 req/s | 100ms | 300ms | 500ms |
| Translation (cached) | 20,000 req/s | 5ms | 10ms | 20ms |
| Translation (uncached) | 500 req/s | 200ms | 500ms | 1000ms |
| Health check | 50,000 req/s | 1ms | 3ms | 5ms |

---

## Test Data

### Sample Events

#### Chat Message Event

```json
{
  "platform": "twitch",
  "channel_id": "12345",
  "user_id": "67890",
  "username": "test_user",
  "message": "Hello everyone!",
  "metadata": {
    "display_name": "Test User",
    "badges": ["subscriber"]
  }
}
```

#### Command Event

```json
{
  "platform": "discord",
  "channel_id": "discord-channel-id",
  "user_id": "discord-user-id",
  "username": "test_user",
  "message": "!balance",
  "command": "!balance",
  "metadata": {
    "display_name": "Test User#1234"
  }
}
```

#### Slash Command Event

```json
{
  "platform": "discord",
  "channel_id": "discord-channel-id",
  "user_id": "discord-user-id",
  "username": "test_user",
  "message": "/help stats",
  "message_type": "slashCommand",
  "metadata": {
    "command_name": "help",
    "options": {
      "topic": "stats"
    },
    "interaction_id": "interaction-id",
    "interaction_token": "interaction-token"
  }
}
```

#### Interaction Event

```json
{
  "platform": "discord",
  "channel_id": "discord-channel-id",
  "user_id": "discord-user-id",
  "username": "test_user",
  "message": "",
  "message_type": "button_click",
  "metadata": {
    "custom_id": "inventory:buy:item_123",
    "interaction_id": "interaction-id",
    "interaction_token": "interaction-token"
  }
}
```

#### Stream Event (Subscription)

```json
{
  "platform": "twitch",
  "channel_id": "12345",
  "user_id": "67890",
  "username": "new_subscriber",
  "message": "",
  "message_type": "subscription",
  "metadata": {
    "tier": "1000",
    "is_gift": false,
    "cumulative_months": 1
  }
}
```

#### Translation Test Event

```json
{
  "platform": "twitch",
  "channel_id": "12345",
  "user_id": "67890",
  "username": "spanish_user",
  "message": "Hola @penguin_user, mira este link https://example.com y usa !help",
  "metadata": {
    "display_name": "Spanish User"
  }
}
```

### Database Test Data

```sql
-- Insert test community
INSERT INTO communities (id, name, config)
VALUES (999, 'Test Community', '{
  "translation": {
    "enabled": true,
    "default_language": "en",
    "min_words": 2,
    "confidence_threshold": 0.7
  }
}'::jsonb);

-- Insert test server mapping
INSERT INTO community_servers (community_id, platform, platform_server_id, is_active)
VALUES (999, 'twitch', '12345', true);

-- Insert test commands
INSERT INTO commands (command, module_name, description, category, is_enabled, is_active)
VALUES
  ('!help', 'core_commands', 'Show help', 'general', true, true),
  ('!balance', 'economy_module', 'Check balance', 'economy', true, true),
  ('!stats', 'stats_module', 'Show stats', 'fun', true, true);

-- Insert test module
INSERT INTO hub_modules (name, url, is_active)
VALUES ('test_module', 'http://test-module:8000', true);
```

---

## Continuous Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/router-tests.yml
name: Router Module Tests

on:
  push:
    branches: [main, develop]
    paths:
      - 'processing/router_module/**'
  pull_request:
    branches: [main, develop]
    paths:
      - 'processing/router_module/**'

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: waddlebot
          POSTGRES_PASSWORD: password
          POSTGRES_DB: waddlebot_test
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

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.13'

      - name: Install dependencies
        run: |
          cd processing/router_module
          pip install -r requirements.txt
          cd ../../libs/flask_core
          pip install -e .

      - name: Run validation tests
        run: |
          cd processing/router_module
          pytest test_validation.py -v --cov=validation_models --cov-report=xml

      - name: Run integration tests
        env:
          DATABASE_URL: postgresql://waddlebot:password@localhost:5432/waddlebot_test
          REDIS_HOST: localhost
          REDIS_PORT: 6379
        run: |
          cd processing/router_module
          pytest test_integration.py -v

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./processing/router_module/coverage.xml
```

---

## Test Checklist

### Before Release

- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] API tests pass (test-api.sh)
- [ ] Load tests show acceptable performance
- [ ] Translation tests pass
- [ ] gRPC tests pass
- [ ] Redis Streams tests pass (if enabled)
- [ ] Error handling tests pass
- [ ] Rate limiting tests pass
- [ ] Cache tests pass
- [ ] Database tests pass
- [ ] Coverage > 80%

---

## See Also

- [API.md](./API.md) - API reference
- [USAGE.md](./USAGE.md) - Usage examples
- [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) - Troubleshooting guide
