# Kick Module Testing Guide

## Testing Framework

The Kick Module uses a comprehensive testing strategy covering unit, integration, functional, and end-to-end tests. All tests must pass before deployment.

### Test Categories

1. **Unit Tests** - Individual function/class behavior
2. **Integration Tests** - Component interactions (API, database, WebSocket)
3. **Functional Tests** - Business logic (event normalization, routing)
4. **End-to-End Tests** - Full workflow from webhook → Router
5. **Performance Tests** - Throughput, latency, memory
6. **Security Tests** - HMAC verification, input validation

## Running Tests

### Quick Start

```bash
cd trigger/receiver/kick_module_flask

# Run all tests
pytest

# Run specific test category
pytest tests/unit/
pytest tests/integration/
pytest tests/functional/

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test
pytest tests/unit/test_kick_api.py::test_get_channel -v
```

### Test Execution Order

Tests should be run in this order (some depend on setup from earlier tests):

```bash
# 1. Unit tests (no external dependencies)
pytest tests/unit/ -v

# 2. Integration tests (require database/Redis)
pytest tests/integration/ -v

# 3. Functional tests (require Core API mock)
pytest tests/functional/ -v

# 4. End-to-end tests (full system)
pytest tests/e2e/ -v

# 5. Performance tests (baseline comparisons)
pytest tests/performance/ -v --benchmark-only
```

### Docker Test Environment

```bash
# Run tests in Docker
docker build -f Dockerfile.test -t kick-module-test .

docker run --rm \
  --network=host \
  -e DATABASE_URL=postgresql://postgres:postgres@localhost:5432/test_db \
  -e REDIS_URL=redis://localhost:6379/1 \
  -e CORE_API_URL=http://localhost:8000 \
  -e ROUTER_API_URL=http://localhost:8001 \
  kick-module-test \
  pytest -v

# With Docker Compose (repo's docker-compose.yml — no separate test compose file exists)
docker-compose up --abort-on-container-exit trigger-kick
```

## Unit Tests

Unit tests verify individual components in isolation.

### Test File: `tests/unit/test_kick_api.py`

```python
import pytest
from src.services.kick_api import KickAPI

@pytest.fixture
async def kick_api():
    """Create KickAPI instance with mock HTTP client"""
    api = KickAPI(session=mock_session)
    yield api
    await api.session.close()

@pytest.mark.asyncio
async def test_get_channel_success(kick_api, mock_response):
    """Test successful channel retrieval"""
    mock_response.json.return_value = {
        "id": 12345,
        "username": "streamer",
        "verified": True
    }

    result = await kick_api.get_channel(12345)

    assert result["username"] == "streamer"
    assert result["verified"] is True

@pytest.mark.asyncio
async def test_get_channel_not_found(kick_api, mock_response):
    """Test 404 handling"""
    mock_response.status = 404

    with pytest.raises(ChannelNotFoundError):
        await kick_api.get_channel(99999)

@pytest.mark.asyncio
async def test_send_chat_message_rate_limit(kick_api, mock_response):
    """Test rate limit handling (429)"""
    mock_response.status = 429
    mock_response.headers = {"Retry-After": "60"}

    with pytest.raises(RateLimitError) as exc:
        await kick_api.send_chat_message(12345, "test")

    assert exc.value.retry_after == 60
```

### Test File: `tests/unit/test_webhook_signature.py`

```python
import pytest
from src.handlers.webhook import verify_signature

def test_signature_valid():
    """Test valid HMAC signature"""
    payload = b'{"event":"chat_message"}'
    secret = "test-secret-32-chars-minimum!!"

    import hmac, hashlib
    expected_sig = "sha256=" + hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

    assert verify_signature(payload, expected_sig, secret) is True

def test_signature_invalid():
    """Test invalid signature rejection"""
    payload = b'{"event":"chat_message"}'
    secret = "test-secret-32-chars-minimum!!"
    bad_sig = "sha256=0000000000000000000000000000000000000000000000000000000000000000"

    assert verify_signature(payload, bad_sig, secret) is False

def test_signature_timing_attack_resistance():
    """Verify constant-time comparison (no timing leaks)"""
    payload = b'{"event":"chat_message"}'
    secret = "test-secret-32-chars-minimum!!"

    import hmac, hashlib
    correct_sig = "sha256=" + hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

    # Should take same time regardless of where sig differs
    import time
    times = []

    for i in range(100):
        bad_sig = "sha256=" + "0" * (i % 64) + "ff" + "0" * (64 - (i % 64) - 2)
        start = time.perf_counter()
        verify_signature(payload, bad_sig, secret)
        times.append(time.perf_counter() - start)

    # Timing variance should be low (constant-time)
    assert max(times) / min(times) < 1.5  # Less than 50% variance

def test_signature_empty_payload():
    """Test signature of empty payload"""
    payload = b''
    secret = "test-secret-32-chars-minimum!!"

    import hmac, hashlib
    expected_sig = "sha256=" + hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

    assert verify_signature(payload, expected_sig, secret) is True
```

### Test File: `tests/unit/test_event_models.py`

```python
import pytest
from src.models.events import ChatMessageEvent, KickSender

def test_chat_message_event_creation():
    """Test event dataclass initialization"""
    sender = KickSender(
        id="123",
        username="testuser",
        display_name="Test User",
        avatar_url="https://example.com/avatar.jpg",
        badges=["subscriber", "moderator"],
        is_verified=False
    )

    event = ChatMessageEvent(
        channel_id="12345",
        sender=sender,
        message="Hello world!",
        message_id="msg_123",
        timestamp="2026-02-24T12:34:56Z"
    )

    assert event.event_type == "chat"
    assert event.sender.username == "testuser"
    assert "subscriber" in event.sender.badges

def test_event_to_dict():
    """Test event serialization"""
    sender = KickSender(
        id="123",
        username="testuser",
        display_name="Test User",
        avatar_url="https://example.com/avatar.jpg",
        badges=[],
        is_verified=False
    )

    event = ChatMessageEvent(
        channel_id="12345",
        sender=sender,
        message="Hello",
        message_id="msg_123",
        timestamp="2026-02-24T12:34:56Z"
    )

    data = event.to_dict()
    assert data["event_type"] == "chat"
    assert data["sender"]["username"] == "testuser"
    assert isinstance(data, dict)

def test_event_validation():
    """Test required fields validation"""
    sender = KickSender(
        id="123",
        username="testuser",
        display_name="Test User",
        avatar_url="https://example.com/avatar.jpg",
        badges=[],
        is_verified=False
    )

    # Missing required fields should fail
    with pytest.raises(TypeError):
        ChatMessageEvent(
            channel_id="12345",
            sender=sender
            # Missing: message, message_id, timestamp
        )
```

## Integration Tests

Integration tests verify component interactions with real dependencies.

### Test File: `tests/integration/test_webhook_handler.py`

```python
import pytest
from quart import create_app
from src.index import app

@pytest.fixture
async def client():
    """Create Quart test client"""
    async with app.test_client() as client:
        yield client

@pytest.mark.asyncio
async def test_webhook_success(client, webhook_payload, webhook_secret):
    """Test successful webhook delivery"""
    import hmac, hashlib

    payload_bytes = webhook_payload.encode()
    sig = "sha256=" + hmac.new(
        webhook_secret.encode(),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()

    response = await client.post(
        '/webhook/kick',
        data=payload_bytes,
        headers={
            'X-Signature': sig,
            'Content-Type': 'application/json'
        }
    )

    assert response.status_code == 202
    data = await response.get_json()
    assert data["status"] == "accepted"

@pytest.mark.asyncio
async def test_webhook_signature_mismatch(client, webhook_payload):
    """Test signature verification failure"""
    response = await client.post(
        '/webhook/kick',
        data=webhook_payload.encode(),
        headers={
            'X-Signature': 'sha256=badbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadb',
            'Content-Type': 'application/json'
        }
    )

    assert response.status_code == 401
    data = await response.get_json()
    assert data["error"] == "signature_mismatch"

@pytest.mark.asyncio
async def test_webhook_duplicate_detection(client, webhook_payload, webhook_secret):
    """Test duplicate webhook rejection"""
    import hmac, hashlib

    payload_bytes = webhook_payload.encode()
    sig = "sha256=" + hmac.new(
        webhook_secret.encode(),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()

    # First request
    response1 = await client.post(
        '/webhook/kick',
        data=payload_bytes,
        headers={'X-Signature': sig, 'Content-Type': 'application/json'}
    )
    assert response1.status_code == 202

    # Duplicate request (same payload)
    response2 = await client.post(
        '/webhook/kick',
        data=payload_bytes,
        headers={'X-Signature': sig, 'Content-Type': 'application/json'}
    )
    assert response2.status_code == 202

    # Should only process once (check database)
    # Implementation detail: verify event count is 1, not 2
```

### Test File: `tests/integration/test_router_integration.py`

```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_event_forwarding_to_router(mock_router_api):
    """Test event is forwarded to Router API"""
    from src.handlers.router import forward_event
    from src.models.events import ChatMessageEvent, KickSender

    sender = KickSender(
        id="123",
        username="testuser",
        display_name="Test User",
        avatar_url="https://example.com/avatar.jpg",
        badges=[],
        is_verified=False
    )

    event = ChatMessageEvent(
        channel_id="12345",
        sender=sender,
        message="Hello",
        message_id="msg_123",
        timestamp="2026-02-24T12:34:56Z"
    )

    await forward_event(event)

    # Verify POST to Router API
    mock_router_api.post.assert_called_once()
    call_args = mock_router_api.post.call_args
    assert '/api/v1/events' in call_args[0][0]

@pytest.mark.asyncio
async def test_router_api_retry_on_failure(mock_router_api):
    """Test retry logic on Router API failure"""
    from src.handlers.router import forward_event
    from src.models.events import ChatMessageEvent, KickSender

    # Simulate API failure then success
    mock_router_api.post.side_effect = [
        Exception("Connection error"),
        AsyncMock(status=200)()
    ]

    sender = KickSender(id="123", username="test", display_name="Test", avatar_url="", badges=[], is_verified=False)
    event = ChatMessageEvent(
        channel_id="12345",
        sender=sender,
        message="test",
        message_id="msg_123",
        timestamp="2026-02-24T12:34:56Z"
    )

    # Should retry and eventually succeed
    await forward_event(event)

    assert mock_router_api.post.call_count == 2
```

## Functional Tests

Functional tests verify business logic and workflows.

### Test File: `tests/functional/test_event_normalization.py`

```python
import pytest
from src.handlers.normalize import normalize_event

def test_chat_message_normalization():
    """Test Kick chat event → standard format"""
    kick_event = {
        "event": "chat_message",
        "created_at": "2026-02-24T12:34:56Z",
        "data": {
            "channel_id": 12345,
            "username": "testuser",
            "user_id": 54321,
            "message": "Hello everyone!",
            "message_id": "msg_xyz789",
            "badges": ["subscriber"]
        }
    }

    normalized = normalize_event(kick_event)

    assert normalized.event_type == "chat"
    assert normalized.platform == "kick"
    assert normalized.channel_id == "12345"
    assert normalized.sender.username == "testuser"
    assert normalized.message == "Hello everyone!"
    assert "subscriber" in normalized.sender.badges

def test_subscription_normalization():
    """Test subscription event normalization"""
    kick_event = {
        "event": "subscription",
        "data": {
            "channel_id": 12345,
            "username": "newsubscriber",
            "user_id": 99999,
            "tier": "2",
            "months": 3
        }
    }

    normalized = normalize_event(kick_event)

    assert normalized.event_type == "subscription"
    assert normalized.metadata["tier"] == "2"
    assert normalized.metadata["months"] == 3
    assert normalized.metadata["is_gift"] is False

def test_raid_normalization():
    """Test raid event normalization"""
    kick_event = {
        "event": "raid",
        "data": {
            "channel_id": 12345,
            "raider_username": "raiding_channel",
            "raider_channel_id": 11111,
            "viewer_count": 245
        }
    }

    normalized = normalize_event(kick_event)

    assert normalized.event_type == "raid"
    assert normalized.metadata["viewer_count"] == 245
    assert normalized.sender.id == "11111"
```

## End-to-End Tests

E2E tests verify complete workflows.

### Test File: `tests/e2e/test_full_workflow.py`

```python
import pytest
from quart import create_app

@pytest.mark.asyncio
async def test_webhook_to_router_flow(client, webhook_secret, mock_router_api, db):
    """Test complete workflow: webhook receipt → Router delivery"""
    import hmac, hashlib
    import json

    # Prepare webhook
    payload_dict = {
        "event": "chat_message",
        "created_at": "2026-02-24T12:34:56Z",
        "data": {
            "channel_id": 12345,
            "username": "testuser",
            "user_id": 54321,
            "message": "Hello!",
            "message_id": "msg_123",
            "badges": []
        }
    }
    payload_bytes = json.dumps(payload_dict).encode()

    sig = "sha256=" + hmac.new(
        webhook_secret.encode(),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()

    # Send webhook
    response = await client.post(
        '/webhook/kick',
        data=payload_bytes,
        headers={
            'X-Signature': sig,
            'Content-Type': 'application/json'
        }
    )

    assert response.status_code == 202

    # Wait for async processing
    import asyncio
    await asyncio.sleep(0.5)

    # Verify event forwarded to Router
    assert mock_router_api.post.called
    call_args = mock_router_api.post.call_args
    posted_data = json.loads(call_args.kwargs["json"])
    assert posted_data["events"][0]["event_type"] == "chat"
    assert posted_data["events"][0]["content"] == "Hello!"

    # Verify in database
    events = db.session.query(KickEvent).filter_by(channel_id=12345).all()
    assert len(events) == 1
    assert events[0].event_type == "chat"

@pytest.mark.asyncio
async def test_websocket_chat_flow(kick_chat_client, mock_pusher):
    """Test WebSocket chat event processing"""
    # Subscribe to channel
    await kick_chat_client.subscribe_channel(12345, 67890)

    # Simulate Pusher message
    await kick_chat_client.handle_message(
        "ChatMessage",
        {
            "username": "chatuser",
            "user_id": 99999,
            "message": "WebSocket test",
            "message_id": "ws_msg_123"
        }
    )

    # Verify event was queued
    # Implementation: check async queue
    await asyncio.sleep(0.1)
    # Verify Router was called
    # Implementation: mock verification
```

## Performance Tests

Performance tests establish baselines and catch regressions.

### Test File: `tests/performance/test_throughput.py`

```python
import pytest
import asyncio

@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_webhook_processing_throughput(benchmark, webhook_payload, webhook_secret):
    """Benchmark webhook signature verification"""
    import hmac, hashlib

    async def process_webhook():
        payload_bytes = webhook_payload.encode()
        sig = "sha256=" + hmac.new(
            webhook_secret.encode(),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
        # Simulate verification
        return hmac.compare_digest(sig, sig)

    # Run benchmark
    result = await benchmark.pedantic(process_webhook, rounds=1000, iterations=1)
    assert result is True

@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_event_normalization_throughput(benchmark, raw_kick_event):
    """Benchmark event normalization"""
    from src.handlers.normalize import normalize_event

    async def normalize():
        return normalize_event(raw_kick_event)

    result = await benchmark.pedantic(normalize, rounds=100, iterations=10)
    assert result.event_type == "chat"

@pytest.mark.asyncio
async def test_concurrent_webhook_handling(client, webhook_secret):
    """Test handling multiple concurrent webhooks"""
    import hmac, hashlib
    import json

    async def send_webhook(num):
        payload_dict = {
            "event": "chat_message",
            "data": {
                "channel_id": 12345,
                "username": f"user_{num}",
                "user_id": 50000 + num,
                "message": f"Message {num}",
                "message_id": f"msg_{num}",
                "badges": []
            }
        }
        payload_bytes = json.dumps(payload_dict).encode()
        sig = "sha256=" + hmac.new(
            webhook_secret.encode(),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()

        return await client.post(
            '/webhook/kick',
            data=payload_bytes,
            headers={'X-Signature': sig, 'Content-Type': 'application/json'}
        )

    # Send 100 concurrent requests
    import time
    start = time.time()

    tasks = [send_webhook(i) for i in range(100)]
    responses = await asyncio.gather(*tasks)

    elapsed = time.time() - start

    # All should succeed
    assert all(r.status_code == 202 for r in responses)

    # Should handle 100 webhooks in <5 seconds
    assert elapsed < 5.0
    print(f"Processed 100 webhooks in {elapsed:.2f}s ({100/elapsed:.0f} webhooks/sec)")
```

## Security Tests

Security tests verify authentication and input validation.

### Test File: `tests/security/test_signature_validation.py`

```python
import pytest

def test_signature_required():
    """Signature header must be present"""
    # Missing header should be rejected
    # Implementation: send webhook without X-Signature

def test_invalid_signature_format():
    """Invalid signature format should be rejected"""
    # E.g., "sha256=" without hex, "md5=...", etc.

def test_payload_tampering_detection():
    """Verify payload tampering is detected"""
    # Change payload after signing, should be rejected

def test_sql_injection_prevention():
    """Malicious payloads should not cause SQL injection"""
    payload = {
        "data": {
            "username": "'; DROP TABLE kick_events; --",
            "message": "SELECT * FROM users WHERE 1=1"
        }
    }
    # Should be safely stored/processed

def test_xss_prevention():
    """HTML/JS payloads should not execute"""
    payload = {
        "data": {
            "message": "<script>alert('xss')</script>",
            "username": "<img src=x onerror=alert('xss')>"
        }
    }
    # Should be stored as plain text, never rendered as HTML
```

## Test Fixtures

Shared fixtures for all tests.

### File: `tests/conftest.py`

```python
import pytest
import os
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def webhook_secret():
    """Return test webhook secret"""
    return "test-secret-minimum-32-chars!!"

@pytest.fixture
def webhook_payload():
    """Return sample webhook payload"""
    return '''{
        "event": "chat_message",
        "created_at": "2026-02-24T12:34:56Z",
        "data": {
            "channel_id": 12345,
            "username": "testuser",
            "user_id": 54321,
            "message": "Test message",
            "message_id": "msg_123",
            "badges": ["subscriber"]
        }
    }'''

@pytest.fixture
def mock_router_api(monkeypatch):
    """Mock Router API"""
    mock = AsyncMock()
    mock.post = AsyncMock(return_value=AsyncMock(status=200))
    # Patch aiohttp.ClientSession.post
    monkeypatch.setattr("aiohttp.ClientSession.post", mock.post)
    return mock

@pytest.fixture
@pytest.mark.asyncio
async def client():
    """Create Quart test client"""
    from src.index import app
    async with app.test_client() as client:
        yield client

@pytest.fixture
def db():
    """Setup test database"""
    # Create test database
    # Run migrations
    # Yield connection
    # Cleanup
    pass
```

## Smoke Test Checklist

Pre-deployment smoke tests (must all pass, &lt;2 minutes):

```bash
# 1. Module starts without errors
docker run --rm \
  -e MODULE_PORT=8007 \
  -e DATABASE_URL=... \
  -e SECRET_KEY=... \
  --health-cmd="curl -f http://localhost:8007/health || exit 1" \
  --health-interval=5s \
  --health-timeout=3s \
  kick-module:latest
# Expected: Container health status = healthy

# 2. Health endpoint responds
curl http://localhost:8007/health
# Expected: {"status": "healthy"}

# 3. Status endpoint functional
curl http://localhost:8007/api/v1/status
# Expected: JSON with module=kick, status=operational

# 4. Metrics endpoint works
curl http://localhost:8007/metrics | head -20
# Expected: Prometheus metrics

# 5. Webhook signature verification works
PAYLOAD='{"event":"test"}'
SECRET="test-secret-32-chars-minimum!!"
SIG=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$SECRET" -hex | cut -d' ' -f2)
curl -X POST http://localhost:8007/webhook/kick \
  -H "X-Signature: sha256=$SIG" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD"
# Expected: HTTP 202 Accepted
```

## CI/CD Integration

### GitHub Actions Workflow

```yaml
name: Kick Module Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
      redis:
        image: redis:7

    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          cd trigger/receiver/kick_module_flask
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-asyncio

      - name: Run unit tests
        run: pytest tests/unit/ --cov=src --cov-report=xml

      - name: Run integration tests
        run: pytest tests/integration/ -v

      - name: Upload coverage
        uses: codecov/codecov-action@v3

      - name: Build Docker image
        run: docker build -t kick-module:test trigger/receiver/kick_module_flask/

      - name: Run smoke tests
        run: |
          docker run --rm kick-module:test pytest tests/smoke/ -v
```

## Test Coverage Goals

- Unit tests: 90%+ coverage
- Integration tests: All major code paths
- Functional tests: All event types
- E2E tests: Happy path + error scenarios
- Security tests: All input validation

## See Also

- [API Documentation](API.md)
- [Usage Guide](USAGE.md)
- [Architecture Details](ARCHITECTURE.md)
- [Troubleshooting Guide](TROUBLESHOOTING.md)
